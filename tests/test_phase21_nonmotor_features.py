"""
Phase 21 Integration Test Suite — Non-Motor Commercial Insurance Lines of Business & Operations.
Covers:
1. Product Classes & Commercial Products Catalog (/non-motor/products)
2. Business Types & Required Document Types (/non-motor/products/business-types, document-types)
3. Endorsement Types & Sub-Types (/non-motor/endorsements)
4. Insurer Types, Sub-Types & Detailed Types (/non-motor/commissions)
5. Non-Motor Commission Grids & Calculations Engine (/non-motor/commissions/grids, calculate)
6. Policy Booking, Transaction Processing & Dashboard Summary (/non-motor/policies)
7. Multi-tier RBAC authorization boundaries (Admin, Finance, Coordinator, Agent)
"""
from datetime import date, datetime, timedelta
from decimal import Decimal
import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from tests.integration.test_phase7_policy_booking_api import create_user_with_role


@pytest.fixture(autouse=True)
async def cleanup_phase21_nonmotor_tables(db_session: AsyncSession):
    """Purge synthetic Phase 21 tables before and after each test."""
    tables = [
        "tbl_nonmotortransaction",
        "tbl_nonmotorcommission",
        "tbl_nonmotortypeofinsurancesubtype",
        "tbl_nonmotorinsurancesubtype",
        "tbl_nonmotorinsurancetype",
        "tbl_nonmotorendorsmentsubtype",
        "tbl_nonmotorendorsmenttype",
        "tbl_nonmotordocumenttype",
        "tbl_nonmotorbusinesstype",
        "tbl_nonmotorproduct",
        "tbl_nonmotorclass",
    ]
    for tbl in tables:
        await db_session.execute(text(f"DELETE FROM {tbl};"))
    await db_session.commit()
    yield
    for tbl in tables:
        await db_session.execute(text(f"DELETE FROM {tbl};"))
    await db_session.commit()


# ==============================================================================
# 1. Product Classes & Commercial Products Catalog
# ==============================================================================

@pytest.mark.asyncio
async def test_nonmotor_classes_and_products_lifecycle(
    async_client: AsyncClient, db_session: AsyncSession
):
    _, admin_headers = await create_user_with_role(db_session, "ADMIN")
    _, agent_headers = await create_user_with_role(db_session, "AGENT")

    # 1. Non-admin forbidden to create product class
    f_resp = await async_client.post(
        "/api/v1/non-motor/products/classes",
        headers=agent_headers,
        json={"Class": "Fire Commercial", "IsActive": 1},
    )
    assert f_resp.status_code == 403

    # 2. Admin creates product class
    c_resp = await async_client.post(
        "/api/v1/non-motor/products/classes",
        headers=admin_headers,
        json={"Class": "Fire & Special Perils", "IsActive": 1},
    )
    assert c_resp.status_code == 201
    class_data = c_resp.json()
    class_id = class_data["ClassId"]
    assert class_data["Class"] == "Fire & Special Perils"

    # 3. List classes
    list_resp = await async_client.get("/api/v1/non-motor/products/classes", headers=admin_headers)
    assert list_resp.status_code == 200
    assert any(c["ClassId"] == class_id for c in list_resp.json())

    # 4. Create product under class
    p_resp = await async_client.post(
        "/api/v1/non-motor/products",
        headers=admin_headers,
        json={
            "ClassId": class_id,
            "ProductType": "Standard Fire Policy",
            "ProductCode": "SFSP-01",
            "IsActive": 1,
        },
    )
    assert p_resp.status_code == 201
    prod_data = p_resp.json()
    prod_id = prod_data["NonMotorProductId"]
    assert prod_data["ProductCode"] == "SFSP-01"

    # 5. List products with class filter
    p_list = await async_client.get(
        f"/api/v1/non-motor/products?class_id={class_id}", headers=admin_headers
    )
    assert p_list.status_code == 200
    assert len(p_list.json()) == 1
    assert p_list.json()[0]["NonMotorProductId"] == prod_id


# ==============================================================================
# 2. Business Types & Required Document Types
# ==============================================================================

@pytest.mark.asyncio
async def test_nonmotor_business_and_document_types(
    async_client: AsyncClient, db_session: AsyncSession
):
    _, admin_headers = await create_user_with_role(db_session, "ADMIN")

    # Create business type
    b_resp = await async_client.post(
        "/api/v1/non-motor/products/business-types",
        headers=admin_headers,
        json={"BusinessType": "Commercial New Booking", "IsActive": 1},
    )
    assert b_resp.status_code == 201
    assert b_resp.json()["BusinessType"] == "Commercial New Booking"

    # List business types
    bl_resp = await async_client.get(
        "/api/v1/non-motor/products/business-types", headers=admin_headers
    )
    assert bl_resp.status_code == 200
    assert len(bl_resp.json()) >= 1

    # Create document type
    d_resp = await async_client.post(
        "/api/v1/non-motor/products/document-types",
        headers=admin_headers,
        json={"DocumentType": "Risk Inspection & Valuation Report", "IsActive": 1},
    )
    assert d_resp.status_code == 201
    assert d_resp.json()["DocumentType"] == "Risk Inspection & Valuation Report"

    # List document types
    dl_resp = await async_client.get(
        "/api/v1/non-motor/products/document-types", headers=admin_headers
    )
    assert dl_resp.status_code == 200
    assert len(dl_resp.json()) >= 1


# ==============================================================================
# 3. Endorsement Hierarchies
# ==============================================================================

@pytest.mark.asyncio
async def test_nonmotor_endorsements_hierarchy(
    async_client: AsyncClient, db_session: AsyncSession
):
    _, admin_headers = await create_user_with_role(db_session, "ADMIN")

    # Create endorsement type
    et_resp = await async_client.post(
        "/api/v1/non-motor/endorsements/types",
        headers=admin_headers,
        json={"EndorsementType": "Financial Alteration", "IsActive": 1},
    )
    assert et_resp.status_code == 201
    et_id = et_resp.json()["NonEndorsementId"]

    # Create endorsement sub-type
    est_resp = await async_client.post(
        "/api/v1/non-motor/endorsements/sub-types",
        headers=admin_headers,
        json={
            "NonEndorsementId": et_id,
            "EndorsementSubType": "Sum Insured Revision",
            "IsActive": 1,
        },
    )
    assert est_resp.status_code == 201
    assert est_resp.json()["NonEndorsementId"] == et_id

    # List sub-types filtered by parent
    sub_list = await async_client.get(
        f"/api/v1/non-motor/endorsements/sub-types?endorsement_id={et_id}",
        headers=admin_headers,
    )
    assert sub_list.status_code == 200
    assert len(sub_list.json()) == 1
    assert sub_list.json()[0]["EndorsementSubType"] == "Sum Insured Revision"


# ==============================================================================
# 4. Insurer Types, Sub-Types & Detailed Types
# ==============================================================================

@pytest.mark.asyncio
async def test_nonmotor_insurer_types_and_subtypes(
    async_client: AsyncClient, db_session: AsyncSession
):
    _, admin_headers = await create_user_with_role(db_session, "ADMIN")

    # Create insurance type
    it_resp = await async_client.post(
        "/api/v1/non-motor/commissions/insurance-types",
        headers=admin_headers,
        json={"InsuranceType": "Marine Cargo", "InsuranceCompanyId": 10},
    )
    assert it_resp.status_code == 201
    it_id = it_resp.json()["InsuranceTypeId"]

    # Create insurance sub-type
    ist_resp = await async_client.post(
        "/api/v1/non-motor/commissions/insurance-sub-types",
        headers=admin_headers,
        json={"InsuranceSubType": "Inland Transit Rail/Road", "InsuranceTypeId": it_id},
    )
    assert ist_resp.status_code == 201
    ist_id = ist_resp.json()["InsuranceSubTypeId"]

    # Create detailed type of sub-type
    dt_resp = await async_client.post(
        "/api/v1/non-motor/commissions/types-of-sub-type",
        headers=admin_headers,
        json={
            "TypeOfSubType": "Special Declaration Policy",
            "InsuranceTypeId": it_id,
            "InsuranceSubTypeId": ist_id,
        },
    )
    assert dt_resp.status_code == 201
    assert dt_resp.json()["TypeOfSubType"] == "Special Declaration Policy"


# ==============================================================================
# 5. Commission Grid & Calculation Engine
# ==============================================================================

@pytest.mark.asyncio
async def test_nonmotor_commission_grid_and_calculation(
    async_client: AsyncClient, db_session: AsyncSession
):
    _, admin_headers = await create_user_with_role(db_session, "ADMIN")
    _, finance_headers = await create_user_with_role(db_session, "ACCOUNT")
    agent_user, agent_headers = await create_user_with_role(db_session, "AGENT")

    # 1. Create commission grid row (Finance role)
    grid_resp = await async_client.post(
        "/api/v1/non-motor/commissions/grids",
        headers=finance_headers,
        json={
            "InsuranceCompanyId": 10,
            "InsuranceTypeId": 5,
            "InsuranceSubTypeId": 2,
            "TypeSubTypeId": 0,
            "ReferanceId": agent_user.UserId,
            "ReferenceType": "Agent",
            "Commission": "15.00",
            "CommissionCalculateOn": "NetPremium",
            "ValidFromDate": str(date.today()),
            "IsActive": 1,
        },
    )
    assert grid_resp.status_code == 201
    comm_row = grid_resp.json()
    assert Decimal(str(comm_row["Commission"])) == Decimal("15.00")

    # 2. Query commission grids
    q_resp = await async_client.get(
        f"/api/v1/non-motor/commissions/grids?company_id=10&reference_id={agent_user.UserId}",
        headers=agent_headers,
    )
    assert q_resp.status_code == 200
    assert len(q_resp.json()) >= 1

    # 3. Calculate commission with TDS
    calc_resp = await async_client.post(
        "/api/v1/non-motor/commissions/calculate",
        headers=agent_headers,
        json={
            "NetPremium": "10000.00",
            "InsuranceCompanyId": 10,
            "InsuranceTypeId": 5,
            "InsuranceSubTypeId": 2,
            "ReferanceId": agent_user.UserId,
            "ReferenceType": "Agent",
            "TdsRate": "5.00",
        },
    )
    assert calc_resp.status_code == 200
    calc_data = calc_resp.json()
    assert Decimal(str(calc_data["CommissionRate"])) == Decimal("15.00")
    assert Decimal(str(calc_data["GrossCommission"])) == Decimal("1500.00")  # 15% of 10000
    assert Decimal(str(calc_data["TdsAmount"])) == Decimal("75.00")  # 5% of 1500
    assert Decimal(str(calc_data["NetCommission"])) == Decimal("1425.00")  # 1500 - 75


# ==============================================================================
# 6. Policy Booking, Transaction Processing & Dashboard Summary
# ==============================================================================

@pytest.mark.asyncio
async def test_nonmotor_policy_transaction_booking_and_summary(
    async_client: AsyncClient, db_session: AsyncSession
):
    _, admin_headers = await create_user_with_role(db_session, "ADMIN")
    coord_user, coord_headers = await create_user_with_role(db_session, "OPERATOR")
    agent_user, agent_headers = await create_user_with_role(db_session, "AGENT")

    # Setup class & product
    c_resp = await async_client.post(
        "/api/v1/non-motor/products/classes",
        headers=admin_headers,
        json={"Class": "Engineering All Risk", "IsActive": 1},
    )
    class_id = c_resp.json()["ClassId"]

    p_resp = await async_client.post(
        "/api/v1/non-motor/products",
        headers=admin_headers,
        json={
            "ClassId": class_id,
            "ProductType": "Contractors All Risk (CAR)",
            "ProductCode": "CAR-01",
            "IsActive": 1,
        },
    )
    product_id = p_resp.json()["NonMotorProductId"]

    # 1. Agent forbidden to book policy transaction directly
    f_resp = await async_client.post(
        "/api/v1/non-motor/policies",
        headers=agent_headers,
        json={
            "BranchId": 1,
            "CustomerId": 101,
            "InsuranceCompanyId": 10,
            "ClassId": class_id,
            "ProductTypeId": product_id,
            "BusinessTypeId": 1,
            "AgentId": agent_user.UserId,
            "NetPermium": "50000.00",
        },
    )
    assert f_resp.status_code == 403

    # 2. Coordinator books policy transaction
    book_resp = await async_client.post(
        "/api/v1/non-motor/policies",
        headers=coord_headers,
        json={
            "BranchId": coord_user.BranchId,
            "CustomerId": 101,
            "InsuranceCompanyId": 10,
            "ClassId": class_id,
            "ProductTypeId": product_id,
            "BusinessTypeId": 1,
            "AgentId": agent_user.UserId,
            "SumInsured": "1000000.00",
            "NetPermium": "50000.00",
            "ProPosalAmt": "50000.00",
            "AgentComm": "10.00",
            "TdsRate": "5.00",
            "PolicyNo": "POL-CAR-2026-999",
            "CoverNote": "CN-CAR-888",
        },
    )
    assert book_resp.status_code == 201
    tx_data = book_resp.json()
    trans_id = tx_data["NonMotorTransactionId"]
    assert tx_data["InwardNo"].startswith("INW-NM-")
    assert Decimal(str(tx_data["AgentCommAmt"])) == Decimal("5000.00")  # 10% of 50000
    assert Decimal(str(tx_data["TdsAmt"])) == Decimal("250.00")  # 5% of 5000
    assert Decimal(str(tx_data["NetCommission"])) == Decimal("4750.00")  # 5000 - 250

    # 3. Retrieve transaction by ID
    get_resp = await async_client.get(
        f"/api/v1/non-motor/policies/{trans_id}", headers=coord_headers
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["NonMotorTransactionId"] == trans_id

    # 4. Update transaction
    upd_resp = await async_client.put(
        f"/api/v1/non-motor/policies/{trans_id}",
        headers=admin_headers,
        json={"Remark": "Policy verified and active", "TStatus": "Completed"},
    )
    assert upd_resp.status_code == 200
    assert upd_resp.json()["TStatus"] == "Completed"
    assert upd_resp.json()["Remark"] == "Policy verified and active"

    # 5. Dashboard summary
    sum_resp = await async_client.get("/api/v1/non-motor/policies/summary", headers=coord_headers)
    assert sum_resp.status_code == 200
    sum_data = sum_resp.json()
    assert sum_data["total_policies"] >= 1
    assert Decimal(str(sum_data["total_net_premium"])) >= Decimal("50000.00")
    assert any(c["class_name"] == "Engineering All Risk" for c in sum_data["by_product_class"])
