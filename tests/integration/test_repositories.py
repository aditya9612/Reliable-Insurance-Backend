from datetime import datetime
from decimal import Decimal
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.customer import Customer
from app.models.vehicle import VehicleDetails
from app.models.account import Account
from app.models.ledger import LedgerMaster
from app.models.payment import TransactionPayment
from app.models.transaction import Transaction
from app.models.transaction_app import TransactionAppNew
from app.models.commission import FranchiseCommission, AgentCommissionPayment, CutNPayCommPayable

from app.repositories.customer import CustomerRepository
from app.repositories.vehicle import VehicleRepository
from app.repositories.transaction import TransactionRepository
from app.repositories.transaction_app import TransactionAppRepository
from app.repositories.payment import PaymentRepository
from app.repositories.account import AccountRepository
from app.repositories.ledger import LedgerRepository
from app.repositories.commission import (
    FranchiseCommissionRepository,
    AgentCommissionRepository,
    CutNPayCommissionRepository,
)


@pytest.mark.asyncio
async def test_database_isolation_safety(db_session: AsyncSession):
    """
    CRITICAL ARCHITECTURAL CONTRACT:
    The test suite must STRICTLY execute against the independent local 'reliable_insurance_dev' database.
    It MUST NEVER communicate with legacy production database 'brahmainsurance' or remote host.
    """
    result = await db_session.execute(text("SELECT DATABASE()"))
    current_db = result.scalar()
    assert current_db == "reliable_insurance_dev", f"Safety violation: unexpected DB {current_db}"
    assert "localhost" in settings.DATABASE_URL or "127.0.0.1" in settings.DATABASE_URL
    assert "brahmainsurance" not in settings.DATABASE_URL


@pytest.mark.asyncio
async def test_customer_repository_crud(db_session: AsyncSession):
    """Verify CustomerRepository CRUD, unique code lookup, mobile lookup, and count."""
    repo = CustomerRepository(db_session)

    # Create synthetic customer
    customer = Customer(
        CustomerCode="CUST-TEST-001",
        CustFName="TestFirst",
        CustLName="TestLast",
        MoblieNo1="9876543210",
        MoblieNo2="9876543211",
        PAN_No="ABCDE1234F",
        BranchId=1,
    )
    created = await repo.create(customer)
    assert created.CustomerId is not None

    # Lookup by ID
    fetched = await repo.get_by_id(created.CustomerId)
    assert fetched is not None
    assert fetched.CustomerCode == "CUST-TEST-001"
    assert fetched.MoblieNo1 == "9876543210"

    # Lookup by Code
    by_code = await repo.get_by_code("CUST-TEST-001")
    assert by_code is not None
    assert by_code.CustomerId == created.CustomerId

    # Lookup by Mobile
    by_mobile = await repo.get_by_mobile("9876543210")
    assert len(by_mobile) >= 1
    assert by_mobile[0].CustomerId == created.CustomerId

    # Lookup by PAN
    by_pan = await repo.get_by_pan("ABCDE1234F")
    assert len(by_pan) >= 1

    # Exists check
    assert await repo.exists(created.CustomerId) is True
    assert await repo.exists(99999999) is False

    # Count
    cnt = await repo.count()
    assert cnt >= 1

    # Delete
    await repo.delete(created)
    assert await repo.get_by_id(created.CustomerId) is None


@pytest.mark.asyncio
async def test_vehicle_repository_crud(db_session: AsyncSession):
    """Verify VehicleRepository CRUD and lookups preserving RegistrationNo and ChaiseNo."""
    repo = VehicleRepository(db_session)

    vehicle = VehicleDetails(
        CustomerId=101,
        RegistrationNo="MH12AB1234",
        ChaiseNo="CHASSIS-TEST-999",
        EngineNo="ENGINE-TEST-888",
        FinancialYear="2026-2027",
    )
    created = await repo.create(vehicle)
    assert created.CustVehId is not None

    # Lookup by RegistrationNo
    by_reg = await repo.get_by_registration_no("MH12AB1234")
    assert by_reg is not None
    assert by_reg.CustVehId == created.CustVehId

    # Lookup by ChaiseNo (legacy typo column)
    by_chassis = await repo.get_by_chassis_no("CHASSIS-TEST-999")
    assert by_chassis is not None
    assert by_chassis.CustVehId == created.CustVehId

    # Lookup by CustomerId
    by_cust = await repo.get_by_customer_id(101)
    assert len(by_cust) >= 1

    # Non-existent lookup returns None
    assert await repo.get_by_registration_no("NONEXISTENT") is None


@pytest.mark.asyncio
async def test_transaction_repository_crud(db_session: AsyncSession):
    """
    Verify TransactionRepository CRUD and lookups preserving
    ODPermium, TPPermium, NetPermium, TStatus, and TransanctionId.
    """
    repo = TransactionRepository(db_session)

    trans = Transaction(
        InwardNo="INW-2026-001",
        PolicyNo="POL-TEST-2026-001",
        CustomerId=101,
        CustVehId=202,
        BranchId=1,
        AgentId=50,
        ODPermium=Decimal("5000.50"),
        TPPermium=Decimal("2000.00"),
        NetPermium=Decimal("7000.50"),
        TStatus="Pending Approval",
        # All required non-null legacy columns without DB defaults
        AddOnRate=Decimal("0.00"),
        CashBackAmt=Decimal("0.00"),
        CashBackStatus=0,
        ChequeBankStatus=0,
        CreatedIP="127.0.0.1",
        CreatedSystem="Web",
        CutNPay=Decimal("0.00"),
        DeuDate=datetime.now(),
        EWalletAmountUsed=Decimal("0.00"),
        ExectiveGrid=Decimal("0.00"),
        FinancialYear="2026-2027",
        FranchiseCode="FR-01",
        FranchiseCommPaid=0,
        FranchiseTypeId=1,
        GridAgentId=0,
        IncentiveStatus=0,
        InsuranceSubTypeId=1,
        InsuranceTypeId=1,
        IntensiveAmount=Decimal("0.00"),
        IsActivePendingCash=0,
        IsChequeCleared=0,
        Ischequeclearing=0,
        IsCompanyChequeNo=0,
        IsQualityCheck=0,
        IsRconDataMatch=0,
        IsRecalculate=0,
        LegalLiabilitytoPaidDriver=Decimal("0.00"),
        LocationHeadId=1,
        MotorOrNonMotor="Motor",
        ND="N",
        OnlinePaymentToCompany=0,
        PACoverDriverCleaner=Decimal("0.00"),
        PACovertoOwner=Decimal("0.00"),
        PolicycancelId=0,
        PortalId="PORTAL1",
        PremiumCashToBank=0,
        QualityCheckDate=datetime.now(),
        RAPaymentStatus="Pending",
        RconComm=Decimal("0.00"),
        RconGrid=Decimal("0.00"),
        SelfDiscount=Decimal("0.00"),
        tdsPercent=Decimal("5.00"),
        TransId=0,
        TypeOfSubType=1,
        UpdatedIP="127.0.0.1",
        UpdatedSystem="Web",
        UpdateEntryStatus=0,
    )
    created = await repo.create(trans)
    assert created.TransanctionId is not None

    # Lookup by PolicyNo
    by_pol = await repo.get_by_policy_no("POL-TEST-2026-001")
    assert by_pol is not None
    assert by_pol.TransanctionId == created.TransanctionId
    assert by_pol.ODPermium == Decimal("5000.50")
    assert by_pol.TPPermium == Decimal("2000.00")
    assert by_pol.NetPermium == Decimal("7000.50")
    assert by_pol.TStatus == "Pending Approval"

    # Lookup by InwardNo
    by_inw = await repo.get_by_inward_no("INW-2026-001")
    assert by_inw is not None

    # Lookup by Status
    by_stat = await repo.get_by_status("Pending Approval")
    assert len(by_stat) >= 1

    # Lookup by CustomerId
    by_cust = await repo.get_by_customer_id(101)
    assert len(by_cust) >= 1


@pytest.mark.asyncio
async def test_transaction_app_repository_crud(db_session: AsyncSession):
    """Verify TransactionAppRepository CRUD for proposal staging intake."""
    repo = TransactionAppRepository(db_session)

    app_entry = TransactionAppNew(
        UserId=99,
        ContactNo="9123456789",
        LeadNo="LEAD-TEST-001",
        # All required non-null columns
        AppShortFallAmt=Decimal("0.00"),
        CashBackAmt=Decimal("0.00"),
        CashPaidAmt=Decimal("1000.00"),
        CashShortAmt=Decimal("0.00"),
        CashStatus="Clear",
        ChequeApprovalStatus=0,
        CoordinatorId=1,
        EwalletStatus=0,
        EWalletUsedamt=Decimal("0.00"),
        ExectiveGrid=Decimal("5.00"),
        FranchiseCode="FC01",
        Grid=Decimal("10.00"),
        incentive=Decimal("0.00"),
        InsuranceSubTypeId=1,
        InsuranceTypeId=1,
        IsAccountApproval=0,
        IsSubmit=0,
        LocationHeadId=1,
        MgfYear="2024",
        ND="N",
        NETCommission=Decimal("0.00"),
        ODCommission=Decimal("0.00"),
        OutstandingAmt=Decimal("0.00"),
        OutstandingWithPersonId=0,
        Paymentlink="https://pay.example.com",
        Quot_Type="Standard",
        ReceivedAmtLedgerMId=0,
        TDS=Decimal("0.00"),
        TPCommission=Decimal("0.00"),
        TPGrid=Decimal("0.00"),
        TransEmpId=1,
        TypeofSubId=1,
    )
    created = await repo.create(app_entry)
    assert created.TransId is not None

    by_user = await repo.get_by_user_id(99)
    assert len(by_user) >= 1

    by_contact = await repo.get_by_contact_no("9123456789")
    assert len(by_contact) >= 1

    by_lead = await repo.get_by_lead_no("LEAD-TEST-001")
    assert by_lead is not None

    by_cash_status = await repo.get_by_cash_status("Clear")
    assert len(by_cash_status) >= 1


@pytest.mark.asyncio
async def test_payment_repository_crud(db_session: AsyncSession):
    """Verify PaymentRepository CRUD on tbl_transactionpayment."""
    repo = PaymentRepository(db_session)

    payment = TransactionPayment(
        TransanctionId=1001,
        docno="DOC-CHQ-12345",
        PaymentType="Cheque",
        bankname="HDFC Bank",
        PaidAmount=Decimal("15000.00"),
        BranchId=2,
        isCompletePayment=1,
    )
    created = await repo.create(payment)
    assert created.PaymentId is not None

    by_trans = await repo.get_by_transaction_id(1001)
    assert len(by_trans) >= 1

    by_doc = await repo.get_by_doc_no("DOC-CHQ-12345")
    assert len(by_doc) >= 1


@pytest.mark.asyncio
async def test_account_and_ledger_repository_crud(db_session: AsyncSession):
    """Verify AccountRepository and LedgerRepository CRUD."""
    ledger_repo = LedgerRepository(db_session)
    account_repo = AccountRepository(db_session)

    # 1. Create Ledger Master
    ledger = LedgerMaster(
        LedgerName="Bank Account - SBI",
        LedgerTypeId=1,
        LedgerGroupId=10,
        BranchId=1,
    )
    created_ledger = await ledger_repo.create(ledger)
    assert created_ledger.LedgerMId is not None

    by_name = await ledger_repo.get_by_name("Bank Account - SBI")
    assert by_name is not None
    assert by_name.LedgerMId == created_ledger.LedgerMId

    # 2. Create Account Entry
    acc_entry = Account(
        TransactionId=5001,
        LedgerMId=created_ledger.LedgerMId,
        Doc_No=778899,
        amount=Decimal("12500.00"),
        Narration="Premium collection entry",
        BranchId=1,
        IsNill=0,
        CustVehId=0,
        MonthId=10,
        EndorsementId=0,
        TransId=0,
    )
    created_acc = await account_repo.create(acc_entry)
    assert created_acc.AccountId is not None

    by_trans = await account_repo.get_by_transaction_id(5001)
    assert len(by_trans) >= 1

    by_ledger = await account_repo.get_by_ledger_id(created_ledger.LedgerMId)
    assert len(by_ledger) >= 1

    by_doc = await account_repo.get_by_doc_no(778899)
    assert len(by_doc) >= 1


@pytest.mark.asyncio
async def test_commission_repositories_crud(db_session: AsyncSession):
    """Verify FranchiseCommission, AgentCommissionPayment, CutNPayCommPayable repositories."""
    f_repo = FranchiseCommissionRepository(db_session)
    a_repo = AgentCommissionRepository(db_session)
    c_repo = CutNPayCommissionRepository(db_session)

    # 1. Franchise Commission
    f_comm = FranchiseCommission(
        TransanctionId=6001,
        FranchiseId=10,
        AgentId=20,
        FranchiseNetComm=Decimal("1200.00"),
        BrokerId=1,
        SelfDiscount=Decimal("0.00"),
        IntensiveAmount=Decimal("0.00"),
    )
    created_f = await f_repo.create(f_comm)
    assert created_f.FranchiseCommId is not None
    assert len(await f_repo.get_by_transaction_id(6001)) >= 1

    # 2. Agent Commission
    a_comm = AgentCommissionPayment(
        TransanctionId=6001,
        AgentName="Rahul Sharma",
        BranchName="Pune Main",
        PremiumAmount=Decimal("25000.00"),
        NetAmount=Decimal("2500.00"),
    )
    created_a = await a_repo.create(a_comm)
    assert created_a.AgentCommId is not None
    assert len(await a_repo.get_by_agent_name("Rahul Sharma")) >= 1

    # 3. Cut & Pay Commission
    c_comm = CutNPayCommPayable(
        TransactionId=6001,
        PolicyNo="POL-CUT-999",
        CommPayable=Decimal("350.00"),
    )
    created_c = await c_repo.create(c_comm)
    assert created_c.CutNPayCommPayId is not None
    assert len(await c_repo.get_by_policy_no("POL-CUT-999")) >= 1


@pytest.mark.asyncio
async def test_repository_rollback_behavior(db_session: AsyncSession):
    """
    Verify transaction rollback semantics:
    Flushed changes roll back cleanly and do not persist across rolled back sessions.
    """
    repo = CustomerRepository(db_session)

    customer = Customer(
        CustomerCode="CUST-ROLLBACK-TEST",
        CustFName="RollbackUser",
    )
    created = await repo.create(customer)
    cust_id = created.CustomerId
    assert cust_id is not None

    # Roll back session explicitly
    await db_session.rollback()

    # Querying after rollback must return None
    assert await repo.get_by_id(cust_id) is None


@pytest.mark.asyncio
async def test_missing_records_graceful_handling(db_session: AsyncSession):
    """Verify repository methods return None or empty collections when records are absent."""
    cust_repo = CustomerRepository(db_session)
    veh_repo = VehicleRepository(db_session)
    trans_repo = TransactionRepository(db_session)

    assert await cust_repo.get_by_id(-999) is None
    assert await cust_repo.get_by_code("NON_EXISTENT_CODE") is None
    assert await cust_repo.get_by_mobile("0000000000") == []

    assert await veh_repo.get_by_id(-999) is None
    assert await veh_repo.get_by_registration_no("NON_EXISTENT_REG") is None

    assert await trans_repo.get_by_id(-999) is None
    assert await trans_repo.get_by_policy_no("NON_EXISTENT_POL") is None
