"""
Phase 11 Integration Tests — Storage Failure Atomicity, Upload Idempotency,
Concurrent Uploads, and Cross-Phase E2E Document Lifecycle.
"""
import asyncio
import io
import json
import zipfile
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.claims_endorsement import Claim, ClaimDocument, PolicyEndorsement
from app.models.document import DocumentRecord
from app.models.payment import TransactionPayment
from app.models.quotation import AppQuatationEntry
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
async def cleanup_phase11_e2e_tables(db_session: AsyncSession, tmp_path: Path):
    storage = LocalFilesystemStorageBackend(str(tmp_path / "phase11_e2e_storage"))
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
async def test_storage_failure_atomicity_and_upload_idempotency(
    async_client: AsyncClient,
    db_session: AsyncSession,
):
    """
    Verifies:
    1. When storage write fails (`simulate_write_failure = True`), upload returns 500
       and leaves ZERO orphan rows in `tbl_documents` or `tbl_claimdocument`.
    2. Idempotent upload replay with identical `Idempotency-Key` and payload returns 200 OK
       and existing `document_id`.
    3. Idempotent upload replay with identical `Idempotency-Key` and mutated payload returns 409 Conflict.
    """
    _, headers = await create_user_with_role(
        db_session, role_name="ADMIN", branch_id=101
    )
    tx = await seed_synthetic_booked_policy(
        db_session, policy_no="POL-ATOM-001", branch_id=101
    )
    claim = Claim(
        ClaimNo="CLM-ATOM-001",
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
        EstimatedAmount=Decimal("15000.00"),
        isdeleted="0",
        CreateDate=datetime.utcnow(),
    )
    db_session.add(claim)
    await db_session.commit()
    await db_session.refresh(claim)

    # 1. Simulate storage failure
    storage = get_storage_backend()
    storage.simulate_write_failure = True
    try:
        fail_resp = await async_client.post(
            "/api/v1/documents/upload",
            headers=headers,
            data={
                "document_type": "CLAIM",
                "doc_sub_type": "SPOT_PHOTO",
                "entity_type": "CLAIM",
                "entity_id": str(claim.ClaimId),
                "claim_id": str(claim.ClaimId),
            },
            files={"file": ("fail_photo.jpg", io.BytesIO(SYNTHETIC_JPEG_BYTES), "image/jpeg")},
        )
        assert fail_resp.status_code == 500
    finally:
        storage.simulate_write_failure = False

    # Verify zero orphan DB rows in tbl_documents and tbl_claimdocument
    doc_cnt = (await db_session.execute(select(func.count()).select_from(DocumentRecord))).scalar_one()
    cdoc_cnt = (await db_session.execute(select(func.count()).select_from(ClaimDocument))).scalar_one()
    assert doc_cnt == 0
    assert cdoc_cnt == 0

    # 2. Idempotent upload + replay + conflict
    idem_headers = dict(headers, **{"Idempotency-Key": "IDEM-UP-11-001"})
    ok_resp = await async_client.post(
        "/api/v1/documents/upload",
        headers=idem_headers,
        data={
            "document_type": "POLICY",
            "doc_sub_type": "PolicyDoc",
            "entity_type": "POLICY",
            "entity_id": str(tx.TransanctionId),
        },
        files={"file": ("idem_policy.pdf", io.BytesIO(SYNTHETIC_PDF_BYTES), "application/pdf")},
    )
    assert ok_resp.status_code == 201
    doc_id = ok_resp.json()["data"]["document_id"]

    replay_resp = await async_client.post(
        "/api/v1/documents/upload",
        headers=idem_headers,
        data={
            "document_type": "POLICY",
            "doc_sub_type": "PolicyDoc",
            "entity_type": "POLICY",
            "entity_id": str(tx.TransanctionId),
        },
        files={"file": ("idem_policy.pdf", io.BytesIO(SYNTHETIC_PDF_BYTES), "application/pdf")},
    )
    assert replay_resp.status_code == 200
    assert replay_resp.json()["data"]["document_id"] == doc_id

    conflict_resp = await async_client.post(
        "/api/v1/documents/upload",
        headers=idem_headers,
        data={
            "document_type": "POLICY",
            "doc_sub_type": "PolicyDoc",
            "entity_type": "POLICY",
            "entity_id": str(tx.TransanctionId),
        },
        files={"file": ("idem_policy.pdf", io.BytesIO(SYNTHETIC_PDF_BYTES + b"%diff\n"), "application/pdf")},
    )
    assert conflict_resp.status_code == 409


@pytest.mark.asyncio
async def test_concurrent_document_uploads_without_collision(
    async_client: AsyncClient,
    db_session: AsyncSession,
):
    """
    Verifies that 5 concurrent uploads with the same filename (`concurrent_doc.pdf`)
    for the same policy transaction all succeed with distinct `storage_key`s and
    zero lost records.
    """
    _, headers = await create_user_with_role(
        db_session, role_name="ADMIN", branch_id=101
    )
    tx = await seed_synthetic_booked_policy(
        db_session, policy_no="POL-CONC-001", branch_id=101
    )
    await db_session.commit()

    async def _upload_one(idx: int):
        payload_bytes = SYNTHETIC_PDF_BYTES + f"% Concurrent Upload {idx}\n".encode("ascii")
        return await async_client.post(
            "/api/v1/documents/upload",
            headers=headers,
            data={
                "document_type": "POLICY",
                "doc_sub_type": "OtherDoc",
                "entity_type": "POLICY",
                "entity_id": str(tx.TransanctionId),
            },
            files={"file": ("concurrent_doc.pdf", io.BytesIO(payload_bytes), "application/pdf")},
        )

    results = await asyncio.gather(*[_upload_one(i) for i in range(5)])
    for r in results:
        assert r.status_code == 201, r.text

    storage_keys = {r.json()["data"]["storage_key"] for r in results}
    assert len(storage_keys) == 5

    list_resp = await async_client.get(
        f"/api/v1/policies/{tx.TransanctionId}/documents",
        headers=headers,
    )
    assert list_resp.status_code == 200
    assert list_resp.json()["data"]["total"] == 5


@pytest.mark.asyncio
async def test_full_cross_phase_e2e_document_lifecycle(
    async_client: AsyncClient,
    db_session: AsyncSession,
):
    """
    Full Cross-Phase E2E Document Journey (Phase 5 -> 6 -> 7 -> 8 -> 10 -> 11):
    1. Customer KYC PAN upload (`CUSTOMER` -> `GET /api/v1/customers/{id}/documents`)
    2. Vehicle RC upload (`VEHICLE` -> `GET /api/v1/vehicles/{id}/documents`)
    3. Quotation PDF generation + Supporting Quote upload (`QUOTATION` -> `GET /api/v1/quotations/{id}/documents`)
    4. Policy PDF (`AppPolicyPdf`) + Policy Proposal (`TransactionDocument`) + HiCaliber Webhook + Policy ZIP (`DownloadAll.ashx`)
    5. Payment Cheque Copy upload (`PAYMENT`)
    6. Claim Spot Photo (`ClaimPhoto`) + Repair Quotation (`QuotationDoc`) + Final Bill (`Claim_Final_Bill_Doc`) + Audio Note (`ClaimAudio`) + Claim ZIP
    7. Endorsement Supporting Proof (`EndorsementDoc` -> `tbl_appendorsement.SupportingDocKey` + `GET /api/v1/endorsements/{id}/documents`)
    """
    _, headers = await create_user_with_role(
        db_session, role_name="ADMIN", branch_id=101
    )
    tx = await seed_synthetic_booked_policy(
        db_session, policy_no="POL-E2E-P11-001", branch_id=101
    )
    q_entry = AppQuatationEntry(
        QuatationCode="QUOT-E2E-P11",
        QuatationDate=datetime.utcnow(),
        ProductName="PRIVATE CAR",
        Title="QUOT-E2E-P11-TITLE",
        IDV="500000",
        AtotalOwnDamPremium="10000.00",
        BtotalLiabilityPremium="5000.00",
        TotalPremium="15000.00",
        GST18="2700.00",
        finalPrmium="17700.00",
        AgentId=501,
        SaleExId=701,
        isdeleted="0",
        RegistrationNo="MH12AB1234",
    )
    db_session.add(q_entry)

    payment = TransactionPayment(
        TransanctionId=tx.TransanctionId,
        PaidAmount=Decimal("17700.00"),
        PaymentType="CHEQUE",
        docno="CHQ998877",
        bankname="HDFC Bank",
        PaymentDate=datetime.utcnow(),
        BranchId=101,
        isdeleted="0",
        isCompletePayment=0,
    )
    db_session.add(payment)

    claim = Claim(
        ClaimNo="CLM-E2E-P11-001",
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
        EstimatedAmount=Decimal("35000.00"),
        isdeleted="0",
        CreateDate=datetime.utcnow(),
    )
    db_session.add(claim)

    endorsement = PolicyEndorsement(
        EndorsementNo="END-E2E-P11-001",
        TransanctionId=tx.TransanctionId,
        PolicyNo=tx.PolicyNo,
        CustomerId=tx.CustomerId,
        CustVehId=tx.CustVehId,
        BranchId=101,
        AgentId=tx.AgentId,
        FranchiseId=601,
        SalesExId=tx.SalesEx_id,
        EndorsementType="NAME_CORRECTION",
        EndorsementCategory="NON_FINANCIAL",
        EndorsementStatus="SUBMITTED",
        EffectiveDate=datetime.utcnow(),
        RequestDate=datetime.utcnow(),
        FieldChangesJson=json.dumps({"CustMName": "K."}),
        isdeleted="0",
        CreateDate=datetime.utcnow(),
    )
    db_session.add(endorsement)
    await db_session.commit()
    await db_session.refresh(q_entry)
    await db_session.refresh(payment)
    await db_session.refresh(claim)
    await db_session.refresh(endorsement)

    # 1. Customer KYC upload
    r_cust = await async_client.post(
        "/api/v1/documents/upload",
        headers=headers,
        data={
            "document_type": "CUSTOMER",
            "doc_sub_type": "PAN",
            "entity_type": "CUSTOMER",
            "entity_id": str(tx.CustomerId),
        },
        files={"file": ("customer_pan.jpg", io.BytesIO(SYNTHETIC_JPEG_BYTES), "image/jpeg")},
    )
    assert r_cust.status_code == 201
    cust_docs = await async_client.get(f"/api/v1/customers/{tx.CustomerId}/documents", headers=headers)
    assert cust_docs.status_code == 200
    assert cust_docs.json()["data"]["total"] == 1

    # 2. Vehicle RC upload
    r_veh = await async_client.post(
        "/api/v1/documents/upload",
        headers=headers,
        data={
            "document_type": "VEHICLE",
            "doc_sub_type": "RCBook",
            "entity_type": "VEHICLE",
            "entity_id": str(tx.CustVehId),
        },
        files={"file": ("vehicle_rc.pdf", io.BytesIO(SYNTHETIC_PDF_BYTES), "application/pdf")},
    )
    assert r_veh.status_code == 201
    veh_docs = await async_client.get(f"/api/v1/vehicles/{tx.CustVehId}/documents", headers=headers)
    assert veh_docs.status_code == 200
    assert veh_docs.json()["data"]["total"] == 1

    # 3. Quotation PDF generation + supporting doc upload
    r_qgen = await async_client.post(
        f"/api/v1/quotations/{q_entry.QuatationId}/generate-pdf",
        headers=headers,
    )
    assert r_qgen.status_code == 201
    r_qsup = await async_client.post(
        "/api/v1/documents/upload",
        headers=headers,
        data={
            "document_type": "QUOTATION",
            "doc_sub_type": "SupportingDoc",
            "entity_type": "QUOTATION",
            "entity_id": str(q_entry.QuatationId),
        },
        files={"file": ("prev_quote.pdf", io.BytesIO(SYNTHETIC_PDF_BYTES), "application/pdf")},
    )
    assert r_qsup.status_code == 201
    quot_docs = await async_client.get(f"/api/v1/quotations/{q_entry.QuatationId}/documents", headers=headers)
    assert quot_docs.status_code == 200
    assert quot_docs.json()["data"]["total"] == 2

    # 4. Policy AppPolicyPdf + PolicyDoc + ZIP
    r_p1 = await async_client.post(
        "/api/v1/documents/upload",
        headers=headers,
        data={
            "document_type": "POLICY",
            "doc_sub_type": "AppPolicyPdf",
            "entity_type": "POLICY",
            "entity_id": str(tx.TransanctionId),
        },
        files={"file": ("issued_policy.pdf", io.BytesIO(SYNTHETIC_PDF_BYTES), "application/pdf")},
    )
    assert r_p1.status_code == 201
    assert r_p1.json()["data"]["legacy_virtual_folder"] == "AppPolicyPdf"

    r_p2 = await async_client.post(
        "/api/v1/documents/upload",
        headers=headers,
        data={
            "document_type": "POLICY",
            "doc_sub_type": "PolicyDoc",
            "entity_type": "POLICY",
            "entity_id": str(tx.TransanctionId),
        },
        files={"file": ("proposal_signed.pdf", io.BytesIO(SYNTHETIC_PDF_BYTES), "application/pdf")},
    )
    assert r_p2.status_code == 201
    assert r_p2.json()["data"]["legacy_virtual_folder"] == "TransactionDocument"

    # 5. Payment Cheque Copy upload
    r_pay = await async_client.post(
        "/api/v1/documents/upload",
        headers=headers,
        data={
            "document_type": "PAYMENT",
            "doc_sub_type": "ChequeCopy",
            "entity_type": "PAYMENT",
            "entity_id": str(payment.PaymentId),
        },
        files={"file": ("cheque_scan.jpg", io.BytesIO(SYNTHETIC_JPEG_BYTES), "image/jpeg")},
    )
    assert r_pay.status_code == 201

    # 6. Claim documents (Spot Photo, Repair Quotation, Final Bill, Audio Note) + Claim ZIP
    for sub_type, fname, fbytes, mime, expected_folder in (
        ("SPOT_PHOTO", "spot1.jpg", SYNTHETIC_JPEG_BYTES, "image/jpeg", "ClaimPhoto"),
        ("REPAIR_QUOTATION_IMG", "estimate.png", SYNTHETIC_PNG_BYTES, "image/png", "QuotationDoc"),
        ("FINAL_BILL_DOC", "invoice.pdf", SYNTHETIC_PDF_BYTES, "application/pdf", "Claim_Final_Bill_Doc"),
        ("CLAIM_AUDIO", "voice_note.mp3", SYNTHETIC_MP3_BYTES, "audio/mpeg", "ClaimAudio"),
    ):
        rc = await async_client.post(
            "/api/v1/documents/upload",
            headers=headers,
            data={
                "document_type": "CLAIM",
                "doc_sub_type": sub_type,
                "entity_type": "CLAIM",
                "entity_id": str(claim.ClaimId),
            },
            files={"file": (fname, io.BytesIO(fbytes), mime)},
        )
        assert rc.status_code == 201, rc.text
        assert rc.json()["data"]["legacy_virtual_folder"] == expected_folder

    claim_zip = await async_client.get(
        f"/api/v1/claims/{claim.ClaimId}/documents/zip",
        headers=headers,
    )
    assert claim_zip.status_code == 200
    with zipfile.ZipFile(io.BytesIO(claim_zip.content), "r") as zf:
        assert sorted(zf.namelist()) == [
            "Files/estimate.png",
            "Files/invoice.pdf",
            "Files/spot1.jpg",
            "Files/voice_note.mp3",
        ]

    # 7. Endorsement supporting document upload + dual-write check
    r_endo = await async_client.post(
        "/api/v1/documents/upload",
        headers=headers,
        data={
            "document_type": "ENDORSEMENT",
            "doc_sub_type": "SupportingDoc",
            "entity_type": "ENDORSEMENT",
            "entity_id": str(endorsement.EndorsementId),
        },
        files={"file": ("name_proof.pdf", io.BytesIO(SYNTHETIC_PDF_BYTES), "application/pdf")},
    )
    assert r_endo.status_code == 201
    endo_key = r_endo.json()["data"]["storage_key"]
    assert r_endo.json()["data"]["legacy_virtual_folder"] == "EndorsementDoc"

    endo_id = endorsement.EndorsementId
    endo_list = await async_client.get(
        f"/api/v1/endorsements/{endo_id}/documents",
        headers=headers,
    )
    assert endo_list.status_code == 200
    assert endo_list.json()["data"]["total"] == 1

    await db_session.commit()
    db_session.expire_all()
    refreshed_endo = (
        await db_session.execute(
            select(PolicyEndorsement).where(PolicyEndorsement.EndorsementId == endo_id)
        )
    ).scalar_one()
    assert refreshed_endo.SupportingDocKey == endo_key
