"""
Phase 10 — Claims & Endorsements Engine Service.

Implements verified legacy business logic for:
1. Motor Claim Intimation, Eligibility & Coverage Period Validation
2. Claim Lifecycle State Machine (`INTIMATED` -> `REGISTERED` -> `UNDER_SURVEY` -> `ASSESSED` -> `APPROVED` -> `SETTLED` -> `CLOSED` / `REJECTED` / `CANCELLED` / `REOPENED`)
3. Claim Assessment Formula (`ApprovedAmount = max(0, Assessed - Depreciation - Deductible - Excess - Salvage)`) & IDV Cap
4. Claim Settlement & Reversal with Balanced Double-Entry Accounting (`AccTransId = 15`, `AccTransId = 16`)
5. Policy Endorsement Lifecycle (`DRAFT` -> `SUBMITTED` -> `APPROVED` -> `APPLIED` -> `REVERSED` / `REJECTED` / `CANCELLED`)
6. Field-Allowlist Policy Modification (`tbl_customer`, `tbl_vehicledetails`, `tbl_transaction`) with `before`/`after` Snapshot
7. Endorsement Premium Recalculation & Delta Engine (reusing Phase 6/7 `Decimal` `ROUND_HALF_UP` rules)
8. Endorsement Commission & TDS Adjustment + Paid-Commission Recovery (`CommissionRecoveryAmount`, reusing Phase 9 `calculate_commission_preview_pure`)
9. Endorsement Additional Premium Receivable & Refund Disbursement/Reversal Engine (`AccTransId = 17`, `AccTransId = 18`)
"""
import asyncio
import json
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, FrozenSet, List, Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import (
    AGENT_PRINCIPAL_ROLES,
    CLAIM_APPROVE_SETTLE_ROLES,
    CLAIM_CREATE_ROLES,
    CLAIM_READ_ROLES,
    CLAIM_UPDATE_ROLES,
    EMPLOYEE_PRINCIPAL_ROLES,
    ENDORSEMENT_APPROVE_APPLY_ROLES,
    ENDORSEMENT_CREATE_ROLES,
    ENDORSEMENT_READ_ROLES,
    FRANCHISE_PRINCIPAL_ROLES,
    REFUND_APPROVE_WRITE_ROLES,
    PrincipalContext,
    _normalize,
    is_global_admin_role,
    is_global_read_role,
)
from app.models.account import Account
from app.models.claims_endorsement import Claim, ClaimDocument, PolicyEndorsement
from app.models.commission import AgentCommissionPayment, FranchiseCommission
from app.models.customer import Customer
from app.models.transaction import Transaction
from app.models.user import User
from app.models.vehicle import VehicleDetails
from app.repositories.claims_endorsement import ClaimsEndorsementRepository
from app.repositories.quotation import _to_decimal
from app.schemas.claims_endorsement import (
    LEGACY_ENDORSEMENT_TYPE_ID_MAP,
    LEGACY_ENDORSEMENT_TYPE_TO_ID_MAP,
    ClaimActionRemarksRequest,
    ClaimApprovalRequest,
    ClaimAssessmentRequest,
    ClaimDocumentCreateRequest,
    ClaimDocumentResponse,
    ClaimIntimateRequest,
    ClaimListResponse,
    ClaimRegisterRequest,
    ClaimRejectionRequest,
    ClaimResponse,
    ClaimSettlementRequest,
    ClaimSurveyUpdateRequest,
    EndorsementActionRequest,
    EndorsementApplyRequest,
    EndorsementCreateRequest,
    EndorsementListResponse,
    EndorsementPreviewResponse,
    EndorsementRejectRequest,
    EndorsementResponse,
    RefundActionRequest,
    RefundDisburseRequest,
)
from app.schemas.commission_accounting import CommissionPreviewRequest
from app.services.commission_accounting import (
    HUNDRED,
    ZERO,
    calculate_commission_preview_pure,
    round_2dp,
)
from app.services.rating import round_rupee

# Canonical Legacy System Ledger IDs (09_legacy_commission_accounting_baseline.md & 11_legacy_endorsement_baseline.md)
LEGACY_COMMISSION_CONTROL_LEDGER_ID = 1161
LEGACY_TDS_PAYABLE_LEDGER_ID = 2113
LEGACY_SALES_EX_COMM_LEDGER_ID = 1930
LEGACY_ENDORSEMENT_INCOME_LEDGER_ID = 1878

# Process-wide async lock serializing claim/endorsement/refund mutations under concurrent load
_PHASE10_WRITE_LOCK = asyncio.Lock()

_AGENT_ROLES_NORM = frozenset(_normalize(r) for r in AGENT_PRINCIPAL_ROLES)
_FRANCHISE_ROLES_NORM = frozenset(_normalize(r) for r in FRANCHISE_PRINCIPAL_ROLES)
_EMPLOYEE_ROLES_NORM = frozenset(_normalize(r) for r in EMPLOYEE_PRINCIPAL_ROLES)

_CLAIM_CREATE_NORM = frozenset(_normalize(r) for r in CLAIM_CREATE_ROLES)
_CLAIM_READ_NORM = frozenset(_normalize(r) for r in CLAIM_READ_ROLES)
_CLAIM_UPDATE_NORM = frozenset(_normalize(r) for r in CLAIM_UPDATE_ROLES)
_CLAIM_APPROVE_SETTLE_NORM = frozenset(_normalize(r) for r in CLAIM_APPROVE_SETTLE_ROLES)

_ENDORSEMENT_CREATE_NORM = frozenset(_normalize(r) for r in ENDORSEMENT_CREATE_ROLES)
_ENDORSEMENT_READ_NORM = frozenset(_normalize(r) for r in ENDORSEMENT_READ_ROLES)
_ENDORSEMENT_APPROVE_APPLY_NORM = frozenset(_normalize(r) for r in ENDORSEMENT_APPROVE_APPLY_ROLES)
_REFUND_APPROVE_WRITE_NORM = frozenset(_normalize(r) for r in REFUND_APPROVE_WRITE_ROLES)

NON_FINANCIAL_ENDORSEMENT_TYPES: FrozenSet[str] = frozenset({
    "NAME_CORRECTION",
    "ADDRESS_CORRECTION",
    "CONTACT_CORRECTION",
    "VEHICLE_REGISTRATION_CORRECTION",
    "ENGINE_CHASSIS_CORRECTION",
    "MAKE_MODEL_CORRECTION",
    "HYPOTHECATION_CHANGE",
    "NOMINEE_CHANGE",
    "CC_SEATING_GVW_CORRECTION",
    "POLICY_PERIOD_CORRECTION",
    "OTHER_CORRECTION",
})

FINANCIAL_ENDORSEMENT_TYPES: FrozenSet[str] = frozenset({
    "IDV_CHANGE",
    "NCB_CORRECTION",
    "NCB_RECOVERY",
    "COVERAGE_ADDON_CHANGE",
    "LPG_CNG_KIT_CHANGE",
    "ACCESSORIES_CHANGE",
    "PA_COVER_CHANGE",
    "LL_COVER_CHANGE",
    "ZERO_DEP_CHANGE",
    "VOLUNTARY_DEDUCTIBLE_CHANGE",
    "OWNERSHIP_TRANSFER",
})

_COVERAGE_FINANCIAL_FIELDS: FrozenSet[str] = frozenset({
    "AddOn",
    "TowingChargesAmt",
    "PACovertoOwner",
    "PACoverDriverCleaner",
    "LegalLiabilitytoPaidDriver",
    "RoadSidePremium",
    "ODPermium",
    "TPPermium",
})

ALLOWED_FIELDS_BY_ENDORSEMENT_TYPE: Dict[str, FrozenSet[str]] = {
    "NAME_CORRECTION": frozenset({"CustFName", "CustMName", "CustLName", "PanNo", "PAN_No", "GSTNo", "Extra1"}),
    "ADDRESS_CORRECTION": frozenset({"Address", "PerAddrLine1", "PerAddrLine2", "ComAddrLine1", "ComAddrLine2"}),
    "CONTACT_CORRECTION": frozenset({"MoblieNo1", "MoblieNo2", "MobileNo", "EMailId"}),
    "VEHICLE_REGISTRATION_CORRECTION": frozenset({"RegistrationNo", "MfgYear"}),
    "ENGINE_CHASSIS_CORRECTION": frozenset({"EngineNo", "ChaiseNo"}),
    "MAKE_MODEL_CORRECTION": frozenset({"VehicleMake", "VehicleModel", "VehicleVariant", "MfgYear", "Extra1", "Extra2"}),
    "HYPOTHECATION_CHANGE": frozenset({"Financer", "FinancerBranch", "Extra1", "Extra2"}),
    "NOMINEE_CHANGE": frozenset({"NomineeName", "NomineeRelation", "NomineeAge"}),
    "CC_SEATING_GVW_CORRECTION": frozenset({"EnginePower", "SeatsCapacity", "VehicleWeight", "GVW"}),
    "POLICY_PERIOD_CORRECTION": frozenset({"PolicyPeriodRemark", "Extra1", "Extra2"}),
    "OTHER_CORRECTION": frozenset({
        "CustFName", "CustMName", "CustLName", "Address", "PerAddrLine1", "MoblieNo1", "MobileNo", "EMailId",
        "RegistrationNo", "EngineNo", "ChaiseNo", "Financer", "Extra1", "Extra2",
    }),
    "IDV_CHANGE": frozenset({"SumInsured", "ODPermium", "NCBPermium"}),
    "NCB_CORRECTION": frozenset({"NCB", "NCBPermium", "ODPermium", "NcbRecovAmt"}),
    "NCB_RECOVERY": frozenset({"NCB", "NCBPermium", "ODPermium", "NcbRecovAmt"}),
    "COVERAGE_ADDON_CHANGE": _COVERAGE_FINANCIAL_FIELDS,
    "LPG_CNG_KIT_CHANGE": _COVERAGE_FINANCIAL_FIELDS,
    "ACCESSORIES_CHANGE": _COVERAGE_FINANCIAL_FIELDS,
    "PA_COVER_CHANGE": _COVERAGE_FINANCIAL_FIELDS,
    "LL_COVER_CHANGE": _COVERAGE_FINANCIAL_FIELDS,
    "ZERO_DEP_CHANGE": _COVERAGE_FINANCIAL_FIELDS,
    "VOLUNTARY_DEDUCTIBLE_CHANGE": _COVERAGE_FINANCIAL_FIELDS,
    "OWNERSHIP_TRANSFER": frozenset({
        "CustFName",
        "CustMName",
        "CustLName",
        "MoblieNo1",
        "MoblieNo2",
        "MobileNo",
        "EMailId",
        "Address",
        "PerAddrLine1",
        "PerAddrLine2",
        "PanNo",
        "PAN_No",
        "GSTNo",
        "Extra1",
        "NCB",
        "NCBPermium",
        "ODPermium",
    }),
}

CUSTOMER_FIELDS: FrozenSet[str] = frozenset({
    "CustFName",
    "CustMName",
    "CustLName",
    "PanNo",
    "PAN_No",
    "GSTNo",
    "Extra1",
    "Address",
    "PerAddrLine1",
    "PerAddrLine2",
    "ComAddrLine1",
    "ComAddrLine2",
    "MoblieNo1",
    "MoblieNo2",
    "MobileNo",
    "EMailId",
    "NomineeName",
})

CUSTOMER_FIELD_ALIAS_MAP: Dict[str, str] = {
    "Address": "PerAddrLine1",
    "PanNo": "PAN_No",
    "GSTNo": "Extra1",
    "MobileNo": "MoblieNo1",
}

VEHICLE_FIELDS: FrozenSet[str] = frozenset({
    "RegistrationNo",
    "MfgYear",
    "EngineNo",
    "ChaiseNo",
    "Financer",
    "FinancerBranch",
    "VehicleMake",
    "VehicleModel",
    "VehicleVariant",
    "EnginePower",
    "SeatsCapacity",
    "VehicleWeight",
    "Extra1",
    "Extra2",
})

VEHICLE_FIELD_ALIAS_MAP: Dict[str, str] = {
    "Financer": "Extra1",
    "FinancerBranch": "Extra2",
    "VehicleMake": "Extra1",
    "VehicleModel": "Extra2",
}

NOMINEE_VIRTUAL_FIELDS: FrozenSet[str] = frozenset({
    "NomineeRelation",
    "NomineeAge",
    "PolicyPeriodRemark",
    "NcbRecovAmt",
})

IMMUTABLE_POLICY_FIELDS: FrozenSet[str] = frozenset({
    "TransanctionId",
    "PolicyNo",
    "CustomerId",
    "CustVehId",
    "BranchId",
    "AgentId",
    "FranchiseId",
    "FranchiseCode",
    "SalesExId",
    "SalesEx_id",
    "InsuranceCompanyId",
    "PolicyStartDate",
    "PolicyEndDate",
    "RiskStartdate",
    "ExpiryDate",
    "PolicycancelId",
    "isdeleted",
})


# ===========================================================================
# Pure Deterministic Calculation Helpers (Unit-Testable Without DB)
# ===========================================================================

def calculate_claim_assessment_pure(
    *,
    assessed_loss_amount: Decimal,
    depreciation_amount: Decimal = ZERO,
    deductible_amount: Decimal = ZERO,
    excess_amount: Decimal = ZERO,
    salvage_amount: Decimal = ZERO,
    sum_insured: Decimal = ZERO,
    claim_type: str = "OD",
) -> Decimal:
    """
    Computes net approved claim amount:
    ApprovedAmount = max(0.00, AssessedLossAmount - DepreciationAmount - DeductibleAmount - ExcessAmount - SalvageAmount)
    Enforces non-negative deductions and IDV (SumInsured) cap for OD, THEFT, TOTAL_LOSS claims.
    """
    assessed = round_2dp(_to_decimal(assessed_loss_amount))
    dep = round_2dp(_to_decimal(depreciation_amount))
    ded = round_2dp(_to_decimal(deductible_amount))
    exc = round_2dp(_to_decimal(excess_amount))
    salv = round_2dp(_to_decimal(salvage_amount))
    idv = round_2dp(_to_decimal(sum_insured))

    if assessed <= ZERO:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Assessed loss amount must be greater than 0.00",
        )
    if any(x < ZERO for x in (dep, ded, exc, salv)):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Depreciation, deductible, excess, and salvage deductions cannot be negative",
        )

    net_payable = round_2dp(assessed - dep - ded - exc - salv)
    if net_payable <= ZERO:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Net assessed claim amount ({net_payable}) after deductions must be greater than 0.00 "
                "to qualify for approval"
            ),
        )

    if claim_type in {"OD", "THEFT", "TOTAL_LOSS"} and idv > ZERO and net_payable > idv:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Approved claim amount ({net_payable}) cannot exceed policy SumInsured / IDV ({idv}) "
                f"for {claim_type} claims"
            ),
        )

    return net_payable


def calculate_claim_settlement_split_pure(
    *,
    settled_amount: Decimal,
    approved_amount: Decimal,
    payee_type: str = "CUSTOMER",
) -> Tuple[Decimal, Decimal, Decimal]:
    """
    Validates `0 < settled_amount <= approved_amount` and returns:
    `(insurer_payable_amount, customer_payable_amount, garage_payable_amount)`
    """
    settled = round_2dp(_to_decimal(settled_amount))
    approved = round_2dp(_to_decimal(approved_amount))

    if settled <= ZERO:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Settled amount must be greater than 0.00",
        )
    if settled > approved:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Settled amount ({settled}) cannot exceed approved amount ({approved})",
        )

    if payee_type == "GARAGE":
        return (settled, ZERO, settled)
    if payee_type in {"CUSTOMER", "INSURER"}:
        return (settled, settled, ZERO)

    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=f"Unsupported payee_type '{payee_type}'",
    )


def validate_endorsement_field_allowlist(
    endorsement_type: str,
    field_changes: Dict[str, Any],
) -> None:
    """
    Validates that `endorsement_type` is known, `field_changes` is non-empty,
    no immutable policy fields are modified, and all keys belong to the allowlist
    for `endorsement_type`.
    """
    allowed = ALLOWED_FIELDS_BY_ENDORSEMENT_TYPE.get(endorsement_type)
    if allowed is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported endorsement_type '{endorsement_type}'",
        )
    if not field_changes:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="field_changes cannot be empty",
        )
    for key in field_changes.keys():
        if key in IMMUTABLE_POLICY_FIELDS:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Policy field '{key}' is immutable and cannot be modified by endorsement",
            )
        if key not in allowed:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"Field '{key}' is not permitted for endorsement_type '{endorsement_type}'. "
                    f"Allowed fields: {sorted(allowed)}"
                ),
            )


def calculate_endorsement_financial_impact_pure(
    *,
    endorsement_type: str,
    field_changes: Dict[str, Any],
    old_idv: Decimal,
    old_ncb_pct: Decimal,
    old_od_premium: Decimal,
    old_tp_premium: Decimal,
    old_net_premium: Decimal,
    old_gst_amount: Decimal,
    old_final_premium: Decimal,
    paid_amount: Decimal,
    agent_comm_od_pct: Decimal = ZERO,
    agent_comm_net_pct: Decimal = ZERO,
    agent_comm_extra_pct: Decimal = ZERO,
    agent_tds_pct: Decimal = Decimal("5.00"),
    old_agent_net_comm: Decimal = ZERO,
    old_agent_tds_amt: Decimal = ZERO,
    franchise_comm_od_pct: Decimal = ZERO,
    franchise_comm_net_pct: Decimal = ZERO,
    franchise_comm_extra_pct: Decimal = ZERO,
    franchise_tds_pct: Decimal = Decimal("5.00"),
    old_franchise_net_comm: Decimal = ZERO,
    commission_already_paid: bool = False,
    current_addon_fields: Optional[Dict[str, Decimal]] = None,
) -> Dict[str, Any]:
    """
    Pure deterministic calculator for Endorsement Premium Delta, GST Delta,
    Agent/Franchise Commission & TDS Delta, Paid-Commission Recovery, and Refund Amount.
    """
    validate_endorsement_field_allowlist(endorsement_type, field_changes)

    o_idv = round_2dp(_to_decimal(old_idv))
    o_ncb = round_2dp(_to_decimal(old_ncb_pct))
    o_od = round_2dp(_to_decimal(old_od_premium))
    o_tp = round_2dp(_to_decimal(old_tp_premium))
    o_net = round_2dp(_to_decimal(old_net_premium))
    o_gst = round_2dp(_to_decimal(old_gst_amount))
    o_final = round_2dp(_to_decimal(old_final_premium))
    paid = round_2dp(_to_decimal(paid_amount))

    n_idv = o_idv
    n_ncb = o_ncb
    n_od = o_od
    n_tp = o_tp
    n_net = o_net
    n_gst = o_gst
    n_final = o_final

    if endorsement_type in NON_FINANCIAL_ENDORSEMENT_TYPES:
        category = "NON_FINANCIAL"
    else:
        # Financial or potentially financial endorsement
        if endorsement_type == "IDV_CHANGE":
            if "SumInsured" in field_changes:
                n_idv = round_2dp(_to_decimal(field_changes["SumInsured"]))
                if n_idv <= ZERO:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail="New SumInsured (IDV) must be greater than 0.00",
                    )
            if "ODPermium" in field_changes:
                n_od = round_2dp(_to_decimal(field_changes["ODPermium"]))
            elif o_idv > ZERO and n_idv != o_idv:
                n_od = round_2dp((o_od * n_idv) / o_idv)

            other_net = round_2dp(o_net - o_od)
            n_net = round_2dp(n_od + other_net)

        elif endorsement_type in {"NCB_CORRECTION", "NCB_RECOVERY", "OWNERSHIP_TRANSFER"}:
            if "NCB" in field_changes:
                n_ncb = round_2dp(_to_decimal(field_changes["NCB"]))
                if n_ncb < ZERO or n_ncb >= HUNDRED:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail="NCB percentage must be between 0.00 and 99.99",
                    )
            elif endorsement_type == "NCB_RECOVERY":
                n_ncb = ZERO
            if "ODPermium" in field_changes:
                n_od = round_2dp(_to_decimal(field_changes["ODPermium"]))
            elif "NcbRecovAmt" in field_changes:
                # LBR-127 NCB Recovery formula: NewOD = OldOD + NcbRecovAmt
                recov_amt = round_2dp(_to_decimal(field_changes["NcbRecovAmt"]))
                n_od = round_2dp(o_od + recov_amt)
            elif n_ncb != o_ncb and o_ncb < HUNDRED:
                denom = round_2dp((HUNDRED - o_ncb) / HUNDRED)
                gross_od = round_2dp(o_od / denom) if denom > ZERO else o_od
                new_ncb_disc = round_2dp((gross_od * n_ncb) / HUNDRED)
                n_od = round_2dp(gross_od - new_ncb_disc)

            other_net = round_2dp(o_net - o_od)
            n_net = round_2dp(n_od + other_net)

        elif endorsement_type in {
            "COVERAGE_ADDON_CHANGE",
            "LPG_CNG_KIT_CHANGE",
            "ACCESSORIES_CHANGE",
            "PA_COVER_CHANGE",
            "LL_COVER_CHANGE",
            "ZERO_DEP_CHANGE",
            "VOLUNTARY_DEDUCTIBLE_CHANGE",
        }:
            addon_map = dict(current_addon_fields or {})
            delta_addons = ZERO
            for cov_field in (
                "AddOn",
                "TowingChargesAmt",
                "PACovertoOwner",
                "PACoverDriverCleaner",
                "LegalLiabilitytoPaidDriver",
                "RoadSidePremium",
            ):
                if cov_field in field_changes:
                    new_val = round_2dp(_to_decimal(field_changes[cov_field]))
                    if new_val < ZERO:
                        raise HTTPException(
                            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail=f"Coverage field '{cov_field}' cannot be negative",
                        )
                    old_val = round_2dp(_to_decimal(addon_map.get(cov_field, ZERO)))
                    delta_addons = round_2dp(delta_addons + (new_val - old_val))

            if "ODPermium" in field_changes:
                n_od = round_2dp(_to_decimal(field_changes["ODPermium"]))
            if "TPPermium" in field_changes:
                n_tp = round_2dp(_to_decimal(field_changes["TPPermium"]))

            delta_od = round_2dp(n_od - o_od)
            delta_tp = round_2dp(n_tp - o_tp)
            n_net = round_2dp(o_net + delta_od + delta_tp + delta_addons)

        if n_od < ZERO or n_tp < ZERO or n_net < ZERO:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Recalculated OD, TP, and Net premiums cannot be negative",
            )

        delta_net = round_2dp(n_net - o_net)
        if delta_net != ZERO:
            # Determine effective GST rate (standard 18% unless policy had specific ratio)
            eff_gst_rate = Decimal("0.18")
            if o_net > ZERO and o_gst > ZERO:
                eff_gst_rate = o_gst / o_net
            delta_gst = round_2dp(delta_net * eff_gst_rate)
            n_gst = round_2dp(o_gst + delta_gst)
            n_final = round_2dp(n_net + n_gst)
        else:
            n_gst = o_gst
            n_final = o_final

        prem_delta = round_2dp(n_final - o_final)
        if prem_delta > ZERO:
            category = "ADDITIONAL_PREMIUM"
        elif prem_delta < ZERO:
            category = "REFUND_PREMIUM"
        else:
            category = (
                "NON_FINANCIAL"
                if endorsement_type == "OWNERSHIP_TRANSFER"
                else "ZERO_PREMIUM"
            )

    prem_delta = round_2dp(n_final - o_final)

    # Commission & TDS recalculation via canonical Phase 9 engine
    o_ag_net = round_2dp(_to_decimal(old_agent_net_comm))
    o_ag_tds = round_2dp(_to_decimal(old_agent_tds_amt))
    o_fr_net = round_2dp(_to_decimal(old_franchise_net_comm))

    if prem_delta == ZERO and n_od == o_od and n_tp == o_tp and n_net == o_net:
        n_ag_net = o_ag_net
        n_ag_tds = o_ag_tds
        ag_delta = ZERO
        n_fr_net = o_fr_net
        fr_delta = ZERO
        comm_preview = None
    else:
        comm_preview = calculate_commission_preview_pure(
            CommissionPreviewRequest(
                od_premium=n_od,
                tp_premium=n_tp,
                net_premium=n_net,
                final_premium=n_final,
                agent_comm_od_pct=round_2dp(_to_decimal(agent_comm_od_pct)),
                agent_comm_net_pct=round_2dp(_to_decimal(agent_comm_net_pct)),
                agent_comm_extra_pct=round_2dp(_to_decimal(agent_comm_extra_pct)),
                agent_tds_pct=round_2dp(_to_decimal(agent_tds_pct)),
                franchise_comm_od_pct=round_2dp(_to_decimal(franchise_comm_od_pct)),
                franchise_comm_net_pct=round_2dp(_to_decimal(franchise_comm_net_pct)),
                franchise_comm_extra_pct=round_2dp(_to_decimal(franchise_comm_extra_pct)),
                franchise_tds_pct=round_2dp(_to_decimal(franchise_tds_pct)),
            )
        )
        n_ag_net = comm_preview.agent_net_commission
        n_ag_tds = comm_preview.agent_tds_amount
        ag_delta = round_2dp(n_ag_net - o_ag_net)
        n_fr_net = comm_preview.franchise_net_commission
        fr_delta = round_2dp(n_fr_net - o_fr_net)

    comm_recovery = ZERO
    if commission_already_paid and ag_delta < ZERO:
        comm_recovery = abs(ag_delta)

    est_refund = ZERO
    if prem_delta < ZERO and paid > n_final:
        est_refund = min(abs(prem_delta), round_2dp(paid - n_final))

    return {
        "endorsement_category": category,
        "old_idv": o_idv,
        "new_idv": n_idv,
        "old_ncb_percent": o_ncb,
        "new_ncb_percent": n_ncb,
        "old_od_premium": o_od,
        "new_od_premium": n_od,
        "old_tp_premium": o_tp,
        "new_tp_premium": n_tp,
        "old_net_premium": o_net,
        "new_net_premium": n_net,
        "old_gst_amount": o_gst,
        "new_gst_amount": n_gst,
        "old_final_premium": o_final,
        "new_final_premium": n_final,
        "premium_delta": prem_delta,
        "old_agent_net_comm": o_ag_net,
        "new_agent_net_comm": n_ag_net,
        "agent_comm_delta": ag_delta,
        "old_agent_tds_amt": o_ag_tds,
        "new_agent_tds_amt": n_ag_tds,
        "old_franchise_net_comm": o_fr_net,
        "new_franchise_net_comm": n_fr_net,
        "franchise_comm_delta": fr_delta,
        "commission_recovery_amount": comm_recovery,
        "estimated_refund_amount": est_refund,
        "commission_preview": comm_preview,
    }


# ===========================================================================
# Phase 10 Claims & Endorsements Service
# ===========================================================================

class ClaimsEndorsementService:
    """
    Transactional service implementing Phase 10 Claims, Endorsements, and Refunds.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = ClaimsEndorsementRepository(db)

    # ------------------------------------------------------------------
    # Role, Branch & Principal Ownership Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _get_principal(current_user: User) -> PrincipalContext:
        ctx = getattr(current_user, "principal_context", None)
        if ctx is not None:
            return ctx
        role_obj = getattr(current_user, "role_obj", None)
        role_name = getattr(current_user, "role_name", None) or (
            role_obj.UserRole if role_obj else None
        )
        return PrincipalContext(
            user_id=getattr(current_user, "UserId", 0) or 0,
            username=getattr(current_user, "UserName", None),
            role_id=getattr(current_user, "UserRoleId", None),
            role_name=role_name,
            branch_id=getattr(current_user, "BranchId", None),
            agent_id=getattr(current_user, "agent_id", None),
            emp_id=getattr(current_user, "emp_id", None),
            employee_id=getattr(current_user, "employee_id", None),
            franchise_id=getattr(current_user, "franchise_id", None),
        )

    @staticmethod
    def _require_role_in(ctx: PrincipalContext, allowed_norm: FrozenSet[str], action_desc: str) -> None:
        norm = _normalize(ctx.role_name)
        if norm not in allowed_norm:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{ctx.role_name}' is not authorized to {action_desc}",
            )

    @staticmethod
    def _is_cross_branch_role(role_name: Optional[str]) -> bool:
        norm = _normalize(role_name)
        return (
            is_global_admin_role(role_name)
            or is_global_read_role(role_name)
            or norm == "SHREYANSH OWNER"
        )

    def _enforce_entity_ownership(
        self,
        ctx: PrincipalContext,
        *,
        entity_branch_id: Optional[int],
        entity_agent_id: Optional[int],
        entity_franchise_id: Optional[int],
        entity_sales_ex_id: Optional[int],
        entity_label: str = "record",
    ) -> None:
        norm = _normalize(ctx.role_name)
        if self._is_cross_branch_role(ctx.role_name):
            return

        if norm in _AGENT_ROLES_NORM:
            eff_agent = ctx.agent_id or ctx.user_id
            if entity_agent_id != eff_agent:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Agent principal is not authorized to access {entity_label} owned by another agent",
                )
            return

        if norm in _FRANCHISE_ROLES_NORM:
            eff_frn = ctx.franchise_id or ctx.user_id
            if entity_franchise_id != eff_frn:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Franchise principal is not authorized to access {entity_label} owned by another franchise",
                )
            return

        if norm in _EMPLOYEE_ROLES_NORM:
            eff_emp = ctx.emp_id or ctx.user_id
            if entity_sales_ex_id is not None and entity_sales_ex_id > 0 and entity_sales_ex_id != eff_emp:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Sales Executive principal is not authorized to access {entity_label} owned by another executive",
                )

        if (
            ctx.branch_id is not None
            and entity_branch_id is not None
            and entity_branch_id > 0
            and ctx.branch_id != entity_branch_id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Branch-scoped role cannot access {entity_label} from branch {entity_branch_id}",
            )

    @staticmethod
    def _extract_policy_franchise_id(policy: Transaction) -> Optional[int]:
        fc = getattr(policy, "FranchiseCode", None)
        if fc is not None:
            try:
                val = int(str(fc).strip())
                if val > 0:
                    return val
            except (ValueError, TypeError):
                pass
        return None

    # ------------------------------------------------------------------
    # Response Mappers
    # ------------------------------------------------------------------
    @staticmethod
    def _encode_final_bill_remarks(
        remarks: Optional[str],
        bill_amount: Optional[Decimal],
        icl_amount: Optional[Decimal],
        il_amount: Optional[Decimal],
    ) -> Optional[str]:
        base = (remarks or "").strip()
        if bill_amount is None and icl_amount is None and il_amount is None:
            return base or None
        b_str = str(round_2dp(bill_amount)) if bill_amount is not None else ""
        icl_str = str(round_2dp(icl_amount)) if icl_amount is not None else ""
        il_str = str(round_2dp(il_amount)) if il_amount is not None else ""
        marker = f"[FINAL_BILL:bill={b_str}|icl={icl_str}|il={il_str}]"
        return f"{base} {marker}".strip()[:1000]

    @staticmethod
    def _decode_final_bill_remarks(
        raw_remarks: Optional[str],
    ) -> Tuple[Optional[str], Optional[Decimal], Optional[Decimal], Optional[Decimal]]:
        if not raw_remarks or "[FINAL_BILL:" not in raw_remarks:
            return raw_remarks, None, None, None
        idx = raw_remarks.find("[FINAL_BILL:")
        end_idx = raw_remarks.find("]", idx)
        if end_idx == -1:
            return raw_remarks, None, None, None
        clean_remarks = (raw_remarks[:idx] + raw_remarks[end_idx + 1 :]).strip() or None
        inner = raw_remarks[idx + len("[FINAL_BILL:") : end_idx]
        b_val: Optional[Decimal] = None
        icl_val: Optional[Decimal] = None
        il_val: Optional[Decimal] = None
        for part in inner.split("|"):
            if part.startswith("bill=") and part[len("bill=") :]:
                b_val = round_2dp(_to_decimal(part[len("bill=") :]))
            elif part.startswith("icl=") and part[len("icl=") :]:
                icl_val = round_2dp(_to_decimal(part[len("icl=") :]))
            elif part.startswith("il=") and part[len("il=") :]:
                il_val = round_2dp(_to_decimal(part[len("il=") :]))
        return clean_remarks, b_val, icl_val, il_val

    @staticmethod
    def _to_claim_response(c: Claim) -> ClaimResponse:
        clean_remarks, bill_amt, icl_amt, il_amt = ClaimsEndorsementService._decode_final_bill_remarks(
            c.Remarks
        )
        return ClaimResponse(
            claim_id=c.ClaimId,
            claim_no=c.ClaimNo,
            transaction_id=c.TransanctionId,
            policy_no=c.PolicyNo,
            customer_id=c.CustomerId,
            cust_veh_id=c.CustVehId,
            insurance_company_id=c.InsuranceCompanyId,
            branch_id=c.BranchId,
            agent_id=c.AgentId,
            franchise_id=c.FranchiseId,
            sales_ex_id=c.SalesExId,
            claim_type=c.ClaimType,
            claim_status=c.ClaimStatus,
            intimation_date=c.IntimationDate,
            loss_date=c.LossDate,
            loss_location=c.LossLocation,
            loss_description=c.LossDescription,
            estimated_amount=round_2dp(_to_decimal(c.EstimatedAmount)),
            surveyor_name=c.SurveyorName,
            surveyor_mobile=c.SurveyorMobile,
            surveyor_license_no=c.SurveyorLicenseNo,
            survey_date=c.SurveyDate,
            assessed_loss_amount=round_2dp(_to_decimal(c.AssessedLossAmount)),
            depreciation_amount=round_2dp(_to_decimal(c.DepreciationAmount)),
            deductible_amount=round_2dp(_to_decimal(c.DeductibleAmount)),
            excess_amount=round_2dp(_to_decimal(c.ExcessAmount)),
            salvage_amount=round_2dp(_to_decimal(c.SalvageAmount)),
            approved_amount=round_2dp(_to_decimal(c.ApprovedAmount)),
            settled_amount=round_2dp(_to_decimal(c.SettledAmount)),
            bill_amount=bill_amt,
            icl_amount=icl_amt,
            il_amount=il_amt,
            insurer_payable_amount=round_2dp(_to_decimal(c.InsurerPayableAmount)),
            customer_payable_amount=round_2dp(_to_decimal(c.CustomerPayableAmount)),
            garage_payable_amount=round_2dp(_to_decimal(c.GaragePayableAmount)),
            payee_type=c.PayeeType,
            payment_mode=c.PaymentMode,
            payment_doc_no=c.PaymentDocNo,
            settlement_date=c.SettlementDate,
            insurer_claim_ref=c.InsurerClaimRef,
            rejection_reason=c.RejectionReason,
            remarks=clean_remarks,
            idempotency_key=c.IdempotencyKey,
            create_date=c.CreateDate,
        )

    @staticmethod
    def _to_endorsement_response(e: PolicyEndorsement) -> EndorsementResponse:
        try:
            snap = json.loads(e.FieldChangesJson or "{}")
        except Exception:
            snap = {}
        meta = snap.get("meta", {}) if isinstance(snap, dict) else {}
        legacy_tid = meta.get("legacy_endorsement_type_id") or LEGACY_ENDORSEMENT_TYPE_TO_ID_MAP.get(
            e.EndorsementType
        )
        prev_cid = meta.get("previous_customer_id", e.CustomerId)
        curr_cid = meta.get("current_customer_id", e.CustomerId)
        return EndorsementResponse(
            endorsement_id=e.EndorsementId,
            endorsement_no=e.EndorsementNo,
            transaction_id=e.TransanctionId,
            policy_no=e.PolicyNo,
            customer_id=e.CustomerId,
            previous_customer_id=int(prev_cid) if prev_cid is not None else None,
            current_customer_id=int(curr_cid) if curr_cid is not None else None,
            cust_veh_id=e.CustVehId,
            branch_id=e.BranchId,
            agent_id=e.AgentId,
            franchise_id=e.FranchiseId,
            sales_ex_id=e.SalesExId,
            endorsement_type=e.EndorsementType,
            legacy_endorsement_type_id=int(legacy_tid) if legacy_tid is not None else None,
            endorsement_category=e.EndorsementCategory,
            endorsement_status=e.EndorsementStatus,
            effective_date=e.EffectiveDate,
            request_date=e.RequestDate,
            field_changes_snapshot=snap,
            old_idv=round_2dp(_to_decimal(e.OldIDV)),
            new_idv=round_2dp(_to_decimal(e.NewIDV)),
            old_ncb_percent=round_2dp(_to_decimal(e.OldNCBPercent)),
            new_ncb_percent=round_2dp(_to_decimal(e.NewNCBPercent)),
            old_od_premium=round_2dp(_to_decimal(e.OldODPremium)),
            new_od_premium=round_2dp(_to_decimal(e.NewODPremium)),
            old_tp_premium=round_2dp(_to_decimal(e.OldTPPremium)),
            new_tp_premium=round_2dp(_to_decimal(e.NewTPPremium)),
            old_net_premium=round_2dp(_to_decimal(e.OldNetPremium)),
            new_net_premium=round_2dp(_to_decimal(e.NewNetPremium)),
            old_gst_amount=round_2dp(_to_decimal(e.OldGSTAmount)),
            new_gst_amount=round_2dp(_to_decimal(e.NewGSTAmount)),
            old_final_premium=round_2dp(_to_decimal(e.OldFinalPremium)),
            new_final_premium=round_2dp(_to_decimal(e.NewFinalPremium)),
            premium_delta=round_2dp(_to_decimal(e.PremiumDelta)),
            old_agent_net_comm=round_2dp(_to_decimal(e.OldAgentNetComm)),
            new_agent_net_comm=round_2dp(_to_decimal(e.NewAgentNetComm)),
            agent_comm_delta=round_2dp(_to_decimal(e.AgentCommDelta)),
            old_agent_tds_amt=round_2dp(_to_decimal(e.OldAgentTdsAmt)),
            new_agent_tds_amt=round_2dp(_to_decimal(e.NewAgentTdsAmt)),
            old_franchise_net_comm=round_2dp(_to_decimal(e.OldFranchiseNetComm)),
            new_franchise_net_comm=round_2dp(_to_decimal(e.NewFranchiseNetComm)),
            franchise_comm_delta=round_2dp(_to_decimal(e.FranchiseCommDelta)),
            commission_recovery_amount=round_2dp(_to_decimal(e.CommissionRecoveryAmount)),
            refund_status=e.RefundStatus,
            refund_amount=round_2dp(_to_decimal(e.RefundAmount)),
            refund_mode=e.RefundMode,
            refund_doc_no=e.RefundDocNo,
            supporting_doc_key=e.SupportingDocKey,
            remarks=e.Remarks,
            rejection_reason=e.RejectionReason,
            idempotency_key=e.IdempotencyKey,
            create_date=e.CreateDate,
        )

    @staticmethod
    def _build_account_row(
        *,
        acc_trans_id: int,
        account_date: datetime,
        ledger_m_id: int,
        amount: Decimal,
        narration: str,
        ref_cust_id: int,
        ref_agent_id: int,
        branch_id: int,
        payment_type: str,
        extra1: str,
        extra2: str,
        doc_no: int,
        created_user: int,
        transaction_id: int,
        cust_veh_id: int,
        endorsement_id: int,
        trans_id: int,
    ) -> Account:
        return Account(
            AccTransId=acc_trans_id,
            AccountDate=account_date,
            LedgerMId=ledger_m_id,
            amount=amount,
            Narration=narration[:500],
            ReferenceCustId=ref_cust_id,
            ReferenceAgentId=ref_agent_id,
            BranchId=branch_id,
            Extra1=extra1[:255],
            Extra2=extra2[:255],
            Doc_No=doc_no,
            CreatedUser=str(created_user),
            CreatedDate=account_date,
            PaymentType=payment_type[:255],
            isdeleted=0,
            IsNill=0,
            TransactionId=transaction_id,
            CustVehId=cust_veh_id,
            MonthId=account_date.month,
            EndorsementId=endorsement_id,
            TransId=trans_id,
        )

    # ------------------------------------------------------------------
    # 1. Claims Engine Operations
    # ------------------------------------------------------------------
    async def intimate_claim(
        self,
        current_user: User,
        payload: ClaimIntimateRequest,
    ) -> Tuple[ClaimResponse, bool]:
        """
        Creates a new Motor Claim Intimation (`ClaimStatus = "INTIMATED"`).
        Returns `(ClaimResponse, is_new_record)`.
        """
        ctx = self._get_principal(current_user)
        self._require_role_in(ctx, _CLAIM_CREATE_NORM, "intimate claims")

        async with _PHASE10_WRITE_LOCK:
            if payload.idempotency_key:
                existing = await self.repo.get_claim_by_idempotency_key(payload.idempotency_key)
                if existing is not None:
                    self._enforce_entity_ownership(
                        ctx,
                        entity_branch_id=existing.BranchId,
                        entity_agent_id=existing.AgentId,
                        entity_franchise_id=existing.FranchiseId,
                        entity_sales_ex_id=existing.SalesExId,
                        entity_label="claim",
                    )
                    return self._to_claim_response(existing), False

            policy = await self.repo.get_policy_for_update(payload.transaction_id)
            if policy is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Booked policy transaction {payload.transaction_id} not found",
                )

            frn_id = self._extract_policy_franchise_id(policy)
            self._enforce_entity_ownership(
                ctx,
                entity_branch_id=policy.BranchId,
                entity_agent_id=policy.AgentId,
                entity_franchise_id=frn_id,
                entity_sales_ex_id=policy.SalesEx_id,
                entity_label="policy",
            )

            # Policy active & non-cancelled check
            if (policy.PolicycancelId or 0) != 0 or (policy.TStatus or "").upper() == "CANCELLED":
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Cannot intimate a claim on a cancelled policy",
                )
            if not policy.PolicyNo:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Cannot intimate a claim on an unissued policy without a PolicyNo",
                )

            # Loss date inside policy coverage period
            loss_dt = payload.loss_date.replace(tzinfo=None)
            intimation_dt = (payload.intimation_date or datetime.utcnow()).replace(tzinfo=None)
            start_dt = policy.RiskStartdate.replace(tzinfo=None) if policy.RiskStartdate else None
            end_dt = policy.ExpiryDate.replace(tzinfo=None) if policy.ExpiryDate else None

            if start_dt and loss_dt.date() < start_dt.date():
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Loss date ({loss_dt.isoformat()}) is prior to policy start date ({start_dt.isoformat()})",
                )
            if end_dt and loss_dt.date() > end_dt.date():
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Loss date ({loss_dt.isoformat()}) is after policy expiry date ({end_dt.isoformat()})",
                )
            if intimation_dt.date() < loss_dt.date():
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Intimation date cannot be earlier than loss date",
                )

            # Policy coverage vs ClaimType check
            od_prem = round_2dp(_to_decimal(policy.ODPermium))
            tp_prem = round_2dp(_to_decimal(policy.TPPermium))
            if payload.claim_type in {"OD", "THEFT", "TOTAL_LOSS"} and od_prem <= ZERO and tp_prem > ZERO:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Claim type '{payload.claim_type}' is not covered under a TP-only policy (ODPermium == 0.00)",
                )
            if payload.claim_type == "TP" and tp_prem <= ZERO and od_prem > ZERO:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Third-Party (TP) claim is not covered under a Standalone OD-only policy (TPPermium == 0.00)",
                )

            # Duplicate active claim check on (TransanctionId, LossDate, ClaimType)
            dup = await self.repo.get_duplicate_active_claim(
                payload.transaction_id, loss_dt, payload.claim_type
            )
            if dup is not None:
                return self._to_claim_response(dup), False

            now_dt = datetime.utcnow()
            temp_no = f"CLM-TMP-{uuid.uuid4().hex[:12].upper()}"
            claim = Claim(
                ClaimNo=temp_no,
                TransanctionId=policy.TransanctionId,
                PolicyNo=policy.PolicyNo,
                CustomerId=policy.CustomerId,
                CustVehId=policy.CustVehId,
                InsuranceCompanyId=policy.InsuranceCompanyId,
                BranchId=policy.BranchId or ctx.branch_id or 1,
                AgentId=policy.AgentId,
                FranchiseId=frn_id,
                SalesExId=policy.SalesEx_id,
                ClaimType=payload.claim_type,
                ClaimStatus="INTIMATED",
                IntimationDate=intimation_dt,
                LossDate=loss_dt,
                LossLocation=payload.loss_location,
                LossDescription=payload.loss_description,
                EstimatedAmount=round_2dp(payload.estimated_amount),
                AssessedLossAmount=ZERO,
                DepreciationAmount=ZERO,
                DeductibleAmount=ZERO,
                ExcessAmount=ZERO,
                SalvageAmount=ZERO,
                ApprovedAmount=ZERO,
                SettledAmount=ZERO,
                InsurerPayableAmount=ZERO,
                CustomerPayableAmount=ZERO,
                GaragePayableAmount=ZERO,
                InsurerClaimRef=payload.insurer_claim_ref,
                Remarks=payload.remarks,
                IdempotencyKey=payload.idempotency_key,
                isdeleted="0",
                CreateDate=now_dt,
                CreateUser=ctx.user_id,
            )
            self.db.add(claim)
            await self.db.flush()

            branch_code = claim.BranchId or 1
            claim.ClaimNo = f"CLM-{branch_code}-{now_dt.year}-{claim.ClaimId:06d}"
            await self.db.commit()
            await self.db.refresh(claim)
            return self._to_claim_response(claim), True

    async def register_claim(
        self,
        current_user: User,
        claim_id: int,
        payload: ClaimRegisterRequest,
    ) -> ClaimResponse:
        ctx = self._get_principal(current_user)
        self._require_role_in(ctx, _CLAIM_UPDATE_NORM, "register claims")

        async with _PHASE10_WRITE_LOCK:
            claim = await self.repo.get_claim_for_update(claim_id)
            if claim is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")
            self._enforce_entity_ownership(
                ctx,
                entity_branch_id=claim.BranchId,
                entity_agent_id=claim.AgentId,
                entity_franchise_id=claim.FranchiseId,
                entity_sales_ex_id=claim.SalesExId,
                entity_label="claim",
            )
            if claim.ClaimStatus not in {"INTIMATED", "REOPENED"}:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Cannot register claim from status '{claim.ClaimStatus}'",
                )
            claim.ClaimStatus = "REGISTERED"
            claim.InsurerClaimRef = payload.insurer_claim_ref
            if payload.remarks:
                claim.Remarks = payload.remarks
            claim.UpdateDate = datetime.utcnow()
            claim.UpdateUser = ctx.user_id
            await self.db.commit()
            await self.db.refresh(claim)
            return self._to_claim_response(claim)

    async def update_survey(
        self,
        current_user: User,
        claim_id: int,
        payload: ClaimSurveyUpdateRequest,
    ) -> ClaimResponse:
        ctx = self._get_principal(current_user)
        self._require_role_in(ctx, _CLAIM_UPDATE_NORM, "assign surveyor or update survey")

        async with _PHASE10_WRITE_LOCK:
            claim = await self.repo.get_claim_for_update(claim_id)
            if claim is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")
            self._enforce_entity_ownership(
                ctx,
                entity_branch_id=claim.BranchId,
                entity_agent_id=claim.AgentId,
                entity_franchise_id=claim.FranchiseId,
                entity_sales_ex_id=claim.SalesExId,
                entity_label="claim",
            )
            if claim.ClaimStatus not in {"INTIMATED", "REGISTERED", "UNDER_SURVEY", "ASSESSED", "REOPENED"}:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Cannot assign surveyor in claim status '{claim.ClaimStatus}'",
                )
            survey_dt = (payload.survey_date or datetime.utcnow()).replace(tzinfo=None)
            if survey_dt.date() < claim.IntimationDate.replace(tzinfo=None).date():
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Survey date cannot be earlier than claim intimation date",
                )
            claim.SurveyorName = payload.surveyor_name
            claim.SurveyorMobile = payload.surveyor_mobile
            claim.SurveyorLicenseNo = payload.surveyor_license_no
            claim.SurveyDate = survey_dt
            claim.ClaimStatus = "UNDER_SURVEY"
            if payload.remarks:
                claim.Remarks = payload.remarks
            claim.UpdateDate = datetime.utcnow()
            claim.UpdateUser = ctx.user_id
            await self.db.commit()
            await self.db.refresh(claim)
            return self._to_claim_response(claim)

    async def assess_claim(
        self,
        current_user: User,
        claim_id: int,
        payload: ClaimAssessmentRequest,
    ) -> ClaimResponse:
        ctx = self._get_principal(current_user)
        self._require_role_in(ctx, _CLAIM_UPDATE_NORM, "assess claims")

        async with _PHASE10_WRITE_LOCK:
            claim = await self.repo.get_claim_for_update(claim_id)
            if claim is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")
            self._enforce_entity_ownership(
                ctx,
                entity_branch_id=claim.BranchId,
                entity_agent_id=claim.AgentId,
                entity_franchise_id=claim.FranchiseId,
                entity_sales_ex_id=claim.SalesExId,
                entity_label="claim",
            )
            if claim.ClaimStatus not in {"INTIMATED", "REGISTERED", "UNDER_SURVEY", "ASSESSED", "REOPENED"}:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Cannot assess claim in status '{claim.ClaimStatus}'",
                )
            policy = await self.repo.get_policy_readonly(claim.TransanctionId)
            sum_insured = round_2dp(_to_decimal(policy.SumInsured)) if policy else ZERO

            approved_amt = calculate_claim_assessment_pure(
                assessed_loss_amount=payload.assessed_loss_amount,
                depreciation_amount=payload.depreciation_amount,
                deductible_amount=payload.deductible_amount,
                excess_amount=payload.excess_amount,
                salvage_amount=payload.salvage_amount,
                sum_insured=sum_insured,
                claim_type=claim.ClaimType,
            )

            claim.AssessedLossAmount = round_2dp(payload.assessed_loss_amount)
            claim.DepreciationAmount = round_2dp(payload.depreciation_amount)
            claim.DeductibleAmount = round_2dp(payload.deductible_amount)
            claim.ExcessAmount = round_2dp(payload.excess_amount)
            claim.SalvageAmount = round_2dp(payload.salvage_amount)
            claim.ApprovedAmount = approved_amt
            claim.ClaimStatus = "ASSESSED"
            if payload.remarks:
                claim.Remarks = payload.remarks
            claim.UpdateDate = datetime.utcnow()
            claim.UpdateUser = ctx.user_id
            await self.db.commit()
            await self.db.refresh(claim)
            return self._to_claim_response(claim)

    async def approve_claim(
        self,
        current_user: User,
        claim_id: int,
        payload: ClaimApprovalRequest,
    ) -> ClaimResponse:
        ctx = self._get_principal(current_user)
        self._require_role_in(ctx, _CLAIM_APPROVE_SETTLE_NORM, "approve claims")

        async with _PHASE10_WRITE_LOCK:
            claim = await self.repo.get_claim_for_update(claim_id)
            if claim is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")
            self._enforce_entity_ownership(
                ctx,
                entity_branch_id=claim.BranchId,
                entity_agent_id=claim.AgentId,
                entity_franchise_id=claim.FranchiseId,
                entity_sales_ex_id=claim.SalesExId,
                entity_label="claim",
            )
            if claim.ClaimStatus not in {"ASSESSED", "REOPENED"}:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Cannot approve claim in status '{claim.ClaimStatus}'; claim must be ASSESSED first",
                )
            assessed_net = round_2dp(_to_decimal(claim.ApprovedAmount))
            if assessed_net <= ZERO:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Cannot approve claim with ApprovedAmount <= 0.00",
                )

            if payload.approved_amount is not None:
                override_amt = round_2dp(payload.approved_amount)
                if override_amt > assessed_net:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=f"Approved amount ({override_amt}) cannot exceed assessed net amount ({assessed_net})",
                    )
                claim.ApprovedAmount = override_amt

            claim.ClaimStatus = "APPROVED"
            if payload.remarks:
                claim.Remarks = payload.remarks
            claim.UpdateDate = datetime.utcnow()
            claim.UpdateUser = ctx.user_id
            await self.db.commit()
            await self.db.refresh(claim)
            return self._to_claim_response(claim)

    async def settle_claim(
        self,
        current_user: User,
        claim_id: int,
        payload: ClaimSettlementRequest,
        *,
        simulate_failure_at: Optional[str] = None,
    ) -> ClaimResponse:
        ctx = self._get_principal(current_user)
        self._require_role_in(ctx, _CLAIM_APPROVE_SETTLE_NORM, "settle claims")

        async with _PHASE10_WRITE_LOCK:
            try:
                claim = await self.repo.get_claim_for_update(claim_id)
                if claim is None:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")
                self._enforce_entity_ownership(
                    ctx,
                    entity_branch_id=claim.BranchId,
                    entity_agent_id=claim.AgentId,
                    entity_franchise_id=claim.FranchiseId,
                    entity_sales_ex_id=claim.SalesExId,
                    entity_label="claim",
                )

                # Idempotent replay check
                if claim.ClaimStatus == "SETTLED":
                    if (
                        payload.idempotency_key
                        and claim.IdempotencyKey == payload.idempotency_key
                        and round_2dp(_to_decimal(claim.SettledAmount)) == round_2dp(payload.settled_amount)
                    ):
                        return self._to_claim_response(claim)
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Claim {claim.ClaimNo} is already SETTLED",
                    )

                if claim.ClaimStatus != "APPROVED":
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Cannot settle claim in status '{claim.ClaimStatus}'; claim must be APPROVED first",
                    )

                ins_pay, cust_pay, gar_pay = calculate_claim_settlement_split_pure(
                    settled_amount=payload.settled_amount,
                    approved_amount=round_2dp(_to_decimal(claim.ApprovedAmount)),
                    payee_type=payload.payee_type,
                )

                now_dt = (payload.settlement_date or datetime.utcnow()).replace(tzinfo=None)
                settled_amt = round_2dp(payload.settled_amount)

                claim.SettledAmount = settled_amt
                claim.InsurerPayableAmount = ins_pay
                claim.CustomerPayableAmount = cust_pay
                claim.GaragePayableAmount = gar_pay
                claim.PayeeType = payload.payee_type
                claim.PaymentMode = payload.payment_mode
                claim.PaymentDocNo = payload.payment_doc_no
                claim.SettlementDate = now_dt
                if payload.insurer_claim_ref:
                    claim.InsurerClaimRef = payload.insurer_claim_ref
                _, prev_bill, prev_icl, prev_il = self._decode_final_bill_remarks(claim.Remarks)
                eff_bill = payload.bill_amount if payload.bill_amount is not None else prev_bill
                eff_icl = payload.icl_amount if payload.icl_amount is not None else prev_icl
                eff_il = (
                    payload.il_amount
                    if payload.il_amount is not None
                    else (settled_amt if prev_il is None else prev_il)
                )
                base_remarks, _, _, _ = self._decode_final_bill_remarks(
                    payload.remarks if payload.remarks is not None else claim.Remarks
                )
                claim.Remarks = self._encode_final_bill_remarks(
                    base_remarks,
                    bill_amount=eff_bill,
                    icl_amount=eff_icl,
                    il_amount=eff_il,
                )
                if payload.idempotency_key:
                    claim.IdempotencyKey = payload.idempotency_key
                claim.ClaimStatus = "SETTLED"
                claim.UpdateDate = datetime.utcnow()
                claim.UpdateUser = ctx.user_id

                # LBR-123 Parity (CL_ClaimNew.aspx.cs / sp_InsertClaimTransaction):
                # Claims are settled directly between the Insurance Company and Customer/Garage.
                # Broker ledger (tbl_account) has ZERO postings on claim settlement.
                await self.db.flush()

                if simulate_failure_at == "BEFORE_COMMIT":
                    raise RuntimeError("Simulated fault BEFORE_COMMIT in settle_claim")

                await self.db.commit()
                await self.db.refresh(claim)
                return self._to_claim_response(claim)
            except HTTPException:
                await self.db.rollback()
                raise
            except Exception as exc:
                await self.db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Atomic claim settlement rolled back: {exc}",
                ) from exc

    async def reverse_claim_settlement(
        self,
        current_user: User,
        claim_id: int,
        payload: ClaimActionRemarksRequest,
    ) -> ClaimResponse:
        ctx = self._get_principal(current_user)
        self._require_role_in(ctx, _CLAIM_APPROVE_SETTLE_NORM, "reverse claim settlements")

        async with _PHASE10_WRITE_LOCK:
            claim = await self.repo.get_claim_for_update(claim_id)
            if claim is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")
            self._enforce_entity_ownership(
                ctx,
                entity_branch_id=claim.BranchId,
                entity_agent_id=claim.AgentId,
                entity_franchise_id=claim.FranchiseId,
                entity_sales_ex_id=claim.SalesExId,
                entity_label="claim",
            )
            if claim.ClaimStatus != "SETTLED":
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Cannot reverse settlement for claim in status '{claim.ClaimStatus}'",
                )
            settled_amt = round_2dp(_to_decimal(claim.SettledAmount))
            if settled_amt <= ZERO:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Claim has no active settled amount to reverse",
                )

            now_dt = datetime.utcnow()
            # LBR-123 Parity: Claim settlement reversal updates claim status/amounts only
            # and posts zero rows in tbl_account.
            claim.SettledAmount = ZERO
            claim.InsurerPayableAmount = ZERO
            claim.CustomerPayableAmount = ZERO
            claim.GaragePayableAmount = ZERO
            claim.ClaimStatus = "APPROVED"
            claim.Remarks = payload.remarks
            claim.UpdateDate = now_dt
            claim.UpdateUser = ctx.user_id

            await self.db.commit()
            await self.db.refresh(claim)
            return self._to_claim_response(claim)

    async def close_claim(
        self,
        current_user: User,
        claim_id: int,
        payload: ClaimActionRemarksRequest,
    ) -> ClaimResponse:
        ctx = self._get_principal(current_user)
        self._require_role_in(ctx, _CLAIM_APPROVE_SETTLE_NORM, "close claims")

        async with _PHASE10_WRITE_LOCK:
            claim = await self.repo.get_claim_for_update(claim_id)
            if claim is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")
            self._enforce_entity_ownership(
                ctx,
                entity_branch_id=claim.BranchId,
                entity_agent_id=claim.AgentId,
                entity_franchise_id=claim.FranchiseId,
                entity_sales_ex_id=claim.SalesExId,
                entity_label="claim",
            )
            if claim.ClaimStatus != "SETTLED":
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Cannot close claim in status '{claim.ClaimStatus}'; claim must be SETTLED first",
                )
            claim.ClaimStatus = "CLOSED"
            claim.Remarks = payload.remarks
            claim.UpdateDate = datetime.utcnow()
            claim.UpdateUser = ctx.user_id
            await self.db.commit()
            await self.db.refresh(claim)
            return self._to_claim_response(claim)

    async def reject_claim(
        self,
        current_user: User,
        claim_id: int,
        payload: ClaimRejectionRequest,
    ) -> ClaimResponse:
        ctx = self._get_principal(current_user)
        self._require_role_in(ctx, _CLAIM_APPROVE_SETTLE_NORM, "reject claims")

        async with _PHASE10_WRITE_LOCK:
            claim = await self.repo.get_claim_for_update(claim_id)
            if claim is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")
            self._enforce_entity_ownership(
                ctx,
                entity_branch_id=claim.BranchId,
                entity_agent_id=claim.AgentId,
                entity_franchise_id=claim.FranchiseId,
                entity_sales_ex_id=claim.SalesExId,
                entity_label="claim",
            )
            if claim.ClaimStatus in {"SETTLED", "CLOSED", "CANCELLED"}:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Cannot reject claim in status '{claim.ClaimStatus}'",
                )
            claim.ClaimStatus = "REJECTED"
            claim.RejectionReason = payload.rejection_reason
            if payload.remarks:
                claim.Remarks = payload.remarks
            claim.UpdateDate = datetime.utcnow()
            claim.UpdateUser = ctx.user_id
            await self.db.commit()
            await self.db.refresh(claim)
            return self._to_claim_response(claim)

    async def cancel_claim(
        self,
        current_user: User,
        claim_id: int,
        payload: ClaimActionRemarksRequest,
    ) -> ClaimResponse:
        ctx = self._get_principal(current_user)
        self._require_role_in(ctx, _CLAIM_UPDATE_NORM, "cancel claims")

        async with _PHASE10_WRITE_LOCK:
            claim = await self.repo.get_claim_for_update(claim_id)
            if claim is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")
            self._enforce_entity_ownership(
                ctx,
                entity_branch_id=claim.BranchId,
                entity_agent_id=claim.AgentId,
                entity_franchise_id=claim.FranchiseId,
                entity_sales_ex_id=claim.SalesExId,
                entity_label="claim",
            )
            if claim.ClaimStatus in {"APPROVED", "SETTLED", "CLOSED"}:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Cannot cancel claim once in status '{claim.ClaimStatus}'",
                )
            claim.ClaimStatus = "CANCELLED"
            claim.Remarks = payload.remarks
            claim.UpdateDate = datetime.utcnow()
            claim.UpdateUser = ctx.user_id
            await self.db.commit()
            await self.db.refresh(claim)
            return self._to_claim_response(claim)

    async def reopen_claim(
        self,
        current_user: User,
        claim_id: int,
        payload: ClaimActionRemarksRequest,
    ) -> ClaimResponse:
        ctx = self._get_principal(current_user)
        self._require_role_in(ctx, _CLAIM_APPROVE_SETTLE_NORM, "reopen claims")

        async with _PHASE10_WRITE_LOCK:
            claim = await self.repo.get_claim_for_update(claim_id)
            if claim is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")
            self._enforce_entity_ownership(
                ctx,
                entity_branch_id=claim.BranchId,
                entity_agent_id=claim.AgentId,
                entity_franchise_id=claim.FranchiseId,
                entity_sales_ex_id=claim.SalesExId,
                entity_label="claim",
            )
            if claim.ClaimStatus not in {"REJECTED", "CLOSED"}:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Only REJECTED or CLOSED claims can be reopened (current: '{claim.ClaimStatus}')",
                )
            claim.ClaimStatus = "REOPENED"
            claim.Remarks = payload.remarks
            claim.UpdateDate = datetime.utcnow()
            claim.UpdateUser = ctx.user_id
            await self.db.commit()
            await self.db.refresh(claim)
            return self._to_claim_response(claim)

    async def attach_claim_document(
        self,
        current_user: User,
        claim_id: int,
        payload: ClaimDocumentCreateRequest,
    ) -> ClaimDocumentResponse:
        ctx = self._get_principal(current_user)
        self._require_role_in(ctx, _CLAIM_CREATE_NORM, "attach claim documents")

        claim = await self.repo.get_claim_readonly(claim_id)
        if claim is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")
        self._enforce_entity_ownership(
            ctx,
            entity_branch_id=claim.BranchId,
            entity_agent_id=claim.AgentId,
            entity_franchise_id=claim.FranchiseId,
            entity_sales_ex_id=claim.SalesExId,
            entity_label="claim",
        )
        now_dt = datetime.utcnow()
        doc = ClaimDocument(
            ClaimId=claim.ClaimId,
            TransanctionId=claim.TransanctionId,
            DocumentType=payload.document_type,
            DocumentName=payload.document_name,
            StorageKey=payload.storage_key,
            VerifiedStatus=payload.verified_status,
            Remarks=payload.remarks,
            isdeleted="0",
            CreateDate=now_dt,
            CreateUser=ctx.user_id,
        )
        self.db.add(doc)
        await self.db.commit()
        await self.db.refresh(doc)
        return ClaimDocumentResponse(
            claim_doc_id=doc.ClaimDocId,
            claim_id=doc.ClaimId,
            transaction_id=doc.TransanctionId,
            document_type=doc.DocumentType,
            document_name=doc.DocumentName,
            storage_key=doc.StorageKey,
            verified_status=doc.VerifiedStatus,
            remarks=doc.Remarks,
            create_date=doc.CreateDate,
        )

    async def list_claim_documents(
        self,
        current_user: User,
        claim_id: int,
    ) -> List[ClaimDocumentResponse]:
        ctx = self._get_principal(current_user)
        self._require_role_in(ctx, _CLAIM_READ_NORM, "read claim documents")

        claim = await self.repo.get_claim_readonly(claim_id)
        if claim is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")
        self._enforce_entity_ownership(
            ctx,
            entity_branch_id=claim.BranchId,
            entity_agent_id=claim.AgentId,
            entity_franchise_id=claim.FranchiseId,
            entity_sales_ex_id=claim.SalesExId,
            entity_label="claim",
        )
        rows = await self.repo.list_claim_documents(claim_id)
        return [
            ClaimDocumentResponse(
                claim_doc_id=d.ClaimDocId,
                claim_id=d.ClaimId,
                transaction_id=d.TransanctionId,
                document_type=d.DocumentType,
                document_name=d.DocumentName,
                storage_key=d.StorageKey,
                verified_status=d.VerifiedStatus,
                remarks=d.Remarks,
                create_date=d.CreateDate,
            )
            for d in rows
        ]

    async def get_claim(self, current_user: User, claim_id: int) -> ClaimResponse:
        ctx = self._get_principal(current_user)
        self._require_role_in(ctx, _CLAIM_READ_NORM, "view claims")

        claim = await self.repo.get_claim_readonly(claim_id)
        if claim is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")
        self._enforce_entity_ownership(
            ctx,
            entity_branch_id=claim.BranchId,
            entity_agent_id=claim.AgentId,
            entity_franchise_id=claim.FranchiseId,
            entity_sales_ex_id=claim.SalesExId,
            entity_label="claim",
        )
        return self._to_claim_response(claim)

    async def list_claims(
        self,
        current_user: User,
        *,
        transaction_id: Optional[int] = None,
        policy_no: Optional[str] = None,
        claim_status: Optional[str] = None,
        claim_type: Optional[str] = None,
        branch_id: Optional[int] = None,
        agent_id: Optional[int] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> ClaimListResponse:
        ctx = self._get_principal(current_user)
        self._require_role_in(ctx, _CLAIM_READ_NORM, "list claims")

        norm = _normalize(ctx.role_name)
        eff_branch = branch_id
        eff_agent = agent_id
        eff_frn: Optional[int] = None
        eff_sales: Optional[int] = None

        if not self._is_cross_branch_role(ctx.role_name):
            if norm in _AGENT_ROLES_NORM:
                eff_agent = ctx.agent_id or ctx.user_id
            elif norm in _FRANCHISE_ROLES_NORM:
                eff_frn = ctx.franchise_id or ctx.user_id
            elif norm in _EMPLOYEE_ROLES_NORM:
                eff_sales = ctx.emp_id or ctx.user_id
            else:
                eff_branch = ctx.branch_id

        rows, total = await self.repo.list_claims(
            transaction_id=transaction_id,
            policy_no=policy_no,
            claim_status=claim_status,
            claim_type=claim_type,
            branch_id=eff_branch,
            agent_id=eff_agent,
            franchise_id=eff_frn,
            sales_ex_id=eff_sales,
            limit=limit,
            offset=offset,
        )
        return ClaimListResponse(
            items=[self._to_claim_response(r) for r in rows],
            total=total,
        )

    # ------------------------------------------------------------------
    # 2. Endorsement & Policy Modification Engine
    # ------------------------------------------------------------------
    async def _compute_endorsement_snapshot_and_impact(
        self,
        policy: Transaction,
        customer: Optional[Customer],
        vehicle: Optional[VehicleDetails],
        endorsement_type: str,
        field_changes: Dict[str, Any],
    ) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Any]]:
        validate_endorsement_field_allowlist(endorsement_type, field_changes)

        before_snap: Dict[str, Any] = {}
        after_snap: Dict[str, Any] = {}

        for key, new_val in field_changes.items():
            if key in CUSTOMER_FIELDS:
                attr_name = CUSTOMER_FIELD_ALIAS_MAP.get(key, key)
                old_val = getattr(customer, attr_name, None) if customer else None
            elif key in VEHICLE_FIELDS:
                attr_name = VEHICLE_FIELD_ALIAS_MAP.get(key, key)
                old_val = getattr(vehicle, attr_name, None) if vehicle else None
            elif key in NOMINEE_VIRTUAL_FIELDS:
                old_val = None
            else:
                old_val = getattr(policy, key, None)

            if isinstance(old_val, Decimal):
                old_val = str(round_2dp(old_val))
            if isinstance(new_val, Decimal):
                new_val = str(round_2dp(new_val))
            before_snap[key] = old_val
            after_snap[key] = new_val

        comp_ag_net = round_2dp(
            _to_decimal(policy.NetCommission_OD)
            + _to_decimal(policy.NetCommission_Net)
            + _to_decimal(policy.NetCommission_Extra)
        )
        old_ag_net = (
            comp_ag_net
            if comp_ag_net > ZERO
            else round_2dp(_to_decimal(policy.NetCommission))
        )

        comp_ag_tds = round_2dp(
            _to_decimal(policy.TdsAmt_OD)
            + _to_decimal(policy.TdsAmt_Net)
            + _to_decimal(policy.TdsAmt_Extra)
        )
        old_ag_tds = (
            comp_ag_tds
            if comp_ag_tds > ZERO
            else round_2dp(_to_decimal(policy.TdsAmt))
        )

        fr_rows = await self.repo.get_franchise_commission_rows_for_update(policy.TransanctionId)
        fr_row = fr_rows[0] if fr_rows else None
        old_fr_net = round_2dp(_to_decimal(fr_row.FranchiseNetComm)) if fr_row else ZERO
        fr_od_pct = round_2dp(_to_decimal(fr_row.Franchisecomm_OD)) if fr_row else ZERO
        fr_net_pct = round_2dp(_to_decimal(fr_row.Franchisecomm_Net)) if fr_row else ZERO
        fr_ext_pct = round_2dp(_to_decimal(fr_row.Franchisecomm_Extra)) if fr_row else ZERO

        comm_paid = str(policy.CommissionPaid or "0").strip() in {"1", "1.0", "1.00", "PAID", "TRUE"}
        ag_rows = await self.repo.get_agent_commission_rows_for_update(policy.TransanctionId)
        if any(round_2dp(_to_decimal(r.PaymentStatus)) == Decimal("1.00") for r in ag_rows):
            comm_paid = True

        current_addons = {
            "AddOn": round_2dp(_to_decimal(policy.AddOn)),
            "TowingChargesAmt": round_2dp(_to_decimal(policy.TowingChargesAmt)),
            "PACovertoOwner": round_2dp(_to_decimal(policy.PACovertoOwner)),
            "PACoverDriverCleaner": round_2dp(_to_decimal(policy.PACoverDriverCleaner)),
            "LegalLiabilitytoPaidDriver": round_2dp(_to_decimal(policy.LegalLiabilitytoPaidDriver)),
            "RoadSidePremium": round_2dp(_to_decimal(policy.RoadSidePremium)),
        }

        impact = calculate_endorsement_financial_impact_pure(
            endorsement_type=endorsement_type,
            field_changes=field_changes,
            old_idv=round_2dp(_to_decimal(policy.SumInsured)),
            old_ncb_pct=round_2dp(_to_decimal(policy.NCB)),
            old_od_premium=round_2dp(_to_decimal(policy.ODPermium)),
            old_tp_premium=round_2dp(_to_decimal(policy.TPPermium)),
            old_net_premium=round_2dp(_to_decimal(policy.NetPermium)),
            old_gst_amount=round_2dp(_to_decimal(policy.GST_Amount)),
            old_final_premium=round_2dp(_to_decimal(policy.Amount)),
            paid_amount=round_2dp(_to_decimal(policy.PaidAmount)),
            agent_comm_od_pct=round_2dp(_to_decimal(policy.AgentComm_OD)),
            agent_comm_net_pct=round_2dp(_to_decimal(policy.AgentComm_Net)),
            agent_comm_extra_pct=round_2dp(_to_decimal(policy.AgentComm_Extra)),
            agent_tds_pct=round_2dp(_to_decimal(policy.tdsPercent) or Decimal("5.00")),
            old_agent_net_comm=old_ag_net,
            old_agent_tds_amt=old_ag_tds,
            franchise_comm_od_pct=fr_od_pct,
            franchise_comm_net_pct=fr_net_pct,
            franchise_comm_extra_pct=fr_ext_pct,
            franchise_tds_pct=round_2dp(_to_decimal(policy.tdsPercent) or Decimal("5.00")),
            old_franchise_net_comm=old_fr_net,
            commission_already_paid=comm_paid,
            current_addon_fields=current_addons,
        )
        snapshot = {"before": before_snap, "after": after_snap}
        return snapshot, impact

    async def preview_endorsement(
        self,
        current_user: User,
        payload: EndorsementCreateRequest,
    ) -> EndorsementPreviewResponse:
        ctx = self._get_principal(current_user)
        self._require_role_in(ctx, _ENDORSEMENT_CREATE_NORM, "preview endorsements")

        policy = await self.repo.get_policy_readonly(payload.transaction_id)
        if policy is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found")
        frn_id = self._extract_policy_franchise_id(policy)
        self._enforce_entity_ownership(
            ctx,
            entity_branch_id=policy.BranchId,
            entity_agent_id=policy.AgentId,
            entity_franchise_id=frn_id,
            entity_sales_ex_id=policy.SalesEx_id,
            entity_label="policy",
        )
        customer = (
            await self.repo.get_customer_for_update(policy.CustomerId)
            if policy.CustomerId
            else None
        )
        vehicle = (
            await self.repo.get_vehicle_for_update(policy.CustVehId)
            if policy.CustVehId
            else None
        )
        snapshot, impact = await self._compute_endorsement_snapshot_and_impact(
            policy, customer, vehicle, payload.endorsement_type, payload.field_changes
        )
        legacy_type_id = payload.legacy_endorsement_type_id or LEGACY_ENDORSEMENT_TYPE_TO_ID_MAP.get(
            payload.endorsement_type
        )
        snapshot["meta"] = {
            "legacy_endorsement_type_id": legacy_type_id,
            "create_new_customer": (
                payload.field_changes.get("CreateNewCustomer", True)
                if payload.endorsement_type == "OWNERSHIP_TRANSFER"
                else bool(payload.create_new_customer or payload.field_changes.get("CreateNewCustomer"))
            ),
            "previous_customer_id": policy.CustomerId,
            "current_customer_id": policy.CustomerId,
        }
        return EndorsementPreviewResponse(
            transaction_id=policy.TransanctionId,
            policy_no=policy.PolicyNo,
            endorsement_type=payload.endorsement_type,
            legacy_endorsement_type_id=legacy_type_id,
            endorsement_category=impact["endorsement_category"],
            field_changes_snapshot=snapshot,
            old_idv=impact["old_idv"],
            new_idv=impact["new_idv"],
            old_ncb_percent=impact["old_ncb_percent"],
            new_ncb_percent=impact["new_ncb_percent"],
            old_od_premium=impact["old_od_premium"],
            new_od_premium=impact["new_od_premium"],
            old_tp_premium=impact["old_tp_premium"],
            new_tp_premium=impact["new_tp_premium"],
            old_net_premium=impact["old_net_premium"],
            new_net_premium=impact["new_net_premium"],
            old_gst_amount=impact["old_gst_amount"],
            new_gst_amount=impact["new_gst_amount"],
            old_final_premium=impact["old_final_premium"],
            new_final_premium=impact["new_final_premium"],
            premium_delta=impact["premium_delta"],
            old_agent_net_comm=impact["old_agent_net_comm"],
            new_agent_net_comm=impact["new_agent_net_comm"],
            agent_comm_delta=impact["agent_comm_delta"],
            old_agent_tds_amt=impact["old_agent_tds_amt"],
            new_agent_tds_amt=impact["new_agent_tds_amt"],
            old_franchise_net_comm=impact["old_franchise_net_comm"],
            new_franchise_net_comm=impact["new_franchise_net_comm"],
            franchise_comm_delta=impact["franchise_comm_delta"],
            commission_recovery_amount=impact["commission_recovery_amount"],
            estimated_refund_amount=impact["estimated_refund_amount"],
            previous_customer_id=policy.CustomerId,
            current_customer_id=policy.CustomerId,
        )

    async def create_endorsement(
        self,
        current_user: User,
        payload: EndorsementCreateRequest,
    ) -> Tuple[EndorsementResponse, bool]:
        ctx = self._get_principal(current_user)
        self._require_role_in(ctx, _ENDORSEMENT_CREATE_NORM, "create endorsements")

        async with _PHASE10_WRITE_LOCK:
            if payload.idempotency_key:
                existing = await self.repo.get_endorsement_by_idempotency_key(payload.idempotency_key)
                if existing is not None:
                    self._enforce_entity_ownership(
                        ctx,
                        entity_branch_id=existing.BranchId,
                        entity_agent_id=existing.AgentId,
                        entity_franchise_id=existing.FranchiseId,
                        entity_sales_ex_id=existing.SalesExId,
                        entity_label="endorsement",
                    )
                    return self._to_endorsement_response(existing), False

            policy = await self.repo.get_policy_for_update(payload.transaction_id)
            if policy is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Booked policy transaction {payload.transaction_id} not found",
                )
            frn_id = self._extract_policy_franchise_id(policy)
            self._enforce_entity_ownership(
                ctx,
                entity_branch_id=policy.BranchId,
                entity_agent_id=policy.AgentId,
                entity_franchise_id=frn_id,
                entity_sales_ex_id=policy.SalesEx_id,
                entity_label="policy",
            )

            if (policy.PolicycancelId or 0) != 0 or (policy.TStatus or "").upper() == "CANCELLED":
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Cannot create an endorsement on a cancelled policy",
                )

            customer = (
                await self.repo.get_customer_for_update(policy.CustomerId)
                if policy.CustomerId
                else None
            )
            vehicle = (
                await self.repo.get_vehicle_for_update(policy.CustVehId)
                if policy.CustVehId
                else None
            )

            snapshot, impact = await self._compute_endorsement_snapshot_and_impact(
                policy, customer, vehicle, payload.endorsement_type, payload.field_changes
            )
            legacy_type_id = payload.legacy_endorsement_type_id or LEGACY_ENDORSEMENT_TYPE_TO_ID_MAP.get(
                payload.endorsement_type
            )
            if payload.endorsement_type == "OWNERSHIP_TRANSFER":
                should_create_new_cust = (
                    False
                    if payload.field_changes.get("CreateNewCustomer") is False
                    else True
                )
            else:
                should_create_new_cust = bool(
                    payload.create_new_customer or payload.field_changes.get("CreateNewCustomer")
                )
            snapshot["meta"] = {
                "legacy_endorsement_type_id": legacy_type_id,
                "create_new_customer": should_create_new_cust,
                "previous_customer_id": policy.CustomerId,
                "current_customer_id": policy.CustomerId,
            }

            now_dt = datetime.utcnow()
            eff_dt = (payload.effective_date or now_dt).replace(tzinfo=None)
            init_status = "SUBMITTED" if payload.submit else "DRAFT"
            temp_no = f"END-TMP-{uuid.uuid4().hex[:12].upper()}"

            end_obj = PolicyEndorsement(
                EndorsementNo=temp_no,
                TransanctionId=policy.TransanctionId,
                PolicyNo=policy.PolicyNo,
                CustomerId=policy.CustomerId,
                CustVehId=policy.CustVehId,
                BranchId=policy.BranchId or ctx.branch_id or 1,
                AgentId=policy.AgentId,
                FranchiseId=frn_id,
                SalesExId=policy.SalesEx_id,
                EndorsementType=payload.endorsement_type,
                EndorsementCategory=impact["endorsement_category"],
                EndorsementStatus=init_status,
                EffectiveDate=eff_dt,
                RequestDate=now_dt,
                FieldChangesJson=json.dumps(snapshot, default=str),
                OldODPremium=impact["old_od_premium"],
                NewODPremium=impact["new_od_premium"],
                OldTPPremium=impact["old_tp_premium"],
                NewTPPremium=impact["new_tp_premium"],
                OldNetPremium=impact["old_net_premium"],
                NewNetPremium=impact["new_net_premium"],
                OldGSTAmount=impact["old_gst_amount"],
                NewGSTAmount=impact["new_gst_amount"],
                OldFinalPremium=impact["old_final_premium"],
                NewFinalPremium=impact["new_final_premium"],
                PremiumDelta=impact["premium_delta"],
                OldNCBPercent=impact["old_ncb_percent"],
                NewNCBPercent=impact["new_ncb_percent"],
                OldIDV=impact["old_idv"],
                NewIDV=impact["new_idv"],
                OldAgentNetComm=impact["old_agent_net_comm"],
                NewAgentNetComm=impact["new_agent_net_comm"],
                AgentCommDelta=impact["agent_comm_delta"],
                OldAgentTdsAmt=impact["old_agent_tds_amt"],
                NewAgentTdsAmt=impact["new_agent_tds_amt"],
                OldFranchiseNetComm=impact["old_franchise_net_comm"],
                NewFranchiseNetComm=impact["new_franchise_net_comm"],
                FranchiseCommDelta=impact["franchise_comm_delta"],
                CommissionRecoveryAmount=impact["commission_recovery_amount"],
                RefundStatus="NONE",
                RefundAmount=impact["estimated_refund_amount"],
                SupportingDocKey=payload.supporting_doc_key,
                Remarks=payload.remarks,
                IdempotencyKey=payload.idempotency_key,
                isdeleted="0",
                CreateDate=now_dt,
                CreateUser=ctx.user_id,
            )
            self.db.add(end_obj)
            await self.db.flush()

            branch_code = end_obj.BranchId or 1
            end_obj.EndorsementNo = f"END-{branch_code}-{now_dt.year}-{end_obj.EndorsementId:06d}"
            await self.db.commit()
            await self.db.refresh(end_obj)
            return self._to_endorsement_response(end_obj), True

    async def submit_endorsement(
        self,
        current_user: User,
        endorsement_id: int,
        payload: EndorsementActionRequest,
    ) -> EndorsementResponse:
        ctx = self._get_principal(current_user)
        self._require_role_in(ctx, _ENDORSEMENT_CREATE_NORM, "submit endorsements")

        async with _PHASE10_WRITE_LOCK:
            end_obj = await self.repo.get_endorsement_for_update(endorsement_id)
            if end_obj is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Endorsement not found")
            self._enforce_entity_ownership(
                ctx,
                entity_branch_id=end_obj.BranchId,
                entity_agent_id=end_obj.AgentId,
                entity_franchise_id=end_obj.FranchiseId,
                entity_sales_ex_id=end_obj.SalesExId,
                entity_label="endorsement",
            )
            if end_obj.EndorsementStatus != "DRAFT":
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Only DRAFT endorsements can be submitted (current: '{end_obj.EndorsementStatus}')",
                )
            end_obj.EndorsementStatus = "SUBMITTED"
            if payload.remarks:
                end_obj.Remarks = payload.remarks
            end_obj.UpdateDate = datetime.utcnow()
            end_obj.UpdateUser = ctx.user_id
            await self.db.commit()
            await self.db.refresh(end_obj)
            return self._to_endorsement_response(end_obj)

    async def approve_endorsement(
        self,
        current_user: User,
        endorsement_id: int,
        payload: EndorsementActionRequest,
    ) -> EndorsementResponse:
        ctx = self._get_principal(current_user)
        self._require_role_in(ctx, _ENDORSEMENT_APPROVE_APPLY_NORM, "approve endorsements")

        async with _PHASE10_WRITE_LOCK:
            end_obj = await self.repo.get_endorsement_for_update(endorsement_id)
            if end_obj is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Endorsement not found")
            self._enforce_entity_ownership(
                ctx,
                entity_branch_id=end_obj.BranchId,
                entity_agent_id=end_obj.AgentId,
                entity_franchise_id=end_obj.FranchiseId,
                entity_sales_ex_id=end_obj.SalesExId,
                entity_label="endorsement",
            )
            if end_obj.EndorsementStatus != "SUBMITTED":
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Cannot approve endorsement in status '{end_obj.EndorsementStatus}'",
                )
            end_obj.EndorsementStatus = "APPROVED"
            if payload.remarks:
                end_obj.Remarks = payload.remarks
            end_obj.UpdateDate = datetime.utcnow()
            end_obj.UpdateUser = ctx.user_id
            await self.db.commit()
            await self.db.refresh(end_obj)
            return self._to_endorsement_response(end_obj)

    async def apply_endorsement(
        self,
        current_user: User,
        endorsement_id: int,
        payload: EndorsementApplyRequest,
        *,
        simulate_failure_at: Optional[str] = None,
    ) -> EndorsementResponse:
        """
        Atomically applies an APPROVED endorsement to:
        - `tbl_customer`, `tbl_vehicledetails`, `tbl_transaction`
        - `tbl_agentcommissionpayment`, `tbl_franchisecommission`
        - `tbl_account` (`AccTransId = 2`, `AccTransId = 3` on `LedgerMId = 1161`, and optional 3-leg `1878` Endorsement Fee split)
        - `tbl_appendorsement` (`EndorsementStatus = "APPLIED"`, `RefundStatus`)
        """
        ctx = self._get_principal(current_user)
        self._require_role_in(ctx, _ENDORSEMENT_APPROVE_APPLY_NORM, "apply endorsements")

        async with _PHASE10_WRITE_LOCK:
            try:
                end_obj = await self.repo.get_endorsement_for_update(endorsement_id)
                if end_obj is None:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Endorsement not found")
                self._enforce_entity_ownership(
                    ctx,
                    entity_branch_id=end_obj.BranchId,
                    entity_agent_id=end_obj.AgentId,
                    entity_franchise_id=end_obj.FranchiseId,
                    entity_sales_ex_id=end_obj.SalesExId,
                    entity_label="endorsement",
                )

                # Idempotent replay check
                if end_obj.EndorsementStatus == "APPLIED":
                    if payload.idempotency_key and end_obj.IdempotencyKey == payload.idempotency_key:
                        return self._to_endorsement_response(end_obj)
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Endorsement {end_obj.EndorsementNo} is already APPLIED",
                    )

                if end_obj.EndorsementStatus != "APPROVED":
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Cannot apply endorsement in status '{end_obj.EndorsementStatus}'; must be APPROVED first",
                    )

                policy = await self.repo.get_policy_for_update(end_obj.TransanctionId)
                if policy is None:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parent policy not found")
                if (policy.PolicycancelId or 0) != 0 or (policy.TStatus or "").upper() == "CANCELLED":
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Cannot apply endorsement to a cancelled policy",
                    )

                customer = (
                    await self.repo.get_customer_for_update(policy.CustomerId)
                    if policy.CustomerId
                    else None
                )
                vehicle = (
                    await self.repo.get_vehicle_for_update(policy.CustVehId)
                    if policy.CustVehId
                    else None
                )

                snap = json.loads(end_obj.FieldChangesJson or "{}")
                after_fields: Dict[str, Any] = snap.get("after", {})
                prev_meta: Dict[str, Any] = snap.get("meta", {}) if isinstance(snap.get("meta"), dict) else {}

                # Re-verify against current policy state so concurrent financial endorsements cannot clobber each other
                re_snap, impact = await self._compute_endorsement_snapshot_and_impact(
                    policy, customer, vehicle, end_obj.EndorsementType, after_fields
                )

                old_cust_id = prev_meta.get("previous_customer_id") or policy.CustomerId
                should_create_new_cust = prev_meta.get(
                    "create_new_customer",
                    end_obj.EndorsementType == "OWNERSHIP_TRANSFER",
                )
                if after_fields.get("CreateNewCustomer") is not None:
                    should_create_new_cust = bool(after_fields.get("CreateNewCustomer"))

                now_dt = datetime.utcnow()
                target_customer = customer
                created_new_customer = False

                # OwnerTransferEndorsement.aspx.cs parity (GAP-P10-003):
                # Ownership transfer creates a new Customer row (NewCustId) and rebinds
                # tbl_vehicledetails.CustomerId and tbl_transaction.CustomerId to NewCustId.
                if end_obj.EndorsementType == "OWNERSHIP_TRANSFER" and should_create_new_cust:
                    if after_fields.get("NewCustomerId") is not None:
                        new_cid = int(after_fields["NewCustomerId"])
                        policy.CustomerId = new_cid
                        end_obj.CustomerId = new_cid
                        if vehicle is not None:
                            vehicle.CustomerId = new_cid
                        created_new_customer = True
                    else:
                        new_cust = Customer(
                            CustomerCode=f"CUST-OT-{uuid.uuid4().hex[:10].upper()}",
                            initial=customer.initial if customer else "MR.",
                            CustFName=customer.CustFName if customer else "NEW",
                            CustMName=customer.CustMName if customer else "",
                            CustLName=customer.CustLName if customer else "OWNER",
                            CustomerType=customer.CustomerType if customer else "INDIVIDUAL",
                            ClientId=customer.ClientId if customer else 0,
                            PerAddrLine1=customer.PerAddrLine1 if customer else "",
                            PerAddrLine2=customer.PerAddrLine2 if customer else "",
                            PerTalukaId=customer.PerTalukaId if customer else 1,
                            PerDistrictId=customer.PerDistrictId if customer else 1,
                            PerStateId=customer.PerStateId if customer else 1,
                            PerPinCode=customer.PerPinCode if customer else "411001",
                            ComAddrLine1=customer.ComAddrLine1 if customer else "",
                            ComAddrLine2=customer.ComAddrLine2 if customer else "",
                            ComTalukaId=customer.ComTalukaId if customer else 1,
                            ComDistrictId=customer.ComDistrictId if customer else 1,
                            ComStateId=customer.ComStateId if customer else 1,
                            ComPinCode=customer.ComPinCode if customer else "411001",
                            MoblieNo1=customer.MoblieNo1 if customer else "9999999999",
                            EMailId=customer.EMailId if customer else "",
                            NomineeName=customer.NomineeName if customer else "",
                            BranchId=policy.BranchId or (customer.BranchId if customer else 1),
                            CreateDate=now_dt,
                            CreateUser=str(ctx.user_id),
                            CompanyName=customer.CompanyName if customer else "",
                            isdeleted="0",
                        )
                        self.db.add(new_cust)
                        await self.db.flush()
                        target_customer = new_cust
                        policy.CustomerId = new_cust.CustomerId
                        end_obj.CustomerId = new_cust.CustomerId
                        if vehicle is not None:
                            vehicle.CustomerId = new_cust.CustomerId
                        created_new_customer = True

                # 1. Apply allowed field changes to Customer, Vehicle, and Policy
                correction_parts: List[str] = []
                for field_name, new_val in after_fields.items():
                    old_val = re_snap["before"].get(field_name)
                    correction_parts.append(f"{field_name}: {old_val} -> {new_val}")
                    if field_name in CUSTOMER_FIELDS and target_customer is not None:
                        attr_name = CUSTOMER_FIELD_ALIAS_MAP.get(field_name, field_name)
                        setattr(target_customer, attr_name, str(new_val))
                    elif field_name in VEHICLE_FIELDS and vehicle is not None:
                        attr_name = VEHICLE_FIELD_ALIAS_MAP.get(field_name, field_name)
                        setattr(vehicle, attr_name, str(new_val))
                    elif field_name in NOMINEE_VIRTUAL_FIELDS:
                        pass
                    elif field_name == "AddOn":
                        policy.AddOn = str(round_2dp(_to_decimal(new_val)))
                    elif hasattr(policy, field_name):
                        setattr(policy, field_name, _to_decimal(new_val))

                re_snap["meta"] = {
                    "legacy_endorsement_type_id": prev_meta.get("legacy_endorsement_type_id")
                    or LEGACY_ENDORSEMENT_TYPE_TO_ID_MAP.get(end_obj.EndorsementType),
                    "create_new_customer": created_new_customer,
                    "previous_customer_id": old_cust_id,
                    "current_customer_id": policy.CustomerId,
                }

                # 2. Apply recalculated premium snapshot onto tbl_transaction
                prem_delta = impact["premium_delta"]
                is_financial = (
                    prem_delta != ZERO
                    or impact["new_od_premium"] != impact["old_od_premium"]
                    or impact["new_tp_premium"] != impact["old_tp_premium"]
                    or impact["new_net_premium"] != impact["old_net_premium"]
                )

                policy.SumInsured = impact["new_idv"]
                policy.NCB = impact["new_ncb_percent"]
                policy.ODPermium = impact["new_od_premium"]
                policy.TPPermium = impact["new_tp_premium"]
                policy.NetPermium = impact["new_net_premium"]
                policy.GST_Amount = impact["new_gst_amount"]
                policy.Amount = impact["new_final_premium"]

                policy.UpdateEntryStatus = 1
                if is_financial:
                    policy.IsRecalculate = 1
                remark_line = f"{end_obj.EndorsementNo} [{end_obj.EndorsementType}]: {payload.remarks or end_obj.Remarks or 'Applied'}"
                policy.UpdateEntryRemark = remark_line[:255]
                policy.CorrectionText = "; ".join(correction_parts)[:300]

                # 3. Payment / Receivable / Refund impact on tbl_transaction
                paid_amt = round_2dp(_to_decimal(policy.PaidAmount))
                new_final = impact["new_final_premium"]
                if prem_delta > ZERO:
                    new_out = max(ZERO, round_2dp(new_final - paid_amt))
                    policy.OutstandingAmount = new_out
                    if new_out > ZERO:
                        policy.pendingStatus = 1
                    end_obj.RefundStatus = "NONE"
                    end_obj.RefundAmount = ZERO
                elif prem_delta < ZERO:
                    if paid_amt > new_final:
                        refund_due = min(abs(prem_delta), round_2dp(paid_amt - new_final))
                        policy.OutstandingAmount = ZERO
                        end_obj.RefundAmount = refund_due
                        end_obj.RefundStatus = "PENDING_APPROVAL"
                    else:
                        policy.OutstandingAmount = max(ZERO, round_2dp(new_final - paid_amt))
                        end_obj.RefundAmount = ZERO
                        end_obj.RefundStatus = "NONE"
                else:
                    end_obj.RefundAmount = ZERO
                    end_obj.RefundStatus = "NONE"

                # 4. Commission & TDS adjustment + Paid-Commission Recovery
                comm_prev = impact["commission_preview"]
                ag_delta = impact["agent_comm_delta"]
                fr_delta = impact["franchise_comm_delta"]

                ag_rows = await self.repo.get_agent_commission_rows_for_update(policy.TransanctionId)
                comm_already_paid = str(policy.CommissionPaid or "0").strip() in {"1", "1.0", "1.00", "PAID", "TRUE"} or any(
                    round_2dp(_to_decimal(r.PaymentStatus)) == Decimal("1.00") for r in ag_rows
                )

                if comm_prev is not None:
                    policy.AgentCommAmt_OD = comm_prev.agent_comm_od_amt
                    policy.TdsAmt_OD = comm_prev.agent_tds_od_amt
                    policy.NetCommission_OD = comm_prev.agent_net_od_amt
                    policy.AgentCommAmt_Net = comm_prev.agent_comm_net_amt
                    policy.TdsAmt_Net = comm_prev.agent_tds_net_amt
                    policy.NetCommission_Net = comm_prev.agent_net_net_amt
                    policy.AgentCommAmt_Extra = comm_prev.agent_comm_extra_amt
                    policy.TdsAmt_Extra = comm_prev.agent_tds_extra_amt
                    policy.NetCommission_Extra = comm_prev.agent_net_extra_amt
                    policy.AgentCommAmt = comm_prev.agent_gross_commission
                    policy.TdsAmt = comm_prev.agent_tds_amount
                    policy.NetCommission = comm_prev.agent_net_commission

                    if not comm_already_paid:
                        unpaid_row = next(
                            (r for r in ag_rows if round_2dp(_to_decimal(r.PaymentStatus)) != Decimal("1.00")),
                            None,
                        )
                        if unpaid_row is not None:
                            unpaid_row.PremiumAmount = impact["new_final_premium"]
                            unpaid_row.NetCommission = comm_prev.agent_net_commission
                            unpaid_row.totalCommision = comm_prev.agent_gross_commission
                            unpaid_row.NetAmount = round_2dp(
                                comm_prev.agent_net_commission - _to_decimal(unpaid_row.AdvAmt)
                            )
                            unpaid_row.NetCommission_OD = comm_prev.agent_net_od_amt
                            unpaid_row.NetCommission_Net = comm_prev.agent_net_net_amt
                            unpaid_row.NetCommission_Extra = comm_prev.agent_net_extra_amt
                            unpaid_row.Narration = f"Updated by {end_obj.EndorsementNo}"
                        end_obj.CommissionRecoveryAmount = ZERO
                    else:
                        # Commission was already paid: never mutate historical PAID rows; insert delta/recovery row
                        if ag_delta < ZERO:
                            end_obj.CommissionRecoveryAmount = abs(ag_delta)
                            rec_row = AgentCommissionPayment(
                                FromDate=now_dt,
                                ToDate=now_dt,
                                TransanctionId=policy.TransanctionId,
                                BranchName=str(policy.BranchId or 1),
                                AgentName=str(policy.AgentId or 0),
                                PremiumAmount=prem_delta,
                                NetCommission=ag_delta,
                                totalCommision=ag_delta,
                                AdvAmt=ZERO,
                                NetAmount=ag_delta,
                                PaymentStatus=Decimal("0.00"),
                                Narration=f"RECOVERY_PENDING: {end_obj.EndorsementNo}",
                                Extra1=end_obj.EndorsementNo,
                                Extra2="RECOVERY_PENDING",
                                isdeleted="0",
                                NetCommission_OD=ag_delta,
                                NetCommission_Net=ZERO,
                                NetCommission_Extra=ZERO,
                                TransDate=now_dt,
                            )
                            self.db.add(rec_row)
                        elif ag_delta > ZERO:
                            end_obj.CommissionRecoveryAmount = ZERO
                            supp_row = AgentCommissionPayment(
                                FromDate=now_dt,
                                ToDate=now_dt,
                                TransanctionId=policy.TransanctionId,
                                BranchName=str(policy.BranchId or 1),
                                AgentName=str(policy.AgentId or 0),
                                PremiumAmount=prem_delta,
                                NetCommission=ag_delta,
                                totalCommision=ag_delta,
                                AdvAmt=ZERO,
                                NetAmount=ag_delta,
                                PaymentStatus=Decimal("0.00"),
                                Narration=f"SUPPLEMENTAL_COMMISSION: {end_obj.EndorsementNo}",
                                Extra1=end_obj.EndorsementNo,
                                Extra2="UNPAID",
                                isdeleted="0",
                                NetCommission_OD=ag_delta,
                                NetCommission_Net=ZERO,
                                NetCommission_Extra=ZERO,
                                TransDate=now_dt,
                            )
                            self.db.add(supp_row)

                    fr_rows = await self.repo.get_franchise_commission_rows_for_update(policy.TransanctionId)
                    if fr_rows and fr_delta != ZERO:
                        fr_row = fr_rows[0]
                        fr_row.FranchiseCommAmt = comm_prev.franchise_gross_commission
                        fr_row.FranchiseTdsAmt = comm_prev.franchise_tds_amount
                        fr_row.FranchiseNetComm = comm_prev.franchise_net_commission
                        fr_row.FranchiseCommAmt_OD = comm_prev.franchise_comm_od_amt
                        fr_row.FranchiseTdsAmt_OD = comm_prev.franchise_tds_od_amt
                        fr_row.FranchiseNetComm_OD = comm_prev.franchise_net_od_amt

                # 5. Post accounting adjustments in tbl_account
                delta_net = round_2dp(impact["new_net_premium"] - impact["old_net_premium"])
                if delta_net != ZERO:
                    # AccTransId = 2 (Insurer Premium Payable: -credit on increase, +debit on decrease)
                    ins_amt = -delta_net
                    self.db.add(
                        self._build_account_row(
                            acc_trans_id=2,
                            account_date=now_dt,
                            ledger_m_id=201,
                            amount=ins_amt,
                            narration=f"Endorsement Insurer Net Delta {end_obj.EndorsementNo}",
                            ref_cust_id=policy.CustomerId or 0,
                            ref_agent_id=policy.AgentId or 0,
                            branch_id=policy.BranchId or 1,
                            payment_type="ENDORSEMENT",
                            extra1=end_obj.EndorsementNo,
                            extra2=end_obj.EndorsementType,
                            doc_no=end_obj.EndorsementId,
                            created_user=ctx.user_id,
                            transaction_id=policy.TransanctionId,
                            cust_veh_id=policy.CustVehId or 0,
                            endorsement_id=end_obj.EndorsementId,
                            trans_id=policy.TransanctionId,
                        )
                    )

                if ag_delta != ZERO:
                    # AccTransId = 3 on LedgerMId = 1161 (Legacy Unclear Commission Control Ledger, GAP-P10-002)
                    comm_amt = -ag_delta
                    self.db.add(
                        self._build_account_row(
                            acc_trans_id=3,
                            account_date=now_dt,
                            ledger_m_id=LEGACY_COMMISSION_CONTROL_LEDGER_ID,
                            amount=comm_amt,
                            narration=f"Endorsement Agent Commission Delta {end_obj.EndorsementNo}",
                            ref_cust_id=policy.CustomerId or 0,
                            ref_agent_id=policy.AgentId or 0,
                            branch_id=policy.BranchId or 1,
                            payment_type="ENDORSEMENT",
                            extra1=end_obj.EndorsementNo,
                            extra2=end_obj.EndorsementType,
                            doc_no=end_obj.EndorsementId,
                            created_user=ctx.user_id,
                            transaction_id=policy.TransanctionId,
                            cust_veh_id=policy.CustVehId or 0,
                            endorsement_id=end_obj.EndorsementId,
                            trans_id=policy.TransanctionId,
                        )
                    )

                # AppEndorsementforApproval.aspx.cs 3-leg Endorsement Fee split (GAP-P10-002 / GAP-P10-003):
                # Leg 1: AccTransId=2, LedgerMId=FromLedgerId, +PaidAmt
                # Leg 2: AccTransId=2, LedgerMId=1878 (Endorsement Income), -CmpAmt
                # Leg 3: AccTransId=1, LedgerMId=PayToLedgerId, -CmpAmt
                # where CmpAmt = Math.Round(PaidAmt - ServiceChargeAmount, 0, AwayFromZero)
                if payload.paid_endorsement_fee is not None and round_2dp(payload.paid_endorsement_fee) > ZERO:
                    paid_fee = round_2dp(payload.paid_endorsement_fee)
                    svc_chg = round_2dp(payload.service_charge_amount or ZERO)
                    cmp_amt = round_rupee(max(ZERO, paid_fee - svc_chg))
                    from_lid = payload.from_ledger_id or 102
                    pay_to_lid = payload.pay_to_ledger_id or 203

                    self.db.add(
                        self._build_account_row(
                            acc_trans_id=2,
                            account_date=now_dt,
                            ledger_m_id=from_lid,
                            amount=paid_fee,
                            narration=f"Endorsement Fee Paid {end_obj.EndorsementNo}",
                            ref_cust_id=policy.CustomerId or 0,
                            ref_agent_id=policy.AgentId or 0,
                            branch_id=policy.BranchId or 1,
                            payment_type="ENDORSEMENT_FEE",
                            extra1=end_obj.EndorsementNo,
                            extra2=end_obj.EndorsementType,
                            doc_no=end_obj.EndorsementId,
                            created_user=ctx.user_id,
                            transaction_id=policy.TransanctionId,
                            cust_veh_id=policy.CustVehId or 0,
                            endorsement_id=end_obj.EndorsementId,
                            trans_id=policy.TransanctionId,
                        )
                    )
                    if cmp_amt > ZERO:
                        self.db.add(
                            self._build_account_row(
                                acc_trans_id=2,
                                account_date=now_dt,
                                ledger_m_id=LEGACY_ENDORSEMENT_INCOME_LEDGER_ID,
                                amount=-cmp_amt,
                                narration=f"Endorsement Income (1878) {end_obj.EndorsementNo}",
                                ref_cust_id=policy.CustomerId or 0,
                                ref_agent_id=policy.AgentId or 0,
                                branch_id=policy.BranchId or 1,
                                payment_type="ENDORSEMENT_FEE",
                                extra1=end_obj.EndorsementNo,
                                extra2=end_obj.EndorsementType,
                                doc_no=end_obj.EndorsementId,
                                created_user=ctx.user_id,
                                transaction_id=policy.TransanctionId,
                                cust_veh_id=policy.CustVehId or 0,
                                endorsement_id=end_obj.EndorsementId,
                                trans_id=policy.TransanctionId,
                            )
                        )
                        self.db.add(
                            self._build_account_row(
                                acc_trans_id=1,
                                account_date=now_dt,
                                ledger_m_id=pay_to_lid,
                                amount=-cmp_amt,
                                narration=f"Endorsement Company Payable {end_obj.EndorsementNo}",
                                ref_cust_id=policy.CustomerId or 0,
                                ref_agent_id=policy.AgentId or 0,
                                branch_id=policy.BranchId or 1,
                                payment_type="ENDORSEMENT_FEE",
                                extra1=end_obj.EndorsementNo,
                                extra2=end_obj.EndorsementType,
                                doc_no=end_obj.EndorsementId,
                                created_user=ctx.user_id,
                                transaction_id=policy.TransanctionId,
                                cust_veh_id=policy.CustVehId or 0,
                                endorsement_id=end_obj.EndorsementId,
                                trans_id=policy.TransanctionId,
                            )
                        )
                    re_snap["meta"]["endorsement_fee"] = {
                        "paid_fee": str(paid_fee),
                        "service_charge": str(svc_chg),
                        "cmp_amt": str(cmp_amt),
                        "from_ledger_id": from_lid,
                        "pay_to_ledger_id": pay_to_lid,
                    }

                end_obj.FieldChangesJson = json.dumps(re_snap, default=str)

                # Update endorsement snapshot & status
                end_obj.EndorsementCategory = impact["endorsement_category"]
                end_obj.OldODPremium = impact["old_od_premium"]
                end_obj.NewODPremium = impact["new_od_premium"]
                end_obj.OldTPPremium = impact["old_tp_premium"]
                end_obj.NewTPPremium = impact["new_tp_premium"]
                end_obj.OldNetPremium = impact["old_net_premium"]
                end_obj.NewNetPremium = impact["new_net_premium"]
                end_obj.OldGSTAmount = impact["old_gst_amount"]
                end_obj.NewGSTAmount = impact["new_gst_amount"]
                end_obj.OldFinalPremium = impact["old_final_premium"]
                end_obj.NewFinalPremium = impact["new_final_premium"]
                end_obj.PremiumDelta = prem_delta
                end_obj.OldNCBPercent = impact["old_ncb_percent"]
                end_obj.NewNCBPercent = impact["new_ncb_percent"]
                end_obj.OldIDV = impact["old_idv"]
                end_obj.NewIDV = impact["new_idv"]
                end_obj.OldAgentNetComm = impact["old_agent_net_comm"]
                end_obj.NewAgentNetComm = impact["new_agent_net_comm"]
                end_obj.AgentCommDelta = ag_delta
                end_obj.OldAgentTdsAmt = impact["old_agent_tds_amt"]
                end_obj.NewAgentTdsAmt = impact["new_agent_tds_amt"]
                end_obj.OldFranchiseNetComm = impact["old_franchise_net_comm"]
                end_obj.NewFranchiseNetComm = impact["new_franchise_net_comm"]
                end_obj.FranchiseCommDelta = fr_delta
                end_obj.EndorsementStatus = "APPLIED"
                if payload.remarks:
                    end_obj.Remarks = payload.remarks
                if payload.idempotency_key:
                    end_obj.IdempotencyKey = payload.idempotency_key
                end_obj.UpdateDate = now_dt
                end_obj.UpdateUser = ctx.user_id

                await self.db.flush()
                if simulate_failure_at == "BEFORE_COMMIT":
                    raise RuntimeError("Simulated fault BEFORE_COMMIT in apply_endorsement")

                await self.db.commit()
                await self.db.refresh(end_obj)
                return self._to_endorsement_response(end_obj)
            except HTTPException:
                await self.db.rollback()
                raise
            except Exception as exc:
                await self.db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Atomic endorsement application rolled back: {exc}",
                ) from exc

    async def reverse_endorsement(
        self,
        current_user: User,
        endorsement_id: int,
        payload: EndorsementActionRequest,
    ) -> EndorsementResponse:
        ctx = self._get_principal(current_user)
        self._require_role_in(ctx, _ENDORSEMENT_APPROVE_APPLY_NORM, "reverse endorsements")

        async with _PHASE10_WRITE_LOCK:
            end_obj = await self.repo.get_endorsement_for_update(endorsement_id)
            if end_obj is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Endorsement not found")
            self._enforce_entity_ownership(
                ctx,
                entity_branch_id=end_obj.BranchId,
                entity_agent_id=end_obj.AgentId,
                entity_franchise_id=end_obj.FranchiseId,
                entity_sales_ex_id=end_obj.SalesExId,
                entity_label="endorsement",
            )
            if end_obj.EndorsementStatus != "APPLIED":
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Only APPLIED endorsements can be reversed (current: '{end_obj.EndorsementStatus}')",
                )
            if end_obj.RefundStatus == "REFUNDED":
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Cannot reverse endorsement while refund is REFUNDED; reverse refund first",
                )

            policy = await self.repo.get_policy_for_update(end_obj.TransanctionId)
            if policy is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parent policy not found")

            snap = json.loads(end_obj.FieldChangesJson or "{}")
            before_fields: Dict[str, Any] = snap.get("before", {})
            meta: Dict[str, Any] = snap.get("meta", {}) if isinstance(snap.get("meta"), dict) else {}

            prev_cust_id = meta.get("previous_customer_id")
            created_new_customer = bool(meta.get("create_new_customer"))
            if prev_cust_id is not None and int(prev_cust_id) != (policy.CustomerId or 0):
                policy.CustomerId = int(prev_cust_id)
                end_obj.CustomerId = int(prev_cust_id)

            customer = (
                await self.repo.get_customer_for_update(policy.CustomerId)
                if policy.CustomerId
                else None
            )
            vehicle = (
                await self.repo.get_vehicle_for_update(policy.CustVehId)
                if policy.CustVehId
                else None
            )
            if prev_cust_id is not None and vehicle is not None:
                vehicle.CustomerId = int(prev_cust_id)
            if prev_cust_id is not None and isinstance(snap.get("meta"), dict):
                snap["meta"]["current_customer_id"] = int(prev_cust_id)
                end_obj.FieldChangesJson = json.dumps(snap, default=str)

            # 1. Restore before fields on Customer, Vehicle, and Policy
            for field_name, old_val in before_fields.items():
                if old_val is None:
                    continue
                if field_name in CUSTOMER_FIELDS and customer is not None and not created_new_customer:
                    attr_name = CUSTOMER_FIELD_ALIAS_MAP.get(field_name, field_name)
                    setattr(customer, attr_name, str(old_val))
                elif field_name in VEHICLE_FIELDS and vehicle is not None:
                    attr_name = VEHICLE_FIELD_ALIAS_MAP.get(field_name, field_name)
                    setattr(vehicle, attr_name, str(old_val))
                elif field_name in NOMINEE_VIRTUAL_FIELDS:
                    pass
                elif field_name == "AddOn":
                    policy.AddOn = str(round_2dp(_to_decimal(old_val)))
                elif hasattr(policy, field_name):
                    setattr(policy, field_name, _to_decimal(old_val))

            # 2. Restore financial values on policy
            policy.SumInsured = round_2dp(_to_decimal(end_obj.OldIDV))
            policy.NCB = round_2dp(_to_decimal(end_obj.OldNCBPercent))
            policy.ODPermium = round_2dp(_to_decimal(end_obj.OldODPremium))
            policy.TPPermium = round_2dp(_to_decimal(end_obj.OldTPPremium))
            policy.NetPermium = round_2dp(_to_decimal(end_obj.OldNetPremium))
            policy.GST_Amount = round_2dp(_to_decimal(end_obj.OldGSTAmount))
            policy.Amount = round_2dp(_to_decimal(end_obj.OldFinalPremium))

            paid_amt = round_2dp(_to_decimal(policy.PaidAmount))
            policy.OutstandingAmount = max(
                ZERO, round_2dp(_to_decimal(end_obj.OldFinalPremium) - paid_amt)
            )
            policy.NetCommission_OD = round_2dp(_to_decimal(end_obj.OldAgentNetComm))
            policy.TdsAmt_OD = round_2dp(_to_decimal(end_obj.OldAgentTdsAmt))

            # 3. Post contra accounting rows in tbl_account
            now_dt = datetime.utcnow()
            delta_net = round_2dp(_to_decimal(end_obj.NewNetPremium) - _to_decimal(end_obj.OldNetPremium))
            if delta_net != ZERO:
                # Opposite of apply_endorsement's (-delta_net) is (+delta_net)
                ins_amt = delta_net
                self.db.add(
                    self._build_account_row(
                        acc_trans_id=2,
                        account_date=now_dt,
                        ledger_m_id=201,
                        amount=ins_amt,
                        narration=f"Reversal of Endorsement Insurer Net Delta {end_obj.EndorsementNo}",
                        ref_cust_id=policy.CustomerId or 0,
                        ref_agent_id=policy.AgentId or 0,
                        branch_id=policy.BranchId or 1,
                        payment_type="ENDORSEMENT_REVERSAL",
                        extra1=end_obj.EndorsementNo,
                        extra2="REVERSAL",
                        doc_no=end_obj.EndorsementId,
                        created_user=ctx.user_id,
                        transaction_id=policy.TransanctionId,
                        cust_veh_id=policy.CustVehId or 0,
                        endorsement_id=end_obj.EndorsementId,
                        trans_id=policy.TransanctionId,
                    )
                )

            ag_delta = round_2dp(_to_decimal(end_obj.AgentCommDelta))
            if ag_delta != ZERO:
                comm_amt = ag_delta
                self.db.add(
                    self._build_account_row(
                        acc_trans_id=3,
                        account_date=now_dt,
                        ledger_m_id=LEGACY_COMMISSION_CONTROL_LEDGER_ID,
                        amount=comm_amt,
                        narration=f"Reversal of Endorsement Agent Commission Delta {end_obj.EndorsementNo}",
                        ref_cust_id=policy.CustomerId or 0,
                        ref_agent_id=policy.AgentId or 0,
                        branch_id=policy.BranchId or 1,
                        payment_type="ENDORSEMENT_REVERSAL",
                        extra1=end_obj.EndorsementNo,
                        extra2="REVERSAL",
                        doc_no=end_obj.EndorsementId,
                        created_user=ctx.user_id,
                        transaction_id=policy.TransanctionId,
                        cust_veh_id=policy.CustVehId or 0,
                        endorsement_id=end_obj.EndorsementId,
                        trans_id=policy.TransanctionId,
                    )
                )

            fee_meta = meta.get("endorsement_fee")
            if isinstance(fee_meta, dict):
                paid_fee = round_2dp(_to_decimal(fee_meta.get("paid_fee")))
                cmp_amt = round_2dp(_to_decimal(fee_meta.get("cmp_amt")))
                from_lid = int(fee_meta.get("from_ledger_id") or 102)
                pay_to_lid = int(fee_meta.get("pay_to_ledger_id") or 203)
                if paid_fee > ZERO:
                    self.db.add(
                        self._build_account_row(
                            acc_trans_id=2,
                            account_date=now_dt,
                            ledger_m_id=from_lid,
                            amount=-paid_fee,
                            narration=f"Reversal of Endorsement Fee Paid {end_obj.EndorsementNo}",
                            ref_cust_id=policy.CustomerId or 0,
                            ref_agent_id=policy.AgentId or 0,
                            branch_id=policy.BranchId or 1,
                            payment_type="ENDORSEMENT_REVERSAL",
                            extra1=end_obj.EndorsementNo,
                            extra2="REVERSAL",
                            doc_no=end_obj.EndorsementId,
                            created_user=ctx.user_id,
                            transaction_id=policy.TransanctionId,
                            cust_veh_id=policy.CustVehId or 0,
                            endorsement_id=end_obj.EndorsementId,
                            trans_id=policy.TransanctionId,
                        )
                    )
                if cmp_amt > ZERO:
                    self.db.add(
                        self._build_account_row(
                            acc_trans_id=2,
                            account_date=now_dt,
                            ledger_m_id=LEGACY_ENDORSEMENT_INCOME_LEDGER_ID,
                            amount=cmp_amt,
                            narration=f"Reversal of Endorsement Income (1878) {end_obj.EndorsementNo}",
                            ref_cust_id=policy.CustomerId or 0,
                            ref_agent_id=policy.AgentId or 0,
                            branch_id=policy.BranchId or 1,
                            payment_type="ENDORSEMENT_REVERSAL",
                            extra1=end_obj.EndorsementNo,
                            extra2="REVERSAL",
                            doc_no=end_obj.EndorsementId,
                            created_user=ctx.user_id,
                            transaction_id=policy.TransanctionId,
                            cust_veh_id=policy.CustVehId or 0,
                            endorsement_id=end_obj.EndorsementId,
                            trans_id=policy.TransanctionId,
                        )
                    )
                    self.db.add(
                        self._build_account_row(
                            acc_trans_id=1,
                            account_date=now_dt,
                            ledger_m_id=pay_to_lid,
                            amount=cmp_amt,
                            narration=f"Reversal of Endorsement Company Payable {end_obj.EndorsementNo}",
                            ref_cust_id=policy.CustomerId or 0,
                            ref_agent_id=policy.AgentId or 0,
                            branch_id=policy.BranchId or 1,
                            payment_type="ENDORSEMENT_REVERSAL",
                            extra1=end_obj.EndorsementNo,
                            extra2="REVERSAL",
                            doc_no=end_obj.EndorsementId,
                            created_user=ctx.user_id,
                            transaction_id=policy.TransanctionId,
                            cust_veh_id=policy.CustVehId or 0,
                            endorsement_id=end_obj.EndorsementId,
                            trans_id=policy.TransanctionId,
                        )
                    )

            end_obj.EndorsementStatus = "REVERSED"
            if end_obj.RefundStatus in {"PENDING_APPROVAL", "APPROVED"}:
                end_obj.RefundStatus = "REVERSED"
            if payload.remarks:
                end_obj.Remarks = payload.remarks
            end_obj.UpdateDate = now_dt
            end_obj.UpdateUser = ctx.user_id

            await self.db.commit()
            await self.db.refresh(end_obj)
            return self._to_endorsement_response(end_obj)

    async def reject_endorsement(
        self,
        current_user: User,
        endorsement_id: int,
        payload: EndorsementRejectRequest,
    ) -> EndorsementResponse:
        ctx = self._get_principal(current_user)
        self._require_role_in(ctx, _ENDORSEMENT_APPROVE_APPLY_NORM, "reject endorsements")

        async with _PHASE10_WRITE_LOCK:
            end_obj = await self.repo.get_endorsement_for_update(endorsement_id)
            if end_obj is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Endorsement not found")
            self._enforce_entity_ownership(
                ctx,
                entity_branch_id=end_obj.BranchId,
                entity_agent_id=end_obj.AgentId,
                entity_franchise_id=end_obj.FranchiseId,
                entity_sales_ex_id=end_obj.SalesExId,
                entity_label="endorsement",
            )
            if end_obj.EndorsementStatus not in {"SUBMITTED", "APPROVED"}:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Cannot reject endorsement in status '{end_obj.EndorsementStatus}'",
                )
            end_obj.EndorsementStatus = "REJECTED"
            end_obj.RejectionReason = payload.rejection_reason
            if payload.remarks:
                end_obj.Remarks = payload.remarks
            end_obj.UpdateDate = datetime.utcnow()
            end_obj.UpdateUser = ctx.user_id
            await self.db.commit()
            await self.db.refresh(end_obj)
            return self._to_endorsement_response(end_obj)

    async def cancel_endorsement(
        self,
        current_user: User,
        endorsement_id: int,
        payload: EndorsementActionRequest,
    ) -> EndorsementResponse:
        ctx = self._get_principal(current_user)
        self._require_role_in(ctx, _ENDORSEMENT_CREATE_NORM, "cancel endorsements")

        async with _PHASE10_WRITE_LOCK:
            end_obj = await self.repo.get_endorsement_for_update(endorsement_id)
            if end_obj is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Endorsement not found")
            self._enforce_entity_ownership(
                ctx,
                entity_branch_id=end_obj.BranchId,
                entity_agent_id=end_obj.AgentId,
                entity_franchise_id=end_obj.FranchiseId,
                entity_sales_ex_id=end_obj.SalesExId,
                entity_label="endorsement",
            )
            if end_obj.EndorsementStatus not in {"DRAFT", "SUBMITTED", "APPROVED"}:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Cannot cancel endorsement in status '{end_obj.EndorsementStatus}'",
                )
            end_obj.EndorsementStatus = "CANCELLED"
            if payload.remarks:
                end_obj.Remarks = payload.remarks
            end_obj.UpdateDate = datetime.utcnow()
            end_obj.UpdateUser = ctx.user_id
            await self.db.commit()
            await self.db.refresh(end_obj)
            return self._to_endorsement_response(end_obj)

    async def get_endorsement(
        self,
        current_user: User,
        endorsement_id: int,
    ) -> EndorsementResponse:
        ctx = self._get_principal(current_user)
        self._require_role_in(ctx, _ENDORSEMENT_READ_NORM, "view endorsements")

        end_obj = await self.repo.get_endorsement_readonly(endorsement_id)
        if end_obj is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Endorsement not found")
        self._enforce_entity_ownership(
            ctx,
            entity_branch_id=end_obj.BranchId,
            entity_agent_id=end_obj.AgentId,
            entity_franchise_id=end_obj.FranchiseId,
            entity_sales_ex_id=end_obj.SalesExId,
            entity_label="endorsement",
        )
        return self._to_endorsement_response(end_obj)

    async def list_endorsements(
        self,
        current_user: User,
        *,
        transaction_id: Optional[int] = None,
        endorsement_status: Optional[str] = None,
        endorsement_type: Optional[str] = None,
        refund_status: Optional[str] = None,
        branch_id: Optional[int] = None,
        agent_id: Optional[int] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> EndorsementListResponse:
        ctx = self._get_principal(current_user)
        self._require_role_in(ctx, _ENDORSEMENT_READ_NORM, "list endorsements")

        norm = _normalize(ctx.role_name)
        eff_branch = branch_id
        eff_agent = agent_id
        eff_frn: Optional[int] = None
        eff_sales: Optional[int] = None

        if not self._is_cross_branch_role(ctx.role_name):
            if norm in _AGENT_ROLES_NORM:
                eff_agent = ctx.agent_id or ctx.user_id
            elif norm in _FRANCHISE_ROLES_NORM:
                eff_frn = ctx.franchise_id or ctx.user_id
            elif norm in _EMPLOYEE_ROLES_NORM:
                eff_sales = ctx.emp_id or ctx.user_id
            else:
                eff_branch = ctx.branch_id

        rows, total = await self.repo.list_endorsements(
            transaction_id=transaction_id,
            endorsement_status=endorsement_status,
            endorsement_type=endorsement_type,
            refund_status=refund_status,
            branch_id=eff_branch,
            agent_id=eff_agent,
            franchise_id=eff_frn,
            sales_ex_id=eff_sales,
            limit=limit,
            offset=offset,
        )
        return EndorsementListResponse(
            items=[self._to_endorsement_response(r) for r in rows],
            total=total,
        )

    # ------------------------------------------------------------------
    # 3. Endorsement Refund Approval, Disbursement & Reversal Engine
    # ------------------------------------------------------------------
    async def list_refunds(
        self,
        current_user: User,
        *,
        transaction_id: Optional[int] = None,
        refund_status: Optional[str] = None,
        branch_id: Optional[int] = None,
    ) -> EndorsementListResponse:
        ctx = self._get_principal(current_user)
        self._require_role_in(ctx, _REFUND_APPROVE_WRITE_NORM, "list refunds")
        return await self.list_endorsements(
            current_user,
            transaction_id=transaction_id,
            refund_status=refund_status,
            branch_id=branch_id,
        )

    async def approve_refund(
        self,
        current_user: User,
        endorsement_id: int,
        payload: RefundActionRequest,
    ) -> EndorsementResponse:
        ctx = self._get_principal(current_user)
        self._require_role_in(ctx, _REFUND_APPROVE_WRITE_NORM, "approve endorsement refunds")

        async with _PHASE10_WRITE_LOCK:
            end_obj = await self.repo.get_endorsement_for_update(endorsement_id)
            if end_obj is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Endorsement not found")
            self._enforce_entity_ownership(
                ctx,
                entity_branch_id=end_obj.BranchId,
                entity_agent_id=end_obj.AgentId,
                entity_franchise_id=end_obj.FranchiseId,
                entity_sales_ex_id=end_obj.SalesExId,
                entity_label="endorsement refund",
            )
            if end_obj.EndorsementStatus != "APPLIED" or end_obj.RefundStatus != "PENDING_APPROVAL":
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Refund cannot be approved in status '{end_obj.RefundStatus}' (endorsement status '{end_obj.EndorsementStatus}')",
                )
            if round_2dp(_to_decimal(end_obj.RefundAmount)) <= ZERO:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Endorsement has no positive RefundAmount to approve",
                )
            end_obj.RefundStatus = "APPROVED"
            if payload.remarks:
                end_obj.Remarks = payload.remarks
            end_obj.UpdateDate = datetime.utcnow()
            end_obj.UpdateUser = ctx.user_id
            await self.db.commit()
            await self.db.refresh(end_obj)
            return self._to_endorsement_response(end_obj)

    async def disburse_refund(
        self,
        current_user: User,
        endorsement_id: int,
        payload: RefundDisburseRequest,
    ) -> EndorsementResponse:
        ctx = self._get_principal(current_user)
        self._require_role_in(ctx, _REFUND_APPROVE_WRITE_NORM, "disburse endorsement refunds")

        async with _PHASE10_WRITE_LOCK:
            end_obj = await self.repo.get_endorsement_for_update(endorsement_id)
            if end_obj is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Endorsement not found")
            self._enforce_entity_ownership(
                ctx,
                entity_branch_id=end_obj.BranchId,
                entity_agent_id=end_obj.AgentId,
                entity_franchise_id=end_obj.FranchiseId,
                entity_sales_ex_id=end_obj.SalesExId,
                entity_label="endorsement refund",
            )

            # Idempotent replay check
            if end_obj.RefundStatus == "REFUNDED":
                if (
                    payload.idempotency_key
                    and end_obj.IdempotencyKey == payload.idempotency_key
                    and end_obj.RefundDocNo == payload.refund_doc_no
                ):
                    return self._to_endorsement_response(end_obj)
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Refund for endorsement {end_obj.EndorsementNo} is already REFUNDED",
                )

            if end_obj.RefundStatus != "APPROVED":
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Cannot disburse refund in status '{end_obj.RefundStatus}'; must be APPROVED first",
                )

            policy = await self.repo.get_policy_for_update(end_obj.TransanctionId)
            if policy is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parent policy not found")

            ref_amt = round_2dp(_to_decimal(end_obj.RefundAmount))
            now_dt = datetime.utcnow()

            # Adjust PaidAmount on policy
            policy.PaidAmount = max(ZERO, round_2dp(_to_decimal(policy.PaidAmount) - ref_amt))

            # Post balanced double-entry refund rows (AccTransId = 17)
            dr_ref = self._build_account_row(
                acc_trans_id=17,
                account_date=now_dt,
                ledger_m_id=204,
                amount=ref_amt,
                narration=f"Endorsement Refund Clearing {end_obj.EndorsementNo} ({payload.refund_doc_no})",
                ref_cust_id=policy.CustomerId or 0,
                ref_agent_id=policy.AgentId or 0,
                branch_id=policy.BranchId or 1,
                payment_type=payload.refund_mode,
                extra1=end_obj.EndorsementNo,
                extra2=payload.refund_doc_no,
                doc_no=end_obj.EndorsementId,
                created_user=ctx.user_id,
                transaction_id=policy.TransanctionId,
                cust_veh_id=policy.CustVehId or 0,
                endorsement_id=end_obj.EndorsementId,
                trans_id=policy.TransanctionId,
            )
            cr_ref = self._build_account_row(
                acc_trans_id=17,
                account_date=now_dt,
                ledger_m_id=102,
                amount=-ref_amt,
                narration=f"Endorsement Refund Payout {end_obj.EndorsementNo} ({payload.refund_doc_no})",
                ref_cust_id=policy.CustomerId or 0,
                ref_agent_id=policy.AgentId or 0,
                branch_id=policy.BranchId or 1,
                payment_type=payload.refund_mode,
                extra1=end_obj.EndorsementNo,
                extra2=payload.refund_doc_no,
                doc_no=end_obj.EndorsementId,
                created_user=ctx.user_id,
                transaction_id=policy.TransanctionId,
                cust_veh_id=policy.CustVehId or 0,
                endorsement_id=end_obj.EndorsementId,
                trans_id=policy.TransanctionId,
            )
            self.db.add(dr_ref)
            self.db.add(cr_ref)

            end_obj.RefundStatus = "REFUNDED"
            end_obj.RefundMode = payload.refund_mode
            end_obj.RefundDocNo = payload.refund_doc_no
            if payload.remarks:
                end_obj.Remarks = payload.remarks
            if payload.idempotency_key:
                end_obj.IdempotencyKey = payload.idempotency_key
            end_obj.UpdateDate = now_dt
            end_obj.UpdateUser = ctx.user_id

            await self.db.commit()
            await self.db.refresh(end_obj)
            return self._to_endorsement_response(end_obj)

    async def reverse_refund(
        self,
        current_user: User,
        endorsement_id: int,
        payload: RefundActionRequest,
    ) -> EndorsementResponse:
        ctx = self._get_principal(current_user)
        self._require_role_in(ctx, _REFUND_APPROVE_WRITE_NORM, "reverse endorsement refunds")

        async with _PHASE10_WRITE_LOCK:
            end_obj = await self.repo.get_endorsement_for_update(endorsement_id)
            if end_obj is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Endorsement not found")
            self._enforce_entity_ownership(
                ctx,
                entity_branch_id=end_obj.BranchId,
                entity_agent_id=end_obj.AgentId,
                entity_franchise_id=end_obj.FranchiseId,
                entity_sales_ex_id=end_obj.SalesExId,
                entity_label="endorsement refund",
            )
            if end_obj.RefundStatus != "REFUNDED":
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Only REFUNDED refunds can be reversed (current: '{end_obj.RefundStatus}')",
                )

            policy = await self.repo.get_policy_for_update(end_obj.TransanctionId)
            if policy is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parent policy not found")

            ref_amt = round_2dp(_to_decimal(end_obj.RefundAmount))
            now_dt = datetime.utcnow()

            policy.PaidAmount = round_2dp(_to_decimal(policy.PaidAmount) + ref_amt)

            dr_contra = self._build_account_row(
                acc_trans_id=18,
                account_date=now_dt,
                ledger_m_id=102,
                amount=ref_amt,
                narration=f"Reversal of Endorsement Refund Payout {end_obj.EndorsementNo}",
                ref_cust_id=policy.CustomerId or 0,
                ref_agent_id=policy.AgentId or 0,
                branch_id=policy.BranchId or 1,
                payment_type=end_obj.RefundMode or "NEFT",
                extra1=end_obj.EndorsementNo,
                extra2="REVERSAL",
                doc_no=end_obj.EndorsementId,
                created_user=ctx.user_id,
                transaction_id=policy.TransanctionId,
                cust_veh_id=policy.CustVehId or 0,
                endorsement_id=end_obj.EndorsementId,
                trans_id=policy.TransanctionId,
            )
            cr_contra = self._build_account_row(
                acc_trans_id=18,
                account_date=now_dt,
                ledger_m_id=204,
                amount=-ref_amt,
                narration=f"Reversal of Endorsement Refund Clearing {end_obj.EndorsementNo}",
                ref_cust_id=policy.CustomerId or 0,
                ref_agent_id=policy.AgentId or 0,
                branch_id=policy.BranchId or 1,
                payment_type=end_obj.RefundMode or "NEFT",
                extra1=end_obj.EndorsementNo,
                extra2="REVERSAL",
                doc_no=end_obj.EndorsementId,
                created_user=ctx.user_id,
                transaction_id=policy.TransanctionId,
                cust_veh_id=policy.CustVehId or 0,
                endorsement_id=end_obj.EndorsementId,
                trans_id=policy.TransanctionId,
            )
            self.db.add(dr_contra)
            self.db.add(cr_contra)

            end_obj.RefundStatus = "REVERSED"
            if payload.remarks:
                end_obj.Remarks = payload.remarks
            end_obj.UpdateDate = now_dt
            end_obj.UpdateUser = ctx.user_id

            await self.db.commit()
            await self.db.refresh(end_obj)
            return self._to_endorsement_response(end_obj)
