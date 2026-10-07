# 01 — Legacy Project Inventory

> **Audit Status**: CONFIRMED FROM CODE & CONFIGURATION (READ-ONLY FORENSIC BASELINE)
> **Repository Root**: `c:\Users\Admin\Downloads\InsurancefinalNew_2026_09_23\InsurancefinalNew`
> **Solution File**: `InsurancefinalNew\Insurance.sln` (Visual Studio 2010 / Format Version 11.00)

---

## 1. Executive Architecture Summary

The legacy system (**Brahma / Reliable Insurance ERP**) is a monolithic 4-project **C# / .NET Framework 4.0** application combining an **ASP.NET WebForms** back-office portal (`Insurance\Clerk\*`), root-level operational/mobile web pages (`Insurance\*.aspx`), SOAP/JSON **ASMX Web Services** (`Service.asmx.cs`, `VehicleService.asmx.cs`), **ASHX HTTP Handlers** (`DownloadAll.ashx.cs`, `ImageHandler.ashx.cs`), a pass-through Business Logic Layer (`BLL`), a monolithic ADO.NET Data Access Layer (`DAL`), and a shared DTO/Entity library (`API`).

```
+-----------------------------------------------------------------------------------+
|                        CLIENTS & EXTERNAL CONSUMERS                               |
|  1. Clerk / Admin Web Browser (WebForms PostBack + jQuery AJAX PageMethods)       |
|  2. Mobile App (Android/iOS) & POSP Portal -> Calls Service.asmx SOAP/JSON        |
|  3. External Webhooks -> PolicyParserWebhook.aspx (HiCaliber PDF Parser)          |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
|                   WEB / PRESENTATION / SERVICE PROJECT (`Insurance`)              |
|  - 1240 `.aspx` WebForms pages (51 root + 0 in `Clerk\` + 3 in `TransactionDocument\`) |
|  - `Service.asmx.cs` (16,546 lines; 339 `[WebMethod]` endpoints; direct DAL/DB)   |
|  - `VehicleService.asmx.cs` (80 lines; 2 `[WebMethod]` endpoints)                 |
|  - `Clerk\SearchMethods.aspx.cs` (41 static `[WebMethod]` AJAX endpoints)        |
|  - `AppSearchMethod.aspx.cs` (16 static `[WebMethod]` AJAX endpoints)             |
|  - 18 additional `[WebMethod]` endpoints across 10 `.aspx.cs` files               |
|  - `DownloadAll.ashx.cs` & `ImageHandler.ashx.cs` (2 HTTP Handlers)               |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
|                        BUSINESS LOGIC LAYER (`BLL`)                               |
|  - `BLL\BLL_Operations.cs` (9,040 lines; 147 `BLL_*` classes)                    |
|  - Primarily thin pass-through wrappers delegating to `DAL_*` classes             |
|  - Note: Most domain calculations (rating, GST, TDS, ledger splits) live in       |
|    `.aspx.cs` code-behind and `Service.asmx.cs`, NOT in `BLL_Operations.cs`       |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
|                          DATA ACCESS LAYER (`DAL`)                                |
|  - `DAL\DAL_Operations.cs` (46,371 lines; 146 `DAL_*` classes)                   |
|  - `DAL\dbConnection.cs` (42 lines; `MySqlConnection` factory for `dbInsuranceCon`)|
|  - 1,896 Stored Procedure executions + 7 raw SQL queries in `DAL_Operations.cs`   |
|  - Note: `Service.asmx.cs` bypasses `DAL` in 442 SP calls & 117 raw SQL queries   |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
|                        SHARED ENTITY / DTO LAYER (`API`)                          |
|  - `API\AllMaster.cs` (3,806 lines; 188 `API_*` POCO classes)                  |
|  - `API\GeoLocationClasses.cs` (66 lines; geo/location helper models)            |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
|                     DATABASE (`brahmainsurance` on MySQL Port 3309)               |
|  - 1855 unique Stored Procedures invoked across `DAL` and `Service.asmx.cs`        |
|  - 19 raw SQL queries invoked across `.cs` files                                 |
|  - 0 `.sql` / DDL migration scripts committed in repository                       |
+-----------------------------------------------------------------------------------+
```

---

## 2. Solution & Project Matrix

| Project Name | Project File | Output Type | Target Framework | Key Source Files | Line Count | Purpose & Responsibilities |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **API** | `API\API.csproj` | Class Library (`Library`) | `.NET Framework v4.0` | `AllMaster.cs` (3,806 lines)<br>`GeoLocationClasses.cs` (66 lines) | 3,872 | Defines 188 data transfer / domain entity classes (`API_Customer`, `API_CustVehicle`, `API_Transaction`, `API_TransactionPayment`, `API_Account`, `API_QuotationSelf`, `API_Claims`, `API_Endorsement`, `API_tds`, etc.). Preserves legacy property misspellings (`TransanctionId`, `ODPermium`, `TPPermium`, `NetPermium`, `NCBPermium`, `QuatationCode`, `ChaiseNo`, `MoblieNo1`). |
| **DAL** | `DAL\DAL.csproj` | Class Library (`Library`) | `.NET Framework v4.0` | `DAL_Operations.cs` (46,371 lines)<br>`dbConnection.cs` (42 lines) | 46,413 | Executes ADO.NET `MySqlCommand` calls (`MySql.Data.MySqlClient`) against MySQL database `brahmainsurance`. Contains 146 `DAL_*` classes executing 1,896 stored procedure calls and 7 inline SQL statements. |
| **BLL** | `BLL\BLL.csproj` | Class Library (`Library`) | `.NET Framework v4.0` | `BLL_Operations.cs` (9,040 lines) | 9,040 | Contains 147 `BLL_*` classes that instantiate corresponding `DAL_*` classes and forward parameters directly. Contains zero transaction management and minimal business logic. |
| **Insurance** | `Insurance\Insurance.csproj` | ASP.NET Web Application (`Library` / IIS Web Project) | `.NET Framework v4.0` | `Service.asmx.cs` (16,546 lines)<br>`VehicleService.asmx.cs` (80 lines)<br>1240 `.aspx` pages & `.aspx.cs` code-behind<br>2 `.ashx.cs` handlers<br>49 `.rdlc` reports & 28 `.xsd` datasets | ~385,000+ | Hosts all UI pages, core business/financial workflows in code-behind (`PE_TransactionEntry.aspx.cs` is 12,788 lines; `PolicyNoUpdatePushNoti.aspx.cs` is 7,600+ lines; `CashierApprovalNew.aspx.cs` is 6,200+ lines; `AgentCommissionRecalculation.aspx.cs` is 5,100+ lines), mobile/partner ASMX web services, external API integrations, and RDLC reporting. |

---

## 3. Third-Party Libraries, NuGet Packages & References

**Evidence**: `Insurance\packages.config`, `Insurance\Insurance.csproj`, `DAL\DAL.csproj`

| Library / Assembly | Version / HintPath | Project(s) | Purpose in Legacy System |
| :--- | :--- | :--- | :--- |
| `MySql.Data` | `6.9.9.0` (`v4.0`) | `DAL`, `Insurance` | ADO.NET driver (`MySqlConnection`, `MySqlCommand`, `MySqlDataAdapter`) for MySQL database `brahmainsurance`. |
| `Newtonsoft.Json` | `13.0.3` (`net40`) | `Insurance` | JSON serialization/deserialization in `Service.asmx.cs`, `PolicyParserWebhook.aspx.cs`, Signzy RC check, and HiCaliber API calls. |
| `itextsharp` | `5.x` (`bin\itextsharp.dll`) | `Insurance` | PDF generation and reading (quotation PDFs, POSP invoices, policy documents). |
| `BouncyCastle.Crypto` | `bin\BouncyCastle.Crypto.dll` | `Insurance` | Cryptographic dependency for iTextSharp PDF manipulation. |
| `ClosedXML` & `DocumentFormat.OpenXml` | `2.5.5631.0` | `Insurance` | Excel (`.xlsx`) import/export for MIS bulk policy import (`adm_ImportTransAgentPolicyMIS.aspx.cs`) and financial reports. |
| `Excel` (`ExcelDataReader`) | `bin\Excel.dll` | `Insurance` | Reading uploaded `.xls`/`.xlsx` files in MIS bulk import workflows. |
| ` Ionic.Zip` | `bin\Ionic.Zip.dll` | `Insurance` | Creating `.zip` archives of policy/claim documents in `DownloadAll.ashx.cs` and `CL_ClaimNew.aspx.cs`. |
| `Microsoft.ReportViewer.WebForms` | `10.0.0.0` | `Insurance` | Rendering 49 local `.rdlc` reports (`Insurance\Report\*`). |
| `AjaxControlToolkit` | `bin\AjaxControlToolkit.dll` | `Insurance` | ASP.NET WebForms UI extenders (calendars, modal popups, autocomplete). |

### Legacy Web References (`Insurance\Web References\`)
1. **`InsuranceAppService`**: Points to `http://103.76.188.138:85/Service.asmx` (`Reference.cs` exposes `insertPolicy`, `insertPolicyAsync` taking `TransDate, PolicyType, Name, ContactNo, ODDiscount, NCB, Premium, IDV, IMT23, UserId`).
2. **`VantageService`**: Points to external Vantage POSP integration web service (`VantageTestingNewServer.aspx.cs`).

---

## 4. Configuration & Environment Structure (Sanitized)

**Evidence**: `Insurance\Web.config` (Lines 1–185)

### 4.1 Database Connection Strings (`<connectionStrings>`)
| Name | Provider | Target Server / Port / DB | Connection Options | Usage |
| :--- | :--- | :--- | :--- | :--- |
| `dbInsuranceCon` | `MySql.Data.MySqlClient` | `server=localhost; port=3309; database=brahmainsurance; user id=root; password=***MASKED***` | `pooling=false; default command Timeout=4200; Allow User Variables=True` | Primary connection string used by `DAL\dbConnection.cs` (`L16`) and `Insurance\Service.asmx.cs` (`L35`). |

### 4.2 Application Settings (`<appSettings>`)
| Key | Sanitized Value / Pattern | Purpose |
| :--- | :--- | :--- |
| `ValidationSettings:UnobtrusiveValidationMode` | `None` | WebForms validation mode. |
| `ChartImageHandler` | `storage=file;timeout=20;dir=c:\TempImageFiles\;` | ASP.NET Chart control temporary storage. |
| `pdfpath` | `http://localhost:2155/` (or production base URL) | Base URL prefix used when embedding/splitting PDF paths in `ViewAppTransEwalletApproval.aspx.cs` (`L367`), `PE_TransactionEntry.aspx.cs`, etc. |
| `FolderPath` | `~/TransactionDocument/` | Upload directory path for transaction attachments. |

### 4.3 HTTP Runtime, Session & Authentication Settings (`<system.web>`)
- **Authentication Mode**: `<authentication mode="Forms" />` is declared in `Web.config`, **HOWEVER**, actual authentication is enforced manually via `Session["UserId"]`, `Session["UserRole"]`, `Session["RoleId"]`, and `Session["BranchId"]` in `Log_In.aspx.cs` and page `Page_Load` checks.
- **Session State**: In-process (`InProc`) ASP.NET session state (`timeout="60"`).
- **Request Limits**: `maxRequestLength="2147483647"` (~2 GB), `executionTimeout="999999"`.
- **Web Services Protocols**: `HttpGet`, `HttpPost`, `HttpPostLocalhost`, `Documentation` enabled for `.asmx` services (`Web.config`).
- **JSON Serialization Limit**: `maxJsonLength="2147483644"` in `<system.web.extensions>`.

---

## 5. Complete File & Module Distribution in `Insurance` Web Project

| Subdirectory / Module | File Count | Primary Files & Responsibilities |
| :--- | :--- | :--- |
| `Insurance\` (Root) | 51 `.aspx`<br>2 `.asmx`<br>2 `.ashx`<br>4 helper `.cs` | `Log_In.aspx.cs`, `Log_Out.aspx.cs`, `Service.asmx.cs`, `VehicleService.asmx.cs`, `AppPolicyRequestNew1_2026.aspx.cs`, `AppSearchMethod.aspx.cs`, `PolicyParserWebhook.aspx.cs`, `POSP_MultiEntryIdealPayment.aspx.cs`, `Adm_LockChequeEntry.aspx.cs`, `adm_LockCashEntry1.aspx.cs`, `Send_SMS.cs`, `ExceptionLogging.cs`, `DownloadAll.ashx.cs`, `ImageHandler.ashx.cs`. |
| `Insurance\Clerk\` | 0 `.aspx` | Core ERP back-office modules:<br>- **Customer & Vehicle**: `adm_CustomerDetails.aspx.cs`, `adm_VehicleDetails.aspx.cs`, `adm_UpdateCustomer.aspx.cs`, `adm_UpdateCustVehicle.aspx.cs`, `RC_CheckVehicleDtl.aspx.cs`<br>- **Quotation & Rating**: `SelfQuotationRequest.aspx.cs`, `SelfQuotationRequest3_W_GCV.aspx.cs`, `SelfQuotationRequest3_W_PCV.aspx.cs`, `SelfQuotationRequestMISC_D.aspx.cs`, `ViewAppQuotationTransction.aspx.cs`<br>- **Policy Booking & Inward**: `PolicyTransactionNew.aspx.cs`, `PolicyTransactionNew1.aspx.cs`, `PE_TransactionEntry.aspx.cs`, `PE_TransactionEntry_2026.aspx.cs`, `adm_PolicyDetails.aspx.cs`, `MotorTransactionEntry.aspx.cs`, `NewPolicyEntry.aspx.cs`, `adm_NonMotarTransaction.aspx.cs`, `NonMotorPolicyDetails.aspx.cs`, `PolicyNoUpdatePushNoti.aspx.cs`<br>- **Payments, Cheques & E-Wallet**: `CashierApproval.aspx.cs`, `CashierApprovalNew.aspx.cs`, `AccountantApproval.aspx.cs`, `adm_AppTransactionCashApproval.aspx.cs`, `adm_AppTransactionCashApprovalNew.aspx.cs`, `ViewAppTransactionChequeApproval.aspx.cs`, `Rpt_viewChequeClearing.aspx.cs`, `Rpt_ChequeClearingByadmin.aspx.cs`, `ViewAppTransEwalletApproval.aspx.cs`, `IdealPaymentReceipt.aspx.cs`<br>- **Commission, TDS, Ledger & Vouchers**: `AgentCommisionPayment.aspx.cs`, `AgentCommissionRecalculation.aspx.cs`, `AgentCommissionRecalculationRS_Date.aspx.cs`, `adm_tdsForAgent.aspx.cs`, `adm_tdsrateforBroker.aspx.cs`, `adm_VoucherEntry.aspx.cs`, `adm_LedgerMaster.aspx.cs`, `Report_Account_By_LedgerType.aspx.cs`<br>- **Claims & Endorsements**: `CL_ClaimNew.aspx.cs`, `AppEndorsementforApproval.aspx.cs`, `OwnerTransferEndorsement.aspx.cs`, `adm_NcbRecovery.aspx.cs`, `adm_PolicyCancel.aspx.cs` |
| `Insurance\TransactionDocument\` | 3 `.aspx` | `Adm_AgentCommissionForApp.aspx.cs` (Agent Commission Statement & PDF/HTML export). |
| `Insurance\Report\` | 49 `.rdlc`<br>28 `.xsd` | Typed datasets (`Ds_AgentCommPaidUnpaid.xsd`, etc.) and RDLC report definitions for vouchers, receipts, ledgers, commission statements, and MIS exports. |

---

## 6. External Integrations Confirmed in Code

| Integration | Source Files & Line Numbers | Protocol / Mechanism | Purpose | Secrets Status |
| :--- | :--- | :--- | :--- | :--- |
| **Signzy Vehicle RC Verification API** | `Insurance\Clerk\RC_CheckVehicleDtl.aspx.cs` (`L95–190`)<br>`Insurance\DemoRC.aspx.cs`<br>`Insurance\demoRC_2.aspx.cs`<br>`Insurance\Service.asmx.cs` | HTTPS REST POST (`https://api.signzy.app/api/v3/vehicle/detailedsearches`) | Fetches live RTO/Vahan vehicle details (Owner Name, Chassis No, Engine No, Make, Model, Fuel Type, Reg Date, GVW, Cubic Capacity, Insurance Expiry) by Registration Number. | Hardcoded `Authorization` bearer token and `x-client-unique-id` present in `.cs` source — **MASKED** in all baseline docs. |
| **HiCaliber Policy PDF Parser & Webhook** | `Insurance\PolicyParserWebhook.aspx.cs` (`L1–180`)<br>`Insurance\PDF_ExtractionDemo_NEW_IDEAL.aspx.cs`<br>`Insurance\Clerk\PE_TransactionEntry.aspx.cs` | Multipart HTTP POST + Webhook callback (`PolicyParserWebhook.aspx`) | Uploads insurer policy PDFs to HiCaliber (`api.hicaliber.in`) and receives parsed policy JSON (Policy No, OD/TP/Net/Total Premium, IDV, NCB, Risk Dates, Vehicle No) via webhook. | API token in source — **MASKED**. |
| **SMS Gateway (`Send_SMS.cs`)** | `Insurance\Send_SMS.cs` (`L1–120`)<br>`Insurance\Service.asmx.cs` | HTTP GET (`http://sms.hspsms.com/sendSMS` / `bulksms`) | Sends transactional SMS for OTPs, policy issuance, cheque bounce, NCB recovery (`adm_NcbRecovery.aspx.cs` L1081), and endorsement approval. | Sender ID & API key in source — **MASKED**. |
| **OneSignal Push Notifications** | `Insurance\SendPushNotiRenewal.aspx.cs`<br>`Insurance\SendPushNotiToAgentForRenewal.aspx.cs`<br>`Insurance\Clerk\PolicyNoUpdatePushNoti.aspx.cs` | HTTPS POST (`https://onesignal.com/api/v1/notifications`) | Sends mobile push notifications to Agents/Customers upon policy number generation, quotation readiness, and renewal reminders. | App ID & REST API Key in source — **MASKED**. |
| **SMTP Email (`System.Net.Mail`)** | `Insurance\SendMailToAutority.aspx.cs`<br>`Insurance\Service.asmx.cs` | SMTP (`smtp.gmail.com` port 587) | Sends automated authority emails, OTPs, and reports. | Credentials in source — **MASKED**. |
