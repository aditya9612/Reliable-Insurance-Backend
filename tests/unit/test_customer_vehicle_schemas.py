from datetime import datetime, date
import pytest
from pydantic import ValidationError

from app.schemas.customer import CustomerCreate, CustomerUpdate, CustomerResponse
from app.schemas.vehicle import VehicleCreate, VehicleUpdate, VehicleResponse


class DummyCustomerORM:
    CustomerId = 101
    CustomerCode = "101"
    initial = "Mr."
    CustFName = "RAHUL"
    CustMName = "K"
    CustLName = "SHARMA"
    CustomerType = "Individual"
    ClientId = 1
    PerAddrLine1 = "FLAT 101"
    PerAddrLine2 = "MAIN ROAD"
    PerTalukaId = 1
    PerDistrictId = 2
    PerStateId = 3
    PerPinCode = "411001"
    ComAddrLine1 = "FLAT 101"
    ComAddrLine2 = "MAIN ROAD"
    ComTalukaId = 1
    ComDistrictId = 2
    ComStateId = 3
    ComPinCode = "411001"
    MoblieNo1 = "9876543210"
    MoblieNo2 = "9876543211"
    Gender = "Male"
    MaritalStatus = "Married"
    PAN_No = "abcde1234f"
    AadharNo = "123456789012"
    DateOfBirth = date(1990, 5, 15)
    EMailId = "RAHUL@EXAMPLE.COM"
    NomineeName = "ANITA SHARMA"
    BranchId = 10
    CreateDate = datetime(2026, 1, 1, 10, 0, 0)
    CreateUser = "admin"
    UpdateDate = datetime(2026, 1, 2, 11, 0, 0)
    UpdateUser = "admin"
    Extra1 = "10-12-2015"
    Extra2 = None
    CompanyName = "ACME"
    isdeleted = "0"


class DummyVehicleORM:
    CustVehId = 501
    CustomerId = 101
    RegistrationNo = "MH12AB1234"
    ChaiseNo = "CHASSIS999"
    EngineNo = "ENGINE888"
    MfgMonth = "05"
    MfgYear = "2023"
    Ex_ShowroomPrice = "800000"
    FuelTypeId = 1
    Veh_Type_ID = 2
    Veh_Sub_Type_ID = 3
    Make_ID = 4
    Model_ID = 5
    Variant_ID = 6
    VehiclePurDate = datetime(2023, 5, 20, 0, 0, 0)
    SeatsCapacity = "5"
    EnginePower = "1197"
    TransTonnageCapacity = ""
    VehicleWeight = "1100"
    VehicleRegDate = datetime(2023, 6, 1, 0, 0, 0)
    RTOId = 1
    BranchId = 10
    CorporateClientId = 1
    CreateDate = datetime(2026, 1, 1, 10, 0, 0)
    CreatedUser = "admin"
    UpdatedDate = datetime(2026, 1, 2, 11, 0, 0)
    UpdatedUser = "admin"
    Extra1 = None
    Extra2 = None
    FinancialYear = "2024-2025"
    VehicleVariant = "VXI"
    isdeleted = "0"


def test_customer_create_casing_and_defaults():
    """Verify CustomerCreate normalizes names and addresses to uppercase, but preserves PAN_No casing."""
    payload = CustomerCreate(
        cust_f_name="  john  ",
        cust_m_name="  william  ",
        cust_l_name="  smith  ",
        per_addr_line1="  123 baker street  ",
        per_addr_line2="  suite 4  ",
        pan_no="  abcde1234f  ",
        aadhar_no="  987654321012  ",
        email_id="  john.smith@example.com  ",
        nominee_name="  mary smith  ",
        marital_status="  ",
        extra1="",
    )
    assert payload.cust_f_name == "JOHN"
    assert payload.cust_m_name == "WILLIAM"
    assert payload.cust_l_name == "SMITH"
    assert payload.per_addr_line1 == "123 BAKER STREET"
    assert payload.per_addr_line2 == "SUITE 4"
    # Legacy audit verified PAN_No is NOT uppercased in C# code-behind
    assert payload.pan_no == "abcde1234f"
    assert payload.aadhar_no == "987654321012"
    assert payload.email_id == "JOHN.SMITH@EXAMPLE.COM"
    assert payload.nominee_name == "MARY SMITH"
    # Empty strings normalized to None
    assert payload.marital_status is None
    assert payload.extra1 is None
    assert payload.customer_type == "Individual"
    assert payload.client_id == 1


def test_customer_create_alias_support():
    """Verify CustomerCreate accepts legacy PascalCase parameter aliases."""
    payload = CustomerCreate.model_validate({
        "CustFName": "AMIT",
        "CustLName": "PATEL",
        "MoblieNo1": "9876543210",
        "CustomerCode": "CUST-001",
        "BranchId": 5,
    })
    assert payload.cust_f_name == "AMIT"
    assert payload.cust_l_name == "PATEL"
    assert payload.moblie_no1 == "9876543210"
    assert payload.customer_code == "CUST-001"
    assert payload.branch_id == 5


def test_customer_response_orm_mapping():
    """Verify CustomerResponse properly validates and serializes from SQLAlchemy ORM entity."""
    orm_cust = DummyCustomerORM()
    resp = CustomerResponse.model_validate(orm_cust)
    data = resp.model_dump()
    assert data["customer_id"] == 101
    assert data["customer_code"] == "101"
    assert data["cust_f_name"] == "RAHUL"
    assert data["cust_l_name"] == "SHARMA"
    assert data["pan_no"] == "abcde1234f"
    assert data["company_name"] == "ACME"
    assert data["isdeleted"] == "0"


def test_vehicle_create_financial_year_required():
    """Verify VehicleCreate raises ValidationError if FinancialYear is omitted or empty."""
    with pytest.raises(ValidationError):
        VehicleCreate(
            registration_no="MH12AB1234",
            # financial_year omitted
        )

    with pytest.raises(ValidationError):
        VehicleCreate(
            registration_no="MH12AB1234",
            financial_year="   ",
        )


def test_vehicle_create_casing_and_chassis_alias():
    """Verify VehicleCreate uppercases technical specs and accepts chaise_no / chassis_no aliases."""
    payload1 = VehicleCreate(
        financial_year="2024-2025",
        registration_no="  mh12ab1234  ",
        chaise_no="  chass123  ",
        engine_no="  eng456  ",
        mfg_year="  2022  ",
        seats_capacity="  5  ",
        engine_power="  1197cc  ",
        vehicle_weight="  1050kg  ",
    )
    assert payload1.registration_no == "MH12AB1234"
    assert payload1.chaise_no == "CHASS123"
    assert payload1.engine_no == "ENG456"
    assert payload1.mfg_year == "2022"
    assert payload1.seats_capacity == "5"
    assert payload1.engine_power == "1197CC"
    assert payload1.vehicle_weight == "1050KG"

    # Test chassis_no alias
    payload2 = VehicleCreate.model_validate({
        "FinancialYear": "2024-2025",
        "chassis_no": "chass999",
    })
    assert payload2.chaise_no == "CHASS999"


def test_vehicle_response_orm_mapping():
    """Verify VehicleResponse validates and serializes from SQLAlchemy ORM entity."""
    orm_veh = DummyVehicleORM()
    resp = VehicleResponse.model_validate(orm_veh)
    data = resp.model_dump()
    assert data["cust_veh_id"] == 501
    assert data["customer_id"] == 101
    assert data["registration_no"] == "MH12AB1234"
    assert data["chaise_no"] == "CHASSIS999"
    assert data["financial_year"] == "2024-2025"
    assert data["isdeleted"] == "0"
