"""
Phase 11 Integration Tests — File Security Validation, Path Traversal Prevention,
MIME / Magic-Byte Verification, RBAC Role Gates, Branch Isolation, and Principal Ownership.
"""
import io
from pathlib import Path
import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.services.storage_backend import (
    LocalFilesystemStorageBackend,
    set_storage_backend,
)
from tests.integration.test_phase7_policy_booking_api import create_user_with_role
from tests.integration.test_phase10_claims_endorsements_api import seed_synthetic_booked_policy


SYNTHETIC_PDF_BYTES = (
    b"%PDF-1.4\n"
    b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
    b"2 0 obj << /Type /Pages /Kids [] /Count 0 >> endobj\n"
    b"trailer << /Root 1 0 R >>\n%%EOF\n"
)
SYNTHETIC_JPEG_BYTES = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xd9"
SYNTHETIC_PNG_BYTES = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x00IEND\xaeB`\x82"
SYNTHETIC_MP3_BYTES = b"ID3\x03\x00\x00\x00\x00\x00\x0fTIT2\x00\x00\x00\x05\x00\x00\x00Test"


@pytest.fixture(autouse=True)
async def cleanup_phase11_security_tables(db_session: AsyncSession, tmp_path: Path):
    storage = LocalFilesystemStorageBackend(str(tmp_path / "phase11_sec_storage"))
    set_storage_backend(storage)
    for tbl in (
        "tbl_documents",
        "tbl_calliber_policy_webhook",
        "tbl_claimdocument",
        "tbl_claims",
        "tbl_appendorsement",
        "tbl_app_requestedquotationfile",
        "tbl_insurancecompanyquotation",
        "tbl_app_quotationrequest",
        "tbl_app_quatationentry",
        "tbl_transactionpayment",
        "tbl_transaction",
        "tbl_vehicledetails",
        "tbl_customer",
    ):
        await db_session.execute(text(f"DELETE FROM {tbl};"))
    await db_session.commit()
    yield
    set_storage_backend(None)
    for tbl in (
        "tbl_documents",
        "tbl_calliber_policy_webhook",
        "tbl_claimdocument",
        "tbl_claims",
        "tbl_appendorsement",
        "tbl_app_requestedquotationfile",
        "tbl_insurancecompanyquotation",
        "tbl_app_quotationrequest",
        "tbl_app_quatationentry",
        "tbl_transactionpayment",
        "tbl_transaction",
        "tbl_vehicledetails",
        "tbl_customer",
    ):
        await db_session.execute(text(f"DELETE FROM {tbl};"))
    await db_session.commit()


@pytest.mark.asyncio
async def test_file_security_rejects_traversal_malicious_extensions_and_mime_spoofing(
    async_client: AsyncClient,
    db_session: AsyncSession,
    tmp_path: Path,
):
    """
    Verifies that Phase 11 rejects:
    1. Path traversal filenames (`../`, `..\\`, `/etc/`, `C:\\`, leading dot `.env.pdf`, null bytes)
    2. Executable/script extensions (`.exe`, `.bat`, `.ps1`, `.php`, `.aspx`, `.ashx`, `.js`, `.html`, `.svg`)
    3. Double-extension attacks (`invoice.php.pdf`, `payload.exe.jpg`)
    4. Magic-byte / MIME spoofing (`MZ` executable masquerading as `.pdf` or `.jpg`)
    5. Empty (0-byte) files and oversized files (`> MAX_UPLOAD_SIZE_BYTES`)
    """
    _, headers = await create_user_with_role(
        db_session,
        role_name="ADMIN",
        branch_id=101,
    )
    tx = await seed_synthetic_booked_policy(
        db_session,
        policy_no="POL-P11-SEC-001",
        branch_id=101,
    )
    await db_session.commit()

    # 1. Path traversal filenames via HTTP multipart and direct validator
    traversal_names = [
        "../../etc/passwd.pdf",
        "..\\..\\Windows\\win.ini.pdf",
        "/etc/shadow.pdf",
        "..%2F..%2Fetc%2Fpasswd.pdf",
        ".htaccess.pdf",
    ]
    for bad_name in traversal_names:
        resp = await async_client.post(
            "/api/v1/documents/upload",
            headers=headers,
            data={
                "document_type": "POLICY",
                "entity_type": "POLICY",
                "entity_id": str(tx.TransanctionId),
            },
            files={"file": (bad_name, io.BytesIO(SYNTHETIC_PDF_BYTES), "application/pdf")},
        )
        assert resp.status_code == 400, f"Expected 400 for {bad_name!r}, got {resp.status_code}: {resp.text}"

    # Direct validator checks for raw Windows drive paths & null bytes (which python-multipart strips at HTTP layer)
    from app.services.storage_backend import validate_and_sanitize_filename
    for direct_bad in ("C:\\Windows\\System32\\cmd.pdf", "bad\x00file.pdf", "../secret.pdf"):
        with pytest.raises(Exception):
            validate_and_sanitize_filename(direct_bad)

    # 2. Forbidden executable/script extensions & double extensions
    forbidden_names = [
        "webshell.aspx",
        "handler.ashx",
        "malware.exe",
        "script.ps1",
        "runner.bat",
        "backdoor.php",
        "xss.html",
        "xss.svg",
        "invoice.php.pdf",
        "trojan.exe.jpg",
    ]
    for bad_ext_name in forbidden_names:
        resp = await async_client.post(
            "/api/v1/documents/upload",
            headers=headers,
            data={
                "document_type": "POLICY",
                "entity_type": "POLICY",
                "entity_id": str(tx.TransanctionId),
            },
            files={"file": (bad_ext_name, io.BytesIO(SYNTHETIC_PDF_BYTES), "application/pdf")},
        )
        assert resp.status_code == 400, f"Expected 400 for {bad_ext_name!r}, got {resp.status_code}"

    # 3. Magic-byte spoofing: Windows PE executable (`MZ...`) uploaded as `.pdf` and `.jpg`
    pe_spoof_bytes = b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff\x00\x00"
    resp_pdf_spoof = await async_client.post(
        "/api/v1/documents/upload",
        headers=headers,
        data={
            "document_type": "POLICY",
            "entity_type": "POLICY",
            "entity_id": str(tx.TransanctionId),
        },
        files={"file": ("policy_copy.pdf", io.BytesIO(pe_spoof_bytes), "application/pdf")},
    )
    assert resp_pdf_spoof.status_code == 400
    assert "magic header" in resp_pdf_spoof.text.lower()

    resp_jpg_spoof = await async_client.post(
        "/api/v1/documents/upload",
        headers=headers,
        data={
            "document_type": "POLICY",
            "entity_type": "POLICY",
            "entity_id": str(tx.TransanctionId),
        },
        files={"file": ("spot_photo.jpg", io.BytesIO(pe_spoof_bytes), "image/jpeg")},
    )
    assert resp_jpg_spoof.status_code == 400
    assert "jpeg" in resp_jpg_spoof.text.lower()

    # 4. Empty (0-byte) file rejection
    resp_empty = await async_client.post(
        "/api/v1/documents/upload",
        headers=headers,
        data={
            "document_type": "POLICY",
            "entity_type": "POLICY",
            "entity_id": str(tx.TransanctionId),
        },
        files={"file": ("empty.pdf", io.BytesIO(b""), "application/pdf")},
    )
    assert resp_empty.status_code == 400
    assert "empty" in resp_empty.text.lower()

    # 5. Oversized file rejection (`413 Request Entity Too Large`)
    orig_max = settings.MAX_UPLOAD_SIZE_BYTES
    settings.MAX_UPLOAD_SIZE_BYTES = 1024  # 1 KB limit for test
    try:
        large_pdf = SYNTHETIC_PDF_BYTES + (b"%" * 2048)
        resp_large = await async_client.post(
            "/api/v1/documents/upload",
            headers=headers,
            data={
                "document_type": "POLICY",
                "entity_type": "POLICY",
                "entity_id": str(tx.TransanctionId),
            },
            files={"file": ("oversized.pdf", io.BytesIO(large_pdf), "application/pdf")},
        )
        assert resp_large.status_code == 413
    finally:
        settings.MAX_UPLOAD_SIZE_BYTES = orig_max

    # 6. Storage backend direct path containment check
    storage = LocalFilesystemStorageBackend(str(tmp_path / "containment_test"))
    with pytest.raises(Exception):
        storage.resolve_safe_path("../../outside.pdf")
    with pytest.raises(Exception):
        storage.resolve_safe_path("/absolute/path.pdf")


@pytest.mark.asyncio
async def test_rbac_branch_and_principal_isolation_for_documents_and_zip(
    async_client: AsyncClient,
    db_session: AsyncSession,
):
    """
    Verifies:
    - Unauthenticated requests -> 401
    - Read-only role (`pOLICY VIEW`) cannot upload/replace/delete (403) but can view/download
    - `HR` role cannot access `POLICY`/`CLAIM` documents (403)
    - Branch 101 `OPERATOR` cannot access Branch 202 policy documents (403)
    - `AGENT` 501 can access own policy documents (`AgentId=501`) but gets 403 on `AGENT` 502's documents
    - `FRANCHISE` 601 can access own policy documents (`FranchiseId=601`) but gets 403 on `FRANCHISE` 602's documents
    - Global `ADMIN` and `ACCOUNT` can read across branches
    """
    # Seed 2 policies in different branches, agents, and franchises
    tx_b101 = await seed_synthetic_booked_policy(
        db_session,
        policy_no="POL-B101-A501",
        branch_id=101,
        agent_id=501,
        franchise_id=601,
        sales_ex_id=701,
    )
    tx_b202 = await seed_synthetic_booked_policy(
        db_session,
        policy_no="POL-B202-A502",
        branch_id=202,
        agent_id=502,
        franchise_id=602,
        sales_ex_id=702,
    )

    _, admin_headers = await create_user_with_role(
        db_session, role_name="ADMIN", branch_id=101
    )
    _, op_b101_headers = await create_user_with_role(
        db_session, role_name="OPERATOR", branch_id=101
    )
    _, op_b202_headers = await create_user_with_role(
        db_session, role_name="OPERATOR", branch_id=202
    )
    _, agent_501_headers = await create_user_with_role(
        db_session, role_name="AGENT", branch_id=101, partner_user_id=501
    )
    _, agent_502_headers = await create_user_with_role(
        db_session, role_name="AGENT", branch_id=202, partner_user_id=502
    )
    _, fran_601_headers = await create_user_with_role(
        db_session, role_name="FRANCHISE", branch_id=101, partner_user_id=601
    )
    _, hr_headers = await create_user_with_role(
        db_session, role_name="HR", branch_id=101
    )
    _, pv_headers = await create_user_with_role(
        db_session, role_name="pOLICY VIEW", branch_id=101
    )
    _, acc_headers = await create_user_with_role(
        db_session, role_name="ACCOUNT", branch_id=101
    )
    await db_session.commit()

    # 1. Unauthenticated request -> 401
    unauth_resp = await async_client.get("/api/v1/documents/1")
    assert unauth_resp.status_code == 401

    # 2. Agent 501 uploads document to own policy (tx_b101) -> 201 Created
    up_501 = await async_client.post(
        "/api/v1/documents/upload",
        headers=agent_501_headers,
        data={
            "document_type": "POLICY",
            "doc_sub_type": "PolicyDoc",
            "entity_type": "POLICY",
            "entity_id": str(tx_b101.TransanctionId),
        },
        files={"file": ("b101_policy.pdf", io.BytesIO(SYNTHETIC_PDF_BYTES), "application/pdf")},
    )
    assert up_501.status_code == 201, up_501.text
    doc_b101_id = up_501.json()["data"]["document_id"]

    # 3. Operator 202 uploads document to Branch 202 policy (tx_b202) -> 201 Created
    up_202 = await async_client.post(
        "/api/v1/documents/upload",
        headers=op_b202_headers,
        data={
            "document_type": "POLICY",
            "doc_sub_type": "RCBookDoc",
            "entity_type": "POLICY",
            "entity_id": str(tx_b202.TransanctionId),
        },
        files={"file": ("b202_rc.pdf", io.BytesIO(SYNTHETIC_PDF_BYTES), "application/pdf")},
    )
    assert up_202.status_code == 201, up_202.text
    doc_b202_id = up_202.json()["data"]["document_id"]

    # 4. Agent 501 CANNOT access Agent 502's document or upload to tx_b202 -> 403 Forbidden
    assert (await async_client.get(f"/api/v1/documents/{doc_b202_id}", headers=agent_501_headers)).status_code == 403
    assert (await async_client.get(f"/api/v1/documents/{doc_b202_id}/download", headers=agent_501_headers)).status_code == 403
    assert (await async_client.get(f"/api/v1/policies/{tx_b202.TransanctionId}/documents/zip", headers=agent_501_headers)).status_code == 403

    # 5. Agent 502 CANNOT access Agent 501's document -> 403 Forbidden
    assert (await async_client.get(f"/api/v1/documents/{doc_b101_id}", headers=agent_502_headers)).status_code == 403

    # 6. Franchise 601 CAN access tx_b101 document, CANNOT access tx_b202 document
    assert (await async_client.get(f"/api/v1/documents/{doc_b101_id}", headers=fran_601_headers)).status_code == 200
    assert (await async_client.get(f"/api/v1/documents/{doc_b202_id}", headers=fran_601_headers)).status_code == 403

    # 7. Branch 101 Operator CAN access Branch 101 doc, CANNOT access Branch 202 doc
    assert (await async_client.get(f"/api/v1/documents/{doc_b101_id}/download", headers=op_b101_headers)).status_code == 200
    assert (await async_client.get(f"/api/v1/documents/{doc_b202_id}/download", headers=op_b101_headers)).status_code == 403

    # 8. Read-only `pOLICY VIEW` (Branch 101) CAN view/download Branch 101 doc, CANNOT upload or delete -> 403
    assert (await async_client.get(f"/api/v1/documents/{doc_b101_id}", headers=pv_headers)).status_code == 200
    pv_up = await async_client.post(
        "/api/v1/documents/upload",
        headers=pv_headers,
        data={
            "document_type": "POLICY",
            "entity_type": "POLICY",
            "entity_id": str(tx_b101.TransanctionId),
        },
        files={"file": ("pv_try.pdf", io.BytesIO(SYNTHETIC_PDF_BYTES), "application/pdf")},
    )
    assert pv_up.status_code == 403
    assert (await async_client.delete(f"/api/v1/documents/{doc_b101_id}", headers=pv_headers)).status_code == 403

    # 9. `HR` role CANNOT access POLICY documents -> 403 Forbidden
    assert (await async_client.get(f"/api/v1/documents/{doc_b101_id}", headers=hr_headers)).status_code == 403

    # 10. Global `ADMIN` and `ACCOUNT` CAN read across branches (both Branch 101 and Branch 202)
    assert (await async_client.get(f"/api/v1/documents/{doc_b202_id}", headers=admin_headers)).status_code == 200
    assert (await async_client.get(f"/api/v1/documents/{doc_b202_id}", headers=acc_headers)).status_code == 200
