"""
Phase 20 Batch 1 Automated Test Suite — Operational Extensions & Parity.
Covers:
1. Bulletins & Circulars Master (F-20-001)
2. Mobile Customer Helpdesk & Support Chat (F-20-002)
3. Web Notification Alerts Master (F-20-003)
4. Partner Loyalty & Reward Points Ledger (F-20-004)
"""
from datetime import date, datetime, timedelta
from decimal import Decimal
import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from tests.integration.test_phase7_policy_booking_api import create_user_with_role


@pytest.fixture(autouse=True)
async def cleanup_phase20_batch1_tables(db_session: AsyncSession):
    """Purge synthetic Phase 20 Batch 1 tables before and after each test."""
    tables = [
        "tbl_rewardpoint",
        "tbl_chatboard",
        "tbl_customerhelp",
        "tbl_webnotification",
        "tbl_circular",
    ]
    for tbl in tables:
        await db_session.execute(text(f"DELETE FROM {tbl};"))
    await db_session.commit()
    yield
    for tbl in tables:
        await db_session.execute(text(f"DELETE FROM {tbl};"))
    await db_session.commit()


# ==============================================================================
# 1. F-20-001: Bulletins & Circulars Master
# ==============================================================================

@pytest.mark.asyncio
async def test_circulars_lifecycle_and_rbac(async_client: AsyncClient, db_session: AsyncSession):
    _, admin_headers = await create_user_with_role(db_session, "ADMIN")
    _, agent_headers = await create_user_with_role(db_session, "AGENT")

    # 1. Non-admin forbidden to create
    forbidden_resp = await async_client.post(
        "/api/v1/admin/circulars",
        headers=agent_headers,
        json={
            "subject": "Unauthorized Circular",
            "circulardate": str(date.today()),
        },
    )
    assert forbidden_resp.status_code == 403

    # 2. Admin creates circular
    create_resp = await async_client.post(
        "/api/v1/admin/circulars",
        headers=admin_headers,
        json={
            "subject": "New Commission Grid Guidelines",
            "circulardate": str(date.today()),
            "pdfpath": "/uploads/circulars/q4_guidelines.pdf",
            "is_active": 1,
        },
    )
    assert create_resp.status_code == 201
    circular_data = create_resp.json()
    circular_id = circular_data["circularid"]
    assert circular_data["subject"] == "New Commission Grid Guidelines"
    assert circular_data["is_active"] == 1

    # 3. List circulars (any authenticated user)
    list_resp = await async_client.get(
        "/api/v1/admin/circulars",
        headers=agent_headers,
    )
    assert list_resp.status_code == 200
    items = list_resp.json()
    assert len(items) >= 1
    assert any(c["circularid"] == circular_id for c in items)

    # 4. Get circular details
    get_resp = await async_client.get(
        f"/api/v1/admin/circulars/{circular_id}",
        headers=agent_headers,
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["subject"] == "New Commission Grid Guidelines"

    # 5. Update circular (Admin only)
    update_resp = await async_client.put(
        f"/api/v1/admin/circulars/{circular_id}",
        headers=admin_headers,
        json={
            "subject": "Updated Commission Grid Guidelines",
            "is_active": 1,
        },
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["subject"] == "Updated Commission Grid Guidelines"

    # 6. Deactivate circular (Admin only)
    del_resp = await async_client.delete(
        f"/api/v1/admin/circulars/{circular_id}",
        headers=admin_headers,
    )
    assert del_resp.status_code == 200

    # 7. Verify inactive circular does not show in active list
    list_active_resp = await async_client.get(
        "/api/v1/admin/circulars?active_only=true",
        headers=agent_headers,
    )
    assert list_active_resp.status_code == 200
    assert not any(c["circularid"] == circular_id for c in list_active_resp.json())


# ==============================================================================
# 2. F-20-002: Mobile Customer Helpdesk & Support Chat
# ==============================================================================

@pytest.mark.asyncio
async def test_customer_helpdesk_and_chat_workflow(async_client: AsyncClient, db_session: AsyncSession):
    _, operator_headers = await create_user_with_role(db_session, "OPERATOR")
    _, agent_headers = await create_user_with_role(db_session, "AGENT")

    # 1. Agent submits customer help inquiry
    create_ticket_resp = await async_client.post(
        "/api/v1/renewals/customer-help",
        headers=agent_headers,
        json={
            "CustomerId": 101,
            "Subject": "Renewal Assistance Needed",
            "Message": "Need quotation for comprehensive cover renewal.",
            "RegistrationNo": "MH12AB1234",
            "PolicyNo": "POL-MOT-9901",
        },
    )
    assert create_ticket_resp.status_code == 201
    ticket = create_ticket_resp.json()
    ticket_id = ticket["CustHelpId"]
    assert ticket["Status"] == "OPEN"
    assert ticket["Subject"] == "Renewal Assistance Needed"

    # 2. List tickets
    list_tickets_resp = await async_client.get(
        "/api/v1/renewals/customer-help",
        headers=operator_headers,
    )
    assert list_tickets_resp.status_code == 200
    assert any(t["CustHelpId"] == ticket_id for t in list_tickets_resp.json())

    # 3. Agent cannot resolve ticket (RBAC forbidden)
    agent_resolve_resp = await async_client.post(
        f"/api/v1/renewals/customer-help/{ticket_id}/resolve",
        headers=agent_headers,
        json={
            "Status": "RESOLVED",
            "ResolutionRemark": "Resolved by agent directly.",
        },
    )
    assert agent_resolve_resp.status_code == 403

    # 4. Operator resolves ticket
    resolve_resp = await async_client.post(
        f"/api/v1/renewals/customer-help/{ticket_id}/resolve",
        headers=operator_headers,
        json={
            "Status": "RESOLVED",
            "ResolutionRemark": "Contacted client and shared renewal quotation via WhatsApp.",
        },
    )
    assert resolve_resp.status_code == 200
    resolved_ticket = resolve_resp.json()
    assert resolved_ticket["Status"] == "RESOLVED"
    assert "Contacted client" in resolved_ticket["ResolutionRemark"]
    assert resolved_ticket["ResolvedBy"] is not None

    # 5. Support Chat: Customer/Agent posts message
    chat_resp = await async_client.post(
        "/api/v1/renewals/customer-help/chat",
        headers=agent_headers,
        json={
            "CustHelpId": ticket_id,
            "ChatText": "Is NCB transfer allowed on this renewal?",
            "RegistrationNo": "MH12AB1234",
            "ReferenceAgentId": 201,
        },
    )
    assert chat_resp.status_code == 201
    chat_msg = chat_resp.json()
    chat_id = chat_msg["ChatId"]
    assert chat_msg["ChatText"] == "Is NCB transfer allowed on this renewal?"
    assert chat_msg["Reply"] is None

    # 6. Operator replies to chat message
    reply_resp = await async_client.post(
        f"/api/v1/renewals/customer-help/chat/{chat_id}/reply",
        headers=operator_headers,
        json={
            "Reply": "Yes, with 50% NCB bonus upon submitting previous policy copy.",
            "Remark": "Confirmed with underwriter.",
        },
    )
    assert reply_resp.status_code == 200
    replied = reply_resp.json()
    assert replied["Reply"] == "Yes, with 50% NCB bonus upon submitting previous policy copy."

    # 7. List chat messages
    messages_resp = await async_client.get(
        f"/api/v1/renewals/customer-help/chat/messages?cust_help_id={ticket_id}",
        headers=agent_headers,
    )
    assert messages_resp.status_code == 200
    messages = messages_resp.json()
    assert len(messages) >= 1
    assert messages[0]["ChatId"] == chat_id


# ==============================================================================
# 3. F-20-003: Web Notifications Alerts Master
# ==============================================================================

@pytest.mark.asyncio
async def test_web_notifications_lifecycle(async_client: AsyncClient, db_session: AsyncSession):
    _, admin_headers = await create_user_with_role(db_session, "ADMIN")
    _, agent_headers = await create_user_with_role(db_session, "AGENT")

    # 1. Non-admin forbidden to create notification
    unauth_resp = await async_client.post(
        "/api/v1/admin/web-notifications",
        headers=agent_headers,
        json={
            "NotMessage": "Testing RBAC",
            "Severity": "INFO",
        },
    )
    assert unauth_resp.status_code == 403

    # 2. Admin creates notification
    create_resp = await async_client.post(
        "/api/v1/admin/web-notifications",
        headers=admin_headers,
        json={
            "NotMessage": "Server maintenance scheduled tonight from 11:00 PM to 01:00 AM.",
            "TargetRole": "AGENT",
            "Severity": "WARNING",
            "ExpiryDate": (datetime.utcnow() + timedelta(days=2)).isoformat(),
        },
    )
    assert create_resp.status_code == 201
    notif = create_resp.json()
    notif_id = notif["NotId"]
    assert notif["Severity"] == "WARNING"
    assert notif["IsActive"] == 1

    # 3. List active notifications
    list_resp = await async_client.get(
        "/api/v1/admin/web-notifications?target_role=AGENT",
        headers=agent_headers,
    )
    assert list_resp.status_code == 200
    items = list_resp.json()
    assert any(n["NotId"] == notif_id for n in items)

    # 4. Dismiss notification
    dismiss_resp = await async_client.delete(
        f"/api/v1/admin/web-notifications/{notif_id}",
        headers=admin_headers,
    )
    assert dismiss_resp.status_code == 200

    # 5. Confirm dismissed notification does not show in active list
    list_after_resp = await async_client.get(
        "/api/v1/admin/web-notifications",
        headers=agent_headers,
    )
    assert list_after_resp.status_code == 200
    assert not any(n["NotId"] == notif_id for n in list_after_resp.json())


# ==============================================================================
# 4. F-20-004: Partner Loyalty & Reward Points Ledger
# ==============================================================================

@pytest.mark.asyncio
async def test_reward_points_ledger_and_summary(async_client: AsyncClient, db_session: AsyncSession):
    _, account_headers = await create_user_with_role(db_session, "ACCOUNT")
    _, agent_headers = await create_user_with_role(db_session, "AGENT")

    partner_id = 501

    # 1. Agent cannot record reward points (RBAC gate)
    unauth_resp = await async_client.post(
        "/api/v1/agents/reward-points",
        headers=agent_headers,
        json={
            "PartnerType": "AGENT",
            "PartnerId": partner_id,
            "RewardPointGet": "100.00",
            "RewardPointUtilizes": "0.00",
            "Remarks": "Self-awarded points",
        },
    )
    assert unauth_resp.status_code == 403

    # 2. Account records CREDIT of 150 points
    credit1_resp = await async_client.post(
        "/api/v1/agents/reward-points",
        headers=account_headers,
        json={
            "PartnerType": "AGENT",
            "PartnerId": partner_id,
            "RewardPointGet": "150.00",
            "RewardPointUtilizes": "0.00",
            "PolicyId": 9901,
            "Remarks": "Policy booking reward bonus",
        },
    )
    assert credit1_resp.status_code == 201
    credit1 = credit1_resp.json()
    assert Decimal(str(credit1["RewardPointGet"])) == Decimal("150.00")
    assert Decimal(str(credit1["PointBalance"])) == Decimal("150.00")

    # 3. Account records another CREDIT of 50 points
    credit2_resp = await async_client.post(
        "/api/v1/agents/reward-points",
        headers=account_headers,
        json={
            "PartnerType": "AGENT",
            "PartnerId": partner_id,
            "RewardPointGet": "50.00",
            "RewardPointUtilizes": "0.00",
            "Remarks": "Target achievement incentive",
        },
    )
    assert credit2_resp.status_code == 201
    assert Decimal(str(credit2_resp.json()["PointBalance"])) == Decimal("200.00")

    # 4. Account records DEBIT of 60 points (redemption)
    debit_resp = await async_client.post(
        "/api/v1/agents/reward-points",
        headers=account_headers,
        json={
            "PartnerType": "AGENT",
            "PartnerId": partner_id,
            "RewardPointGet": "0.00",
            "RewardPointUtilizes": "60.00",
            "Remarks": "Amazon voucher redemption",
        },
    )
    assert debit_resp.status_code == 201
    assert Decimal(str(debit_resp.json()["PointBalance"])) == Decimal("140.00")

    # 5. List reward points ledger
    ledger_resp = await async_client.get(
        f"/api/v1/agents/reward-points?partner_type=AGENT&partner_id={partner_id}",
        headers=agent_headers,
    )
    assert ledger_resp.status_code == 200
    ledger_items = ledger_resp.json()
    assert len(ledger_items) == 3

    # 6. Check reward points summary (Total Earned = 200, Redeemed = 60, Balance = 140)
    summary_resp = await async_client.get(
        f"/api/v1/agents/reward-points/summary?partner_type=AGENT&partner_id={partner_id}",
        headers=agent_headers,
    )
    assert summary_resp.status_code == 200
    summary = summary_resp.json()
    assert summary["PartnerId"] == partner_id
    assert Decimal(str(summary["TotalEarned"])) == Decimal("200.00")
    assert Decimal(str(summary["TotalUtilized"])) == Decimal("60.00")
    assert Decimal(str(summary["CurrentBalance"])) == Decimal("140.00")
    assert summary["TransactionsCount"] == 3
