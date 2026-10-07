"""
FastAPI v1 Endpoints for Phase 11 — Document, File Handling, Download, ZIP & Webhook Engine.

Exposes:
1. `documents_router` (`/api/v1/documents`):
   - `POST /api/v1/documents/upload`
   - `GET /api/v1/documents/{document_id}`
   - `GET /api/v1/documents/{document_id}/download`
   - `DELETE /api/v1/documents/{document_id}`
   - `POST /api/v1/documents/{document_id}/replace`
   - `POST /api/v1/documents/zip`
   - `GET /api/v1/documents/legacy/DownloadAll.ashx`
   - `GET /api/v1/documents/legacy/ImageHandler.ashx`
   - `POST /api/v1/documents/webhooks/policy-parser`
2. `entity_documents_router` (mounted at `/api/v1`):
   - `GET /api/v1/policies/{policy_id}/documents`
   - `GET /api/v1/policies/{policy_id}/documents/zip`
   - `GET /api/v1/quotations/{quotation_id}/documents`
   - `POST /api/v1/quotations/{quotation_id}/generate-pdf`
   - `GET /api/v1/claims/{claim_id}/documents/zip`
   - `GET /api/v1/endorsements/{endorsement_id}/documents`
   - `GET /api/v1/customers/{customer_id}/documents`
   - `GET /api/v1/vehicles/{vehicle_id}/documents`
"""
import io
import json
from typing import Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Header,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import StreamingResponse
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db, require_roles
from app.core.rbac import (
    DOCUMENT_DELETE_REPLACE_ROLES,
    DOCUMENT_READ_ROLES,
    DOCUMENT_UPLOAD_ROLES,
)
from app.models.user import User
from app.schemas.document import (
    APIResponse,
    DocumentListResponse,
    DocumentMetadataResponse,
    DocumentZipRequest,
    PolicyParserWebhookRequest,
    PolicyParserWebhookResponse,
)
from app.services.document_service import DocumentService


documents_router = APIRouter()
entity_documents_router = APIRouter()


# ===========================================================================
# 1. Core Document Endpoints (`/api/v1/documents`)
# ===========================================================================

@documents_router.post(
    "/upload",
    response_model=APIResponse[DocumentMetadataResponse],
    status_code=status.HTTP_201_CREATED,
)
async def upload_document_endpoint(
    response: Response,
    file: UploadFile = File(...),
    document_type: str = Form(...),
    doc_sub_type: Optional[str] = Form(default=None),
    entity_type: Optional[str] = Form(default=None),
    entity_id: Optional[int] = Form(default=None),
    transaction_id: Optional[int] = Form(default=None),
    quotation_id: Optional[int] = Form(default=None),
    claim_id: Optional[int] = Form(default=None),
    endorsement_id: Optional[int] = Form(default=None),
    customer_id: Optional[int] = Form(default=None),
    vehicle_id: Optional[int] = Form(default=None),
    payment_id: Optional[int] = Form(default=None),
    policy_no: Optional[str] = Form(default=None),
    remarks: Optional[str] = Form(default=None),
    idempotency_key_form: Optional[str] = Form(default=None, alias="idempotency_key"),
    idempotency_key_header: Optional[str] = Header(default=None, alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*DOCUMENT_UPLOAD_ROLES)),
) -> APIResponse[DocumentMetadataResponse]:
    raw_bytes = await file.read()
    effective_idem = idempotency_key_header or idempotency_key_form
    svc = DocumentService(db)
    data, is_new = await svc.upload_document(
        current_user,
        file_bytes=raw_bytes,
        raw_filename=file.filename,
        declared_content_type=file.content_type,
        document_type=document_type,
        doc_sub_type=doc_sub_type,
        entity_type=entity_type,
        entity_id=entity_id,
        transaction_id=transaction_id,
        quotation_id=quotation_id,
        claim_id=claim_id,
        endorsement_id=endorsement_id,
        customer_id=customer_id,
        vehicle_id=vehicle_id,
        payment_id=payment_id,
        policy_no=policy_no,
        remarks=remarks,
        idempotency_key=effective_idem,
    )
    if not is_new:
        response.status_code = status.HTTP_200_OK
    return APIResponse(
        success=True,
        message="Document uploaded successfully" if is_new else "Idempotent document upload replay returned",
        data=data,
    )


@documents_router.get(
    "/{document_id}",
    response_model=APIResponse[DocumentMetadataResponse],
)
async def get_document_metadata_endpoint(
    document_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*DOCUMENT_READ_ROLES)),
) -> APIResponse[DocumentMetadataResponse]:
    svc = DocumentService(db)
    data = await svc.get_document_metadata(current_user, document_id)
    return APIResponse(
        success=True,
        message="Document metadata retrieved successfully",
        data=data,
    )


@documents_router.get("/{document_id}/download")
async def download_document_endpoint(
    document_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*DOCUMENT_READ_ROLES)),
) -> StreamingResponse:
    svc = DocumentService(db)
    doc, content = await svc.open_document_download(current_user, document_id)
    safe_disp_name = (doc.OriginalFileName or doc.StoredFileName).replace('"', "").replace("\r", "").replace("\n", "")
    headers = {
        "Content-Disposition": f'attachment; filename="{safe_disp_name}"',
        "Content-Length": str(len(content)),
        "X-Content-Type-Options": "nosniff",
        "X-Document-Id": str(doc.DocumentId),
        "X-Document-SHA256": doc.ChecksumSha256,
    }
    return StreamingResponse(
        io.BytesIO(content),
        media_type=doc.MimeType,
        headers=headers,
    )


@documents_router.delete(
    "/{document_id}",
    response_model=APIResponse[DocumentMetadataResponse],
)
async def delete_document_endpoint(
    document_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*DOCUMENT_DELETE_REPLACE_ROLES)),
) -> APIResponse[DocumentMetadataResponse]:
    svc = DocumentService(db)
    data = await svc.delete_document(current_user, document_id)
    return APIResponse(
        success=True,
        message="Document soft-deleted successfully",
        data=data,
    )


@documents_router.post(
    "/{document_id}/replace",
    response_model=APIResponse[DocumentMetadataResponse],
)
async def replace_document_endpoint(
    document_id: int,
    file: UploadFile = File(...),
    doc_sub_type: Optional[str] = Form(default=None),
    remarks: Optional[str] = Form(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*DOCUMENT_DELETE_REPLACE_ROLES)),
) -> APIResponse[DocumentMetadataResponse]:
    raw_bytes = await file.read()
    svc = DocumentService(db)
    data = await svc.replace_document(
        current_user,
        document_id,
        file_bytes=raw_bytes,
        raw_filename=file.filename,
        declared_content_type=file.content_type,
        doc_sub_type=doc_sub_type,
        remarks=remarks,
    )
    return APIResponse(
        success=True,
        message="Document replaced with new version successfully",
        data=data,
    )


@documents_router.post("/zip")
async def build_documents_zip_endpoint(
    payload: DocumentZipRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*DOCUMENT_READ_ROLES)),
) -> StreamingResponse:
    svc = DocumentService(db)
    zip_bytes, archive_filename, included_count, missing_count = await svc.build_zip_archive(
        current_user,
        payload,
    )
    headers = {
        "Content-Disposition": f'attachment; filename="{archive_filename}"',
        "Content-Length": str(len(zip_bytes)),
        "X-Content-Type-Options": "nosniff",
        "X-Included-File-Count": str(included_count),
        "X-Missing-File-Count": str(missing_count),
    }
    return StreamingResponse(
        io.BytesIO(zip_bytes),
        media_type="application/zip",
        headers=headers,
    )


# ===========================================================================
# 2. Legacy Handler Compatibility Endpoints (`DownloadAll.ashx`, `ImageHandler.ashx`)
# ===========================================================================

@documents_router.get("/legacy/DownloadAll.ashx")
async def legacy_download_all_ashx_endpoint(
    TransId: str = Query(..., description="Legacy TransId (integer or base64 token)"),
    PolicyNo: Optional[str] = Query(default=None, description="Legacy PolicyNo for ZIP filename"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*DOCUMENT_READ_ROLES)),
) -> StreamingResponse:
    svc = DocumentService(db)
    parsed_tid = svc._parse_legacy_trans_id(TransId)
    zip_req = DocumentZipRequest(
        transaction_id=parsed_tid,
        policy_no=PolicyNo,
    )
    zip_bytes, archive_filename, included_count, missing_count = await svc.build_zip_archive(
        current_user,
        zip_req,
    )
    headers = {
        "Content-Disposition": f'attachment; filename="{archive_filename}"',
        "Content-Length": str(len(zip_bytes)),
        "X-Content-Type-Options": "nosniff",
        "X-Included-File-Count": str(included_count),
        "X-Missing-File-Count": str(missing_count),
    }
    return StreamingResponse(
        io.BytesIO(zip_bytes),
        media_type="application/zip",
        headers=headers,
    )


@documents_router.get("/legacy/ImageHandler.ashx")
async def legacy_image_handler_ashx_endpoint(
    Id: int = Query(..., gt=0, description="DocumentId or legacy ClaimDocId"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*DOCUMENT_READ_ROLES)),
) -> StreamingResponse:
    svc = DocumentService(db)
    data, mime_type, filename = await svc.legacy_image_handler_stream(current_user, Id)
    safe_name = (filename or f"image_{Id}").replace('"', "").replace("\r", "").replace("\n", "")
    headers = {
        "Content-Disposition": f'inline; filename="{safe_name}"',
        "Content-Length": str(len(data)),
        "X-Content-Type-Options": "nosniff",
    }
    return StreamingResponse(
        io.BytesIO(data),
        media_type=mime_type,
        headers=headers,
    )


# ===========================================================================
# 3. HiCaliber Policy PDF Parser Webhook (`PolicyParserWebhook.aspx.cs`)
# ===========================================================================

@documents_router.post(
    "/webhooks/policy-parser",
    response_model=APIResponse[PolicyParserWebhookResponse],
    status_code=status.HTTP_201_CREATED,
)
async def policy_parser_webhook_endpoint(
    request: Request,
    response: Response,
    x_webhook_secret: Optional[str] = Header(default=None, alias="X-Webhook-Secret"),
    x_calliber_signature: Optional[str] = Header(default=None, alias="X-Calliber-Signature"),
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[PolicyParserWebhookResponse]:
    raw_body = await request.body()
    svc = DocumentService(db)
    svc.verify_webhook_signature_or_secret(
        raw_body=raw_body,
        webhook_secret_header=x_webhook_secret,
        hmac_signature_header=x_calliber_signature,
    )

    try:
        json_obj = json.loads(raw_body.decode("utf-8"))
        if not isinstance(json_obj, dict):
            raise ValueError("Webhook body must be a JSON object")
        parsed_payload = PolicyParserWebhookRequest.model_validate(json_obj)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Malformed JSON webhook payload: {exc}",
        ) from exc
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=exc.errors(),
        ) from exc

    data, is_new = await svc.process_policy_parser_webhook(
        parsed_payload,
        raw_body=raw_body,
        idempotency_key_header=idempotency_key,
    )
    if not is_new:
        response.status_code = status.HTTP_200_OK
    return APIResponse(
        success=True,
        message="Policy parser webhook processed successfully" if is_new else "Idempotent webhook replay returned",
        data=data,
    )


# ===========================================================================
# 4. Entity-Scoped Document Endpoints
# ===========================================================================

@entity_documents_router.get(
    "/policies/{policy_id}/documents",
    response_model=APIResponse[DocumentListResponse],
    tags=["documents", "policies"],
)
async def list_policy_documents_endpoint(
    policy_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*DOCUMENT_READ_ROLES)),
) -> APIResponse[DocumentListResponse]:
    svc = DocumentService(db)
    data = await svc.list_entity_documents(
        current_user,
        entity_type="POLICY",
        entity_id=policy_id,
    )
    return APIResponse(
        success=True,
        message="Policy documents retrieved successfully",
        data=data,
    )


@entity_documents_router.get(
    "/policies/{policy_id}/documents/zip",
    tags=["documents", "policies"],
)
async def download_policy_documents_zip_endpoint(
    policy_id: int,
    policy_no: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*DOCUMENT_READ_ROLES)),
) -> StreamingResponse:
    svc = DocumentService(db)
    zip_req = DocumentZipRequest(
        transaction_id=policy_id,
        policy_no=policy_no,
    )
    zip_bytes, archive_filename, included_count, missing_count = await svc.build_zip_archive(
        current_user,
        zip_req,
    )
    headers = {
        "Content-Disposition": f'attachment; filename="{archive_filename}"',
        "Content-Length": str(len(zip_bytes)),
        "X-Content-Type-Options": "nosniff",
        "X-Included-File-Count": str(included_count),
        "X-Missing-File-Count": str(missing_count),
    }
    return StreamingResponse(
        io.BytesIO(zip_bytes),
        media_type="application/zip",
        headers=headers,
    )


@entity_documents_router.get(
    "/quotations/{quotation_id}/documents",
    response_model=APIResponse[DocumentListResponse],
    tags=["documents", "quotations"],
)
async def list_quotation_documents_endpoint(
    quotation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*DOCUMENT_READ_ROLES)),
) -> APIResponse[DocumentListResponse]:
    svc = DocumentService(db)
    data = await svc.list_entity_documents(
        current_user,
        entity_type="QUOTATION",
        entity_id=quotation_id,
    )
    return APIResponse(
        success=True,
        message="Quotation documents retrieved successfully",
        data=data,
    )


@entity_documents_router.post(
    "/quotations/{quotation_id}/generate-pdf",
    response_model=APIResponse[DocumentMetadataResponse],
    status_code=status.HTTP_201_CREATED,
    tags=["documents", "quotations"],
)
async def generate_quotation_pdf_endpoint(
    quotation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*DOCUMENT_UPLOAD_ROLES)),
) -> APIResponse[DocumentMetadataResponse]:
    svc = DocumentService(db)
    data = await svc.generate_quotation_pdf(current_user, quotation_id)
    return APIResponse(
        success=True,
        message="Quotation PDF generated successfully",
        data=data,
    )


@entity_documents_router.get(
    "/claims/{claim_id}/documents/zip",
    tags=["documents", "claims"],
)
async def download_claim_documents_zip_endpoint(
    claim_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*DOCUMENT_READ_ROLES)),
) -> StreamingResponse:
    svc = DocumentService(db)
    zip_req = DocumentZipRequest(
        entity_type="CLAIM",
        entity_id=claim_id,
    )
    zip_bytes, archive_filename, included_count, missing_count = await svc.build_zip_archive(
        current_user,
        zip_req,
    )
    headers = {
        "Content-Disposition": f'attachment; filename="{archive_filename}"',
        "Content-Length": str(len(zip_bytes)),
        "X-Content-Type-Options": "nosniff",
        "X-Included-File-Count": str(included_count),
        "X-Missing-File-Count": str(missing_count),
    }
    return StreamingResponse(
        io.BytesIO(zip_bytes),
        media_type="application/zip",
        headers=headers,
    )


@entity_documents_router.get(
    "/endorsements/{endorsement_id}/documents",
    response_model=APIResponse[DocumentListResponse],
    tags=["documents", "endorsements"],
)
async def list_endorsement_documents_endpoint(
    endorsement_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*DOCUMENT_READ_ROLES)),
) -> APIResponse[DocumentListResponse]:
    svc = DocumentService(db)
    data = await svc.list_entity_documents(
        current_user,
        entity_type="ENDORSEMENT",
        entity_id=endorsement_id,
    )
    return APIResponse(
        success=True,
        message="Endorsement documents retrieved successfully",
        data=data,
    )


@entity_documents_router.get(
    "/customers/{customer_id}/documents",
    response_model=APIResponse[DocumentListResponse],
    tags=["documents", "customers"],
)
async def list_customer_documents_endpoint(
    customer_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*DOCUMENT_READ_ROLES)),
) -> APIResponse[DocumentListResponse]:
    svc = DocumentService(db)
    data = await svc.list_entity_documents(
        current_user,
        entity_type="CUSTOMER",
        entity_id=customer_id,
    )
    return APIResponse(
        success=True,
        message="Customer documents retrieved successfully",
        data=data,
    )


@entity_documents_router.get(
    "/vehicles/{vehicle_id}/documents",
    response_model=APIResponse[DocumentListResponse],
    tags=["documents", "vehicles"],
)
async def list_vehicle_documents_endpoint(
    vehicle_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*DOCUMENT_READ_ROLES)),
) -> APIResponse[DocumentListResponse]:
    svc = DocumentService(db)
    data = await svc.list_entity_documents(
        current_user,
        entity_type="VEHICLE",
        entity_id=vehicle_id,
    )
    return APIResponse(
        success=True,
        message="Vehicle documents retrieved successfully",
        data=data,
    )
