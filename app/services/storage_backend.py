"""
Phase 11 — Storage Backend Abstraction, File Security Validation & Legacy Naming Mapper.

Provides:
1. `StorageBackend` protocol + `LocalFilesystemStorageBackend` + `InMemoryObjectStorageBackend`
2. Strict path-traversal prevention (`Path.resolve().is_relative_to(root)`)
3. Extension, MIME-type, and magic-byte signature validation
4. Legacy virtual folder (`~/TransactionDocument/`, `~/AppPolicyPdf/`, `~/PDF_Files/`,
   `~/QuotationDoc/`, `~/ClaimPhoto/`, `~/Claim_Final_Bill_Doc/`, `~/Clerk/ClaimAudio/`,
   `~/EndorsementDoc/`, `~/AgentDoc/`, `~/POSDoc/`) and filename conventions.
"""
import hashlib
import os
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import AsyncIterator, Dict, Optional, Protocol, Tuple
from fastapi import HTTPException, status

from app.core.config import settings


class StorageBackendError(Exception):
    """Raised when the underlying storage backend fails to read, write, or delete an object."""


class StorageBackend(Protocol):
    """Protocol for pluggable local filesystem or S3/MinIO-compatible object storage."""

    def write_bytes(self, storage_key: str, data: bytes) -> int:
        ...

    def read_bytes(self, storage_key: str) -> bytes:
        ...

    async def iter_chunks(self, storage_key: str, chunk_size: int = 65536) -> AsyncIterator[bytes]:
        ...

    def exists(self, storage_key: str) -> bool:
        ...

    def delete_bytes(self, storage_key: str) -> bool:
        ...

    def get_size(self, storage_key: str) -> int:
        ...


# ---------------------------------------------------------------------------
# 1. File Security, Extension, MIME & Magic-Byte Validation
# ---------------------------------------------------------------------------

FORBIDDEN_EXTENSIONS = frozenset({
    ".exe", ".dll", ".bat", ".cmd", ".ps1", ".sh", ".bash", ".php", ".phtml",
    ".asp", ".aspx", ".ashx", ".asmx", ".cs", ".py", ".pyc", ".pyo", ".rb",
    ".pl", ".cgi", ".jar", ".war", ".jsp", ".jspx", ".js", ".mjs", ".vbs",
    ".scr", ".com", ".msi", ".reg", ".htaccess", ".env", ".html", ".htm",
    ".svg", ".xhtml", ".swf",
})

ALLOWED_EXTENSIONS_TO_MIME: Dict[str, Tuple[str, ...]] = {
    ".pdf": ("application/pdf", "application/x-pdf", "application/octet-stream"),
    ".jpg": ("image/jpeg", "image/jpg", "image/pjpeg", "application/octet-stream"),
    ".jpeg": ("image/jpeg", "image/jpg", "image/pjpeg", "application/octet-stream"),
    ".png": ("image/png", "image/x-png", "application/octet-stream"),
    ".mp3": ("audio/mpeg", "audio/mp3", "audio/x-mp3", "application/octet-stream"),
    ".wav": ("audio/wav", "audio/x-wav", "audio/wave", "application/octet-stream"),
    ".txt": ("text/plain", "application/octet-stream"),
    ".csv": ("text/csv", "text/plain", "application/vnd.ms-excel", "application/octet-stream"),
    ".json": ("application/json", "text/plain", "application/octet-stream"),
}

CANONICAL_MIME_BY_EXT: Dict[str, str] = {
    ".pdf": "application/pdf",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".txt": "text/plain",
    ".csv": "text/csv",
    ".json": "application/json",
}

DANGEROUS_TEXT_PREFIXES = (
    b"MZ",
    b"\x7fELF",
    b"#!",
    b"<?php",
    b"<%@",
    b"<script",
    b"<!DOCTYPE html",
    b"<html",
)

_SAFE_FILENAME_RE = re.compile(r"[^A-Za-z0-9._-]")


def validate_and_sanitize_filename(raw_filename: Optional[str]) -> Tuple[str, str, str]:
    """
    Validates a client-supplied filename against path traversal, null bytes,
    double-extension executable spoofing, and forbidden extensions.

    Returns:
        Tuple of (original_display_name, sanitized_base_name, normalized_ext)
    """
    if not raw_filename or not raw_filename.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required",
        )

    if "\x00" in raw_filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filename: null bytes are not allowed",
        )

    # Reject explicit path traversal or directory separator injection in raw filename
    trimmed = raw_filename.strip()
    if (
        ".." in trimmed
        or "/" in trimmed
        or "\\" in trimmed
        or ":" in trimmed
        or trimmed.startswith(".")
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filename: path traversal or directory components are forbidden",
        )

    if len(trimmed) > 200:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filename: exceeds maximum length of 200 characters",
        )

    parts = trimmed.split(".")
    if len(parts) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filename: file extension is required",
        )

    ext = "." + parts[-1].lower()
    if ext in FORBIDDEN_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Forbidden file extension '{ext}'",
        )

    # Check intermediate extensions for double-extension attacks (e.g. invoice.php.pdf, shell.exe.jpg)
    for sub_part in parts[1:-1]:
        sub_ext = "." + sub_part.lower()
        if sub_ext in FORBIDDEN_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Forbidden double extension '{sub_ext}' detected in filename",
            )

    if ext not in ALLOWED_EXTENSIONS_TO_MIME:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file extension '{ext}'. Allowed: {sorted(ALLOWED_EXTENSIONS_TO_MIME.keys())}",
        )

    stem_raw = ".".join(parts[:-1])
    sanitized_stem = _SAFE_FILENAME_RE.sub("_", stem_raw).strip("._-")
    if not sanitized_stem:
        sanitized_stem = "document"
    sanitized_stem = sanitized_stem[:100]

    sanitized_filename = f"{sanitized_stem}{ext}"
    return trimmed, sanitized_filename, ext


def validate_file_content_and_mime(
    data: bytes,
    ext: str,
    declared_content_type: Optional[str] = None,
    max_size_bytes: Optional[int] = None,
) -> Tuple[str, str]:
    """
    Validates file size, declared MIME type, and binary magic-byte signatures.

    Returns:
        Tuple of (canonical_mime_type, sha256_hex_digest)
    """
    if data is None or len(data) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty (0-byte) files are not permitted",
        )

    limit = max_size_bytes if max_size_bytes is not None else settings.MAX_UPLOAD_SIZE_BYTES
    if len(data) > limit:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size ({len(data)} bytes) exceeds maximum allowed limit ({limit} bytes)",
        )

    # Validate declared Content-Type if provided
    if declared_content_type:
        base_mime = declared_content_type.split(";")[0].strip().lower()
        allowed_mimes = ALLOWED_EXTENSIONS_TO_MIME.get(ext, ())
        if base_mime and base_mime not in allowed_mimes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Content-Type '{base_mime}' does not match file extension '{ext}'",
            )

    # Validate binary magic bytes against extension
    if ext == ".pdf":
        if not data.startswith(b"%PDF-"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid PDF file: missing '%PDF-' magic header",
            )
    elif ext in (".jpg", ".jpeg"):
        if not data.startswith(b"\xff\xd8\xff"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JPEG image: missing JPEG SOI/marker magic bytes",
            )
    elif ext == ".png":
        if not data.startswith(b"\x89PNG\r\n\x1a\n"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid PNG image: missing PNG signature bytes",
            )
    elif ext == ".mp3":
        valid_mp3 = (
            data.startswith(b"ID3")
            or data.startswith(b"\xff\xfb")
            or data.startswith(b"\xff\xf3")
            or data.startswith(b"\xff\xf2")
            or data.startswith(b"\xff\xe3")
        )
        if not valid_mp3:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid MP3 audio file: missing ID3 or MPEG frame sync header",
            )
    elif ext == ".wav":
        if len(data) < 12 or not (data.startswith(b"RIFF") and data[8:12] == b"WAVE"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid WAV audio file: missing RIFF/WAVE header",
            )
    elif ext in (".txt", ".csv", ".json"):
        head_lower = data[:64].lstrip()
        for prefix in DANGEROUS_TEXT_PREFIXES:
            if head_lower.lower().startswith(prefix.lower()):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Malicious or executable content detected in text file",
                )
        if b"\x00" in data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Binary content (null bytes) not allowed in text/csv/json files",
            )

    sha256_hex = hashlib.sha256(data).hexdigest()
    canonical_mime = CANONICAL_MIME_BY_EXT[ext]
    return canonical_mime, sha256_hex


# ---------------------------------------------------------------------------
# 2. Legacy Virtual Directory & Filename Mapping
# ---------------------------------------------------------------------------

VALID_DOCUMENT_TYPES = frozenset({
    "POLICY",
    "QUOTATION",
    "CLAIM",
    "ENDORSEMENT",
    "CUSTOMER",
    "VEHICLE",
    "PAYMENT",
    "CHEQUE",
    "COMMISSION",
    "SUPPORT",
    "KYC",
    "POSP",
    "AGENT",
    "FRANCHISE",
    "INVOICE",
    "REPORT",
    "OTHER",
})


def resolve_legacy_virtual_folder(document_type: str, doc_sub_type: Optional[str] = None) -> str:
    """
    Maps (document_type, doc_sub_type) to the exact legacy virtual directory
    confirmed in `docs/migration/17_legacy_document_file_baseline.md`.
    """
    dtype = (document_type or "OTHER").strip().upper()
    sub = (doc_sub_type or "").strip().upper()

    if dtype == "POLICY":
        if sub in ("APPPOLICYPDF", "APP_POLICY_PDF", "MOBILE_POLICY_PDF"):
            return "AppPolicyPdf"
        return "TransactionDocument"

    if dtype == "QUOTATION":
        if sub in ("QUOTATIONPDF", "QUOTATION_PDF", "GENERATED_PDF", "PDF"):
            return "PDF_Files"
        return "QuotationDoc"

    if dtype == "CLAIM":
        if sub in ("FINAL_BILL_DOC", "FINALBILLDOC", "FINAL_BILL", "FINALBILL"):
            return "Claim_Final_Bill_Doc"
        if sub in ("CLAIM_AUDIO", "CLAIMAUDIO", "AUDIOFILE", "AUDIO"):
            return "ClaimAudio"
        if sub in ("REPAIR_QUOTATION_IMG", "REPAIRQUOTATIONIMG", "CLAIM_QUOTATION_IMG"):
            return "QuotationDoc"
        return "ClaimPhoto"

    if dtype == "ENDORSEMENT":
        return "EndorsementDoc"

    if dtype == "POSP":
        return "POSDoc"

    if dtype in ("AGENT", "KYC"):
        return "AgentDoc"

    return "TransactionDocument"


def build_stored_filename_and_key(
    *,
    document_type: str,
    doc_sub_type: Optional[str],
    entity_type: str,
    entity_id: Optional[int],
    sanitized_filename: str,
    ext: str,
    policy_no: Optional[str] = None,
    now: Optional[datetime] = None,
) -> Tuple[str, str, str]:
    """
    Generates a deterministic, collision-safe `stored_filename` and canonical `storage_key`
    preserving legacy naming patterns while preventing file overwrites (`DEF-010`).

    Returns:
        Tuple of (legacy_virtual_folder, stored_filename, storage_key)
    """
    ts = (now or datetime.utcnow()).strftime("%Y%m%d%H%M%S")
    uid8 = uuid.uuid4().hex[:8]
    eid = entity_id if entity_id is not None else 0
    folder = resolve_legacy_virtual_folder(document_type, doc_sub_type)
    dtype = (document_type or "OTHER").strip().upper()
    sub_clean = _SAFE_FILENAME_RE.sub("_", (doc_sub_type or dtype)).strip("_")[:40] or dtype

    if folder == "AppPolicyPdf":
        pol_clean = _SAFE_FILENAME_RE.sub("_", (policy_no or f"Trans_{eid}")).strip("_")[:50]
        stored_filename = f"{pol_clean}_{uid8}_Policy{ext}"
    elif folder == "PDF_Files":
        stored_filename = f"Quotation_{eid}_{uid8}{ext}"
    elif folder in ("ClaimPhoto", "Claim_Final_Bill_Doc"):
        stored_filename = f"{eid}_{ts}_Img_{uid8}{ext}"
    elif folder == "ClaimAudio":
        stored_filename = f"{ts}_{uid8}{ext}"
    elif folder == "EndorsementDoc":
        stored_filename = f"{eid}_{uid8}_{sanitized_filename}"
    elif folder in ("AgentDoc", "POSDoc"):
        stored_filename = f"{eid}_{sub_clean}_{uid8}{ext}"
    else:
        stored_filename = f"{eid}_{sub_clean}_{uid8}_{sanitized_filename}"

    entity_slug = _SAFE_FILENAME_RE.sub("_", (entity_type or dtype).lower()).strip("_") or "other"
    storage_key = f"{folder}/{entity_slug}/{eid}/{stored_filename}"
    return folder, stored_filename, storage_key


# ---------------------------------------------------------------------------
# 3. Local Filesystem Storage Backend (with Path Traversal Protection)
# ---------------------------------------------------------------------------

class LocalFilesystemStorageBackend:
    """
    Local disk storage provider rooted at `settings.LOCAL_STORAGE_ROOT`.
    Enforces strict path containment so no key can escape `base_dir`.
    """

    def __init__(self, root_dir: Optional[str] = None) -> None:
        raw_root = root_dir or settings.LOCAL_STORAGE_ROOT
        self.base_dir: Path = Path(raw_root).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.simulate_write_failure: bool = False
        self.simulate_read_failure: bool = False

    def resolve_safe_path(self, storage_key: str) -> Path:
        """
        Resolves `storage_key` relative to `self.base_dir` and verifies that the
        resulting path is strictly inside `self.base_dir`.
        """
        if not storage_key or not storage_key.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid empty storage key",
            )
        if "\x00" in storage_key:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Null byte in storage key is forbidden",
            )

        cleaned = storage_key.strip().replace("\\", "/")
        if cleaned.startswith("/") or ":" in cleaned or ".." in cleaned.split("/"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Path traversal or absolute storage key is forbidden",
            )

        candidate = (self.base_dir / cleaned).resolve()
        try:
            is_inside = candidate.is_relative_to(self.base_dir)
        except AttributeError:
            is_inside = str(candidate).startswith(str(self.base_dir) + os.sep)

        if not is_inside or candidate == self.base_dir:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Security violation: storage key resolves outside storage root",
            )
        return candidate

    def write_bytes(self, storage_key: str, data: bytes) -> int:
        if self.simulate_write_failure:
            raise StorageBackendError("Simulated storage write failure")
        target = self.resolve_safe_path(storage_key)
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            return len(data)
        except OSError as exc:
            raise StorageBackendError(f"Failed to write object '{storage_key}': {exc}") from exc

    def read_bytes(self, storage_key: str) -> bytes:
        if self.simulate_read_failure:
            raise StorageBackendError("Simulated storage read failure")
        target = self.resolve_safe_path(storage_key)
        if not target.is_file():
            raise FileNotFoundError(f"Object not found in storage: {storage_key}")
        try:
            return target.read_bytes()
        except OSError as exc:
            raise StorageBackendError(f"Failed to read object '{storage_key}': {exc}") from exc

    async def iter_chunks(self, storage_key: str, chunk_size: int = 65536) -> AsyncIterator[bytes]:
        if self.simulate_read_failure:
            raise StorageBackendError("Simulated storage stream failure")
        target = self.resolve_safe_path(storage_key)
        if not target.is_file():
            raise FileNotFoundError(f"Object not found in storage: {storage_key}")
        with target.open("rb") as fh:
            while True:
                chunk = fh.read(chunk_size)
                if not chunk:
                    break
                yield chunk

    def exists(self, storage_key: str) -> bool:
        try:
            target = self.resolve_safe_path(storage_key)
            return target.is_file()
        except HTTPException:
            return False

    def delete_bytes(self, storage_key: str) -> bool:
        target = self.resolve_safe_path(storage_key)
        if target.is_file():
            target.unlink()
            return True
        return False

    def get_size(self, storage_key: str) -> int:
        target = self.resolve_safe_path(storage_key)
        if not target.is_file():
            raise FileNotFoundError(f"Object not found in storage: {storage_key}")
        return target.stat().st_size


# ---------------------------------------------------------------------------
# 4. In-Memory / Mock S3-Compatible Object Storage Backend
# ---------------------------------------------------------------------------

class InMemoryObjectStorageBackend:
    """
    S3/MinIO-compatible in-memory object store for unit/integration testing
    and storage-failure simulation without external network dependencies.
    """

    def __init__(self) -> None:
        self._objects: Dict[str, bytes] = {}
        self.simulate_write_failure: bool = False
        self.simulate_read_failure: bool = False

    def _validate_key(self, storage_key: str) -> str:
        if not storage_key or not storage_key.strip() or "\x00" in storage_key:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid storage key",
            )
        cleaned = storage_key.strip().replace("\\", "/")
        if cleaned.startswith("/") or ":" in cleaned or ".." in cleaned.split("/"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Path traversal or absolute storage key is forbidden",
            )
        return cleaned

    def write_bytes(self, storage_key: str, data: bytes) -> int:
        if self.simulate_write_failure:
            raise StorageBackendError("Simulated S3/object storage write failure")
        key = self._validate_key(storage_key)
        self._objects[key] = bytes(data)
        return len(data)

    def read_bytes(self, storage_key: str) -> bytes:
        if self.simulate_read_failure:
            raise StorageBackendError("Simulated S3/object storage read failure")
        key = self._validate_key(storage_key)
        if key not in self._objects:
            raise FileNotFoundError(f"Object not found in storage: {key}")
        return self._objects[key]

    async def iter_chunks(self, storage_key: str, chunk_size: int = 65536) -> AsyncIterator[bytes]:
        data = self.read_bytes(storage_key)
        for offset in range(0, len(data), chunk_size):
            yield data[offset : offset + chunk_size]

    def exists(self, storage_key: str) -> bool:
        try:
            key = self._validate_key(storage_key)
            return key in self._objects
        except HTTPException:
            return False

    def delete_bytes(self, storage_key: str) -> bool:
        key = self._validate_key(storage_key)
        if key in self._objects:
            del self._objects[key]
            return True
        return False

    def get_size(self, storage_key: str) -> int:
        data = self.read_bytes(storage_key)
        return len(data)


_default_storage_backend: Optional[StorageBackend] = None


def get_storage_backend() -> StorageBackend:
    """Returns the singleton configured StorageBackend instance."""
    global _default_storage_backend
    if _default_storage_backend is None:
        if settings.STORAGE_BACKEND.lower() in ("memory", "s3_mock"):
            _default_storage_backend = InMemoryObjectStorageBackend()
        else:
            _default_storage_backend = LocalFilesystemStorageBackend(settings.LOCAL_STORAGE_ROOT)
    return _default_storage_backend


def set_storage_backend(backend: Optional[StorageBackend]) -> None:
    """Allows tests to inject a custom or failure-simulating StorageBackend."""
    global _default_storage_backend
    _default_storage_backend = backend
