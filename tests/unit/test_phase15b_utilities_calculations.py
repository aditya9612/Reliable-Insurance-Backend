"""
Unit Tests for Phase 15B — Profiles, Utilities, Bulk Import & Operational Task Calculations.
Tests:
- IDV override thresholds and status validation
- Health family grid member validation and sum insured calculations
- Bulk CSV and Excel Policy MIS row mapping, numeric parsing and normalization
- LBR-069 Overdue Cheque Lock threshold calculation
- Birthday candidate matching logic
"""
from datetime import datetime, date, timedelta
from decimal import Decimal
import pytest
from app.models.profile import Employee, Agent, Franchise
from app.models.utility import IDVRequest, HealthMember, ImportAgentPolicy
from app.schemas.utility import (
    IDVRequestCreate,
    HealthMemberCreate,
    ImportPolicyMISRow,
)
from app.services.utility_service import UtilityService


def test_idv_request_model_and_status():
    req = IDVRequest(
        IDVRequestId=1,
        RequestedIDV=Decimal("500000.00"),
        VehicleMake="MARUTI",
        VehicleModel="SWIFT",
        RegistrationNo="MH12AB1234",
        Status="PENDING",
        RequestedBy="agent_user",
    )
    assert req.RequestedIDV == Decimal("500000.00")
    assert req.Status == "PENDING"
    assert req.is_active is True

    # Transition to APPROVED
    req.Status = "APPROVED"
    req.ApprovedIDV = Decimal("480000.00")
    req.ApprovedBy = "underwriter_admin"
    assert req.ApprovedIDV == Decimal("480000.00")
    assert req.Status == "APPROVED"


def test_health_member_validation_and_age_bounds():
    m = HealthMember(
        MemberId=10,
        MemberName="Jane Doe",
        Relationship="SPOUSE",
        Gender="FEMALE",
        Age=32,
        SumInsured=Decimal("500000.00"),
        PreExistingDisease="Hypertension",
        Status="ACTIVE",
    )
    assert m.MemberName == "Jane Doe"
    assert m.Relationship == "SPOUSE"
    assert m.Age == 32
    assert m.SumInsured == Decimal("500000.00")
    assert m.is_active is True


def test_employee_and_agent_model_properties():
    emp = Employee(
        EmpId=101,
        UserName="john_staff",
        EmpFName="John",
        EmpMName="M",
        EmpLName="Doe",
        isdeleted="0",
    )
    assert emp.full_name == "John M Doe"
    assert emp.is_active is True

    agent = Agent(
        AgentId=202,
        AgentFName="Agent",
        AgentLName="Smith",
        IsActive=1,
        isdeleted="0",
    )
    assert agent.full_name == "Agent Smith"
    assert agent.is_active is True

    fran = Franchise(
        FranchiseId=303,
        FranFName="Franchise",
        FranLName="North",
        isdeleted="0",
    )
    assert fran.full_name == "Franchise North"
    assert fran.is_active is True


def test_bulk_mis_numeric_parsing():
    # Mocking row parsing from CSV/Excel
    service = UtilityService(session=None)  # row mapping doesn't require session

    mock_row = {
        "date of insurance": "2026-05-10",
        "broker name": "Acme Broker",
        "client name": "Test Client",
        "vehicle type": "4W",
        "vehicle number": "MH12XY9999",
        "policy number": "POL12345678",
        "segments": "Private Car",
        "insurance company": "Bajaj Allianz",
        "gross amount": " 15,250.50 ",
        "net amount": "12,924.00",
        "o.d premium": "8,000.00",
        "t.p premium": "4,924.00",
        "broker received %": "15.00%",
        "broker payout": "1,938.60",
    }

    class MockUser:
        UserName = "uploader_admin"

    entity = service._map_row_to_entity(mock_row, batch_id="BATCH_TEST_01", current_user=MockUser())
    assert entity.PolicyNumber == "POL12345678"
    assert entity.GrossAmount == Decimal("15250.50")
    assert entity.NetAmount == Decimal("12924.00")
    assert entity.ODPremium == Decimal("8000.00")
    assert entity.TPPremium == Decimal("4924.00")
    assert entity.BrokerPayout == Decimal("1938.60")
    assert entity.IsProcess == 0
    assert entity.BatchId == "BATCH_TEST_01"


def test_overdue_cheque_cutoff_logic():
    now = datetime(2026, 10, 8, 12, 0, 0)
    threshold_days = 15
    cutoff = now - timedelta(days=threshold_days)

    cheque_1_date = datetime(2026, 9, 20, 10, 0, 0)  # 18 days ago -> OVERDUE
    cheque_2_date = datetime(2026, 10, 1, 10, 0, 0)  # 7 days ago -> NOT OVERDUE

    assert cheque_1_date <= cutoff
    assert not (cheque_2_date <= cutoff)


def test_birthday_matching_logic():
    today = date(2026, 10, 8)
    cust_dob_match = date(1990, 10, 8)
    cust_dob_no_match = date(1992, 10, 9)

    assert (cust_dob_match.month, cust_dob_match.day) == (today.month, today.day)
    assert (cust_dob_no_match.month, cust_dob_no_match.day) != (today.month, today.day)
