"""
Pydantic v2 Request & Response Schemas for Phase 11 — Document, File Handling,
ZIP Streaming & HiCaliber Policy Parser Webhook Engine.
"""
from datetime import datetime
from decimal import Decimal
from typing import Generic, List, Optional, TypeVar
from pydantic import AliasChoices, BaseModel, ConfigDict, Field


T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    success: bool = True
    message: str
    data: T


class DocumentMetadataResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    document_id: int
    document_uuid: str
    document_type: str
    doc_sub_type: Optional[str] = None
    entity_type: str
    entity_id: Optional[int] = None
    transaction_id: Optional[int] = None
    policy_no: Optional[str] = None
    quotation_id: Optional[int] = None
    claim_id: Optional[int] = None
    endorsement_id: Optional[int] = None
    customer_id: Optional[int] = None
    vehicle_id: Optional[int] = None
    payment_id: Optional[int] = None
    branch_id: Optional[int] = None
    agent_id: Optional[int] = None
    franchise_id: Optional[int] = None
    sales_ex_id: Optional[int] = None
    legacy_virtual_folder: str
    original_filename: str
    stored_filename: str
    storage_key: str
    mime_type: str
    file_extension: str
    file_size_bytes: int
    checksum_sha256: str
    version_no: int
    replaces_document_id: Optional[int] = None
    replaced_by_document_id: Optional[int] = None
    legacy_ref_table: Optional[str] = None
    legacy_ref_id: Optional[int] = None
    verified_status: str
    remarks: Optional[str] = None
    idempotency_key: Optional[str] = None
    is_deleted: bool = False
    created_at: datetime
    created_by: Optional[int] = None
    updated_at: Optional[datetime] = None
    updated_by: Optional[int] = None
    download_url: str


class DocumentListResponse(BaseModel):
    total: int
    items: List[DocumentMetadataResponse]


class DocumentZipRequest(BaseModel):
    document_ids: Optional[List[int]] = Field(default=None, description="Explicit list of DocumentIds to include in ZIP")
    entity_type: Optional[str] = Field(default=None, description="Optional entity type filter (POLICY, CLAIM, QUOTATION, ENDORSEMENT)")
    entity_id: Optional[int] = Field(default=None, description="Optional entity ID filter")
    transaction_id: Optional[int] = Field(default=None, description="Optional TransanctionId filter (DownloadAll.ashx parity)")
    policy_no: Optional[str] = Field(default=None, description="Optional PolicyNo for ZIP filename")
    archive_filename: Optional[str] = Field(default=None, description="Optional custom archive filename")


class PolicyParserWebhookRequest(BaseModel):
    """
    HiCaliber Policy PDF OCR / Parser Webhook Payload (`PolicyParserWebhook.aspx.cs` / `API_Calliber_Policy`).
    Accepts both legacy PascalCase keys and snake_case equivalents.
    """
    model_config = ConfigDict(populate_by_name=True, extra="allow")

    webhook_event_id: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("webhook_event_id", "WebhookEventId", "event_id", "EventId"),
    )
    idempotency_key: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("idempotency_key", "IdempotencyKey"),
    )
    policy_no: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("policy_no", "PolicyNo", "policyNo"),
    )
    customer_name: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("customer_name", "CustomerName", "customerName"),
    )
    vehicle_reg_no: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("vehicle_reg_no", "VehicleRegNo", "RegistrationNo", "VehRegNo"),
    )
    engine_no: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("engine_no", "EngineNo", "engineNo"),
    )
    chassis_no: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("chassis_no", "ChassisNo", "chassisNo"),
    )
    ins_company: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("ins_company", "InsCompany", "InsuranceCompany"),
    )
    product_type: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("product_type", "ProductType"),
    )
    policy_type: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("policy_type", "PolicyType"),
    )
    start_date: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("start_date", "StartDate", "RiskStartDate"),
    )
    end_date: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("end_date", "EndDate", "ExpiryDate"),
    )
    idv: Decimal = Field(
        default=Decimal("0.00"),
        ge=Decimal("0.00"),
        validation_alias=AliasChoices("idv", "IDV", "SumInsured"),
    )
    od_premium: Decimal = Field(
        default=Decimal("0.00"),
        ge=Decimal("0.00"),
        validation_alias=AliasChoices("od_premium", "ODPremium", "ODPermium"),
    )
    tp_premium: Decimal = Field(
        default=Decimal("0.00"),
        ge=Decimal("0.00"),
        validation_alias=AliasChoices("tp_premium", "TPPremium", "TPPermium"),
    )
    net_premium: Decimal = Field(
        default=Decimal("0.00"),
        ge=Decimal("0.00"),
        validation_alias=AliasChoices("net_premium", "NetPremium", "NetPermium"),
    )
    gst_amount: Decimal = Field(
        default=Decimal("0.00"),
        ge=Decimal("0.00"),
        validation_alias=AliasChoices("gst_amount", "GSTAmount", "GST_Amount", "GST18"),
    )
    gross_premium: Decimal = Field(
        default=Decimal("0.00"),
        ge=Decimal("0.00"),
        validation_alias=AliasChoices("gross_premium", "GrossPremium", "FinalPremium", "ProPosalAmt"),
    )
    ncb_percent: Decimal = Field(
        default=Decimal("0.00"),
        ge=Decimal("0.00"),
        le=Decimal("100.00"),
        validation_alias=AliasChoices("ncb_percent", "NCBPercent", "NCB", "NCBPer"),
    )
    document_id: Optional[int] = Field(
        default=None,
        validation_alias=AliasChoices("document_id", "DocumentId"),
    )
    transaction_id: Optional[int] = Field(
        default=None,
        validation_alias=AliasChoices("transaction_id", "TransanctionId", "TransId"),
    )
    updated_by: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("updated_by", "UpdatedBy", "calliber_UpdateBy"),
    )


class PolicyParserWebhookResponse(BaseModel):
    calliber_policy_id: int
    webhook_event_id: Optional[str] = None
    idempotency_key: Optional[str] = None
    payload_sha256: str
    policy_no: Optional[str] = None
    customer_name: Optional[str] = None
    vehicle_reg_no: Optional[str] = None
    engine_no: Optional[str] = None
    chassis_no: Optional[str] = None
    ins_company: Optional[str] = None
    product_type: Optional[str] = None
    policy_type: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    idv: Decimal
    od_premium: Decimal
    tp_premium: Decimal
    net_premium: Decimal
    gst_amount: Decimal
    gross_premium: Decimal
    ncb_percent: Decimal
    document_id: Optional[int] = None
    linked_transaction_id: Optional[int] = None
    processing_status: str
    updated_by: Optional[str] = None
    created_at: datetime
