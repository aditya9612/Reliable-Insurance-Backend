"""
Phase 11 Golden Parity & Webhook Tests — Legacy Virtual Directories, Dual-Write Compatibility,
`DEF-010` Remediation (`Claim_Final_Bill_Doc` vs `ClaimPhoto`), `DownloadAll.ashx` ZIP Streaming,
`ImageHandler.ashx` Binary Streaming, Quotation PDF Generation, and `PolicyParserWebhook.aspx`.
"""
import base64
import hashlib
import hmac
import io
import json
import zipfile
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.claims_endorsement import Claim, ClaimDocument, PolicyEndorsement
from app.models.document import DocumentRecord, PolicyParserWebhookRecord
from app.models.quotation import (
    AppQuatationEntry,
    AppQuotationRequest,
    AppRequestedQuotationFile,
    InsuranceCompanyQuotation,
)
from app.models.transaction import Transaction
from app.services.storage_backend import (
    LocalFilesystemStorageBackend,
    get_storage_backend,
    set_storage_backend,
)
from tests.integration.test_phase7_policy_booking_api import create_user_with_role
from tests.integration.test_phase10_claims_endorsements_api import seed_synthetic_booked_policy
from tests.integration.test_phase11_documents_security_and_rbac import (
    SYNTHETIC_JPEG_BYTES,
    SYNTHETIC_MP3_BYTES,
    SYNTHETIC_PDF_BYTES,
    SYNTHETIC_PNG_BYTES,
)


@pytest.fixture(autouse=True)
async def cleanup_phase11_parity_tables(db_session: AsyncSession, tmp_path: Path):
    storage = LocalFilesystemStorageBackend(str(tmp_path / "phase11_parity_storage"))
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
async def test_def010_remediation_claim_final_bill_replacement_preserves_claim_photo(
    async_client: AsyncClient,
    db_session: AsyncSession,
):
    """
    Verifies remediation of `DEF-010` (`Clerk/CL_ClaimNew.aspx.cs:L354`):
    1. Upload a Spot Survey Photo (`SPOT_PHOTO` -> `ClaimPhoto/`) and a Final Bill Document
       (`FINAL_BILL_DOC` -> `Claim_Final_Bill_Doc/`) for the same Claim.
    2. Replace the Final Bill Document (`POST /api/v1/documents/{id}/replace`).
    3. Verify that:
       - New version (`VersionNo=2`) is saved in `Claim_Final_Bill_Doc/`.
       - `tbl_claimdocument.StorageKey` is atomically updated to the new version's `StorageKey`.
       - The Spot Survey Photo in `ClaimPhoto/` remains 100% intact on disk and downloadable!
    """
    _, headers = await create_user_with_role(
        db_session, role_name="CLAIM", branch_id=101
    )
    tx = await seed_synthetic_booked_policy(db_session, policy_no="POL-DEF010-001", branch_id=101)
    claim = Claim(
        ClaimNo="CLM-DEF010-001",
        TransanctionId=tx.TransanctionId,
        PolicyNo=tx.PolicyNo,
        CustomerId=tx.CustomerId,
        CustVehId=tx.CustVehId,
        BranchId=101,
        AgentId=tx.AgentId,
        FranchiseId=601,
        SalesExId=tx.SalesEx_id,
        ClaimType="OD",
        ClaimStatus="INTIMATED",
        IntimationDate=datetime.utcnow(),
        LossDate=datetime.utcnow(),
        EstimatedAmount=Decimal("25000.00"),
        isdeleted="0",
        CreateDate=datetime.utcnow(),
    )
    db_session.add(claim)
    await db_session.commit()
    await db_session.refresh(claim)

    # 1. Upload Spot Survey Photo -> ClaimPhoto/
    up_spot = await async_client.post(
        "/api/v1/documents/upload",
        headers=headers,
        data={
            "document_type": "CLAIM",
            "doc_sub_type": "SPOT_PHOTO",
            "entity_type": "CLAIM",
            "entity_id": str(claim.ClaimId),
            "claim_id": str(claim.ClaimId),
        },
        files={"file": ("spot_damage.jpg", io.BytesIO(SYNTHETIC_JPEG_BYTES), "image/jpeg")},
    )
    assert up_spot.status_code == 201, up_spot.text
    spot_data = up_spot.json()["data"]
    assert spot_data["legacy_virtual_folder"] == "ClaimPhoto"
    assert spot_data["storage_key"].startswith("ClaimPhoto/")

    # 2. Upload Final Bill Document v1 -> Claim_Final_Bill_Doc/
    up_fb_v1 = await async_client.post(
        "/api/v1/documents/upload",
        headers=headers,
        data={
            "document_type": "CLAIM",
            "doc_sub_type": "FINAL_BILL_DOC",
            "entity_type": "CLAIM",
            "entity_id": str(claim.ClaimId),
            "claim_id": str(claim.ClaimId),
        },
        files={"file": ("final_bill_v1.pdf", io.BytesIO(SYNTHETIC_PDF_BYTES), "application/pdf")},
    )
    assert up_fb_v1.status_code == 201, up_fb_v1.text
    fb_v1_data = up_fb_v1.json()["data"]
    assert fb_v1_data["legacy_virtual_folder"] == "Claim_Final_Bill_Doc"
    assert fb_v1_data["storage_key"].startswith("Claim_Final_Bill_Doc/")
    assert fb_v1_data["legacy_ref_table"] == "tbl_claimdocument"
    legacy_claim_doc_id = fb_v1_data["legacy_ref_id"]

    # 3. Replace Final Bill Document with v2
    updated_pdf_bytes = SYNTHETIC_PDF_BYTES + b"% Updated Final Bill V2\n"
    rep_resp = await async_client.post(
        f"/api/v1/documents/{fb_v1_data['document_id']}/replace",
        headers=headers,
        data={"remarks": "Revised garage invoice"},
        files={"file": ("final_bill_v2.pdf", io.BytesIO(updated_pdf_bytes), "application/pdf")},
    )
    assert rep_resp.status_code == 200, rep_resp.text
    fb_v2_data = rep_resp.json()["data"]
    assert fb_v2_data["version_no"] == 2
    assert fb_v2_data["replaces_document_id"] == fb_v1_data["document_id"]
    assert fb_v2_data["legacy_virtual_folder"] == "Claim_Final_Bill_Doc"
    assert fb_v2_data["storage_key"].startswith("Claim_Final_Bill_Doc/")
    assert fb_v2_data["storage_key"] != fb_v1_data["storage_key"]

    # 4. Verify Spot Photo in ClaimPhoto/ is 100% untouched (`DEF-010` fixed)
    dl_spot = await async_client.get(
        f"/api/v1/documents/{spot_data['document_id']}/download",
        headers=headers,
    )
    assert dl_spot.status_code == 200
    assert dl_spot.content == SYNTHETIC_JPEG_BYTES

    # 5. Verify dual-written `tbl_claimdocument` points to v2's canonical StorageKey
    await db_session.commit()
    db_session.expire_all()
    c_doc = (
        await db_session.execute(
            select(ClaimDocument).where(ClaimDocument.ClaimDocId == legacy_claim_doc_id)
        )
    ).scalar_one()
    assert c_doc.StorageKey == fb_v2_data["storage_key"]
    assert c_doc.DocumentName == "final_bill_v2.pdf"


@pytest.mark.asyncio
async def test_download_all_ashx_zip_and_image_handler_ashx_golden_parity(
    async_client: AsyncClient,
    db_session: AsyncSession,
):
    """
    Verifies Golden Parity for:
    1. `DownloadAll.ashx` (`GET /api/v1/documents/legacy/DownloadAll.ashx?TransId=...&PolicyNo=...`):
       - Supports both raw integer `TransId` and base64-encoded `TransId`
       - Places all files inside `"Files/"` folder inside the ZIP (`Files/<filename>`)
       - Disambiguates duplicate filenames (`Files/rc_copy.pdf`, `Files/rc_copy_2.pdf`)
       - Gracefully skips missing physical files on disk (`X-Missing-File-Count: 1`)
       - Sets `Content-Disposition: attachment; filename="POL-ZIP-777.zip"`
    2. `ImageHandler.ashx` (`GET /api/v1/documents/legacy/ImageHandler.ashx?Id=...`):
       - Streams exact image bytes with `Content-Type: image/png` / `image/jpeg`
    """
    _, headers = await create_user_with_role(
        db_session, role_name="ADMIN", branch_id=101
    )
    tx = await seed_synthetic_booked_policy(
        db_session, policy_no="POL-ZIP-777", branch_id=101
    )
    await db_session.commit()

    # Upload 3 documents (two with identical filename `rc_copy.pdf` and one PNG image)
    pdf_a = SYNTHETIC_PDF_BYTES + b"% Doc A\n"
    pdf_b = SYNTHETIC_PDF_BYTES + b"% Doc B\n"

    r1 = await async_client.post(
        "/api/v1/documents/upload",
        headers=headers,
        data={
            "document_type": "POLICY",
            "doc_sub_type": "RCBookDoc",
            "entity_type": "POLICY",
            "entity_id": str(tx.TransanctionId),
        },
        files={"file": ("rc_copy.pdf", io.BytesIO(pdf_a), "application/pdf")},
    )
    assert r1.status_code == 201
    doc1_key = r1.json()["data"]["storage_key"]

    r2 = await async_client.post(
        "/api/v1/documents/upload",
        headers=headers,
        data={
            "document_type": "POLICY",
            "doc_sub_type": "PrevPolicyDoc",
            "entity_type": "POLICY",
            "entity_id": str(tx.TransanctionId),
        },
        files={"file": ("rc_copy.pdf", io.BytesIO(pdf_b), "application/pdf")},
    )
    assert r2.status_code == 201

    r3 = await async_client.post(
        "/api/v1/documents/upload",
        headers=headers,
        data={
            "document_type": "POLICY",
            "doc_sub_type": "OtherDoc",
            "entity_type": "POLICY",
            "entity_id": str(tx.TransanctionId),
        },
        files={"file": ("vehicle_front.png", io.BytesIO(SYNTHETIC_PNG_BYTES), "image/png")},
    )
    assert r3.status_code == 201
    img_doc_id = r3.json()["data"]["document_id"]

    # 1. Test `ImageHandler.ashx` streaming parity
    img_resp = await async_client.get(
        f"/api/v1/documents/legacy/ImageHandler.ashx?Id={img_doc_id}",
        headers=headers,
    )
    assert img_resp.status_code == 200
    assert img_resp.headers["content-type"] == "image/png"
    assert img_resp.headers["x-content-type-options"] == "nosniff"
    assert img_resp.content == SYNTHETIC_PNG_BYTES

    # 2. Test `DownloadAll.ashx` with base64-encoded TransId
    b64_tid = base64.urlsafe_b64encode(str(tx.TransanctionId).encode("ascii")).decode("ascii")
    zip_resp = await async_client.get(
        f"/api/v1/documents/legacy/DownloadAll.ashx?TransId={b64_tid}&PolicyNo=POL-ZIP-777",
        headers=headers,
    )
    assert zip_resp.status_code == 200
    assert zip_resp.headers["content-type"] == "application/zip"
    assert 'filename="POL-ZIP-777.zip"' in zip_resp.headers["content-disposition"]
    assert zip_resp.headers["x-included-file-count"] == "3"
    assert zip_resp.headers["x-missing-file-count"] == "0"

    with zipfile.ZipFile(io.BytesIO(zip_resp.content), "r") as zf:
        names = sorted(zf.namelist())
        assert names == [
            "Files/rc_copy.pdf",
            "Files/rc_copy_2.pdf",
            "Files/vehicle_front.png",
        ]
        assert zf.read("Files/rc_copy.pdf") == pdf_a
        assert zf.read("Files/rc_copy_2.pdf") == pdf_b
        assert zf.read("Files/vehicle_front.png") == SYNTHETIC_PNG_BYTES

    # 3. Simulate a missing legacy file on disk (`if (File.Exists(filePath))` in DownloadAll.ashx.cs:L57)
    get_storage_backend().delete_bytes(doc1_key)
    zip_resp_partial = await async_client.get(
        f"/api/v1/documents/legacy/DownloadAll.ashx?TransId={tx.TransanctionId}&PolicyNo=POL-ZIP-777",
        headers=headers,
    )
    assert zip_resp_partial.status_code == 200
    assert zip_resp_partial.headers["x-included-file-count"] == "2"
    assert zip_resp_partial.headers["x-missing-file-count"] == "1"


@pytest.mark.asyncio
async def test_quotation_pdf_generation_and_policy_parser_webhook_parity(
    async_client: AsyncClient,
    db_session: AsyncSession,
):
    """
    Verifies:
    1. Quotation PDF generation (`POST /api/v1/quotations/{id}/generate-pdf`) -> `PDF_Files/` + `tbl_app_requestedquotationfile`
    2. HiCaliber Policy Parser Webhook (`POST /api/v1/documents/webhooks/policy-parser`):
       - Rejects unauthenticated or invalid HMAC signature (`401 Unauthorized`)
       - Accepts valid HMAC-SHA256 `X-Calliber-Signature`
       - Persists `tbl_calliber_policy_webhook` and links `tbl_transaction.calliber_policyId`
       - Replays idempotently (`200 OK`) on duplicate delivery and returns `409 Conflict` on payload mismatch
    """
    _, headers = await create_user_with_role(
        db_session, role_name="ADMIN", branch_id=101
    )
    tx = await seed_synthetic_booked_policy(
        db_session, policy_no="POL-CALLIBER-901", branch_id=101
    )
    q_entry = AppQuatationEntry(
        QuatationCode="QUOT-P11-001",
        QuatationDate=datetime.utcnow(),
        ProductName="PRIVATE CAR",
        Title="QUOT-P11-001-TITLE",
        IDV="650000",
        AtotalOwnDamPremium="12000.00",
        BtotalLiabilityPremium="3500.00",
        TotalPremium="15500.00",
        GST18="2790.00",
        finalPrmium="18290.00",
        AgentId=501,
        SaleExId=701,
        isdeleted="0",
        RegistrationNo="MH12XY9999",
    )
    db_session.add(q_entry)
    await db_session.commit()
    await db_session.refresh(q_entry)

    # 1. Generate Quotation PDF
    gen_resp = await async_client.post(
        f"/api/v1/quotations/{q_entry.QuatationId}/generate-pdf",
        headers=headers,
    )
    assert gen_resp.status_code == 201, gen_resp.text
    gen_data = gen_resp.json()["data"]
    assert gen_data["legacy_virtual_folder"] == "PDF_Files"
    assert gen_data["legacy_ref_table"] == "tbl_app_requestedquotationfile"

    dl_pdf = await async_client.get(gen_data["download_url"], headers=headers)
    assert dl_pdf.status_code == 200
    assert dl_pdf.content.startswith(b"%PDF-1.4")
    assert b"QUOT-P11-001" in dl_pdf.content

    # 2. PolicyParserWebhook: missing auth header -> 401
    webhook_payload = {
        "WebhookEventId": "EVT-CAL-901",
        "PolicyNo": "POL-CALLIBER-901",
        "CustomerName": "Ramesh Kumar Verma",
        "VehicleRegNo": "MH12AB1234",
        "EngineNo": "ENGINEP10001",
        "ChassisNo": "CHASSISP10001",
        "InsCompany": "ICICI Lombard",
        "ProductType": "PRIVATE CAR",
        "PolicyType": "PACKAGE",
        "StartDate": "2026-10-01",
        "EndDate": "2027-09-30",
        "IDV": "500000.00",
        "ODPremium": "10000.00",
        "TPPremium": "5000.00",
        "NetPremium": "15000.00",
        "GSTAmount": "2700.00",
        "GrossPremium": "17700.00",
        "NCBPercent": "20.00",
        "UpdatedBy": "HiCaliberBot",
    }
    raw_json = json.dumps(webhook_payload).encode("utf-8")

    unauth_wh = await async_client.post(
        "/api/v1/documents/webhooks/policy-parser",
        content=raw_json,
        headers={"Content-Type": "application/json"},
    )
    assert unauth_wh.status_code == 401

    bad_sig_wh = await async_client.post(
        "/api/v1/documents/webhooks/policy-parser",
        content=raw_json,
        headers={
            "Content-Type": "application/json",
            "X-Calliber-Signature": "sha256=0000000000000000000000000000000000000000000000000000000000000000",
        },
    )
    assert bad_sig_wh.status_code == 401

    # 3. Valid HMAC-SHA256 signature -> 201 Created + links tbl_transaction.calliber_policyId
    valid_sig = hmac.new(
        settings.POLICY_PARSER_WEBHOOK_SECRET.encode("utf-8"),
        raw_json,
        hashlib.sha256,
    ).hexdigest()

    ok_wh = await async_client.post(
        "/api/v1/documents/webhooks/policy-parser",
        content=raw_json,
        headers={
            "Content-Type": "application/json",
            "X-Calliber-Signature": f"sha256={valid_sig}",
            "Idempotency-Key": "IDEM-WH-901",
        },
    )
    assert ok_wh.status_code == 201, ok_wh.text
    wh_data = ok_wh.json()["data"]
    tx_id = tx.TransanctionId
    assert wh_data["policy_no"] == "POL-CALLIBER-901"
    assert wh_data["linked_transaction_id"] == tx_id
    assert wh_data["processing_status"] == "LINKED"

    await db_session.commit()
    db_session.expire_all()
    refreshed_tx = (
        await db_session.execute(
            select(Transaction).where(Transaction.TransanctionId == tx_id)
        )
    ).scalar_one()
    assert refreshed_tx.calliber_policyId == wh_data["calliber_policy_id"]
    assert refreshed_tx.calliber_UpdateBy == "HiCaliberBot"

    # 4. Idempotent replay with same Idempotency-Key -> 200 OK
    replay_wh = await async_client.post(
        "/api/v1/documents/webhooks/policy-parser",
        content=raw_json,
        headers={
            "Content-Type": "application/json",
            "X-Calliber-Signature": f"sha256={valid_sig}",
            "Idempotency-Key": "IDEM-WH-901",
        },
    )
    assert replay_wh.status_code == 200
    assert replay_wh.json()["data"]["calliber_policy_id"] == wh_data["calliber_policy_id"]

    # 5. Same Idempotency-Key with modified payload -> 409 Conflict
    mutated_payload = dict(webhook_payload, GrossPremium="19999.00")
    mutated_raw = json.dumps(mutated_payload).encode("utf-8")
    mutated_sig = hmac.new(
        settings.POLICY_PARSER_WEBHOOK_SECRET.encode("utf-8"),
        mutated_raw,
        hashlib.sha256,
    ).hexdigest()
    conflict_wh = await async_client.post(
        "/api/v1/documents/webhooks/policy-parser",
        content=mutated_raw,
        headers={
            "Content-Type": "application/json",
            "X-Calliber-Signature": f"sha256={mutated_sig}",
            "Idempotency-Key": "IDEM-WH-901",
        },
    )
    assert conflict_wh.status_code == 409
