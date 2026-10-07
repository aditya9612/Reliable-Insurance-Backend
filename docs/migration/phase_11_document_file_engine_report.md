# Phase 11 — Legacy Document / File Handling, Storage, Download, Authorization, ZIP, Webhook & Parity Report

## 1. Executive Summary
Phase 11 migrates the legacy C#/.NET 4.0 document and file handling architecture (`InsurancefinalNew`) into the FastAPI async backend (`Reliable-Insurance-Backend`) with:
- **Zero Production Exposure**: Strictly local database (`localhost:3306/reliable_insurance_dev`) and local/mock storage (`./storage_data` / `InMemoryObjectStorageBackend`). Production storage identifiers (`brahmainsurance`, `103.149.199.250`, `103.7.181.105`, `103.104.73.198`, `amazonaws.com`) are blocked at configuration validation time.
- **Additive Unified Registry + Legacy Table Dual-Write**: All document uploads write to the unified `tbl_documents` audit registry while atomically updating legacy physical tables/columns (`tbl_transaction`, `tbl_transactionappnew`, `tbl_app_requestedquotationfile`, `tbl_insurancecompanyquotation`, `tbl_app_quotationrequest`, `tbl_claimdocument`, `tbl_claim.audiofile`, `tbl_appendorsement.SupportingDocKey`).
- **Legacy Defect Remediation (`DEF-010`)**: Remediated the legacy cross-folder deletion bug (`CL_ClaimNew.aspx.cs:L354`) where replacing a `Claim_Final_Bill_Doc` file deleted files from `~/ClaimPhoto/` instead of `~/Claim_Final_Bill_Doc/`. Each document now stores its canonical `StorageKey` (`{LegacyVirtualFolder}/{entity_slug}/{entity_id}/{stored_filename}`) and replacement only supersedes the matching subtype/key.
- **Intentional Security Hardening**:
  - `PolicyParserWebhook.aspx` (`/api/v1/documents/webhooks/policy-parser`) enforces `X-Webhook-Secret` or `X-Calliber-Signature` HMAC-SHA256 verification before persisting to `tbl_calliber_policy_webhook` (`sp_InsertCalliberPolicyData` parity) and linking `tbl_transaction.calliber_policyId`.
  - `DownloadAll.ashx` (`/api/v1/documents/legacy/download-all`) and `ImageHandler.ashx` (`/api/v1/documents/legacy/image-handler`) require authenticated JWT RBAC and enforce object-level, branch-level, and principal-level (`agent_id`, `franchise_id`, `emp_id`) ownership checks.

---

## 2. Schema & Alembic Migration (`b11d0c5f1101`)
- **Migration Revision**: `b11d0c5f1101` (revises `a10c1a1m5001`)
- **Additive Tables Created**:
  1. `tbl_documents` (`DocumentRecord`):
     - Primary Key: `DocumentId` (`BIGINT AUTO_INCREMENT`)
     - Entity Polymorphism & Direct Foreign References: `DocumentType`, `DocSubType`, `EntityType`, `EntityId`, `TransId`, `QuotationId`, `ClaimId`, `EndorsementId`, `CustomerId`, `VehicleId`, `PaymentId`, `AgentId`, `FranchiseId`, `BranchId`
     - Storage & Integrity Metadata: `LegacyVirtualFolder`, `OriginalFilename`, `SanitizedFilename`, `StoredFilename`, `FileExtension`, `MimeType`, `FileSizeBytes`, `ChecksumSha256`, `StorageBackend`, `StorageKey` (unique), `LegacyTableRef`, `LegacyRecordId`
     - Versioning & Lifecycle: `Version`, `ReplacesDocumentId`, `Status` (`ACTIVE` / `REPLACED` / `DELETED`), `IsDeleted`, `IdempotencyKey` (unique)
     - Audit Metadata: `UploadedByUserId`, `UploadedByRole`, `CreatedDate`, `ModifyDate`, `DeletedDate`, `DeletedByUserId`, `Remark`
  2. `tbl_calliber_policy_webhook` (`PolicyParserWebhookRecord`):
     - Primary Key: `CalliberPolicyId` (`BIGINT AUTO_INCREMENT`)
     - Legacy `API_Calliber_Policy` Columns: `PolicyNo`, `InsuredName`, `InsurerName`, `RegistrationNo`, `EngineNo`, `ChassisNo`, `PolicyStartDate`, `PolicyEndDate`, `NetPremium`, `GST`, `TotalPremium`, `IDV`, `NCB`, `PlanName`, `VehicleMake`, `VehicleModel`, `DocumentFileName`, `DocumentId`, `TransId`, `PayloadHashSha256`, `RawPayloadJson`, `WebhookStatus`, `CreatedDate`

---

## 3. Legacy Virtual Folder & Dual-Write Parity Matrix

| Document Category (`DocumentType` / `DocSubType`) | Legacy Virtual Folder | Legacy Physical Table / Column Updated Atomically |
|---|---|---|
| `POLICY` / `POLICY_PDF`, `PROPOSAL_DOC`, `PREVIOUS_POLICY_DOC`, `VEHICLE_RC`, `AADHAR_DOC`, `PAN_DOC`, `GST_DOC`, `CHEQUE_IMAGE` | `TransactionDocument` | `tbl_transaction` (`PolicyDoc`, `ProposalDoc`, `PerviousPolicyDoc`, `VehicleRc`, `AadharDoc`, `PanDoc`, `GstDoc`, `ChequeImg`) |
| `POLICY` / `APP_POLICY_PDF` | `AppPolicyPdf` | `tbl_transactionappnew.PolicyPdfPath`, `tbl_transaction.PolicyDoc` |
| `QUOTATION` / `QUOTATION_PDF` | `PDF_Files` | `tbl_insurancecompanyquotation.QuotationPDF`, `tbl_app_quotationrequest.QuotationPdfPath` |
| `QUOTATION` / `QUOTATION_DOC` | `QuotationDoc` | `tbl_app_requestedquotationfile` (`sp_InsertRequestedQuotationFile` parity) |
| `CLAIM` / `CLAIM_PHOTO` | `ClaimPhoto` | `tbl_claimdocument` (`DocType = 'Claim_Doc'`, `sp_InsertClaimDocument` parity) |
| `CLAIM` / `FINAL_BILL_DOC` | `Claim_Final_Bill_Doc` | `tbl_claimdocument` (`DocType = 'Final_Bill_Doc'`, `DEF-010` remediated) |
| `CLAIM` / `CLAIM_AUDIO` | `ClaimAudio` | `tbl_claim.audiofile`, `tbl_claimdocument` (`DocType = 'Claim_Audio'`) |
| `ENDORSEMENT` / `SUPPORTING_DOC` | `EndorsementDoc` | `tbl_appendorsement.SupportingDocKey` |
| `AGENT` / `KYC` | `AgentDoc` | `tbl_documents` (`LegacyVirtualFolder = 'AgentDoc'`) |
| `POSP` | `POSDoc` | `tbl_documents` (`LegacyVirtualFolder = 'POSDoc'`) |

---

## 4. Documented UNKNOWN Items (Preserved Without Guessing)
In strict accordance with the legacy baseline (`docs/migration/legacy_baseline/`), the following 3 items remain explicitly documented as `UNKNOWN — REQUIRES AUTHORIZED EXTERNAL VERIFICATION`:
1. **`GAP-UNK-11-001`**: Physical SQL DDL and body of `sp_InsertCalliberPolicyData` in external schema `brahmainsurance` (not present in the legacy source repository dump; handled via additive `tbl_calliber_policy_webhook` + `tbl_transaction.calliber_policyId` linkage).
2. **`GAP-UNK-11-002`**: Physical SQL body of `sp_UpdateVehicleDetailsByQuotationId` (referenced in `QuotationEntry.aspx.cs` during quotation PDF generation; vehicle details are read directly from `tbl_vehicledetails` / `tbl_quotation` without speculative mutation).
3. **`GAP-UNK-11-003`**: Physical SQL body of `sp_InsertPolicyPdfApp` (referenced in `Service.asmx.cs` for mobile app policy PDF upload; handled via atomic dual-write to `tbl_transactionappnew.PolicyPdfPath` and `tbl_transaction.PolicyDoc`).

---

## 5. Verification & Regression Results
- **Phase 11 Unit & Integration Test Suite**: **14 passed**
  - `tests/unit/test_phase11_storage_and_naming.py` (6 passed)
  - `tests/integration/test_phase11_documents_security_and_rbac.py` (2 passed)
  - `tests/integration/test_phase11_golden_parity_and_webhooks.py` (3 passed)
  - `tests/integration/test_phase11_concurrency_atomicity_e2e.py` (3 passed)
- **Full Repository Regression Suite (Phases 0–11)**: **309 passed in 99.01s** (295 Phase 0–10 tests + 14 Phase 11 tests, 0 failures)
- **Production Isolation Check**: Verified `localhost:3306/reliable_insurance_dev`, `redis://localhost:6379/0`, and `STORAGE_BACKEND=local` (`./storage_data`). Zero production DB, S3/MinIO, or webhook access.
