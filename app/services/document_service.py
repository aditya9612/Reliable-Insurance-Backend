"""
Phase 11 — Document, File Handling, Storage, Download, ZIP & Policy Parser Webhook Service.

Implements:
- Unified additive document storage (`tbl_documents`) with atomic dual-write to legacy tables:
  - `tbl_claimdocument` (`ClaimDocument`)
  - `tbl_appendorsement.SupportingDocKey` (`PolicyEndorsement`)
  - `tbl_app_requestedquotationfile` (`AppRequestedQuotationFile`)
  - `tbl_insurancecompanyquotation` (`InsuranceCompanyQuotation`)
  - `tbl_app_quotationrequest` (`AppQuotationRequest`)
  - `tbl_transaction` (`CustDocStatus`, `calliber_policyId`, `calliber_UpdateBy`)
  - `tbl_transactionappnew` (`FileUpload`, `FileNameForPdf`)
- `DEF-010` remediation: canonical `StorageKey` per document version; replacing a Claim Final Bill
  document in `Claim_Final_Bill_Doc/` never deletes or touches files in `ClaimPhoto/`.
- Strict RBAC, branch, and principal ownership enforcement (`PrincipalContext`).
- Legacy compatibility for `DownloadAll.ashx` (`Files/` ZIP layout), `ImageHandler.ashx`,
  and `PolicyParserWebhook.aspx` (with `INTENTIONAL HARDENING` HMAC/secret verification).
"""
import base64
import hashlib
import hmac
import io
import json
import re
import uuid
import zipfile
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.rbac import (
    AGENT_PRINCIPAL_ROLES,
    EMPLOYEE_PRINCIPAL_ROLES,
    FRANCHISE_PRINCIPAL_ROLES,
    PrincipalContext,
    is_global_admin_role,
    is_global_read_role,
    is_quotation_coordinator_role,
)
from app.models.claims_endorsement import Claim, ClaimDocument, PolicyEndorsement
from app.models.customer import Customer
from app.models.document import DocumentRecord, PolicyParserWebhookRecord
from app.models.payment import TransactionPayment
from app.models.quotation import (
    AppQuatationEntry,
    AppQuotationRequest,
    AppRequestedQuotationFile,
    InsuranceCompanyQuotation,
)
from app.models.transaction import Transaction
from app.models.transaction_app import TransactionAppNew
from app.models.user import User
from app.models.vehicle import VehicleDetails
from app.schemas.document import (
    DocumentListResponse,
    DocumentMetadataResponse,
    DocumentZipRequest,
    PolicyParserWebhookRequest,
    PolicyParserWebhookResponse,
)
from app.services.storage_backend import (
    StorageBackend,
    StorageBackendError,
    VALID_DOCUMENT_TYPES,
    build_stored_filename_and_key,
    get_storage_backend,
    validate_and_sanitize_filename,
    validate_file_content_and_mime,
)

_SAFE_ZIP_NAME_RE = re.compile(r"[^A-Za-z0-9._-]")


class DocumentService:
    """Service orchestrating Phase 11 document storage, authorization, ZIPs, and webhooks."""

    def __init__(
        self,
        session: AsyncSession,
        storage: Optional[StorageBackend] = None,
    ) -> None:
        self.session = session
        self.storage: StorageBackend = storage or get_storage_backend()

    # -----------------------------------------------------------------------
    # 1. Principal & Entity Authorization Helpers
    # -----------------------------------------------------------------------

    @staticmethod
    def _get_principal(current_user: User) -> PrincipalContext:
        ctx = getattr(current_user, "principal_context", None)
        if isinstance(ctx, PrincipalContext):
            return ctx
        return PrincipalContext(
            user_id=current_user.UserId,
            username=getattr(current_user, "UserName", None),
            role_id=getattr(current_user, "UserRoleId", None),
            role_name=getattr(current_user, "role_name", None),
            branch_id=getattr(current_user, "BranchId", None),
            agent_id=getattr(current_user, "agent_id", None),
            emp_id=getattr(current_user, "emp_id", None),
            employee_id=getattr(current_user, "employee_id", None),
            franchise_id=getattr(current_user, "franchise_id", None),
        )

    @staticmethod
    def _norm_role(role_name: Optional[str]) -> str:
        return (role_name or "").strip().upper()

    def _assert_not_restricted_role_for_entity(
        self,
        principal: PrincipalContext,
        entity_type: str,
        is_write: bool,
    ) -> None:
        norm_role = self._norm_role(principal.role_name)
        if norm_role == "POLICY VIEW" and is_write:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Read-only role 'pOLICY VIEW' is not permitted to upload, replace, or delete documents",
            )
        if norm_role == "HR" and entity_type.upper() in (
            "POLICY",
            "CLAIM",
            "ENDORSEMENT",
            "PAYMENT",
            "CHEQUE",
            "COMMISSION",
            "QUOTATION",
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role 'HR' is not permitted to access {entity_type} documents",
            )

    def _check_ownership_and_branch_scope(
        self,
        principal: PrincipalContext,
        *,
        entity_type: str,
        branch_id: Optional[int],
        agent_id: Optional[int],
        franchise_id: Optional[int],
        sales_ex_id: Optional[int],
        created_by_user_id: Optional[int] = None,
        is_write: bool = False,
    ) -> None:
        """
        Enforces server-resolved RBAC, branch jurisdiction, and principal ownership.
        """
        self._assert_not_restricted_role_for_entity(principal, entity_type, is_write=is_write)
        role_name = principal.role_name
        norm_role = self._norm_role(role_name)

        # Global Admins have cross-branch authority
        if is_global_admin_role(role_name) or norm_role == "SHREYANSH OWNER":
            return

        # Global Read roles (ACCOUNT, ACCOUNT HEAD) have cross-branch read authority
        # and write authority on payment/commission/endorsement/policy accounting docs
        if is_global_read_role(role_name):
            if not is_write or entity_type.upper() in ("PAYMENT", "CHEQUE", "COMMISSION", "POLICY", "ENDORSEMENT", "CLAIM"):
                return

        # Global Quotation Coordinators have cross-branch authority on QUOTATION documents
        if entity_type.upper() == "QUOTATION" and is_quotation_coordinator_role(role_name):
            return

        # Agent Principal Isolation
        agent_roles_upper = {r.upper() for r in AGENT_PRINCIPAL_ROLES}
        if norm_role in agent_roles_upper:
            if created_by_user_id is not None and created_by_user_id == principal.user_id and agent_id is None:
                return
            if principal.agent_id is not None and agent_id is not None and principal.agent_id == agent_id:
                return
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: document or parent entity belongs to a different Agent principal",
            )

        # Franchise Principal Isolation
        franchise_roles_upper = {r.upper() for r in FRANCHISE_PRINCIPAL_ROLES}
        if norm_role in franchise_roles_upper:
            if franchise_id is not None and principal.franchise_id is not None:
                if principal.franchise_id != franchise_id:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Access denied: document or parent entity belongs to a different Franchise principal",
                    )
                return
            if branch_id is not None and principal.branch_id is not None and branch_id != principal.branch_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: cross-branch access is not permitted for Franchise role",
                )
            if created_by_user_id is not None and created_by_user_id != principal.user_id and franchise_id is None and branch_id is None:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: document does not belong to current Franchise principal",
                )
            return

        # Employee / Sales Executive Principal Isolation
        employee_roles_upper = {r.upper() for r in EMPLOYEE_PRINCIPAL_ROLES}
        if norm_role in employee_roles_upper:
            if sales_ex_id is not None and principal.emp_id is not None:
                if principal.emp_id != sales_ex_id:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Access denied: document or parent entity belongs to a different Sales Executive principal",
                    )
            if branch_id is not None and principal.branch_id is not None and branch_id > 0 and principal.branch_id > 0:
                if branch_id != principal.branch_id:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Access denied: cross-branch document access is not permitted",
                    )
            return

        # Standard Branch-Scoped Operational Roles (OPERATOR, CASHIER, CLAIM, ENDORSEMENT, etc.)
        if (
            branch_id is not None
            and principal.branch_id is not None
            and branch_id > 0
            and principal.branch_id > 0
            and branch_id != principal.branch_id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: entity BranchId ({branch_id}) is outside user BranchId ({principal.branch_id})",
            )

    async def _resolve_entity_context(
        self,
        *,
        entity_type: str,
        entity_id: Optional[int] = None,
        transaction_id: Optional[int] = None,
        quotation_id: Optional[int] = None,
        claim_id: Optional[int] = None,
        endorsement_id: Optional[int] = None,
        customer_id: Optional[int] = None,
        vehicle_id: Optional[int] = None,
        payment_id: Optional[int] = None,
        policy_no: Optional[str] = None,
        principal: PrincipalContext,
        is_write: bool = False,
    ) -> Dict[str, Any]:
        """
        Resolves parent entity metadata from the local database and enforces
        object-level / branch / principal access control.
        """
        etype = (entity_type or "OTHER").strip().upper()
        ctx: Dict[str, Any] = {
            "entity_type": etype,
            "entity_id": entity_id,
            "transaction_id": transaction_id,
            "policy_no": policy_no,
            "quotation_id": quotation_id,
            "claim_id": claim_id,
            "endorsement_id": endorsement_id,
            "customer_id": customer_id,
            "vehicle_id": vehicle_id,
            "payment_id": payment_id,
            "branch_id": principal.branch_id,
            "agent_id": principal.agent_id,
            "franchise_id": principal.franchise_id,
            "sales_ex_id": principal.emp_id,
        }

        if etype == "CLAIM" or claim_id is not None:
            cid = claim_id if claim_id is not None else entity_id
            if cid is None:
                raise HTTPException(status_code=400, detail="claim_id or entity_id is required for CLAIM documents")
            claim = (
                await self.session.execute(
                    select(Claim).where(Claim.ClaimId == cid, Claim.isdeleted == "0")
                )
            ).scalar_one_or_none()
            if not claim:
                raise HTTPException(status_code=404, detail=f"Claim {cid} not found")
            self._check_ownership_and_branch_scope(
                principal,
                entity_type="CLAIM",
                branch_id=claim.BranchId,
                agent_id=claim.AgentId,
                franchise_id=claim.FranchiseId,
                sales_ex_id=claim.SalesExId,
                created_by_user_id=claim.CreateUser,
                is_write=is_write,
            )
            ctx.update({
                "entity_type": "CLAIM",
                "entity_id": claim.ClaimId,
                "claim_id": claim.ClaimId,
                "transaction_id": claim.TransanctionId,
                "policy_no": claim.PolicyNo or policy_no,
                "customer_id": claim.CustomerId,
                "vehicle_id": claim.CustVehId,
                "branch_id": claim.BranchId,
                "agent_id": claim.AgentId,
                "franchise_id": claim.FranchiseId,
                "sales_ex_id": claim.SalesExId,
            })
            return ctx

        if etype == "ENDORSEMENT" or endorsement_id is not None:
            eid = endorsement_id if endorsement_id is not None else entity_id
            if eid is None:
                raise HTTPException(status_code=400, detail="endorsement_id or entity_id is required for ENDORSEMENT documents")
            endo = (
                await self.session.execute(
                    select(PolicyEndorsement).where(
                        PolicyEndorsement.EndorsementId == eid,
                        PolicyEndorsement.isdeleted == "0",
                    )
                )
            ).scalar_one_or_none()
            if not endo:
                raise HTTPException(status_code=404, detail=f"Endorsement {eid} not found")
            self._check_ownership_and_branch_scope(
                principal,
                entity_type="ENDORSEMENT",
                branch_id=endo.BranchId,
                agent_id=endo.AgentId,
                franchise_id=endo.FranchiseId,
                sales_ex_id=endo.SalesExId,
                created_by_user_id=endo.CreateUser,
                is_write=is_write,
            )
            ctx.update({
                "entity_type": "ENDORSEMENT",
                "entity_id": endo.EndorsementId,
                "endorsement_id": endo.EndorsementId,
                "transaction_id": endo.TransanctionId,
                "policy_no": endo.PolicyNo or policy_no,
                "customer_id": endo.CustomerId,
                "vehicle_id": endo.CustVehId,
                "branch_id": endo.BranchId,
                "agent_id": endo.AgentId,
                "franchise_id": endo.FranchiseId,
                "sales_ex_id": endo.SalesExId,
            })
            return ctx

        if etype == "POLICY" or (transaction_id is not None and etype == "OTHER"):
            tid = transaction_id if transaction_id is not None else entity_id
            if tid is None:
                raise HTTPException(status_code=400, detail="transaction_id or entity_id is required for POLICY documents")
            trans = (
                await self.session.execute(
                    select(Transaction).where(
                        Transaction.TransanctionId == tid,
                        or_(Transaction.isdeleted == "0", Transaction.isdeleted.is_(None)),
                    )
                )
            ).scalar_one_or_none()
            if trans:
                fran_id: Optional[int] = None
                if trans.FranchiseCode and str(trans.FranchiseCode).strip().isdigit():
                    fran_id = int(str(trans.FranchiseCode).strip())
                self._check_ownership_and_branch_scope(
                    principal,
                    entity_type="POLICY",
                    branch_id=trans.BranchId,
                    agent_id=trans.AgentId,
                    franchise_id=fran_id,
                    sales_ex_id=trans.SalesEx_id,
                    is_write=is_write,
                )
                ctx.update({
                    "entity_type": "POLICY",
                    "entity_id": trans.TransanctionId,
                    "transaction_id": trans.TransanctionId,
                    "policy_no": trans.PolicyNo or policy_no,
                    "customer_id": trans.CustomerId,
                    "vehicle_id": trans.CustVehId,
                    "branch_id": trans.BranchId,
                    "agent_id": trans.AgentId,
                    "franchise_id": fran_id,
                    "sales_ex_id": trans.SalesEx_id,
                })
                return ctx

            # Fallback check in staged proposals (`tbl_transactionappnew`)
            app_trans = (
                await self.session.execute(
                    select(TransactionAppNew).where(TransactionAppNew.TransId == tid)
                )
            ).scalar_one_or_none()
            if not app_trans:
                raise HTTPException(status_code=404, detail=f"Policy transaction {tid} not found")
            self._check_ownership_and_branch_scope(
                principal,
                entity_type="POLICY",
                branch_id=app_trans.LocationHeadId if app_trans.LocationHeadId > 0 else None,
                agent_id=app_trans.UserId,
                franchise_id=app_trans.FranchaiseId if app_trans.FranchaiseId and app_trans.FranchaiseId > 0 else None,
                sales_ex_id=app_trans.SalesExecutiveId,
                created_by_user_id=app_trans.UserId,
                is_write=is_write,
            )
            ctx.update({
                "entity_type": "POLICY",
                "entity_id": app_trans.TransId,
                "transaction_id": app_trans.TransId,
                "policy_no": policy_no,
                "branch_id": app_trans.LocationHeadId if app_trans.LocationHeadId > 0 else principal.branch_id,
                "agent_id": app_trans.UserId,
                "franchise_id": app_trans.FranchaiseId,
                "sales_ex_id": app_trans.SalesExecutiveId,
            })
            return ctx

        if etype == "QUOTATION" or quotation_id is not None:
            qid = quotation_id if quotation_id is not None else entity_id
            if qid is None:
                raise HTTPException(status_code=400, detail="quotation_id or entity_id is required for QUOTATION documents")
            q_entry = (
                await self.session.execute(
                    select(AppQuatationEntry).where(
                        AppQuatationEntry.QuatationId == qid,
                        or_(AppQuatationEntry.isdeleted == "0", AppQuatationEntry.isdeleted.is_(None)),
                    )
                )
            ).scalar_one_or_none()
            if q_entry:
                self._check_ownership_and_branch_scope(
                    principal,
                    entity_type="QUOTATION",
                    branch_id=None,
                    agent_id=q_entry.AgentId,
                    franchise_id=None,
                    sales_ex_id=q_entry.SaleExId,
                    is_write=is_write,
                )
                ctx.update({
                    "entity_type": "QUOTATION",
                    "entity_id": q_entry.QuatationId,
                    "quotation_id": q_entry.QuatationId,
                    "agent_id": q_entry.AgentId,
                    "sales_ex_id": q_entry.SaleExId,
                })
                return ctx

            q_req = (
                await self.session.execute(
                    select(AppQuotationRequest).where(
                        AppQuotationRequest.QuatationId == qid,
                        AppQuotationRequest.isdeleted == 0,
                    )
                )
            ).scalar_one_or_none()
            if not q_req:
                raise HTTPException(status_code=404, detail=f"Quotation {qid} not found")
            self._check_ownership_and_branch_scope(
                principal,
                entity_type="QUOTATION",
                branch_id=q_req.LocationHeadId if q_req.LocationHeadId > 0 else None,
                agent_id=q_req.AgentId,
                franchise_id=q_req.FranchiseId if q_req.FranchiseId > 0 else None,
                sales_ex_id=q_req.SalesEx_Id,
                is_write=is_write,
            )
            ctx.update({
                "entity_type": "QUOTATION",
                "entity_id": q_req.QuatationId,
                "quotation_id": q_req.QuatationId,
                "vehicle_id": q_req.VehicleId,
                "branch_id": q_req.LocationHeadId if q_req.LocationHeadId > 0 else principal.branch_id,
                "agent_id": q_req.AgentId,
                "franchise_id": q_req.FranchiseId if q_req.FranchiseId > 0 else None,
                "sales_ex_id": q_req.SalesEx_Id,
            })
            return ctx

        if etype == "CUSTOMER" or (customer_id is not None and etype == "OTHER"):
            cid = customer_id if customer_id is not None else entity_id
            if cid is None:
                raise HTTPException(status_code=400, detail="customer_id or entity_id is required for CUSTOMER documents")
            cust = (
                await self.session.execute(
                    select(Customer).where(
                        Customer.CustomerId == cid,
                        or_(Customer.isdeleted == "0", Customer.isdeleted.is_(None)),
                    )
                )
            ).scalar_one_or_none()
            if not cust:
                raise HTTPException(status_code=404, detail=f"Customer {cid} not found")
            self._check_ownership_and_branch_scope(
                principal,
                entity_type="CUSTOMER",
                branch_id=cust.BranchId,
                agent_id=principal.agent_id,
                franchise_id=principal.franchise_id,
                sales_ex_id=principal.emp_id,
                is_write=is_write,
            )
            ctx.update({
                "entity_type": "CUSTOMER",
                "entity_id": cust.CustomerId,
                "customer_id": cust.CustomerId,
                "branch_id": cust.BranchId,
            })
            return ctx

        if etype == "VEHICLE" or (vehicle_id is not None and etype == "OTHER"):
            vid = vehicle_id if vehicle_id is not None else entity_id
            if vid is None:
                raise HTTPException(status_code=400, detail="vehicle_id or entity_id is required for VEHICLE documents")
            veh = (
                await self.session.execute(
                    select(VehicleDetails).where(
                        VehicleDetails.CustVehId == vid,
                        or_(VehicleDetails.isdeleted == "0", VehicleDetails.isdeleted.is_(None)),
                    )
                )
            ).scalar_one_or_none()
            if not veh:
                raise HTTPException(status_code=404, detail=f"Vehicle {vid} not found")
            self._check_ownership_and_branch_scope(
                principal,
                entity_type="VEHICLE",
                branch_id=veh.BranchId,
                agent_id=principal.agent_id,
                franchise_id=principal.franchise_id,
                sales_ex_id=principal.emp_id,
                is_write=is_write,
            )
            ctx.update({
                "entity_type": "VEHICLE",
                "entity_id": veh.CustVehId,
                "vehicle_id": veh.CustVehId,
                "customer_id": veh.CustomerId,
                "branch_id": veh.BranchId,
            })
            return ctx

        if etype in ("PAYMENT", "CHEQUE") or payment_id is not None:
            pid = payment_id if payment_id is not None else entity_id
            if pid is None:
                raise HTTPException(status_code=400, detail="payment_id or entity_id is required for PAYMENT/CHEQUE documents")
            pay = (
                await self.session.execute(
                    select(TransactionPayment).where(
                        TransactionPayment.PaymentId == pid,
                        or_(TransactionPayment.isdeleted == "0", TransactionPayment.isdeleted.is_(None)),
                    )
                )
            ).scalar_one_or_none()
            if not pay:
                raise HTTPException(status_code=404, detail=f"Payment {pid} not found")
            parent_trans = None
            if pay.TransanctionId:
                parent_trans = (
                    await self.session.execute(
                        select(Transaction).where(Transaction.TransanctionId == pay.TransanctionId)
                    )
                ).scalar_one_or_none()
            branch_val = pay.BranchId or (parent_trans.BranchId if parent_trans else principal.branch_id)
            agent_val = parent_trans.AgentId if parent_trans else principal.agent_id
            sales_val = parent_trans.SalesEx_id if parent_trans else principal.emp_id
            fran_val: Optional[int] = None
            if parent_trans and parent_trans.FranchiseCode and str(parent_trans.FranchiseCode).strip().isdigit():
                fran_val = int(str(parent_trans.FranchiseCode).strip())
            self._check_ownership_and_branch_scope(
                principal,
                entity_type=etype,
                branch_id=branch_val,
                agent_id=agent_val,
                franchise_id=fran_val,
                sales_ex_id=sales_val,
                is_write=is_write,
            )
            ctx.update({
                "entity_type": etype,
                "entity_id": pay.PaymentId,
                "payment_id": pay.PaymentId,
                "transaction_id": pay.TransanctionId,
                "policy_no": parent_trans.PolicyNo if parent_trans else policy_no,
                "branch_id": branch_val,
                "agent_id": agent_val,
                "franchise_id": fran_val,
                "sales_ex_id": sales_val,
            })
            return ctx

        # Generic / KYC / POSP / AGENT / SUPPORT / OTHER
        self._assert_not_restricted_role_for_entity(principal, etype, is_write=is_write)
        return ctx

    def _authorize_document_record(
        self,
        principal: PrincipalContext,
        doc: DocumentRecord,
        *,
        is_write: bool = False,
    ) -> None:
        self._check_ownership_and_branch_scope(
            principal,
            entity_type=doc.EntityType,
            branch_id=doc.BranchId,
            agent_id=doc.AgentId,
            franchise_id=doc.FranchiseId,
            sales_ex_id=doc.SalesExId,
            created_by_user_id=doc.CreateUser,
            is_write=is_write,
        )

    @staticmethod
    def _to_metadata_response(doc: DocumentRecord) -> DocumentMetadataResponse:
        return DocumentMetadataResponse(
            document_id=doc.DocumentId,
            document_uuid=doc.DocumentUUID,
            document_type=doc.DocumentType,
            doc_sub_type=doc.DocSubType,
            entity_type=doc.EntityType,
            entity_id=doc.EntityId,
            transaction_id=doc.TransanctionId,
            policy_no=doc.PolicyNo,
            quotation_id=doc.QuotationId,
            claim_id=doc.ClaimId,
            endorsement_id=doc.EndorsementId,
            customer_id=doc.CustomerId,
            vehicle_id=doc.CustVehId,
            payment_id=doc.PaymentId,
            branch_id=doc.BranchId,
            agent_id=doc.AgentId,
            franchise_id=doc.FranchiseId,
            sales_ex_id=doc.SalesExId,
            legacy_virtual_folder=doc.LegacyVirtualFolder,
            original_filename=doc.OriginalFileName,
            stored_filename=doc.StoredFileName,
            storage_key=doc.StorageKey,
            mime_type=doc.MimeType,
            file_extension=doc.FileExtension,
            file_size_bytes=doc.FileSizeBytes,
            checksum_sha256=doc.ChecksumSha256,
            version_no=doc.VersionNo,
            replaces_document_id=doc.ReplacesDocumentId,
            replaced_by_document_id=doc.ReplacedByDocumentId,
            legacy_ref_table=doc.LegacyRefTable,
            legacy_ref_id=doc.LegacyRefId,
            verified_status=doc.VerifiedStatus,
            remarks=doc.Remarks,
            idempotency_key=doc.IdempotencyKey,
            is_deleted=(doc.isdeleted != "0"),
            created_at=doc.CreateDate,
            created_by=doc.CreateUser,
            updated_at=doc.UpdateDate,
            updated_by=doc.UpdateUser,
            download_url=f"{settings.API_V1_PREFIX}/documents/{doc.DocumentId}/download",
        )

    # -----------------------------------------------------------------------
    # 2. Upload Document (with Idempotency, Dual-Write & Rollback Safety)
    # -----------------------------------------------------------------------

    async def upload_document(
        self,
        current_user: User,
        *,
        file_bytes: bytes,
        raw_filename: Optional[str],
        declared_content_type: Optional[str],
        document_type: str,
        doc_sub_type: Optional[str] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[int] = None,
        transaction_id: Optional[int] = None,
        quotation_id: Optional[int] = None,
        claim_id: Optional[int] = None,
        endorsement_id: Optional[int] = None,
        customer_id: Optional[int] = None,
        vehicle_id: Optional[int] = None,
        payment_id: Optional[int] = None,
        policy_no: Optional[str] = None,
        remarks: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> Tuple[DocumentMetadataResponse, bool]:
        """
        Validates, stores, and records an uploaded document atomically across
        storage backend, `tbl_documents`, and legacy entity document tables.
        """
        principal = self._get_principal(current_user)
        dtype = (document_type or "OTHER").strip().upper()
        if dtype not in VALID_DOCUMENT_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported document_type '{dtype}'. Valid types: {sorted(VALID_DOCUMENT_TYPES)}",
            )

        etype = (entity_type or dtype).strip().upper()

        # 1. Validate filename, extension, MIME, and binary magic bytes BEFORE touching DB/storage
        original_name, sanitized_name, ext = validate_and_sanitize_filename(raw_filename)
        canonical_mime, sha256_hex = validate_file_content_and_mime(
            file_bytes,
            ext,
            declared_content_type=declared_content_type,
        )

        # 2. Idempotency replay check
        clean_idem = idempotency_key.strip() if idempotency_key and idempotency_key.strip() else None
        if clean_idem:
            existing_idem = (
                await self.session.execute(
                    select(DocumentRecord).where(
                        DocumentRecord.IdempotencyKey == clean_idem,
                        DocumentRecord.isdeleted == "0",
                    )
                )
            ).scalar_one_or_none()
            if existing_idem:
                self._authorize_document_record(principal, existing_idem, is_write=True)
                if existing_idem.ChecksumSha256 != sha256_hex:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Idempotency key already used with a different file payload",
                    )
                return self._to_metadata_response(existing_idem), False

        # 3. Resolve parent entity & enforce RBAC/branch/principal scoping
        resolved = await self._resolve_entity_context(
            entity_type=etype,
            entity_id=entity_id,
            transaction_id=transaction_id,
            quotation_id=quotation_id,
            claim_id=claim_id,
            endorsement_id=endorsement_id,
            customer_id=customer_id,
            vehicle_id=vehicle_id,
            payment_id=payment_id,
            policy_no=policy_no,
            principal=principal,
            is_write=True,
        )

        now = datetime.utcnow()
        folder, stored_filename, storage_key = build_stored_filename_and_key(
            document_type=dtype,
            doc_sub_type=doc_sub_type,
            entity_type=resolved["entity_type"],
            entity_id=resolved["entity_id"],
            sanitized_filename=sanitized_name,
            ext=ext,
            policy_no=resolved["policy_no"],
            now=now,
        )

        # 4. Write binary payload to storage backend first
        try:
            written_size = self.storage.write_bytes(storage_key, file_bytes)
        except StorageBackendError as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Storage backend write failed: {exc}",
            ) from exc

        # 5. Persist DB records + dual-write to legacy tables with rollback cleanup on DB error
        try:
            legacy_ref_table: Optional[str] = None
            legacy_ref_id: Optional[int] = None

            if resolved["claim_id"] is not None:
                claim_doc = ClaimDocument(
                    ClaimId=resolved["claim_id"],
                    TransanctionId=resolved["transaction_id"] or 0,
                    DocumentType=(doc_sub_type or "SUPPORTING")[:50],
                    DocumentName=original_name[:255],
                    StorageKey=storage_key,
                    VerifiedStatus="PENDING",
                    Remarks=(remarks or "")[:500] if remarks else None,
                    isdeleted="0",
                    CreateDate=now,
                    CreateUser=current_user.UserId,
                )
                self.session.add(claim_doc)
                await self.session.flush()
                legacy_ref_table = "tbl_claimdocument"
                legacy_ref_id = claim_doc.ClaimDocId

            elif resolved["endorsement_id"] is not None:
                endo = (
                    await self.session.execute(
                        select(PolicyEndorsement).where(
                            PolicyEndorsement.EndorsementId == resolved["endorsement_id"]
                        )
                    )
                ).scalar_one_or_none()
                if endo:
                    endo.SupportingDocKey = storage_key
                    endo.UpdateDate = now
                    endo.UpdateUser = current_user.UserId
                    legacy_ref_table = "tbl_appendorsement"
                    legacy_ref_id = endo.EndorsementId

            elif resolved["quotation_id"] is not None:
                qid = resolved["quotation_id"]
                if folder == "PDF_Files":
                    req_file = AppRequestedQuotationFile(
                        QuotationId=qid,
                        CompanyId=0,
                        File_Name=stored_filename,
                        FilePath=storage_key,
                        IsDelete=0,
                        CreatedDate=now.strftime("%Y-%m-%d %H:%M:%S"),
                    )
                    self.session.add(req_file)
                    await self.session.flush()
                    legacy_ref_table = "tbl_app_requestedquotationfile"
                    legacy_ref_id = req_file.Id
                else:
                    ic_quot = InsuranceCompanyQuotation(
                        InsuranceCompanyId=0,
                        TransctionId=qid,
                        agentId=resolved["agent_id"] or 0,
                        QuotationFile=storage_key[:255],
                        EmpId=resolved["sales_ex_id"] or 0,
                        isdeleted="0",
                        InsertDate=now,
                        Remark=(remarks or "")[:255] if remarks else None,
                        Quotationfile_Name=original_name[:255],
                        ProductId=1,
                    )
                    self.session.add(ic_quot)
                    await self.session.flush()
                    legacy_ref_table = "tbl_insurancecompanyquotation"
                    legacy_ref_id = ic_quot.QuotationId

                    q_req = (
                        await self.session.execute(
                            select(AppQuotationRequest).where(AppQuotationRequest.QuatationId == qid)
                        )
                    ).scalar_one_or_none()
                    if q_req:
                        if (doc_sub_type or "").upper() in ("POLICYIMAGE", "PREV_POLICY_IMAGE", "RCIMAGE"):
                            q_req.PolicyImage = storage_key
                        else:
                            q_req.QuotationFile = storage_key

            elif resolved["transaction_id"] is not None and resolved["entity_type"] == "POLICY":
                trans = (
                    await self.session.execute(
                        select(Transaction).where(Transaction.TransanctionId == resolved["transaction_id"])
                    )
                ).scalar_one_or_none()
                if trans:
                    trans.CustDocStatus = "Uploaded"
                    legacy_ref_table = "tbl_transaction"
                    legacy_ref_id = trans.TransanctionId

            doc_record = DocumentRecord(
                DocumentUUID=str(uuid.uuid4()),
                DocumentType=dtype,
                DocSubType=doc_sub_type,
                EntityType=resolved["entity_type"],
                EntityId=resolved["entity_id"],
                TransanctionId=resolved["transaction_id"],
                PolicyNo=resolved["policy_no"],
                QuotationId=resolved["quotation_id"],
                ClaimId=resolved["claim_id"],
                EndorsementId=resolved["endorsement_id"],
                CustomerId=resolved["customer_id"],
                CustVehId=resolved["vehicle_id"],
                PaymentId=resolved["payment_id"],
                BranchId=resolved["branch_id"],
                AgentId=resolved["agent_id"],
                FranchiseId=resolved["franchise_id"],
                SalesExId=resolved["sales_ex_id"],
                LegacyVirtualFolder=folder,
                OriginalFileName=original_name,
                StoredFileName=stored_filename,
                StorageKey=storage_key,
                MimeType=canonical_mime,
                FileExtension=ext,
                FileSizeBytes=written_size,
                ChecksumSha256=sha256_hex,
                VersionNo=1,
                ReplacesDocumentId=None,
                ReplacedByDocumentId=None,
                LegacyRefTable=legacy_ref_table,
                LegacyRefId=legacy_ref_id,
                VerifiedStatus="PENDING",
                Remarks=remarks,
                IdempotencyKey=clean_idem,
                isdeleted="0",
                CreateDate=now,
                CreateUser=current_user.UserId,
            )
            self.session.add(doc_record)
            await self.session.commit()
            await self.session.refresh(doc_record)
            return self._to_metadata_response(doc_record), True

        except Exception:
            await self.session.rollback()
            try:
                self.storage.delete_bytes(storage_key)
            except Exception:
                pass
            raise

    # -----------------------------------------------------------------------
    # 3. Get Metadata, Stream Download, Replace (`DEF-010` Fix) & Soft Delete
    # -----------------------------------------------------------------------

    async def get_document_record_authorized(
        self,
        current_user: User,
        document_id: int,
        *,
        is_write: bool = False,
        for_update: bool = False,
    ) -> DocumentRecord:
        principal = self._get_principal(current_user)
        stmt = select(DocumentRecord).where(
            DocumentRecord.DocumentId == document_id,
            DocumentRecord.isdeleted == "0",
        )
        if for_update:
            stmt = stmt.with_for_update()
        doc = (await self.session.execute(stmt)).scalar_one_or_none()
        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document {document_id} not found",
            )
        self._authorize_document_record(principal, doc, is_write=is_write)
        return doc

    async def get_document_metadata(
        self,
        current_user: User,
        document_id: int,
    ) -> DocumentMetadataResponse:
        doc = await self.get_document_record_authorized(current_user, document_id, is_write=False)
        return self._to_metadata_response(doc)

    async def open_document_download(
        self,
        current_user: User,
        document_id: int,
    ) -> Tuple[DocumentRecord, bytes]:
        doc = await self.get_document_record_authorized(current_user, document_id, is_write=False)
        if not self.storage.exists(doc.StorageKey):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Physical file for document {document_id} is missing from storage",
            )
        try:
            content = self.storage.read_bytes(doc.StorageKey)
        except FileNotFoundError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Physical file for document {document_id} not found",
            ) from exc
        except StorageBackendError as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Storage read error: {exc}",
            ) from exc
        return doc, content

    async def replace_document(
        self,
        current_user: User,
        document_id: int,
        *,
        file_bytes: bytes,
        raw_filename: Optional[str],
        declared_content_type: Optional[str],
        doc_sub_type: Optional[str] = None,
        remarks: Optional[str] = None,
    ) -> DocumentMetadataResponse:
        """
        Replaces an existing document version atomically and fixes legacy `DEF-010`:
        - Generates a new canonical `StorageKey` in the target virtual folder.
        - Never deletes files from unrelated folders (e.g. `ClaimPhoto/` is untouched
          when replacing a `Claim_Final_Bill_Doc/` document).
        - Updates both `tbl_documents` (version chain) and any linked legacy record.
        """
        old_doc = await self.get_document_record_authorized(
            current_user,
            document_id,
            is_write=True,
            for_update=True,
        )

        original_name, sanitized_name, ext = validate_and_sanitize_filename(raw_filename)
        canonical_mime, sha256_hex = validate_file_content_and_mime(
            file_bytes,
            ext,
            declared_content_type=declared_content_type,
        )

        now = datetime.utcnow()
        effective_sub_type = doc_sub_type if doc_sub_type is not None else old_doc.DocSubType
        folder, stored_filename, new_storage_key = build_stored_filename_and_key(
            document_type=old_doc.DocumentType,
            doc_sub_type=effective_sub_type,
            entity_type=old_doc.EntityType,
            entity_id=old_doc.EntityId,
            sanitized_filename=sanitized_name,
            ext=ext,
            policy_no=old_doc.PolicyNo,
            now=now,
        )

        try:
            written_size = self.storage.write_bytes(new_storage_key, file_bytes)
        except StorageBackendError as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Storage backend write failed during replacement: {exc}",
            ) from exc

        try:
            new_doc = DocumentRecord(
                DocumentUUID=str(uuid.uuid4()),
                DocumentType=old_doc.DocumentType,
                DocSubType=effective_sub_type,
                EntityType=old_doc.EntityType,
                EntityId=old_doc.EntityId,
                TransanctionId=old_doc.TransanctionId,
                PolicyNo=old_doc.PolicyNo,
                QuotationId=old_doc.QuotationId,
                ClaimId=old_doc.ClaimId,
                EndorsementId=old_doc.EndorsementId,
                CustomerId=old_doc.CustomerId,
                CustVehId=old_doc.CustVehId,
                PaymentId=old_doc.PaymentId,
                BranchId=old_doc.BranchId,
                AgentId=old_doc.AgentId,
                FranchiseId=old_doc.FranchiseId,
                SalesExId=old_doc.SalesExId,
                LegacyVirtualFolder=folder,
                OriginalFileName=original_name,
                StoredFileName=stored_filename,
                StorageKey=new_storage_key,
                MimeType=canonical_mime,
                FileExtension=ext,
                FileSizeBytes=written_size,
                ChecksumSha256=sha256_hex,
                VersionNo=old_doc.VersionNo + 1,
                ReplacesDocumentId=old_doc.DocumentId,
                ReplacedByDocumentId=None,
                LegacyRefTable=old_doc.LegacyRefTable,
                LegacyRefId=old_doc.LegacyRefId,
                VerifiedStatus="PENDING",
                Remarks=remarks if remarks is not None else old_doc.Remarks,
                IdempotencyKey=None,
                isdeleted="0",
                CreateDate=now,
                CreateUser=current_user.UserId,
            )
            self.session.add(new_doc)
            await self.session.flush()

            # Mark old version as superseded
            old_doc.ReplacedByDocumentId = new_doc.DocumentId
            old_doc.isdeleted = "1"
            old_doc.UpdateDate = now
            old_doc.UpdateUser = current_user.UserId

            # Synchronize dual-written legacy reference to point to the new canonical StorageKey
            if old_doc.LegacyRefTable == "tbl_claimdocument" and old_doc.LegacyRefId:
                c_doc = (
                    await self.session.execute(
                        select(ClaimDocument).where(ClaimDocument.ClaimDocId == old_doc.LegacyRefId)
                    )
                ).scalar_one_or_none()
                if c_doc:
                    c_doc.DocumentName = original_name[:255]
                    c_doc.StorageKey = new_storage_key
                    if effective_sub_type:
                        c_doc.DocumentType = effective_sub_type[:50]
            elif old_doc.LegacyRefTable == "tbl_appendorsement" and old_doc.LegacyRefId:
                endo = (
                    await self.session.execute(
                        select(PolicyEndorsement).where(PolicyEndorsement.EndorsementId == old_doc.LegacyRefId)
                    )
                ).scalar_one_or_none()
                if endo:
                    endo.SupportingDocKey = new_storage_key
                    endo.UpdateDate = now
                    endo.UpdateUser = current_user.UserId
            elif old_doc.LegacyRefTable == "tbl_app_requestedquotationfile" and old_doc.LegacyRefId:
                q_file = (
                    await self.session.execute(
                        select(AppRequestedQuotationFile).where(AppRequestedQuotationFile.Id == old_doc.LegacyRefId)
                    )
                ).scalar_one_or_none()
                if q_file:
                    q_file.File_Name = stored_filename
                    q_file.FilePath = new_storage_key

            await self.session.commit()
            await self.session.refresh(new_doc)
            return self._to_metadata_response(new_doc)

        except Exception:
            await self.session.rollback()
            try:
                self.storage.delete_bytes(new_storage_key)
            except Exception:
                pass
            raise

    async def delete_document(
        self,
        current_user: User,
        document_id: int,
    ) -> DocumentMetadataResponse:
        doc = await self.get_document_record_authorized(
            current_user,
            document_id,
            is_write=True,
            for_update=True,
        )
        now = datetime.utcnow()
        doc.isdeleted = "1"
        doc.UpdateDate = now
        doc.UpdateUser = current_user.UserId

        if doc.LegacyRefTable == "tbl_claimdocument" and doc.LegacyRefId:
            c_doc = (
                await self.session.execute(
                    select(ClaimDocument).where(ClaimDocument.ClaimDocId == doc.LegacyRefId)
                )
            ).scalar_one_or_none()
            if c_doc:
                c_doc.isdeleted = "1"
        elif doc.LegacyRefTable == "tbl_app_requestedquotationfile" and doc.LegacyRefId:
            q_file = (
                await self.session.execute(
                    select(AppRequestedQuotationFile).where(AppRequestedQuotationFile.Id == doc.LegacyRefId)
                )
            ).scalar_one_or_none()
            if q_file:
                q_file.IsDelete = 1

        await self.session.commit()
        await self.session.refresh(doc)
        return self._to_metadata_response(doc)

    # -----------------------------------------------------------------------
    # 4. Entity Document Listing
    # -----------------------------------------------------------------------

    async def list_entity_documents(
        self,
        current_user: User,
        *,
        entity_type: str,
        entity_id: int,
    ) -> DocumentListResponse:
        principal = self._get_principal(current_user)
        etype = entity_type.strip().upper()
        await self._resolve_entity_context(
            entity_type=etype,
            entity_id=entity_id,
            transaction_id=entity_id if etype == "POLICY" else None,
            quotation_id=entity_id if etype == "QUOTATION" else None,
            claim_id=entity_id if etype == "CLAIM" else None,
            endorsement_id=entity_id if etype == "ENDORSEMENT" else None,
            customer_id=entity_id if etype == "CUSTOMER" else None,
            vehicle_id=entity_id if etype == "VEHICLE" else None,
            payment_id=entity_id if etype in ("PAYMENT", "CHEQUE") else None,
            principal=principal,
            is_write=False,
        )

        filters = [DocumentRecord.isdeleted == "0"]
        if etype == "POLICY":
            filters.append(
                or_(
                    (DocumentRecord.EntityType == "POLICY") & (DocumentRecord.EntityId == entity_id),
                    DocumentRecord.TransanctionId == entity_id,
                )
            )
        elif etype == "QUOTATION":
            filters.append(
                or_(
                    (DocumentRecord.EntityType == "QUOTATION") & (DocumentRecord.EntityId == entity_id),
                    DocumentRecord.QuotationId == entity_id,
                )
            )
        elif etype == "CLAIM":
            filters.append(
                or_(
                    (DocumentRecord.EntityType == "CLAIM") & (DocumentRecord.EntityId == entity_id),
                    DocumentRecord.ClaimId == entity_id,
                )
            )
        elif etype == "ENDORSEMENT":
            filters.append(
                or_(
                    (DocumentRecord.EntityType == "ENDORSEMENT") & (DocumentRecord.EntityId == entity_id),
                    DocumentRecord.EndorsementId == entity_id,
                )
            )
        elif etype == "CUSTOMER":
            filters.append(
                or_(
                    (DocumentRecord.EntityType == "CUSTOMER") & (DocumentRecord.EntityId == entity_id),
                    DocumentRecord.CustomerId == entity_id,
                )
            )
        elif etype == "VEHICLE":
            filters.append(
                or_(
                    (DocumentRecord.EntityType == "VEHICLE") & (DocumentRecord.EntityId == entity_id),
                    DocumentRecord.CustVehId == entity_id,
                )
            )
        elif etype in ("PAYMENT", "CHEQUE"):
            filters.append(
                or_(
                    (DocumentRecord.EntityType.in_(("PAYMENT", "CHEQUE"))) & (DocumentRecord.EntityId == entity_id),
                    DocumentRecord.PaymentId == entity_id,
                )
            )
        else:
            filters.append((DocumentRecord.EntityType == etype) & (DocumentRecord.EntityId == entity_id))

        rows = (
            await self.session.execute(
                select(DocumentRecord)
                .where(*filters)
                .order_by(DocumentRecord.DocumentId.asc())
            )
        ).scalars().all()

        items = [self._to_metadata_response(r) for r in rows]
        return DocumentListResponse(total=len(items), items=items)

    # -----------------------------------------------------------------------
    # 5. Deterministic Quotation PDF Generation (`~/PDF_Files/Quotation_<id>.pdf`)
    # -----------------------------------------------------------------------

    @staticmethod
    def _build_minimal_pdf_bytes(lines: List[str]) -> bytes:
        """
        Generates a valid, deterministic PDF-1.4 binary document without requiring
        external OS native binaries.
        """
        escaped_lines = []
        for idx, line in enumerate(lines):
            safe_txt = (
                line.replace("\\", "\\\\")
                .replace("(", "\\(")
                .replace(")", "\\)")
            )
            y_pos = 760 - (idx * 18)
            if y_pos < 60:
                break
            escaped_lines.append(f"BT /F1 11 Tf 50 {y_pos} Td ({safe_txt}) Tj ET")

        stream_content = "\n".join(escaped_lines).encode("latin-1", errors="replace")
        stream_len = len(stream_content)

        obj1 = b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        obj2 = b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        obj3 = (
            b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>\nendobj\n"
        )
        obj4 = b"4 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"
        obj5 = (
            f"5 0 obj\n<< /Length {stream_len} >>\nstream\n".encode("ascii")
            + stream_content
            + b"\nendstream\nendobj\n"
        )

        header = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"
        body_parts = [obj1, obj2, obj3, obj4, obj5]
        offsets = []
        cursor = len(header)
        for part in body_parts:
            offsets.append(cursor)
            cursor += len(part)

        xref_lines = [f"xref\n0 {len(body_parts) + 1}\n0000000000 65535 f \n"]
        for off in offsets:
            xref_lines.append(f"{off:010d} 00000 n \n")
        xref_bytes = "".join(xref_lines).encode("ascii")
        trailer = (
            f"trailer\n<< /Size {len(body_parts) + 1} /Root 1 0 R >>\n"
            f"startxref\n{cursor}\n%%EOF\n"
        ).encode("ascii")

        return header + b"".join(body_parts) + xref_bytes + trailer

    async def generate_quotation_pdf(
        self,
        current_user: User,
        quotation_id: int,
    ) -> DocumentMetadataResponse:
        """
        Generates a Quotation Comparison/Summary PDF and stores it in `PDF_Files/`
        (reproducing `Qt_QuotationRateCalculation.aspx.cs` / `SelfQuotationRequest.aspx.cs`).
        """
        principal = self._get_principal(current_user)
        await self._resolve_entity_context(
            entity_type="QUOTATION",
            entity_id=quotation_id,
            quotation_id=quotation_id,
            principal=principal,
            is_write=True,
        )

        q_entry = (
            await self.session.execute(
                select(AppQuatationEntry).where(AppQuatationEntry.QuatationId == quotation_id)
            )
        ).scalar_one_or_none()
        q_req = (
            await self.session.execute(
                select(AppQuotationRequest).where(AppQuotationRequest.QuatationId == quotation_id)
            )
        ).scalar_one_or_none()

        lines = [
            "RELIABLE INSURANCE BROKERS - MOTOR QUOTATION SUMMARY",
            f"Quotation ID: {quotation_id}",
        ]
        if q_entry:
            lines.extend([
                f"Quotation Code: {q_entry.QuatationCode or 'N/A'}",
                f"Product Name: {q_entry.ProductName or 'MOTOR'}",
                f"Registration No: {q_entry.RegistrationNo or 'NEW'}",
                f"IDV (Sum Insured): INR {q_entry.IDV or '0.00'}",
                f"Total Own Damage (A): INR {q_entry.AtotalOwnDamPremium or '0.00'}",
                f"Total Liability (B): INR {q_entry.BtotalLiabilityPremium or '0.00'}",
                f"Net Premium: INR {q_entry.TotalPremium or '0.00'}",
                f"GST (18%): INR {q_entry.GST18 or '0.00'}",
                f"Final Payable Premium: INR {q_entry.finalPrmium or '0.00'}",
            ])
        elif q_req:
            lines.extend([
                f"Quotation Code: {q_req.QuatationCode or 'N/A'}",
                f"Vehicle No: {q_req.VehicleNo or 'NEW'}",
                f"Make / Model: {q_req.VehicleMake or ''} {q_req.VehicleModel or ''}",
                f"Product / Policy Mode: {q_req.ProductType or ''} / {q_req.PolicyMode or ''}",
            ])

        pdf_bytes = self._build_minimal_pdf_bytes(lines)
        filename = f"Quotation_{quotation_id}.pdf"
        doc_resp, _ = await self.upload_document(
            current_user,
            file_bytes=pdf_bytes,
            raw_filename=filename,
            declared_content_type="application/pdf",
            document_type="QUOTATION",
            doc_sub_type="QuotationPdf",
            entity_type="QUOTATION",
            entity_id=quotation_id,
            quotation_id=quotation_id,
            remarks="System-generated quotation comparison PDF",
        )
        return doc_resp

    # -----------------------------------------------------------------------
    # 6. Bulk ZIP Download & `DownloadAll.ashx` Compatibility
    # -----------------------------------------------------------------------

    @staticmethod
    def _parse_legacy_trans_id(raw_trans_id: str) -> int:
        """
        Parses integer or base64-encoded `TransId` query parameter from `DownloadAll.ashx`
        (`GAP-UNK-11-002` documented).
        """
        if not raw_trans_id or not raw_trans_id.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="TransId parameter is required",
            )
        cleaned = raw_trans_id.strip()
        if cleaned.isdigit():
            val = int(cleaned)
            if val <= 0:
                raise HTTPException(status_code=400, detail="TransId must be a positive integer")
            return val

        # Support URL-safe base64 encoded numeric ID for legacy token compatibility
        try:
            padded = cleaned + "=" * (-len(cleaned) % 4)
            decoded = base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8").strip()
            if decoded.isdigit() and int(decoded) > 0:
                return int(decoded)
        except Exception:
            pass

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or unsupported TransId format",
        )

    async def build_zip_archive(
        self,
        current_user: User,
        request: DocumentZipRequest,
    ) -> Tuple[bytes, str, int, int]:
        """
        Builds a ZIP archive containing all authorized documents matching `request`.
        Preserves `DownloadAll.ashx.cs` archive layout (`Files/<filename>` inside ZIP).

        Returns:
            Tuple of (zip_bytes, archive_filename, included_file_count, missing_file_count)
        """
        principal = self._get_principal(current_user)
        docs: List[DocumentRecord] = []
        default_zip_stem = "Documents"

        if request.document_ids:
            for doc_id in request.document_ids:
                doc = await self.get_document_record_authorized(current_user, doc_id, is_write=False)
                docs.append(doc)
            if request.policy_no:
                default_zip_stem = request.policy_no
        elif request.transaction_id is not None:
            resolved = await self._resolve_entity_context(
                entity_type="POLICY",
                entity_id=request.transaction_id,
                transaction_id=request.transaction_id,
                policy_no=request.policy_no,
                principal=principal,
                is_write=False,
            )
            default_zip_stem = request.policy_no or resolved.get("policy_no") or f"Transaction_{request.transaction_id}"
            rows = (
                await self.session.execute(
                    select(DocumentRecord)
                    .where(
                        DocumentRecord.TransanctionId == request.transaction_id,
                        DocumentRecord.isdeleted == "0",
                    )
                    .order_by(DocumentRecord.DocumentId.asc())
                )
            ).scalars().all()
            docs = list(rows)
        elif request.entity_type and request.entity_id is not None:
            etype = request.entity_type.strip().upper()
            resolved = await self._resolve_entity_context(
                entity_type=etype,
                entity_id=request.entity_id,
                transaction_id=request.entity_id if etype == "POLICY" else None,
                quotation_id=request.entity_id if etype == "QUOTATION" else None,
                claim_id=request.entity_id if etype == "CLAIM" else None,
                endorsement_id=request.entity_id if etype == "ENDORSEMENT" else None,
                customer_id=request.entity_id if etype == "CUSTOMER" else None,
                vehicle_id=request.entity_id if etype == "VEHICLE" else None,
                payment_id=request.entity_id if etype in ("PAYMENT", "CHEQUE") else None,
                policy_no=request.policy_no,
                principal=principal,
                is_write=False,
            )
            default_zip_stem = (
                request.policy_no
                or resolved.get("policy_no")
                or f"{etype}_{request.entity_id}"
            )
            list_resp = await self.list_entity_documents(
                current_user,
                entity_type=etype,
                entity_id=request.entity_id,
            )
            for item in list_resp.items:
                d = await self.get_document_record_authorized(current_user, item.document_id, is_write=False)
                docs.append(d)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Must specify document_ids, transaction_id, or (entity_type and entity_id)",
            )

        if not docs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active documents found for ZIP archive",
            )

        buf = io.BytesIO()
        used_names: Dict[str, int] = {}
        included_count = 0
        missing_count = 0

        with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            for doc in docs:
                if not self.storage.exists(doc.StorageKey):
                    missing_count += 1
                    continue
                try:
                    raw_bytes = self.storage.read_bytes(doc.StorageKey)
                except (FileNotFoundError, StorageBackendError):
                    missing_count += 1
                    continue

                base_name = _SAFE_ZIP_NAME_RE.sub("_", doc.OriginalFileName or doc.StoredFileName)
                if not base_name:
                    base_name = f"doc_{doc.DocumentId}{doc.FileExtension}"

                if base_name in used_names:
                    used_names[base_name] += 1
                    seq = used_names[base_name]
                    if "." in base_name:
                        stem, ext_part = base_name.rsplit(".", 1)
                        entry_name = f"{stem}_{seq}.{ext_part}"
                    else:
                        entry_name = f"{base_name}_{seq}"
                else:
                    used_names[base_name] = 1
                    entry_name = base_name

                # Preserve legacy DownloadAll.ashx.cs: zip.AddFile(filePath, "Files")
                zf.writestr(f"Files/{entry_name}", raw_bytes)
                included_count += 1

        safe_stem = _SAFE_ZIP_NAME_RE.sub("_", request.archive_filename or default_zip_stem).strip("._-") or "Documents"
        if not safe_stem.lower().endswith(".zip"):
            archive_filename = f"{safe_stem}.zip"
        else:
            archive_filename = safe_stem

        return buf.getvalue(), archive_filename, included_count, missing_count

    # -----------------------------------------------------------------------
    # 7. `ImageHandler.ashx` Compatibility
    # -----------------------------------------------------------------------

    async def legacy_image_handler_stream(
        self,
        current_user: User,
        image_id: int,
    ) -> Tuple[bytes, str, str]:
        """
        Reproduces `ImageHandler.ashx?Id=<id>` with RBAC and principal ownership checks.
        Resolves `DocumentId` in `tbl_documents` (or fallback `ClaimDocId` in `tbl_claimdocument`).
        """
        doc = (
            await self.session.execute(
                select(DocumentRecord).where(
                    DocumentRecord.DocumentId == image_id,
                    DocumentRecord.isdeleted == "0",
                )
            )
        ).scalar_one_or_none()

        if doc:
            _, data = await self.open_document_download(current_user, doc.DocumentId)
            return data, doc.MimeType, doc.OriginalFileName

        # Fallback: check if `Id` refers to legacy `tbl_claimdocument.ClaimDocId`
        claim_doc = (
            await self.session.execute(
                select(ClaimDocument).where(
                    ClaimDocument.ClaimDocId == image_id,
                    ClaimDocument.isdeleted == "0",
                )
            )
        ).scalar_one_or_none()
        if claim_doc:
            linked_doc = (
                await self.session.execute(
                    select(DocumentRecord).where(
                        DocumentRecord.LegacyRefTable == "tbl_claimdocument",
                        DocumentRecord.LegacyRefId == claim_doc.ClaimDocId,
                        DocumentRecord.isdeleted == "0",
                    )
                )
            ).scalar_one_or_none()
            if linked_doc:
                _, data = await self.open_document_download(current_user, linked_doc.DocumentId)
                return data, linked_doc.MimeType, linked_doc.OriginalFileName

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Image or document Id {image_id} not found",
        )

    # -----------------------------------------------------------------------
    # 8. HiCaliber Policy Parser Webhook (`PolicyParserWebhook.aspx.cs`)
    # -----------------------------------------------------------------------

    @staticmethod
    def verify_webhook_signature_or_secret(
        raw_body: bytes,
        webhook_secret_header: Optional[str],
        hmac_signature_header: Optional[str],
    ) -> None:
        """
        INTENTIONAL HARDENING over legacy `PolicyParserWebhook.aspx.cs`:
        Verifies either `X-Webhook-Secret` shared secret header or
        `X-Calliber-Signature` HMAC-SHA256 signature against `settings.POLICY_PARSER_WEBHOOK_SECRET`.
        """
        configured_secret = settings.POLICY_PARSER_WEBHOOK_SECRET
        if hmac_signature_header:
            sig_clean = hmac_signature_header.strip()
            if sig_clean.lower().startswith("sha256="):
                sig_clean = sig_clean.split("=", 1)[1].strip()
            expected_hmac = hmac.new(
                configured_secret.encode("utf-8"),
                raw_body,
                hashlib.sha256,
            ).hexdigest()
            if hmac.compare_digest(sig_clean.lower(), expected_hmac.lower()):
                return
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook HMAC signature",
            )

        if webhook_secret_header:
            if hmac.compare_digest(webhook_secret_header.strip(), configured_secret):
                return
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook secret header",
            )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing webhook authentication header (X-Webhook-Secret or X-Calliber-Signature)",
        )

    @staticmethod
    def _to_webhook_response(rec: PolicyParserWebhookRecord) -> PolicyParserWebhookResponse:
        return PolicyParserWebhookResponse(
            calliber_policy_id=rec.CalliberPolicyId,
            webhook_event_id=rec.WebhookEventId,
            idempotency_key=rec.IdempotencyKey,
            payload_sha256=rec.PayloadSha256,
            policy_no=rec.PolicyNo,
            customer_name=rec.CustomerName,
            vehicle_reg_no=rec.VehicleRegNo,
            engine_no=rec.EngineNo,
            chassis_no=rec.ChassisNo,
            ins_company=rec.InsCompany,
            product_type=rec.ProductType,
            policy_type=rec.PolicyType,
            start_date=rec.StartDate,
            end_date=rec.EndDate,
            idv=Decimal(str(rec.IDV or "0.00")),
            od_premium=Decimal(str(rec.ODPremium or "0.00")),
            tp_premium=Decimal(str(rec.TPPremium or "0.00")),
            net_premium=Decimal(str(rec.NetPremium or "0.00")),
            gst_amount=Decimal(str(rec.GSTAmount or "0.00")),
            gross_premium=Decimal(str(rec.GrossPremium or "0.00")),
            ncb_percent=Decimal(str(rec.NCBPercent or "0.00")),
            document_id=rec.DocumentId,
            linked_transaction_id=rec.LinkedTransanctionId,
            processing_status=rec.ProcessingStatus,
            updated_by=rec.UpdatedBy,
            created_at=rec.CreateDate,
        )

    async def process_policy_parser_webhook(
        self,
        payload: PolicyParserWebhookRequest,
        *,
        raw_body: bytes,
        idempotency_key_header: Optional[str] = None,
    ) -> Tuple[PolicyParserWebhookResponse, bool]:
        """
        Processes a HiCaliber Policy PDF OCR extraction webhook (`PolicyParserWebhook.aspx.cs`),
        enforces idempotency, persists `tbl_calliber_policy_webhook`, and links
        `tbl_transaction.calliber_policyId` and `tbl_transaction.calliber_UpdateBy` when matched.
        """
        if not payload.policy_no and not payload.vehicle_reg_no and payload.transaction_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Webhook payload must include at least policy_no, vehicle_reg_no, or transaction_id",
            )

        canonical_dict = payload.model_dump(mode="json", exclude={"idempotency_key", "webhook_event_id"})
        payload_sha256 = hashlib.sha256(
            json.dumps(canonical_dict, sort_keys=True).encode("utf-8")
        ).hexdigest()

        effective_idem = (
            (idempotency_key_header or "").strip()
            or (payload.idempotency_key or "").strip()
            or (payload.webhook_event_id or "").strip()
            or None
        )

        if effective_idem:
            existing = (
                await self.session.execute(
                    select(PolicyParserWebhookRecord).where(
                        or_(
                            PolicyParserWebhookRecord.IdempotencyKey == effective_idem,
                            PolicyParserWebhookRecord.WebhookEventId == effective_idem,
                        ),
                        PolicyParserWebhookRecord.isdeleted == "0",
                    )
                )
            ).scalar_one_or_none()
            if existing:
                if existing.PayloadSha256 != payload_sha256:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Webhook idempotency key already used with a different payload",
                    )
                return self._to_webhook_response(existing), False
        else:
            existing_hash = (
                await self.session.execute(
                    select(PolicyParserWebhookRecord).where(
                        PolicyParserWebhookRecord.PayloadSha256 == payload_sha256,
                        PolicyParserWebhookRecord.isdeleted == "0",
                    )
                )
            ).scalar_one_or_none()
            if existing_hash:
                return self._to_webhook_response(existing_hash), False

        # Resolve optional linked Transaction by transaction_id or PolicyNo
        linked_trans: Optional[Transaction] = None
        if payload.transaction_id is not None:
            linked_trans = (
                await self.session.execute(
                    select(Transaction).where(Transaction.TransanctionId == payload.transaction_id)
                )
            ).scalar_one_or_none()
        elif payload.policy_no:
            linked_trans = (
                await self.session.execute(
                    select(Transaction)
                    .where(
                        Transaction.PolicyNo == payload.policy_no.strip(),
                        or_(Transaction.isdeleted == "0", Transaction.isdeleted.is_(None)),
                    )
                    .order_by(Transaction.TransanctionId.desc())
                )
            ).scalars().first()

        now = datetime.utcnow()
        updated_by = (payload.updated_by or "HiCaliberWebhook")[:200]
        rec = PolicyParserWebhookRecord(
            WebhookEventId=payload.webhook_event_id,
            IdempotencyKey=effective_idem,
            PayloadSha256=payload_sha256,
            PolicyNo=payload.policy_no.strip() if payload.policy_no else None,
            CustomerName=payload.customer_name,
            VehicleRegNo=payload.vehicle_reg_no,
            EngineNo=payload.engine_no,
            ChassisNo=payload.chassis_no,
            InsCompany=payload.ins_company,
            ProductType=payload.product_type,
            PolicyType=payload.policy_type,
            StartDate=payload.start_date,
            EndDate=payload.end_date,
            IDV=payload.idv,
            ODPremium=payload.od_premium,
            TPPremium=payload.tp_premium,
            NetPremium=payload.net_premium,
            GSTAmount=payload.gst_amount,
            GrossPremium=payload.gross_premium,
            NCBPercent=payload.ncb_percent,
            DocumentId=payload.document_id,
            LinkedTransanctionId=linked_trans.TransanctionId if linked_trans else None,
            RawPayloadJson=raw_body.decode("utf-8", errors="replace"),
            ProcessingStatus="LINKED" if linked_trans else "PROCESSED",
            UpdatedBy=updated_by,
            isdeleted="0",
            CreateDate=now,
        )
        self.session.add(rec)
        await self.session.flush()

        if linked_trans:
            linked_trans.calliber_policyId = rec.CalliberPolicyId
            linked_trans.calliber_UpdateBy = updated_by

        await self.session.commit()
        await self.session.refresh(rec)
        return self._to_webhook_response(rec), True
