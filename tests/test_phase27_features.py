"""
Phase 27 Comprehensive Test Suite:
Company Outstanding Premium Remittance & Cash-to-Bank Deposit Settlement Engine.
Physical Tables:
1. tbl_debitfrombankaccount (BankDebitRemittance)
2. tbl_account (Double-entry financial ledger)
3. tbl_transaction (Policy proposals and settlements)
4. tbl_ledgermaster (Chart of accounts)
"""
from datetime import datetime, timedelta
from decimal import Decimal
import pytest
from httpx import AsyncClient
from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import AsyncSession

from tests.integration.test_phase7_policy_booking_api import create_user_with_role
from app.models.phase27_features import BankDebitRemittance
from app.models.account import Account
from app.models.ledger import LedgerMaster
from app.models.transaction import Transaction
from app.models.master import InsuranceCompany, Branch


@pytest.fixture(autouse=True)
async def cleanup_phase27_tables(db_session: AsyncSession):
    """Purge synthetic Phase 27 settlement journal and accounting test rows before and after each test."""
    try:
        await db_session.execute(text("DELETE FROM tbl_debitfrombankaccount;"))
        await db_session.commit()
    except Exception:
        await db_session.rollback()
    yield
    try:
        await db_session.execute(text("DELETE FROM tbl_debitfrombankaccount;"))
        await db_session.commit()
    except Exception:
        await db_session.rollback()


async def get_or_create_test_ledgers(db_session: AsyncSession) -> tuple[int, int, int]:
    """Returns (cash_ledger_id, bank_ledger_id, company_ledger_id)."""
    # 1. Cash Ledger
    cash_stmt = select(LedgerMaster).where(LedgerMaster.LedgerName == "TEST_CASH_IN_HAND").limit(1)
    cash_ledger = (await db_session.execute(cash_stmt)).scalars().first()
    if not cash_ledger:
        cash_ledger = LedgerMaster(
            LedgerName="TEST_CASH_IN_HAND",
            LedgerTypeId=1,
            LedgerGroupId=1,
            BranchId=101,
            isdeleted="0",
        )
        db_session.add(cash_ledger)
        await db_session.flush()

    # 2. Bank Ledger
    bank_stmt = select(LedgerMaster).where(LedgerMaster.LedgerName == "TEST_AXIS_BANK").limit(1)
    bank_ledger = (await db_session.execute(bank_stmt)).scalars().first()
    if not bank_ledger:
        bank_ledger = LedgerMaster(
            LedgerName="TEST_AXIS_BANK",
            LedgerTypeId=2,
            LedgerGroupId=2,
            BranchId=101,
            isdeleted="0",
        )
        db_session.add(bank_ledger)
        await db_session.flush()

    # 3. Company Ledger
    comp_stmt = select(LedgerMaster).where(LedgerMaster.LedgerName == "TEST_ICICI_LOMBARD_LEDGER").limit(1)
    comp_ledger = (await db_session.execute(comp_stmt)).scalars().first()
    if not comp_ledger:
        comp_ledger = LedgerMaster(
            LedgerName="TEST_ICICI_LOMBARD_LEDGER",
            LedgerTypeId=3,
            LedgerGroupId=3,
            BranchId=101,
            isdeleted="0",
        )
        db_session.add(comp_ledger)
        await db_session.flush()

    await db_session.commit()
    return cash_ledger.LedgerMId, bank_ledger.LedgerMId, comp_ledger.LedgerMId


async def get_or_create_test_company(db_session: AsyncSession) -> int:
    """Ensures at least one active InsuranceCompany exists."""
    stmt = select(InsuranceCompany).limit(1)
    comp = (await db_session.execute(stmt)).scalars().first()
    if comp:
        return comp.InsuranceCompanyId
    new_comp = InsuranceCompany(
        InsuranceCompany="TEST_ICICI_LOMBARD",
        BranchName="MUMBAI_HO",
        BranchCode="MUM01",
        NCB="0",
        Cluster="WEST",
        ZeroDeep="YES",
        isdeleted="0",
        IsAppQuotation="1",
        CompImgPath="/logos/icici.png",
        LedgerMId=1001,
    )
    db_session.add(new_comp)
    await db_session.commit()
    await db_session.refresh(new_comp)
    return new_comp.InsuranceCompanyId


async def create_test_transaction(
    db_session: AsyncSession,
    company_id: int,
    amount: Decimal,
    branch_id: int = 101,
    inward_no: str = "INW-TEST-001",
) -> Transaction:
    """Creates an unremitted policy transaction."""
    trans = Transaction(
        InwardNo=inward_no,
        PolicyNo=f"POL-{inward_no}",
        InsuranceCompanyId=company_id,
        BranchId=branch_id,
        Amount=amount,
        NetPermium=amount,
        ProPosalAmt=amount,
        OnlinePaymentToCompany=0,
        PremiumCashToBank=0,
        IsRecalculate=0,
        MotorOrNonMotor="Motor",
        InsuranceTypeId=1,
        InsuranceSubTypeId=1,
        TypeOfSubType=1,
        AddOnRate=Decimal("0.00"),
        GridAgentId=0,
        CreatedSystem="TEST",
        CreatedIP="127.0.0.1",
        UpdatedSystem="TEST",
        UpdatedIP="127.0.0.1",
        PortalId="DIRECT",
        FranchiseCode="RA",
        SelfDiscount=Decimal("0.00"),
        IntensiveAmount=Decimal("0.00"),
        LocationHeadId=0,
        Ischequeclearing=0,
        IsChequeCleared=0,
        IsCompanyChequeNo=0,
        IsActivePendingCash=0,
        tdsPercent=Decimal("0.00"),
        FinancialYear="2026-2027",
        CashBackStatus=0,
        CashBackAmt=Decimal("0.00"),
        CutNPay=Decimal("0.00"),
        ChequeBankStatus=0,
        IncentiveStatus=0,
        DeuDate=datetime.utcnow(),
        UpdateEntryStatus=0,
        ExectiveGrid=Decimal("0.00"),
        EWalletAmountUsed=Decimal("0.00"),
        PACovertoOwner=Decimal("0.00"),
        PACoverDriverCleaner=Decimal("0.00"),
        LegalLiabilitytoPaidDriver=Decimal("0.00"),
        PolicycancelId=0,
        FranchiseCommPaid=0,
        IsRconDataMatch=1,
        TransId=0,
        RconGrid=Decimal("0.00"),
        RconComm=Decimal("0.00"),
        IsQualityCheck=1,
        QualityCheckDate=datetime.utcnow(),
        ND="NO",
        FranchiseTypeId=0,
        RAPaymentStatus="COMPLETE",
        isdeleted="0",
        CreateDate=datetime.utcnow(),
    )
    db_session.add(trans)
    await db_session.commit()
    await db_session.refresh(trans)
    return trans


# ==============================================================================
# 1. CASH-TO-BANK DEPOSIT SETTLEMENT & DOUBLE-ENTRY LEDGER PARITY
# ==============================================================================

@pytest.mark.asyncio
async def test_cash_to_bank_deposit_balanced_double_entry(
    async_client: AsyncClient, db_session: AsyncSession
):
    admin_user, admin_headers = await create_user_with_role(db_session, "ADMIN")
    cash_ledger_id, bank_ledger_id, _ = await get_or_create_test_ledgers(db_session)

    deposit_amt = Decimal("7500.00")
    payload = {
        "from_cash_ledger_id": cash_ledger_id,
        "to_bank_ledger_id": bank_ledger_id,
        "deposit_amount": str(deposit_amt),
        "deposit_date": datetime.utcnow().isoformat(),
        "payment_mode": "Cash",
        "branch_id": 101,
        "narration": "Daily branch cash deposit to bank",
    }

    response = await async_client.post(
        "/api/v1/bank-remittance/cash-to-bank",
        json=payload,
        headers=admin_headers,
    )
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["success"] is True
    doc_no = data["doc_no"]
    assert doc_no is not None

    # Verify tbl_debitfrombankaccount audit record
    await db_session.commit()
    debit_id = data["remittance_record"]["debit_account_id"]
    debit_entry = await db_session.get(BankDebitRemittance, debit_id)
    assert debit_entry is not None
    assert debit_entry.Flag == "Cash"
    assert Decimal(str(debit_entry.Amount)) == deposit_amt
    assert debit_entry.Doc_No == doc_no

    # Verify double-entry ledger balance in tbl_account
    doc_no_int = int(doc_no)
    account_stmt = select(Account).where(Account.Doc_No == doc_no_int)
    voucher_entries = (await db_session.execute(account_stmt)).scalars().all()
    assert len(voucher_entries) == 2

    # Check polarity and zero-sum balance
    # One Credit to Bank (AccTransId 1, amount = -7500.00)
    # One Debit to Cash (AccTransId 3, amount = +7500.00)
    total_ledger_sum = Decimal("0.00")
    acc_trans_ids = set()
    for entry in voucher_entries:
        total_ledger_sum += Decimal(str(entry.amount))
        acc_trans_ids.add(entry.AccTransId)

    assert total_ledger_sum == Decimal("0.00"), f"Ledger not balanced! Sum is {total_ledger_sum}"
    assert 1 in acc_trans_ids
    assert 3 in acc_trans_ids


# ==============================================================================
# 2. COMPANY REMITTANCE BATCH CLEARANCE & TRANSACTION STATUS UPDATES
# ==============================================================================

@pytest.mark.asyncio
async def test_company_remittance_batch_lifecycle(
    async_client: AsyncClient, db_session: AsyncSession
):
    admin_user, admin_headers = await create_user_with_role(db_session, "ADMIN")
    cash_ledger_id, bank_ledger_id, comp_ledger_id = await get_or_create_test_ledgers(db_session)
    company_id = await get_or_create_test_company(db_session)

    # Create 2 unremitted transactions
    t1 = await create_test_transaction(db_session, company_id, Decimal("3200.00"), inward_no="INW-BATCH-1")
    t2 = await create_test_transaction(db_session, company_id, Decimal("4800.00"), inward_no="INW-BATCH-2")

    # 1. Discover pending company remittances
    pending_resp = await async_client.get(
        f"/api/v1/bank-remittance/pending-company?company_id={company_id}&branch_id=101",
        headers=admin_headers,
    )
    assert pending_resp.status_code == 200
    pending_list = pending_resp.json()
    pending_ids = [p["transaction_id"] for p in pending_list]
    assert t1.TransanctionId in pending_ids
    assert t2.TransanctionId in pending_ids

    # 2. Execute batch remittance payment
    batch_payload = {
        "company_id": company_id,
        "company_ledger_id": comp_ledger_id,
        "bank_ledger_id": bank_ledger_id,
        "payment_mode": "Cheque",
        "cheque_no": "CHQ-998877",
        "payment_date": datetime.utcnow().isoformat(),
        "transaction_ids": [t1.TransanctionId, t2.TransanctionId],
        "branch_id": 101,
        "narration": "Batch premium remittance for July 2026",
    }

    batch_resp = await async_client.post(
        "/api/v1/bank-remittance/company-batch",
        json=batch_payload,
        headers=admin_headers,
    )
    assert batch_resp.status_code == 201, batch_resp.text
    batch_data = batch_resp.json()
    assert batch_data["success"] is True
    assert Decimal(str(batch_data["total_remitted_amount"])) == Decimal("8000.00")
    assert batch_data["transaction_count"] == 2
    doc_no = batch_data["doc_no"]

    # 3. Verify transactions updated
    await db_session.commit()
    await db_session.refresh(t1)
    await db_session.refresh(t2)
    assert t1.OnlinePaymentToCompany == 1
    assert t1.CompSubmitionDocNo == doc_no
    assert t1.CompanyChequeNo == "CHQ-998877"
    assert t2.OnlinePaymentToCompany == 1
    assert t2.CompSubmitionDocNo == doc_no

    # 4. Verify balanced double-entry vouchers in tbl_account
    doc_no_int = int(doc_no)
    account_stmt = select(Account).where(Account.Doc_No == doc_no_int)
    voucher_entries = (await db_session.execute(account_stmt)).scalars().all()
    # 2 Debits to Company Ledger + 1 Credit to Bank Ledger = 3 entries
    assert len(voucher_entries) == 3
    total_ledger_sum = sum(Decimal(str(e.amount)) for e in voucher_entries)
    assert total_ledger_sum == Decimal("0.00"), f"Batch remittance voucher sum must balance to 0, got {total_ledger_sum}"

    # 5. Pending list must now exclude settled transactions
    pending_resp2 = await async_client.get(
        f"/api/v1/bank-remittance/pending-company?company_id={company_id}&branch_id=101",
        headers=admin_headers,
    )
    pending_list2 = pending_resp2.json()
    pending_ids2 = [p["transaction_id"] for p in pending_list2]
    assert t1.TransanctionId not in pending_ids2
    assert t2.TransanctionId not in pending_ids2


# ==============================================================================
# 3. DUPLICATE REMITTANCE PROTECTION
# ==============================================================================

@pytest.mark.asyncio
async def test_duplicate_remittance_rejection(
    async_client: AsyncClient, db_session: AsyncSession
):
    admin_user, admin_headers = await create_user_with_role(db_session, "ADMIN")
    _, bank_ledger_id, comp_ledger_id = await get_or_create_test_ledgers(db_session)
    company_id = await get_or_create_test_company(db_session)

    t = await create_test_transaction(db_session, company_id, Decimal("5000.00"), inward_no="INW-DUP-1")

    # First remittance succeeds
    payload = {
        "company_id": company_id,
        "company_ledger_id": comp_ledger_id,
        "bank_ledger_id": bank_ledger_id,
        "payment_mode": "Online",
        "payment_date": datetime.utcnow().isoformat(),
        "transaction_ids": [t.TransanctionId],
        "branch_id": 101,
    }
    r1 = await async_client.post("/api/v1/bank-remittance/company-batch", json=payload, headers=admin_headers)
    assert r1.status_code == 201

    # Second remittance for the same transaction must fail with 400
    r2 = await async_client.post("/api/v1/bank-remittance/company-batch", json=payload, headers=admin_headers)
    assert r2.status_code == 400
    assert "already been remitted" in r2.text


# ==============================================================================
# 4. BRANCH CASH BALANCE SUMMARY & METRICS
# ==============================================================================

@pytest.mark.asyncio
async def test_cash_balance_summary_endpoint(
    async_client: AsyncClient, db_session: AsyncSession
):
    admin_user, admin_headers = await create_user_with_role(db_session, "ADMIN")

    resp = await async_client.get(
        "/api/v1/bank-remittance/cash-balance?branch_id=101",
        headers=admin_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "branch_id" in data
    assert data["branch_id"] == 101
    assert "current_cash_balance" in data
    assert "total_cash_deposited_to_bank" in data


# ==============================================================================
# 5. AUDIT HISTORY & DETAIL RETRIEVAL
# ==============================================================================

@pytest.mark.asyncio
async def test_remittance_history_and_detail(
    async_client: AsyncClient, db_session: AsyncSession
):
    admin_user, admin_headers = await create_user_with_role(db_session, "ADMIN")
    cash_ledger_id, bank_ledger_id, _ = await get_or_create_test_ledgers(db_session)

    # Create a cash deposit
    payload = {
        "from_cash_ledger_id": cash_ledger_id,
        "to_bank_ledger_id": bank_ledger_id,
        "deposit_amount": "2500.00",
        "deposit_date": datetime.utcnow().isoformat(),
        "payment_mode": "Cash",
        "branch_id": 101,
        "narration": "History test cash deposit",
    }
    create_resp = await async_client.post(
        "/api/v1/bank-remittance/cash-to-bank", json=payload, headers=admin_headers
    )
    assert create_resp.status_code == 201
    debit_id = create_resp.json()["remittance_record"]["debit_account_id"]

    # History list
    hist_resp = await async_client.get(
        "/api/v1/bank-remittance/history?flag=Cash&branch_id=101",
        headers=admin_headers,
    )
    assert hist_resp.status_code == 200
    hist_data = hist_resp.json()
    assert hist_data["total"] >= 1
    ids = [item["debit_account_id"] for item in hist_data["items"]]
    assert debit_id in ids

    # Detail by ID
    detail_resp = await async_client.get(
        f"/api/v1/bank-remittance/{debit_id}",
        headers=admin_headers,
    )
    assert detail_resp.status_code == 200
    detail_data = detail_resp.json()
    assert detail_data["debit_account_id"] == debit_id
    assert detail_data["flag"] == "Cash"
    assert Decimal(str(detail_data["amount"])) == Decimal("2500.00")


# ==============================================================================
# 6. BRANCH ISOLATION & RBAC CONTROLS
# ==============================================================================

@pytest.mark.asyncio
async def test_branch_isolation_clerk_cannot_deposit_for_other_branch(
    async_client: AsyncClient, db_session: AsyncSession
):
    # Clerk tied to Branch 102
    clerk_user, clerk_headers = await create_user_with_role(
        db_session, "OPERATOR", branch_id=102
    )
    cash_ledger_id, bank_ledger_id, _ = await get_or_create_test_ledgers(db_session)

    # Attempting to remit for Branch 101 must be forbidden
    payload = {
        "from_cash_ledger_id": cash_ledger_id,
        "to_bank_ledger_id": bank_ledger_id,
        "deposit_amount": "1000.00",
        "deposit_date": datetime.utcnow().isoformat(),
        "payment_mode": "Cash",
        "branch_id": 101,  # Different from clerk's 102
    }
    resp = await async_client.post(
        "/api/v1/bank-remittance/cash-to-bank",
        json=payload,
        headers=clerk_headers,
    )
    assert resp.status_code == 403
    assert "scoping violation" in resp.text
