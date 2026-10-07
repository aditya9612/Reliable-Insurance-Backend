# 17 — Legacy Document, Upload & File Handling Baseline

> **Forensic Classification**: `CONFIRMED FROM CODE`  
> **Scope**: Physical file upload directories, naming conventions, database path storage, PDF generation, ZIP streaming (`DownloadAll.ashx.cs`), image serving (`ImageHandler.ashx.cs`), and OCR/PDF parsing (`PolicyParserWebhook.aspx.cs`).

---

## 1. Upload Directory & Storage Matrix

All legacy file uploads are stored directly on the local web server filesystem using `Server.MapPath(...)`. No cloud object storage (S3/GCS/Azure Blob) is used in the legacy codebase.

| Functional Area | Virtual Path (`Server.MapPath`) | File Naming Convention | DB Table / Column Reference | Source File & Lines |
|---|---|---|---|---|
| **Policy / Transaction Documents** | `~/TransactionDocument/` | `<TransactionId>_<DocType>_<OriginalFileName>` or `<DateTime>_<FileName>` | `tbltransaction` (`PolicyDoc`, `RCBookDoc`, `PrevPolicyDoc`, `OtherDoc`), `tbltransactiondocument` | `PolicyTransactionNew.aspx.cs`, `PE_TransactionEntry.aspx.cs`, `DownloadAll.ashx.cs:L59` |
| **Mobile / App Policy PDFs** | `~/AppPolicyPdf/` | `<PolicyNo>.pdf` or `<TransactionId>_Policy.pdf` | `tbltransaction` / `tblapppolicypdf` | `Service.asmx.cs`, `AppEndorsementforApproval.aspx.cs` |
| **Generated Quotation PDFs** | `~/PDF_Files/` | `Quotation_<QuotationId>.pdf` (or `<QuatationCode>.pdf`) | `tblquotation` (`PDFPath`) | `Qt_QuotationRateCalculation.aspx.cs`, `SelfQuotationRequest.aspx.cs` |
| **Uploaded Quotation Supporting Docs** | `~/QuotationDoc/` | `<QuotationId>_<FileName>` | `tblquotation` / `tblquotationdoc` | `Qt_QuotationRequest.aspx.cs`, `Service.asmx.cs` |
| **Claim Spot Survey / Incident Photos** | `~/ClaimPhoto/` | `temp_FBId + DateTime.Now.ToString("yyyyMMddHHmmss") + "Img" + i + ".jpeg"` | `tblclaimspotphoto` / `tblclaim` (`SpotPhoto`) | `Clerk/CL_ClaimNew.aspx.cs:L251, L342` |
| **Claim Final Bill Documents** | `~/Claim_Final_Bill_Doc/` | `temp_FBId + DateTime.Now.ToString("yyyyMMddHHmmss") + "Img" + i + ".jpeg"` | `tblclaimfinalbilldoc` / `tblclaim` (`FinalBillDoc`) | `Clerk/CL_ClaimNew.aspx.cs:L274, L365` |
| **Claim Voice / Audio Notes** | `~/Clerk/ClaimAudio/` | `date1 + i + ".mp3"` (where `date1 = DateTime.Now.ToString("yyyyMMddHHmmss")`) | `tblclaim` (`AudioFile`) | `Clerk/CL_ClaimNew.aspx.cs:L157, L219` |
| **Endorsement Supporting Proof Docs** | `~/EndorsementDoc/` or `~/TransactionDocument/` | `<EndorsementId>_<FileName>` | `tblendorsement` (`DocPath` / `Document1`, `Document2`) | `Endorsment_Request.aspx.cs`, `AppEndorsementforApproval.aspx.cs` |
| **POS / Agent KYC Documents** | `~/AgentDoc/` or `~/POSDoc/` | `<AgentId>_PAN.jpg`, `<AgentId>_Aadhar.jpg`, `<AgentId>_Cert.pdf` | `tblagent` / `tblposregistration` | `Service.asmx.cs`, `adm_AgentMaster.aspx.cs` |
| **Exception Log Files** | `~/ExceptionDetailsFile/` | `<dd-MM-yy>.txt` | Filesystem only | `App_Code/ExceptionLogging.cs:L26` |

---

## 2. HTTP Handlers (`.ashx`) for File Delivery

### 2.1 Bulk Document ZIP Download (`DownloadAll.ashx.cs`)
- **File**: `InsurancefinalNew/DownloadAll.ashx.cs` (L1–L90)
- **Trigger**: `GET /DownloadAll.ashx?TransId=<encrypted_or_raw_id>&PolicyNo=<policy_no>`
- **Behavior**:
  1. Queries document filenames associated with the transaction (`BLL_SelectTransactionDocumentByTransId`).
  2. Instantiates `Ionic.Zip.ZipFile` (`DotNetZip` library).
  3. Resolves each file under `context.Server.MapPath("~/TransactionDocument/" + fileName)`.
  4. If `File.Exists(filePath)` is true, adds file to the ZIP archive (`zip.AddFile(filePath, "Files")`).
  5. Sets HTTP response headers:
     - `context.Response.ContentType = "application/zip";`
     - `context.Response.AddHeader("content-disposition", "attachment; filename=" + PolicyNo + ".zip");`
  6. Streams ZIP archive directly to `context.Response.OutputStream`.

### 2.2 Image Streaming Handler (`ImageHandler.ashx.cs`)
- **File**: `InsurancefinalNew/ImageHandler.ashx.cs` (L1–L45)
- **Trigger**: `GET /ImageHandler.ashx?Id=<id>`
- **Behavior**:
  - Streams binary image data (`byte[]`) or resolves image path from DB and writes to `context.Response.OutputStream` with `ContentType = "image/jpeg"` (or `"image/png"`).

---

## 3. PDF Generation & Parsing Workflows

### 3.1 Quotation Comparison & Proposal PDF Generation
- **Libraries Used**: `iTextSharp` (`iTextSharp.text`, `iTextSharp.text.pdf`, `iTextSharp.tool.xml`) and `SelectPdf` (`HtmlToPdf`).
- **Files**: `Qt_QuotationRateCalculation.aspx.cs`, `SelfQuotationRequest.aspx.cs`, `SelfQuotationRequestTwoWheeler.aspx.cs`, `SelfQuotationRequestPCV.aspx.cs`, `SelfQuotationRequestMISC_D.aspx.cs`.
- **Behavior**:
  - Renders HTML template containing vehicle details, IDV, add-ons, and multi-insurer premium comparison table.
  - Converts HTML to PDF and saves to `Server.MapPath("~/PDF_Files/Quotation_" + quotId + ".pdf")`.
  - Optionally emails PDF attachment via `SendMail` or exposes download link to the client/POS agent.

### 3.2 Automated Policy PDF Parsing Webhook (`PolicyParserWebhook.aspx.cs`)
- **File**: `InsurancefinalNew/PolicyParserWebhook.aspx.cs` (L1–L145)
- **External Integration**: **HiCaliber** Policy PDF OCR/Parser service.
- **Behavior**:
  - Receives JSON webhook payload containing extracted policy fields (`PolicyNo`, `CustomerName`, `VehicleRegNo`, `EngineNo`, `ChassisNo`, `ODPremium`, `TPPremium`, `NetPremium`, `GrossPremium`, `StartDate`, `EndDate`, `InsCompany`).
  - Persists parsed fields via `DAL_Operations` / `BLL_Operations` to pre-populate policy entry forms.

---

## 4. Known File-Handling Defect (`CONFIRMED FROM CODE`)
- **Claim Final Bill Document Delete Path Mismatch**:
  - In `Clerk/CL_ClaimNew.aspx.cs`:
    - On **Insert** (`L274`), Final Bill documents are saved to `Server.MapPath("~/Claim_Final_Bill_Doc/")`.
    - On **Update** (`L354`), before saving replacement Final Bill documents to `~/Claim_Final_Bill_Doc/` (`L365`), the code attempts to delete the old file from `Server.MapPath("~/ClaimPhoto/" + file)` (`L354`) instead of `~/Claim_Final_Bill_Doc/`.
    - **Result**: Old Final Bill documents in `~/Claim_Final_Bill_Doc/` are never deleted on update, and if a file with the same name existed in `~/ClaimPhoto/`, it would be erroneously deleted.
