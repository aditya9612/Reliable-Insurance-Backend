"""Phase 11 Unit Tests: Storage Backend Abstraction, Legacy Folder Naming, File Validation & Production Isolation."""
from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.core.config import Settings
from app.services.storage_backend import (
    InMemoryObjectStorageBackend,
    LocalFilesystemStorageBackend,
    StorageBackendError,
    build_stored_filename_and_key,
    resolve_legacy_virtual_folder,
    validate_and_sanitize_filename,
    validate_file_content_and_mime,
)


def test_legacy_virtual_folder_mapping_all_categories():
    """Verify all canonical document categories and subtypes map to their exact legacy virtual folder."""
    assert resolve_legacy_virtual_folder("POLICY", "POLICY_PDF") == "TransactionDocument"
    assert resolve_legacy_virtual_folder("POLICY", "APP_POLICY_PDF") == "AppPolicyPdf"
    assert resolve_legacy_virtual_folder("QUOTATION", "QUOTATION_PDF") == "PDF_Files"
    assert resolve_legacy_virtual_folder("QUOTATION", "REQ_QUOTE_FILE") == "QuotationDoc"
    assert resolve_legacy_virtual_folder("CLAIM", "CLAIM_PHOTO") == "ClaimPhoto"
    assert resolve_legacy_virtual_folder("CLAIM", "FINAL_BILL_DOC") == "Claim_Final_Bill_Doc"
    assert resolve_legacy_virtual_folder("CLAIM", "CLAIM_AUDIO") == "ClaimAudio"
    assert resolve_legacy_virtual_folder("CLAIM", "REPAIR_QUOTATION_IMG") == "QuotationDoc"
    assert resolve_legacy_virtual_folder("ENDORSEMENT", "SUPPORTING_DOC") == "EndorsementDoc"
    assert resolve_legacy_virtual_folder("POSP", "PAN_CARD") == "POSDoc"
    assert resolve_legacy_virtual_folder("AGENT", "AADHAR_CARD") == "AgentDoc"
    assert resolve_legacy_virtual_folder("KYC", "PAN") == "AgentDoc"
    assert resolve_legacy_virtual_folder("CUSTOMER", "KYC") == "TransactionDocument"
    assert resolve_legacy_virtual_folder("VEHICLE", "RC") == "TransactionDocument"


def test_build_stored_filename_and_key_deterministic_and_unique():
    """Verify legacy naming patterns and canonical storage key generation."""
    folder1, fn1, key1 = build_stored_filename_and_key(
        document_type="CLAIM",
        doc_sub_type="CLAIM_PHOTO",
        entity_type="CLAIM",
        entity_id=42,
        sanitized_filename="photo.jpg",
        ext=".jpg",
    )
    assert folder1 == "ClaimPhoto"
    assert fn1.startswith("42_")
    assert "_Img_" in fn1
    assert fn1.endswith(".jpg")
    assert key1 == f"ClaimPhoto/claim/42/{fn1}"

    folder2, fn2, key2 = build_stored_filename_and_key(
        document_type="CLAIM",
        doc_sub_type="FINAL_BILL_DOC",
        entity_type="CLAIM",
        entity_id=42,
        sanitized_filename="bill.pdf",
        ext=".pdf",
    )
    assert folder2 == "Claim_Final_Bill_Doc"
    assert fn2.startswith("42_")
    assert fn2.endswith(".pdf")
    assert key2 == f"Claim_Final_Bill_Doc/claim/42/{fn2}"
    assert key1 != key2

    folder_q, fn_q, key_q = build_stored_filename_and_key(
        document_type="QUOTATION",
        doc_sub_type="QUOTATION_PDF",
        entity_type="QUOTATION",
        entity_id=105,
        sanitized_filename="quotation.pdf",
        ext=".pdf",
    )
    assert folder_q == "PDF_Files"
    assert fn_q.startswith("Quotation_105_")
    assert fn_q.endswith(".pdf")
    assert key_q == f"PDF_Files/quotation/105/{fn_q}"


def test_filename_validation_rejects_traversal_and_dangerous_extensions():
    """Verify path traversal, null bytes, leading dots, and dangerous extensions are rejected."""
    for bad_name in [
        "../secret.pdf",
        "..\\secret.pdf",
        "/etc/passwd.pdf",
        "C:\\Windows\\win.ini.pdf",
        ".hidden.pdf",
        "file\x00.pdf",
        "script.php.pdf",
        "malware.exe",
        "shell.ashx",
        "page.aspx",
        "xss.svg",
        "page.html",
        "run.bat",
        "run.ps1",
    ]:
        with pytest.raises(HTTPException) as exc_info:
            validate_and_sanitize_filename(bad_name)
        assert exc_info.value.status_code == 400


def test_file_content_and_mime_magic_bytes():
    """Verify binary magic byte checks for PDF, JPEG, PNG, MP3, WAV, and CSV/TXT."""
    mime_pdf, sha_pdf = validate_file_content_and_mime(b"%PDF-1.4\ncontent\n%%EOF", ".pdf", "application/pdf")
    assert mime_pdf == "application/pdf"
    assert len(sha_pdf) == 64

    mime_jpg, _ = validate_file_content_and_mime(b"\xff\xd8\xff\xe0\x00\x10JFIF", ".jpg", "image/jpeg")
    assert mime_jpg == "image/jpeg"

    mime_png, _ = validate_file_content_and_mime(b"\x89PNG\r\n\x1a\n\x00\x00", ".png", "image/png")
    assert mime_png == "image/png"

    mime_mp3, _ = validate_file_content_and_mime(b"ID3\x04\x00\x00\x00", ".mp3", "audio/mpeg")
    assert mime_mp3 == "audio/mpeg"

    mime_wav, _ = validate_file_content_and_mime(b"RIFF\x24\x00\x00\x00WAVEfmt ", ".wav", "audio/wav")
    assert mime_wav == "audio/wav"

    mime_csv, _ = validate_file_content_and_mime(b"col1,col2\n1,2\n", ".csv", "text/csv")
    assert mime_csv == "text/csv"

    with pytest.raises(HTTPException):
        validate_file_content_and_mime(b"", ".pdf", "application/pdf")

    with pytest.raises(HTTPException):
        validate_file_content_and_mime(b"NOT_A_PDF", ".pdf", "application/pdf")

    with pytest.raises(HTTPException):
        validate_file_content_and_mime(b"%PDF-1.4\n%%EOF", ".pdf", "image/png")


@pytest.mark.asyncio
async def test_local_and_in_memory_storage_backends(tmp_path):
    """Verify LocalFilesystemStorageBackend and InMemoryObjectStorageBackend operations and traversal blocks."""
    local_backend = LocalFilesystemStorageBackend(str(tmp_path))
    local_backend.write_bytes("TransactionDocument/test_1.pdf", b"%PDF-1.4\ntest\n%%EOF")
    assert local_backend.exists("TransactionDocument/test_1.pdf") is True
    assert local_backend.read_bytes("TransactionDocument/test_1.pdf") == b"%PDF-1.4\ntest\n%%EOF"
    chunks = [c async for c in local_backend.iter_chunks("TransactionDocument/test_1.pdf")]
    assert b"".join(chunks) == b"%PDF-1.4\ntest\n%%EOF"
    assert local_backend.delete_bytes("TransactionDocument/test_1.pdf") is True
    assert local_backend.exists("TransactionDocument/test_1.pdf") is False

    with pytest.raises(HTTPException):
        local_backend.resolve_safe_path("../escape.pdf")

    mem_backend = InMemoryObjectStorageBackend()
    mem_backend.write_bytes("ClaimPhoto/1_Photo.jpg", b"\xff\xd8\xff\xe0JFIF")
    assert mem_backend.exists("ClaimPhoto/1_Photo.jpg") is True
    assert mem_backend.read_bytes("ClaimPhoto/1_Photo.jpg") == b"\xff\xd8\xff\xe0JFIF"

    mem_backend.simulate_read_failure = True
    with pytest.raises(StorageBackendError):
        mem_backend.read_bytes("ClaimPhoto/1_Photo.jpg")
    mem_backend.simulate_read_failure = False

    assert mem_backend.delete_bytes("ClaimPhoto/1_Photo.jpg") is True
    with pytest.raises(FileNotFoundError):
        mem_backend.read_bytes("ClaimPhoto/1_Photo.jpg")


def test_production_storage_isolation_guardrail():
    """Verify Settings blocks production storage identifiers."""
    with pytest.raises(ValueError, match="CRITICAL SAFETY VIOLATION"):
        Settings(LOCAL_STORAGE_ROOT="https://s3.amazonaws.com/brahmainsurance-prod")
