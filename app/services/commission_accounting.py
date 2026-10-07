"""
Phase 9 — Commission & Accounting Engine Service.

Implements verified legacy business logic for:
1. Stateless Commission, TDS, Cut & Pay, and Franchise Overriding Spread Preview
2. Policy Commission Evaluation, Synchronization & Payout Eligibility Verification
3. Commission Approval Gate (`PaymentStatus = 3.00`)
4. Atomic Commission Payout (`tbl_agentcommissionpayment`, `tbl_franchisecommission`, `tbl_transaction`, `tbl_account` AccTransId=6)
5. Atomic Commission Payout Reversal (`tbl_account` AccTransId=7 + balance restoration)
6. Chart of Accounts / Master Ledgers (`tbl_ledgermaster`) & Running-Balance Ledger Statements (`tbl_account`)
7. Double-Entry Vouchers (`AccTransId = 8`) & Voucher Reversals (`AccTransId = 9`)
8. Trial Balance Aggregation & Zero-Variance Double-Entry Invariants
"""
import asyncio
from datetime import date, datetime
from decimal import Decimal
from typing import Dict, List, Literal, Optional, Sequence, Tuple
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import (
    ACCOUNTING_VOUCHER_WRITE_ROLES,
    AGENT_PRINCIPAL_ROLES,
    COMMISSION_APPROVAL_ROLES,
    COMMISSION_PAYOUT_WRITE_ROLES,
    EMPLOYEE_PRINCIPAL_ROLES,
    FRANCHISE_PRINCIPAL_ROLES,
    PrincipalContext,
    _normalize,
    is_global_admin_role,
    is_global_read_role,
)
from app.models.account import Account
from app.models.commission import (
    AgentCommissionPayment,
    CutNPayCommPayable,
    FranchiseCommission,
)
from app.models.ledger import LedgerMaster
from app.models.transaction import Transaction
from app.models.user import User
from app.repositories.commission_accounting import CommissionAccountingRepository
from app.schemas.commission_accounting import (
    AgentCommissionRowResponse,
    CommissionApprovalRequest,
    CommissionCalculateRequest,
    CommissionPayableItemResponse,
    CommissionPayableListResponse,
    CommissionPayoutAllocationInput,
    CommissionPayoutAllocationResponse,
    CommissionPayoutCreateRequest,
    CommissionPayoutListResponse,
    CommissionPayoutResponse,
    CommissionPayoutReverseRequest,
    CommissionPreviewRequest,
    CommissionPreviewResponse,
    CutNPayRowResponse,
    FranchiseCommissionRowResponse,
    LedgerMasterCreateRequest,
    LedgerMasterListResponse,
    LedgerMasterResponse,
    LedgerStatementEntryResponse,
    LedgerStatementResponse,
    PolicyCommissionListResponse,
    PolicyCommissionRecordResponse,
    TrialBalanceLedgerRowResponse,
    TrialBalanceResponse,
    VoucherCreateRequest,
    VoucherLineResponse,
    VoucherListResponse,
    VoucherResponse,
    VoucherReverseRequest,
)
from app.services.rating import HUNDRED, ZERO
from app.repositories.quotation import _to_decimal


def round_2dp(val: Decimal) -> Decimal:
    """Round to 2 decimal places using ROUND_HALF_UP."""
    from decimal import ROUND_HALF_UP
    return val.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


# Process-wide async mutex serializing commission payouts, reversals, and voucher sequence allocation
_COMMISSION_WRITE_LOCK = asyncio.Lock()

_AGENT_ROLES_NORM = frozenset(_normalize(r) for r in AGENT_PRINCIPAL_ROLES)
_FRANCHISE_ROLES_NORM = frozenset(_normalize(r) for r in FRANCHISE_PRINCIPAL_ROLES)
_EMPLOYEE_ROLES_NORM = frozenset(_normalize(r) for r in EMPLOYEE_PRINCIPAL_ROLES)
_APPROVAL_ROLES_NORM = frozenset(_normalize(r) for r in COMMISSION_APPROVAL_ROLES)
_PAYOUT_WRITE_NORM = frozenset(_normalize(r) for r in COMMISSION_PAYOUT_WRITE_ROLES)
_VOUCHER_WRITE_NORM = frozenset(_normalize(r) for r in ACCOUNTING_VOUCHER_WRITE_ROLES)

LEDGER_TYPE_LABELS: Dict[int, str] = {
    1: "ASSET",
    2: "LIABILITY",
    3: "INCOME",
    4: "EXPENSE",
    5: "EQUITY",
}

# Canonical Legacy AccTransId Mapping (GAP-P10-002):
# Legacy core transaction types are 1 (Payment/Receivable), 2 (Receipt/Payable),
# 3 (Commission), and 4 (Contra/Reversal). Note: 15/16 are retired per LBR-123 (zero ledger impact on claims).
LEGACY_ACC_TRANS_TYPE_MAP: Dict[int, str] = {
    1: "LEGACY_PAYMENT_OR_RECEIVABLE",
    2: "LEGACY_RECEIPT_OR_PAYABLE",
    3: "LEGACY_COMMISSION",
    4: "LEGACY_CONTRA_OR_REVERSAL",
    5: "CHEQUE_BOUNCE_PENALTY",
    6: "COMMISSION_PAYOUT_SETTLEMENT",
    7: "COMMISSION_PAYOUT_REVERSAL",
    8: "DOUBLE_ENTRY_VOUCHER",
    9: "VOUCHER_REVERSAL",
    10: "EWALLET_CREDIT",
    11: "EWALLET_DEBIT",
    12: "EWALLET_LOCK",
    13: "EWALLET_RELEASE",
    14: "INSURER_RECONCILIATION",
    17: "ENDORSEMENT_REFUND_DISBURSEMENT",
    18: "ENDORSEMENT_REFUND_REVERSAL",
}

# Canonical Legacy System Ledger Master IDs (LBR-059..LBR-065, LBR-126, GAP-P10-002):
LEGACY_SYSTEM_LEDGER_META: Dict[int, Tuple[str, int, int]] = {
    1161: ("UNCLEAR COMMISSION CONTROL LEDGER (1161)", 2, 20),
    2113: ("TDS PAYABLE LEDGER (2113)", 2, 20),
    1930: ("SALES EXECUTIVE COMMISSION LEDGER (1930)", 4, 40),
    1878: ("ENDORSEMENT INCOME LEDGER (1878)", 3, 30),
}


def payment_status_to_label(ps: Decimal) -> str:
    val = round_2dp(_to_decimal(ps))
    if val == Decimal("1.00"):
        return "PAID"
    if val == Decimal("2.00"):
        return "PARTIALLY_PAID"
    if val == Decimal("3.00"):
        return "APPROVED"
    return "UNPAID"


def calculate_commission_preview_pure(
    payload: CommissionPreviewRequest,
) -> CommissionPreviewResponse:
    """
    Pure deterministic function computing Agent Commission, Franchise Commission,
    OD/Net/Extra bucket splits, TDS deductions, Cut & Pay deduction, and Franchise spread.
    Uses `Decimal` 2-decimal half-up rounding exclusively.
    """
    od_prem = round_2dp(payload.od_premium)
    tp_prem = round_2dp(payload.tp_premium)
    net_prem = (
        round_2dp(payload.net_premium)
        if payload.net_premium is not None
        else round_2dp(od_prem + tp_prem)
    )
    final_prem = (
        round_2dp(payload.final_premium)
        if payload.final_premium is not None
        else round_2dp(net_prem * Decimal("1.18"))
    )

    # 1. Agent Commission (OD, Net, Extra + TDS)
    ag_od_pct = round_2dp(payload.agent_comm_od_pct)
    ag_net_pct = round_2dp(payload.agent_comm_net_pct)
    ag_ext_pct = round_2dp(payload.agent_comm_extra_pct)
    ag_tds_pct = round_2dp(payload.agent_tds_pct)

    ag_od_amt = round_2dp((od_prem * ag_od_pct) / HUNDRED)
    ag_net_amt = round_2dp((net_prem * ag_net_pct) / HUNDRED)
    ag_ext_amt = round_2dp((od_prem * ag_ext_pct) / HUNDRED)

    if (
        ag_od_amt == ZERO
        and ag_net_amt == ZERO
        and ag_ext_amt == ZERO
        and payload.agent_comm_flat_amt is not None
        and payload.agent_comm_flat_amt > ZERO
    ):
        ag_od_amt = round_2dp(payload.agent_comm_flat_amt)

    ag_od_tds = round_2dp((ag_od_amt * ag_tds_pct) / HUNDRED)
    ag_net_tds = round_2dp((ag_net_amt * ag_tds_pct) / HUNDRED)
    ag_ext_tds = round_2dp((ag_ext_amt * ag_tds_pct) / HUNDRED)

    ag_od_net = round_2dp(ag_od_amt - ag_od_tds)
    ag_net_net = round_2dp(ag_net_amt - ag_net_tds)
    ag_ext_net = round_2dp(ag_ext_amt - ag_ext_tds)

    ag_gross = round_2dp(ag_od_amt + ag_net_amt + ag_ext_amt)
    ag_tds = round_2dp(ag_od_tds + ag_net_tds + ag_ext_tds)
    ag_net = round_2dp(ag_gross - ag_tds)

    # 2. Cut & Pay Evaluation
    cutnpay_deducted = ZERO
    if payload.cutnpay_enabled:
        cutnpay_deducted = (
            round_2dp(payload.cutnpay_amount)
            if payload.cutnpay_amount is not None
            else ag_net
        )
        if cutnpay_deducted > ag_net:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"Cut & Pay deduction ({cutnpay_deducted}) cannot exceed "
                    f"Agent Net Commission ({ag_net})."
                ),
            )
        if cutnpay_deducted > final_prem:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"Cut & Pay deduction ({cutnpay_deducted}) cannot exceed "
                    f"Final Premium ({final_prem})."
                ),
            )

    req_payable = round_2dp(final_prem - cutnpay_deducted)
    ag_adv_amt = cutnpay_deducted
    ag_rem_payable = round_2dp(ag_net - ag_adv_amt)

    if ag_net > ZERO and ag_rem_payable == ZERO and ag_adv_amt > ZERO:
        ag_init_status = Decimal("1.00")
    elif ag_adv_amt > ZERO and ag_rem_payable > ZERO:
        ag_init_status = Decimal("2.00")
    else:
        ag_init_status = Decimal("0.00")

    unclear_comm_acct = -ag_net if ag_net > ZERO else ZERO

    # 3. Franchise Commission (OD, Net, Extra + TDS + Spread)
    frn_od_pct = round_2dp(payload.franchise_comm_od_pct)
    frn_net_pct = round_2dp(payload.franchise_comm_net_pct)
    frn_ext_pct = round_2dp(payload.franchise_comm_extra_pct)
    frn_tds_pct = round_2dp(payload.franchise_tds_pct)

    frn_od_amt = round_2dp((od_prem * frn_od_pct) / HUNDRED)
    frn_net_amt = round_2dp((net_prem * frn_net_pct) / HUNDRED)
    frn_ext_amt = round_2dp((od_prem * frn_ext_pct) / HUNDRED)

    frn_od_tds = round_2dp((frn_od_amt * frn_tds_pct) / HUNDRED)
    frn_net_tds = round_2dp((frn_net_amt * frn_tds_pct) / HUNDRED)
    frn_ext_tds = round_2dp((frn_ext_amt * frn_tds_pct) / HUNDRED)

    frn_od_net = round_2dp(frn_od_amt - frn_od_tds)
    frn_net_net = round_2dp(frn_net_amt - frn_net_tds)
    frn_ext_net = round_2dp(frn_ext_amt - frn_ext_tds)

    frn_gross = round_2dp(frn_od_amt + frn_net_amt + frn_ext_amt)
    frn_tds = round_2dp(frn_od_tds + frn_net_tds + frn_ext_tds)
    frn_net = round_2dp(frn_gross - frn_tds)
    profit_spread = round_2dp(frn_net - ag_net) if frn_gross > ZERO else ZERO

    return CommissionPreviewResponse(
        od_premium=od_prem,
        tp_premium=tp_prem,
        net_premium=net_prem,
        final_premium=final_prem,
        agent_id=payload.agent_id,
        agent_comm_od_pct=ag_od_pct,
        agent_comm_od_amt=ag_od_amt,
        agent_tds_od_amt=ag_od_tds,
        agent_net_od_amt=ag_od_net,
        agent_comm_net_pct=ag_net_pct,
        agent_comm_net_amt=ag_net_amt,
        agent_tds_net_amt=ag_net_tds,
        agent_net_net_amt=ag_net_net,
        agent_comm_extra_pct=ag_ext_pct,
        agent_comm_extra_amt=ag_ext_amt,
        agent_tds_extra_amt=ag_ext_tds,
        agent_net_extra_amt=ag_ext_net,
        agent_tds_pct=ag_tds_pct,
        agent_gross_commission=ag_gross,
        agent_tds_amount=ag_tds,
        agent_net_commission=ag_net,
        cutnpay_enabled=payload.cutnpay_enabled,
        cutnpay_deducted_amount=cutnpay_deducted,
        customer_required_payable_amount=req_payable,
        agent_initial_paid_adv_amt=ag_adv_amt,
        agent_remaining_payable_amount=ag_rem_payable,
        agent_initial_payment_status=ag_init_status,
        unclear_commission_account_amount=unclear_comm_acct,
        franchise_id=payload.franchise_id,
        franchise_comm_od_pct=frn_od_pct,
        franchise_comm_od_amt=frn_od_amt,
        franchise_tds_od_amt=frn_od_tds,
        franchise_net_od_amt=frn_od_net,
        franchise_comm_net_pct=frn_net_pct,
        franchise_comm_net_amt=frn_net_amt,
        franchise_tds_net_amt=frn_net_tds,
        franchise_net_net_amt=frn_net_net,
        franchise_comm_extra_pct=frn_ext_pct,
        franchise_comm_extra_amt=frn_ext_amt,
        franchise_tds_extra_amt=frn_ext_tds,
        franchise_net_extra_amt=frn_ext_net,
        franchise_tds_pct=frn_tds_pct,
        franchise_gross_commission=frn_gross,
        franchise_tds_amount=frn_tds,
        franchise_net_commission=frn_net,
        profit_of_net_commission=profit_spread,
        franchise_remaining_payable_amount=frn_net,
    )


class CommissionAccountingService:
    """
    Business logic service for Phase 9 Commission Calculation, Approval, Payout,
    Payout Reversal, Master Ledgers, Double-Entry Vouchers, and Trial Balance.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = CommissionAccountingRepository(session)

    # -----------------------------------------------------------------------
    # 1. Principal & RBAC Scope Helpers
    # -----------------------------------------------------------------------

    @staticmethod
    def _get_principal(user: User) -> PrincipalContext:
        ctx = getattr(user, "principal_context", None)
        if isinstance(ctx, PrincipalContext):
            return ctx
        return PrincipalContext(
            user_id=user.UserId,
            username=getattr(user, "UserName", None),
            role_id=getattr(user, "UserRoleId", None),
            role_name=getattr(user, "role_name", None),
            branch_id=getattr(user, "BranchId", None),
            agent_id=getattr(user, "agent_id", None),
            emp_id=getattr(user, "emp_id", None),
            employee_id=getattr(user, "employee_id", None),
            franchise_id=getattr(user, "franchise_id", None),
        )

    @staticmethod
    def _is_cross_branch_role(role_name: Optional[str]) -> bool:
        norm = _normalize(role_name)
        return (
            is_global_admin_role(role_name)
            or is_global_read_role(role_name)
            or norm in {"SHREYANSH OWNER", "ALL USER"}
        )

    def _assert_can_access_transaction(
        self,
        tx: Transaction,
        user: User,
        for_write: bool = False,
    ) -> None:
        ctx = self._get_principal(user)
        norm_role = _normalize(ctx.role_name)

        if is_global_admin_role(ctx.role_name) or norm_role in {"ACCOUNT", "ACCOUNT HEAD", "SHREYANSH OWNER"}:
            return

        if not for_write and self._is_cross_branch_role(ctx.role_name):
            return

        if ctx.branch_id is not None and tx.BranchId is not None and tx.BranchId != ctx.branch_id:
            if norm_role != "ALL USER":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=(
                        f"Access denied: Policy Transaction #{tx.TransanctionId} belongs to "
                        f"Branch {tx.BranchId}, outside caller Branch {ctx.branch_id}."
                    ),
                )

        if norm_role in _AGENT_ROLES_NORM:
            expected_agent = ctx.agent_id or ctx.user_id
            if tx.AgentId != expected_agent:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: Commission record does not belong to your AgentId.",
                )
        elif norm_role in _FRANCHISE_ROLES_NORM:
            expected_frn = str(ctx.franchise_id or ctx.user_id)
            if str(tx.FranchiseCode or "0") != expected_frn:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: Commission record does not belong to your Franchise scope.",
                )
        elif norm_role in _EMPLOYEE_ROLES_NORM:
            expected_emp = ctx.emp_id or ctx.user_id
            if tx.SalesEx_id != expected_emp and tx.LocationHeadId != expected_emp:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: Commission record is outside your Sales Executive / Hierarchy scope.",
                )

    # -----------------------------------------------------------------------
    # 2. Eligibility Evaluation & Row Mappers
    # -----------------------------------------------------------------------

    @staticmethod
    def evaluate_payout_eligibility(
        tx: Transaction,
        acp: Optional[AgentCommissionPayment] = None,
        cnp: Optional[CutNPayCommPayable] = None,
    ) -> Tuple[bool, str]:
        """
        Determines whether a policy transaction is eligible for post-booking commission payout.
        """
        if tx.isdeleted not in ("0", None) or (tx.TStatus or "").strip().lower() == "cancelled":
            return False, "Policy is cancelled or soft-deleted."

        outstanding = round_2dp(_to_decimal(tx.OutstandingAmount))
        if outstanding > ZERO:
            return False, f"Policy has unpaid OutstandingAmount ({outstanding})."

        if (tx.Ischequeclearing or 0) == 1:
            return False, "Policy has a cheque pending bank clearance (Ischequeclearing=1)."

        if (tx.ChequeBankStatus or 0) == 2:
            return False, "Policy has a dishonored/bounced cheque (ChequeBankStatus=2)."

        if cnp is not None and (cnp.Flag or "").strip().upper().startswith("HOLD"):
            return False, f"Commission is on hold due to {cnp.Flag}."

        if acp is not None and (acp.Narration or "").strip().upper().startswith("HOLD:"):
            return False, f"Agent commission is on hold ({acp.Narration})."

        return True, "ELIGIBLE"

    @staticmethod
    def _map_agent_comm_row(acp: AgentCommissionPayment) -> AgentCommissionRowResponse:
        agent_id_val: Optional[int] = None
        if acp.Extra1 and str(acp.Extra1).strip().isdigit():
            agent_id_val = int(str(acp.Extra1).strip())
        tds_val = ZERO
        if acp.Extra2:
            tds_val = round_2dp(_to_decimal(acp.Extra2))
        else:
            tds_val = round_2dp(
                _to_decimal(acp.totalCommision) - _to_decimal(acp.NetCommission)
            )
        ps = round_2dp(_to_decimal(acp.PaymentStatus))
        return AgentCommissionRowResponse(
            agent_comm_id=acp.AgentCommId,
            transaction_id=acp.TransanctionId or 0,
            agent_id=agent_id_val,
            agent_name=acp.AgentName,
            branch_name=acp.BranchName,
            premium_amount=round_2dp(_to_decimal(acp.PremiumAmount)),
            gross_commission=round_2dp(_to_decimal(acp.totalCommision)),
            tds_amount=tds_val,
            net_commission=round_2dp(_to_decimal(acp.NetCommission)),
            net_commission_od=round_2dp(_to_decimal(acp.NetCommission_OD)),
            net_commission_net=round_2dp(_to_decimal(acp.NetCommission_Net)),
            net_commission_extra=round_2dp(_to_decimal(acp.NetCommission_Extra)),
            adv_amt_paid=round_2dp(_to_decimal(acp.AdvAmt)),
            remaining_net_amount=round_2dp(_to_decimal(acp.NetAmount)),
            payment_status=ps,
            payment_status_label=payment_status_to_label(ps),
            narration=acp.Narration,
            isdeleted=acp.isdeleted or "0",
            trans_date=acp.TransDate,
        )

    @staticmethod
    def _map_franchise_comm_row(fc: FranchiseCommission) -> FranchiseCommissionRowResponse:
        net_comm = round_2dp(_to_decimal(fc.FranchiseNetComm))
        paid_amt = round_2dp(_to_decimal(fc.FCommissionPaid))
        rem_amt = max(ZERO, round_2dp(net_comm - paid_amt))
        return FranchiseCommissionRowResponse(
            franchise_comm_id=fc.FranchiseCommId,
            transaction_id=fc.TransanctionId or 0,
            franchise_id=fc.FranchiseId,
            agent_id=fc.AgentId,
            franchise_comm_pct=round_2dp(_to_decimal(fc.Franchisecomm)),
            gross_commission=round_2dp(_to_decimal(fc.FranchiseCommAmt)),
            tds_amount=round_2dp(_to_decimal(fc.FranchiseTdsAmt)),
            net_commission=net_comm,
            paid_amount=paid_amt,
            remaining_payable_amount=rem_amt,
            profit_of_net_commission=round_2dp(_to_decimal(fc.ProfitofNetCommision)),
            franchise_comm_od_pct=round_2dp(_to_decimal(fc.Franchisecomm_OD)),
            franchise_comm_amt_od=round_2dp(_to_decimal(fc.FranchiseCommAmt_OD)),
            franchise_tds_amt_od=round_2dp(_to_decimal(fc.FranchiseTdsAmt_OD)),
            franchise_net_comm_od=round_2dp(_to_decimal(fc.FranchiseNetComm_OD)),
            franchise_comm_net_pct=round_2dp(_to_decimal(fc.Franchisecomm_Net)),
            franchise_comm_amt_net=round_2dp(_to_decimal(fc.FranchiseCommAmt_Net)),
            franchise_tds_amt_net=round_2dp(_to_decimal(fc.FranchiseTdsAmt_Net)),
            franchise_net_comm_net=round_2dp(_to_decimal(fc.FranchiseNetComm_Net)),
            franchise_comm_extra_pct=round_2dp(_to_decimal(fc.Franchisecomm_Extra)),
            franchise_comm_amt_extra=round_2dp(_to_decimal(fc.FranchiseCommAmt_Extra)),
            franchise_tds_amt_extra=round_2dp(_to_decimal(fc.FranchiseTdsAmt_Extra)),
            franchise_net_comm_extra=round_2dp(_to_decimal(fc.FranchiseNetComm_Extra)),
            broker_id=fc.BrokerId or 0,
            self_discount=round_2dp(_to_decimal(fc.SelfDiscount)),
            intensive_amount=round_2dp(_to_decimal(fc.IntensiveAmount)),
            isdeleted=fc.isdeleted or 0,
            franchise_date=fc.FranchiseDate,
        )

    @staticmethod
    def _map_cutnpay_row(cnp: CutNPayCommPayable) -> CutNPayRowResponse:
        return CutNPayRowResponse(
            cutnpay_comm_pay_id=cnp.CutNPayCommPayId,
            transaction_id=cnp.TransactionId or 0,
            policy_no=cnp.PolicyNo,
            customer_id=cnp.CustomerId,
            agent_id=cnp.AgentId,
            sales_ex_id=cnp.SalesExId,
            balance=round_2dp(_to_decimal(cnp.Balance)),
            comm_payable=round_2dp(_to_decimal(cnp.CommPayable)),
            flag=cnp.Flag or "CUTNPAY",
            isdeleted=cnp.Isdeleted or 0,
            created_date=cnp.CreatedDate,
        )

    async def _build_policy_commission_response(
        self,
        tx: Transaction,
    ) -> PolicyCommissionRecordResponse:
        acp = await self.repo.get_agent_comm_by_tx(tx.TransanctionId, include_deleted=False)
        fc = await self.repo.get_franchise_comm_by_tx(tx.TransanctionId, include_deleted=False)
        cnp = await self.repo.get_cutnpay_by_tx(tx.TransanctionId, include_deleted=False)

        eligible, reason = self.evaluate_payout_eligibility(tx, acp, cnp)

        acp_resp = self._map_agent_comm_row(acp) if acp is not None else None
        fc_resp = self._map_franchise_comm_row(fc) if fc is not None else None
        cnp_resp = self._map_cutnpay_row(cnp) if cnp is not None else None

        frn_id_val: Optional[int] = None
        if fc is not None and fc.FranchiseId:
            frn_id_val = fc.FranchiseId
        elif tx.FranchiseCode and str(tx.FranchiseCode).strip().isdigit():
            parsed_frn = int(str(tx.FranchiseCode).strip())
            if parsed_frn > 0:
                frn_id_val = parsed_frn

        ag_gross = (
            acp_resp.gross_commission
            if acp_resp is not None
            else round_2dp(
                _to_decimal(tx.AgentCommAmt_OD or tx.AgentCommAmt)
                + _to_decimal(tx.AgentCommAmt_Net)
                + _to_decimal(tx.AgentCommAmt_Extra)
            )
        )
        ag_tds = (
            acp_resp.tds_amount
            if acp_resp is not None
            else round_2dp(_to_decimal(tx.TdsAmt))
        )
        ag_net = (
            acp_resp.net_commission
            if acp_resp is not None
            else round_2dp(_to_decimal(tx.NetCommission))
        )
        cnp_deducted = cnp_resp.comm_payable if cnp_resp is not None else ZERO
        ag_paid = acp_resp.adv_amt_paid if acp_resp is not None else cnp_deducted
        ag_rem = (
            acp_resp.remaining_net_amount
            if acp_resp is not None
            else max(ZERO, round_2dp(ag_net - ag_paid))
        )

        frn_gross = fc_resp.gross_commission if fc_resp is not None else ZERO
        frn_tds = fc_resp.tds_amount if fc_resp is not None else ZERO
        frn_net = fc_resp.net_commission if fc_resp is not None else ZERO
        frn_paid = fc_resp.paid_amount if fc_resp is not None else ZERO
        frn_rem = fc_resp.remaining_payable_amount if fc_resp is not None else ZERO
        profit_spread = fc_resp.profit_of_net_commission if fc_resp is not None else ZERO

        return PolicyCommissionRecordResponse(
            transaction_id=tx.TransanctionId,
            inward_no=tx.InwardNo or "",
            policy_no=tx.PolicyNo,
            branch_id=tx.BranchId or 1,
            customer_id=tx.CustomerId or 0,
            agent_id=tx.AgentId,
            franchise_id=frn_id_val,
            sales_ex_id=tx.SalesEx_id,
            t_status=tx.TStatus or "Pending",
            pending_status=tx.pendingStatus if tx.pendingStatus is not None else 1,
            paid_amount=round_2dp(_to_decimal(tx.PaidAmount)),
            outstanding_amount=round_2dp(_to_decimal(tx.OutstandingAmount)),
            is_cheque_clearing=tx.Ischequeclearing or 0,
            is_cheque_cleared=tx.IsChequeCleared or 0,
            cheque_bank_status=tx.ChequeBankStatus or 0,
            commission_paid_flag=tx.CommissionPaid or 0,
            is_payout_eligible=eligible,
            eligibility_reason=reason,
            od_premium=round_2dp(_to_decimal(tx.ODPermium)),
            tp_premium=round_2dp(_to_decimal(tx.TPPermium)),
            net_premium=round_2dp(_to_decimal(tx.NetPermium)),
            final_premium=round_2dp(_to_decimal(tx.Amount)),
            agent_gross_commission=ag_gross,
            agent_tds_amount=ag_tds,
            agent_net_commission=ag_net,
            cutnpay_deducted_amount=cnp_deducted,
            agent_paid_amount=ag_paid,
            agent_remaining_payable=ag_rem,
            franchise_gross_commission=frn_gross,
            franchise_tds_amount=frn_tds,
            franchise_net_commission=frn_net,
            franchise_paid_amount=frn_paid,
            franchise_remaining_payable=frn_rem,
            profit_of_net_commission=profit_spread,
            agent_commission_row=acp_resp,
            franchise_commission_row=fc_resp,
            cutnpay_row=cnp_resp,
        )

    # -----------------------------------------------------------------------
    # 3. Commission Preview, Policy Calculation, Read, Payables & Approval
    # -----------------------------------------------------------------------

    async def preview_commission(
        self,
        payload: CommissionPreviewRequest,
        current_user: User,
    ) -> CommissionPreviewResponse:
        return calculate_commission_preview_pure(payload)

    async def calculate_or_sync_policy_commission(
        self,
        payload: CommissionCalculateRequest,
        current_user: User,
    ) -> PolicyCommissionRecordResponse:
        """
        Evaluates or recalculates commission rows for a booked policy (`POST /api/v1/commissions/calculate`).
        """
        async with _COMMISSION_WRITE_LOCK:
            try:
                tx = await self.repo.get_transaction_by_id(
                    payload.transaction_id, include_deleted=False, for_update=True
                )
                if tx is None:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Policy Transaction #{payload.transaction_id} not found.",
                    )
                self._assert_can_access_transaction(tx, current_user, for_write=True)

                acp = await self.repo.get_agent_comm_by_tx(
                    tx.TransanctionId, include_deleted=False, for_update=True
                )
                fc = await self.repo.get_franchise_comm_by_tx(
                    tx.TransanctionId, include_deleted=False, for_update=True
                )
                cnp = await self.repo.get_cutnpay_by_tx(
                    tx.TransanctionId, include_deleted=False, for_update=True
                )

                if payload.recalculate:
                    # Verify no post-booking cash payout has already occurred
                    cnp_amt = round_2dp(_to_decimal(cnp.CommPayable)) if cnp is not None else ZERO
                    adv_amt = round_2dp(_to_decimal(acp.AdvAmt)) if acp is not None else ZERO
                    frn_paid = round_2dp(_to_decimal(fc.FCommissionPaid)) if fc is not None else ZERO
                    if adv_amt > cnp_amt or frn_paid > ZERO or ((tx.CommissionPaid or 0) == 1 and cnp_amt == ZERO):
                        raise HTTPException(
                            status_code=status.HTTP_409_CONFLICT,
                            detail=(
                                f"Cannot recalculate commission on Policy #{tx.TransanctionId}: "
                                f"commission payout has already been partially or fully disbursed."
                            ),
                        )

                    frn_id_val: Optional[int] = None
                    if fc is not None and fc.FranchiseId:
                        frn_id_val = fc.FranchiseId
                    elif tx.FranchiseCode and str(tx.FranchiseCode).strip().isdigit():
                        frn_id_val = int(str(tx.FranchiseCode).strip())

                    preview_req = CommissionPreviewRequest(
                        od_premium=round_2dp(_to_decimal(tx.ODPermium)),
                        tp_premium=round_2dp(_to_decimal(tx.TPPermium)),
                        net_premium=round_2dp(_to_decimal(tx.NetPermium)),
                        final_premium=round_2dp(_to_decimal(tx.Amount)),
                        agent_id=tx.AgentId,
                        agent_comm_od_pct=(
                            payload.agent_comm_od_pct
                            if payload.agent_comm_od_pct is not None
                            else round_2dp(_to_decimal(tx.AgentComm_OD or tx.AgentComm))
                        ),
                        agent_comm_net_pct=(
                            payload.agent_comm_net_pct
                            if payload.agent_comm_net_pct is not None
                            else round_2dp(_to_decimal(tx.AgentComm_Net))
                        ),
                        agent_comm_extra_pct=(
                            payload.agent_comm_extra_pct
                            if payload.agent_comm_extra_pct is not None
                            else round_2dp(_to_decimal(tx.AgentComm_Extra))
                        ),
                        agent_tds_pct=(
                            payload.agent_tds_pct
                            if payload.agent_tds_pct is not None
                            else round_2dp(_to_decimal(tx.tdsPercent or Decimal("5.00")))
                        ),
                        franchise_id=frn_id_val,
                        franchise_comm_od_pct=(
                            payload.franchise_comm_od_pct
                            if payload.franchise_comm_od_pct is not None
                            else (
                                round_2dp(_to_decimal(fc.Franchisecomm_OD))
                                if fc is not None
                                else ZERO
                            )
                        ),
                        franchise_comm_net_pct=(
                            payload.franchise_comm_net_pct
                            if payload.franchise_comm_net_pct is not None
                            else (
                                round_2dp(_to_decimal(fc.Franchisecomm_Net))
                                if fc is not None
                                else ZERO
                            )
                        ),
                        franchise_comm_extra_pct=(
                            payload.franchise_comm_extra_pct
                            if payload.franchise_comm_extra_pct is not None
                            else (
                                round_2dp(_to_decimal(fc.Franchisecomm_Extra))
                                if fc is not None
                                else ZERO
                            )
                        ),
                        franchise_tds_pct=(
                            payload.franchise_tds_pct
                            if payload.franchise_tds_pct is not None
                            else (
                                round_2dp(_to_decimal(fc.tat or Decimal("5.00")))
                                if fc is not None
                                else Decimal("5.00")
                            )
                        ),
                        cutnpay_enabled=(cnp is not None and cnp_amt > ZERO),
                        cutnpay_amount=cnp_amt if (cnp is not None and cnp_amt > ZERO) else None,
                    )
                    calc = calculate_commission_preview_pure(preview_req)
                    now_dt = datetime.utcnow()

                    # Update tbl_transaction commission fields
                    tx.AgentComm = calc.agent_comm_od_pct
                    tx.AgentComm_OD = calc.agent_comm_od_pct
                    tx.AgentCommAmt = calc.agent_gross_commission
                    tx.AgentCommAmt_OD = calc.agent_comm_od_amt
                    tx.tdsPercent = calc.agent_tds_pct
                    tx.TdsAmt = calc.agent_tds_amount
                    tx.TdsAmt_OD = calc.agent_tds_od_amt
                    tx.NetCommission_OD = calc.agent_net_od_amt
                    tx.AgentComm_Net = calc.agent_comm_net_pct
                    tx.AgentCommAmt_Net = calc.agent_comm_net_amt
                    tx.TdsAmt_Net = calc.agent_tds_net_amt
                    tx.NetCommission_Net = calc.agent_net_net_amt
                    tx.AgentComm_Extra = calc.agent_comm_extra_pct
                    tx.AgentCommAmt_Extra = calc.agent_comm_extra_amt
                    tx.TdsAmt_Extra = calc.agent_tds_extra_amt
                    tx.NetCommission_Extra = calc.agent_net_extra_amt
                    tx.NetCommission = calc.agent_net_commission
                    tx.UpdateDate = now_dt
                    tx.UpdateUser = str(current_user.UserId)

                    if payload.simulate_failure_at == "AFTER_TX_UPDATE":
                        raise RuntimeError("Simulated fault AFTER_TX_UPDATE in calculate_or_sync_policy_commission")

                    # Update or create AgentCommissionPayment
                    if acp is not None:
                        acp.PremiumAmount = calc.net_premium
                        acp.totalCommision = calc.agent_gross_commission
                        acp.NetCommission = calc.agent_net_commission
                        acp.AdvAmt = calc.agent_initial_paid_adv_amt
                        acp.NetAmount = calc.agent_remaining_payable_amount
                        acp.PaymentStatus = calc.agent_initial_payment_status
                        acp.Extra2 = str(calc.agent_tds_amount)
                        acp.NetCommission_OD = calc.agent_net_od_amt
                        acp.NetCommission_Net = calc.agent_net_net_amt
                        acp.NetCommission_Extra = calc.agent_net_extra_amt
                    elif calc.agent_gross_commission > ZERO or tx.AgentId:
                        acp = AgentCommissionPayment(
                            FromDate=now_dt,
                            ToDate=now_dt,
                            TransanctionId=tx.TransanctionId,
                            BranchName=f"Branch-{tx.BranchId or 1}",
                            AgentName=f"Agent-{tx.AgentId or 0}",
                            PremiumAmount=calc.net_premium,
                            NetCommission=calc.agent_net_commission,
                            totalCommision=calc.agent_gross_commission,
                            AdvAmt=calc.agent_initial_paid_adv_amt,
                            NetAmount=calc.agent_remaining_payable_amount,
                            PaymentStatus=calc.agent_initial_payment_status,
                            Narration=f"Policy Commission Evaluated - {tx.InwardNo}",
                            Extra1=str(tx.AgentId or 0),
                            Extra2=str(calc.agent_tds_amount),
                            isdeleted="0",
                            NetCommission_OD=calc.agent_net_od_amt,
                            NetCommission_Net=calc.agent_net_net_amt,
                            NetCommission_Extra=calc.agent_net_extra_amt,
                            TransDate=now_dt,
                        )
                        self.session.add(acp)
                        await self.session.flush()

                    # Update or create FranchiseCommission
                    if fc is not None:
                        fc.tat = calc.franchise_tds_pct
                        fc.Franchisecomm = round_2dp(
                            calc.franchise_comm_od_pct
                            + calc.franchise_comm_net_pct
                            + calc.franchise_comm_extra_pct
                        )
                        fc.FranchiseCommAmt = calc.franchise_gross_commission
                        fc.FranchiseTdsAmt = calc.franchise_tds_amount
                        fc.FranchiseNetComm = calc.franchise_net_commission
                        fc.Franchisecomm_OD = calc.franchise_comm_od_pct
                        fc.FranchiseCommAmt_OD = calc.franchise_comm_od_amt
                        fc.FranchiseTdsAmt_OD = calc.franchise_tds_od_amt
                        fc.FranchiseNetComm_OD = calc.franchise_net_od_amt
                        fc.Franchisecomm_Net = calc.franchise_comm_net_pct
                        fc.FranchiseCommAmt_Net = calc.franchise_comm_net_amt
                        fc.FranchiseTdsAmt_Net = calc.franchise_tds_net_amt
                        fc.FranchiseNetComm_Net = calc.franchise_net_net_amt
                        fc.Franchisecomm_Extra = calc.franchise_comm_extra_pct
                        fc.FranchiseCommAmt_Extra = calc.franchise_comm_extra_amt
                        fc.FranchiseTdsAmt_Extra = calc.franchise_tds_extra_amt
                        fc.FranchiseNetComm_Extra = calc.franchise_net_extra_amt
                        fc.ProfitofNetCommision = calc.profit_of_net_commission
                    elif calc.franchise_gross_commission > ZERO or frn_id_val:
                        fc = FranchiseCommission(
                            FranchiseDate=now_dt,
                            TransanctionId=tx.TransanctionId,
                            FranchiseId=frn_id_val or 0,
                            AgentId=tx.AgentId or 0,
                            tat=calc.franchise_tds_pct,
                            Franchisecomm=round_2dp(
                                calc.franchise_comm_od_pct
                                + calc.franchise_comm_net_pct
                                + calc.franchise_comm_extra_pct
                            ),
                            FranchiseCommAmt=calc.franchise_gross_commission,
                            FranchiseTdsAmt=calc.franchise_tds_amount,
                            FranchiseNetComm=calc.franchise_net_commission,
                            FCommissionPaid=ZERO,
                            isdeleted=0,
                            Franchisecomm_OD=calc.franchise_comm_od_pct,
                            FranchiseCommAmt_OD=calc.franchise_comm_od_amt,
                            FranchiseTdsAmt_OD=calc.franchise_tds_od_amt,
                            FranchiseNetComm_OD=calc.franchise_net_od_amt,
                            Franchisecomm_Net=calc.franchise_comm_net_pct,
                            FranchiseCommAmt_Net=calc.franchise_comm_net_amt,
                            FranchiseTdsAmt_Net=calc.franchise_tds_net_amt,
                            FranchiseNetComm_Net=calc.franchise_net_net_amt,
                            Franchisecomm_Extra=calc.franchise_comm_extra_pct,
                            FranchiseCommAmt_Extra=calc.franchise_comm_extra_amt,
                            FranchiseTdsAmt_Extra=calc.franchise_tds_extra_amt,
                            FranchiseNetComm_Extra=calc.franchise_net_extra_amt,
                            ProfitofNetCommision=calc.profit_of_net_commission,
                            GridValidDate=now_dt,
                            BrokerId=0,
                            SelfDiscount=ZERO,
                            IntensiveAmount=ZERO,
                        )
                        self.session.add(fc)
                        await self.session.flush()

                    if payload.simulate_failure_at == "BEFORE_COMMIT":
                        raise RuntimeError("Simulated fault BEFORE_COMMIT in calculate_or_sync_policy_commission")

                await self.session.commit()
            except HTTPException:
                await self.session.rollback()
                raise
            except Exception as exc:
                await self.session.rollback()
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Atomic commission calculation rolled back: {exc}",
                ) from exc

        return await self._build_policy_commission_response(tx)

    async def get_policy_commission(
        self,
        transaction_id: int,
        current_user: User,
    ) -> PolicyCommissionRecordResponse:
        tx = await self.repo.get_transaction_by_id(transaction_id, include_deleted=False)
        if tx is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Policy Transaction #{transaction_id} not found.",
            )
        self._assert_can_access_transaction(tx, current_user, for_write=False)
        return await self._build_policy_commission_response(tx)

    async def list_commissions(
        self,
        current_user: User,
        *,
        agent_id: Optional[int] = None,
        franchise_id: Optional[int] = None,
        policy_no: Optional[str] = None,
        inward_no: Optional[str] = None,
        commission_paid: Optional[int] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> PolicyCommissionListResponse:
        ctx = self._get_principal(current_user)
        norm_role = _normalize(ctx.role_name)

        branch_filter: Optional[int] = None
        agent_filter = agent_id
        frn_filter = str(franchise_id) if franchise_id is not None else None
        sales_filter: Optional[int] = None

        if not self._is_cross_branch_role(ctx.role_name):
            branch_filter = ctx.branch_id or 1
            if norm_role in _AGENT_ROLES_NORM:
                bound_agent = ctx.agent_id or ctx.user_id
                if agent_id is not None and agent_id != bound_agent:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Access denied: Agent principal can only query its own commissions.",
                    )
                agent_filter = bound_agent
            elif norm_role in _FRANCHISE_ROLES_NORM:
                bound_frn = str(ctx.franchise_id or ctx.user_id)
                if frn_filter is not None and frn_filter != bound_frn:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Access denied: Franchise principal can only query its own commissions.",
                    )
                frn_filter = bound_frn
            elif norm_role in _EMPLOYEE_ROLES_NORM:
                sales_filter = ctx.emp_id or ctx.user_id

        total, rows = await self.repo.list_commission_transactions(
            branch_id=branch_filter,
            agent_id=agent_filter,
            franchise_code=frn_filter,
            sales_ex_id=sales_filter,
            policy_no=policy_no,
            inward_no=inward_no,
            commission_paid=commission_paid,
            limit=limit,
            offset=offset,
        )
        items = [await self._build_policy_commission_response(r) for r in rows]
        return PolicyCommissionListResponse(
            total=total,
            limit=limit,
            offset=offset,
            items=items,
        )

    async def list_commission_payables(
        self,
        current_user: User,
        *,
        partner_type: Optional[Literal["AGENT", "FRANCHISE"]] = None,
        partner_id: Optional[int] = None,
        only_eligible: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> CommissionPayableListResponse:
        ctx = self._get_principal(current_user)
        norm_role = _normalize(ctx.role_name)

        eff_type = partner_type
        eff_partner_id = partner_id
        branch_filter: Optional[int] = None

        if not self._is_cross_branch_role(ctx.role_name):
            branch_filter = ctx.branch_id or 1
            if norm_role in _AGENT_ROLES_NORM:
                bound_agent = ctx.agent_id or ctx.user_id
                if eff_type == "FRANCHISE" or (eff_partner_id is not None and eff_partner_id != bound_agent):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Access denied: Agent principal can only view its own Agent commission payables.",
                    )
                eff_type = "AGENT"
                eff_partner_id = bound_agent
            elif norm_role in _FRANCHISE_ROLES_NORM:
                bound_frn = ctx.franchise_id or ctx.user_id
                if eff_type == "AGENT" or (eff_partner_id is not None and eff_partner_id != bound_frn):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Access denied: Franchise principal can only view its own Franchise commission payables.",
                    )
                eff_type = "FRANCHISE"
                eff_partner_id = bound_frn

        payable_items: List[CommissionPayableItemResponse] = []

        # 1. Collect Agent Commission Payables
        if eff_type in (None, "AGENT"):
            acp_rows = await self.repo.list_agent_comm_rows_for_partner(
                agent_id=eff_partner_id,
                only_unpaid=True,
                for_update=False,
            )
            for acp in acp_rows:
                if not acp.TransanctionId:
                    continue
                tx = await self.repo.get_transaction_by_id(acp.TransanctionId, include_deleted=False)
                if tx is None:
                    continue
                if branch_filter is not None and (tx.BranchId or 1) != branch_filter:
                    continue
                cnp = await self.repo.get_cutnpay_by_tx(tx.TransanctionId, include_deleted=False)
                eligible, reason = self.evaluate_payout_eligibility(tx, acp, cnp)
                if only_eligible and not eligible:
                    continue

                mapped = self._map_agent_comm_row(acp)
                payable_items.append(
                    CommissionPayableItemResponse(
                        partner_type="AGENT",
                        partner_id=mapped.agent_id or (tx.AgentId or 0),
                        transaction_id=tx.TransanctionId,
                        inward_no=tx.InwardNo or "",
                        policy_no=tx.PolicyNo,
                        branch_id=tx.BranchId or 1,
                        commission_row_id=acp.AgentCommId,
                        gross_commission=mapped.gross_commission,
                        tds_amount=mapped.tds_amount,
                        net_commission=mapped.net_commission,
                        already_settled_amount=mapped.adv_amt_paid,
                        remaining_payable_amount=mapped.remaining_net_amount,
                        payment_status=mapped.payment_status,
                        payment_status_label=mapped.payment_status_label,
                        is_payout_eligible=eligible,
                        eligibility_reason=reason,
                        trans_date=mapped.trans_date or tx.TransDate,
                    )
                )

        # 2. Collect Franchise Commission Payables
        if eff_type in (None, "FRANCHISE"):
            fc_rows = await self.repo.list_franchise_comm_rows_for_partner(
                franchise_id=eff_partner_id,
                only_unpaid=True,
                for_update=False,
            )
            for fc in fc_rows:
                if not fc.TransanctionId:
                    continue
                tx = await self.repo.get_transaction_by_id(fc.TransanctionId, include_deleted=False)
                if tx is None:
                    continue
                if branch_filter is not None and (tx.BranchId or 1) != branch_filter:
                    continue
                acp = await self.repo.get_agent_comm_by_tx(tx.TransanctionId, include_deleted=False)
                cnp = await self.repo.get_cutnpay_by_tx(tx.TransanctionId, include_deleted=False)
                eligible, reason = self.evaluate_payout_eligibility(tx, acp, cnp)
                if only_eligible and not eligible:
                    continue

                mapped_fc = self._map_franchise_comm_row(fc)
                if mapped_fc.remaining_payable_amount <= ZERO:
                    continue
                ps_fc = (
                    Decimal("2.00")
                    if mapped_fc.paid_amount > ZERO
                    else Decimal("0.00")
                )
                payable_items.append(
                    CommissionPayableItemResponse(
                        partner_type="FRANCHISE",
                        partner_id=fc.FranchiseId or 0,
                        transaction_id=tx.TransanctionId,
                        inward_no=tx.InwardNo or "",
                        policy_no=tx.PolicyNo,
                        branch_id=tx.BranchId or 1,
                        commission_row_id=fc.FranchiseCommId,
                        gross_commission=mapped_fc.gross_commission,
                        tds_amount=mapped_fc.tds_amount,
                        net_commission=mapped_fc.net_commission,
                        already_settled_amount=mapped_fc.paid_amount,
                        remaining_payable_amount=mapped_fc.remaining_payable_amount,
                        payment_status=ps_fc,
                        payment_status_label=payment_status_to_label(ps_fc),
                        is_payout_eligible=eligible,
                        eligibility_reason=reason,
                        trans_date=mapped_fc.franchise_date or tx.TransDate,
                    )
                )

        total_payable = round_2dp(
            sum((item.remaining_payable_amount for item in payable_items), ZERO)
        )
        eligible_payable = round_2dp(
            sum(
                (
                    item.remaining_payable_amount
                    for item in payable_items
                    if item.is_payout_eligible
                ),
                ZERO,
            )
        )
        sliced = payable_items[offset : offset + limit]
        return CommissionPayableListResponse(
            total=len(payable_items),
            limit=limit,
            offset=offset,
            total_payable_amount=total_payable,
            eligible_payable_amount=eligible_payable,
            items=sliced,
        )

    async def approve_policy_commission(
        self,
        transaction_id: int,
        payload: CommissionApprovalRequest,
        current_user: User,
    ) -> PolicyCommissionRecordResponse:
        """
        Approves a policy's unpaid commission payable (`PaymentStatus = 3.00`).
        Rejects approval with 409 Conflict if the policy is not eligible (e.g., pending/bounced cheque
        or unpaid customer premium).
        """
        ctx = self._get_principal(current_user)
        if _normalize(ctx.role_name) not in _APPROVAL_ROLES_NORM:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{ctx.role_name}' is not authorized to approve commission payables.",
            )

        async with _COMMISSION_WRITE_LOCK:
            try:
                tx = await self.repo.get_transaction_by_id(
                    transaction_id, include_deleted=False, for_update=True
                )
                if tx is None:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Policy Transaction #{transaction_id} not found.",
                    )
                acp = await self.repo.get_agent_comm_by_tx(
                    transaction_id, include_deleted=False, for_update=True
                )
                fc = await self.repo.get_franchise_comm_by_tx(
                    transaction_id, include_deleted=False, for_update=True
                )
                cnp = await self.repo.get_cutnpay_by_tx(
                    transaction_id, include_deleted=False, for_update=True
                )

                eligible, reason = self.evaluate_payout_eligibility(tx, acp, cnp)
                if not eligible:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Commission on Policy #{transaction_id} is not eligible for approval: {reason}",
                    )

                ag_rem = round_2dp(_to_decimal(acp.NetAmount)) if acp is not None else ZERO
                frn_rem = (
                    round_2dp(_to_decimal(fc.FranchiseNetComm) - _to_decimal(fc.FCommissionPaid))
                    if fc is not None
                    else ZERO
                )
                if ag_rem <= ZERO and frn_rem <= ZERO:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Commission on Policy #{transaction_id} has 0.00 remaining payable balance.",
                    )

                if payload.partner_type in ("AGENT", "BOTH") and acp is not None and ag_rem > ZERO:
                    acp.PaymentStatus = Decimal("3.00")
                    note = payload.remark or "Approved for Payout"
                    acp.Narration = f"APPROVED: {note} ({tx.InwardNo})"[:255]

                tx.UpdateDate = datetime.utcnow()
                tx.UpdateUser = str(current_user.UserId)
                await self.session.commit()
            except HTTPException:
                await self.session.rollback()
                raise
            except Exception as exc:
                await self.session.rollback()
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to approve commission on Policy #{transaction_id}: {exc}",
                ) from exc

        return await self._build_policy_commission_response(tx)

    # -----------------------------------------------------------------------
    # 4. Atomic Commission Payout & Payout Reversal
    # -----------------------------------------------------------------------

    @staticmethod
    def _encode_payout_extra2(
        voucher_no: str,
        allocations: List[Tuple[int, int, Decimal]],
        idempotency_key: Optional[str] = None,
        bank_reference: Optional[str] = None,
    ) -> str:
        """
        Encodes compact payout metadata into `tbl_account.Extra2` (max 255 chars):
        Format: `VCH-CPAY-{doc_no}|IDEMP:{key}|REF:{ref}|ALLOC:{tx_id}:{row_id}:{amt},...`
        """
        parts = [voucher_no]
        if idempotency_key:
            parts.append(f"IDEMP:{idempotency_key.strip()[:40]}")
        if bank_reference:
            parts.append(f"REF:{bank_reference.strip()[:30]}")
        alloc_str = ",".join(f"{t}:{r}:{round_2dp(a)}" for t, r, a in allocations)
        parts.append(f"ALLOC:{alloc_str}")
        encoded = "|".join(parts)
        return encoded[:255]

    @staticmethod
    def _decode_payout_extra2(
        extra2: Optional[str],
    ) -> Tuple[str, Optional[str], Optional[str], List[Tuple[int, int, Decimal]]]:
        if not extra2:
            return "VCH-CPAY-0", None, None, []
        tokens = extra2.split("|")
        voucher_no = tokens[0] if tokens else "VCH-CPAY-0"
        idemp: Optional[str] = None
        bank_ref: Optional[str] = None
        allocs: List[Tuple[int, int, Decimal]] = []
        for tok in tokens[1:]:
            if tok.startswith("IDEMP:"):
                idemp = tok[len("IDEMP:") :]
            elif tok.startswith("REF:"):
                bank_ref = tok[len("REF:") :]
            elif tok.startswith("ALLOC:"):
                raw_list = tok[len("ALLOC:") :]
                if raw_list:
                    for item in raw_list.split(","):
                        sub = item.split(":")
                        if len(sub) == 3:
                            try:
                                allocs.append(
                                    (int(sub[0]), int(sub[1]), round_2dp(_to_decimal(sub[2])))
                                )
                            except (ValueError, TypeError):
                                continue
        return voucher_no, idemp, bank_ref, allocs

    async def _build_payout_response_from_doc_no(
        self,
        doc_no: int,
    ) -> CommissionPayoutResponse:
        lines = await self.repo.get_account_rows_by_doc_no(
            doc_no, acc_trans_ids=[6], include_deleted=False
        )
        if len(lines) < 2:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Commission Payout #{doc_no} not found.",
            )

        dr_line = next((l for l in lines if _to_decimal(l.amount) > ZERO), lines[0])
        cr_line = next((l for l in lines if _to_decimal(l.amount) < ZERO), lines[-1])

        extra1_str = dr_line.Extra1 or "COMM_PAYOUT_DR:AGENT:0"
        # Format: COMM_PAYOUT_DR:{partner_type}:{partner_id}[|REVERSED_BY:{rev_doc_no}|REASON:{reason}]
        main_seg = extra1_str.split("|")[0]
        seg_parts = main_seg.split(":")
        partner_type: Literal["AGENT", "FRANCHISE"] = (
            "FRANCHISE"
            if len(seg_parts) >= 2 and seg_parts[1] == "FRANCHISE"
            else "AGENT"
        )
        partner_id = (
            int(seg_parts[2])
            if len(seg_parts) >= 3 and seg_parts[2].isdigit()
            else (dr_line.ReferenceAgentId or 0)
        )

        status_val: Literal["PAID", "REVERSED"] = "PAID"
        rev_doc_no: Optional[int] = None
        rev_reason: Optional[str] = None
        for seg in extra1_str.split("|")[1:]:
            if seg.startswith("REVERSED_BY:"):
                status_val = "REVERSED"
                raw_rev = seg[len("REVERSED_BY:") :]
                if raw_rev.isdigit():
                    rev_doc_no = int(raw_rev)
            elif seg.startswith("REASON:"):
                rev_reason = seg[len("REASON:") :]

        voucher_no, idemp_key, bank_ref, raw_allocs = self._decode_payout_extra2(
            dr_line.Extra2
        )

        alloc_responses: List[CommissionPayoutAllocationResponse] = []
        for tx_id, row_id, alloc_amt in raw_allocs:
            tx = await self.repo.get_transaction_by_id(tx_id, include_deleted=True)
            inward_no = tx.InwardNo if tx and tx.InwardNo else f"TX-{tx_id}"
            policy_no = tx.PolicyNo if tx else None
            comm_paid_flag = tx.CommissionPaid if tx and tx.CommissionPaid is not None else 0

            if partner_type == "AGENT":
                acp = await self.repo.get_agent_comm_by_tx(tx_id, include_deleted=True)
                new_paid = round_2dp(_to_decimal(acp.AdvAmt)) if acp else alloc_amt
                rem_amt = round_2dp(_to_decimal(acp.NetAmount)) if acp else ZERO
                p_stat = round_2dp(_to_decimal(acp.PaymentStatus)) if acp else Decimal("1.00")
                prev_paid = max(ZERO, round_2dp(new_paid - alloc_amt))
            else:
                fc = await self.repo.get_franchise_comm_by_tx(tx_id, include_deleted=True)
                new_paid = round_2dp(_to_decimal(fc.FCommissionPaid)) if fc else alloc_amt
                net_c = round_2dp(_to_decimal(fc.FranchiseNetComm)) if fc else alloc_amt
                rem_amt = max(ZERO, round_2dp(net_c - new_paid))
                p_stat = Decimal("1.00") if rem_amt == ZERO else Decimal("2.00")
                prev_paid = max(ZERO, round_2dp(new_paid - alloc_amt))

            alloc_responses.append(
                CommissionPayoutAllocationResponse(
                    transaction_id=tx_id,
                    inward_no=inward_no,
                    policy_no=policy_no,
                    commission_row_id=row_id,
                    allocated_amount=alloc_amt,
                    previous_paid_amount=prev_paid,
                    new_paid_amount=new_paid,
                    remaining_payable_amount=rem_amt,
                    payment_status=p_stat,
                    commission_paid_flag=comm_paid_flag,
                )
            )

        return CommissionPayoutResponse(
            payout_id=doc_no,
            voucher_no=voucher_no,
            partner_type=partner_type,
            partner_id=partner_id,
            branch_id=dr_line.BranchId or 1,
            payment_mode=dr_line.PaymentType or "NEFT",
            total_payout_amount=round_2dp(abs(_to_decimal(dr_line.amount))),
            status=status_val,
            bank_reference=bank_ref,
            narration=dr_line.Narration or "",
            idempotency_key=idemp_key,
            debit_account_id=dr_line.AccountId,
            credit_account_id=cr_line.AccountId,
            debit_ledger_m_id=dr_line.LedgerMId or 0,
            credit_ledger_m_id=cr_line.LedgerMId or 0,
            reversal_doc_no=rev_doc_no,
            reversal_reason=rev_reason,
            created_user=dr_line.CreatedUser,
            created_date=dr_line.CreatedDate,
            allocations=alloc_responses,
        )

    async def create_commission_payout(
        self,
        payload: CommissionPayoutCreateRequest,
        current_user: User,
    ) -> CommissionPayoutResponse:
        """
        Executes an atomic, concurrency-safe Commission Payout (`POST /api/v1/commission-payouts`).
        Serializes under `_COMMISSION_WRITE_LOCK` and InnoDB `SELECT ... FOR UPDATE` (`populate_existing=True`)
        so 100 concurrent payouts against the same payable pool never over-disburse or produce negative payables.
        """
        ctx = self._get_principal(current_user)
        if _normalize(ctx.role_name) not in _PAYOUT_WRITE_NORM:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{ctx.role_name}' is not authorized to disburse commission payouts.",
            )

        eff_branch = payload.branch_id or ctx.branch_id or 1

        async with _COMMISSION_WRITE_LOCK:
            try:
                # 1. Idempotency check inside the lock
                if payload.idempotency_key:
                    marker = f"IDEMP:{payload.idempotency_key.strip()[:40]}"
                    dup_acc = await self.repo.get_account_by_idempotency(
                        marker, acc_trans_ids=[6]
                    )
                    if dup_acc is not None:
                        raise HTTPException(
                            status_code=status.HTTP_409_CONFLICT,
                            detail=(
                                f"Duplicate commission payout request: idempotency_key "
                                f"'{payload.idempotency_key}' already processed as Payout #{dup_acc.Doc_No}."
                            ),
                        )

                # 2. Resolve & Lock Candidate Payable Rows (with populate_existing=True!)
                explicit_map: Dict[int, Optional[Decimal]] = {}
                target_tx_ids: Optional[List[int]] = None

                if payload.allocations:
                    for al in payload.allocations:
                        if al.transaction_id in explicit_map:
                            raise HTTPException(
                                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                detail=f"Duplicate transaction_id #{al.transaction_id} in payout allocations.",
                            )
                        explicit_map[al.transaction_id] = (
                            round_2dp(al.amount) if al.amount is not None else None
                        )
                    target_tx_ids = list(explicit_map.keys())
                elif payload.transaction_ids:
                    target_tx_ids = list(dict.fromkeys(payload.transaction_ids))

                locked_allocations: List[Tuple[Transaction, Optional[AgentCommissionPayment], Optional[FranchiseCommission], Optional[CutNPayCommPayable], Decimal]] = []

                if payload.partner_type == "AGENT":
                    candidate_rows = await self.repo.list_agent_comm_rows_for_partner(
                        agent_id=payload.partner_id,
                        transaction_ids=target_tx_ids,
                        only_unpaid=(target_tx_ids is None),
                        for_update=True,
                    )
                    row_by_tx: Dict[int, AgentCommissionPayment] = {
                        r.TransanctionId: r for r in candidate_rows if r.TransanctionId
                    }
                    if target_tx_ids:
                        for req_tx_id in target_tx_ids:
                            if req_tx_id not in row_by_tx:
                                # Check if policy exists or belongs to another agent
                                check_acp = await self.repo.get_agent_comm_by_tx(
                                    req_tx_id, include_deleted=False, for_update=True
                                )
                                if check_acp is None:
                                    raise HTTPException(
                                        status_code=status.HTTP_404_NOT_FOUND,
                                        detail=f"Agent commission record for Policy #{req_tx_id} not found.",
                                    )
                                if str(check_acp.Extra1 or "0") != str(payload.partner_id):
                                    raise HTTPException(
                                        status_code=status.HTTP_403_FORBIDDEN,
                                        detail=(
                                            f"Policy #{req_tx_id} belongs to Agent #{check_acp.Extra1}, "
                                            f"not requested Agent #{payload.partner_id}."
                                        ),
                                    )
                                row_by_tx[req_tx_id] = check_acp

                    ordered_rows = (
                        [row_by_tx[tid] for tid in target_tx_ids]
                        if target_tx_ids
                        else candidate_rows
                    )
                    if not ordered_rows:
                        raise HTTPException(
                            status_code=status.HTTP_409_CONFLICT,
                            detail=f"No unpaid Agent commission payables found for Agent #{payload.partner_id}.",
                        )

                    remaining_pool_budget = (
                        round_2dp(payload.payout_amount)
                        if payload.payout_amount is not None
                        else None
                    )

                    for acp in ordered_rows:
                        tx_id = acp.TransanctionId or 0
                        tx = await self.repo.get_transaction_by_id(
                            tx_id, include_deleted=False, for_update=True
                        )
                        if tx is None:
                            raise HTTPException(
                                status_code=status.HTTP_404_NOT_FOUND,
                                detail=f"Policy Transaction #{tx_id} not found.",
                            )
                        fc = await self.repo.get_franchise_comm_by_tx(
                            tx_id, include_deleted=False, for_update=True
                        )
                        cnp = await self.repo.get_cutnpay_by_tx(
                            tx_id, include_deleted=False, for_update=True
                        )
                        eligible, reason = self.evaluate_payout_eligibility(tx, acp, cnp)
                        if not eligible:
                            if target_tx_ids is not None:
                                raise HTTPException(
                                    status_code=status.HTTP_409_CONFLICT,
                                    detail=f"Policy #{tx_id} is not eligible for commission payout: {reason}",
                                )
                            continue

                        avail_rem = round_2dp(_to_decimal(acp.NetAmount))
                        if avail_rem <= ZERO:
                            if target_tx_ids is not None and remaining_pool_budget is None:
                                raise HTTPException(
                                    status_code=status.HTTP_409_CONFLICT,
                                    detail=f"Policy #{tx_id} has 0.00 remaining Agent commission payable.",
                                )
                            continue

                        if tx_id in explicit_map and explicit_map[tx_id] is not None:
                            req_amt = explicit_map[tx_id]
                            assert req_amt is not None
                            if req_amt > avail_rem:
                                raise HTTPException(
                                    status_code=status.HTTP_409_CONFLICT,
                                    detail=(
                                        f"Requested payout allocation ({req_amt}) exceeds remaining "
                                        f"Agent commission payable ({avail_rem}) on Policy #{tx_id}."
                                    ),
                                )
                            alloc_amt = req_amt
                        elif remaining_pool_budget is not None:
                            if remaining_pool_budget <= ZERO:
                                break
                            alloc_amt = min(avail_rem, remaining_pool_budget)
                            remaining_pool_budget = round_2dp(remaining_pool_budget - alloc_amt)
                        else:
                            alloc_amt = avail_rem

                        if alloc_amt > ZERO:
                            locked_allocations.append((tx, acp, fc, cnp, alloc_amt))

                    if remaining_pool_budget is not None and remaining_pool_budget > ZERO:
                        raise HTTPException(
                            status_code=status.HTTP_409_CONFLICT,
                            detail=(
                                f"Insufficient eligible Agent commission payable balance for Agent #{payload.partner_id}: "
                                f"shortfall of {remaining_pool_budget} (requested {round_2dp(payload.payout_amount)})."
                            ),
                        )

                else:
                    # FRANCHISE Payout
                    candidate_fcs = await self.repo.list_franchise_comm_rows_for_partner(
                        franchise_id=payload.partner_id,
                        transaction_ids=target_tx_ids,
                        only_unpaid=(target_tx_ids is None),
                        for_update=True,
                    )
                    fc_by_tx: Dict[int, FranchiseCommission] = {
                        r.TransanctionId: r for r in candidate_fcs if r.TransanctionId
                    }
                    if target_tx_ids:
                        for req_tx_id in target_tx_ids:
                            if req_tx_id not in fc_by_tx:
                                check_fc = await self.repo.get_franchise_comm_by_tx(
                                    req_tx_id, include_deleted=False, for_update=True
                                )
                                if check_fc is None:
                                    raise HTTPException(
                                        status_code=status.HTTP_404_NOT_FOUND,
                                        detail=f"Franchise commission record for Policy #{req_tx_id} not found.",
                                    )
                                if (check_fc.FranchiseId or 0) != payload.partner_id:
                                    raise HTTPException(
                                        status_code=status.HTTP_403_FORBIDDEN,
                                        detail=(
                                            f"Policy #{req_tx_id} belongs to Franchise #{check_fc.FranchiseId}, "
                                            f"not requested Franchise #{payload.partner_id}."
                                        ),
                                    )
                                fc_by_tx[req_tx_id] = check_fc

                    ordered_fcs = (
                        [fc_by_tx[tid] for tid in target_tx_ids]
                        if target_tx_ids
                        else candidate_fcs
                    )
                    if not ordered_fcs:
                        raise HTTPException(
                            status_code=status.HTTP_409_CONFLICT,
                            detail=f"No unpaid Franchise commission payables found for Franchise #{payload.partner_id}.",
                        )

                    remaining_pool_budget = (
                        round_2dp(payload.payout_amount)
                        if payload.payout_amount is not None
                        else None
                    )

                    for fc in ordered_fcs:
                        tx_id = fc.TransanctionId or 0
                        tx = await self.repo.get_transaction_by_id(
                            tx_id, include_deleted=False, for_update=True
                        )
                        if tx is None:
                            raise HTTPException(
                                status_code=status.HTTP_404_NOT_FOUND,
                                detail=f"Policy Transaction #{tx_id} not found.",
                            )
                        acp = await self.repo.get_agent_comm_by_tx(
                            tx_id, include_deleted=False, for_update=True
                        )
                        cnp = await self.repo.get_cutnpay_by_tx(
                            tx_id, include_deleted=False, for_update=True
                        )
                        eligible, reason = self.evaluate_payout_eligibility(tx, acp, cnp)
                        if not eligible:
                            if target_tx_ids is not None:
                                raise HTTPException(
                                    status_code=status.HTTP_409_CONFLICT,
                                    detail=f"Policy #{tx_id} is not eligible for Franchise commission payout: {reason}",
                                )
                            continue

                        avail_rem = max(
                            ZERO,
                            round_2dp(
                                _to_decimal(fc.FranchiseNetComm)
                                - _to_decimal(fc.FCommissionPaid)
                            ),
                        )
                        if avail_rem <= ZERO:
                            if target_tx_ids is not None and remaining_pool_budget is None:
                                raise HTTPException(
                                    status_code=status.HTTP_409_CONFLICT,
                                    detail=f"Policy #{tx_id} has 0.00 remaining Franchise commission payable.",
                                )
                            continue

                        if tx_id in explicit_map and explicit_map[tx_id] is not None:
                            req_amt = explicit_map[tx_id]
                            assert req_amt is not None
                            if req_amt > avail_rem:
                                raise HTTPException(
                                    status_code=status.HTTP_409_CONFLICT,
                                    detail=(
                                        f"Requested payout allocation ({req_amt}) exceeds remaining "
                                        f"Franchise commission payable ({avail_rem}) on Policy #{tx_id}."
                                    ),
                                )
                            alloc_amt = req_amt
                        elif remaining_pool_budget is not None:
                            if remaining_pool_budget <= ZERO:
                                break
                            alloc_amt = min(avail_rem, remaining_pool_budget)
                            remaining_pool_budget = round_2dp(remaining_pool_budget - alloc_amt)
                        else:
                            alloc_amt = avail_rem

                        if alloc_amt > ZERO:
                            locked_allocations.append((tx, acp, fc, cnp, alloc_amt))

                    if remaining_pool_budget is not None and remaining_pool_budget > ZERO:
                        raise HTTPException(
                            status_code=status.HTTP_409_CONFLICT,
                            detail=(
                                f"Insufficient eligible Franchise commission payable balance for Franchise #{payload.partner_id}: "
                                f"shortfall of {remaining_pool_budget} (requested {round_2dp(payload.payout_amount)})."
                            ),
                        )

                if not locked_allocations:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"No eligible commission payable balance available for {payload.partner_type} #{payload.partner_id}.",
                    )

                total_payout = round_2dp(
                    sum((item[4] for item in locked_allocations), ZERO)
                )
                if payload.payout_amount is not None and total_payout != round_2dp(payload.payout_amount):
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=(
                            f"Allocated payout sum ({total_payout}) does not match requested "
                            f"payout_amount ({round_2dp(payload.payout_amount)})."
                        ),
                    )

                now_dt = datetime.utcnow()
                compact_allocs: List[Tuple[int, int, Decimal]] = []

                # 3. Apply Commission Row Updates & Policy Settlement Flags
                for tx, acp, fc, cnp, alloc_amt in locked_allocations:
                    if payload.partner_type == "AGENT":
                        assert acp is not None
                        new_adv = round_2dp(_to_decimal(acp.AdvAmt) + alloc_amt)
                        net_c = round_2dp(_to_decimal(acp.NetCommission))
                        new_rem = round_2dp(net_c - new_adv)
                        if new_rem < ZERO:
                            raise HTTPException(
                                status_code=status.HTTP_409_CONFLICT,
                                detail=f"Negative payable invariant violation on Policy #{tx.TransanctionId}.",
                            )
                        acp.AdvAmt = new_adv
                        acp.NetAmount = new_rem
                        acp.PaymentStatus = Decimal("1.00") if new_rem == ZERO else Decimal("2.00")
                        acp.Narration = (
                            payload.narration
                            or f"Commission Payout ({payload.payment_mode}) - {tx.InwardNo}"
                        )[:255]
                        if cnp is not None and new_rem == ZERO:
                            cnp.Flag = "SETTLED"
                        row_id = acp.AgentCommId
                    else:
                        assert fc is not None
                        new_fpaid = round_2dp(_to_decimal(fc.FCommissionPaid) + alloc_amt)
                        fnet = round_2dp(_to_decimal(fc.FranchiseNetComm))
                        if new_fpaid > fnet:
                            raise HTTPException(
                                status_code=status.HTTP_409_CONFLICT,
                                detail=f"Negative Franchise payable invariant violation on Policy #{tx.TransanctionId}.",
                            )
                        fc.FCommissionPaid = new_fpaid
                        row_id = fc.FranchiseCommId

                    # Check if all Agent & Franchise commissions on this policy are now 100% settled
                    ag_rem_now = (
                        round_2dp(_to_decimal(acp.NetAmount))
                        if acp is not None
                        else ZERO
                    )
                    frn_rem_now = (
                        max(
                            ZERO,
                            round_2dp(
                                _to_decimal(fc.FranchiseNetComm)
                                - _to_decimal(fc.FCommissionPaid)
                            ),
                        )
                        if fc is not None
                        else ZERO
                    )
                    tx.CommissionPaid = 1 if (ag_rem_now == ZERO and frn_rem_now == ZERO) else 0
                    tx.UpdateDate = now_dt
                    tx.UpdateUser = str(current_user.UserId)
                    compact_allocs.append((tx.TransanctionId, row_id, alloc_amt))

                await self.session.flush()

                if payload.simulate_failure_at == "AFTER_COMMISSION_UPDATE":
                    raise RuntimeError("Simulated fault AFTER_COMMISSION_UPDATE in create_commission_payout")

                # 4. Allocate Voucher Doc_No & Post Balanced Double-Entry Payout Lines (AccTransId = 6)
                doc_no = await self.repo.allocate_next_doc_no()
                voucher_no = f"VCH-CPAY-{doc_no}"
                extra2_str = self._encode_payout_extra2(
                    voucher_no=voucher_no,
                    allocations=compact_allocs,
                    idempotency_key=payload.idempotency_key,
                    bank_reference=payload.bank_reference,
                )

                payable_ledger = await self.repo.resolve_or_create_system_ledger(
                    ledger_name=f"COMMISSION PAYABLE - {payload.partner_type} #{payload.partner_id}",
                    ledger_type_id=2,
                    ledger_group_id=20,
                    reference_id=payload.partner_id,
                    branch_id=eff_branch,
                    actor_user_id=current_user.UserId,
                    for_update=True,
                )
                settlement_ledger = await self.repo.resolve_or_create_system_ledger(
                    ledger_name=f"BANK / PAYOUT SETTLEMENT ({payload.payment_mode}) - BRANCH #{eff_branch}",
                    ledger_type_id=1,
                    ledger_group_id=10,
                    reference_id=0,
                    branch_id=eff_branch,
                    actor_user_id=current_user.UserId,
                    for_update=True,
                )

                first_tx = locked_allocations[0][0]
                primary_tx_id = first_tx.TransanctionId if len(locked_allocations) == 1 else 0
                narr = (
                    payload.narration
                    or f"Commission Payout {voucher_no} to {payload.partner_type} #{payload.partner_id}"
                )[:500]

                dr_entry = Account(
                    AccTransId=6,
                    AccountDate=now_dt,
                    LedgerMId=payable_ledger.LedgerMId,
                    amount=total_payout,
                    Narration=narr,
                    ReferenceCustId=first_tx.CustomerId or 0,
                    ReferenceAgentId=payload.partner_id,
                    BranchId=eff_branch,
                    Extra1=f"COMM_PAYOUT_DR:{payload.partner_type}:{payload.partner_id}",
                    Extra2=extra2_str,
                    Doc_No=doc_no,
                    CreatedUser=str(current_user.UserId),
                    CreatedDate=now_dt,
                    UpdatedUser=str(current_user.UserId),
                    UpdatedDate=now_dt,
                    PaymentType=payload.payment_mode,
                    isdeleted=0,
                    IsNill=0,
                    TransactionId=primary_tx_id,
                    CustVehId=first_tx.CustVehId or 0,
                    MonthId=now_dt.month,
                    EndorsementId=0,
                    TransId=first_tx.TransId or 0,
                )
                cr_entry = Account(
                    AccTransId=6,
                    AccountDate=now_dt,
                    LedgerMId=settlement_ledger.LedgerMId,
                    amount=-total_payout,
                    Narration=narr,
                    ReferenceCustId=first_tx.CustomerId or 0,
                    ReferenceAgentId=payload.partner_id,
                    BranchId=eff_branch,
                    Extra1=f"COMM_PAYOUT_CR:{payload.partner_type}:{payload.partner_id}",
                    Extra2=extra2_str,
                    Doc_No=doc_no,
                    CreatedUser=str(current_user.UserId),
                    CreatedDate=now_dt,
                    UpdatedUser=str(current_user.UserId),
                    UpdatedDate=now_dt,
                    PaymentType=payload.payment_mode,
                    isdeleted=0,
                    IsNill=0,
                    TransactionId=primary_tx_id,
                    CustVehId=first_tx.CustVehId or 0,
                    MonthId=now_dt.month,
                    EndorsementId=0,
                    TransId=first_tx.TransId or 0,
                )
                await self.repo.create_account_entry(dr_entry)
                await self.repo.create_account_entry(cr_entry)

                if payload.simulate_failure_at == "BEFORE_COMMIT":
                    raise RuntimeError("Simulated fault BEFORE_COMMIT in create_commission_payout")

                await self.session.commit()
            except HTTPException:
                await self.session.rollback()
                raise
            except Exception as exc:
                await self.session.rollback()
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Atomic commission payout rolled back: {exc}",
                ) from exc

        return await self._build_payout_response_from_doc_no(doc_no)

    async def get_commission_payout(
        self,
        payout_id: int,
        current_user: User,
    ) -> CommissionPayoutResponse:
        resp = await self._build_payout_response_from_doc_no(payout_id)
        ctx = self._get_principal(current_user)
        norm_role = _normalize(ctx.role_name)
        if not self._is_cross_branch_role(ctx.role_name):
            if norm_role in _AGENT_ROLES_NORM:
                bound_agent = ctx.agent_id or ctx.user_id
                if resp.partner_type != "AGENT" or resp.partner_id != bound_agent:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Access denied: Agent principal can only access its own commission payouts.",
                    )
            elif norm_role in _FRANCHISE_ROLES_NORM:
                bound_frn = ctx.franchise_id or ctx.user_id
                if resp.partner_type != "FRANCHISE" or resp.partner_id != bound_frn:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Access denied: Franchise principal can only access its own commission payouts.",
                    )
            elif ctx.branch_id is not None and resp.branch_id != ctx.branch_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: Commission Payout belongs to another branch.",
                )
        return resp

    async def list_commission_payouts(
        self,
        current_user: User,
        *,
        partner_type: Optional[Literal["AGENT", "FRANCHISE"]] = None,
        partner_id: Optional[int] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> CommissionPayoutListResponse:
        ctx = self._get_principal(current_user)
        norm_role = _normalize(ctx.role_name)

        branch_filter: Optional[int] = None
        eff_type = partner_type
        eff_partner_id = partner_id

        if not self._is_cross_branch_role(ctx.role_name):
            branch_filter = ctx.branch_id or 1
            if norm_role in _AGENT_ROLES_NORM:
                eff_type = "AGENT"
                eff_partner_id = ctx.agent_id or ctx.user_id
            elif norm_role in _FRANCHISE_ROLES_NORM:
                eff_type = "FRANCHISE"
                eff_partner_id = ctx.franchise_id or ctx.user_id

        extra1_pref: Optional[str] = None
        if eff_type:
            extra1_pref = f"COMM_PAYOUT_DR:{eff_type}:"

        total, doc_nos = await self.repo.list_distinct_voucher_doc_nos(
            acc_trans_ids=[6],
            branch_id=branch_filter,
            reference_agent_id=eff_partner_id,
            extra1_prefix=extra1_pref,
            limit=limit,
            offset=offset,
        )
        items = [await self._build_payout_response_from_doc_no(d) for d in doc_nos]
        return CommissionPayoutListResponse(
            total=total,
            limit=limit,
            offset=offset,
            items=items,
        )

    async def reverse_commission_payout(
        self,
        payout_id: int,
        payload: CommissionPayoutReverseRequest,
        current_user: User,
    ) -> CommissionPayoutResponse:
        """
        Atomically reverses a Commission Payout (`POST /api/v1/commission-payouts/{payout_id}/reverse`):
        1. Locks original payout lines (`Doc_No = payout_id`, `AccTransId = 6`) with `FOR UPDATE`.
        2. Rejects duplicate reversal (`409 Conflict`).
        3. Restores `AdvAmt`, `NetAmount`, `PaymentStatus`, `FCommissionPaid`, `tx.CommissionPaid = 0`,
           and `cnp.Flag = 'CUTNPAY'`.
        4. Posts contra double-entry reversal lines (`AccTransId = 7`) in `tbl_account`.
        """
        ctx = self._get_principal(current_user)
        if _normalize(ctx.role_name) not in _PAYOUT_WRITE_NORM:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{ctx.role_name}' is not authorized to reverse commission payouts.",
            )

        async with _COMMISSION_WRITE_LOCK:
            try:
                orig_lines = await self.repo.get_account_rows_by_doc_no(
                    payout_id, acc_trans_ids=[6], include_deleted=False, for_update=True
                )
                if len(orig_lines) < 2:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Commission Payout #{payout_id} not found.",
                    )

                dr_line = next((l for l in orig_lines if _to_decimal(l.amount) > ZERO), orig_lines[0])
                cr_line = next((l for l in orig_lines if _to_decimal(l.amount) < ZERO), orig_lines[-1])

                if "REVERSED_BY:" in (dr_line.Extra1 or ""):
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Commission Payout #{payout_id} has already been reversed.",
                    )

                main_seg = (dr_line.Extra1 or "COMM_PAYOUT_DR:AGENT:0").split("|")[0]
                seg_parts = main_seg.split(":")
                partner_type: Literal["AGENT", "FRANCHISE"] = (
                    "FRANCHISE"
                    if len(seg_parts) >= 2 and seg_parts[1] == "FRANCHISE"
                    else "AGENT"
                )
                partner_id = (
                    int(seg_parts[2])
                    if len(seg_parts) >= 3 and seg_parts[2].isdigit()
                    else (dr_line.ReferenceAgentId or 0)
                )

                _, _, _, raw_allocs = self._decode_payout_extra2(dr_line.Extra2)
                now_dt = datetime.utcnow()

                # Restore each policy's commission payable balance
                for tx_id, _, alloc_amt in raw_allocs:
                    tx = await self.repo.get_transaction_by_id(
                        tx_id, include_deleted=True, for_update=True
                    )
                    cnp = await self.repo.get_cutnpay_by_tx(
                        tx_id, include_deleted=True, for_update=True
                    )
                    if partner_type == "AGENT":
                        acp = await self.repo.get_agent_comm_by_tx(
                            tx_id, include_deleted=True, for_update=True
                        )
                        if acp is not None:
                            new_adv = max(ZERO, round_2dp(_to_decimal(acp.AdvAmt) - alloc_amt))
                            net_c = round_2dp(_to_decimal(acp.NetCommission))
                            new_rem = round_2dp(net_c - new_adv)
                            acp.AdvAmt = new_adv
                            acp.NetAmount = new_rem
                            if new_adv > ZERO and new_rem > ZERO:
                                acp.PaymentStatus = Decimal("2.00")
                            elif new_adv == ZERO:
                                acp.PaymentStatus = Decimal("0.00")
                            else:
                                acp.PaymentStatus = Decimal("1.00")
                            acp.Narration = f"REVERSED PAYOUT #{payout_id}: {payload.reason}"[:255]
                            if cnp is not None and (cnp.Flag or "") == "SETTLED" and new_rem > ZERO:
                                cnp.Flag = "CUTNPAY"
                    else:
                        fc = await self.repo.get_franchise_comm_by_tx(
                            tx_id, include_deleted=True, for_update=True
                        )
                        if fc is not None:
                            fc.FCommissionPaid = max(
                                ZERO, round_2dp(_to_decimal(fc.FCommissionPaid) - alloc_amt)
                            )

                    if tx is not None:
                        tx.CommissionPaid = 0
                        tx.UpdateDate = now_dt
                        tx.UpdateUser = str(current_user.UserId)

                await self.session.flush()

                if payload.simulate_failure_at == "AFTER_BALANCE_RESTORE":
                    raise RuntimeError("Simulated fault AFTER_BALANCE_RESTORE in reverse_commission_payout")

                rev_doc_no = await self.repo.allocate_next_doc_no()
                rev_voucher_no = f"VCH-CREV-{rev_doc_no}"
                total_amt = round_2dp(abs(_to_decimal(dr_line.amount)))
                clean_reason = payload.reason.strip().replace("|", "/")[:80]

                # Mark original lines as reversed
                for orig in orig_lines:
                    orig.Extra1 = f"{orig.Extra1}|REVERSED_BY:{rev_doc_no}|REASON:{clean_reason}"[:255]
                    orig.UpdatedDate = now_dt
                    orig.UpdatedUser = str(current_user.UserId)

                rev_narr = f"Reversal of Commission Payout #{payout_id}: {payload.reason}"[:500]

                # Contra line 1: Credit Commission Payable (-total_amt)
                contra_payable = Account(
                    AccTransId=7,
                    AccountDate=now_dt,
                    LedgerMId=dr_line.LedgerMId,
                    amount=-total_amt,
                    Narration=rev_narr,
                    ReferenceCustId=dr_line.ReferenceCustId or 0,
                    ReferenceAgentId=partner_id,
                    BranchId=dr_line.BranchId or 1,
                    Extra1=f"COMM_PAYOUT_REV_CR:{partner_type}:{partner_id}|ORIG:{payout_id}",
                    Extra2=rev_voucher_no,
                    Doc_No=rev_doc_no,
                    CreatedUser=str(current_user.UserId),
                    CreatedDate=now_dt,
                    UpdatedUser=str(current_user.UserId),
                    UpdatedDate=now_dt,
                    PaymentType=dr_line.PaymentType or "NEFT",
                    isdeleted=0,
                    IsNill=0,
                    TransactionId=dr_line.TransactionId or 0,
                    CustVehId=dr_line.CustVehId or 0,
                    MonthId=now_dt.month,
                    EndorsementId=0,
                    TransId=dr_line.TransId or 0,
                )
                # Contra line 2: Debit Bank / Settlement (+total_amt)
                contra_bank = Account(
                    AccTransId=7,
                    AccountDate=now_dt,
                    LedgerMId=cr_line.LedgerMId,
                    amount=total_amt,
                    Narration=rev_narr,
                    ReferenceCustId=cr_line.ReferenceCustId or 0,
                    ReferenceAgentId=partner_id,
                    BranchId=cr_line.BranchId or 1,
                    Extra1=f"COMM_PAYOUT_REV_DR:{partner_type}:{partner_id}|ORIG:{payout_id}",
                    Extra2=rev_voucher_no,
                    Doc_No=rev_doc_no,
                    CreatedUser=str(current_user.UserId),
                    CreatedDate=now_dt,
                    UpdatedUser=str(current_user.UserId),
                    UpdatedDate=now_dt,
                    PaymentType=cr_line.PaymentType or "NEFT",
                    isdeleted=0,
                    IsNill=0,
                    TransactionId=cr_line.TransactionId or 0,
                    CustVehId=cr_line.CustVehId or 0,
                    MonthId=now_dt.month,
                    EndorsementId=0,
                    TransId=cr_line.TransId or 0,
                )
                await self.repo.create_account_entry(contra_payable)
                await self.repo.create_account_entry(contra_bank)

                if payload.simulate_failure_at == "BEFORE_COMMIT":
                    raise RuntimeError("Simulated fault BEFORE_COMMIT in reverse_commission_payout")

                await self.session.commit()
            except HTTPException:
                await self.session.rollback()
                raise
            except Exception as exc:
                await self.session.rollback()
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Atomic commission payout reversal rolled back: {exc}",
                ) from exc

        return await self._build_payout_response_from_doc_no(payout_id)

    # -----------------------------------------------------------------------
    # 5. Master Ledgers (`tbl_ledgermaster`) & Running-Balance Statements
    # -----------------------------------------------------------------------

    async def _build_ledger_response(
        self,
        row: LedgerMaster,
        include_balances: bool = True,
    ) -> LedgerMasterResponse:
        tot_dr = ZERO
        tot_cr = ZERO
        closing = ZERO
        polarity: Literal["DR", "CR", "ZERO"] = "ZERO"

        if include_balances:
            entries = await self.repo.list_ledger_entries(row.LedgerMId, include_deleted=False)
            for e in entries:
                amt = round_2dp(_to_decimal(e.amount))
                if amt > ZERO:
                    tot_dr = round_2dp(tot_dr + amt)
                elif amt < ZERO:
                    tot_cr = round_2dp(tot_cr + abs(amt))
            closing = round_2dp(tot_dr - tot_cr)
            if closing > ZERO:
                polarity = "DR"
            elif closing < ZERO:
                polarity = "CR"

        ltype = row.LedgerTypeId or 1
        return LedgerMasterResponse(
            ledger_m_id=row.LedgerMId,
            ledger_name=row.LedgerName or f"Ledger #{row.LedgerMId}",
            ledger_type_id=ltype,
            ledger_type_label=LEDGER_TYPE_LABELS.get(ltype, "ASSET"),
            ledger_group_id=row.LedgerGroupId or 10,
            reference_id=row.ReferenceId or 0,
            branch_id=row.BranchId or 1,
            isdeleted=row.isdeleted or "0",
            total_debit=tot_dr,
            total_credit=tot_cr,
            closing_balance=closing,
            closing_polarity=polarity,
            create_date=row.CreateDate,
        )

    async def create_ledger(
        self,
        payload: LedgerMasterCreateRequest,
        current_user: User,
    ) -> LedgerMasterResponse:
        ctx = self._get_principal(current_user)
        if _normalize(ctx.role_name) not in _VOUCHER_WRITE_NORM:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{ctx.role_name}' is not authorized to create master ledgers.",
            )
        eff_branch = payload.branch_id or ctx.branch_id or 1

        async with _COMMISSION_WRITE_LOCK:
            try:
                dup = await self.repo.get_ledger_by_name_and_branch(
                    ledger_name=payload.ledger_name,
                    branch_id=eff_branch,
                    for_update=True,
                )
                if dup is not None:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=(
                            f"Master Ledger '{payload.ledger_name}' already exists in Branch #{eff_branch} "
                            f"(LedgerMId #{dup.LedgerMId})."
                        ),
                    )
                now_dt = datetime.utcnow()
                row = LedgerMaster(
                    LedgerTypeId=payload.ledger_type_id,
                    LedgerName=payload.ledger_name.strip(),
                    LedgerGroupId=payload.ledger_group_id,
                    ReferenceId=payload.reference_id,
                    BranchId=eff_branch,
                    isdeleted="0",
                    CreateUser=str(current_user.UserId),
                    CreateDate=now_dt,
                    UpdateUser=str(current_user.UserId),
                    UpdateDate=now_dt,
                )
                await self.repo.create_ledger(row)
                await self.session.commit()
            except HTTPException:
                await self.session.rollback()
                raise
            except Exception as exc:
                await self.session.rollback()
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to create master ledger: {exc}",
                ) from exc

        return await self._build_ledger_response(row, include_balances=False)

    async def list_ledgers(
        self,
        current_user: User,
        *,
        branch_id: Optional[int] = None,
        ledger_type_id: Optional[int] = None,
        ledger_group_id: Optional[int] = None,
        reference_id: Optional[int] = None,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> LedgerMasterListResponse:
        ctx = self._get_principal(current_user)
        norm_role = _normalize(ctx.role_name)

        eff_branch = branch_id
        eff_ref = reference_id
        if not self._is_cross_branch_role(ctx.role_name):
            eff_branch = ctx.branch_id or 1
            if norm_role in _AGENT_ROLES_NORM:
                eff_ref = ctx.agent_id or ctx.user_id
            elif norm_role in _FRANCHISE_ROLES_NORM:
                eff_ref = ctx.franchise_id or ctx.user_id

        total, rows = await self.repo.list_ledgers(
            branch_id=eff_branch,
            ledger_type_id=ledger_type_id,
            ledger_group_id=ledger_group_id,
            reference_id=eff_ref,
            search=search,
            include_deleted=False,
            limit=limit,
            offset=offset,
        )
        items = [await self._build_ledger_response(r, include_balances=True) for r in rows]
        return LedgerMasterListResponse(
            total=total,
            limit=limit,
            offset=offset,
            items=items,
        )

    async def get_ledger_statement(
        self,
        ledger_m_id: int,
        current_user: User,
        *,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
    ) -> LedgerStatementResponse:
        ledger = await self.repo.get_ledger_by_id(ledger_m_id, include_deleted=False)
        if ledger is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Master Ledger #{ledger_m_id} not found.",
            )

        ctx = self._get_principal(current_user)
        norm_role = _normalize(ctx.role_name)
        if not self._is_cross_branch_role(ctx.role_name):
            if norm_role in _AGENT_ROLES_NORM:
                bound_agent = ctx.agent_id or ctx.user_id
                if (ledger.ReferenceId or 0) != bound_agent:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Access denied: Agent principal can only view its own sub-ledgers.",
                    )
            elif norm_role in _FRANCHISE_ROLES_NORM:
                bound_frn = ctx.franchise_id or ctx.user_id
                if (ledger.ReferenceId or 0) != bound_frn:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Access denied: Franchise principal can only view its own sub-ledgers.",
                    )
            elif ctx.branch_id is not None and (ledger.BranchId or 1) != ctx.branch_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: Master Ledger belongs to another branch.",
                )

        rows = await self.repo.list_ledger_entries(
            ledger_m_id,
            from_date=from_date,
            to_date=to_date,
            include_deleted=False,
        )

        running = ZERO
        tot_dr = ZERO
        tot_cr = ZERO
        stmt_items: List[LedgerStatementEntryResponse] = []

        for r in rows:
            signed = round_2dp(_to_decimal(r.amount))
            dr = signed if signed > ZERO else ZERO
            cr = abs(signed) if signed < ZERO else ZERO
            tot_dr = round_2dp(tot_dr + dr)
            tot_cr = round_2dp(tot_cr + cr)
            running = round_2dp(running + signed)
            if running > ZERO:
                pol: Literal["DR", "CR", "ZERO"] = "DR"
            elif running < ZERO:
                pol = "CR"
            else:
                pol = "ZERO"

            vch_no: Optional[str] = None
            if r.Extra2 and str(r.Extra2).startswith("VCH-"):
                vch_no = str(r.Extra2).split("|")[0]
            elif r.Doc_No:
                vch_no = f"DOC-{r.Doc_No}"

            stmt_items.append(
                LedgerStatementEntryResponse(
                    account_id=r.AccountId,
                    acc_trans_id=r.AccTransId or 0,
                    account_date=r.AccountDate,
                    doc_no=r.Doc_No,
                    voucher_no=vch_no,
                    entry_type=(r.Extra1 or "LEDGER_ENTRY").split("|")[0],
                    narration=r.Narration or "",
                    payment_type=r.PaymentType,
                    transaction_id=r.TransactionId or 0,
                    reference_cust_id=r.ReferenceCustId,
                    reference_agent_id=r.ReferenceAgentId,
                    branch_id=r.BranchId or 1,
                    signed_amount=signed,
                    debit_amount=dr,
                    credit_amount=cr,
                    running_balance=running,
                    running_polarity=pol,
                )
            )

        closing_pol: Literal["DR", "CR", "ZERO"] = (
            "DR" if running > ZERO else ("CR" if running < ZERO else "ZERO")
        )
        ledger_resp = await self._build_ledger_response(ledger, include_balances=False)
        ledger_resp.total_debit = tot_dr
        ledger_resp.total_credit = tot_cr
        ledger_resp.closing_balance = running
        ledger_resp.closing_polarity = closing_pol

        return LedgerStatementResponse(
            ledger=ledger_resp,
            opening_balance=ZERO,
            total_debit=tot_dr,
            total_credit=tot_cr,
            closing_balance=running,
            closing_polarity=closing_pol,
            total_entries=len(stmt_items),
            items=stmt_items,
        )

    # -----------------------------------------------------------------------
    # 6. Double-Entry Vouchers (`AccTransId = 8, 9`) & Reversal
    # -----------------------------------------------------------------------

    async def _build_voucher_response_from_doc_no(
        self,
        doc_no: int,
    ) -> VoucherResponse:
        lines = await self.repo.get_account_rows_by_doc_no(
            doc_no, acc_trans_ids=[6, 7, 8, 9], include_deleted=False
        )
        if not lines:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Accounting Voucher #{doc_no} not found.",
            )

        first = lines[0]
        extra1_raw = first.Extra1 or "VOUCHER_JOURNAL_DR"
        status_val: Literal["POSTED", "REVERSED"] = "POSTED"
        rev_doc_no: Optional[int] = None
        for seg in extra1_raw.split("|")[1:]:
            if seg.startswith("REVERSED_BY:"):
                status_val = "REVERSED"
                r_str = seg[len("REVERSED_BY:") :]
                if r_str.isdigit():
                    rev_doc_no = int(r_str)

        head_seg = extra1_raw.split("|")[0]
        if head_seg.startswith("COMM_PAYOUT_REV"):
            v_type = "COMMISSION_PAYOUT_REVERSAL"
        elif head_seg.startswith("COMM_PAYOUT"):
            v_type = "COMMISSION_PAYOUT"
        elif head_seg.startswith("VOUCHER_REV_"):
            v_type = "VOUCHER_REVERSAL"
        elif head_seg.startswith("VOUCHER_"):
            parts = head_seg.split("_")
            v_type = parts[1] if len(parts) >= 2 else "JOURNAL"
        else:
            v_type = "JOURNAL"

        voucher_no = (
            str(first.Extra2).split("|")[0]
            if (first.Extra2 and str(first.Extra2).startswith("VCH-"))
            else f"VCH-{doc_no}"
        )

        tot_dr = ZERO
        tot_cr = ZERO
        line_items: List[VoucherLineResponse] = []

        for l in lines:
            signed = round_2dp(_to_decimal(l.amount))
            dr_cr: Literal["DR", "CR"] = "DR" if signed >= ZERO else "CR"
            abs_amt = abs(signed)
            if dr_cr == "DR":
                tot_dr = round_2dp(tot_dr + abs_amt)
            else:
                tot_cr = round_2dp(tot_cr + abs_amt)

            ledger_obj = (
                await self.repo.get_ledger_by_id(l.LedgerMId, include_deleted=True)
                if l.LedgerMId
                else None
            )
            line_items.append(
                VoucherLineResponse(
                    account_id=l.AccountId,
                    acc_trans_id=l.AccTransId or 8,
                    ledger_m_id=l.LedgerMId or 0,
                    ledger_name=ledger_obj.LedgerName if ledger_obj else None,
                    dr_cr=dr_cr,
                    amount=abs_amt,
                    signed_amount=signed,
                    narration=l.Narration or "",
                    reference_cust_id=l.ReferenceCustId,
                    reference_agent_id=l.ReferenceAgentId,
                    transaction_id=l.TransactionId or 0,
                )
            )

        return VoucherResponse(
            doc_no=doc_no,
            voucher_no=voucher_no,
            voucher_type=v_type,
            voucher_date=first.AccountDate or datetime.utcnow(),
            branch_id=first.BranchId or 1,
            payment_mode=first.PaymentType or "JOURNAL",
            narration=first.Narration or "",
            total_debit=tot_dr,
            total_credit=tot_cr,
            is_balanced=(tot_dr == tot_cr),
            status=status_val,
            reversal_doc_no=rev_doc_no,
            created_user=first.CreatedUser,
            created_date=first.CreatedDate,
            lines=line_items,
        )

    async def create_voucher(
        self,
        payload: VoucherCreateRequest,
        current_user: User,
    ) -> VoucherResponse:
        """
        Creates a balanced Double-Entry Accounting Voucher (`POST /api/v1/accounting/vouchers`).
        Enforces $\sum \text{DR} == \sum \text{CR}$ (`422 Unprocessable Entity` if unbalanced).
        """
        ctx = self._get_principal(current_user)
        if _normalize(ctx.role_name) not in _VOUCHER_WRITE_NORM:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{ctx.role_name}' is not authorized to post accounting vouchers.",
            )

        tot_dr = round_2dp(
            sum((round_2dp(l.amount) for l in payload.lines if l.dr_cr == "DR"), ZERO)
        )
        tot_cr = round_2dp(
            sum((round_2dp(l.amount) for l in payload.lines if l.dr_cr == "CR"), ZERO)
        )
        if tot_dr <= ZERO or tot_cr <= ZERO or tot_dr != tot_cr:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"Unbalanced voucher rejected: total_debit ({tot_dr}) must equal "
                    f"total_credit ({tot_cr}) and both must be > 0.00."
                ),
            )

        eff_branch = payload.branch_id or ctx.branch_id or 1

        async with _COMMISSION_WRITE_LOCK:
            try:
                if payload.idempotency_key:
                    marker = f"IDEMP:{payload.idempotency_key.strip()[:40]}"
                    dup = await self.repo.get_account_by_idempotency(
                        marker, acc_trans_ids=[8]
                    )
                    if dup is not None:
                        raise HTTPException(
                            status_code=status.HTTP_409_CONFLICT,
                            detail=(
                                f"Duplicate voucher request: idempotency_key '{payload.idempotency_key}' "
                                f"already posted as Voucher #{dup.Doc_No}."
                            ),
                        )

                # Verify all referenced ledgers exist
                for line in payload.lines:
                    ledger = await self.repo.get_ledger_by_id(
                        line.ledger_m_id, include_deleted=False, for_update=True
                    )
                    if ledger is None:
                        raise HTTPException(
                            status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Master Ledger #{line.ledger_m_id} not found.",
                        )

                doc_no = await self.repo.allocate_next_doc_no()
                v_prefix = payload.voucher_type[:3].upper()
                voucher_no = f"VCH-{v_prefix}-{doc_no}"
                extra2_str = (
                    f"{voucher_no}|IDEMP:{payload.idempotency_key.strip()[:40]}"
                    if payload.idempotency_key
                    else voucher_no
                )

                now_dt = datetime.utcnow()
                v_dt = (
                    datetime.combine(payload.voucher_date, datetime.min.time())
                    if payload.voucher_date
                    else now_dt
                )

                for idx, line in enumerate(payload.lines):
                    amt = round_2dp(line.amount)
                    signed_amt = amt if line.dr_cr == "DR" else -amt
                    acc_row = Account(
                        AccTransId=8,
                        AccountDate=v_dt,
                        LedgerMId=line.ledger_m_id,
                        amount=signed_amt,
                        Narration=(line.narration or payload.narration)[:500],
                        ReferenceCustId=line.reference_cust_id or 0,
                        ReferenceAgentId=line.reference_agent_id or 0,
                        BranchId=eff_branch,
                        Extra1=f"VOUCHER_{payload.voucher_type}_{line.dr_cr}",
                        Extra2=extra2_str,
                        Doc_No=doc_no,
                        CreatedUser=str(current_user.UserId),
                        CreatedDate=now_dt,
                        UpdatedUser=str(current_user.UserId),
                        UpdatedDate=now_dt,
                        PaymentType=payload.payment_mode.strip().upper(),
                        isdeleted=0,
                        IsNill=0,
                        TransactionId=line.transaction_id or 0,
                        CustVehId=0,
                        MonthId=v_dt.month,
                        EndorsementId=0,
                        TransId=0,
                    )
                    await self.repo.create_account_entry(acc_row)

                    if idx == 0 and payload.simulate_failure_at == "AFTER_FIRST_LINE":
                        raise RuntimeError("Simulated fault AFTER_FIRST_LINE in create_voucher")

                if payload.simulate_failure_at == "BEFORE_COMMIT":
                    raise RuntimeError("Simulated fault BEFORE_COMMIT in create_voucher")

                await self.session.commit()
            except HTTPException:
                await self.session.rollback()
                raise
            except Exception as exc:
                await self.session.rollback()
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Atomic voucher creation rolled back: {exc}",
                ) from exc

        return await self._build_voucher_response_from_doc_no(doc_no)

    async def get_voucher(
        self,
        doc_no: int,
        current_user: User,
    ) -> VoucherResponse:
        resp = await self._build_voucher_response_from_doc_no(doc_no)
        ctx = self._get_principal(current_user)
        if not self._is_cross_branch_role(ctx.role_name):
            if ctx.branch_id is not None and resp.branch_id != ctx.branch_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: Voucher belongs to another branch.",
                )
        return resp

    async def list_vouchers(
        self,
        current_user: User,
        *,
        branch_id: Optional[int] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> VoucherListResponse:
        ctx = self._get_principal(current_user)
        eff_branch = branch_id
        if not self._is_cross_branch_role(ctx.role_name):
            eff_branch = ctx.branch_id or 1

        total, doc_nos = await self.repo.list_distinct_voucher_doc_nos(
            acc_trans_ids=[6, 7, 8, 9],
            branch_id=eff_branch,
            limit=limit,
            offset=offset,
        )
        items = [await self._build_voucher_response_from_doc_no(d) for d in doc_nos]
        return VoucherListResponse(
            total=total,
            limit=limit,
            offset=offset,
            items=items,
        )

    async def reverse_voucher(
        self,
        doc_no: int,
        payload: VoucherReverseRequest,
        current_user: User,
    ) -> VoucherResponse:
        """
        Atomically reverses a Double-Entry Accounting Voucher (`POST /api/v1/accounting/vouchers/{doc_no}/reverse`).
        Posts mirror contra lines (`AccTransId = 9`) and marks the original voucher `REVERSED`.
        """
        ctx = self._get_principal(current_user)
        if _normalize(ctx.role_name) not in _VOUCHER_WRITE_NORM:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{ctx.role_name}' is not authorized to reverse accounting vouchers.",
            )

        async with _COMMISSION_WRITE_LOCK:
            try:
                orig_lines = await self.repo.get_account_rows_by_doc_no(
                    doc_no, acc_trans_ids=[8], include_deleted=False, for_update=True
                )
                if not orig_lines:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Accounting Voucher #{doc_no} not found.",
                    )

                if "REVERSED_BY:" in (orig_lines[0].Extra1 or ""):
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Accounting Voucher #{doc_no} has already been reversed.",
                    )

                rev_doc_no = await self.repo.allocate_next_doc_no()
                rev_voucher_no = f"VCH-REV-{rev_doc_no}"
                now_dt = datetime.utcnow()
                clean_reason = payload.reason.strip().replace("|", "/")[:80]

                for orig in orig_lines:
                    orig.Extra1 = f"{orig.Extra1}|REVERSED_BY:{rev_doc_no}|REASON:{clean_reason}"[:255]
                    orig.UpdatedDate = now_dt
                    orig.UpdatedUser = str(current_user.UserId)

                for idx, orig in enumerate(orig_lines):
                    orig_signed = round_2dp(_to_decimal(orig.amount))
                    contra_signed = -orig_signed
                    dr_cr = "DR" if contra_signed >= ZERO else "CR"
                    contra_row = Account(
                        AccTransId=9,
                        AccountDate=now_dt,
                        LedgerMId=orig.LedgerMId,
                        amount=contra_signed,
                        Narration=f"Reversal of Voucher #{doc_no}: {payload.reason}"[:500],
                        ReferenceCustId=orig.ReferenceCustId or 0,
                        ReferenceAgentId=orig.ReferenceAgentId or 0,
                        BranchId=orig.BranchId or 1,
                        Extra1=f"VOUCHER_REV_{dr_cr}|ORIG:{doc_no}",
                        Extra2=rev_voucher_no,
                        Doc_No=rev_doc_no,
                        CreatedUser=str(current_user.UserId),
                        CreatedDate=now_dt,
                        UpdatedUser=str(current_user.UserId),
                        UpdatedDate=now_dt,
                        PaymentType=orig.PaymentType or "JOURNAL",
                        isdeleted=0,
                        IsNill=0,
                        TransactionId=orig.TransactionId or 0,
                        CustVehId=orig.CustVehId or 0,
                        MonthId=now_dt.month,
                        EndorsementId=0,
                        TransId=orig.TransId or 0,
                    )
                    await self.repo.create_account_entry(contra_row)

                    if idx == 0 and payload.simulate_failure_at == "AFTER_FIRST_CONTRA":
                        raise RuntimeError("Simulated fault AFTER_FIRST_CONTRA in reverse_voucher")

                if payload.simulate_failure_at == "BEFORE_COMMIT":
                    raise RuntimeError("Simulated fault BEFORE_COMMIT in reverse_voucher")

                await self.session.commit()
            except HTTPException:
                await self.session.rollback()
                raise
            except Exception as exc:
                await self.session.rollback()
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Atomic voucher reversal rolled back: {exc}",
                ) from exc

        return await self._build_voucher_response_from_doc_no(doc_no)

    # -----------------------------------------------------------------------
    # 7. Trial Balance Engine (`GET /api/v1/accounting/trial-balance`)
    # -----------------------------------------------------------------------

    async def get_trial_balance(
        self,
        current_user: User,
        *,
        branch_id: Optional[int] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
    ) -> TrialBalanceResponse:
        """
        Generates a balanced Trial Balance report from `tbl_account` joined with `tbl_ledgermaster`.
        - Double-entry vouchers (`AccTransId in {6, 7, 8, 9}`) are already self-balanced across their
          debit (`+amount`) and credit (`-amount`) ledger rows.
        - Operational single-sided rows from Phase 7 & 8 (`AccTransId in {1, 2, 3, 4, 5, 10, 11, 12, 13, 14}`)
          are automatically paired with their corresponding Control Accounts so that:
          `total_gross_debit == total_gross_credit`, `total_net_debit == total_net_credit`,
          `variance == 0.00`, and `is_balanced == True`.
        """
        ctx = self._get_principal(current_user)
        eff_branch = branch_id
        if not self._is_cross_branch_role(ctx.role_name):
            eff_branch = ctx.branch_id or 1

        entries = await self.repo.list_active_account_entries(
            branch_id=eff_branch,
            from_date=from_date,
            to_date=to_date,
        )

        # Accumulate (gross_dr, gross_cr) per LedgerMId
        ledger_buckets: Dict[int, Tuple[Decimal, Decimal, int]] = {}
        # Control account buckets for single-sided Phase 7/8 operational entries:
        # 990001: Policy Premium & Insurer Control
        # 990002: Customer Receipt & Bank Clearing Control
        # 990003: Unclear Commission Accrual Control
        # 990004: Partner E-Wallet Clearing Control
        control_meta: Dict[int, Tuple[str, int, int]] = {
            **LEGACY_SYSTEM_LEDGER_META,
            990001: ("POLICY PREMIUM & INSURER CONTROL ACCOUNT", 3, 30),
            990002: ("CUSTOMER RECEIPT & BANK CLEARING CONTROL", 1, 10),
            990003: ("UNCLEAR COMMISSION ACCRUAL CONTROL", 4, 40),
            990004: ("PARTNER E-WALLET CLEARING CONTROL", 2, 20),
        }

        def _add_to_bucket(lid: int, dr_val: Decimal, cr_val: Decimal, b_id: int) -> None:
            prev_dr, prev_cr, prev_b = ledger_buckets.get(lid, (ZERO, ZERO, b_id))
            ledger_buckets[lid] = (
                round_2dp(prev_dr + dr_val),
                round_2dp(prev_cr + cr_val),
                prev_b,
            )

        for e in entries:
            signed = round_2dp(_to_decimal(e.amount))
            if signed == ZERO:
                continue
            lid = e.LedgerMId or 1
            b_id = e.BranchId or (eff_branch or 1)
            dr_amt = signed if signed > ZERO else ZERO
            cr_amt = abs(signed) if signed < ZERO else ZERO

            _add_to_bucket(lid, dr_amt, cr_amt, b_id)

            acc_type = e.AccTransId or 0
            # Pair single-sided operational entries from Phases 7, 8 & 10 with their Control Account;
            # double-entry vouchers (6, 7, 8, 9, 15, 16, 17, 18) are already self-balanced.
            if acc_type not in {6, 7, 8, 9, 15, 16, 17, 18}:
                if acc_type in {1, 4, 5}:
                    ctrl_id = 990001
                elif acc_type == 2:
                    ctrl_id = 990002
                elif acc_type == 3:
                    ctrl_id = 990003
                else:
                    ctrl_id = 990004
                # Opposite leg on the Control Account
                _add_to_bucket(ctrl_id, cr_amt, dr_amt, b_id)

        tb_rows: List[TrialBalanceLedgerRowResponse] = []
        tot_gross_dr = ZERO
        tot_gross_cr = ZERO
        tot_net_dr = ZERO
        tot_net_cr = ZERO

        for lid in sorted(ledger_buckets.keys()):
            g_dr, g_cr, b_id = ledger_buckets[lid]
            closing = round_2dp(g_dr - g_cr)
            if closing > ZERO:
                n_dr = closing
                n_cr = ZERO
                pol: Literal["DR", "CR", "ZERO"] = "DR"
            elif closing < ZERO:
                n_dr = ZERO
                n_cr = abs(closing)
                pol = "CR"
            else:
                n_dr = ZERO
                n_cr = ZERO
                pol = "ZERO"

            if lid in control_meta:
                lname, ltype_id, lgrp_id = control_meta[lid]
            else:
                l_obj = await self.repo.get_ledger_by_id(lid, include_deleted=True)
                if l_obj is not None:
                    lname = l_obj.LedgerName or f"Ledger #{lid}"
                    ltype_id = l_obj.LedgerTypeId or 1
                    lgrp_id = l_obj.LedgerGroupId or 10
                else:
                    lname = f"Operational Ledger #{lid}"
                    ltype_id = 1
                    lgrp_id = 10

            tot_gross_dr = round_2dp(tot_gross_dr + g_dr)
            tot_gross_cr = round_2dp(tot_gross_cr + g_cr)
            tot_net_dr = round_2dp(tot_net_dr + n_dr)
            tot_net_cr = round_2dp(tot_net_cr + n_cr)

            tb_rows.append(
                TrialBalanceLedgerRowResponse(
                    ledger_m_id=lid,
                    ledger_name=lname,
                    ledger_type_id=ltype_id,
                    ledger_type_label=LEDGER_TYPE_LABELS.get(ltype_id, "ASSET"),
                    ledger_group_id=lgrp_id,
                    branch_id=b_id,
                    gross_debit=g_dr,
                    gross_credit=g_cr,
                    net_debit=n_dr,
                    net_credit=n_cr,
                    closing_balance=closing,
                    closing_polarity=pol,
                )
            )

        variance = round_2dp(tot_net_dr - tot_net_cr)
        return TrialBalanceResponse(
            branch_id=eff_branch,
            from_date=from_date,
            to_date=to_date,
            total_gross_debit=tot_gross_dr,
            total_gross_credit=tot_gross_cr,
            total_net_debit=tot_net_dr,
            total_net_credit=tot_net_cr,
            variance=variance,
            is_balanced=(variance == ZERO and tot_gross_dr == tot_gross_cr),
            ledger_count=len(tb_rows),
            items=tb_rows,
        )
