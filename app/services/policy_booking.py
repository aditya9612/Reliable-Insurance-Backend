"""
Service Layer for Phase 7 Policy Booking & Transaction Engine.

Orchestrates:
1. Policy Booking Financial Preview & Revalidation (reusing Phase 6 RatingEngineService & QuotationService)
2. Staged Mobile/Partner Policy Proposal Intake & Cashier/Accountant/Owner Approvals (tbl_transactionappnew)
3. Atomic Policy Booking (tbl_transaction + InwardNo + tbl_transactionpayment + commission tables + tbl_account)
4. Subsequent Payment Instrument Recording & Balance Reconciliation
5. Policy Underwriting Update & Atomic Cancellation / Ledger Reversal
"""
import asyncio
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import (
    AGENT_PRINCIPAL_ROLES,
    EMPLOYEE_PRINCIPAL_ROLES,
    FRANCHISE_PRINCIPAL_ROLES,
    POLICY_ACCOUNTANT_APPROVAL_ROLES,
    POLICY_CASHIER_APPROVAL_ROLES,
    POLICY_OWNER_APPROVAL_ROLES,
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
from app.models.payment import TransactionPayment
from app.models.transaction import Transaction
from app.models.transaction_app import TransactionAppNew
from app.models.user import User
from app.repositories.payment_engine import PaymentEngineRepository
from app.repositories.policy_booking import (
    PolicyBookingRepository,
    resolve_financial_year,
)
from app.repositories.quotation import QuotationRepository, _to_decimal
from app.schemas.policy import (
    AccountingEntryResponse,
    CommissionInput,
    PaymentInstrumentCreateRequest,
    PaymentInstrumentResponse,
    PolicyBookingCreateRequest,
    PolicyBookingListResponse,
    PolicyBookingResponse,
    PolicyBookingUpdateRequest,
    PolicyCancelRequest,
    PolicyCancelResponse,
    PolicyCommissionSummary,
    PolicyPaymentSummary,
    PolicyPremiumSummary,
    PolicyPreviewRequest,
    PolicyPreviewResponse,
    PolicyProposalApprovalRequest,
    PolicyProposalCreateRequest,
    PolicyProposalListResponse,
    PolicyProposalResponse,
)
from app.schemas.quotation import PremiumBreakdownResponse
from app.services.payment_engine import (
    WalletService,
    evaluate_payment_instrument_state,
    map_payment_instrument_response,
)
from app.services.quotation import QuotationService
from app.services.rating import HUNDRED, ONE_RUPEE, ZERO, RatingEngineService, round_rupee


TWO_DP = Decimal("0.01")

# Process-level lock that complements MySQL InnoDB FOR UPDATE locks during concurrent async bookings
_BOOKING_WRITE_LOCK = asyncio.Lock()

_AGENT_ROLES_NORM = frozenset(_normalize(r) for r in AGENT_PRINCIPAL_ROLES)
_EMPLOYEE_ROLES_NORM = frozenset(_normalize(r) for r in EMPLOYEE_PRINCIPAL_ROLES)
_FRANCHISE_ROLES_NORM = frozenset(_normalize(r) for r in FRANCHISE_PRINCIPAL_ROLES)
_CASHIER_APPROVAL_NORM = frozenset(_normalize(r) for r in POLICY_CASHIER_APPROVAL_ROLES)
_ACCOUNTANT_APPROVAL_NORM = frozenset(_normalize(r) for r in POLICY_ACCOUNTANT_APPROVAL_ROLES)
_OWNER_APPROVAL_NORM = frozenset(_normalize(r) for r in POLICY_OWNER_APPROVAL_ROLES)


def round_2dp(val: Decimal) -> Decimal:
    """Rounds a Decimal monetary or percentage value to 2 decimal places using ROUND_HALF_UP."""
    return val.quantize(TWO_DP, rounding=ROUND_HALF_UP)


class PolicyBookingService:
    """Business logic service for Phase 7 Policy Booking & Transaction Engine."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = PolicyBookingRepository(session)
        self.payment_repo = PaymentEngineRepository(session)
        self.wallet_service = WalletService(session)
        self.quotation_repo = QuotationRepository(session)
        self.rating_service = RatingEngineService(self.quotation_repo)
        self.quotation_service = QuotationService(session)


    # -----------------------------------------------------------------------
    # 1. Principal Context & Authorization Helpers
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
    def _is_cross_branch_read_role(role_name: Optional[str]) -> bool:
        norm = _normalize(role_name)
        return is_global_read_role(role_name) or norm == "ALL USER"

    def _resolve_commission_ownership(
        self,
        user: User,
        comm_in: CommissionInput,
        prefill_agent_id: Optional[int] = None,
        prefill_sales_ex_id: Optional[int] = None,
    ) -> Tuple[int, int, int, int]:
        """
        Resolves (agent_id, sales_ex_id, franchise_id, location_head_id) while enforcing
        strict server-side principal isolation so Agents, Employees, and Franchises cannot spoof ownership.
        """
        ctx = self._get_principal(user)
        norm_role = _normalize(ctx.role_name)

        req_agent = comm_in.agent_id if comm_in.agent_id is not None else prefill_agent_id
        req_sales = comm_in.sales_ex_id if comm_in.sales_ex_id is not None else prefill_sales_ex_id
        req_frn = comm_in.franchise_id
        req_loc = comm_in.location_head_id or 0

        if norm_role in _AGENT_ROLES_NORM:
            bound_agent = ctx.agent_id or ctx.user_id
            if comm_in.agent_id is not None and comm_in.agent_id > 0 and comm_in.agent_id != bound_agent:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: Agent principal cannot spoof another AgentId.",
                )
            eff_agent = bound_agent
            eff_sales = req_sales or 0
            eff_frn = ctx.franchise_id or (req_frn or 0)
        elif norm_role in _FRANCHISE_ROLES_NORM:
            bound_frn = ctx.franchise_id or ctx.user_id
            if comm_in.franchise_id is not None and comm_in.franchise_id > 0 and comm_in.franchise_id != bound_frn:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: Franchise principal cannot book policies for another FranchiseId.",
                )
            eff_frn = bound_frn
            eff_agent = req_agent or 0
            eff_sales = req_sales or 0
        elif norm_role in _EMPLOYEE_ROLES_NORM:
            bound_emp = ctx.emp_id or ctx.user_id
            if comm_in.sales_ex_id is not None and comm_in.sales_ex_id > 0 and comm_in.sales_ex_id != bound_emp:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: Employee/RM principal cannot spoof another SalesExecutiveId.",
                )
            eff_sales = bound_emp
            eff_agent = req_agent or 0
            eff_frn = ctx.franchise_id or (req_frn or 0)
        else:
            eff_agent = req_agent or 0
            eff_sales = req_sales or (ctx.emp_id or 0)
            eff_frn = req_frn or 0

        return eff_agent, eff_sales, eff_frn, req_loc

    def _assert_can_access_transaction(
        self,
        tx: Transaction,
        user: User,
        for_write: bool = False,
    ) -> None:
        """
        Enforces branch isolation and principal ownership scoping on tbl_transaction.
        """
        ctx = self._get_principal(user)
        norm_role = _normalize(ctx.role_name)

        if is_global_admin_role(ctx.role_name):
            return

        if not for_write and self._is_cross_branch_read_role(ctx.role_name):
            return

        # Branch isolation check
        if ctx.branch_id is not None and tx.BranchId is not None and tx.BranchId != ctx.branch_id:
            if norm_role != "ALL USER":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Access denied: Policy belongs to Branch {tx.BranchId}, outside caller Branch {ctx.branch_id}.",
                )

        # Principal ownership isolation
        if norm_role in _AGENT_ROLES_NORM:
            expected_agent = ctx.agent_id or ctx.user_id
            if tx.AgentId != expected_agent:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: Policy does not belong to your AgentId.",
                )
        elif norm_role in _FRANCHISE_ROLES_NORM:
            expected_frn = str(ctx.franchise_id or ctx.user_id)
            if str(tx.FranchiseCode or "0") != expected_frn:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: Policy does not belong to your Franchise scope.",
                )
        elif norm_role in _EMPLOYEE_ROLES_NORM:
            expected_emp = ctx.emp_id or ctx.user_id
            if tx.SalesEx_id != expected_emp and tx.LocationHeadId != expected_emp:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: Policy is outside your Sales Executive / Hierarchy scope.",
                )

    # -----------------------------------------------------------------------
    # 2. Financial Revalidation (Premium, NCB, OD Discount, GST)
    # -----------------------------------------------------------------------

    async def _resolve_and_revalidate_premiums(
        self,
        payload: PolicyPreviewRequest,
        current_user: User,
    ) -> Tuple[
        PolicyPremiumSummary,
        str,
        Optional[str],
        Optional[int],
        Optional[int],
        Optional[PremiumBreakdownResponse],
    ]:
        """
        Resolves and revalidates policy premium components without double-applying NCB,
        OD discount, or GST.
        Returns (premium_summary, source_type, quotation_code, prefill_agent_id, prefill_sales_ex_id, rating_breakdown).
        """
        source_type = "DIRECT_UNDERWRITING"
        quotation_code: Optional[str] = None
        prefill_agent_id: Optional[int] = None
        prefill_sales_ex_id: Optional[int] = None
        rating_breakdown: Optional[PremiumBreakdownResponse] = None

        # Validate NCB eligibility rules upfront
        if payload.product_type_id == 2:
            # Liability Only (STP) cannot carry OD, NCB, OD Discount, or Add-On
            if (
                (payload.od_premium is not None and payload.od_premium > ZERO)
                or payload.ncb_percent > ZERO
                or payload.ncb_amount > ZERO
                or payload.od_discount_percent > ZERO
                or payload.addon_premium > ZERO
            ):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=(
                        "Liability-only (product_type_id=2) policy cannot have positive "
                        "OD premium, NCB, OD discount, or Add-On premium."
                    ),
                )

        if payload.product_type_id == 3:
            # Standalone OD (SAOD) cannot carry Third-Party Liability premium
            if payload.tp_premium is not None and payload.tp_premium > ZERO:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Standalone OD (product_type_id=3) policy cannot have positive TP premium.",
                )

        if payload.business_type_id == 1 or payload.claim_in_previous_policy:
            if payload.ncb_percent > ZERO or payload.ncb_amount > ZERO:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="NCB must be 0% for New vehicles (business_type_id=1) or policies with a previous claim.",
                )

        # Pathway A: Self-Quotation or Assisted Quotation Request Link
        if payload.quotation_id is not None:
            q_source = payload.quotation_source_type or "SELF_QUOTATION"
            prefill = await self.quotation_service.get_policy_prefill(
                quotation_id=payload.quotation_id,
                source_type=q_source,
                current_user=current_user,
                insurance_company_id=payload.insurance_company_id,
            )
            source_type = q_source
            quotation_code = prefill.quotation_code
            prefill_agent_id = prefill.agent_id
            prefill_sales_ex_id = prefill.sales_ex_id

            if q_source == "SELF_QUOTATION" and payload.calculation_input is None:
                entry = await self.quotation_repo.get_self_quotation_by_id(payload.quotation_id)
                assert entry is not None

                # Anti-tamper check when caller also supplies net_premium or final_premium
                q_od = round_2dp(_to_decimal(entry.AtotalOwnDamPremium))
                q_tp = round_2dp(_to_decimal(entry.BtotalLiabilityPremium))
                q_net = round_2dp(_to_decimal(entry.TotalPremium))
                q_gst = round_2dp(_to_decimal(entry.GST18))
                q_final = round_2dp(_to_decimal(entry.finalPrmium))

                if not payload.allow_underwriting_override:
                    if payload.net_premium is not None and abs(payload.net_premium - q_net) > ONE_RUPEE:
                        raise HTTPException(
                            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail=(
                                f"Submitted net_premium ({payload.net_premium}) does not match "
                                f"Self-Quotation TotalPremium ({q_net})."
                            ),
                        )
                    if payload.final_premium is not None and abs(payload.final_premium - q_final) > ONE_RUPEE:
                        raise HTTPException(
                            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail=(
                                f"Submitted final_premium ({payload.final_premium}) does not match "
                                f"Self-Quotation finalPrmium ({q_final})."
                            ),
                        )

                gross_od = _to_decimal(entry.OwnDamagePremium)
                od_disc_amt = round_2dp(_to_decimal(entry.OD))
                od_disc_pct = (
                    round_2dp((od_disc_amt * HUNDRED) / gross_od)
                    if gross_od > ZERO
                    else ZERO
                )
                addon_amt = round_2dp(_to_decimal(entry.ZeroDepreciation))
                ncb_amt = round_2dp(_to_decimal(entry.NoClaimBonus))
                ncb_pct = round_2dp(_to_decimal(entry.NCBPre))
                imt23_amt = round_2dp(_to_decimal(entry.AddExtra15IMTno23))
                towing_amt = round_2dp(
                    _to_decimal(getattr(entry, "Extratowingcoverage", None) or payload.towing_amount)
                )
                pa_owner = round_2dp(_to_decimal(getattr(entry, "PAforOwnerDriver", None)))
                pa_drv_cleaner = round_2dp(
                    _to_decimal(getattr(entry, "PAToPaidDriver", None) or payload.pa_driver_cleaner)
                )
                ll_driver = round_2dp(
                    _to_decimal(getattr(entry, "legallibtoPaidDriver", None))
                    + _to_decimal(getattr(entry, "LLtoDrCleanerandCoolies", None))
                    + _to_decimal(getattr(entry, "LegallibtoEmp", None))
                )

                # IMPORTANT: AtotalOwnDamPremium already includes OD discount, NCB deduction, and Add-Ons.
                # Never subtract NCB or OD discount a second time!
                summary = PolicyPremiumSummary(
                    sum_insured_idv=round_2dp(_to_decimal(entry.IDV)),
                    gvw=round_2dp(Decimal(str(entry.VehicleWeight or "0"))),
                    od_premium=q_od,
                    tp_premium=q_tp,
                    basic_tp_premium=round_2dp(_to_decimal(entry.LiabilityPremium)),
                    net_premium=q_net,
                    gst_amount=q_gst,
                    final_premium=q_final,
                    ncb_percent=ncb_pct,
                    ncb_amount=ncb_amt,
                    od_discount_percent=od_disc_pct,
                    od_discount_amount=od_disc_amt,
                    addon_rate_percent=payload.addon_rate_percent,
                    addon_premium=addon_amt,
                    is_nill_dep=bool(addon_amt > ZERO or payload.is_nill_dep),
                    imt23_amount=imt23_amt,
                    towing_amount=towing_amt,
                    rsa_amount=round_2dp(payload.rsa_amount),
                    pa_owner_driver=pa_owner,
                    pa_driver_cleaner=pa_drv_cleaner,
                    ll_paid_driver=ll_driver,
                )
                return (
                    summary,
                    source_type,
                    quotation_code,
                    prefill_agent_id,
                    prefill_sales_ex_id,
                    None,
                )

        # Pathway B: Full Deterministic Rating Engine Revalidation
        if payload.calculation_input is not None:
            if source_type == "DIRECT_UNDERWRITING":
                source_type = "RATING_ENGINE"
            rating_breakdown = await self.rating_service.calculate_premium(
                payload.calculation_input
            )
            r_od = round_2dp(rating_breakdown.total_od_with_addons)
            r_tp = round_2dp(rating_breakdown.total_tp_premium)
            r_net = round_2dp(rating_breakdown.net_premium)
            r_gst = round_2dp(rating_breakdown.total_gst)
            r_final = round_2dp(rating_breakdown.final_payable_premium)

            if not payload.allow_underwriting_override:
                if payload.net_premium is not None and abs(payload.net_premium - r_net) > ONE_RUPEE:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=(
                            f"Submitted net_premium ({payload.net_premium}) does not match "
                            f"revalidated rating net_premium ({r_net})."
                        ),
                    )
                if payload.gst_amount is not None and abs(payload.gst_amount - r_gst) > ONE_RUPEE:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=(
                            f"Submitted gst_amount ({payload.gst_amount}) does not match "
                            f"revalidated rating total_gst ({r_gst})."
                        ),
                    )
                if payload.final_premium is not None and abs(payload.final_premium - r_final) > ONE_RUPEE:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=(
                            f"Submitted final_premium ({payload.final_premium}) does not match "
                            f"revalidated rating final_payable_premium ({r_final})."
                        ),
                    )

            ll_combined = round_2dp(
                rating_breakdown.ll_paid_driver_premium
                + rating_breakdown.ll_cleaner_premium
                + rating_breakdown.ll_coolie_premium
                + rating_breakdown.ll_employee_premium
            )
            summary = PolicyPremiumSummary(
                sum_insured_idv=round_2dp(rating_breakdown.total_idv),
                gvw=round_2dp(Decimal(str(payload.calculation_input.gross_vehicle_weight))),
                od_premium=r_od,
                tp_premium=r_tp,
                basic_tp_premium=round_2dp(rating_breakdown.basic_tp_premium),
                net_premium=r_net,
                gst_amount=r_gst,
                final_premium=r_final,
                ncb_percent=round_2dp(rating_breakdown.ncb_percent),
                ncb_amount=round_2dp(rating_breakdown.ncb_amount),
                od_discount_percent=round_2dp(rating_breakdown.od_discount_percent),
                od_discount_amount=round_2dp(rating_breakdown.od_discount_amount),
                addon_rate_percent=round_2dp(rating_breakdown.zero_dep_rate_percent),
                addon_premium=round_2dp(rating_breakdown.zero_dep_premium),
                is_nill_dep=bool(rating_breakdown.zero_dep_premium > ZERO),
                imt23_amount=round_2dp(rating_breakdown.imt23_loading_amount),
                towing_amount=round_2dp(rating_breakdown.towing_charges_amount),
                rsa_amount=round_2dp(payload.rsa_amount),
                pa_owner_driver=round_2dp(rating_breakdown.pa_owner_driver_premium),
                pa_driver_cleaner=round_2dp(rating_breakdown.pa_paid_driver_premium),
                ll_paid_driver=ll_combined,
            )
            return (
                summary,
                source_type,
                quotation_code,
                prefill_agent_id,
                prefill_sales_ex_id,
                rating_breakdown,
            )

        # Pathway C: Direct Underwriting Figures (or Assisted Quotation Request with Manual Insurer Schedule)
        if payload.od_premium is None and payload.tp_premium is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "Either calculation_input, a SELF_QUOTATION quotation_id, or explicit "
                    "od_premium/tp_premium figures must be provided."
                ),
            )

        od_prem = round_2dp(payload.od_premium or ZERO)
        tp_prem = round_2dp(payload.tp_premium or ZERO)
        expected_net = round_2dp(od_prem + tp_prem)

        if payload.net_premium is not None:
            net_prem = round_2dp(payload.net_premium)
            if abs(net_prem - expected_net) > ONE_RUPEE:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=(
                        f"Mathematical inconsistency: net_premium ({net_prem}) must equal "
                        f"od_premium ({od_prem}) + tp_premium ({tp_prem}) = {expected_net}."
                    ),
                )
        else:
            net_prem = expected_net

        # Statutory GST calculation & revalidation
        pa_owner = round_2dp(payload.pa_owner_driver)
        pa_cleaner = round_2dp(payload.pa_driver_cleaner)
        ll_driver = round_2dp(payload.ll_paid_driver)

        if payload.basic_tp_premium is not None:
            basic_tp = round_2dp(payload.basic_tp_premium)
        else:
            basic_tp = max(ZERO, round_2dp(tp_prem - pa_owner - pa_cleaner - ll_driver))

        if (
            payload.vehicle_category in {"Public_GCV", "Private_GCV", "PublicGCV3W"}
            and payload.gcv_split_tp_gst
        ):
            explicit_risk_date = (
                payload.risk_start_date
                if ("risk_start_date" in payload.model_fields_set and payload.risk_start_date is not None)
                else None
            )
            gcv_tp_gst_rate = RatingEngineService.resolve_gcv_basic_tp_gst_rate(
                risk_start_date=explicit_risk_date,
                calculation_date=payload.risk_start_date,
                apply_cutover=payload.apply_gcv_2025_09_23_tp_gst_cutover,
                rate_override=payload.gcv_basic_tp_gst_rate_override,
            )
            gst_basic_tp = round_rupee((basic_tp * gcv_tp_gst_rate) / HUNDRED)
            gst_18 = round_rupee(((net_prem - basic_tp) * Decimal("18")) / HUNDRED)
            expected_gst = round_2dp(gst_basic_tp + gst_18)
        else:
            expected_gst = round_2dp(round_rupee((net_prem * Decimal("18")) / HUNDRED))

        if payload.gst_amount is not None:
            gst_amt = round_2dp(payload.gst_amount)
            if payload.validate_statutory_gst and abs(gst_amt - expected_gst) > ONE_RUPEE:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=(
                        f"GST revalidation failed: submitted gst_amount ({gst_amt}) deviates from "
                        f"statutory GST ({expected_gst}) for category '{payload.vehicle_category}'."
                    ),
                )
        else:
            gst_amt = expected_gst

        expected_final = round_2dp(net_prem + gst_amt)
        if payload.final_premium is not None:
            final_prem = round_2dp(payload.final_premium)
            if abs(final_prem - expected_final) > ONE_RUPEE:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=(
                        f"Mathematical inconsistency: final_premium ({final_prem}) must equal "
                        f"net_premium ({net_prem}) + gst_amount ({gst_amt}) = {expected_final}."
                    ),
                )
        else:
            final_prem = expected_final

        sum_insured = round_2dp(
            payload.sum_insured_idv
            if payload.sum_insured_idv is not None
            else (ZERO if payload.product_type_id == 2 else Decimal("100000.00"))
        )
        if payload.product_type_id == 2:
            sum_insured = ZERO

        summary = PolicyPremiumSummary(
            sum_insured_idv=sum_insured,
            gvw=round_2dp(payload.gvw),
            od_premium=od_prem,
            tp_premium=tp_prem,
            basic_tp_premium=basic_tp,
            net_premium=net_prem,
            gst_amount=gst_amt,
            final_premium=final_prem,
            ncb_percent=round_2dp(payload.ncb_percent),
            ncb_amount=round_2dp(payload.ncb_amount),
            od_discount_percent=round_2dp(payload.od_discount_percent),
            od_discount_amount=round_2dp(payload.od_discount_amount),
            addon_rate_percent=round_2dp(payload.addon_rate_percent),
            addon_premium=round_2dp(payload.addon_premium),
            is_nill_dep=bool(payload.is_nill_dep or payload.addon_premium > ZERO),
            imt23_amount=round_2dp(payload.imt23_amount),
            towing_amount=round_2dp(payload.towing_amount),
            rsa_amount=round_2dp(payload.rsa_amount),
            pa_owner_driver=pa_owner,
            pa_driver_cleaner=pa_cleaner,
            ll_paid_driver=ll_driver,
        )
        return (
            summary,
            source_type,
            quotation_code,
            prefill_agent_id,
            prefill_sales_ex_id,
            None,
        )

    # -----------------------------------------------------------------------
    # 3. Deterministic Commission & TDS Calculation
    # -----------------------------------------------------------------------

    @staticmethod
    def calculate_commission_summary(
        premium: PolicyPremiumSummary,
        comm_in: CommissionInput,
        eff_agent_id: int,
        eff_sales_ex_id: int,
        eff_franchise_id: int,
        eff_location_head_id: int,
        *,
        insurance_company_id: int = 1,
        policy_type_id: int = 1,
        motor_or_non_motor: str = "MOTOR",
    ) -> PolicyCommissionSummary:
        """
        Calculates deterministic multi-bucket (OD, Net/TP, Extra) agent and franchise
        commissions and TDS deductions using Decimal arithmetic (ROUND_HALF_UP).
        Includes:
        - `adm_PolicyDetails.aspx.cs:L1468` GCV + HDFC ERGO (`InsuranceCompanyId == 2` and `PolicyTypeId > 18`)
          Net-only commission branch (`GAP-P7-001`)
        - `adm_NewEntryForLifeORHelth.aspx.cs` Non-Motor (`NONMOTOR`) 15% default TDS (`GAP-P7-002`)
        """
        if motor_or_non_motor == "NONMOTOR" and "tds_percent" not in comm_in.model_fields_set:
            tds_pct = Decimal("15.00")
        else:
            tds_pct = round_2dp(comm_in.tds_percent)
        od_pct = round_2dp(comm_in.agent_comm_od_percent)
        net_pct = round_2dp(comm_in.agent_comm_net_percent)
        extra_pct = round_2dp(comm_in.agent_comm_extra_percent)
        headline_pct = round_2dp(comm_in.agent_comm_percent)

        # adm_PolicyDetails.aspx.cs:L1468 parity:
        # For GCV + HDFC ERGO (InsuranceCompanyId == 2 and PolicyTypeId > 18), only Net Commission applies
        is_hdfc_gcv_net_only = bool(
            comm_in.enforce_hdfc_gcv_net_only
            or (insurance_company_id == 2 and policy_type_id > 18)
        )

        od_base = premium.od_premium
        if is_hdfc_gcv_net_only or comm_in.commission_on_full_net or (od_pct == ZERO and net_pct > ZERO):
            net_base = premium.net_premium
        else:
            if comm_in.include_pa_in_tp_comm:
                net_base = premium.tp_premium
            else:
                net_base = max(ZERO, round_2dp(premium.tp_premium - premium.pa_owner_driver))

        extra_base = premium.od_premium if premium.od_premium > ZERO else premium.net_premium

        if is_hdfc_gcv_net_only:
            eff_net_pct = net_pct if net_pct > ZERO else (headline_pct if headline_pct > ZERO else od_pct)
            od_pct = ZERO
            od_base = ZERO
            od_comm_amt = ZERO
            tds_od = ZERO
            net_comm_od = ZERO

            net_pct = eff_net_pct
            net_comm_amt = round_2dp((net_base * net_pct) / HUNDRED)
            tds_net = round_2dp((net_comm_amt * tds_pct) / HUNDRED)
            net_comm_net = round_2dp(net_comm_amt - tds_net)

            extra_pct = ZERO
            extra_base = ZERO
            extra_comm_amt = ZERO
            tds_extra = ZERO
            net_comm_extra = ZERO
            headline_pct = net_pct
        elif od_pct == ZERO and net_pct == ZERO and extra_pct == ZERO and headline_pct > ZERO:
            od_comm_amt = ZERO
            tds_od = ZERO
            net_comm_od = ZERO

            net_base = premium.net_premium
            net_pct = headline_pct
            net_comm_amt = round_2dp((net_base * headline_pct) / HUNDRED)
            tds_net = round_2dp((net_comm_amt * tds_pct) / HUNDRED)
            net_comm_net = round_2dp(net_comm_amt - tds_net)

            extra_comm_amt = ZERO
            tds_extra = ZERO
            net_comm_extra = ZERO
        else:
            od_comm_amt = round_2dp((od_base * od_pct) / HUNDRED)
            tds_od = round_2dp((od_comm_amt * tds_pct) / HUNDRED)
            net_comm_od = round_2dp(od_comm_amt - tds_od)

            net_comm_amt = round_2dp((net_base * net_pct) / HUNDRED)
            tds_net = round_2dp((net_comm_amt * tds_pct) / HUNDRED)
            net_comm_net = round_2dp(net_comm_amt - tds_net)

            extra_comm_amt = round_2dp((extra_base * extra_pct) / HUNDRED)
            tds_extra = round_2dp((extra_comm_amt * tds_pct) / HUNDRED)
            net_comm_extra = round_2dp(extra_comm_amt - tds_extra)

            if headline_pct == ZERO:
                headline_pct = round_2dp(od_pct + net_pct + extra_pct)

        total_gross = round_2dp(od_comm_amt + net_comm_amt + extra_comm_amt)
        total_tds = round_2dp(tds_od + tds_net + tds_extra)
        total_net = round_2dp(total_gross - total_tds)

        # Franchise commission calculation when eff_franchise_id > 0
        frn_gross = ZERO
        frn_tds = ZERO
        frn_net = ZERO
        if eff_franchise_id > 0:
            f_od_pct = (
                ZERO
                if is_hdfc_gcv_net_only
                else (
                    round_2dp(comm_in.franchise_comm_od_percent)
                    if comm_in.franchise_comm_od_percent is not None
                    else od_pct
                )
            )
            f_net_pct = (
                round_2dp(comm_in.franchise_comm_net_percent)
                if comm_in.franchise_comm_net_percent is not None
                else net_pct
            )
            f_extra_pct = (
                ZERO
                if is_hdfc_gcv_net_only
                else (
                    round_2dp(comm_in.franchise_comm_extra_percent)
                    if comm_in.franchise_comm_extra_percent is not None
                    else extra_pct
                )
            )
            f_od_amt = round_2dp((od_base * f_od_pct) / HUNDRED)
            f_od_tds = round_2dp((f_od_amt * tds_pct) / HUNDRED)
            f_net_amt = round_2dp((net_base * f_net_pct) / HUNDRED)
            f_net_tds = round_2dp((f_net_amt * tds_pct) / HUNDRED)
            f_ext_amt = round_2dp((extra_base * f_extra_pct) / HUNDRED)
            f_ext_tds = round_2dp((f_ext_amt * tds_pct) / HUNDRED)

            frn_gross = round_2dp(f_od_amt + f_net_amt + f_ext_amt)
            frn_tds = round_2dp(f_od_tds + f_net_tds + f_ext_tds)
            frn_net = round_2dp(frn_gross - frn_tds)

        return PolicyCommissionSummary(
            agent_id=eff_agent_id,
            sales_ex_id=eff_sales_ex_id,
            franchise_id=eff_franchise_id,
            location_head_id=eff_location_head_id,
            od_commission_base=od_base,
            agent_comm_od_percent=od_pct,
            agent_comm_od_amount=od_comm_amt,
            tds_od_amount=tds_od,
            net_comm_od_amount=net_comm_od,
            net_commission_base=net_base,
            agent_comm_net_percent=net_pct,
            agent_comm_net_amount=net_comm_amt,
            tds_net_amount=tds_net,
            net_comm_net_amount=net_comm_net,
            extra_commission_base=extra_base,
            agent_comm_extra_percent=extra_pct,
            agent_comm_extra_amount=extra_comm_amt,
            tds_extra_amount=tds_extra,
            net_comm_extra_amount=net_comm_extra,
            headline_agent_comm_percent=headline_pct,
            total_gross_commission=total_gross,
            tds_percent=tds_pct,
            total_tds_amount=total_tds,
            total_net_commission=total_net,
            franchise_gross_commission=frn_gross,
            franchise_tds_amount=frn_tds,
            franchise_net_commission=frn_net,
        )

    # -----------------------------------------------------------------------
    # 4. Deterministic Payment & Balance Calculation
    # -----------------------------------------------------------------------

    @staticmethod
    def calculate_payment_summary(
        premium: PolicyPremiumSummary,
        commission: PolicyCommissionSummary,
        cutnpay_enabled: bool,
        cutnpay_amount: Optional[Decimal],
        ewallet_amount_used: Decimal,
        online_payment_to_company: Decimal,
        payments: List[PaymentInstrumentCreateRequest],
        branch_id: int,
    ) -> PolicyPaymentSummary:
        """
        Computes required payable amount, Cut & Pay deduction, E-Wallet deduction,
        instrument collection total, and remaining outstanding balance.
        """
        gross_payable = premium.final_premium
        ewallet_amt = round_2dp(ewallet_amount_used)
        online_amt = round_2dp(online_payment_to_company)

        if cutnpay_enabled:
            if cutnpay_amount is not None:
                cnp_deduction = round_2dp(cutnpay_amount)
                if (
                    commission.total_net_commission > ZERO
                    and cnp_deduction > commission.total_net_commission
                ):
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=(
                            f"cutnpay_amount ({cnp_deduction}) cannot exceed "
                            f"total_net_commission ({commission.total_net_commission})."
                        ),
                    )
            else:
                cnp_deduction = commission.total_net_commission
        else:
            if cutnpay_amount is not None and cutnpay_amount > ZERO:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="cutnpay_amount cannot be positive when cutnpay_enabled is False.",
                )
            cnp_deduction = ZERO

        if cnp_deduction > gross_payable:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Cut & Pay deduction ({cnp_deduction}) cannot exceed gross premium ({gross_payable}).",
            )

        required_payable = round_2dp(gross_payable - cnp_deduction)
        instrument_total = round_2dp(sum((p.paid_amount for p in payments), ZERO))
        total_paid = round_2dp(instrument_total + ewallet_amt + online_amt)

        if total_paid > required_payable:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"Overpayment rejected: Total paid amount ({total_paid}) exceeds "
                    f"required payable amount ({required_payable})."
                ),
            )

        outstanding = round_2dp(max(ZERO, required_payable - total_paid))
        is_complete = 1 if outstanding == ZERO else 0

        payment_responses: List[PaymentInstrumentResponse] = []
        for p in payments:
            p_dt = (
                datetime.combine(p.payment_date, datetime.min.time())
                if p.payment_date
                else datetime.utcnow()
            )
            init_status, cash_app = evaluate_payment_instrument_state(p.payment_type)
            payment_responses.append(
                PaymentInstrumentResponse(
                    payment_type=p.payment_type,
                    paid_amount=round_2dp(p.paid_amount),
                    payment_date=p_dt,
                    docno=p.docno,
                    bankname=p.bankname,
                    payment_details=p.payment_details,
                    status=init_status,
                    cashier_approval=cash_app,
                    is_complete_payment=is_complete,
                    branch_id=branch_id,
                    isdeleted="0",
                )
            )


        return PolicyPaymentSummary(
            gross_payable_amount=gross_payable,
            cutnpay_enabled=cutnpay_enabled,
            cutnpay_deduction=cnp_deduction,
            ewallet_amount_used=ewallet_amt,
            online_payment_to_company=online_amt,
            required_payable_amount=required_payable,
            instrument_paid_amount=instrument_total,
            paid_amount=total_paid,
            outstanding_amount=outstanding,
            is_complete_payment=is_complete,
            payments=payment_responses,
        )

    # -----------------------------------------------------------------------
    # 5. Deterministic Double-Entry Accounting Builder (AccTransId = 1, 2, 3)
    # -----------------------------------------------------------------------

    @staticmethod
    def build_accounting_entries(
        premium: PolicyPremiumSummary,
        commission: PolicyCommissionSummary,
        payment: PolicyPaymentSummary,
        branch_id: int,
        ledger_m_id: int = 1,
        customer_id: Optional[int] = None,
        cust_veh_id: int = 0,
        transaction_id: Optional[int] = None,
        inward_no: str = "PREVIEW",
    ) -> List[AccountingEntryResponse]:
        """
        Builds the 3 canonical accounting ledger rows for tbl_account:
        - AccTransId = 1: Policy Premium Receivable (+Amount)
        - AccTransId = 2: Policy Payment Receipt (+PaidAmount, when PaidAmount > 0)
        - AccTransId = 3: Unclear Policy Commission Entry (-NetCommission, ALWAYS negative polarity!)
        """
        is_nill_int = 1 if premium.is_nill_dep else 0
        primary_pay_type = (
            payment.payments[0].payment_type
            if payment.payments
            else ("CUTNPAY" if payment.cutnpay_enabled else "CASH")
        )

        entries: List[AccountingEntryResponse] = [
            AccountingEntryResponse(
                acc_trans_id=1,
                transaction_type="POLICY_BOOKING",
                ledger_m_id=ledger_m_id,
                amount=premium.final_premium,
                narration=f"Policy Premium Booking - {inward_no}",
                reference_cust_id=customer_id,
                reference_agent_id=commission.agent_id,
                branch_id=branch_id,
                payment_type=primary_pay_type,
                transaction_id=transaction_id,
                cust_veh_id=cust_veh_id,
                is_nill=is_nill_int,
                isdeleted=0,
            )
        ]

        if payment.paid_amount > ZERO:
            entries.append(
                AccountingEntryResponse(
                    acc_trans_id=2,
                    transaction_type="POLICY_PAYMENT",
                    ledger_m_id=ledger_m_id,
                    amount=payment.paid_amount,
                    narration=f"Policy Payment Receipt - {inward_no}",
                    reference_cust_id=customer_id,
                    reference_agent_id=commission.agent_id,
                    branch_id=branch_id,
                    payment_type=primary_pay_type,
                    transaction_id=transaction_id,
                    cust_veh_id=cust_veh_id,
                    is_nill=is_nill_int,
                    isdeleted=0,
                )
            )

        # AccTransId = 3: Unclear Policy Commission Entry with negative polarity (-NetCommission)
        neg_net_comm = (
            -commission.total_net_commission
            if commission.total_net_commission > ZERO
            else ZERO
        )
        entries.append(
            AccountingEntryResponse(
                acc_trans_id=3,
                transaction_type="UNCLEAR_COMMISSION",
                ledger_m_id=ledger_m_id,
                amount=neg_net_comm,
                narration=f"Unclear Policy Commission Entry - {inward_no}",
                reference_cust_id=customer_id,
                reference_agent_id=commission.agent_id,
                branch_id=branch_id,
                payment_type="COMMISSION",
                transaction_id=transaction_id,
                cust_veh_id=cust_veh_id,
                is_nill=is_nill_int,
                isdeleted=0,
            )
        )

        return entries

    # -----------------------------------------------------------------------
    # 6. Stateless / Quotation-Backed Preview (POST /api/v1/policies/preview)
    # -----------------------------------------------------------------------

    async def preview_policy(
        self,
        payload: PolicyPreviewRequest,
        current_user: User,
    ) -> PolicyPreviewResponse:
        ctx = self._get_principal(current_user)
        branch_id = ctx.branch_id or 1

        (
            premium_summary,
            source_type,
            quotation_code,
            prefill_agent_id,
            prefill_sales_ex_id,
            rating_breakdown,
        ) = await self._resolve_and_revalidate_premiums(payload, current_user)

        eff_agent, eff_sales, eff_frn, eff_loc = self._resolve_commission_ownership(
            user=current_user,
            comm_in=payload.commission,
            prefill_agent_id=prefill_agent_id,
            prefill_sales_ex_id=prefill_sales_ex_id,
        )

        comm_summary = self.calculate_commission_summary(
            premium=premium_summary,
            comm_in=payload.commission,
            eff_agent_id=eff_agent,
            eff_sales_ex_id=eff_sales,
            eff_franchise_id=eff_frn,
            eff_location_head_id=eff_loc,
            insurance_company_id=payload.insurance_company_id,
            policy_type_id=payload.policy_type_id,
            motor_or_non_motor=payload.motor_or_non_motor,
        )

        pay_summary = self.calculate_payment_summary(
            premium=premium_summary,
            commission=comm_summary,
            cutnpay_enabled=payload.cutnpay_enabled,
            cutnpay_amount=payload.cutnpay_amount,
            ewallet_amount_used=payload.ewallet_amount_used,
            online_payment_to_company=payload.online_payment_to_company,
            payments=payload.payments,
            branch_id=branch_id,
        )

        acct_entries = self.build_accounting_entries(
            premium=premium_summary,
            commission=comm_summary,
            payment=pay_summary,
            branch_id=branch_id,
        )

        t_status = "Booked" if pay_summary.is_complete_payment == 1 else "Pending"
        pending_status = 0 if pay_summary.is_complete_payment == 1 else 1

        return PolicyPreviewResponse(
            source_type=source_type,
            quotation_code=quotation_code,
            insurance_company_id=payload.insurance_company_id,
            product_type_id=payload.product_type_id,
            business_type_id=payload.business_type_id,
            vehicle_category=payload.vehicle_category,
            t_status=t_status,
            pending_status=pending_status,
            premium_summary=premium_summary,
            commission_summary=comm_summary,
            payment_summary=pay_summary,
            accounting_entries=acct_entries,
            rating_breakdown=rating_breakdown,
        )

    # -----------------------------------------------------------------------
    # 7. Atomic Policy Booking (POST /api/v1/policies/book)
    # -----------------------------------------------------------------------

    async def book_policy(
        self,
        payload: PolicyBookingCreateRequest,
        current_user: User,
    ) -> PolicyBookingResponse:
        """
        Executes atomic policy booking across:
        - tbl_transaction (with concurrency-safe InwardNo)
        - tbl_transactionpayment
        - tbl_franchisecommission / tbl_cutnpaycommpayable / tbl_agentcommissionpayment
        - tbl_account (AccTransId = 1, 2, 3)
        - tbl_transactionappnew (if proposal_trans_id is linked)
        Rolls back the entire unit of work on any downstream error.
        """
        ctx = self._get_principal(current_user)
        norm_role = _normalize(ctx.role_name)

        # 1. Verify Customer & Vehicle exist and belong together
        customer = await self.repo.get_active_customer(payload.customer_id)
        if customer is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Customer #{payload.customer_id} not found or deleted.",
            )

        vehicle = await self.repo.get_active_vehicle(payload.cust_veh_id)
        if vehicle is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Vehicle #{payload.cust_veh_id} not found or deleted.",
            )

        if vehicle.CustomerId != customer.CustomerId:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"Vehicle #{vehicle.CustVehId} belongs to Customer #{vehicle.CustomerId}, "
                    f"not Customer #{customer.CustomerId}."
                ),
            )

        # 2. Enforce Branch Isolation on Customer & Vehicle
        if not is_global_admin_role(ctx.role_name) and norm_role != "ALL USER":
            caller_branch = ctx.branch_id or 1
            if customer.BranchId is not None and customer.BranchId != caller_branch:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=(
                        f"Access denied: Customer #{customer.CustomerId} belongs to "
                        f"Branch {customer.BranchId}, outside caller Branch {caller_branch}."
                    ),
                )
            if vehicle.BranchId is not None and vehicle.BranchId != caller_branch:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=(
                        f"Access denied: Vehicle #{vehicle.CustVehId} belongs to "
                        f"Branch {vehicle.BranchId}, outside caller Branch {caller_branch}."
                    ),
                )

        eff_branch_id = (
            payload.branch_id
            if (payload.branch_id is not None and is_global_admin_role(ctx.role_name))
            else (customer.BranchId or ctx.branch_id or 1)
        )

        # 3. Validate Staged Proposal if linked
        staged_proposal: Optional[TransactionAppNew] = None
        if payload.proposal_trans_id is not None:
            staged_proposal = await self.repo.get_proposal_by_id(payload.proposal_trans_id)
            if staged_proposal is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Staged Policy Proposal #{payload.proposal_trans_id} not found.",
                )

        # 4. Revalidate Premium, NCB, OD Discount, GST, Commission & Payment Math
        (
            premium_summary,
            _,
            quotation_code,
            prefill_agent_id,
            prefill_sales_ex_id,
            _,
        ) = await self._resolve_and_revalidate_premiums(payload, current_user)

        if quotation_code is None and staged_proposal is not None and staged_proposal.QuatationCode:
            quotation_code = staged_proposal.QuatationCode

        eff_agent, eff_sales, eff_frn, eff_loc = self._resolve_commission_ownership(
            user=current_user,
            comm_in=payload.commission,
            prefill_agent_id=prefill_agent_id,
            prefill_sales_ex_id=prefill_sales_ex_id,
        )

        comm_summary = self.calculate_commission_summary(
            premium=premium_summary,
            comm_in=payload.commission,
            eff_agent_id=eff_agent,
            eff_sales_ex_id=eff_sales,
            eff_franchise_id=eff_frn,
            eff_location_head_id=eff_loc,
            insurance_company_id=payload.insurance_company_id,
            policy_type_id=payload.policy_type_id,
            motor_or_non_motor=payload.motor_or_non_motor,
        )

        pay_summary = self.calculate_payment_summary(
            premium=premium_summary,
            commission=comm_summary,
            cutnpay_enabled=payload.cutnpay_enabled,
            cutnpay_amount=payload.cutnpay_amount,
            ewallet_amount_used=payload.ewallet_amount_used,
            online_payment_to_company=payload.online_payment_to_company,
            payments=payload.payments,
            branch_id=eff_branch_id,
        )

        # 5. Atomic Write Section (Serialized via _BOOKING_WRITE_LOCK + InnoDB FOR UPDATE)
        async with _BOOKING_WRITE_LOCK:
            try:
                # 5a. Check Idempotency & Duplicate Guards under FOR UPDATE lock
                if payload.idempotency_key:
                    dup_idem = await self.repo.get_active_by_idempotency_key(
                        payload.idempotency_key
                    )
                    if dup_idem is not None:
                        raise HTTPException(
                            status_code=status.HTTP_409_CONFLICT,
                            detail=(
                                f"Duplicate booking request: idempotency_key '{payload.idempotency_key}' "
                                f"already booked as Transaction #{dup_idem.TransanctionId} ({dup_idem.InwardNo})."
                            ),
                        )

                if payload.policy_no:
                    dup_pol = await self.repo.get_active_by_policy_no(
                        policy_no=payload.policy_no,
                        insurance_company_id=payload.insurance_company_id,
                    )
                    if dup_pol is not None:
                        raise HTTPException(
                            status_code=status.HTTP_409_CONFLICT,
                            detail=(
                                f"Duplicate PolicyNo: Policy '{payload.policy_no}' is already booked "
                                f"for Insurer #{payload.insurance_company_id} under Transaction #{dup_pol.TransanctionId}."
                            ),
                        )

                if quotation_code:
                    dup_quot = await self.repo.get_active_by_quotation_code(quotation_code)
                    if dup_quot is not None:
                        raise HTTPException(
                            status_code=status.HTTP_409_CONFLICT,
                            detail=(
                                f"Quotation '{quotation_code}' has already been consumed by "
                                f"active Transaction #{dup_quot.TransanctionId} ({dup_quot.InwardNo})."
                            ),
                        )

                if payload.proposal_trans_id is not None:
                    dup_prop = await self.repo.get_active_by_proposal_id(
                        payload.proposal_trans_id
                    )
                    if dup_prop is not None:
                        raise HTTPException(
                            status_code=status.HTTP_409_CONFLICT,
                            detail=(
                                f"Staged Proposal #{payload.proposal_trans_id} has already been booked "
                                f"under Transaction #{dup_prop.TransanctionId} ({dup_prop.InwardNo})."
                            ),
                        )

                # 5b. Allocate concurrency-safe InwardNo
                tx_date = payload.trans_date or date.today()
                inward_no, financial_year = await self.repo.allocate_inward_no(
                    branch_id=eff_branch_id,
                    target_date=tx_date,
                )

                now_dt = datetime.utcnow()
                trans_dt = datetime.combine(tx_date, datetime.min.time())
                cn_dt = (
                    datetime.combine(payload.cn_issue_date, datetime.min.time())
                    if payload.cn_issue_date
                    else trans_dt
                )
                risk_dt = datetime.combine(payload.risk_start_date, datetime.min.time())
                exp_date = payload.expiry_date or (
                    payload.risk_start_date + timedelta(days=364)
                )
                exp_dt = datetime.combine(exp_date, datetime.min.time())

                t_status = "Booked" if pay_summary.is_complete_payment == 1 else "Pending"
                pending_status = 0 if pay_summary.is_complete_payment == 1 else 1
                has_cheque = any(p.payment_type in {"CHEQUE", "DD"} for p in payload.payments)

                # 5c. Insert tbl_transaction
                tx_row = Transaction(
                    InwardNo=inward_no,
                    TransDate=trans_dt,
                    BranchId=eff_branch_id,
                    PolicyTypeId=payload.policy_type_id,
                    CustomerId=customer.CustomerId,
                    CustVehId=vehicle.CustVehId,
                    InsuranceCompanyId=payload.insurance_company_id,
                    PolicyNo=payload.policy_no.strip() if payload.policy_no else None,
                    CnIssueDate=cn_dt,
                    PolicyModeId=payload.policy_mode_id,
                    Lead_No=payload.lead_no,
                    ProductTypeId=payload.product_type_id,
                    BusinessTypeId=payload.business_type_id,
                    AgentId=comm_summary.agent_id,
                    SalesEx_id=comm_summary.sales_ex_id,
                    RiskStartdate=risk_dt,
                    ExpiryDate=exp_dt,
                    SumInsured=premium_summary.sum_insured_idv,
                    GVW=str(premium_summary.gvw),
                    Imt23=str(premium_summary.imt23_amount),
                    IMT47="0.00",
                    AddOn=str(premium_summary.addon_premium),
                    TowingChargesAmt=premium_summary.towing_amount,
                    NCB=premium_summary.ncb_percent,
                    NCBPermium=premium_summary.ncb_amount,
                    ODDiscount=premium_summary.od_discount_percent,
                    ODPermium=premium_summary.od_premium,
                    TPPermium=premium_summary.tp_premium,
                    NetPermium=premium_summary.net_premium,
                    ProPosalAmt=premium_summary.final_premium,
                    Remark=payload.remark,
                    AgentComm=comm_summary.headline_agent_comm_percent,
                    AgentCommAmt=comm_summary.total_gross_commission,
                    TdsAmt=comm_summary.total_tds_amount,
                    NetCommission=comm_summary.total_net_commission,
                    Amount=premium_summary.final_premium,
                    TStatus=t_status,
                    PaidAmount=pay_summary.paid_amount,
                    OutstandingAmount=pay_summary.outstanding_amount,
                    CommissionPaid=1 if payload.cutnpay_enabled else 0,
                    pendingStatus=pending_status,
                    QuatationCode=quotation_code,
                    isdeleted="0",
                    CreateDate=now_dt,
                    CreateUser=str(current_user.UserId),
                    UpdateDate=now_dt,
                    UpdateUser=str(current_user.UserId),
                    AgentComm_OD=comm_summary.agent_comm_od_percent,
                    AgentCommAmt_OD=comm_summary.agent_comm_od_amount,
                    TdsAmt_OD=comm_summary.tds_od_amount,
                    NetCommission_OD=comm_summary.net_comm_od_amount,
                    AgentComm_Net=comm_summary.agent_comm_net_percent,
                    AgentCommAmt_Net=comm_summary.agent_comm_net_amount,
                    TdsAmt_Net=comm_summary.tds_net_amount,
                    NetCommission_Net=comm_summary.net_comm_net_amount,
                    AgentComm_Extra=comm_summary.agent_comm_extra_percent,
                    AgentCommAmt_Extra=comm_summary.agent_comm_extra_amount,
                    TdsAmt_Extra=comm_summary.tds_extra_amount,
                    NetCommission_Extra=comm_summary.net_comm_extra_amount,
                    PACovertoOwner=premium_summary.pa_owner_driver,
                    PACoverDriverCleaner=premium_summary.pa_driver_cleaner,
                    LegalLiabilitytoPaidDriver=premium_summary.ll_paid_driver,
                    CommProcessSubmit=0,
                    IsRecalculate=0,
                    MotorOrNonMotor=payload.motor_or_non_motor,
                    InsuranceTypeId=1,
                    InsuranceSubTypeId=1,
                    TypeOfSubType=1,
                    AddOnRate=premium_summary.addon_rate_percent,
                    OnlinePaymentToCompany=int(round_rupee(pay_summary.online_payment_to_company)),
                    GridAgentId=comm_summary.agent_id,
                    PremiumCashToBank=0,
                    CreatedSystem="FASTAPI",
                    CreatedIP="127.0.0.1",
                    UpdatedSystem="FASTAPI",
                    UpdatedIP="127.0.0.1",
                    PortalId="DIRECT",
                    FranchiseCode=str(comm_summary.franchise_id),
                    SelfDiscount=payload.commission.self_discount,
                    IntensiveAmount=payload.commission.incentive_amount,
                    LocationHeadId=comm_summary.location_head_id,
                    Ischequeclearing=1 if has_cheque else 0,
                    IsChequeCleared=0 if has_cheque else 1,
                    IsCompanyChequeNo=0,
                    IsActivePendingCash=1 if pending_status == 1 else 0,
                    tdsPercent=comm_summary.tds_percent,
                    FinancialYear=financial_year,
                    PaymentDate=now_dt if pay_summary.paid_amount > ZERO else None,
                    CashBackStatus=0,
                    CashBackAmt=ZERO,
                    CutNPay=pay_summary.cutnpay_deduction,
                    ChequeBankStatus=0,
                    IncentiveStatus=0,
                    DeuDate=exp_dt,
                    UpdateEntryStatus=0,
                    ExectiveGrid=ZERO,
                    EWalletAmountUsed=pay_summary.ewallet_amount_used,
                    PolicycancelId=0,
                    FranchiseCommPaid=0,
                    IsRconDataMatch=0,
                    TransId=payload.proposal_trans_id or 0,
                    RconGrid=ZERO,
                    RconComm=ZERO,
                    IsQualityCheck=0 if (payload.insurance_company_id in {3, 32} and payload.policy_type_id > 18) else 1,
                    QualityCheckDate=now_dt,
                    ND="YES" if premium_summary.is_nill_dep else "NO",
                    FranchiseTypeId=1 if comm_summary.franchise_id > 0 else 0,
                    NCBPer=premium_summary.ncb_percent,
                    PaymentRequest=(
                        f"IDEMP:{payload.idempotency_key.strip()}"
                        if payload.idempotency_key
                        else None
                    ),
                    RAPaymentStatus="COMPLETE" if pending_status == 0 else "PENDING",
                    GST_Amount=premium_summary.gst_amount,
                    RoadSidePremium=premium_summary.rsa_amount,
                )
                await self.repo.create_transaction(tx_row)

                if payload.simulate_failure_at == "AFTER_TRANSACTION":
                    raise RuntimeError("Simulated fault AFTER_TRANSACTION for rollback verification")

                # 5d. Execute Partner E-Wallet lock consumption / debit if explicitly requested
                if pay_summary.ewallet_amount_used > ZERO and (
                    payload.wallet_owner_id is not None or payload.wallet_lock_id is not None
                ):
                    w_owner_type = payload.wallet_owner_type or (
                        "FRANCHISE"
                        if (comm_summary.franchise_id > 0 and comm_summary.agent_id == 0)
                        else "AGENT"
                    )
                    w_owner_id = payload.wallet_owner_id or (
                        comm_summary.franchise_id
                        if w_owner_type == "FRANCHISE"
                        else comm_summary.agent_id
                    )
                    await self.wallet_service.consume_or_debit_in_session(
                        owner_type=w_owner_type,
                        owner_id=w_owner_id,
                        amount=pay_summary.ewallet_amount_used,
                        branch_id=eff_branch_id,
                        actor_user_id=current_user.UserId,
                        transaction_id=tx_row.TransanctionId,
                        proposal_trans_id=payload.proposal_trans_id or 0,
                        lock_account_id=payload.wallet_lock_id,
                        narration=f"E-Wallet Debit for Policy Booking {inward_no}",
                    )

                # 5d-2. Insert tbl_transactionpayment rows
                persisted_payments: List[PaymentInstrumentResponse] = []
                for p_in in payload.payments:
                    p_dt = (
                        datetime.combine(p_in.payment_date, datetime.min.time())
                        if p_in.payment_date
                        else now_dt
                    )
                    init_status, cash_app = evaluate_payment_instrument_state(p_in.payment_type)
                    if p_in.payment_type == "EWALLET" and (
                        p_in.wallet_owner_id is not None or p_in.wallet_lock_id is not None
                    ):
                        pw_type = p_in.wallet_owner_type or (
                            "FRANCHISE"
                            if (comm_summary.franchise_id > 0 and comm_summary.agent_id == 0)
                            else "AGENT"
                        )
                        pw_id = p_in.wallet_owner_id or (
                            comm_summary.franchise_id
                            if pw_type == "FRANCHISE"
                            else comm_summary.agent_id
                        )
                        await self.wallet_service.consume_or_debit_in_session(
                            owner_type=pw_type,
                            owner_id=pw_id,
                            amount=round_2dp(p_in.paid_amount),
                            branch_id=eff_branch_id,
                            actor_user_id=current_user.UserId,
                            transaction_id=tx_row.TransanctionId,
                            proposal_trans_id=payload.proposal_trans_id or 0,
                            lock_account_id=p_in.wallet_lock_id,
                            narration=f"E-Wallet Instrument Debit for Policy Booking {inward_no}",
                            idempotency_key=p_in.idempotency_key,
                        )
                        tx_row.EWalletAmountUsed = round_2dp(
                            _to_decimal(tx_row.EWalletAmountUsed) + round_2dp(p_in.paid_amount)
                        )

                    p_row = TransactionPayment(
                        PaymentDate=p_dt,
                        PaymentType=p_in.payment_type,
                        PaymentDetails=p_in.payment_details or f"Policy Booking {inward_no}",
                        bankname=p_in.bankname,
                        docno=p_in.docno,
                        PaidAmount=round_2dp(p_in.paid_amount),
                        CashierApproval=cash_app,
                        CashierApprovalDate=now_dt if cash_app == 1 else None,
                        AccountantApproval=0,
                        OwnerApproval=0,
                        BranchId=eff_branch_id,
                        TransanctionId=tx_row.TransanctionId,
                        Extra1=init_status,
                        Extra2=(
                            f"IDEMP:{p_in.idempotency_key.strip()}"
                            if p_in.idempotency_key
                            else None
                        ),
                        isdeleted="0",
                        CreateUser=str(current_user.UserId),
                        CreateDate=now_dt,
                        UpdateDate=now_dt,
                        UpdateUser=str(current_user.UserId),
                        isCompletePayment=pay_summary.is_complete_payment,
                    )
                    await self.repo.create_payment(p_row)
                    persisted_payments.append(map_payment_instrument_response(p_row))
                pay_summary.payments = persisted_payments


                if payload.simulate_failure_at == "AFTER_PAYMENT":
                    raise RuntimeError("Simulated fault AFTER_PAYMENT for rollback verification")

                # 5e. Insert Downstream Commission Rows
                if comm_summary.franchise_id > 0:
                    fc_row = FranchiseCommission(
                        FranchiseDate=now_dt,
                        TransanctionId=tx_row.TransanctionId,
                        FranchiseId=comm_summary.franchise_id,
                        AgentId=comm_summary.agent_id,
                        tat=ZERO,
                        Franchisecomm=comm_summary.headline_agent_comm_percent,
                        FranchiseCommAmt=comm_summary.franchise_gross_commission,
                        FranchiseTdsAmt=comm_summary.franchise_tds_amount,
                        FranchiseNetComm=comm_summary.franchise_net_commission,
                        FCommissionPaid=ZERO,
                        isdeleted=0,
                        Franchisecomm_OD=comm_summary.agent_comm_od_percent,
                        FranchiseCommAmt_OD=comm_summary.agent_comm_od_amount,
                        FranchiseTdsAmt_OD=comm_summary.tds_od_amount,
                        FranchiseNetComm_OD=comm_summary.net_comm_od_amount,
                        Franchisecomm_Net=comm_summary.agent_comm_net_percent,
                        FranchiseCommAmt_Net=comm_summary.agent_comm_net_amount,
                        FranchiseTdsAmt_Net=comm_summary.tds_net_amount,
                        FranchiseNetComm_Net=comm_summary.net_comm_net_amount,
                        Franchisecomm_Extra=comm_summary.agent_comm_extra_percent,
                        FranchiseCommAmt_Extra=comm_summary.agent_comm_extra_amount,
                        FranchiseTdsAmt_Extra=comm_summary.tds_extra_amount,
                        FranchiseNetComm_Extra=comm_summary.net_comm_extra_amount,
                        ProfitofNetCommision=round_2dp(
                            comm_summary.franchise_net_commission - comm_summary.total_net_commission
                        ),
                        GridValidDate=now_dt,
                        BrokerId=0,
                        SelfDiscount=payload.commission.self_discount,
                        IntensiveAmount=payload.commission.incentive_amount,
                    )
                    await self.repo.create_franchise_commission(fc_row)
                    comm_summary.franchise_comm_id = fc_row.FranchiseCommId

                if payload.cutnpay_enabled:
                    cnp_row = CutNPayCommPayable(
                        TransactionId=tx_row.TransanctionId,
                        PolicyNo=tx_row.PolicyNo or inward_no,
                        CustomerId=customer.CustomerId,
                        AgentId=comm_summary.agent_id,
                        SalesExId=comm_summary.sales_ex_id,
                        Balance=round_2dp(
                            comm_summary.total_net_commission - pay_summary.cutnpay_deduction
                        ),
                        CommPayable=pay_summary.cutnpay_deduction,
                        Flag="CUTNPAY",
                        Isdeleted=0,
                        CreatedDate=now_dt,
                    )
                    await self.repo.create_cutnpay_payable(cnp_row)
                    comm_summary.cutnpay_payable_id = cnp_row.CutNPayCommPayId

                if comm_summary.agent_id > 0 and comm_summary.total_net_commission > ZERO:
                    acp_row = AgentCommissionPayment(
                        FromDate=now_dt,
                        ToDate=now_dt,
                        TransanctionId=tx_row.TransanctionId,
                        BranchName=f"BRANCH-{eff_branch_id}",
                        AgentName=f"AGENT-{comm_summary.agent_id}",
                        PremiumAmount=premium_summary.net_premium,
                        NetCommission=comm_summary.total_net_commission,
                        totalCommision=comm_summary.total_gross_commission,
                        AdvAmt=pay_summary.cutnpay_deduction,
                        NetAmount=round_2dp(
                            comm_summary.total_net_commission - pay_summary.cutnpay_deduction
                        ),
                        PaymentStatus=Decimal("1.00") if payload.cutnpay_enabled else ZERO,
                        Narration=f"Policy Booking {inward_no}",
                        Extra1=str(comm_summary.agent_id),
                        Extra2=str(comm_summary.total_tds_amount),
                        isdeleted="0",
                        NetCommission_OD=comm_summary.net_comm_od_amount,
                        NetCommission_Net=comm_summary.net_comm_net_amount,
                        NetCommission_Extra=comm_summary.net_comm_extra_amount,
                        TransDate=now_dt,
                    )
                    await self.repo.create_agent_commission_payment(acp_row)
                    comm_summary.agent_comm_pay_id = acp_row.AgentCommId

                if payload.simulate_failure_at == "AFTER_COMMISSION":
                    raise RuntimeError("Simulated fault AFTER_COMMISSION for rollback verification")

                # 5f. Insert Double-Entry Accounting Rows in tbl_account (AccTransId = 1, 2, 3)
                ledger_m_id = await self.repo.resolve_or_create_policy_ledger(
                    branch_id=eff_branch_id,
                    actor_user_id=current_user.UserId,
                )
                planned_entries = self.build_accounting_entries(
                    premium=premium_summary,
                    commission=comm_summary,
                    payment=pay_summary,
                    branch_id=eff_branch_id,
                    ledger_m_id=ledger_m_id,
                    customer_id=customer.CustomerId,
                    cust_veh_id=vehicle.CustVehId,
                    transaction_id=tx_row.TransanctionId,
                    inward_no=inward_no,
                )

                persisted_entries: List[AccountingEntryResponse] = []
                for idx, e_plan in enumerate(planned_entries):
                    if payload.simulate_failure_at == "DURING_ACCOUNTING" and idx == len(planned_entries) - 1:
                        raise RuntimeError("Simulated fault DURING_ACCOUNTING for rollback verification")

                    acc_row = Account(
                        AccTransId=e_plan.acc_trans_id,
                        AccountDate=now_dt,
                        LedgerMId=ledger_m_id,
                        amount=e_plan.amount,
                        Narration=e_plan.narration,
                        ReferenceCustId=customer.CustomerId,
                        ReferenceAgentId=comm_summary.agent_id,
                        BranchId=eff_branch_id,
                        Extra1=e_plan.transaction_type,
                        Extra2=inward_no,
                        Doc_No=tx_row.TransanctionId,
                        CreatedUser=str(current_user.UserId),
                        CreatedDate=now_dt,
                        UpdatedUser=str(current_user.UserId),
                        UpdatedDate=now_dt,
                        PaymentType=e_plan.payment_type,
                        isdeleted=0,
                        IsNill=e_plan.is_nill,
                        TransactionId=tx_row.TransanctionId,
                        CustVehId=vehicle.CustVehId,
                        MonthId=tx_date.month,
                        EndorsementId=0,
                        TransId=payload.proposal_trans_id or 0,
                    )
                    await self.repo.create_account_entry(acc_row)
                    e_plan.account_id = acc_row.AccountId
                    persisted_entries.append(e_plan)

                # 5g. Mark staged proposal as submitted if linked
                if staged_proposal is not None:
                    staged_proposal.IsSubmit = 1
                    staged_proposal.UpdatedDate = now_dt
                    staged_proposal.UpdatedUser = str(current_user.UserId)
                    await self.session.flush()

                # 5h. Commit single atomic transaction
                await self.session.commit()

            except HTTPException:
                await self.session.rollback()
                raise
            except Exception as exc:
                await self.session.rollback()
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Atomic policy booking rolled back due to downstream failure: {exc}",
                ) from exc

        return PolicyBookingResponse(
            transaction_id=tx_row.TransanctionId,
            inward_no=inward_no,
            trans_date=trans_dt,
            branch_id=eff_branch_id,
            financial_year=financial_year,
            customer_id=customer.CustomerId,
            cust_veh_id=vehicle.CustVehId,
            insurance_company_id=payload.insurance_company_id,
            policy_type_id=payload.policy_type_id,
            product_type_id=payload.product_type_id,
            business_type_id=payload.business_type_id,
            policy_no=tx_row.PolicyNo,
            cn_issue_date=cn_dt,
            risk_start_date=risk_dt,
            expiry_date=exp_dt,
            due_date=exp_dt,
            quotation_code=quotation_code,
            proposal_trans_id=payload.proposal_trans_id or 0,
            t_status=t_status,
            pending_status=pending_status,
            isdeleted="0",
            remark=tx_row.Remark,
            premium_summary=premium_summary,
            commission_summary=comm_summary,
            payment_summary=pay_summary,
            accounting_entries=persisted_entries,
        )

    # -----------------------------------------------------------------------
    # 8. Reconstruct PolicyBookingResponse from Persisted DB Rows
    # -----------------------------------------------------------------------

    async def _build_policy_response(self, tx: Transaction) -> PolicyBookingResponse:
        payments_db = await self.repo.get_payments_by_transaction_id(tx.TransanctionId)
        fc_rows = await self.repo.get_franchise_commissions_by_tx(tx.TransanctionId)
        cnp_rows = await self.repo.get_cutnpay_by_tx(tx.TransanctionId)
        acp_rows = await self.repo.get_agent_comm_payments_by_tx(tx.TransanctionId)
        acc_rows = await self.repo.get_account_entries_by_tx(tx.TransanctionId)

        od_prem = round_2dp(_to_decimal(tx.ODPermium))
        tp_prem = round_2dp(_to_decimal(tx.TPPermium))
        net_prem = round_2dp(_to_decimal(tx.NetPermium))
        gst_amt = round_2dp(_to_decimal(tx.GST_Amount))
        final_prem = round_2dp(_to_decimal(tx.Amount))
        pa_owner = round_2dp(_to_decimal(tx.PACovertoOwner))
        pa_cleaner = round_2dp(_to_decimal(tx.PACoverDriverCleaner))
        ll_driver = round_2dp(_to_decimal(tx.LegalLiabilitytoPaidDriver))

        premium_summary = PolicyPremiumSummary(
            sum_insured_idv=round_2dp(_to_decimal(tx.SumInsured)),
            gvw=round_2dp(_to_decimal(tx.GVW)),
            od_premium=od_prem,
            tp_premium=tp_prem,
            basic_tp_premium=max(ZERO, round_2dp(tp_prem - pa_owner - pa_cleaner - ll_driver)),
            net_premium=net_prem,
            gst_amount=gst_amt,
            final_premium=final_prem,
            ncb_percent=round_2dp(_to_decimal(tx.NCB)),
            ncb_amount=round_2dp(_to_decimal(tx.NCBPermium)),
            od_discount_percent=round_2dp(_to_decimal(tx.ODDiscount)),
            od_discount_amount=ZERO,
            addon_rate_percent=round_2dp(_to_decimal(tx.AddOnRate)),
            addon_premium=round_2dp(_to_decimal(tx.AddOn)),
            is_nill_dep=(tx.ND == "YES"),
            imt23_amount=round_2dp(_to_decimal(tx.Imt23)),
            towing_amount=round_2dp(_to_decimal(tx.TowingChargesAmt)),
            rsa_amount=round_2dp(_to_decimal(tx.RoadSidePremium)),
            pa_owner_driver=pa_owner,
            pa_driver_cleaner=pa_cleaner,
            ll_paid_driver=ll_driver,
        )

        fc_first = fc_rows[0] if fc_rows else None
        cnp_first = cnp_rows[0] if cnp_rows else None
        acp_first = acp_rows[0] if acp_rows else None
        frn_id = int(tx.FranchiseCode) if (tx.FranchiseCode and tx.FranchiseCode.isdigit()) else 0

        comm_summary = PolicyCommissionSummary(
            agent_id=tx.AgentId or 0,
            sales_ex_id=tx.SalesEx_id or 0,
            franchise_id=frn_id,
            location_head_id=tx.LocationHeadId or 0,
            od_commission_base=od_prem,
            agent_comm_od_percent=round_2dp(_to_decimal(tx.AgentComm_OD)),
            agent_comm_od_amount=round_2dp(_to_decimal(tx.AgentCommAmt_OD)),
            tds_od_amount=round_2dp(_to_decimal(tx.TdsAmt_OD)),
            net_comm_od_amount=round_2dp(_to_decimal(tx.NetCommission_OD)),
            net_commission_base=tp_prem,
            agent_comm_net_percent=round_2dp(_to_decimal(tx.AgentComm_Net)),
            agent_comm_net_amount=round_2dp(_to_decimal(tx.AgentCommAmt_Net)),
            tds_net_amount=round_2dp(_to_decimal(tx.TdsAmt_Net)),
            net_comm_net_amount=round_2dp(_to_decimal(tx.NetCommission_Net)),
            extra_commission_base=od_prem,
            agent_comm_extra_percent=round_2dp(_to_decimal(tx.AgentComm_Extra)),
            agent_comm_extra_amount=round_2dp(_to_decimal(tx.AgentCommAmt_Extra)),
            tds_extra_amount=round_2dp(_to_decimal(tx.TdsAmt_Extra)),
            net_comm_extra_amount=round_2dp(_to_decimal(tx.NetCommission_Extra)),
            headline_agent_comm_percent=round_2dp(_to_decimal(tx.AgentComm)),
            total_gross_commission=round_2dp(_to_decimal(tx.AgentCommAmt)),
            tds_percent=round_2dp(_to_decimal(tx.tdsPercent)),
            total_tds_amount=round_2dp(_to_decimal(tx.TdsAmt)),
            total_net_commission=round_2dp(_to_decimal(tx.NetCommission)),
            franchise_comm_id=fc_first.FranchiseCommId if fc_first else None,
            franchise_gross_commission=round_2dp(_to_decimal(fc_first.FranchiseCommAmt)) if fc_first else ZERO,
            franchise_tds_amount=round_2dp(_to_decimal(fc_first.FranchiseTdsAmt)) if fc_first else ZERO,
            franchise_net_commission=round_2dp(_to_decimal(fc_first.FranchiseNetComm)) if fc_first else ZERO,
            cutnpay_payable_id=cnp_first.CutNPayCommPayId if cnp_first else None,
            agent_comm_pay_id=acp_first.AgentCommId if acp_first else None,
        )

        pay_items = [map_payment_instrument_response(p) for p in payments_db]
        inst_paid = round_2dp(sum((i.paid_amount for i in pay_items), ZERO))

        cnp_deduction = round_2dp(_to_decimal(tx.CutNPay))
        ewallet_used = round_2dp(_to_decimal(tx.EWalletAmountUsed))
        online_co = round_2dp(Decimal(str(tx.OnlinePaymentToCompany or 0)))
        req_payable = round_2dp(max(ZERO, final_prem - cnp_deduction))
        paid_amt = round_2dp(_to_decimal(tx.PaidAmount))
        out_amt = round_2dp(_to_decimal(tx.OutstandingAmount))

        pay_summary = PolicyPaymentSummary(
            gross_payable_amount=final_prem,
            cutnpay_enabled=bool(cnp_deduction > ZERO or cnp_first is not None),
            cutnpay_deduction=cnp_deduction,
            ewallet_amount_used=ewallet_used,
            online_payment_to_company=online_co,
            required_payable_amount=req_payable,
            instrument_paid_amount=inst_paid,
            paid_amount=paid_amt,
            outstanding_amount=out_amt,
            is_complete_payment=1 if out_amt == ZERO else 0,
            payments=pay_items,
        )

        acct_items = [
            AccountingEntryResponse(
                account_id=a.AccountId,
                acc_trans_id=a.AccTransId or 0,
                transaction_type=a.Extra1 or "POLICY_ENTRY",
                ledger_m_id=a.LedgerMId or 1,
                amount=round_2dp(_to_decimal(a.amount)),
                narration=a.Narration or "",
                reference_cust_id=a.ReferenceCustId,
                reference_agent_id=a.ReferenceAgentId,
                branch_id=a.BranchId or (tx.BranchId or 1),
                payment_type=a.PaymentType,
                transaction_id=a.TransactionId,
                cust_veh_id=a.CustVehId,
                is_nill=a.IsNill,
                isdeleted=a.isdeleted or 0,
            )
            for a in acc_rows
        ]

        return PolicyBookingResponse(
            transaction_id=tx.TransanctionId,
            inward_no=tx.InwardNo or "",
            trans_date=tx.TransDate or datetime.utcnow(),
            branch_id=tx.BranchId or 1,
            financial_year=tx.FinancialYear or "2026-2027",
            customer_id=tx.CustomerId or 0,
            cust_veh_id=tx.CustVehId or 0,
            insurance_company_id=tx.InsuranceCompanyId or 1,
            policy_type_id=tx.PolicyTypeId or 1,
            product_type_id=tx.ProductTypeId or 1,
            business_type_id=tx.BusinessTypeId or 3,
            policy_no=tx.PolicyNo,
            cn_issue_date=tx.CnIssueDate,
            risk_start_date=tx.RiskStartdate,
            expiry_date=tx.ExpiryDate,
            due_date=tx.DeuDate,
            quotation_code=tx.QuatationCode,
            proposal_trans_id=tx.TransId or 0,
            t_status=tx.TStatus or "Booked",
            pending_status=tx.pendingStatus if tx.pendingStatus is not None else 0,
            isdeleted=tx.isdeleted or "0",
            remark=tx.Remark,
            premium_summary=premium_summary,
            commission_summary=comm_summary,
            payment_summary=pay_summary,
            accounting_entries=acct_items,
        )

    # -----------------------------------------------------------------------
    # 9. Policy Read, List, Update, Subsequent Payment & Cancel
    # -----------------------------------------------------------------------

    async def get_policy(
        self,
        transaction_id: int,
        current_user: User,
    ) -> PolicyBookingResponse:
        tx = await self.repo.get_transaction_by_id(transaction_id, include_deleted=False)
        if tx is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Policy Transaction #{transaction_id} not found.",
            )
        self._assert_can_access_transaction(tx, current_user, for_write=False)
        return await self._build_policy_response(tx)

    async def list_policies(
        self,
        current_user: User,
        *,
        customer_id: Optional[int] = None,
        cust_veh_id: Optional[int] = None,
        policy_no: Optional[str] = None,
        inward_no: Optional[str] = None,
        quotation_code: Optional[str] = None,
        t_status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> PolicyBookingListResponse:
        ctx = self._get_principal(current_user)
        norm_role = _normalize(ctx.role_name)

        branch_filter: Optional[int] = None
        agent_filter: Optional[int] = None
        sales_filter: Optional[int] = None
        frn_filter: Optional[str] = None

        if not is_global_admin_role(ctx.role_name) and not self._is_cross_branch_read_role(ctx.role_name):
            branch_filter = ctx.branch_id or 1
            if norm_role in _AGENT_ROLES_NORM:
                agent_filter = ctx.agent_id or ctx.user_id
            elif norm_role in _FRANCHISE_ROLES_NORM:
                frn_filter = str(ctx.franchise_id or ctx.user_id)
            elif norm_role in _EMPLOYEE_ROLES_NORM:
                sales_filter = ctx.emp_id or ctx.user_id

        total, rows = await self.repo.list_transactions(
            branch_id=branch_filter,
            agent_id=agent_filter,
            sales_ex_id=sales_filter,
            franchise_code=frn_filter,
            customer_id=customer_id,
            cust_veh_id=cust_veh_id,
            policy_no=policy_no,
            inward_no=inward_no,
            quotation_code=quotation_code,
            t_status=t_status,
            limit=limit,
            offset=offset,
        )
        items = [await self._build_policy_response(r) for r in rows]
        return PolicyBookingListResponse(
            total=total,
            limit=limit,
            offset=offset,
            items=items,
        )

    async def update_policy(
        self,
        transaction_id: int,
        payload: PolicyBookingUpdateRequest,
        current_user: User,
    ) -> PolicyBookingResponse:
        tx = await self.repo.get_transaction_by_id(transaction_id, include_deleted=False)
        if tx is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Policy Transaction #{transaction_id} not found.",
            )
        self._assert_can_access_transaction(tx, current_user, for_write=True)

        async with _BOOKING_WRITE_LOCK:
            try:
                if payload.policy_no is not None and payload.policy_no.strip() != (tx.PolicyNo or ""):
                    dup = await self.repo.get_active_by_policy_no(
                        policy_no=payload.policy_no,
                        insurance_company_id=tx.InsuranceCompanyId or 1,
                    )
                    if dup is not None and dup.TransanctionId != tx.TransanctionId:
                        raise HTTPException(
                            status_code=status.HTTP_409_CONFLICT,
                            detail=(
                                f"PolicyNo '{payload.policy_no}' is already assigned to "
                                f"Transaction #{dup.TransanctionId}."
                            ),
                        )
                    tx.PolicyNo = payload.policy_no.strip()

                if payload.cn_issue_date is not None:
                    tx.CnIssueDate = datetime.combine(payload.cn_issue_date, datetime.min.time())
                if payload.risk_start_date is not None:
                    tx.RiskStartdate = datetime.combine(payload.risk_start_date, datetime.min.time())
                if payload.expiry_date is not None:
                    exp_dt = datetime.combine(payload.expiry_date, datetime.min.time())
                    tx.ExpiryDate = exp_dt
                    tx.DeuDate = exp_dt
                if payload.t_status is not None:
                    tx.TStatus = payload.t_status.strip()
                if payload.remark is not None:
                    tx.Remark = payload.remark

                tx.UpdateDate = datetime.utcnow()
                tx.UpdateUser = str(current_user.UserId)
                tx.UpdateEntryStatus = 1

                await self.session.commit()
            except HTTPException:
                await self.session.rollback()
                raise
            except Exception as exc:
                await self.session.rollback()
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to update Policy Transaction #{transaction_id}: {exc}",
                ) from exc

        return await self._build_policy_response(tx)

    async def record_payment(
        self,
        transaction_id: int,
        payload: PaymentInstrumentCreateRequest,
        current_user: User,
    ) -> PolicyBookingResponse:
        """
        Records an additional payment instrument against an existing policy transaction
        and atomically updates PaidAmount, OutstandingAmount, and tbl_account (AccTransId = 2).
        """
        tx = await self.repo.get_transaction_by_id(transaction_id, include_deleted=False)
        if tx is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Policy Transaction #{transaction_id} not found.",
            )
        self._assert_can_access_transaction(tx, current_user, for_write=True)

        current_outstanding = round_2dp(_to_decimal(tx.OutstandingAmount))
        add_amount = round_2dp(payload.paid_amount)
        if add_amount <= ZERO:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Additional payment paid_amount must be greater than 0.00.",
            )
        if add_amount > current_outstanding:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"Overpayment rejected: payment amount ({add_amount}) exceeds "
                    f"current outstanding balance ({current_outstanding})."
                ),
            )

        async with _BOOKING_WRITE_LOCK:
            try:
                if payload.idempotency_key:
                    dup_pay = await self.payment_repo.get_active_payment_by_idempotency(
                        transaction_id=tx.TransanctionId,
                        idempotency_key=payload.idempotency_key,
                    )
                    if dup_pay is not None:
                        raise HTTPException(
                            status_code=status.HTTP_409_CONFLICT,
                            detail=(
                                f"Duplicate payment request: idempotency_key '{payload.idempotency_key}' "
                                f"already recorded as Payment #{dup_pay.PaymentId}."
                            ),
                        )

                if payload.payment_type in {"CHEQUE", "DD"} and payload.docno and payload.bankname:
                    dup_chq = await self.payment_repo.get_active_cheque_duplicate(
                        transaction_id=tx.TransanctionId,
                        docno=payload.docno,
                        bankname=payload.bankname,
                    )
                    if dup_chq is not None:
                        raise HTTPException(
                            status_code=status.HTTP_409_CONFLICT,
                            detail=(
                                f"Duplicate active {payload.payment_type}: docno '{payload.docno}' "
                                f"from bank '{payload.bankname}' is already recorded on Policy #{tx.TransanctionId}."
                            ),
                        )

                now_dt = datetime.utcnow()
                new_paid = round_2dp(_to_decimal(tx.PaidAmount) + add_amount)
                new_outstanding = round_2dp(current_outstanding - add_amount)
                is_complete = 1 if new_outstanding == ZERO else 0
                is_cheque_like = payload.payment_type in {"CHEQUE", "DD"}

                tx.PaidAmount = new_paid
                tx.OutstandingAmount = new_outstanding
                if is_cheque_like:
                    tx.Ischequeclearing = 1
                    tx.IsChequeCleared = 0
                    tx.ChequeBankStatus = 0
                if is_complete == 1:
                    tx.TStatus = "Booked"
                    tx.pendingStatus = 0
                    tx.RAPaymentStatus = "COMPLETE"
                    tx.IsActivePendingCash = 0
                    if (tx.Ischequeclearing or 0) == 0:
                        if tx.ChequeBankStatus == 2:
                            tx.ChequeBankStatus = 0
                        cnp_rows = await self.repo.get_cutnpay_by_tx(tx.TransanctionId)
                        for cnp in cnp_rows:
                            if (cnp.Flag or "").upper().startswith("HOLD"):
                                cnp.Flag = "CUTNPAY"
                        acp_rows = await self.repo.get_agent_comm_payments_by_tx(tx.TransanctionId)
                        for acp in acp_rows:
                            if (acp.Narration or "").upper().startswith("HOLD:"):
                                adv_v = round_2dp(_to_decimal(acp.AdvAmt))
                                rem_v = round_2dp(_to_decimal(acp.NetAmount))
                                acp.PaymentStatus = (
                                    Decimal("1.00")
                                    if (adv_v > ZERO and rem_v == ZERO)
                                    else (Decimal("2.00") if adv_v > ZERO else ZERO)
                                )
                                acp.Narration = f"Commission Payable Active - {tx.InwardNo}"[:255]
                if payload.payment_type == "EWALLET":
                    tx.EWalletAmountUsed = round_2dp(
                        _to_decimal(tx.EWalletAmountUsed) + add_amount
                    )
                    if payload.wallet_owner_id is not None or payload.wallet_lock_id is not None:
                        frn_id = (
                            int(tx.FranchiseCode)
                            if (tx.FranchiseCode and tx.FranchiseCode.isdigit())
                            else 0
                        )
                        w_type = payload.wallet_owner_type or (
                            "FRANCHISE" if (frn_id > 0 and not tx.AgentId) else "AGENT"
                        )
                        w_id = payload.wallet_owner_id or (
                            tx.AgentId if w_type == "AGENT" else frn_id
                        )
                        await self.wallet_service.consume_or_debit_in_session(
                            owner_type=w_type,
                            owner_id=w_id or 1,
                            amount=add_amount,
                            branch_id=tx.BranchId or 1,
                            actor_user_id=current_user.UserId,
                            transaction_id=tx.TransanctionId,
                            proposal_trans_id=tx.TransId or 0,
                            lock_account_id=payload.wallet_lock_id,
                            narration=f"Subsequent E-Wallet Payment for {tx.InwardNo}",
                            idempotency_key=payload.idempotency_key,
                        )

                tx.UpdateDate = now_dt
                tx.UpdateUser = str(current_user.UserId)

                p_dt = (
                    datetime.combine(payload.payment_date, datetime.min.time())
                    if payload.payment_date
                    else now_dt
                )
                init_status, cash_app = evaluate_payment_instrument_state(payload.payment_type)
                p_row = TransactionPayment(
                    PaymentDate=p_dt,
                    PaymentType=payload.payment_type,
                    PaymentDetails=payload.payment_details or f"Subsequent Payment {tx.InwardNo}",
                    bankname=payload.bankname,
                    docno=payload.docno,
                    PaidAmount=add_amount,
                    CashierApproval=cash_app,
                    CashierApprovalDate=now_dt if cash_app == 1 else None,
                    AccountantApproval=0,
                    OwnerApproval=0,
                    BranchId=tx.BranchId or 1,
                    TransanctionId=tx.TransanctionId,
                    Extra1=init_status,
                    Extra2=(
                        f"IDEMP:{payload.idempotency_key.strip()}"
                        if payload.idempotency_key
                        else None
                    ),
                    isdeleted="0",
                    CreateUser=str(current_user.UserId),
                    CreateDate=now_dt,
                    UpdateDate=now_dt,
                    UpdateUser=str(current_user.UserId),
                    isCompletePayment=is_complete,
                )
                await self.repo.create_payment(p_row)

                if payload.simulate_failure_at == "AFTER_PAYMENT_INSERT":
                    raise RuntimeError("Simulated fault AFTER_PAYMENT_INSERT in record_payment")

                ledger_m_id = await self.repo.resolve_or_create_policy_ledger(
                    branch_id=tx.BranchId or 1,
                    actor_user_id=current_user.UserId,
                )
                acc_row = Account(
                    AccTransId=2,
                    AccountDate=now_dt,
                    LedgerMId=ledger_m_id,
                    amount=add_amount,
                    Narration=f"Subsequent Policy Payment Receipt - {tx.InwardNo}",
                    ReferenceCustId=tx.CustomerId,
                    ReferenceAgentId=tx.AgentId,
                    BranchId=tx.BranchId or 1,
                    Extra1="POLICY_PAYMENT",
                    Extra2=tx.InwardNo,
                    Doc_No=tx.TransanctionId,
                    CreatedUser=str(current_user.UserId),
                    CreatedDate=now_dt,
                    UpdatedUser=str(current_user.UserId),
                    UpdatedDate=now_dt,
                    PaymentType=payload.payment_type,
                    isdeleted=0,
                    IsNill=1 if tx.ND == "YES" else 0,
                    TransactionId=tx.TransanctionId,
                    CustVehId=tx.CustVehId or 0,
                    MonthId=now_dt.month,
                    EndorsementId=0,
                    TransId=tx.TransId or 0,
                )
                await self.repo.create_account_entry(acc_row)

                if payload.simulate_failure_at == "BEFORE_LEDGER_COMMIT":
                    raise RuntimeError("Simulated fault BEFORE_LEDGER_COMMIT in record_payment")

                await self.session.commit()
            except HTTPException:
                await self.session.rollback()
                raise
            except Exception as exc:
                await self.session.rollback()
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to record payment on Transaction #{transaction_id}: {exc}",
                ) from exc

        return await self._build_policy_response(tx)


    async def cancel_policy(
        self,
        transaction_id: int,
        payload: PolicyCancelRequest,
        current_user: User,
    ) -> PolicyCancelResponse:
        """
        Soft-deletes a booked policy transaction (sp_DeleteTransactionByTransId parity)
        and atomically marks all associated payment, commission, and accounting rows as deleted.
        """
        tx = await self.repo.get_transaction_by_id(transaction_id, include_deleted=True)
        if tx is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Policy Transaction #{transaction_id} not found.",
            )
        if tx.isdeleted == "1":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Policy Transaction #{transaction_id} is already cancelled.",
            )

        async with _BOOKING_WRITE_LOCK:
            try:
                now_dt = datetime.utcnow()
                tx.isdeleted = "1"
                tx.TStatus = "Cancelled"
                tx.PolicycancelId = payload.policy_cancel_id
                tx.CorrectionText = payload.reason
                if payload.use_legacy_cust_veh_id_500_sentinel:
                    tx.CustVehId = 500
                tx.UpdateDate = now_dt
                tx.UpdateUser = str(current_user.UserId)

                payments = await self.repo.get_payments_by_transaction_id(transaction_id)
                for p in payments:
                    p.isdeleted = "1"
                    p.UpdateDate = now_dt
                    p.UpdateUser = str(current_user.UserId)

                fc_rows = await self.repo.get_franchise_commissions_by_tx(transaction_id)
                for fc in fc_rows:
                    fc.isdeleted = 1

                cnp_rows = await self.repo.get_cutnpay_by_tx(transaction_id)
                for cnp in cnp_rows:
                    cnp.Isdeleted = 1

                acp_rows = await self.repo.get_agent_comm_payments_by_tx(transaction_id)
                for acp in acp_rows:
                    acp.isdeleted = "1"

                acc_rows = await self.repo.get_account_entries_by_tx(transaction_id)
                for acc in acc_rows:
                    acc.isdeleted = 1
                    acc.UpdatedDate = now_dt
                    acc.UpdatedUser = str(current_user.UserId)

                await self.session.commit()
            except Exception as exc:
                await self.session.rollback()
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to cancel Policy Transaction #{transaction_id}: {exc}",
                ) from exc

        return PolicyCancelResponse(
            transaction_id=tx.TransanctionId,
            inward_no=tx.InwardNo or "",
            t_status=tx.TStatus or "Cancelled",
            isdeleted="1",
            cust_veh_id=tx.CustVehId or 0,
            payments_reversed=len(payments),
            accounting_entries_reversed=len(acc_rows),
            franchise_commissions_reversed=len(fc_rows),
            cutnpay_reversed=len(cnp_rows),
            agent_comm_payments_reversed=len(acp_rows),
            reason=payload.reason,
        )

    # -----------------------------------------------------------------------
    # 10. Staged Policy Proposal Workflow (tbl_transactionappnew)
    # -----------------------------------------------------------------------

    @staticmethod
    def _map_proposal_response(row: TransactionAppNew) -> PolicyProposalResponse:
        return PolicyProposalResponse(
            trans_id=row.TransId,
            trans_date=row.TransDate,
            quotation_code=row.QuatationCode,
            quot_type=row.Quot_Type or "DIRECT",
            customer_name=row.Name,
            contact_no=row.ContactNo,
            registration_no=row.RegistrationNo,
            insurance_company=row.insurancecompany,
            product_type=row.ProductType,
            business_type=row.BusinessType,
            policy_mode=row.PolicyMode,
            start_date=row.StartDate,
            expiry_date=row.Expirydate,
            idv_amount=round_2dp(_to_decimal(row.IDV)),
            od_discount_percent=round_2dp(_to_decimal(row.ODDiscount)),
            ncb_percent=round_2dp(_to_decimal(row.NCBPre)),
            ncb_amount=round_2dp(_to_decimal(row.NCB)),
            od_premium=round_2dp(_to_decimal(row.ODPremium)),
            tp_premium=round_2dp(_to_decimal(row.TPPremium)),
            net_premium=round_2dp(_to_decimal(row.NetPremium)),
            final_premium=round_2dp(_to_decimal(row.Premium)),
            cash_paid_amount=round_2dp(_to_decimal(row.CashPaidAmt)),
            cash_short_amount=round_2dp(_to_decimal(row.CashShortAmt)),
            ewallet_used_amount=round_2dp(_to_decimal(row.EWalletUsedamt)),
            outstanding_amount=round_2dp(_to_decimal(row.OutstandingAmt)),
            is_owner_approve=row.IsOwnerApprove or 0,
            is_cashier_approve=row.IsChashierApprove or 0,
            is_account_approval=row.IsAccountApproval or 0,
            is_submit=row.IsSubmit or 0,
            user_id=row.UserId,
            sales_executive_id=row.SalesExecutiveId,
            franchise_id=row.FranchaiseId,
            franchise_code=row.FranchiseCode or "0",
            approved_by=row.ApprovedBy,
            account_remark=row.AccountRemark,
        )

    async def create_proposal(
        self,
        payload: PolicyProposalCreateRequest,
        current_user: User,
    ) -> PolicyProposalResponse:
        """
        Creates a staged mobile/partner policy proposal in tbl_transactionappnew
        (Sp_InsertAppTransctiondetailsNew8 parity).
        """
        ctx = self._get_principal(current_user)
        norm_role = _normalize(ctx.role_name)

        # Enforce mathematical consistency on proposal figures
        expected_net = round_2dp(payload.od_premium + payload.tp_premium)
        if abs(round_2dp(payload.net_premium) - expected_net) > ONE_RUPEE:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"Proposal net_premium ({payload.net_premium}) must equal "
                    f"od_premium ({payload.od_premium}) + tp_premium ({payload.tp_premium})."
                ),
            )

        total_paid = round_2dp(payload.cash_paid_amount + payload.ewallet_used_amount)
        if total_paid > round_2dp(payload.final_premium):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Proposal cash_paid_amount + ewallet_used_amount cannot exceed final_premium.",
            )
        shortfall = round_2dp(max(ZERO, payload.final_premium - total_paid))

        # Resolve principal ownership without trusting spoofed IDs
        if norm_role in _AGENT_ROLES_NORM:
            eff_user_id = ctx.agent_id or ctx.user_id
            eff_sales_id = payload.sales_executive_id or 0
            eff_frn_id = ctx.franchise_id or (payload.franchise_id or 0)
        elif norm_role in _EMPLOYEE_ROLES_NORM:
            eff_user_id = payload.agent_id or ctx.user_id
            eff_sales_id = ctx.emp_id or ctx.user_id
            eff_frn_id = ctx.franchise_id or (payload.franchise_id or 0)
        elif norm_role in _FRANCHISE_ROLES_NORM:
            eff_user_id = payload.agent_id or ctx.user_id
            eff_sales_id = payload.sales_executive_id or 0
            eff_frn_id = ctx.franchise_id or ctx.user_id
        else:
            eff_user_id = payload.agent_id or ctx.user_id
            eff_sales_id = payload.sales_executive_id or (ctx.emp_id or 0)
            eff_frn_id = payload.franchise_id or 0

        q_code = payload.quotation_code
        quot_type = "DIRECT"
        if payload.quotation_id is not None:
            q_src = payload.quotation_source_type or "SELF_QUOTATION"
            prefill = await self.quotation_service.get_policy_prefill(
                quotation_id=payload.quotation_id,
                source_type=q_src,
                current_user=current_user,
                insurance_company_id=payload.insurance_company_id,
            )
            q_code = prefill.quotation_code
            quot_type = "SELFQUO" if q_src == "SELF_QUOTATION" else "ASSISTED"

        now_dt = datetime.utcnow()
        exp_date = payload.expiry_date or (payload.start_date + timedelta(days=364))

        prop_row = TransactionAppNew(
            TransDate=now_dt,
            insurancecompany=str(payload.insurance_company_id),
            ProductType=payload.product_type,
            BusinessType=payload.business_type,
            PolicyMode=payload.policy_mode,
            UserId=eff_user_id,
            SalesExecutiveId=eff_sales_id,
            FranchaiseId=eff_frn_id,
            Name=payload.customer_name,
            ContactNo=payload.contact_no,
            Emailid=payload.email_id,
            VehicleType=payload.vehicle_type,
            StartDate=payload.start_date,
            Expirydate=exp_date,
            ODDiscount=round_2dp(payload.od_discount_percent),
            NCB=round_2dp(payload.ncb_amount),
            NCBPre=round_2dp(payload.ncb_percent),
            NCBPer=round_2dp(payload.ncb_percent),
            TPPremium=round_2dp(payload.tp_premium),
            ODPremium=round_2dp(payload.od_premium),
            NetPremium=round_2dp(payload.net_premium),
            Premium=round_2dp(payload.final_premium),
            Amount=round_2dp(payload.final_premium),
            IDV=str(round_2dp(payload.idv_amount)),
            PaymentMode=payload.policy_mode,
            PaymentDetails1=payload.payment_details_1,
            PaymentDetails2=payload.payment_details_2,
            RegistrationNo=payload.registration_no,
            QuatationCode=q_code,
            Remark=payload.remark,
            UserRoleId=ctx.role_id or 4,
            IsOwnerApprove=1 if shortfall == ZERO else 0,
            IsChashierApprove=0,
            Quot_Type=quot_type,
            CashPaidAmt=round_2dp(payload.cash_paid_amount),
            CashShortAmt=shortfall,
            CashType=payload.policy_mode,
            UpdatedDate=now_dt,
            UpdatedUser=str(current_user.UserId),
            TransEmpId=eff_sales_id,
            LocationHeadId=0,
            CoordinatorId=0,
            CashStatus="PAID" if shortfall == ZERO else "SHORT",
            IsAccountApproval=0,
            AppShortFallAmt=shortfall,
            IsSubmit=0,
            Grid=ZERO,
            CashBackAmt=ZERO,
            Paymentlink="",
            TDS=ZERO,
            incentive=ZERO,
            FranchiseCode=str(eff_frn_id),
            ExectiveGrid=ZERO,
            MgfYear=payload.mgf_year,
            EWalletUsedamt=round_2dp(payload.ewallet_used_amount),
            EwalletStatus=1 if payload.ewallet_used_amount > ZERO else 0,
            TPGrid=ZERO,
            TPCommission=ZERO,
            ODCommission=ZERO,
            NETCommission=ZERO,
            OutstandingAmt=shortfall,
            OutstandingWithPersonId=eff_user_id,
            ReceivedAmtLedgerMId=1,
            InsuranceTypeId=1,
            InsuranceSubTypeId=1,
            TypeofSubId=1,
            ND="NO",
            ChequeApprovalStatus=0,
        )
        await self.repo.create_proposal(prop_row)
        await self.session.commit()
        return self._map_proposal_response(prop_row)

    def _assert_can_access_proposal(
        self,
        row: TransactionAppNew,
        user: User,
    ) -> None:
        ctx = self._get_principal(user)
        norm_role = _normalize(ctx.role_name)
        if is_global_admin_role(ctx.role_name) or self._is_cross_branch_read_role(ctx.role_name):
            return
        if norm_role in _AGENT_ROLES_NORM:
            expected_user = ctx.agent_id or ctx.user_id
            if row.UserId != expected_user:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: Proposal does not belong to your Agent identity.",
                )
        elif norm_role in _FRANCHISE_ROLES_NORM:
            expected_frn = ctx.franchise_id or ctx.user_id
            if row.FranchaiseId != expected_frn:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: Proposal is outside your Franchise scope.",
                )
        elif norm_role in _EMPLOYEE_ROLES_NORM:
            expected_emp = ctx.emp_id or ctx.user_id
            if row.SalesExecutiveId != expected_emp and row.UserId != expected_emp:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: Proposal is outside your Sales Executive scope.",
                )

    async def get_proposal(
        self,
        trans_id: int,
        current_user: User,
    ) -> PolicyProposalResponse:
        row = await self.repo.get_proposal_by_id(trans_id)
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Staged Policy Proposal #{trans_id} not found.",
            )
        self._assert_can_access_proposal(row, current_user)
        return self._map_proposal_response(row)

    async def list_proposals(
        self,
        current_user: User,
        *,
        quotation_code: Optional[str] = None,
        registration_no: Optional[str] = None,
        is_submit: Optional[int] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> PolicyProposalListResponse:
        ctx = self._get_principal(current_user)
        norm_role = _normalize(ctx.role_name)

        user_filter: Optional[int] = None
        sales_filter: Optional[int] = None
        frn_filter: Optional[int] = None

        if not is_global_admin_role(ctx.role_name) and not self._is_cross_branch_read_role(ctx.role_name):
            if norm_role in _AGENT_ROLES_NORM:
                user_filter = ctx.agent_id or ctx.user_id
            elif norm_role in _FRANCHISE_ROLES_NORM:
                frn_filter = ctx.franchise_id or ctx.user_id
            elif norm_role in _EMPLOYEE_ROLES_NORM:
                sales_filter = ctx.emp_id or ctx.user_id

        total, rows = await self.repo.list_proposals(
            user_id=user_filter,
            sales_executive_id=sales_filter,
            franchise_id=frn_filter,
            quotation_code=quotation_code,
            registration_no=registration_no,
            is_submit=is_submit,
            limit=limit,
            offset=offset,
        )
        return PolicyProposalListResponse(
            total=total,
            limit=limit,
            offset=offset,
            items=[self._map_proposal_response(r) for r in rows],
        )

    async def approve_proposal(
        self,
        trans_id: int,
        payload: PolicyProposalApprovalRequest,
        current_user: User,
    ) -> PolicyProposalResponse:
        """
        Executes stage-specific approval gate transitions on tbl_transactionappnew:
        - CASHIER -> IsChashierApprove (sp_UpdateCashierApproval parity)
        - ACCOUNTANT -> IsAccountApproval (sp_UpdateAccountantApproval parity)
        - OWNER -> IsOwnerApprove (sp_UpdateOwnerApproval parity)
        """
        ctx = self._get_principal(current_user)
        norm_role = _normalize(ctx.role_name)

        if payload.stage == "CASHIER" and norm_role not in _CASHIER_APPROVAL_NORM:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{ctx.role_name}' is not authorized for CASHIER approval.",
            )
        if payload.stage == "ACCOUNTANT" and norm_role not in _ACCOUNTANT_APPROVAL_NORM:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{ctx.role_name}' is not authorized for ACCOUNTANT approval.",
            )
        if payload.stage == "OWNER" and norm_role not in _OWNER_APPROVAL_NORM:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{ctx.role_name}' is not authorized for OWNER approval.",
            )

        row = await self.repo.get_proposal_by_id(trans_id)
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Staged Policy Proposal #{trans_id} not found.",
            )

        if norm_role in _FRANCHISE_ROLES_NORM:
            expected_frn = ctx.franchise_id or ctx.user_id
            if row.FranchaiseId != expected_frn:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: Franchise can only approve proposals within its own FranchiseId.",
                )

        flag_val = 1 if payload.approved else 2
        if payload.stage == "CASHIER":
            row.IsChashierApprove = flag_val
        elif payload.stage == "ACCOUNTANT":
            row.IsAccountApproval = flag_val
            if payload.remark:
                row.AccountRemark = payload.remark
        elif payload.stage == "OWNER":
            row.IsOwnerApprove = flag_val

        row.ApprovedBy = getattr(current_user, "UserName", None) or str(current_user.UserId)
        row.UpdatedDate = datetime.utcnow()
        row.UpdatedUser = str(current_user.UserId)
        await self.session.commit()
        return self._map_proposal_response(row)
