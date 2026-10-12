"""
Phase 22 Integration Test Suite — Sales Executive & Location Head Commission Hierarchy,
Insurer Partner Portals Registry, and App Billing & Field Reimbursement Claims.
"""
from datetime import date, datetime, timedelta
from decimal import Decimal
import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from tests.integration.test_phase7_policy_booking_api import create_user_with_role


@pytest.fixture(autouse=True)
async def cleanup_phase22_tables(db_session: AsyncSession):
    """Purge synthetic Phase 22 tables before and after each test."""
    tables = [
        "tbl_appbillingattachment",
        "tbl_appbillingdetails",
        "tbl_insurancecompanyportal",
        "tbl_locationheadsalesexmap",
        "tbl_locationheadcommission",
        "tbl_salesexcommission",
    ]
    for tbl in tables:
        await db_session.execute(text(f"DELETE FROM {tbl};"))
    await db_session.commit()
    yield
    for tbl in tables:
        await db_session.execute(text(f"DELETE FROM {tbl};"))
    await db_session.commit()


# ==============================================================================
# 1. Sales Executive Commission Matrix & RBAC
# ==============================================================================

@pytest.mark.asyncio
async def test_sales_ex_commission_crud_and_rbac(
    async_client: AsyncClient, db_session: AsyncSession
):
    _, admin_headers = await create_user_with_role(db_session, "ADMIN")
    _, agent_headers = await create_user_with_role(db_session, "AGENT")
    _, sales_headers = await create_user_with_role(db_session, "SALES EXECUTIVE")

    payload = {
        "SalesEx_Id": 101,
        "InsuranceCompanyId": 1,
        "PolicyType": "Comprehensive",
        "ProductType": "Private Car",
        "VehiTypeId": 1,
        "FuelTypeId": 1,
        "Commission": "15.00",
        "Commission_OD": "10.00",
        "Commission_Net": "12.50",
        "CommissionCalculateOn": "-",
        "ReferenceType": "Self",
        "FlatRate": "No",
        "OD_Discount": "0.00",
        "FranchiseCode": "RA",
        "ncb": 20,
        "CCRange": "1000-1500",
        "Slab": "A",
        "ND": "Yes",
        "MakeId": 1,
        "ModelId": 2,
        "RtoId": 10,
        "StateId": 27,
        "ValidFromDate": str(date.today()),
        "ValidToDate": str(date.today() + timedelta(days=365)),
        "IsActive": 1,
    }

    # 1. Non-admin forbidden to create grid
    forbidden_resp = await async_client.post(
        "/api/v1/commissions/sales-executives/grids",
        json=payload,
        headers=agent_headers,
    )
    assert forbidden_resp.status_code == 403

    # 2. Admin creates grid entry
    create_resp = await async_client.post(
        "/api/v1/commissions/sales-executives/grids",
        json=payload,
        headers=admin_headers,
    )
    assert create_resp.status_code == 201
    created_data = create_resp.json()
    grid_id = created_data["SalesCommissionId"]
    assert created_data["SalesEx_Id"] == 101
    assert Decimal(created_data["Commission"]) == Decimal("15.00")

    # 3. Duplicate creation rejected with 409
    dup_resp = await async_client.post(
        "/api/v1/commissions/sales-executives/grids",
        json=payload,
        headers=admin_headers,
    )
    assert dup_resp.status_code == 409

    # 4. Negative rate rejected with 400
    bad_payload = payload.copy()
    bad_payload["Commission"] = "-5.00"
    bad_resp = await async_client.post(
        "/api/v1/commissions/sales-executives/grids",
        json=bad_payload,
        headers=admin_headers,
    )
    assert bad_resp.status_code == 400

    # 5. Sales Executive lists grids
    list_resp = await async_client.get(
        "/api/v1/commissions/sales-executives/grids?sales_ex_id=101",
        headers=sales_headers,
    )
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1

    # 6. Get single grid
    get_resp = await async_client.get(
        f"/api/v1/commissions/sales-executives/grids/{grid_id}",
        headers=sales_headers,
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["SalesCommissionId"] == grid_id

    # 7. Update grid
    upd_resp = await async_client.put(
        f"/api/v1/commissions/sales-executives/grids/{grid_id}",
        json={"Commission": "18.50", "Commission_Net": "14.00"},
        headers=admin_headers,
    )
    assert upd_resp.status_code == 200
    assert Decimal(upd_resp.json()["Commission"]) == Decimal("18.50")

    # 8. Soft delete grid
    del_resp = await async_client.delete(
        f"/api/v1/commissions/sales-executives/grids/{grid_id}",
        headers=admin_headers,
    )
    assert del_resp.status_code == 200
    assert del_resp.json()["IsActive"] == 0


# ==============================================================================
# 2. Sales Executive Commission Matching & Lookup
# ==============================================================================

@pytest.mark.asyncio
async def test_sales_ex_commission_lookup_priority(
    async_client: AsyncClient, db_session: AsyncSession
):
    _, admin_headers = await create_user_with_role(db_session, "ADMIN")
    _, sales_headers = await create_user_with_role(db_session, "SALES EXECUTIVE")

    # Insert two grids: standard RA grid and special ST broker grid
    grid_ra = {
        "SalesEx_Id": 202,
        "InsuranceCompanyId": 2,
        "PolicyType": "Comprehensive",
        "ProductType": "Two Wheeler",
        "VehiTypeId": 2,
        "FuelTypeId": 1,
        "Commission": "10.00",
        "Commission_OD": "8.00",
        "Commission_Net": "9.00",
        "FranchiseCode": "RA",
        "ValidFromDate": str(date.today() - timedelta(days=30)),
        "IsActive": 1,
    }
    grid_st = {
        "SalesEx_Id": 202,
        "InsuranceCompanyId": 2,
        "PolicyType": "Comprehensive",
        "ProductType": "Two Wheeler",
        "VehiTypeId": 2,
        "FuelTypeId": 1,
        "Commission": "14.00",
        "Commission_OD": "11.00",
        "Commission_Net": "12.00",
        "FranchiseCode": "ST",
        "ValidFromDate": str(date.today() - timedelta(days=30)),
        "IsActive": 1,
    }

    r1 = await async_client.post(
        "/api/v1/commissions/sales-executives/grids", json=grid_ra, headers=admin_headers
    )
    assert r1.status_code == 201

    r2 = await async_client.post(
        "/api/v1/commissions/sales-executives/grids", json=grid_st, headers=admin_headers
    )
    assert r2.status_code == 201

    # Lookup RA grid
    lookup_ra = await async_client.post(
        "/api/v1/commissions/sales-executives/lookup",
        json={
            "SalesEx_Id": 202,
            "InsuranceCompanyId": 2,
            "FranchiseCode": "RA",
            "VehiTypeId": 2,
            "FuelTypeId": 1,
        },
        headers=sales_headers,
    )
    assert lookup_ra.status_code == 200
    data_ra = lookup_ra.json()
    assert data_ra["matched"] is True
    assert Decimal(data_ra["Commission"]) == Decimal("10.00")

    # Lookup ST grid
    lookup_st = await async_client.post(
        "/api/v1/commissions/sales-executives/lookup",
        json={
            "SalesEx_Id": 202,
            "InsuranceCompanyId": 2,
            "FranchiseCode": "ST",
            "VehiTypeId": 2,
            "FuelTypeId": 1,
        },
        headers=sales_headers,
    )
    assert lookup_st.status_code == 200
    data_st = lookup_st.json()
    assert data_st["matched"] is True
    assert Decimal(data_st["Commission"]) == Decimal("14.00")

    # Lookup with unmatched sales exec
    lookup_none = await async_client.post(
        "/api/v1/commissions/sales-executives/lookup",
        json={
            "SalesEx_Id": 99999,
            "InsuranceCompanyId": 2,
        },
        headers=sales_headers,
    )
    assert lookup_none.status_code == 200
    assert lookup_none.json()["matched"] is False


# ==============================================================================
# 3. Location Head Commission & Team Hierarchy Assignment
# ==============================================================================

@pytest.mark.asyncio
async def test_location_head_commission_and_assignment_hierarchy(
    async_client: AsyncClient, db_session: AsyncSession
):
    _, admin_headers = await create_user_with_role(db_session, "ADMIN")
    _, sales_headers = await create_user_with_role(db_session, "SALES EXECUTIVE")

    # 1. Create Location Head override grid
    lh_payload = {
        "LocationHeadId": 301,
        "InsuranceCompanyId": 3,
        "PolicyType": "Comprehensive",
        "ProductType": "Commercial Vehicle",
        "VehiTypeId": 3,
        "FuelTypeId": 2,
        "Commission": "5.00",
        "Commission_OD": "3.50",
        "Commission_Net": "4.00",
        "OD_Discount": "0.00",
        "FranchiseCode": "RA",
        "ReferenceType": "L.Head",
        "ValidFromDate": str(date.today()),
        "IsActive": 1,
    }
    lh_resp = await async_client.post(
        "/api/v1/commissions/location-heads/grids",
        json=lh_payload,
        headers=admin_headers,
    )
    assert lh_resp.status_code == 201
    assert lh_resp.json()["LocationHeadId"] == 301

    # 2. Lookup Location Head override rate
    lh_lookup = await async_client.post(
        "/api/v1/commissions/location-heads/lookup",
        json={
            "LocationHeadId": 301,
            "InsuranceCompanyId": 3,
            "FranchiseCode": "RA",
            "VehiTypeId": 3,
        },
        headers=admin_headers,
    )
    assert lh_lookup.status_code == 200
    assert lh_lookup.json()["matched"] is True
    assert Decimal(lh_lookup.json()["Commission"]) == Decimal("5.00")

    # 3. Assign Sales Executives to Location Head
    assign_resp = await async_client.post(
        "/api/v1/commissions/location-heads/assignments",
        json={
            "LocationHeadId": 301,
            "SalesEx_Ids": [501, 502, 503],
        },
        headers=admin_headers,
    )
    assert assign_resp.status_code == 200
    assert len(assign_resp.json()) == 3

    # 4. Query Location Head for Sales Executive 501
    get_lh = await async_client.get(
        "/api/v1/commissions/location-heads/sales-executives/501",
        headers=sales_headers,
    )
    assert get_lh.status_code == 200
    assert get_lh.json()["LocationHeadId"] == 301

    # 5. Query team under Location Head 301
    get_team = await async_client.get(
        "/api/v1/commissions/location-heads/301/team",
        headers=admin_headers,
    )
    assert get_team.status_code == 200
    team_data = get_team.json()
    assert len(team_data) == 3
    assigned_ids = {m["SalesEx_Id"] for m in team_data}
    assert assigned_ids == {501, 502, 503}


# ==============================================================================
# 4. Insurer Partner Portals Registry
# ==============================================================================

@pytest.mark.asyncio
async def test_insurer_portals_registry_lifecycle(
    async_client: AsyncClient, db_session: AsyncSession
):
    _, admin_headers = await create_user_with_role(db_session, "ADMIN")
    _, sales_headers = await create_user_with_role(db_session, "SALES EXECUTIVE")

    portal_payload = {
        "InsuranceCompanyId": 5,
        "PortalId": "HDFC_ERGO_PUN_01",
        "PersonName": "Ramesh Underwriter",
        "BrokerId": 1,
        "PortalUrl": "https://partner.hdfcergo.com/login",
        "PortalPassword": "EncryptedPortalSecret#123",
        "IsActive": 1,
    }

    # 1. Admin creates portal entry
    create_resp = await async_client.post(
        "/api/v1/masters/insurer-portals",
        json=portal_payload,
        headers=admin_headers,
    )
    assert create_resp.status_code == 201
    portal_data = create_resp.json()
    portal_id = portal_data["tbl_Id"]
    assert portal_data["PortalId"] == "HDFC_ERGO_PUN_01"

    # 2. Sales Executive lists portals
    list_resp = await async_client.get(
        "/api/v1/masters/insurer-portals?insurance_company_id=5",
        headers=sales_headers,
    )
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1

    # 3. Get single portal
    get_resp = await async_client.get(
        f"/api/v1/masters/insurer-portals/{portal_id}",
        headers=sales_headers,
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["PersonName"] == "Ramesh Underwriter"

    # 4. Update portal
    upd_resp = await async_client.put(
        f"/api/v1/masters/insurer-portals/{portal_id}",
        json={"PersonName": "Ramesh Senior Underwriter", "PortalId": "HDFC_PUN_LEAD"},
        headers=admin_headers,
    )
    assert upd_resp.status_code == 200
    assert upd_resp.json()["PersonName"] == "Ramesh Senior Underwriter"

    # 5. Soft delete portal
    del_resp = await async_client.delete(
        f"/api/v1/masters/insurer-portals/{portal_id}",
        headers=admin_headers,
    )
    assert del_resp.status_code == 200
    assert del_resp.json()["IsActive"] == 0


# ==============================================================================
# 5. App Billing & Field Reimbursement Claims
# ==============================================================================

@pytest.mark.asyncio
async def test_app_billing_claims_and_reimbursement_workflow(
    async_client: AsyncClient, db_session: AsyncSession
):
    _, admin_headers = await create_user_with_role(db_session, "ADMIN")
    _, sales_headers = await create_user_with_role(db_session, "SALES EXECUTIVE")
    _, finance_headers = await create_user_with_role(db_session, "ACCOUNTANT")

    claim_payload = {
        "SalesExId": 601,
        "FromDate": str(date.today() - timedelta(days=7)),
        "ToDate": str(date.today()),
        "Remark": "Territory travel to Nashik dealership partners",
        "BillingAmount": "4500.00",
        "ReimbursementTypeId": 2,  # Travel & Fuel
        "Destination": "Nashik",
        "attachments": [
            {
                "FileType": "IMG",
                "FilePath": "~/AppBillingImages/BILL_IMG_2026_10_01.jpeg",
                "FileName": "fuel_bill_nashik.jpeg",
            },
            {
                "FileType": "PDF",
                "FilePath": "~/AppBillingPdf/BILL_PDF_2026_10_01.pdf",
                "FileName": "toll_receipts_nashik.pdf",
            },
        ],
    }

    # 1. Invalid date range rejected with 400
    bad_dates = claim_payload.copy()
    bad_dates["FromDate"] = str(date.today())
    bad_dates["ToDate"] = str(date.today() - timedelta(days=1))
    bad_date_resp = await async_client.post(
        "/api/v1/billing/claims", json=bad_dates, headers=sales_headers
    )
    assert bad_date_resp.status_code == 400

    # 2. Negative amount rejected with 400
    bad_amt = claim_payload.copy()
    bad_amt["BillingAmount"] = "-500.00"
    bad_amt_resp = await async_client.post(
        "/api/v1/billing/claims", json=bad_amt, headers=sales_headers
    )
    assert bad_amt_resp.status_code == 400

    # 3. Sales Executive submits claim
    create_resp = await async_client.post(
        "/api/v1/billing/claims", json=claim_payload, headers=sales_headers
    )
    assert create_resp.status_code == 201
    claim_data = create_resp.json()
    billing_id = claim_data["BillingId"]
    assert claim_data["Status"] == "PENDING"
    assert Decimal(claim_data["BillingAmount"]) == Decimal("4500.00")
    assert len(claim_data["attachments"]) == 2

    # 4. List claims
    list_resp = await async_client.get(
        f"/api/v1/billing/claims?sales_ex_id=601",
        headers=sales_headers,
    )
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1

    # 5. Get claim details with attachments
    get_resp = await async_client.get(
        f"/api/v1/billing/claims/{billing_id}",
        headers=sales_headers,
    )
    assert get_resp.status_code == 200
    assert len(get_resp.json()["attachments"]) == 2

    # 6. Finance approves claim
    appr_resp = await async_client.patch(
        f"/api/v1/billing/claims/{billing_id}/status",
        json={"Status": "APPROVED", "Remark": "Approved by Finance Head"},
        headers=finance_headers,
    )
    assert appr_resp.status_code == 200
    assert appr_resp.json()["Status"] == "APPROVED"

    # 7. Finance marks claim as PROCESSED (payment voucher created)
    proc_resp = await async_client.patch(
        f"/api/v1/billing/claims/{billing_id}/status",
        json={"Status": "PROCESSED", "Remark": "Processed via NEFT"},
        headers=finance_headers,
    )
    assert proc_resp.status_code == 200
    assert proc_resp.json()["Status"] == "PROCESSED"
    assert proc_resp.json()["ProcessedDate"] is not None

    # 8. Invalid status update rejected
    inv_status_resp = await async_client.patch(
        f"/api/v1/billing/claims/{billing_id}/status",
        json={"Status": "INVALID_STATE"},
        headers=finance_headers,
    )
    assert inv_status_resp.status_code == 400
