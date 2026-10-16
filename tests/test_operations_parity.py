"""
Phase 18A Automated Test Suite — Complete Remaining Legacy Feature Implementation.
Covers all 10 SHOULD features (F-17B-083..088, F-17B-091..094) and all 7 ENHANCE
features (F-17B-089..090, F-17B-095..099), including:
- Happy-path E2E verification
- Input validation (422 Unprocessable Entity)
- Unauthenticated (401) & RBAC authorization (403) gates
- Decimal financial precision & idempotency
- Mocked external provider adapters (Attestr RC, HiCaliber OCR, Google Reverse Geocode, Email)
"""
from datetime import date, datetime, timedelta
from decimal import Decimal
import io
import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.quotation import AppQuotationRequest
from app.models.profile import Agent
from app.providers.attestr import AttestrRCProvider
from tests.integration.test_phase7_policy_booking_api import create_user_with_role
from tests.integration.test_phase12_search import make_synthetic_tx


async def _insert_test_tx(db_session: AsyncSession, **overrides) -> int:
    tx = make_synthetic_tx(
        policy_no=overrides.get("PolicyNo", "POL-18A-001"),
        branch_id=overrides.get("BranchId", 1),
        pending_status=overrides.get("pendingStatus", 0),
    )
    for k, v in overrides.items():
        setattr(tx, k, v)
    db_session.add(tx)
    await db_session.flush()
    return tx.TransanctionId


@pytest.fixture(autouse=True)
async def cleanup_phase18a_tables(db_session: AsyncSession):
    """Purge synthetic Phase 18A tables before and after each test."""
    tables = [
        "tbl_idealpaymentreceipt",
        "tbl_commission_rate_grid",
        "tbl_remainingpendingcash",
        "tbl_salesregistration",
        "tbl_inspectionrequest",
        "tbl_supportapp",
        "tbl_callingimportdata",
        "tbl_cashback",
        "tbl_app_requestedquotationfile",
    ]
    for tbl in tables:
        await db_session.execute(text(f"DELETE FROM {tbl};"))
    await db_session.commit()
    yield
    for tbl in tables:
        await db_session.execute(text(f"DELETE FROM {tbl};"))
    await db_session.commit()


# ==============================================================================
# 1. F-17B-083: Outbound HiCaliber Policy PDF Upload, Pre-Fill & Link Transaction
# ==============================================================================
@pytest.mark.asyncio
async def test_f17b_083_policy_pdf_extraction_upload_prefill_and_link(
    async_client: AsyncClient, db_session: AsyncSession
):
    _, admin_headers = await create_user_with_role(db_session, "ADMIN")
    tx_id = await _insert_test_tx(
        db_session,
        PolicyNo="POL-18A-DUP-001",
        BranchId=1,
        OutstandingAmount=Decimal("0.00"),
    )
    await db_session.commit()

    # 1. Reject non-PDF upload (422)
    bad_files = {"file": ("invalid.txt", b"not a pdf", "text/plain")}
    res_bad = await async_client.post(
        "/api/v1/documents/policy-extraction/upload",
        files=bad_files,
        headers=admin_headers,
    )
    assert res_bad.status_code == 422

    # 2. Valid PDF upload with duplicate policy number hint
    pdf_bytes = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"
    files = {"file": ("motor_schedule.pdf", pdf_bytes, "application/pdf")}
    data = {"policy_no_hint": "POL-18A-DUP-001"}
    res_up = await async_client.post(
        "/api/v1/documents/policy-extraction/upload",
        files=files,
        data=data,
        headers=admin_headers,
    )
    assert res_up.status_code == 201, res_up.text
    up_body = res_up.json()
    calliber_id = up_body["calliber_policy_id"]
    identifier = up_body["policy_identifier"]
    assert up_body["extraction_status"] == "EXTRACTED"
    assert up_body["duplicate_policy_exists"] is True
    assert up_body["extracted_fields"]["policy_number"] == "POL-18A-DUP-001"

    # 3. Pre-fill lookup by policy_identifier
    res_pre = await async_client.get(
        f"/api/v1/documents/policy-extraction/{identifier}/prefill",
        headers=admin_headers,
    )
    assert res_pre.status_code == 200, res_pre.text
    pre_body = res_pre.json()
    assert pre_body["calliber_policy_id"] == calliber_id
    assert pre_body["policy_number"] == "POL-18A-DUP-001"
    assert Decimal(str(pre_body["gross_premium"])) == Decimal("14160.00")
    assert pre_body["duplicate_policy_exists"] is True
    assert tx_id in pre_body["duplicate_transaction_ids"]

    # 4. Link extracted record to Transaction (sp_PE_UpdateTransId_bycalliber_policyId)
    res_link = await async_client.post(
        f"/api/v1/documents/policy-extraction/{calliber_id}/link-transaction",
        json={"transaction_id": tx_id},
        headers=admin_headers,
    )
    assert res_link.status_code == 200, res_link.text
    assert res_link.json()["status"] == "LINKED"
    assert res_link.json()["transaction_id"] == tx_id


# ==============================================================================
# 2. F-17B-084: Extended Operator Lockouts (Pending Cash & Pending App Trans)
# ==============================================================================
@pytest.mark.asyncio
async def test_f17b_084_pending_cash_and_app_transaction_locks(
    async_client: AsyncClient, db_session: AsyncSession
):
    _, admin_headers = await create_user_with_role(db_session, "ADMIN")
    op_user, op_headers = await create_user_with_role(db_session, "OPERATOR", branch_id=105)

    # Create overdue cash transaction for Mumbai branch (105) older than 4 days
    four_days_ago = datetime.utcnow() - timedelta(days=4)
    await _insert_test_tx(
        db_session,
        PolicyNo="POL-MUM-CASH-01",
        BranchId=105,
        TransDate=four_days_ago,
        OutstandingAmount=Decimal("3500.00"),
        pendingStatus=1,
        CreateUser=str(op_user.UserId),
    )
    await db_session.commit()

    # Check operator lock status before account deactivation
    status_res = await async_client.get(
        "/api/v1/batch-tasks/operator-lock-status",
        headers=op_headers,
    )
    assert status_res.status_code == 200, status_res.text
    st_body = status_res.json()
    assert st_body["is_mumbai_branch"] is True
    assert st_body["pending_cash_overdue_count"] >= 1
    assert st_body["is_locked"] is True

    # Run pending cash lock batch enforcement (dry-run apply_user_lock=False so op_headers stay valid for next check)
    cash_lock_res = await async_client.post(
        "/api/v1/batch-tasks/enforce-pending-cash-locks",
        json={
            "default_threshold_days": 2,
            "mumbai_branch_id": 105,
            "mumbai_threshold_days": 3,
            "apply_user_lock": False,
        },
        headers=admin_headers,
    )
    assert cash_lock_res.status_code == 200, cash_lock_res.text
    cl_body = cash_lock_res.json()
    assert cl_body["overdue_mumbai_branch_count"] >= 1

    # Run pending app transaction lock enforcement
    app_lock_res = await async_client.post(
        "/api/v1/batch-tasks/enforce-pending-app-transaction-locks",
        json={"threshold_days": 1, "apply_user_lock": False},
        headers=admin_headers,
    )
    assert app_lock_res.status_code == 200, app_lock_res.text
    assert "evaluated_app_transactions" in app_lock_res.json()


# ==============================================================================
# 3. F-17B-085 & F-17B-090: Ideal Payment Receipts, InstaPay & Authority Summary
# ==============================================================================
@pytest.mark.asyncio
async def test_f17b_085_and_090_ideal_receipts_instapay_and_authority_summary(
    async_client: AsyncClient, db_session: AsyncSession
):
    _, admin_headers = await create_user_with_role(db_session, "ADMIN")
    tx_id = await _insert_test_tx(db_session, PolicyNo="POL-IDEAL-101", BranchId=1)
    await db_session.commit()

    # 1. Bulk upload Ideal receipts (with duplicate doc_no in same batch to verify idempotency)
    bulk_payload = {
        "receipts": [
            {
                "ideal_doc_no": "IDL-2026-0001",
                "payment_date": "2026-10-08",
                "posp_type_id": 1,
                "posp_id": 501,
                "ideal_amount": "4250.50",
                "ideal_neft_no": "NEFT998877",
                "policy_no": "POL-IDEAL-101",
                "transaction_id": tx_id,
                "receipt_type": "Regular",
            },
            {
                "ideal_doc_no": "IDL-2026-0001",
                "payment_date": "2026-10-08",
                "posp_type_id": 1,
                "posp_id": 501,
                "ideal_amount": "4250.50",
                "ideal_neft_no": "NEFT998877",
                "policy_no": "POL-IDEAL-101",
                "transaction_id": tx_id,
                "receipt_type": "Regular",
            },
        ]
    }
    res_bulk = await async_client.post(
        "/api/v1/commission-payouts/ideal-payment-receipts/bulk",
        json=bulk_payload,
        headers=admin_headers,
    )
    assert res_bulk.status_code == 201, res_bulk.text
    b_body = res_bulk.json()
    assert b_body["total_submitted"] == 2
    assert b_body["inserted_count"] == 1
    assert b_body["duplicate_skipped_count"] == 1
    assert Decimal(str(b_body["total_settled_amount"])) == Decimal("4250.50")

    # 2. Submit InstaPay request
    res_insta = await async_client.post(
        "/api/v1/commission-payouts/instapay/requests",
        json={
            "transaction_id": tx_id,
            "agent_id": 501,
            "requested_amount": "1500.25",
            "neft_reference": "INSTA-NEFT-01",
            "remark": "Fast payout",
        },
        headers=admin_headers,
    )
    assert res_insta.status_code == 201, res_insta.text
    assert res_insta.json()["receipt_type"] == "Insta"

    # 3. Get Daily InstaPay Authority Summary (F-17B-090)
    res_sum = await async_client.get(
        "/api/v1/reports/operations/instapay-authority-summary",
        headers=admin_headers,
    )
    assert res_sum.status_code == 200, res_sum.text
    sum_body = res_sum.json()
    assert sum_body["total_policies"] == 2
    assert Decimal(str(sum_body["total_instapay_payout"])) == Decimal("1500.25")
    assert Decimal(str(sum_body["total_gross_premium"])) == Decimal("5750.75")

    # 4. Dispatch Authority Summary Email with PDF attachment
    res_disp = await async_client.post(
        "/api/v1/reports/operations/instapay-authority-summary/dispatch",
        json={"recipients": ["authority@reliable.local"], "attach_pdf": True},
        headers=admin_headers,
    )
    assert res_disp.status_code == 200, res_disp.text
    assert res_disp.json()["dispatch_status"] == "SENT"


# ==============================================================================
# 4. F-17B-086: Commission Rate Grid CRUD, CSV Import & Reliance 90%/60% Capping
# ==============================================================================
@pytest.mark.asyncio
async def test_f17b_086_commission_grids_and_reliance_capping(
    async_client: AsyncClient, db_session: AsyncSession
):
    _, admin_headers = await create_user_with_role(db_session, "ADMIN")

    # 1. Create Commission Rate Grid
    res_grid = await async_client.post(
        "/api/v1/commissions/grids",
        json={
            "grid_scope": "BROKER",
            "insurance_company_id": 4,
            "vehi_type_id": 1,
            "broker_id": 10,
            "commission_od": "27.50",
            "commission_net": "15.00",
            "commission_tp": "2.50",
            "od_discount": "55.00",
            "cal_on": "OD",
        },
        headers=admin_headers,
    )
    assert res_grid.status_code == 201, res_grid.text
    assert Decimal(str(res_grid.json()["commission_od"])) == Decimal("27.50")

    # 2. CSV Import of Commission Rate Grids
    csv_content = (
        "grid_scope,insurance_company_id,vehi_type_id,agent_id,commission_od,commission_net,commission_tp,od_discount,cal_on\n"
        "AGENT,4,2,88,22.00,12.00,0.00,50.00,OD\n"
    ).encode("utf-8")
    res_csv = await async_client.post(
        "/api/v1/commissions/grids/import-csv",
        files={"file": ("grids.csv", csv_content, "text/csv")},
        headers=admin_headers,
    )
    assert res_csv.status_code == 201, res_csv.text
    assert len(res_csv.json()) == 1

    # 3. Lookup grids
    res_lookup = await async_client.get(
        "/api/v1/commissions/grids/lookup?insurance_company_id=4",
        headers=admin_headers,
    )
    assert res_lookup.status_code == 200
    assert len(res_lookup.json()) == 2

    # 4. Evaluate Reliance 90% Capping & 60% Max OD Discount (sp_CappingForRelianceCompany)
    # Input: Grid = 35%, OD Discount = 65% -> OD capped to 60%, Effective Grid capped to 90 - 60 = 30%
    res_cap = await async_client.post(
        "/api/v1/commissions/capping/reliance-evaluate",
        json={
            "grid_percent": "35.00",
            "od_discount_percent": "65.00",
            "od_premium": "10000.00",
        },
        headers=admin_headers,
    )
    assert res_cap.status_code == 200, res_cap.text
    cap = res_cap.json()
    assert cap["is_od_discount_capped"] is True
    assert Decimal(str(cap["effective_od_discount_percent"])) == Decimal("60.00")
    assert cap["is_total_capping_applied"] is True
    assert Decimal(str(cap["effective_grid_percent"])) == Decimal("30.00")
    assert Decimal(str(cap["effective_commission_amount"])) == Decimal("3000.00")


# ==============================================================================
# 5. F-17B-087: Remaining / Shortfall Cash Premium Ledger & Cashier Approval
# ==============================================================================
@pytest.mark.asyncio
async def test_f17b_087_remaining_pending_cash_lifecycle(
    async_client: AsyncClient, db_session: AsyncSession
):
    _, admin_headers = await create_user_with_role(db_session, "ADMIN")
    _, agent_headers = await create_user_with_role(db_session, "AGENT")

    # 1. Create Shortfall Cash record
    res_create = await async_client.post(
        "/api/v1/payments/remaining-cash",
        json={
            "transaction_ids": [101, 102],
            "total_premium": "15000.00",
            "paid_premium": "12000.00",
            "agent_id": 7,
            "branch_id": 1,
            "remark": "Customer paying shortfall tomorrow",
        },
        headers=agent_headers,
    )
    assert res_create.status_code == 201, res_create.text
    created = res_create.json()
    pending_cash_id = created["pending_cash_id"]
    assert Decimal(str(created["remaining_premium"])) == Decimal("3000.00")
    assert created["remaining_status"] == "Short Fall"
    assert created["cashier_approval"] == 0

    # 2. Agent role cannot approve remaining cash (403 Forbidden)
    res_forbidden = await async_client.post(
        f"/api/v1/payments/remaining-cash/{pending_cash_id}/approve",
        json={"approved": True, "additional_paid_amount": "3000.00"},
        headers=agent_headers,
    )
    assert res_forbidden.status_code == 403

    # 3. Cashier/Admin approves and settles shortfall
    res_app = await async_client.post(
        f"/api/v1/payments/remaining-cash/{pending_cash_id}/approve",
        json={
            "approved": True,
            "additional_paid_amount": "3000.00",
            "remark": "Shortfall collected in cash",
        },
        headers=admin_headers,
    )
    assert res_app.status_code == 200, res_app.text
    app_body = res_app.json()
    assert Decimal(str(app_body["remaining_premium"])) == Decimal("0.00")
    assert app_body["remaining_status"] == "Completed"
    assert app_body["cashier_approval"] == 1


# ==============================================================================
# 6. F-17B-088 & F-17B-099: B2B Sales Invoice Registration & Office Expenses
# ==============================================================================
@pytest.mark.asyncio
async def test_f17b_088_and_099_sales_registration_and_office_expenses(
    async_client: AsyncClient, db_session: AsyncSession
):
    _, admin_headers = await create_user_with_role(db_session, "ADMIN")

    # 1. Create B2B Sales Invoice Registration (100,000 + 9% CGST + 9% SGST = 118,000)
    res_sr = await async_client.post(
        "/api/v1/accounting/sales-registrations",
        json={
            "invoice_no": "RA/2026-27/INV-009",
            "sales_date": "2026-10-08",
            "client_master_id": 4,
            "ledger_m_id": 2004,
            "description": "October Brokerage Invoice",
            "amount": "100000.00",
            "cgst_per": "9.00",
            "sgst_per": "9.00",
            "igst_per": "0.00",
        },
        headers=admin_headers,
    )
    assert res_sr.status_code == 201, res_sr.text
    sr = res_sr.json()
    sr_id = sr["sales_reg_id"]
    assert Decimal(str(sr["cgst_amt"])) == Decimal("9000.00")
    assert Decimal(str(sr["sgst_amt"])) == Decimal("9000.00")
    assert Decimal(str(sr["total"])) == Decimal("118000.00")
    assert Decimal(str(sr["balance_amt"])) == Decimal("118000.00")

    # 2. Adjust Company Advance Master against Sales Invoice
    res_adj = await async_client.post(
        f"/api/v1/accounting/sales-registrations/{sr_id}/adjust-advance",
        json={
            "received_amount": "50000.00",
            "history_date": "2026-10-08",
            "acc_doc_no": "ADV-DOC-2026-01",
            "narration": "Partial insurer payout adjustment",
        },
        headers=admin_headers,
    )
    assert res_adj.status_code == 200, res_adj.text
    adj = res_adj.json()
    assert Decimal(str(adj["received_amt"])) == Decimal("50000.00")
    assert Decimal(str(adj["balance_amt"])) == Decimal("68000.00")

    # 3. Create Petty Office Expense & Stationary Voucher (F-17B-099)
    res_exp = await async_client.post(
        "/api/v1/accounting/office-expenses",
        json={
            "voucher_no": "EXP-2026-101",
            "expense_date": "2026-10-08",
            "expense_category": "STATIONARY",
            "vendor_or_payee": "Shree Stationers Pune",
            "amount": "1850.00",
            "payment_mode": "CASH",
            "branch_id": 1,
            "narration": "A4 paper rims and printer toner",
        },
        headers=admin_headers,
    )
    assert res_exp.status_code == 201, res_exp.text
    exp = res_exp.json()
    assert exp["voucher_no"] == "EXP-2026-101"
    assert Decimal(str(exp["amount"])) == Decimal("1850.00")

    res_exp_list = await async_client.get(
        "/api/v1/accounting/office-expenses?branch_id=1",
        headers=admin_headers,
    )
    assert res_exp_list.status_code == 200
    assert any(x["voucher_no"] == "EXP-2026-101" for x in res_exp_list.json())


# ==============================================================================
# 7. F-17B-091: Vehicle Break-In Inspection Coordinator Request Queue
# ==============================================================================
@pytest.mark.asyncio
async def test_f17b_091_inspection_coordinator_queue_and_decision(
    async_client: AsyncClient, db_session: AsyncSession
):
    _, admin_headers = await create_user_with_role(db_session, "ADMIN")

    # 1. Create Break-In Inspection Request
    res_insp = await async_client.post(
        "/api/v1/inspections",
        json={
            "registration_no": "mh14xy9876",
            "customer_name": "Vikram Deshmukh",
            "mobile_no": "9822011223",
            "insurance_company_id": 2,
            "vehicle_type_id": 1,
            "branch_id": 1,
            "remark": "Policy expired 10 days ago, break-in inspection needed",
        },
        headers=admin_headers,
    )
    assert res_insp.status_code == 201, res_insp.text
    insp_id = res_insp.json()["inspection_id"]
    assert res_insp.json()["registration_no"] == "MH14XY9876"
    assert res_insp.json()["inspection_status"] == "PENDING"

    # 2. Check pending inspection notification count (BLL_SelectInspectionMsgCount)
    res_cnt = await async_client.get(
        "/api/v1/inspections/pending-count?branch_id=1",
        headers=admin_headers,
    )
    assert res_cnt.status_code == 200
    assert res_cnt.json()["pending_inspection_count"] == 1

    # 3. Coordinator approves inspection with LeadNo and PDF report
    res_dec = await async_client.post(
        f"/api/v1/inspections/{insp_id}/decision",
        json={
            "decision": "APPROVED",
            "lead_no": "LEAD-INSP-2026-99",
            "inspection_pdf_path": "QuotationFile/Inspection_MH14XY9876.pdf",
            "image_paths": ["InspectionImages/front.jpg", "InspectionImages/odometer.jpg"],
            "remark": "Odometer and chassis verified clear",
        },
        headers=admin_headers,
    )
    assert res_dec.status_code == 200, res_dec.text
    dec = res_dec.json()
    assert dec["inspection_status"] == "APPROVED"
    assert dec["is_owner"] == 1
    assert dec["lead_no"] == "LEAD-INSP-2026-99"
    assert len(dec["image_paths"]) == 2


# ==============================================================================
# 8. F-17B-092: Internal IT / Operator / Admin Support Ticketing Portal
# ==============================================================================
@pytest.mark.asyncio
async def test_f17b_092_support_ticketing_portal_lifecycle(
    async_client: AsyncClient, db_session: AsyncSession
):
    _, admin_headers = await create_user_with_role(db_session, "ADMIN")
    _, agent_headers = await create_user_with_role(db_session, "AGENT")

    # 1. Agent creates support ticket
    res_create = await async_client.post(
        "/api/v1/admin/support-tickets",
        json={
            "support_type_id": 2,
            "support_type": "POLICY_CORRECTION",
            "remark": "Please update hypothecation bank name on policy #9921",
            "attachment_file_name": "rc_copy.pdf",
        },
        headers=agent_headers,
    )
    assert res_create.status_code == 201, res_create.text
    support_id = res_create.json()["support_id"]
    assert res_create.json()["status"] == "OPEN"

    # 2. Check badge counts
    res_counts = await async_client.get(
        "/api/v1/admin/support-tickets/counts",
        headers=admin_headers,
    )
    assert res_counts.status_code == 200
    assert res_counts.json()["open_count"] >= 1

    # 3. Add threaded remark
    res_rem = await async_client.post(
        f"/api/v1/admin/support-tickets/{support_id}/remarks",
        json={"remark": "Checking with insurer endorsement team", "remark_from": "IT"},
        headers=admin_headers,
    )
    assert res_rem.status_code == 200
    assert len(res_rem.json()["remarks_thread"]) == 2

    # 4. Resolve & approve support ticket
    res_stat = await async_client.patch(
        f"/api/v1/admin/support-tickets/{support_id}/status",
        json={"status": "RESOLVED", "is_approved": True, "remark": "Endorsement completed"},
        headers=admin_headers,
    )
    assert res_stat.status_code == 200, res_stat.text
    assert res_stat.json()["status"] == "RESOLVED"
    assert res_stat.json()["is_approved"] == 1


# ==============================================================================
# 9. F-17B-093 & F-17B-098: Telecalling Leads CRM & Field Visit GPS Check-In
# ==============================================================================
@pytest.mark.asyncio
async def test_f17b_093_and_098_telecalling_crm_and_gps_check_in(
    async_client: AsyncClient, db_session: AsyncSession
):
    admin_user, admin_headers = await create_user_with_role(db_session, "ADMIN")
    today_str = date.today().isoformat()

    # 1. Import telecalling leads
    res_imp = await async_client.post(
        "/api/v1/renewals/telecalling/leads/import",
        json={
            "leads": [
                {
                    "registration_no": "mh12tc4567",
                    "owner_name": "Sanjay Kulkarni",
                    "mobile_no": "9890012345",
                    "maker_model": "HONDA CITY ZX",
                }
            ]
        },
        headers=admin_headers,
    )
    assert res_imp.status_code == 201, res_imp.text
    lead_id = res_imp.json()[0]["calling_import_id"]

    # 2. Assign lead & record call disposition with FollowUpDate = today
    res_disp = await async_client.post(
        f"/api/v1/renewals/telecalling/leads/{lead_id}/dispositions",
        json={
            "calling_status_id": 2,
            "follow_up_date": today_str,
            "note": "Customer asked for Zero-Dep quote callback today",
        },
        headers=admin_headers,
    )
    assert res_disp.status_code == 200, res_disp.text
    assert res_disp.json()["calling_status_name"] == "INTERESTED_CALLBACK"

    # 3. Query FollowUpToday queue
    res_q = await async_client.get(
        f"/api/v1/renewals/telecalling/leads?mode=FollowUpToday&assigned_user_id={admin_user.UserId}",
        headers=admin_headers,
    )
    assert res_q.status_code == 200
    assert any(item["calling_import_id"] == lead_id for item in res_q.json())

    # 4. Field Executive GPS Check-In with (0.0, 0.0) -> "No Address Found" rule (Clerk/Location.aspx.cs)
    res_zero_geo = await async_client.post(
        "/api/v1/integrations/geo/check-in",
        json={
            "customer_id": 10,
            "latitude": "0.0",
            "longitude": "0.0",
            "visit_note": "GPS signal unavailable indoors",
        },
        headers=admin_headers,
    )
    assert res_zero_geo.status_code == 201, res_zero_geo.text
    assert res_zero_geo.json()["resolved_address"] == "No Address Found"
    assert res_zero_geo.json()["geocode_source"] == "ZERO_COORDINATE_RULE"

    # 5. Field Executive GPS Check-In with real coordinates
    res_geo = await async_client.post(
        "/api/v1/integrations/geo/check-in",
        json={
            "calling_import_id": lead_id,
            "latitude": "18.5204",
            "longitude": "73.8567",
            "visit_note": "Met customer at Pune office",
        },
        headers=admin_headers,
    )
    assert res_geo.status_code == 201, res_geo.text
    assert "18.5204" in res_geo.json()["resolved_address"]


# ==============================================================================
# 10. F-17B-094: Multi-Insurer Quotation Request PDF File Sharing
# ==============================================================================
@pytest.mark.asyncio
async def test_f17b_094_requested_quotation_files_workflow(
    async_client: AsyncClient, db_session: AsyncSession
):
    _, admin_headers = await create_user_with_role(db_session, "ADMIN")

    q_req = AppQuotationRequest(
        QuatationDate=datetime.utcnow(),
        InsuranceCompanyId="1,2",
        AgentId=1,
        ProductType="MOTOR",
        VehicleNo="MH12QF1111",
        Camera="",
        LocationHeadId=1,
        ReadStatus=0,
        Note="",
        isdeleted=0,
        FranchiseId=0,
    )
    db_session.add(q_req)
    await db_session.commit()
    await db_session.refresh(q_req)

    # Attach 2 insurer quotation PDF files
    for comp_id, fname in [(1, "icici_quote_1111.pdf"), (2, "hdfc_quote_1111.pdf")]:
        res_att = await async_client.post(
            f"/api/v1/quotations/requests/{q_req.QuatationId}/requested-files",
            json={"insurance_company_id": comp_id, "file_name": fname},
            headers=admin_headers,
        )
        assert res_att.status_code == 201, res_att.text

    res_list = await async_client.get(
        f"/api/v1/quotations/requests/{q_req.QuatationId}/requested-files",
        headers=admin_headers,
    )
    assert res_list.status_code == 200, res_list.text
    files = res_list.json()
    assert len(files) == 2
    assert {f["file_name"] for f in files} == {"icici_quote_1111.pdf", "hdfc_quote_1111.pdf"}


# ==============================================================================
# 11. F-17B-089, F-17B-095, F-17B-096, F-17B-097: Attestr RC, Cashbacks, Targets & Sub-Agents
# ==============================================================================
@pytest.mark.asyncio
async def test_f17b_089_095_096_097_attestr_cashback_targets_and_sub_agents(
    async_client: AsyncClient, db_session: AsyncSession, monkeypatch
):
    _, admin_headers = await create_user_with_role(db_session, "ADMIN")

    # --- F-17B-089: Multi-Provider RC listing & AttestrRCProvider unit/adapter verification ---
    res_prov = await async_client.get(
        "/api/v1/integrations/vehicle-rc/providers",
        headers=admin_headers,
    )
    assert res_prov.status_code == 200
    prov_ids = {p["id"] for p in res_prov.json()["available_providers"]}
    assert {"mock", "apiclub", "signzy", "attestr"}.issubset(prov_ids)

    # Verify AttestrRCProvider parsing with mocked httpx response
    class DummyResp:
        status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            return {
                "uuid": "attestr-req-001",
                "data": {
                    "valid": True,
                    "owner": "ROHIT PATIL",
                    "father": "SURESH PATIL",
                    "financed": True,
                    "financier": "HDFC BANK LTD",
                    "insurer": "BAJAJ ALLIANZ",
                    "policyNumber": "BAJ-998877",
                    "insuranceUpto": "2027-05-15",
                    "registered": "2022-05-16",
                    "chassis": "CHASSIS778899",
                    "engine": "ENG778899",
                    "fuelType": "DIESEL",
                    "makerDescription": "TATA MOTORS",
                    "makerModel": "HARRIER XZ",
                    "status": "ACTIVE",
                },
            }

    async def fake_post(self, url, json=None, headers=None):
        return DummyResp()

    monkeypatch.setattr("httpx.AsyncClient.post", fake_post)
    attestr_adapter = AttestrRCProvider(base_url="https://mock.attestr.local/rc", api_key="test-key")
    rc_data = await attestr_adapter.lookup_rc("MH-12-AT-9999")
    monkeypatch.undo()
    assert rc_data is not None
    assert rc_data.license_plate_RegNo == "MH12AT9999"
    assert rc_data.owner_name == "ROHIT PATIL"
    assert rc_data.is_financed == "YES"
    assert rc_data.CreatedBy == "ATTESTR_PROVIDER"

    # --- F-17B-095: Promotional Cashback Entry ---
    res_cb = await async_client.post(
        "/api/v1/commissions/cashbacks",
        json={
            "transaction_id": 555,
            "customer_id": 12,
            "agent_id": 7,
            "cashback_amount": "750.00",
            "trans_date": "2026-10-08",
            "narration": "Diwali motor policy cashback scheme",
        },
        headers=admin_headers,
    )
    assert res_cb.status_code == 201, res_cb.text
    assert Decimal(str(res_cb.json()["cashback_amount"])) == Decimal("750.00")

    # --- F-17B-096: Sales Target CRUD & Contest Tier Calculation ---
    res_tgt = await async_client.post(
        "/api/v1/reports/targets",
        json={
            "emp_id": 21,
            "financial_year": "2026-2027",
            "month": "October",
            "target_amount": "200000.00",
            "achieved_target_amount": "160000.00",
            "health_insurance_amount": "40000.00",
            "annual_amount": "2400000.00",
        },
        headers=admin_headers,
    )
    assert res_tgt.status_code == 201, res_tgt.text
    t_id = res_tgt.json()["target_id"]
    assert Decimal(str(res_tgt.json()["achievement_percent"])) == Decimal("80.00")
    assert res_tgt.json()["contest_reward_tier"] == "SILVER_QUALIFIER"

    res_tgt_up = await async_client.put(
        f"/api/v1/reports/targets/{t_id}",
        json={"achieved_target_amount": "260000.00"},
        headers=admin_headers,
    )
    assert res_tgt_up.status_code == 200, res_tgt_up.text
    assert Decimal(str(res_tgt_up.json()["achievement_percent"])) == Decimal("130.00")
    assert res_tgt_up.json()["contest_reward_tier"] == "PLATINUM_CHAMPION"

    # --- F-17B-097: Sub-Agent Secondary Hierarchy & Split Payout ---
    parent_agent = Agent(
        AgentCode="AGT-PARENT-01",
        AgentFName="Prakash",
        AgentLName="Joshi",
        MobileNo="9811122233",
        BranchId=1,
        IsActive=1,
        kyc_status="VERIFIED",
        isdeleted="0",
    )
    db_session.add(parent_agent)
    await db_session.commit()
    await db_session.refresh(parent_agent)

    res_sub = await async_client.post(
        f"/api/v1/agents/{parent_agent.AgentId}/sub-agents",
        json={
            "agent_code": "SUB-AGT-001",
            "agent_first_name": "Nilesh",
            "agent_last_name": "Joshi",
            "mobile_no": "9822233344",
            "split_percent": "60.00",
        },
        headers=admin_headers,
    )
    assert res_sub.status_code == 201, res_sub.text
    sub_id = res_sub.json()["sub_agent_id"]

    res_split = await async_client.post(
        f"/api/v1/agents/{parent_agent.AgentId}/sub-agents/calculate-split",
        json={
            "sub_agent_id": sub_id,
            "total_commission_amount": "5000.00",
        },
        headers=admin_headers,
    )
    assert res_split.status_code == 200, res_split.text
    sp = res_split.json()
    assert Decimal(str(sp["sub_agent_payout_amount"])) == Decimal("3000.00")
    assert Decimal(str(sp["parent_agent_retained_amount"])) == Decimal("2000.00")


# ==============================================================================
# 12. Security & Validation Guards (401 Unauthenticated & 422 Schema Validation)
# ==============================================================================
@pytest.mark.asyncio
async def test_phase18a_unauthenticated_and_validation_guards(
    async_client: AsyncClient, db_session: AsyncSession
):
    # Unauthenticated requests must return 401
    for path in [
        "/api/v1/batch-tasks/operator-lock-status",
        "/api/v1/commission-payouts/ideal-payment-receipts",
        "/api/v1/commissions/grids/lookup",
        "/api/v1/payments/remaining-cash",
        "/api/v1/accounting/sales-registrations",
        "/api/v1/inspections",
        "/api/v1/admin/support-tickets",
        "/api/v1/renewals/telecalling/leads",
        "/api/v1/integrations/geo/check-ins",
    ]:
        res = await async_client.get(path)
        assert res.status_code == 401, f"Expected 401 on {path}, got {res.status_code}"

    # Authenticated 422 validation checks (extra='forbid' and business constraints)
    _, admin_headers = await create_user_with_role(db_session, "ADMIN")
    res_extra = await async_client.post(
        "/api/v1/commissions/capping/reliance-evaluate",
        json={
            "grid_percent": "20.00",
            "od_discount_percent": "50.00",
            "unexpected_field": "rejected",
        },
        headers=admin_headers,
    )
    assert res_extra.status_code == 422

    # Paid premium > total premium must return 422
    res_overpaid = await async_client.post(
        "/api/v1/payments/remaining-cash",
        json={
            "transaction_ids": [1],
            "total_premium": "5000.00",
            "paid_premium": "6000.00",
        },
        headers=admin_headers,
    )
    assert res_overpaid.status_code == 422


# ==============================================================================
# 13. Phase 18C FIND-18B-002: Support Ticket Remarks Ownership & IDOR Hardening
# ==============================================================================
@pytest.mark.asyncio
async def test_p18c_find_18b_002_support_ticket_remarks_idor_and_ownership_hardening(
    async_client: AsyncClient, db_session: AsyncSession
):
    owner_agent, owner_headers = await create_user_with_role(db_session, "AGENT", branch_id=1)
    _, other_agent_headers = await create_user_with_role(db_session, "AGENT", branch_id=1)
    _, hr_headers = await create_user_with_role(db_session, "HR", branch_id=1)
    _, op_branch1_headers = await create_user_with_role(db_session, "OPERATOR", branch_id=1)
    _, op_branch2_headers = await create_user_with_role(db_session, "OPERATOR", branch_id=2)
    _, it_branch2_headers = await create_user_with_role(db_session, "IT SUPPORT", branch_id=2)
    _, admin_branch2_headers = await create_user_with_role(db_session, "ADMIN", branch_id=2)

    # 1. Owner Agent creates ticket in Branch 1
    res_create = await async_client.post(
        "/api/v1/admin/support-tickets",
        json={
            "support_type_id": 1,
            "support_type": "IT_TECHNICAL",
            "remark": "Portal login OTP issue",
        },
        headers=owner_headers,
    )
    assert res_create.status_code == 201, res_create.text
    support_id = res_create.json()["support_id"]
    assert res_create.json()["user_id"] == owner_agent.UserId

    # 2. Unauthorized user (unauthenticated) -> 401
    res_unauth = await async_client.post(
        f"/api/v1/admin/support-tickets/{support_id}/remarks",
        json={"remark": "Unauth attempt", "remark_from": "USER"},
    )
    assert res_unauth.status_code == 401

    # 3. Valid authorized access: ticket owner adds follow-up remark -> 200
    res_owner = await async_client.post(
        f"/api/v1/admin/support-tickets/{support_id}/remarks",
        json={"remark": "Attaching screenshot reference", "remark_from": "USER"},
        headers=owner_headers,
    )
    assert res_owner.status_code == 200, res_owner.text

    # 4. Valid authorized access: same-branch back-office Operator adds remark -> 200
    res_op1 = await async_client.post(
        f"/api/v1/admin/support-tickets/{support_id}/remarks",
        json={"remark": "Checked by branch operator", "remark_from": "OPTR"},
        headers=op_branch1_headers,
    )
    assert res_op1.status_code == 200, res_op1.text

    # 5. Wrong owner / wrong agent / unauthorized role -> 403
    res_other_agent = await async_client.post(
        f"/api/v1/admin/support-tickets/{support_id}/remarks",
        json={"remark": "Cross-agent IDOR attempt", "remark_from": "USER"},
        headers=other_agent_headers,
    )
    assert res_other_agent.status_code == 403

    res_hr = await async_client.post(
        f"/api/v1/admin/support-tickets/{support_id}/remarks",
        json={"remark": "HR cross-user attempt", "remark_from": "USER"},
        headers=hr_headers,
    )
    assert res_hr.status_code == 403

    # 6. Wrong branch: Operator from Branch 2 on Branch 1 ticket -> 403
    res_op2 = await async_client.post(
        f"/api/v1/admin/support-tickets/{support_id}/remarks",
        json={"remark": "Cross-branch operator attempt", "remark_from": "OPTR"},
        headers=op_branch2_headers,
    )
    assert res_op2.status_code == 403

    # 7. Invalid object ID (0) -> 422 & non-existent object ID (999999) -> 404
    res_invalid_id = await async_client.post(
        "/api/v1/admin/support-tickets/0/remarks",
        json={"remark": "Invalid ID", "remark_from": "IT"},
        headers=admin_branch2_headers,
    )
    assert res_invalid_id.status_code == 422

    res_missing = await async_client.post(
        "/api/v1/admin/support-tickets/999999/remarks",
        json={"remark": "Missing ID", "remark_from": "IT"},
        headers=admin_branch2_headers,
    )
    assert res_missing.status_code == 404

    # 8. Privileged authorized access: cross-branch IT SUPPORT and ADMIN -> 200
    res_it = await async_client.post(
        f"/api/v1/admin/support-tickets/{support_id}/remarks",
        json={"remark": "Resolved by central IT support", "remark_from": "IT"},
        headers=it_branch2_headers,
    )
    assert res_it.status_code == 200, res_it.text

    res_adm = await async_client.post(
        f"/api/v1/admin/support-tickets/{support_id}/remarks",
        json={"remark": "Verified by Admin", "remark_from": "ADMIN"},
        headers=admin_branch2_headers,
    )
    assert res_adm.status_code == 200, res_adm.text
    assert len(res_adm.json()["remarks_thread"]) == 5


# ==============================================================================
# 14. Phase 18C FIND-18B-002: Quotation Requested Files Ownership & IDOR Hardening
# ==============================================================================
@pytest.mark.asyncio
async def test_p18c_find_18b_002_quotation_requested_files_idor_and_ownership_hardening(
    async_client: AsyncClient, db_session: AsyncSession
):
    owner_user, owner_headers = await create_user_with_role(db_session, "AGENT", branch_id=1)
    other_agent_user, other_agent_headers = await create_user_with_role(
        db_session, "AGENT", branch_id=1
    )
    _, sales_other_headers = await create_user_with_role(db_session, "SALES", branch_id=1)
    _, fran_other_headers = await create_user_with_role(db_session, "FRANCHISE", branch_id=1)
    _, pv_headers = await create_user_with_role(db_session, "pOLICY VIEW", branch_id=1)
    _, coord_b1_headers = await create_user_with_role(
        db_session, "QUOT CO-ORDINATOR", branch_id=1
    )
    _, coord_b2_headers = await create_user_with_role(
        db_session, "QUOT CO-ORDINATOR", branch_id=2
    )
    _, admin_b2_headers = await create_user_with_role(db_session, "ADMIN", branch_id=2)

    owner_agent_profile = Agent(
        AgentCode="AGT-QRF-OWNER-01",
        AgentFName="Kiran",
        AgentLName="More",
        MobileNo="9810011111",
        BranchId=1,
        UserId=owner_user.UserId,
        IsActive=1,
        kyc_status="VERIFIED",
        isdeleted="0",
    )
    other_agent_profile = Agent(
        AgentCode="AGT-QRF-OTHER-02",
        AgentFName="Ramesh",
        AgentLName="Pawar",
        MobileNo="9810022222",
        BranchId=1,
        UserId=other_agent_user.UserId,
        IsActive=1,
        kyc_status="VERIFIED",
        isdeleted="0",
    )
    db_session.add_all([owner_agent_profile, other_agent_profile])
    await db_session.flush()
    owner_user.partner_user_id = str(owner_agent_profile.AgentId)
    other_agent_user.partner_user_id = str(other_agent_profile.AgentId)

    q_req = AppQuotationRequest(
        QuatationDate=datetime.utcnow(),
        InsuranceCompanyId="1,2",
        AgentId=owner_agent_profile.AgentId,
        SalesEx_Id=777,
        LocationHeadId=888,
        FranchiseId=999,
        ProductType="MOTOR",
        VehicleNo="MH12IDOR01",
        Camera="",
        ReadStatus=0,
        Note="",
        isdeleted=0,
    )
    db_session.add(q_req)
    await db_session.commit()
    await db_session.refresh(q_req)
    qid = q_req.QuatationId

    # 1. Unauthenticated -> 401 on POST and GET
    assert (
        await async_client.post(
            f"/api/v1/quotations/requests/{qid}/requested-files",
            json={"insurance_company_id": 1, "file_name": "unauth.pdf"},
        )
    ).status_code == 401
    assert (
        await async_client.get(f"/api/v1/quotations/requests/{qid}/requested-files")
    ).status_code == 401

    # 2. Valid authorized access: owning Agent attaches and lists files -> 201 / 200
    res_owner_post = await async_client.post(
        f"/api/v1/quotations/requests/{qid}/requested-files",
        json={"insurance_company_id": 1, "file_name": "owner_quote.pdf"},
        headers=owner_headers,
    )
    assert res_owner_post.status_code == 201, res_owner_post.text

    res_owner_get = await async_client.get(
        f"/api/v1/quotations/requests/{qid}/requested-files",
        headers=owner_headers,
    )
    assert res_owner_get.status_code == 200, res_owner_get.text
    assert len(res_owner_get.json()) == 1

    # 3. Valid authorized access: same-branch Quotation Coordinator -> 201 / 200
    res_coord_post = await async_client.post(
        f"/api/v1/quotations/requests/{qid}/requested-files",
        json={"insurance_company_id": 2, "file_name": "coord_quote.pdf"},
        headers=coord_b1_headers,
    )
    assert res_coord_post.status_code == 201, res_coord_post.text

    res_coord_get = await async_client.get(
        f"/api/v1/quotations/requests/{qid}/requested-files",
        headers=coord_b1_headers,
    )
    assert res_coord_get.status_code == 200

    # 4. Unauthorized role for write (pOLICY VIEW) -> 403
    res_pv_post = await async_client.post(
        f"/api/v1/quotations/requests/{qid}/requested-files",
        json={"insurance_company_id": 1, "file_name": "pv_quote.pdf"},
        headers=pv_headers,
    )
    assert res_pv_post.status_code == 403

    # 5. Wrong owner / wrong agent / wrong sales exec / wrong franchise -> 403 on POST and GET
    for bad_headers in [other_agent_headers, sales_other_headers, fran_other_headers]:
        res_bad_post = await async_client.post(
            f"/api/v1/quotations/requests/{qid}/requested-files",
            json={"insurance_company_id": 3, "file_name": "idor_attempt.pdf"},
            headers=bad_headers,
        )
        assert res_bad_post.status_code == 403

        res_bad_get = await async_client.get(
            f"/api/v1/quotations/requests/{qid}/requested-files",
            headers=bad_headers,
        )
        assert res_bad_get.status_code == 403

    # 6. Wrong branch: Coordinator from Branch 2 on Branch 1 quotation request -> 403
    res_b2_post = await async_client.post(
        f"/api/v1/quotations/requests/{qid}/requested-files",
        json={"insurance_company_id": 4, "file_name": "cross_branch.pdf"},
        headers=coord_b2_headers,
    )
    assert res_b2_post.status_code == 403

    res_b2_get = await async_client.get(
        f"/api/v1/quotations/requests/{qid}/requested-files",
        headers=coord_b2_headers,
    )
    assert res_b2_get.status_code == 403

    # 7. Invalid object ID (0) -> 422 & non-existent object ID (999999) -> 404
    assert (
        await async_client.post(
            "/api/v1/quotations/requests/0/requested-files",
            json={"insurance_company_id": 1, "file_name": "zero.pdf"},
            headers=admin_b2_headers,
        )
    ).status_code == 422
    assert (
        await async_client.get(
            "/api/v1/quotations/requests/0/requested-files",
            headers=admin_b2_headers,
        )
    ).status_code == 422

    assert (
        await async_client.post(
            "/api/v1/quotations/requests/999999/requested-files",
            json={"insurance_company_id": 1, "file_name": "missing.pdf"},
            headers=admin_b2_headers,
        )
    ).status_code == 404
    assert (
        await async_client.get(
            "/api/v1/quotations/requests/999999/requested-files",
            headers=admin_b2_headers,
        )
    ).status_code == 404

    # 8. Privileged authorized access: cross-branch ADMIN -> 201 / 200
    res_adm_post = await async_client.post(
        f"/api/v1/quotations/requests/{qid}/requested-files",
        json={"insurance_company_id": 5, "file_name": "admin_override.pdf"},
        headers=admin_b2_headers,
    )
    assert res_adm_post.status_code == 201, res_adm_post.text

    res_adm_get = await async_client.get(
        f"/api/v1/quotations/requests/{qid}/requested-files",
        headers=admin_b2_headers,
    )
    assert res_adm_get.status_code == 200
    assert len(res_adm_get.json()) == 3


# ==============================================================================
# 15. Phase 18C FIND-18B-002: Sub-Agent Hierarchy Ownership & IDOR Hardening
# ==============================================================================
@pytest.mark.asyncio
async def test_p18c_find_18b_002_sub_agents_idor_and_ownership_hardening(
    async_client: AsyncClient, db_session: AsyncSession
):
    owner_user, owner_headers = await create_user_with_role(db_session, "AGENT", branch_id=1)
    other_agent_user, other_agent_headers = await create_user_with_role(
        db_session, "AGENT", branch_id=1
    )
    _, sales_other_headers = await create_user_with_role(db_session, "SALES", branch_id=1)
    _, fran_other_headers = await create_user_with_role(db_session, "FRANCHISE", branch_id=1)
    _, pv_headers = await create_user_with_role(db_session, "pOLICY VIEW", branch_id=1)
    _, op_b2_headers = await create_user_with_role(db_session, "OPERATOR", branch_id=2)
    _, admin_b2_headers = await create_user_with_role(db_session, "ADMIN", branch_id=2)

    parent_agent = Agent(
        AgentCode="AGT-SUB-PARENT-01",
        AgentFName="Sandeep",
        AgentLName="Kulkarni",
        MobileNo="9823011111",
        BranchId=1,
        UserId=owner_user.UserId,
        SalesExecutiveId=701,
        FranchiseId=801,
        IsActive=1,
        kyc_status="VERIFIED",
        isdeleted="0",
    )
    other_agent = Agent(
        AgentCode="AGT-SUB-OTHER-02",
        AgentFName="Mahesh",
        AgentLName="Shinde",
        MobileNo="9823022222",
        BranchId=1,
        UserId=other_agent_user.UserId,
        IsActive=1,
        kyc_status="VERIFIED",
        isdeleted="0",
    )
    db_session.add_all([parent_agent, other_agent])
    await db_session.flush()
    owner_user.partner_user_id = str(parent_agent.AgentId)
    other_agent_user.partner_user_id = str(other_agent.AgentId)
    await db_session.commit()
    await db_session.refresh(parent_agent)
    pid = parent_agent.AgentId

    # 1. Unauthenticated -> 401
    assert (
        await async_client.post(
            f"/api/v1/agents/{pid}/sub-agents",
            json={
                "agent_code": "SUB-UNAUTH",
                "agent_first_name": "No",
                "mobile_no": "9000000001",
                "split_percent": "50.00",
            },
        )
    ).status_code == 401
    assert (await async_client.get(f"/api/v1/agents/{pid}/sub-agents")).status_code == 401
    assert (
        await async_client.post(
            f"/api/v1/agents/{pid}/sub-agents/calculate-split",
            json={"sub_agent_id": 1, "total_commission_amount": "1000.00"},
        )
    ).status_code == 401

    # 2. Valid authorized access: owning parent Agent creates, lists, and calculates split -> 201 / 200
    res_create = await async_client.post(
        f"/api/v1/agents/{pid}/sub-agents",
        json={
            "agent_code": "SUB-OWN-001",
            "agent_first_name": "Amit",
            "agent_last_name": "Kulkarni",
            "mobile_no": "9823099991",
            "split_percent": "40.00",
        },
        headers=owner_headers,
    )
    assert res_create.status_code == 201, res_create.text
    sub_id = res_create.json()["sub_agent_id"]

    res_list = await async_client.get(
        f"/api/v1/agents/{pid}/sub-agents",
        headers=owner_headers,
    )
    assert res_list.status_code == 200, res_list.text
    assert len(res_list.json()) == 1

    res_calc = await async_client.post(
        f"/api/v1/agents/{pid}/sub-agents/calculate-split",
        json={"sub_agent_id": sub_id, "total_commission_amount": "2000.00"},
        headers=owner_headers,
    )
    assert res_calc.status_code == 200, res_calc.text
    assert Decimal(str(res_calc.json()["sub_agent_payout_amount"])) == Decimal("800.00")

    # 3. Unauthorized role for write (pOLICY VIEW) -> 403
    res_pv_create = await async_client.post(
        f"/api/v1/agents/{pid}/sub-agents",
        json={
            "agent_code": "SUB-PV-001",
            "agent_first_name": "PV",
            "mobile_no": "9823099992",
            "split_percent": "25.00",
        },
        headers=pv_headers,
    )
    assert res_pv_create.status_code == 403

    # 4. Wrong owner / wrong agent / wrong sales exec / wrong franchise -> 403
    for bad_headers in [other_agent_headers, sales_other_headers, fran_other_headers]:
        assert (
            await async_client.post(
                f"/api/v1/agents/{pid}/sub-agents",
                json={
                    "agent_code": "SUB-IDOR-001",
                    "agent_first_name": "Bad",
                    "mobile_no": "9823099993",
                    "split_percent": "50.00",
                },
                headers=bad_headers,
            )
        ).status_code == 403

        assert (
            await async_client.get(
                f"/api/v1/agents/{pid}/sub-agents",
                headers=bad_headers,
            )
        ).status_code == 403

        assert (
            await async_client.post(
                f"/api/v1/agents/{pid}/sub-agents/calculate-split",
                json={"sub_agent_id": sub_id, "total_commission_amount": "2000.00"},
                headers=bad_headers,
            )
        ).status_code == 403

    # 5. Wrong branch: Operator from Branch 2 on Branch 1 parent agent -> 403
    assert (
        await async_client.post(
            f"/api/v1/agents/{pid}/sub-agents",
            json={
                "agent_code": "SUB-B2-001",
                "agent_first_name": "BranchTwo",
                "mobile_no": "9823099994",
                "split_percent": "30.00",
            },
            headers=op_b2_headers,
        )
    ).status_code == 403
    assert (
        await async_client.get(f"/api/v1/agents/{pid}/sub-agents", headers=op_b2_headers)
    ).status_code == 403
    assert (
        await async_client.post(
            f"/api/v1/agents/{pid}/sub-agents/calculate-split",
            json={"sub_agent_id": sub_id, "total_commission_amount": "2000.00"},
            headers=op_b2_headers,
        )
    ).status_code == 403

    # 6. Invalid object ID (0) -> 422 & non-existent object ID (999999) -> 404
    assert (
        await async_client.get("/api/v1/agents/0/sub-agents", headers=admin_b2_headers)
    ).status_code == 422
    assert (
        await async_client.get("/api/v1/agents/999999/sub-agents", headers=admin_b2_headers)
    ).status_code == 404
    assert (
        await async_client.post(
            "/api/v1/agents/999999/sub-agents",
            json={
                "agent_code": "SUB-MISSING",
                "agent_first_name": "Missing",
                "mobile_no": "9823099995",
                "split_percent": "20.00",
            },
            headers=admin_b2_headers,
        )
    ).status_code == 404
    assert (
        await async_client.post(
            "/api/v1/agents/999999/sub-agents/calculate-split",
            json={"sub_agent_id": sub_id, "total_commission_amount": "2000.00"},
            headers=admin_b2_headers,
        )
    ).status_code == 404

    # 7. Privileged authorized access: cross-branch ADMIN -> 201 / 200
    res_adm_create = await async_client.post(
        f"/api/v1/agents/{pid}/sub-agents",
        json={
            "agent_code": "SUB-ADM-002",
            "agent_first_name": "AdminCreated",
            "mobile_no": "9823099996",
            "split_percent": "50.00",
        },
        headers=admin_b2_headers,
    )
    assert res_adm_create.status_code == 201, res_adm_create.text

    res_adm_list = await async_client.get(
        f"/api/v1/agents/{pid}/sub-agents",
        headers=admin_b2_headers,
    )
    assert res_adm_list.status_code == 200
    assert len(res_adm_list.json()) == 2
