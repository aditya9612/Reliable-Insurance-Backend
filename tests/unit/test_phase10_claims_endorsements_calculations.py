"""
Phase 10 Unit Tests — Claims Assessment, Settlement Split, Endorsement Allowlist,
Premium Recalculation Delta, Commission & TDS Adjustment, Paid-Commission Recovery, and Refund Math.
"""
from decimal import Decimal
import pytest
from fastapi import HTTPException

from app.schemas.claims_endorsement import ClaimDocumentCreateRequest
from app.services.claims_endorsement import (
    calculate_claim_assessment_pure,
    calculate_claim_settlement_split_pure,
    calculate_endorsement_financial_impact_pure,
    validate_endorsement_field_allowlist,
)


def test_claim_assessment_pure_exact_math_and_half_up_rounding():
    # Assessed=45000, Dep=5000, Ded=1000, Exc=500, Salv=1500 => 37000.00
    approved = calculate_claim_assessment_pure(
        assessed_loss_amount=Decimal("45000.00"),
        depreciation_amount=Decimal("5000.00"),
        deductible_amount=Decimal("1000.00"),
        excess_amount=Decimal("500.00"),
        salvage_amount=Decimal("1500.00"),
        sum_insured=Decimal("500000.00"),
        claim_type="OD",
    )
    assert approved == Decimal("37000.00")


def test_claim_assessment_idv_cap_enforced_for_od_theft_total_loss():
    with pytest.raises(HTTPException) as exc:
        calculate_claim_assessment_pure(
            assessed_loss_amount=Decimal("550000.00"),
            depreciation_amount=Decimal("10000.00"),
            deductible_amount=Decimal("2000.00"),
            sum_insured=Decimal("500000.00"),
            claim_type="TOTAL_LOSS",
        )
    assert exc.value.status_code == 422
    assert "SumInsured" in exc.value.detail

    # TP claim is statutory and not capped by vehicle OD SumInsured
    tp_approved = calculate_claim_assessment_pure(
        assessed_loss_amount=Decimal("800000.00"),
        sum_insured=Decimal("500000.00"),
        claim_type="TP",
    )
    assert tp_approved == Decimal("800000.00")


def test_claim_assessment_rejects_non_positive_net_or_negative_deductions():
    with pytest.raises(HTTPException) as exc1:
        calculate_claim_assessment_pure(
            assessed_loss_amount=Decimal("5000.00"),
            depreciation_amount=Decimal("4000.00"),
            deductible_amount=Decimal("1500.00"),
        )
    assert exc1.value.status_code == 422

    with pytest.raises(HTTPException) as exc2:
        calculate_claim_assessment_pure(
            assessed_loss_amount=Decimal("10000.00"),
            depreciation_amount=Decimal("-100.00"),
        )
    assert exc2.value.status_code == 422


def test_claim_settlement_split_pure_customer_and_garage():
    ins_c, cust_c, gar_c = calculate_claim_settlement_split_pure(
        settled_amount=Decimal("37000.00"),
        approved_amount=Decimal("37000.00"),
        payee_type="CUSTOMER",
    )
    assert (ins_c, cust_c, gar_c) == (Decimal("37000.00"), Decimal("37000.00"), Decimal("0.00"))

    ins_g, cust_g, gar_g = calculate_claim_settlement_split_pure(
        settled_amount=Decimal("25000.00"),
        approved_amount=Decimal("37000.00"),
        payee_type="GARAGE",
    )
    assert (ins_g, cust_g, gar_g) == (Decimal("25000.00"), Decimal("0.00"), Decimal("25000.00"))

    with pytest.raises(HTTPException) as exc:
        calculate_claim_settlement_split_pure(
            settled_amount=Decimal("37000.01"),
            approved_amount=Decimal("37000.00"),
            payee_type="CUSTOMER",
        )
    assert exc.value.status_code == 422


def test_endorsement_field_allowlist_and_immutable_guard():
    validate_endorsement_field_allowlist("NAME_CORRECTION", {"CustFName": "Aarav", "PanNo": "ABCDE1234F"})
    validate_endorsement_field_allowlist("VEHICLE_REGISTRATION_CORRECTION", {"RegistrationNo": "MH01AB9999"})

    with pytest.raises(HTTPException) as exc_immut:
        validate_endorsement_field_allowlist("NAME_CORRECTION", {"PolicyNo": "HACK-001"})
    assert exc_immut.value.status_code == 422
    assert "immutable" in exc_immut.value.detail

    with pytest.raises(HTTPException) as exc_disallowed:
        validate_endorsement_field_allowlist("ADDRESS_CORRECTION", {"SumInsured": "900000"})
    assert exc_disallowed.value.status_code == 422


def test_endorsement_financial_impact_upward_idv_and_unpaid_commission():
    res = calculate_endorsement_financial_impact_pure(
        endorsement_type="IDV_CHANGE",
        field_changes={"SumInsured": "600000.00"},
        old_idv=Decimal("500000.00"),
        old_ncb_pct=Decimal("20.00"),
        old_od_premium=Decimal("10000.00"),
        old_tp_premium=Decimal("5000.00"),
        old_net_premium=Decimal("15000.00"),
        old_gst_amount=Decimal("2700.00"),
        old_final_premium=Decimal("17700.00"),
        paid_amount=Decimal("17700.00"),
        agent_comm_od_pct=Decimal("15.00"),
        agent_tds_pct=Decimal("5.00"),
        old_agent_net_comm=Decimal("1425.00"),
        old_agent_tds_amt=Decimal("75.00"),
        commission_already_paid=False,
    )
    assert res["endorsement_category"] == "ADDITIONAL_PREMIUM"
    assert res["new_od_premium"] == Decimal("12000.00")
    assert res["new_net_premium"] == Decimal("17000.00")
    assert res["new_gst_amount"] == Decimal("3060.00")
    assert res["new_final_premium"] == Decimal("20060.00")
    assert res["premium_delta"] == Decimal("2360.00")
    # New OD comm: 12000 * 15% = 1800, TDS 5% = 90, Net = 1710 => delta = +285.00
    assert res["new_agent_net_comm"] == Decimal("1710.00")
    assert res["agent_comm_delta"] == Decimal("285.00")
    assert res["commission_recovery_amount"] == Decimal("0.00")
    assert res["estimated_refund_amount"] == Decimal("0.00")


def test_endorsement_financial_impact_downward_idv_paid_commission_recovery_and_refund():
    res = calculate_endorsement_financial_impact_pure(
        endorsement_type="IDV_CHANGE",
        field_changes={"SumInsured": "400000.00"},
        old_idv=Decimal("500000.00"),
        old_ncb_pct=Decimal("20.00"),
        old_od_premium=Decimal("10000.00"),
        old_tp_premium=Decimal("5000.00"),
        old_net_premium=Decimal("15000.00"),
        old_gst_amount=Decimal("2700.00"),
        old_final_premium=Decimal("17700.00"),
        paid_amount=Decimal("17700.00"),
        agent_comm_od_pct=Decimal("15.00"),
        agent_tds_pct=Decimal("5.00"),
        old_agent_net_comm=Decimal("1425.00"),
        old_agent_tds_amt=Decimal("75.00"),
        commission_already_paid=True,
    )
    assert res["endorsement_category"] == "REFUND_PREMIUM"
    assert res["new_od_premium"] == Decimal("8000.00")
    assert res["new_net_premium"] == Decimal("13000.00")
    assert res["new_gst_amount"] == Decimal("2340.00")
    assert res["new_final_premium"] == Decimal("15340.00")
    assert res["premium_delta"] == Decimal("-2360.00")
    assert res["estimated_refund_amount"] == Decimal("2360.00")
    # New OD comm: 8000 * 15% = 1200, TDS 5% = 60, Net = 1140 => delta = -285.00
    assert res["new_agent_net_comm"] == Decimal("1140.00")
    assert res["agent_comm_delta"] == Decimal("-285.00")
    assert res["commission_recovery_amount"] == Decimal("285.00")


def test_claim_document_safe_storage_key_validation():
    valid_doc = ClaimDocumentCreateRequest(
        document_type="FIR",
        document_name="fir_report.pdf",
        storage_key="claims/2026/clm_0001/fir_report.pdf",
    )
    assert valid_doc.storage_key == "claims/2026/clm_0001/fir_report.pdf"

    with pytest.raises(Exception):
        ClaimDocumentCreateRequest(
            document_type="FIR",
            document_name="fir.pdf",
            storage_key=r"D:\Inetpub\wwwroot\Uploads\fir.pdf",
        )

    with pytest.raises(Exception):
        ClaimDocumentCreateRequest(
            document_type="FIR",
            document_name="fir.pdf",
            storage_key="claims/../../etc/passwd",
        )


def test_gap_p10_003_legacy_endorsement_type_id_1_to_22_mapping_and_ncb_recovery():
    """
    GAP-P10-003 (LBR-126 / LBR-128):
    - All 22 legacy EndorsementTypeId values (1..22) resolve deterministically to canonical types.
    - EndorsementCreateRequest accepts legacy_endorsement_type_id without requiring endorsement_type.
    - NCB_RECOVERY (EndorsementTypeId = 13) supports direct NcbRecovAmt recovery.
    """
    from app.schemas.claims_endorsement import (
        EndorsementCreateRequest,
        LEGACY_ENDORSEMENT_TYPE_ID_MAP,
    )

    assert len(LEGACY_ENDORSEMENT_TYPE_ID_MAP) == 22
    assert set(LEGACY_ENDORSEMENT_TYPE_ID_MAP.keys()) == set(range(1, 23))

    # EndorsementTypeId = 12 -> OWNERSHIP_TRANSFER
    req_12 = EndorsementCreateRequest(
        transaction_id=1001,
        legacy_endorsement_type_id=12,
        field_changes={"CustFName": "NewOwner"},
    )
    assert req_12.endorsement_type == "OWNERSHIP_TRANSFER"
    assert req_12.legacy_endorsement_type_id == 12

    # EndorsementTypeId = 13 -> NCB_RECOVERY with NcbRecovAmt
    req_13 = EndorsementCreateRequest(
        transaction_id=1001,
        legacy_endorsement_type_id=13,
        field_changes={"NcbRecovAmt": "2000.00"},
    )
    assert req_13.endorsement_type == "NCB_RECOVERY"
    validate_endorsement_field_allowlist(req_13.endorsement_type, req_13.field_changes)

    res_ncb_recov = calculate_endorsement_financial_impact_pure(
        endorsement_type="NCB_RECOVERY",
        field_changes={"NcbRecovAmt": "2000.00"},
        old_idv=Decimal("500000.00"),
        old_ncb_pct=Decimal("20.00"),
        old_od_premium=Decimal("8000.00"),
        old_tp_premium=Decimal("5000.00"),
        old_net_premium=Decimal("13000.00"),
        old_gst_amount=Decimal("2340.00"),
        old_final_premium=Decimal("15340.00"),
        paid_amount=Decimal("15340.00"),
        agent_comm_od_pct=Decimal("15.00"),
        agent_tds_pct=Decimal("5.00"),
        old_agent_net_comm=Decimal("1140.00"),
        old_agent_tds_amt=Decimal("60.00"),
        commission_already_paid=False,
    )
    assert res_ncb_recov["endorsement_category"] == "ADDITIONAL_PREMIUM"
    assert res_ncb_recov["new_od_premium"] == Decimal("10000.00")
    assert res_ncb_recov["new_ncb_percent"] == Decimal("0.00")
    assert res_ncb_recov["premium_delta"] == Decimal("2360.00")

