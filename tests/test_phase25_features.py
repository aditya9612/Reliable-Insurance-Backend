"""
Phase 25 Comprehensive Test Suite:
Corporate Group Clients, Commercial Sales Invoicing & Sister Concern Advances.
"""
import asyncio
from unittest.mock import patch
from datetime import date, datetime
from decimal import Decimal
import pytest
from httpx import AsyncClient
from sqlalchemy import text, select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from tests.integration.test_phase7_policy_booking_api import create_user_with_role
from app.models.phase25_features import (
    SalesType,
    ReliableCompany,
    ClientMaster,
    SalesRegDetails,
    CompanyAdvanceMaster,
    CompanyAdvDetail,
    InvoiceSequence,
)
from app.models.phase18a_features import SalesRegistration
from app.models.account import Account
from app.models.ledger import LedgerMaster
from app.services.phase25_service import round_bankers_rupee, Phase25Service
from app.schemas.phase25 import CommercialInvoiceCreateRequest, CommercialInvoiceLineItemCreate


import uuid
from app.models.user import User


@pytest.fixture(autouse=True)
async def cleanup_phase25_tables(db_session: AsyncSession):
    """Purge synthetic Phase 25 tables and test ledger entries before and after each test."""
    tables = [
        "tbl_companyadvdetails",
        "tbl_companyadvancemaster",
        "tbl_salesregdetails",
        "tbl_salesregistration",
        "tbl_clientmaster",
        "tbl_reliablecompanymst",
        "tbl_salestype",
        "tbl_invoicesequence",
    ]
    for tbl in tables:
        await db_session.execute(text(f"DELETE FROM {tbl};"))
    await db_session.execute(text("DELETE FROM tbl_account WHERE Narration = 'sales Registration Amount' OR Narration LIKE 'Coord Accounting Voucher%' OR Extra1 LIKE 'RBK/%' OR Extra1 LIKE 'TPC/%' OR Extra1 LIKE 'CSC/%';"))
    await db_session.execute(text("DELETE FROM tbl_ledgermaster WHERE LedgerName LIKE 'Coord%';"))
    await db_session.commit()
    yield
    for tbl in tables:
        await db_session.execute(text(f"DELETE FROM {tbl};"))
    await db_session.execute(text("DELETE FROM tbl_account WHERE Narration = 'sales Registration Amount' OR Narration LIKE 'Coord Accounting Voucher%' OR Extra1 LIKE 'RBK/%' OR Extra1 LIKE 'TPC/%' OR Extra1 LIKE 'CSC/%';"))
    await db_session.execute(text("DELETE FROM tbl_ledgermaster WHERE LedgerName LIKE 'Coord%';"))
    await db_session.commit()


# ==============================================================================
# 1. TAX CALCULATION & BANKER'S ROUNDING PARITY UNIT TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_bankers_rounding_rupee_parity():
    """
    Verifies parity with .NET Math.Round(double) default MidpointRounding.ToEven to 0 decimals:
    2.50 -> 2 (Even), 3.50 -> 4 (Even), 4.50 -> 4 (Even), 12.50 -> 12 (Even), 13.50 -> 14 (Even)
    """
    assert round_bankers_rupee(Decimal("1.50")) == Decimal("2")
    assert round_bankers_rupee(Decimal("2.50")) == Decimal("2")
    assert round_bankers_rupee(Decimal("3.50")) == Decimal("4")
    assert round_bankers_rupee(Decimal("4.50")) == Decimal("4")
    assert round_bankers_rupee(Decimal("12.50")) == Decimal("12")
    assert round_bankers_rupee(Decimal("13.50")) == Decimal("14")
    assert round_bankers_rupee(Decimal("118.50")) == Decimal("118")
    assert round_bankers_rupee(Decimal("119.50")) == Decimal("120")


# ==============================================================================
# 2. COMMERCIAL MASTERS CRUD & VALIDATION
# ==============================================================================

@pytest.mark.asyncio
async def test_commercial_masters_crud_and_validation(
    async_client: AsyncClient, db_session: AsyncSession
):
    _, admin_headers = await create_user_with_role(db_session, "ADMIN")
    _, agent_headers = await create_user_with_role(db_session, "AGENT")

    # 1. Create SalesType (Admin)
    st_payload = {"Description": "Brokerage Commission", "IsActive": True}
    res_st = await async_client.post("/api/v1/commercial/sales-types", json=st_payload, headers=admin_headers)
    assert res_st.status_code == 201, res_st.text
    st_data = res_st.json()
    st_id = st_data["sales_type_id"]
    assert st_data["description"] == "Brokerage Commission"
    assert st_data["is_active"] is True

    # Duplicate sales type rejected (409)
    res_dup_st = await async_client.post("/api/v1/commercial/sales-types", json=st_payload, headers=admin_headers)
    assert res_dup_st.status_code == 409

    # Agent forbidden from creating sales type (403)
    res_forb = await async_client.post("/api/v1/commercial/sales-types", json={"Description": "Other"}, headers=agent_headers)
    assert res_forb.status_code == 403

    # 2. Create ReliableCompany (Admin)
    rc_payload = {
        "RCompany": "JPB Financial Services Ltd",
        "Prefix": "JPB",
        "LedgerMId": 501,
        "IsActive": True,
    }
    res_rc = await async_client.post("/api/v1/commercial/reliable-companies", json=rc_payload, headers=admin_headers)
    assert res_rc.status_code == 201, res_rc.text
    rc_data = res_rc.json()
    rc_id = rc_data["r_company_id"]
    assert rc_data["prefix"] == "JPB"

    # Duplicate company prefix rejected (409)
    res_dup_rc = await async_client.post(
        "/api/v1/commercial/reliable-companies",
        json={"RCompany": "Another JPB", "Prefix": "JPB", "LedgerMId": 502, "IsActive": True},
        headers=admin_headers,
    )
    assert res_dup_rc.status_code == 409

    # 3. Create Corporate ClientMaster (Admin / Operator / Account)
    cm_payload = {
        "Description": "Tata Motors Fleet Services Ltd",
        "InsuranceCompanyId": 1,
        "Address": "Pimpri Works, Pune, Maharashtra 411018",
        "PanNo": "AAACT1234K",
        "GST": "27AAACT1234K1Z1",
        "CGST": "9.00",
        "SGST": "9.00",
        "IGST": "0.00",
        "IsActive": True,
    }
    res_cm = await async_client.post("/api/v1/commercial/corporate-clients", json=cm_payload, headers=admin_headers)
    assert res_cm.status_code == 201, res_cm.text
    cm_data = res_cm.json()
    cm_id = cm_data["client_master_id"]
    assert cm_data["description"] == "Tata Motors Fleet Services Ltd"
    assert cm_data["pan_no"] == "AAACT1234K"
    assert cm_data["gst"] == "27AAACT1234K1Z1"

    # Invalid PAN format rejected (422)
    bad_pan = dict(cm_payload, Description="Bad PAN Client", PanNo="INVALIDPAN12")
    res_bad_pan = await async_client.post("/api/v1/commercial/corporate-clients", json=bad_pan, headers=admin_headers)
    assert res_bad_pan.status_code == 422

    # 4. Search and List Corporate Clients
    res_list = await async_client.get("/api/v1/commercial/corporate-clients?search=Tata", headers=admin_headers)
    assert res_list.status_code == 200
    assert len(res_list.json()) >= 1
    assert res_list.json()[0]["client_master_id"] == cm_id

    # 5. Soft-Delete ClientMaster
    res_del = await async_client.delete(f"/api/v1/commercial/corporate-clients/{cm_id}", headers=admin_headers)
    assert res_del.status_code == 200
    assert res_del.json()["mode"] == "soft"
    # Verify deactivated
    res_cm_after = await async_client.get(f"/api/v1/commercial/corporate-clients/{cm_id}", headers=admin_headers)
    assert res_cm_after.json()["is_active"] is False


# ==============================================================================
# 3. MULTI-LINE COMMERCIAL INVOICE GENERATION & ATOMIC REVENUE POSTING
# ==============================================================================

@pytest.mark.asyncio
async def test_commercial_invoicing_atomicity_and_ledger_posting(
    async_client: AsyncClient, db_session: AsyncSession
):
    _, admin_headers = await create_user_with_role(db_session, "ADMIN", branch_id=1)

    # Setup Master Entities
    rc_res = await async_client.post(
        "/api/v1/commercial/reliable-companies",
        json={"RCompany": "Reliable Assurance Corp", "Prefix": "REL", "LedgerMId": 601, "IsActive": True},
        headers=admin_headers,
    )
    rc_id = rc_res.json()["r_company_id"]

    cm_res = await async_client.post(
        "/api/v1/commercial/corporate-clients",
        json={
            "Description": "Reliance Infrastructure Ltd",
            "InsuranceCompanyId": 1,
            "Address": "Mumbai",
            "PanNo": "AABCR9999R",
            "GST": "27AABCR9999R1Z5",
            "CGST": "9.00",
            "SGST": "9.00",
            "IGST": "0.00",
            "IsActive": True,
        },
        headers=admin_headers,
    )
    cm_id = cm_res.json()["client_master_id"]

    # 1. Check Invoice Number Preview Endpoint
    res_preview = await async_client.get(
        f"/api/v1/commercial/invoices/next-number?r_company_id={rc_id}",
        headers=admin_headers,
    )
    assert res_preview.status_code == 200
    assert "REL/" in res_preview.json()["preview_invoice_no"]

    # 2. Create Multi-Line Commercial Invoice
    # Line 1: ₹100.50 with 9% CGST (9.045 -> 9.00) & 9% SGST (9.045 -> 9.00). Total = 100.50 + 9 + 9 = 118.50 -> 118.00 (Even)
    # Line 2: ₹50.00 with 5% CGST (2.50 -> 2.00 Even) & 5% SGST (2.50 -> 2.00 Even). Total = 50 + 2 + 2 = 54.00
    # Expected Grand Total = 118.00 + 54.00 = ₹172.00
    invoice_payload = {
        "r_company_id": rc_id,
        "client_master_id": cm_id,
        "sales_date": date(2026, 10, 15).isoformat(),
        "sales_type_id": 1,
        "registration_type": "COMMERCIAL_B2B",
        "description": "Multi-Line Commercial Brokerage Services",
        "items": [
            {
                "sales_type": "Corporate Retainer",
                "sales_type_id": 1,
                "taxable_amt": "100.50",
                "cgst_per": "9.00",
                "sgst_per": "9.00",
                "igst_per": "0.00",
            },
            {
                "sales_type": "Risk Survey Fee",
                "sales_type_id": 1,
                "taxable_amt": "50.00",
                "cgst_per": "5.00",
                "sgst_per": "5.00",
                "igst_per": "0.00",
            },
        ],
    }

    res_inv = await async_client.post("/api/v1/commercial/invoices", json=invoice_payload, headers=admin_headers)
    assert res_inv.status_code == 201, res_inv.text
    inv_data = res_inv.json()
    sr_id = inv_data["sales_reg_id"]
    inv_no = inv_data["invoice_no"]

    assert inv_no.startswith("REL/")
    assert Decimal(str(inv_data["amount"])) == Decimal("150.50")
    assert Decimal(str(inv_data["cgst_amt"])) == Decimal("11.00") # 9.00 + 2.00
    assert Decimal(str(inv_data["sgst_amt"])) == Decimal("11.00") # 9.00 + 2.00
    assert Decimal(str(inv_data["total"])) == Decimal("172.00")   # 118.00 + 54.00
    assert Decimal(str(inv_data["received_amt"])) == Decimal("0.00")
    assert Decimal(str(inv_data["balance_amt"])) == Decimal("172.00")
    assert len(inv_data["items"]) == 2

    # Verify line items in tbl_salesregdetails
    await db_session.commit()
    det_rows = (await db_session.execute(
        select(SalesRegDetails).where(SalesRegDetails.InvoiceId == sr_id).order_by(SalesRegDetails.SalesRegDetailId.asc())
    )).scalars().all()
    assert len(det_rows) == 2
    assert det_rows[0].TaxableAmt == Decimal("100.50")
    assert det_rows[0].CGSTAmt == Decimal("9.00")
    assert det_rows[0].Total == Decimal("118.00")
    assert det_rows[1].TaxableAmt == Decimal("50.00")
    assert det_rows[1].CGSTAmt == Decimal("2.00") # 2.50 rounded to Even
    assert det_rows[1].Total == Decimal("54.00")

    # 3. Verify Double-Entry General Ledger Posting in tbl_account
    acc_row = (await db_session.execute(
        select(Account).where(
            Account.Extra1 == inv_no,
            Account.Narration == "sales Registration Amount"
        )
    )).scalar_one_or_none()
    assert acc_row is not None
    assert acc_row.AccTransId == 1                       # Verified legacy constant
    assert acc_row.LedgerMId == 2756                     # Verified legacy sales revenue ledger
    assert acc_row.amount == Decimal("-172.00")          # Verified negative credit polarity
    assert acc_row.BranchId == 1                         # Verified legacy constant
    assert acc_row.Doc_No is not None                    # Monotonically allocated
    assert acc_row.Doc_No >= 1000

    # 4. Sequential Number Allocation & Collision Stepping Test
    # Manually create out-of-band invoice with candidate number to test collision avoidance
    seq_stmt = select(InvoiceSequence.CurrentValue).where(InvoiceSequence.SequenceName == "COMMERCIAL_SALES")
    cur_val = (await db_session.execute(seq_stmt)).scalar() or 1000
    next_candidate = f"REL/{cur_val + 1}"
    # Seed out-of-band invoice
    oob = SalesRegistration(
        InvoiceNo=next_candidate,
        SalesDate=date(2026, 10, 1),
        ClientMasterId=cm_id,
        amount=Decimal("10.00"),
        Total=Decimal("10.00"),
        ReceivedAmt=Decimal("0.00"),
        BalanceAmt=Decimal("10.00"),
    )
    db_session.add(oob)
    await db_session.commit()

    # Next invoice creation should detect collision and step over to cur_val + 2
    res_inv2 = await async_client.post("/api/v1/commercial/invoices", json=invoice_payload, headers=admin_headers)
    assert res_inv2.status_code == 201
    assert res_inv2.json()["invoice_no"] == f"REL/{cur_val + 2}"


# ==============================================================================
# 4. SISTER CONCERN ADVANCE DISBURSEMENT & RECOVERY
# ==============================================================================

@pytest.mark.asyncio
async def test_sister_concern_advance_booking_and_recovery(
    async_client: AsyncClient, db_session: AsyncSession
):
    _, admin_headers = await create_user_with_role(db_session, "ADMIN")

    # 1. Book Sister Concern Advance of ₹50,000.00
    adv_payload = {
        "ledger_m_id": 888,
        "advance_date": date(2026, 10, 10).isoformat(),
        "amount": "50000.00",
        "description": "Sister Concern Operational Facility Advance",
    }
    res_adv = await async_client.post("/api/v1/commercial/advances", json=adv_payload, headers=admin_headers)
    assert res_adv.status_code == 201, res_adv.text
    adv_data = res_adv.json()
    adv_id = adv_data["company_adv_id"]
    assert Decimal(str(adv_data["amount"])) == Decimal("50000.00")
    assert Decimal(str(adv_data["receiving_amount"])) == Decimal("0.00")
    assert Decimal(str(adv_data["balance_amt"])) == Decimal("50000.00")

    # 2. Test Partial Recovery of ₹20,000.00
    rec_payload = {
        "recovery_amount": "20000.00",
        "recovery_date": date(2026, 10, 16).isoformat(),
        "sales_invoice_id": "REL/1001",
        "acc_doc_no": "VCH-2026-901",
        "narration": "First tranche recovery via voucher 901",
    }
    res_rec1 = await async_client.post(f"/api/v1/commercial/advances/{adv_id}/recover", json=rec_payload, headers=admin_headers)
    assert res_rec1.status_code == 200, res_rec1.text
    rec_data1 = res_rec1.json()
    assert Decimal(str(rec_data1["advance"]["receiving_amount"])) == Decimal("20000.00")
    assert Decimal(str(rec_data1["advance"]["balance_amt"])) == Decimal("30000.00")
    assert rec_data1["acc_doc_no"] == "VCH-2026-901"

    # 3. Duplicate Voucher Submission Rejected (409 Conflict)
    res_dup_vch = await async_client.post(f"/api/v1/commercial/advances/{adv_id}/recover", json=rec_payload, headers=admin_headers)
    assert res_dup_vch.status_code == 409

    # 4. Zero or Negative Recovery Rejected (422)
    bad_amt = dict(rec_payload, recovery_amount="0.00", acc_doc_no="VCH-NEW-1")
    res_zero = await async_client.post(f"/api/v1/commercial/advances/{adv_id}/recover", json=bad_amt, headers=admin_headers)
    assert res_zero.status_code == 422

    # 5. Over-Recovery Exceeding Remaining Balance Rejected (422)
    # Remaining balance is ₹30,000.00; attempt to recover ₹30,000.01
    over_rec = dict(rec_payload, recovery_amount="30000.01", acc_doc_no="VCH-OVER-1")
    res_over = await async_client.post(f"/api/v1/commercial/advances/{adv_id}/recover", json=over_rec, headers=admin_headers)
    assert res_over.status_code == 422
    err_msg = res_over.json().get("detail") or res_over.json().get("error", {}).get("message", "")
    assert "cannot exceed available advance balance" in err_msg

    # 6. Exact-Balance Final Recovery of ₹30,000.00
    exact_rec = dict(rec_payload, recovery_amount="30000.00", acc_doc_no="VCH-FINAL-1")
    res_final = await async_client.post(f"/api/v1/commercial/advances/{adv_id}/recover", json=exact_rec, headers=admin_headers)
    assert res_final.status_code == 200
    assert Decimal(str(res_final.json()["advance"]["balance_amt"])) == Decimal("0.00")
    assert Decimal(str(res_final.json()["advance"]["receiving_amount"])) == Decimal("50000.00")

    # 7. Verify Recovery History in tbl_companyadvdetails
    await db_session.commit()
    det_rows = (await db_session.execute(
        select(CompanyAdvDetail).where(CompanyAdvDetail.CompanyAdvId == adv_id).order_by(CompanyAdvDetail.DetailId.asc())
    )).scalars().all()
    assert len(det_rows) == 2
    assert det_rows[0].Amount == Decimal("20000.00")
    assert det_rows[0].AccDocNo == "VCH-2026-901"
    assert det_rows[1].Amount == Decimal("30000.00")
    assert det_rows[1].AccDocNo == "VCH-FINAL-1"


# ==============================================================================
# 5. COMMERCIAL SALES REGISTER & ADVANCE REPORTS
# ==============================================================================

@pytest.mark.asyncio
async def test_commercial_reports(
    async_client: AsyncClient, db_session: AsyncSession
):
    _, admin_headers = await create_user_with_role(db_session, "ADMIN")

    # Setup company, client and invoice
    rc = ReliableCompany(RCompany="Report Test Co", Prefix="RPT", IsActive=True)
    cm = ClientMaster(Description="Report Client Ltd", IsActive=True)
    db_session.add(rc)
    db_session.add(cm)
    await db_session.commit()
    await db_session.refresh(rc)
    await db_session.refresh(cm)

    inv = SalesRegistration(
        InvoiceNo="RPT/1001",
        SalesDate=date(2026, 10, 12),
        RCompanyId=rc.RCompanyId,
        ClientMasterId=cm.ClientMasterId,
        amount=Decimal("1000.00"),
        CGSTPer=Decimal("9.00"),
        CGSTAmt=Decimal("90.00"),
        SGSTPer=Decimal("9.00"),
        SGSTAmt=Decimal("90.00"),
        IGSTPer=Decimal("0.00"),
        IGSTAmt=Decimal("0.00"),
        Total=Decimal("1180.00"),
        ReceivedAmt=Decimal("1180.00"),
        BalanceAmt=Decimal("0.00"),
    )
    db_session.add(inv)
    await db_session.commit()

    # Query Commercial Sales Register Report
    res_rpt = await async_client.get(
        f"/api/v1/commercial/invoices/report?r_company_id={rc.RCompanyId}",
        headers=admin_headers,
    )
    assert res_rpt.status_code == 200, res_rpt.text
    rpt_data = res_rpt.json()
    assert rpt_data["count"] == 1
    assert Decimal(str(rpt_data["total_taxable"])) == Decimal("1000.00")
    assert Decimal(str(rpt_data["total_cgst"])) == Decimal("90.00")
    assert Decimal(str(rpt_data["total_grand"])) == Decimal("1180.00")
    assert Decimal(str(rpt_data["total_received"])) == Decimal("1180.00")
    assert Decimal(str(rpt_data["total_balance"])) == Decimal("0.00")

    # Advance Report
    adv = CompanyAdvanceMaster(
        LedgerMID=999,
        compAdvDate=date(2026, 10, 5),
        Amount=Decimal("10000.00"),
        RecivingAmount=Decimal("5000.00"),
        BalanceAmt=Decimal("5000.00"),
    )
    db_session.add(adv)
    await db_session.commit()
    await db_session.refresh(adv)

    res_adv_rpt = await async_client.get(
        f"/api/v1/commercial/advances/report?advance_id={adv.CompanyAdvId}",
        headers=admin_headers,
    )
    assert res_adv_rpt.status_code == 200
    adv_rpt_data = res_adv_rpt.json()
    assert Decimal(str(adv_rpt_data["total_advance_amount"])) == Decimal("10000.00")
    assert Decimal(str(adv_rpt_data["total_recovered_amount"])) == Decimal("5000.00")
    assert Decimal(str(adv_rpt_data["total_balance_amount"])) == Decimal("5000.00")


# ==============================================================================
# 6. MASTER DELETION REFERENTIAL INTEGRITY & PRESERVATION
# ==============================================================================

@pytest.mark.asyncio
async def test_master_deletion_referential_integrity(
    async_client: AsyncClient, db_session: AsyncSession
):
    _, admin_headers = await create_user_with_role(db_session, "ADMIN")

    # Create unreferenced sales type
    st = SalesType(Description="Unreferenced Type", IsActive=True)
    db_session.add(st)
    await db_session.commit()
    await db_session.refresh(st)

    # Hard delete unreferenced sales type succeeds
    res_del_ok = await async_client.delete(f"/api/v1/commercial/sales-types/{st.SalesTypeId}?hard_delete=true", headers=admin_headers)
    assert res_del_ok.status_code == 200
    assert res_del_ok.json()["mode"] == "hard"

    # Create referenced sales type
    st2 = SalesType(Description="Referenced Type", IsActive=True)
    db_session.add(st2)
    await db_session.commit()
    await db_session.refresh(st2)

    # Attach invoice referencing st2
    inv = SalesRegistration(
        InvoiceNo="TEST/REF/01",
        SalesDate=date(2026, 10, 1),
        SalesTypeId=st2.SalesTypeId,
        ClientMasterId=1,
        amount=Decimal("100.00"),
        Total=Decimal("100.00"),
        ReceivedAmt=Decimal("0.00"),
        BalanceAmt=Decimal("100.00"),
    )
    db_session.add(inv)
    await db_session.commit()

    # Attempting hard delete on referenced sales type is blocked with 409 Conflict
    res_block = await async_client.delete(f"/api/v1/commercial/sales-types/{st2.SalesTypeId}?hard_delete=true", headers=admin_headers)
    assert res_block.status_code == 409
    err_msg = res_block.json().get("detail") or res_block.json().get("error", {}).get("message", "")
    assert "referenced by 1 commercial invoices" in err_msg

    # Soft delete succeeds
    res_soft = await async_client.delete(f"/api/v1/commercial/sales-types/{st2.SalesTypeId}?hard_delete=false", headers=admin_headers)
    assert res_soft.status_code == 200
    assert res_soft.json()["mode"] == "soft"


# ==============================================================================
# 7. CONCURRENT INVOICE NUMBER COLD-START & ALLOCATION TESTS (FIX A)
# ==============================================================================

@pytest.mark.asyncio
async def test_concurrent_invoice_number_cold_start_and_allocation(
    async_client: AsyncClient, db_session: AsyncSession
):
    """
    Simulates high-concurrency cold-start where tbl_invoicesequence has zero rows.
    Executes 10 concurrent invoice generation requests.
    Verifies:
    - Zero IntegrityError crashes on first-use initialization.
    - All 10 allocated invoice numbers are strictly unique and sequentially contiguous.
    """
    _, admin_headers = await create_user_with_role(db_session, "ADMIN")

    # 1. Setup company and client
    rc = ReliableCompany(RCompany="ColdStart Corp", Prefix="CSC", IsActive=True)
    cm = ClientMaster(Description="ColdStart Client Ltd", IsActive=True)
    db_session.add(rc)
    db_session.add(cm)
    # Purge sequence counter to guarantee true cold start
    await db_session.execute(text("DELETE FROM tbl_invoicesequence;"))
    await db_session.commit()
    await db_session.refresh(rc)
    await db_session.refresh(cm)

    invoice_payload = {
        "r_company_id": rc.RCompanyId,
        "client_master_id": cm.ClientMasterId,
        "sales_date": date(2026, 10, 20).isoformat(),
        "sales_type_id": 1,
        "registration_type": "COMMERCIAL_B2B",
        "description": "Concurrent Cold-Start Test Invoice",
        "items": [
            {
                "sales_type": "Retainer",
                "sales_type_id": 1,
                "taxable_amt": "100.00",
                "cgst_per": "9.00",
                "sgst_per": "9.00",
                "igst_per": "0.00",
            }
        ],
    }

    async def _post_invoice(worker_id: int):
        payload = dict(invoice_payload, description=f"Concurrent Worker #{worker_id}")
        return await async_client.post("/api/v1/commercial/invoices", json=payload, headers=admin_headers)

    # Fire 10 parallel requests
    responses = await asyncio.gather(*(_post_invoice(i) for i in range(10)))

    # All 10 must succeed with HTTP 201
    assert all(r.status_code == 201 for r in responses), [r.text for r in responses if r.status_code != 201]

    # Verify all 10 allocated invoice numbers are strictly unique
    allocated_numbers = [r.json()["invoice_no"] for r in responses]
    assert len(set(allocated_numbers)) == 10

    # Verify all numbers follow CSC/1001 through CSC/1010 pattern
    expected_numbers = {f"CSC/{i}" for i in range(1001, 1011)}
    assert set(allocated_numbers) == expected_numbers


# ==============================================================================
# 8. CONCURRENT DOC_NO COORDINATION BETWEEN PHASE 25 & PHASE 9 VOUCHERS (FIX B)
# ==============================================================================

@pytest.mark.asyncio
async def test_concurrent_doc_no_coordination_between_phase25_and_accounting_vouchers(
    async_client: AsyncClient, db_session: AsyncSession
):
    """
    Verifies that Phase 25 commercial sales invoices and Phase 9 accounting vouchers
    share the exact same database counter ('ACCOUNT_DOC_NO') without collisions or race conditions.
    Fires 5 commercial invoices and 5 manual accounting vouchers concurrently.
    Verifies all 10 allocated Doc_No values in tbl_account are strictly unique.
    """
    _, admin_headers = await create_user_with_role(db_session, "ADMIN")

    # 1. Setup Masters
    rc = ReliableCompany(RCompany="Coord Co", Prefix="CRD", IsActive=True)
    cm = ClientMaster(Description="Coord Client Ltd", IsActive=True)
    l_exp = LedgerMaster(
        LedgerTypeId=1, LedgerName="Coord Expense", LedgerGroupId=10,
        ReferenceId=0, BranchId=1, isdeleted="0"
    )
    l_bank = LedgerMaster(
        LedgerTypeId=2, LedgerName="Coord Bank", LedgerGroupId=20,
        ReferenceId=0, BranchId=1, isdeleted="0"
    )
    db_session.add(rc)
    db_session.add(cm)
    db_session.add(l_exp)
    db_session.add(l_bank)
    await db_session.commit()
    await db_session.refresh(rc)
    await db_session.refresh(cm)
    await db_session.refresh(l_exp)
    await db_session.refresh(l_bank)

    # Commercial Invoice Task
    async def _post_commercial_invoice(worker_id: int):
        payload = {
            "r_company_id": rc.RCompanyId,
            "client_master_id": cm.ClientMasterId,
            "sales_date": date(2026, 10, 20).isoformat(),
            "sales_type_id": 1,
            "description": f"Coord Commercial Invoice #{worker_id}",
            "items": [
                {
                    "sales_type": "Fee",
                    "sales_type_id": 1,
                    "taxable_amt": "200.00",
                    "cgst_per": "9.00",
                    "sgst_per": "9.00",
                    "igst_per": "0.00",
                }
            ],
        }
        return await async_client.post("/api/v1/commercial/invoices", json=payload, headers=admin_headers)

    # Accounting Voucher Task
    async def _post_accounting_voucher(worker_id: int):
        payload = {
            "voucher_type": "PAYMENT",
            "payment_mode": "NEFT",
            "narration": f"Coord Accounting Voucher #{worker_id}",
            "idempotency_key": f"IDEMP-COORD-{uuid.uuid4().hex[:6]}-{worker_id}",
            "lines": [
                {"ledger_m_id": l_exp.LedgerMId, "dr_cr": "DR", "amount": "100.00"},
                {"ledger_m_id": l_bank.LedgerMId, "dr_cr": "CR", "amount": "100.00"},
            ],
        }
        return await async_client.post("/api/v1/accounting/vouchers", json=payload, headers=admin_headers)

    # Interleave 5 commercial invoice and 5 accounting voucher requests concurrently
    tasks = []
    for i in range(5):
        tasks.append(_post_commercial_invoice(i))
        tasks.append(_post_accounting_voucher(i))

    responses = await asyncio.gather(*tasks)
    assert all(r.status_code == 201 for r in responses), [r.text for r in responses if r.status_code != 201]

    # Verify all Doc_No values recorded in tbl_account for these transactions
    await db_session.commit()
    rows = (await db_session.execute(
        select(Account.Doc_No).where(
            or_(
                Account.Narration == "sales Registration Amount",
                Account.Narration.like("Coord Accounting Voucher%"),
            )
        )
    )).scalars().all()

    distinct_docs = set(rows)
    assert len(distinct_docs) >= 10, f"Expected at least 10 unique Doc_Nos, got {len(distinct_docs)}: {distinct_docs}"


# ==============================================================================
# 9. CONCURRENT ADVANCE RECOVERY PESSIMISTIC LOCKING TESTS (FIX C)
# ==============================================================================

@pytest.mark.asyncio
async def test_concurrent_advance_recovery_pessimistic_locking(
    async_client: AsyncClient, db_session: AsyncSession
):
    """
    Deterministic concurrency test for Sister Concern Advance recovery engine:
    1. Two concurrent recovery attempts (₹6,000 each) against a ₹10,000 balance.
       Proves: Exactly 1 succeeds (200), exactly 1 rejected with 422 (over-recovery).
       Total recovered never exceeds initial available balance.
    2. Two concurrent recovery attempts (₹2,000 each) against the remaining ₹4,000 balance.
       Proves: Both succeed (200), driving balance to exactly ₹0.00.
    3. Two concurrent recovery attempts with identical AccDocNo voucher.
       Proves: Exactly 1 succeeds, duplicate voucher rejected with 409 Conflict.
    """
    _, admin_headers = await create_user_with_role(db_session, "ADMIN")

    # 1. Create advance facility of ₹10,000.00
    adv = CompanyAdvanceMaster(
        LedgerMID=555,
        compAdvDate=date(2026, 10, 1),
        Amount=Decimal("10000.00"),
        RecivingAmount=Decimal("0.00"),
        BalanceAmt=Decimal("10000.00"),
        Description="Locking Test Facility",
    )
    db_session.add(adv)
    await db_session.commit()
    await db_session.refresh(adv)
    adv_id = adv.CompanyAdvId

    # Part A: Two concurrent recoveries of ₹6,000.00 (Total ₹12,000 > ₹10,000 balance)
    async def _attempt_recovery(amount: str, vch: str):
        payload = {
            "recovery_amount": amount,
            "recovery_date": date(2026, 10, 20).isoformat(),
            "acc_doc_no": vch,
            "narration": f"Concurrent tranche {vch}",
        }
        return await async_client.post(f"/api/v1/commercial/advances/{adv_id}/recover", json=payload, headers=admin_headers)

    resp_a, resp_b = await asyncio.gather(
        _attempt_recovery("6000.00", "VCH-LOCK-A1"),
        _attempt_recovery("6000.00", "VCH-LOCK-A2"),
    )

    statuses = {resp_a.status_code, resp_b.status_code}
    assert statuses == {200, 422}, f"Expected {200, 422}, got {statuses}"

    failed_resp = resp_a if resp_a.status_code == 422 else resp_b
    err_msg = failed_resp.json().get("detail") or failed_resp.json().get("error", {}).get("message", "")
    assert "cannot exceed available advance balance" in err_msg

    # Verify database state after Part A
    await db_session.commit()
    db_session.expire_all()
    adv_after_a = await db_session.get(CompanyAdvanceMaster, adv_id)
    assert adv_after_a.BalanceAmt == Decimal("4000.00")
    assert adv_after_a.RecivingAmount == Decimal("6000.00")

    det_rows_a = (await db_session.execute(
        select(CompanyAdvDetail).where(CompanyAdvDetail.CompanyAdvId == adv_id)
    )).scalars().all()
    assert len(det_rows_a) == 1

    # Part B: Two concurrent recoveries of ₹2,000.00 each against remaining ₹4,000.00 balance
    resp_c, resp_d = await asyncio.gather(
        _attempt_recovery("2000.00", "VCH-LOCK-B1"),
        _attempt_recovery("2000.00", "VCH-LOCK-B2"),
    )
    assert resp_c.status_code == 200
    assert resp_d.status_code == 200

    # Verify database state after Part B
    await db_session.commit()
    db_session.expire_all()
    adv_after_b = await db_session.get(CompanyAdvanceMaster, adv_id)
    assert adv_after_b.BalanceAmt == Decimal("0.00")
    assert adv_after_b.RecivingAmount == Decimal("10000.00")

    det_rows_b = (await db_session.execute(
        select(CompanyAdvDetail).where(CompanyAdvDetail.CompanyAdvId == adv_id)
    )).scalars().all()
    assert len(det_rows_b) == 3

    # Part C: Concurrent duplicate voucher submission against a new advance
    adv2 = CompanyAdvanceMaster(
        LedgerMID=556,
        compAdvDate=date(2026, 10, 1),
        Amount=Decimal("5000.00"),
        RecivingAmount=Decimal("0.00"),
        BalanceAmt=Decimal("5000.00"),
    )
    db_session.add(adv2)
    await db_session.commit()
    await db_session.refresh(adv2)

    async def _attempt_dup_recovery(worker_id: int):
        payload = {
            "recovery_amount": "1000.00",
            "recovery_date": date(2026, 10, 20).isoformat(),
            "acc_doc_no": "VCH-SAME-DOC-99",
            "narration": f"Worker {worker_id}",
        }
        return await async_client.post(f"/api/v1/commercial/advances/{adv2.CompanyAdvId}/recover", json=payload, headers=admin_headers)

    resp_dup1, resp_dup2 = await asyncio.gather(_attempt_dup_recovery(1), _attempt_dup_recovery(2))
    dup_statuses = {resp_dup1.status_code, resp_dup2.status_code}
    assert dup_statuses == {200, 409}, f"Expected {200, 409}, got {dup_statuses}"


# ==============================================================================
# 10. ATOMIC ROLLBACK FAILURE INJECTION TESTS (FIX D)
# ==============================================================================

@pytest.mark.asyncio
async def test_invoice_creation_atomic_rollback_on_failure(
    db_session: AsyncSession
):
    """
    Proves that a failure midway through commercial invoice generation rolls back
    every participating write:
    - Injected failure during line-item persistence -> Rollback.
    - Injected failure during general ledger posting -> Rollback.
    - In both cases: No orphan header, no orphan details, no orphan ledger entry,
      and sequence counter is preserved.
    - Subsequent valid invoice succeeds cleanly on a healthy session.
    """
    rc = ReliableCompany(RCompany="Rollback Co", Prefix="RBK", IsActive=True)
    cm = ClientMaster(Description="Rollback Client Ltd", IsActive=True)
    user, _ = await create_user_with_role(db_session, "ADMIN")
    db_session.add(rc)
    db_session.add(cm)
    await db_session.commit()
    await db_session.refresh(rc)
    await db_session.refresh(cm)
    await db_session.refresh(user)
    rc_id = rc.RCompanyId
    cm_id = cm.ClientMasterId
    user_id = user.UserId

    invoice_payload = CommercialInvoiceCreateRequest(
        r_company_id=rc_id,
        client_master_id=cm_id,
        sales_date=date(2026, 10, 20),
        sales_type_id=1,
        registration_type="COMMERCIAL_B2B",
        description="Rollback Test Invoice",
        items=[
            CommercialInvoiceLineItemCreate(
                sales_type="Audit",
                sales_type_id=1,
                taxable_amt=Decimal("500.00"),
                cgst_per=Decimal("9.00"),
                sgst_per=Decimal("9.00"),
                igst_per=Decimal("0.00"),
            )
        ],
    )

    # 1. Injected failure during line-item persistence (after counter allocation)
    service = Phase25Service(db_session)

    with patch.object(db_session, "flush", side_effect=RuntimeError("Simulated database failure during flush")):
        with pytest.raises(RuntimeError, match="Simulated database failure during flush"):
            await service.create_commercial_invoice(invoice_payload, current_user=user)
        await db_session.rollback()

    # Verify zero partial records persisted
    headers = (await db_session.execute(
        select(SalesRegistration).where(SalesRegistration.RCompanyId == rc_id)
    )).scalars().all()
    assert len(headers) == 0

    accounts = (await db_session.execute(
        select(Account).where(Account.Extra1.like("RBK/%"))
    )).scalars().all()
    assert len(accounts) == 0

    # 2. Injected failure during general ledger Doc_No allocation
    user = await db_session.get(User, user_id)
    with patch.object(service, "_allocate_doc_no", side_effect=RuntimeError("Simulated Doc_No allocation crash")):
        with pytest.raises(RuntimeError, match="Simulated Doc_No allocation crash"):
            await service.create_commercial_invoice(invoice_payload, current_user=user)
        await db_session.rollback()

    headers2 = (await db_session.execute(
        select(SalesRegistration).where(SalesRegistration.RCompanyId == rc_id)
    )).scalars().all()
    assert len(headers2) == 0

    # 3. Subsequent valid request on healthy session succeeds completely
    user = await db_session.get(User, user_id)
    resp = await service.create_commercial_invoice(invoice_payload, current_user=user)
    assert resp.invoice_no == "RBK/1001"
    assert resp.total == Decimal("590.00")

    await db_session.commit()
    header_ok = (await db_session.execute(
        select(SalesRegistration).where(SalesRegistration.InvoiceNo == "RBK/1001")
    )).scalar_one_or_none()
    assert header_ok is not None

    details_ok = (await db_session.execute(
        select(SalesRegDetails).where(SalesRegDetails.InvoiceNo == "RBK/1001")
    )).scalars().all()
    assert len(details_ok) == 1

    acc_ok = (await db_session.execute(
        select(Account).where(Account.Extra1 == "RBK/1001")
    )).scalar_one_or_none()
    assert acc_ok is not None
    assert acc_ok.amount == Decimal("-590.00")


# ==============================================================================
# 11. FINANCIAL LINE-BY-LINE VS AGGREGATE ROUNDING DISTINCTION TEST (SECTION 6)
# ==============================================================================

@pytest.mark.asyncio
async def test_financial_line_vs_aggregate_rounding_distinction(
    async_client: AsyncClient, db_session: AsyncSession
):
    """
    Demonstrates and validates financial rounding behavior:
    Distinguishes line-item tax calculation from aggregate calculation.
    Case:
    - Line 1: Taxable ₹10.30 @ 5% CGST, 5% SGST
      CGST = 10.30 * 0.05 = 0.515 -> round_bankers_rupee = ₹1.00
      SGST = 10.30 * 0.05 = 0.515 -> round_bankers_rupee = ₹1.00
      Line 1 Total = 10.30 + 1 + 1 = 12.30 -> round_bankers_rupee = ₹12.00
    - Line 2: Identical to Line 1 -> Line 2 Total = ₹12.00
    - Sum of Line Totals = 12.00 + 12.00 = ₹24.00
    - Comparison if aggregate had been rounded instead:
      Aggregate Taxable = 20.60
      Aggregate CGST = 20.60 * 0.05 = 1.03 -> ₹1.00
      Aggregate SGST = 20.60 * 0.05 = 1.03 -> ₹1.00
      Aggregate Grand Total = 20.60 + 1 + 1 = 22.60 -> ₹23.00 (!= ₹24.00)
    Proves:
    - The implementation stores Total = ₹24.00, guaranteeing that
      tbl_salesregistration.Total is identically equal to sum(tbl_salesregdetails.Total).
    - Preserves exact parity with legacy C# where tbl_salesregistration.Total was set
      directly from the line item calculation.
    """
    _, admin_headers = await create_user_with_role(db_session, "ADMIN")

    rc = ReliableCompany(RCompany="Tax Parity Corp", Prefix="TPC", IsActive=True)
    cm = ClientMaster(Description="Tax Parity Client", IsActive=True)
    db_session.add(rc)
    db_session.add(cm)
    await db_session.commit()
    await db_session.refresh(rc)
    await db_session.refresh(cm)

    invoice_payload = {
        "r_company_id": rc.RCompanyId,
        "client_master_id": cm.ClientMasterId,
        "sales_date": date(2026, 10, 20).isoformat(),
        "sales_type_id": 1,
        "description": "Tax Rounding Parity Invoice",
        "items": [
            {
                "sales_type": "Tranche 1",
                "sales_type_id": 1,
                "taxable_amt": "10.30",
                "cgst_per": "5.00",
                "sgst_per": "5.00",
                "igst_per": "0.00",
            },
            {
                "sales_type": "Tranche 2",
                "sales_type_id": 1,
                "taxable_amt": "10.30",
                "cgst_per": "5.00",
                "sgst_per": "5.00",
                "igst_per": "0.00",
            },
        ],
    }

    res = await async_client.post("/api/v1/commercial/invoices", json=invoice_payload, headers=admin_headers)
    assert res.status_code == 201, res.text
    data = res.json()

    line1 = data["items"][0]
    line2 = data["items"][1]
    assert Decimal(str(line1["taxable_amt"])) == Decimal("10.30")
    assert Decimal(str(line1["cgst_amt"])) == Decimal("1.00")
    assert Decimal(str(line1["sgst_amt"])) == Decimal("1.00")
    assert Decimal(str(line1["total"])) == Decimal("12.00")

    assert Decimal(str(line2["taxable_amt"])) == Decimal("10.30")
    assert Decimal(str(line2["cgst_amt"])) == Decimal("1.00")
    assert Decimal(str(line2["sgst_amt"])) == Decimal("1.00")
    assert Decimal(str(line2["total"])) == Decimal("12.00")

    assert Decimal(str(data["amount"])) == Decimal("20.60")
    assert Decimal(str(data["cgst_amt"])) == Decimal("2.00")
    assert Decimal(str(data["sgst_amt"])) == Decimal("2.00")
    assert Decimal(str(data["total"])) == Decimal("24.00")

    await db_session.commit()
    acc = (await db_session.execute(
        select(Account).where(Account.Extra1 == data["invoice_no"])
    )).scalar_one_or_none()
    assert acc is not None
    assert acc.amount == Decimal("-24.00")

