"""
Unit tests for Comprehensive Schema Validation Defect Remediation.
Verifies rejection of ghost records, extra fields, invalid mobile, PAN, Aadhaar,
PIN, IFSC, Email, date bounds, claim deductions, and wallet reversal fields.
"""
from datetime import date, datetime, timedelta
from decimal import Decimal
import pytest
from pydantic import ValidationError

from app.schemas.profile import (
    EmployeeCreate,
    EmployeeUpdate,
    AgentCreate,
    AgentUpdate,
    FranchiseCreate,
    FranchiseUpdate,
)
from app.schemas.customer import CustomerCreate, CustomerUpdate
from app.schemas.vehicle import VehicleCreate, VehicleUpdate
from app.schemas.policy import (
    PolicyBookingCreateRequest,
    PolicyBookingUpdateRequest,
    PolicyProposalCreateRequest,
)
from app.schemas.claims_endorsement import (
    ClaimAssessmentRequest,
    ClaimSurveyUpdateRequest,
)
from app.schemas.payment import PaymentReversalRequest
from app.schemas.renewal import CreateRenewalFollowupRequest


# ============================================================================
# 1. Profile Schemas (VAL-REQ-01, VAL-CID-01, VAL-CID-02, VAL-CID-03)
# ============================================================================

def test_employee_create_requires_first_name():
    """VAL-REQ-01: Empty payload must fail validation on EmployeeCreate."""
    with pytest.raises(ValidationError) as exc_info:
        EmployeeCreate.model_validate({})
    errors = exc_info.value.errors()
    assert any(e["loc"] == ("EmpFName",) for e in errors)


def test_employee_create_rejects_whitespace_only_name():
    """REG-01: Whitespace-only string must be rejected for EmpFName."""
    with pytest.raises(ValidationError):
        EmployeeCreate(EmpFName="   ")


def test_employee_create_forbids_extra_fields():
    """VAL-EXT-01: Unexpected attributes on EmployeeCreate must fail validation."""
    with pytest.raises(ValidationError) as exc_info:
        EmployeeCreate.model_validate({
            "EmpFName": "Ramesh",
            "unexpected_field": "hacker_input",
        })
    errors = exc_info.value.errors()
    assert any("extra_forbidden" in e["type"] for e in errors)


def test_employee_contact_and_statutory_validation():
    """VAL-CID-01/02/03: Validates mobile, PAN, Aadhaar, IFSC on Employee."""
    # Valid payload
    emp = EmployeeCreate(
        EmpFName="Ramesh",
        MoblieNo="9876543210",
        MoblieNo1="+91 9876543211",
        EmailId="ramesh@example.com",
        PAN_No="ABCDE1234F",
        AadharNo="123456789012",
        Ifsc_code="sbin0001234",
    )
    assert emp.MoblieNo == "9876543210"
    assert emp.MoblieNo1 == "9876543211"
    assert emp.EmailId == "ramesh@example.com"
    assert emp.PAN_No == "ABCDE1234F"
    assert emp.AadharNo == "123456789012"
    assert emp.Ifsc_code == "SBIN0001234"

    # Invalid mobile (less than 10 digits)
    with pytest.raises(ValidationError):
        EmployeeCreate(EmpFName="Ramesh", MoblieNo="12345")

    # Invalid PAN (format mismatch)
    with pytest.raises(ValidationError):
        EmployeeCreate(EmpFName="Ramesh", PAN_No="INVALIDPAN")

    # Invalid Aadhaar (contains letters)
    with pytest.raises(ValidationError):
        EmployeeCreate(EmpFName="Ramesh", AadharNo="12345678901A")

    # Invalid IFSC (5th char must be 0)
    with pytest.raises(ValidationError):
        EmployeeCreate(EmpFName="Ramesh", Ifsc_code="SBIN1001234")

    # Invalid Email
    with pytest.raises(ValidationError):
        EmployeeCreate(EmpFName="Ramesh", EmailId="invalid-email-address")


def test_agent_create_validation():
    """AgentCreate requires AgentFName, forbids extra fields, validates contacts."""
    # Empty payload rejected
    with pytest.raises(ValidationError) as exc_info:
        AgentCreate.model_validate({})
    assert any(e["loc"] == ("AgentFName",) for e in exc_info.value.errors())

    # Whitespace-only rejected
    with pytest.raises(ValidationError):
        AgentCreate(AgentFName="   ")

    # Extra fields forbidden
    with pytest.raises(ValidationError):
        AgentCreate.model_validate({"AgentFName": "Suresh", "unknown_extra": 123})

    # Valid agent
    agent = AgentCreate(
        AgentFName="Suresh",
        MobileNo="09822011223",
        EmailId="suresh@posp.com",
        PANNo="abcde1234f",
        AadharNo="1234 5678 9012",
    )
    assert agent.MobileNo == "9822011223"
    assert agent.PANNo == "abcde1234f"
    assert agent.AadharNo == "123456789012"


def test_franchise_create_validation():
    """FranchiseCreate requires FranFName, forbids extra fields, validates PIN code."""
    # Empty payload rejected
    with pytest.raises(ValidationError) as exc_info:
        FranchiseCreate.model_validate({})
    assert any(e["loc"] == ("FranFName",) for e in exc_info.value.errors())

    # Whitespace-only rejected
    with pytest.raises(ValidationError):
        FranchiseCreate(FranFName="   ")

    # Extra fields forbidden
    with pytest.raises(ValidationError):
        FranchiseCreate.model_validate({"FranFName": "Nashik Prime", "rogue": True})

    # Valid franchise
    fran = FranchiseCreate(
        FranFName="Nashik Prime",
        PerPinCode="411001",
        MoblieNo1="9988776655",
    )
    assert fran.FranFName == "Nashik Prime"
    assert fran.PerPinCode == "411001"

    # Invalid PIN code (must be 6 digits, non-zero first digit)
    with pytest.raises(ValidationError):
        FranchiseCreate(FranFName="Nashik Prime", PerPinCode="011001")
    with pytest.raises(ValidationError):
        FranchiseCreate(FranFName="Nashik Prime", PerPinCode="4110")


def test_user_mobile_validation():
    """MOB-01: Validates and normalizes user mobile numbers."""
    from app.schemas.user import UserCreate, UserUpdate
    user = UserCreate(UserName="test_user", UserPassword="Password123!", mobile_no="+91 9898989898")
    assert user.mobile_no == "9898989898"

    with pytest.raises(ValidationError):
        UserCreate(UserName="test_user", UserPassword="Password123!", mobile_no="12345")


# ============================================================================
# 2. Customer & Vehicle Schemas (VAL-EXT-01, VAL-CID-01, VAL-CID-02, VAL-CID-03)
# ============================================================================

def test_customer_create_and_update_ignores_extra_immutable_fields():
    """Customer mutation schemas safely ignore undeclared extra attributes and immutable fields."""
    c = CustomerCreate.model_validate({
        "CustFName": "AMIT",
        "per_addr_line1": "Road 1",
        "unknown_extra": "ignored",
    })
    assert c.cust_f_name == "AMIT"

    up = CustomerUpdate.model_validate({
        "cust_f_name": "AMIT",
        "CompanyName": "HACKED_CORP",
        "CustomerCode": "HACKED_CODE",
    })
    assert up.cust_f_name == "AMIT"
    assert not hasattr(up, "CompanyName") or getattr(up, "CompanyName", None) is None


def test_customer_validation_rules():
    """CustomerBase validates mobile, PAN, Aadhaar, PIN, and Email syntax."""
    cust = CustomerCreate(
        cust_f_name="John",
        moblie_no1="+91 9822012345",
        pan_no="abcde1234f",
        aadhar_no="123456789012",
        per_pin_code="411038",
        email_id="suresh.patil@example.com",
    )
    assert cust.moblie_no1 == "9822012345"
    assert cust.pan_no == "abcde1234f"
    assert cust.aadhar_no == "123456789012"
    assert cust.per_pin_code == "411038"
    assert cust.email_id == "SURESH.PATIL@EXAMPLE.COM"

    # Invalid mobile
    with pytest.raises(ValidationError):
        CustomerCreate(cust_f_name="John", moblie_no1="5551234567")

    # Invalid PAN
    with pytest.raises(ValidationError):
        CustomerCreate(cust_f_name="John", pan_no="12345")

    # Invalid Aadhaar
    with pytest.raises(ValidationError):
        CustomerCreate(cust_f_name="John", aadhar_no="123")

    # Invalid PIN
    with pytest.raises(ValidationError):
        CustomerCreate(cust_f_name="John", per_pin_code="41100")

    # Invalid Email
    with pytest.raises(ValidationError):
        CustomerCreate(cust_f_name="John", email_id="not-an-email")


def test_vehicle_create_and_update_ignores_extra_immutable_fields():
    """Vehicle mutation schemas safely ignore undeclared extra attributes and immutable fields."""
    v = VehicleCreate.model_validate({
        "FinancialYear": "2024-2025",
        "RegistrationNo": "MH12AB1234",
        "unsupported_key": "ignored",
    })
    assert v.registration_no == "MH12AB1234"

    up = VehicleUpdate.model_validate({
        "RegistrationNo": "MH12AB1234",
        "financial_year": "HACKED_FY",
    })
    assert up.registration_no == "MH12AB1234"


# ============================================================================
# 3. Policy Date Validation (VAL-BUS-01)
# ============================================================================

def test_policy_booking_dates_validation():
    """Policy booking rejects expiry_date prior to risk_start_date."""
    today = date.today()
    yesterday = today - timedelta(days=1)

    with pytest.raises(ValidationError) as exc_info:
        PolicyBookingCreateRequest(
            customer_id=1,
            cust_veh_id=1,
            risk_start_date=today,
            expiry_date=yesterday,
        )
    assert "expiry_date cannot be earlier than risk_start_date" in str(exc_info.value)

    # Valid dates
    valid = PolicyBookingCreateRequest(
        customer_id=1,
        cust_veh_id=1,
        risk_start_date=today,
        expiry_date=today + timedelta(days=364),
    )
    assert valid.expiry_date > valid.risk_start_date

    # Equal dates allowed (e.g. single-day transit policy)
    equal_dates = PolicyBookingCreateRequest(
        customer_id=1,
        cust_veh_id=1,
        risk_start_date=today,
        expiry_date=today,
    )
    assert equal_dates.expiry_date == equal_dates.risk_start_date


def test_policy_booking_update_dates_validation():
    """PolicyBookingUpdateRequest rejects invalid date sequence."""
    today = date.today()
    with pytest.raises(ValidationError):
        PolicyBookingUpdateRequest(
            risk_start_date=today,
            expiry_date=today - timedelta(days=5),
        )


def test_policy_proposal_dates_and_contacts_validation():
    """PolicyProposalCreateRequest validates contact, email, and dates."""
    today = date.today()
    with pytest.raises(ValidationError):
        PolicyProposalCreateRequest(
            customer_name="Anita Roy",
            contact_no="12345",
            registration_no="MH12AB1234",
            od_premium=Decimal("1000.00"),
            tp_premium=Decimal("500.00"),
        )

    with pytest.raises(ValidationError):
        PolicyProposalCreateRequest(
            customer_name="Anita Roy",
            contact_no="9876543210",
            email_id="not-an-email",
            registration_no="MH12AB1234",
            od_premium=Decimal("1000.00"),
            tp_premium=Decimal("500.00"),
        )

    with pytest.raises(ValidationError):
        PolicyProposalCreateRequest(
            customer_name="Anita Roy",
            contact_no="9876543210",
            registration_no="MH12AB1234",
            start_date=today,
            expiry_date=today - timedelta(days=1),
            od_premium=Decimal("1000.00"),
            tp_premium=Decimal("500.00"),
        )


# ============================================================================
# 4. Claims Deductions Validation (VAL-BUS-02)
# ============================================================================

def test_claim_assessment_deductions_exceeding_loss():
    """Total deductions exceeding assessed_loss_amount must be rejected."""
    with pytest.raises(ValidationError) as exc_info:
        ClaimAssessmentRequest(
            assessed_loss_amount=Decimal("10000.00"),
            depreciation_amount=Decimal("4000.00"),
            deductible_amount=Decimal("3000.00"),
            excess_amount=Decimal("2000.00"),
            salvage_amount=Decimal("2000.00"),  # Total = 11000.00 > 10000.00
        )
    assert "Total deductions" in str(exc_info.value)

    # Valid assessment
    req = ClaimAssessmentRequest(
        assessed_loss_amount=Decimal("10000.00"),
        depreciation_amount=Decimal("2000.00"),
        deductible_amount=Decimal("1000.00"),
        excess_amount=Decimal("500.00"),
        salvage_amount=Decimal("500.00"),  # Total = 4000.00 <= 10000.00
    )
    assert req.assessed_loss_amount == Decimal("10000.00")


def test_claim_surveyor_mobile_validation():
    """ClaimSurveyUpdateRequest validates surveyor mobile format."""
    with pytest.raises(ValidationError):
        ClaimSurveyUpdateRequest(
            surveyor_name="R. K. Verma",
            surveyor_license_no="SLA-12345",
            surveyor_mobile="12345",
        )

    req = ClaimSurveyUpdateRequest(
        surveyor_name="R. K. Verma",
        surveyor_license_no="SLA-12345",
        surveyor_mobile="9811122233",
    )
    assert req.surveyor_mobile == "9811122233"


# ============================================================================
# 5. Payment Reversal Wallet Target Validation (VAL-BUS-03)
# ============================================================================

def test_payment_reversal_wallet_fields_pair_validation():
    """PaymentReversalRequest requires wallet_owner_type and wallet_owner_id together."""
    # Type without ID rejected
    with pytest.raises(ValidationError):
        PaymentReversalRequest(
            reason="Incorrect Payment",
            wallet_owner_type="AGENT",
            wallet_owner_id=None,
        )

    # ID without Type rejected
    with pytest.raises(ValidationError):
        PaymentReversalRequest(
            reason="Incorrect Payment",
            wallet_owner_type=None,
            wallet_owner_id=601,
        )

    # Both provided accepted
    req1 = PaymentReversalRequest(
        reason="Incorrect Payment",
        wallet_owner_type="AGENT",
        wallet_owner_id=601,
    )
    assert req1.wallet_owner_type == "AGENT"
    assert req1.wallet_owner_id == 601

    # Neither provided accepted (e.g. for Cash/Cheque reversal)
    req2 = PaymentReversalRequest(
        reason="Cash Reversal",
    )
    assert req2.wallet_owner_type is None
    assert req2.wallet_owner_id is None


# ============================================================================
# 6. Renewal Followup Validation (VAL-NUM-02)
# ============================================================================

def test_renewal_followup_total_premium_and_mobile():
    """CreateRenewalFollowupRequest rejects negative total_premium and invalid mobile."""
    # Negative premium rejected
    with pytest.raises(ValidationError):
        CreateRenewalFollowupRequest(
            transaction_id=1,
            registration_number="MH12XY1000",
            financial_year="2024-2025",
            remark="Followup",
            followup_date=datetime.utcnow(),
            total_premium=Decimal("-100.00"),
        )

    # Invalid mobile rejected
    with pytest.raises(ValidationError):
        CreateRenewalFollowupRequest(
            transaction_id=1,
            registration_number="MH12XY1000",
            financial_year="2024-2025",
            remark="Followup",
            followup_date=datetime.utcnow(),
            mobile_number="invalid_phone",
        )

    # Valid
    req = CreateRenewalFollowupRequest(
        transaction_id=1,
        registration_number="MH12XY1000",
        financial_year="2024-2025",
        remark="Followup",
        followup_date=datetime.utcnow(),
        total_premium=Decimal("12500.00"),
        mobile_number="9850299999",
    )
    assert req.total_premium == Decimal("12500.00")
    assert req.mobile_number == "9850299999"


# ============================================================================
# 7. Policy Partial Update & Chronology Merging (LEGACY PARITY AUDIT)
# ============================================================================

@pytest.mark.asyncio
async def test_policy_booking_partial_update_date_scenarios():
    """
    Verifies that PolicyBookingService.update_policy validates the effective merged
    pair of dates (persisted + incoming) before committing to the database.
    Covers all 7 partial update matrix scenarios:
    1. Update only expiry_date earlier than persisted start date (Rejected HTTP 400)
    2. Update only risk_start_date later than persisted expiry date (Rejected HTTP 400)
    3. Update both dates with valid later expiry (Accepted)
    4. Omit both dates (Dates preserved, other fields updated)
    5. Submit equal dates (Same-day transit policy, Accepted)
    6. Update only expiry_date to valid later date (Accepted)
    7. Update only risk_start_date to valid earlier date (Accepted)
    """
    from unittest.mock import AsyncMock, MagicMock
    from fastapi import HTTPException
    from app.models.transaction import Transaction
    from app.models.user import User
    from app.services.policy_booking import PolicyBookingService

    mock_session = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.rollback = AsyncMock()
    service = PolicyBookingService(mock_session)
    service.repo = AsyncMock()
    service._build_policy_response = AsyncMock(return_value={"status": "ok"})

    admin_user = MagicMock(spec=User)
    admin_user.UserId = 1
    admin_user.UserName = "admin"
    admin_user.UserRole = "ADMIN"
    admin_user.BranchId = 1
    admin_user.partner_user_id = None

    def create_persisted_tx():
        tx = Transaction()
        tx.TransanctionId = 100
        tx.BranchId = 1
        tx.AgentId = 1
        tx.PolicyNo = "POL100"
        tx.RiskStartdate = datetime(2026, 5, 1, 0, 0, 0)
        tx.ExpiryDate = datetime(2027, 4, 30, 0, 0, 0)
        tx.DeuDate = datetime(2027, 4, 30, 0, 0, 0)
        return tx

    # 1. Update only expiry_date earlier than persisted risk_start_date -> 400 + Rollback
    service.repo.get_transaction_by_id = AsyncMock(return_value=create_persisted_tx())
    payload1 = PolicyBookingUpdateRequest(expiry_date=date(2026, 4, 30))
    with pytest.raises(HTTPException) as exc1:
        await service.update_policy(100, payload1, admin_user)
    assert exc1.value.status_code == 400
    assert "Policy ExpiryDate cannot be earlier than RiskStartdate" in exc1.value.detail
    mock_session.rollback.assert_called()
    mock_session.commit.assert_not_called()

    # 2. Update only risk_start_date later than persisted expiry_date -> 400 + Rollback
    mock_session.reset_mock()
    service.repo.get_transaction_by_id = AsyncMock(return_value=create_persisted_tx())
    payload2 = PolicyBookingUpdateRequest(risk_start_date=date(2027, 5, 2))
    with pytest.raises(HTTPException) as exc2:
        await service.update_policy(100, payload2, admin_user)
    assert exc2.value.status_code == 400
    assert "Policy ExpiryDate cannot be earlier than RiskStartdate" in exc2.value.detail
    mock_session.rollback.assert_called()
    mock_session.commit.assert_not_called()

    # 3. Update both dates with valid later expiry -> Commit
    mock_session.reset_mock()
    tx3 = create_persisted_tx()
    service.repo.get_transaction_by_id = AsyncMock(return_value=tx3)
    payload3 = PolicyBookingUpdateRequest(risk_start_date=date(2026, 6, 1), expiry_date=date(2027, 5, 31))
    await service.update_policy(100, payload3, admin_user)
    assert tx3.RiskStartdate == datetime(2026, 6, 1, 0, 0, 0)
    assert tx3.ExpiryDate == datetime(2027, 5, 31, 0, 0, 0)
    mock_session.commit.assert_called_once()

    # 4. Omit both dates (dates unchanged) -> Commit
    mock_session.reset_mock()
    tx4 = create_persisted_tx()
    service.repo.get_transaction_by_id = AsyncMock(return_value=tx4)
    payload4 = PolicyBookingUpdateRequest(remark="Only remark updated")
    await service.update_policy(100, payload4, admin_user)
    assert tx4.RiskStartdate == datetime(2026, 5, 1, 0, 0, 0)
    assert tx4.ExpiryDate == datetime(2027, 4, 30, 0, 0, 0)
    assert tx4.Remark == "Only remark updated"
    mock_session.commit.assert_called_once()

    # 5. Submit equal dates (same-day expiry, valid for commercial transit) -> Commit
    mock_session.reset_mock()
    tx5 = create_persisted_tx()
    service.repo.get_transaction_by_id = AsyncMock(return_value=tx5)
    payload5 = PolicyBookingUpdateRequest(risk_start_date=date(2026, 5, 1), expiry_date=date(2026, 5, 1))
    await service.update_policy(100, payload5, admin_user)
    assert tx5.RiskStartdate == tx5.ExpiryDate == datetime(2026, 5, 1, 0, 0, 0)
    mock_session.commit.assert_called_once()

    # 6. Update only expiry_date to valid later date -> Commit
    mock_session.reset_mock()
    tx6 = create_persisted_tx()
    service.repo.get_transaction_by_id = AsyncMock(return_value=tx6)
    payload6 = PolicyBookingUpdateRequest(expiry_date=date(2027, 6, 30))
    await service.update_policy(100, payload6, admin_user)
    assert tx6.RiskStartdate == datetime(2026, 5, 1, 0, 0, 0)
    assert tx6.ExpiryDate == datetime(2027, 6, 30, 0, 0, 0)
    mock_session.commit.assert_called_once()

    # 7. Update only risk_start_date to valid earlier date -> Commit
    mock_session.reset_mock()
    tx7 = create_persisted_tx()
    service.repo.get_transaction_by_id = AsyncMock(return_value=tx7)
    payload7 = PolicyBookingUpdateRequest(risk_start_date=date(2026, 4, 1))
    await service.update_policy(100, payload7, admin_user)
    assert tx7.RiskStartdate == datetime(2026, 4, 1, 0, 0, 0)
    assert tx7.ExpiryDate == datetime(2027, 4, 30, 0, 0, 0)
    mock_session.commit.assert_called_once()


# ============================================================================
# 8. Calendar-Correct Default Expiry & Leap-Year Boundaries
# ============================================================================

def test_legacy_calendar_correct_default_expiry_boundaries():
    """
    Verifies that compute_legacy_default_expiry exactly replicates legacy C#
    `DateTime.AddYears(years).AddDays(-1)` across leap years, leap day (Feb 29),
    month ends, year ends, and multi-year tenures.
    """
    from app.services.policy_booking import compute_legacy_default_expiry

    test_matrix = [
        # (risk_start_date, tenure_years, expected_csharp_result)
        ("2023-01-01", 1, "2023-12-31"),
        ("2024-01-01", 1, "2024-12-31"),  # Leap year 2024 (366 days, 365 inclusive)
        ("2024-02-28", 1, "2025-02-27"),  # Leap year before Feb 29
        ("2024-02-29", 1, "2025-02-27"),  # Leap day! .NET AddYears(1) clamps to Feb 28, minus 1 day = Feb 27
        ("2024-03-01", 1, "2025-02-28"),  # Post-leap-day start
        ("2025-02-28", 1, "2026-02-27"),
        ("2025-03-01", 1, "2026-02-28"),
        ("2023-12-31", 1, "2024-12-30"),  # Spans leap year 2024
        ("2024-12-31", 1, "2025-12-30"),
        ("2023-01-31", 1, "2024-01-30"),  # Month-end date
        # Non-motor multi-year tenures
        ("2023-01-01", 2, "2024-12-31"),  # 2 years
        ("2023-01-01", 3, "2025-12-31"),  # 3 years
        ("2023-01-01", 5, "2027-12-31"),  # 5 years
        # Leap-day start when target year IS a leap year (2024 + 4 = 2028)
        ("2024-02-29", 4, "2028-02-28"),  # 4 years: Feb 29 2028 - 1 day = Feb 28 2028
    ]

    for start_str, tenure, expected_str in test_matrix:
        start_d = date.fromisoformat(start_str)
        expected_d = date.fromisoformat(expected_str)
        actual_d = compute_legacy_default_expiry(start_d, years=tenure)
        assert actual_d == expected_d, (
            f"Failed on start={start_str} tenure={tenure}: "
            f"expected {expected_str}, got {actual_d.isoformat()}"
        )
        assert type(actual_d) is date, f"Expected return type date, got {type(actual_d)}"

    # Datetime inputs with time component normalized to pure date
    dt_input1 = datetime(2024, 1, 1, 14, 30, 45)
    exp_dt1 = compute_legacy_default_expiry(dt_input1, years=1)
    assert type(exp_dt1) is date
    assert exp_dt1 == date(2024, 12, 31)

    dt_input2 = datetime(2024, 2, 29, 23, 59, 59)
    exp_dt2 = compute_legacy_default_expiry(dt_input2, years=1)
    assert type(exp_dt2) is date
    assert exp_dt2 == date(2025, 2, 27)

    # Invalid tenure (zero or negative)
    with pytest.raises(ValueError):
        compute_legacy_default_expiry(date(2024, 1, 1), years=0)

    with pytest.raises(ValueError):
        compute_legacy_default_expiry(date(2024, 1, 1), years=-1)

    # Null start date
    with pytest.raises(ValueError):
        compute_legacy_default_expiry(None, years=1)
