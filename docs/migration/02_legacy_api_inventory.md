# 02 — Legacy API & Entry Point Inventory

> **Audit Status**: CONFIRMED FROM CODE & ROUTING DEFINITIONS
> **Total Programmatic API Endpoints (`[WebMethod]` + `.ashx`)**: **418** (416 `[WebMethod]` endpoints + 2 `.ashx` HTTP handlers)
> **Total WebForms UI/Code-Behind Pages (`.aspx`)**: **1240**

---

## 1. Entry Point Summary by Category

| Category | File(s) | Endpoint Count | Protocol / Format | Authentication Mechanism | Primary Consumers |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Primary Mobile & Partner Web Service** | `Insurance\Service.asmx.cs` | **339** `[WebMethod]` | SOAP 1.1/1.2, HTTP POST, JSON (`Context.Response.Write`) | **NONE** at transport/attribute level (accepts `UserId`, `AgentId`, `RoleId`, `BranchId` as request parameters; login methods validate credentials). | Mobile App (Android/iOS), POSP Portal, Franchise App. |
| **Vehicle Lookup Web Service** | `Insurance\VehicleService.asmx.cs` | **2** `[WebMethod]` | SOAP / JSON | **NONE** | Internal autocomplete / vehicle lookup. |
| **Clerk Portal AJAX PageMethods** | `Insurance\Clerk\SearchMethods.aspx.cs` | **41** `[WebMethod]` (`static`) | HTTP POST JSON (`application/json`) | Relies on browser cookie / mostly unvalidated `static` methods taking filter parameters. | Clerk WebForms UI (`Clerk\*.aspx`) via jQuery `$.ajax`. |
| **App Request AJAX PageMethods** | `Insurance\AppSearchMethod.aspx.cs` | **16** `[WebMethod]` (`static`) | HTTP POST JSON (`application/json`) | Unvalidated `static` methods. | Root-level App Policy Request pages (`AppPolicyRequestNew1_2026.aspx`). |
| **Page-Specific AJAX WebMethods** | 10 `.aspx.cs` files (`GraphicalDashBoard*.aspx.cs`, `DashBorad*.aspx.cs`, `Location.aspx.cs`, `MIS_RequestExective.aspx.cs`, `rpt_POSP_Invoice*.aspx.cs`, `SendPushNoti*.aspx.cs`) | **18** `[WebMethod]` | HTTP POST JSON | Session / Page context. | Dashboard charts, GPS location tracking, POSP invoice generation. |
| **Binary / File HTTP Handlers** | `Insurance\DownloadAll.ashx.cs`<br>`Insurance\ImageHandler.ashx.cs` | **2** `IHttpHandler` | HTTP GET (`QueryString`) | **NONE** (accepts file/image ID or path via query string). | Document ZIP download and image rendering. |
| **External Webhook Receiver** | `Insurance\PolicyParserWebhook.aspx.cs` | **1** `Page_Load` POST | HTTP POST (`multipart/form-data` / JSON) | **NONE** (public webhook endpoint). | HiCaliber PDF extraction callback. |
| **Back-Office WebForms PostBack Pages** | `Insurance\Clerk\*.aspx.cs` & `Insurance\*.aspx.cs` | **1240** pages | HTTP POST (`__doPostBack` + `ViewState`) | Checks `Session["UserId"]` / `Session["UserRole"]` in `Page_Load` (inconsistently applied; see File 12). | Clerk, Admin, Cashier, Accountant, Franchise, Coordinator, Telecaller, Claim handlers. |

---

## 2. HTTP Handlers (`.ashx`) & Webhook Entry Points

| Entry Point | File & Line | HTTP Method | Query / Body Parameters | Database / File Operations | Security / Forensic Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `DownloadAll.ashx` | `Insurance\DownloadAll.ashx.cs` (L19–85) | `GET` | Query parameters for transaction/claim document archive | Reads files from server disk using `Ionic.Zip` (`ZipFile`) and streams `application/zip` to `context.Response`. | `IsReusable => false`. No session check in `ProcessRequest`. |
| `ImageHandler.ashx` | `Insurance\ImageHandler.ashx.cs` (L18–65) | `GET` | `id` / image identifier | Queries DB for binary/file image data and writes to `context.Response.OutputStream`. | No session check in `ProcessRequest`. |
| `PolicyParserWebhook.aspx` | `Insurance\PolicyParserWebhook.aspx.cs` (L18–175) | `POST` | JSON payload from HiCaliber PDF parser | Parses JSON fields (PolicyNo, RegistrationNo, OD/TP/Net/Total Premium, IDV, NCB, Insurer) and updates/inserts parsed policy record via `DAL`/`MySqlCommand`. | Publicly callable webhook endpoint. |

---

## 3. Core WebForms Transaction Entry Points (Phases 5–10)

| Phase | Functional Area | Primary `.aspx.cs` Entry Point(s) | Key Event Handlers | BLL / DAL / SP Invocations |
| :--- | :--- | :--- | :--- | :--- |
| **Phase 5** | Customer, Vehicle & RBAC | `Log_In.aspx.cs`<br>`Clerk\adm_CustomerDetails.aspx.cs`<br>`Clerk\adm_VehicleDetails.aspx.cs`<br>`Clerk\RC_CheckVehicleDtl.aspx.cs` | `btnLogIn_Click` (L38)<br>`btnSave_Click`<br>`btnCheckRC_Click` | `BLL_CheckLogin` (`usp_CheckLogin`), `BLL_CheckLoginfrFranchise` (`usp_CheckLoginForFranchise`), `BLL_InsertCustomer` (`usp_CustomerOperation`), `BLL_InsertVehicleDetails` (`usp_VehicleDetailsOperation`). |
| **Phase 6** | Quotation, Rating & Premium Calculation | `Clerk\SelfQuotationRequest.aspx.cs`<br>`Clerk\SelfQuotationRequest3_W_GCV.aspx.cs`<br>`Clerk\SelfQuotationRequest3_W_PCV.aspx.cs`<br>`Clerk\SelfQuotationRequestMISC_D.aspx.cs`<br>`Clerk\adm_PolicyDetails.aspx.cs` | `GetQuotationPremium` (L890)<br>`SaveData` (L1394)<br>`txt_TPPremium_TextChanged` (L622)<br>`txt_ODPremium_TextChanged` (L704) | `BLL_SelectMgfyearOfyearmonth`, `BLL_SelectRTOByIDself`, `BLL_quot_liabilitypremium` (`usp_quot_liabilitypremium`), `BLL_quot_damagepremium` (`usp_quot_damagepremium`), `BLL_SelectTowingChargesByCompanyId`, `BLL_GetQuotationCodeForSelfQuotation`, `BLL_InsertAppQuotationEntry` (`usp_InsertAppQuotationEntry`). |
| **Phase 7** | Policy Booking, Inward & Transaction | `Clerk\PolicyTransactionNew.aspx.cs`<br>`Clerk\PE_TransactionEntry.aspx.cs`<br>`Clerk\PE_TransactionEntry_2026.aspx.cs`<br>`Clerk\PolicyNoUpdatePushNoti.aspx.cs`<br>`AppPolicyRequestNew1_2026.aspx.cs` | `btnSave_Click` (L1214)<br>`InsertTransaction` (L960)<br>`InsertFranchiseDetails` (L1446)<br>`AccountEntry_2025` (L9580) | `BLL_generateCustomerCode`, `BLL_generateInwardNo`, `BLL_InsertTransaction` (`usp_TransactionOperation`), `BLL_InsertFranchaiseComm` (`usp_FranchaiseCommissionOperation`), `BLL_TransactionPaymentOpration` (`usp_TransactionPaymentOpration`), `BLL_UpdatePolicyNo`, `BLL_UpdateStatusForInvert`. |
| **Phase 8** | Payments, Cheques, Reconciliation & E-Wallet | `Clerk\CashierApprovalNew.aspx.cs`<br>`Clerk\AccountantApproval.aspx.cs`<br>`Clerk\adm_AppTransactionCashApprovalNew.aspx.cs`<br>`Clerk\Rpt_viewChequeClearing.aspx.cs`<br>`Clerk\ViewAppTransEwalletApproval.aspx.cs`<br>`Adm_LockChequeEntry.aspx.cs` | `btnApprove_Click`<br>`btnBounce_Click`<br>`btn_Upload_Click` (L435)<br>`OnlintoRAEntry` (L10141) | `BLL_PaymentApproval` (`usp_PaymentApproval`), `BLL_AgentCommWalletBalance` (`usp_AgentCommWalletBalance`), `BLL_selectEwalletBalanceApprovedetails`, `BLL_UpdateAppPolicyAccountApproval1`, `BLL_InsertAccountDetails` (`usp_AccountDetailsOperation`), `BLL_InsertClearingAccountDetails` (`usp_ClearingAccountDetailsOperation`). |
| **Phase 9** | Commission, TDS, Cut & Pay, Ledger, Voucher & Trial Balance | `Clerk\AgentCommisionPayment.aspx.cs`<br>`Clerk\AgentCommissionRecalculation.aspx.cs`<br>`Clerk\adm_tdsForAgent.aspx.cs`<br>`Clerk\adm_tdsrateforBroker.aspx.cs`<br>`Clerk\adm_VoucherEntry.aspx.cs`<br>`Clerk\Report_Account_By_LedgerType.aspx.cs` | `btnCalc_Click` (L1875)<br>`AgentCommissionPaymentTableentry` (L9817)<br>`FranchiseAccountEntry` (L10035)<br>`btnSaveVoucher_Click` | `BLL_SelectFranchiseCommission` (`usp_SelectFranchiseCommission`), `BLL_GetDiscountByRange`, `BLL_InsertAgentCommPayment` (`usp_AgentCommPaymentOperation`), `BLL_UpdateAgentCommissionPay` (`usp_UpdateAgentCommissionPay`), `BLL_Inserttdsforagent` (`usp_tdsforagent`), `BLL_tdsforbroker` (`usp_tdsforbroker`), `BLL_InsertAccountDetails` (`LedgerMId = 2113` TDS, `LedgerMId = 1161` Comm, `LedgerMId = 1930` SalesEx). |
| **Phase 10** | Claims, Endorsements, NCB Recovery & Policy Cancellation | `Clerk\CL_ClaimNew.aspx.cs`<br>`Clerk\AppEndorsementforApproval.aspx.cs`<br>`Clerk\OwnerTransferEndorsement.aspx.cs`<br>`Clerk\adm_NcbRecovery.aspx.cs`<br>`Clerk\adm_PolicyCancel.aspx.cs` | `Save4_Click` (L251)<br>`Save3_Click` (L407)<br>`btnApprove_click` (L199)<br>`btnSave_Click` (L205)<br>`btn_Recovery_Click` (L1072)<br>`ReturnUnclearingCheque` (L888) | `BLL_Claim_FINALBILL_Insert`, `BLL_ClaimQuotaionInsert`, `BLL_ClaimAudio`, `DAL_InsertAccountDetailsendos` (`LedgerMId = 1878`), `BLL_EndosementCashierApprovalStatus`, `BLL_UpdateEndorsement` (`usp_UpdateEndorsement`), `BLL_EndorsementHistoryOpration` (`usp_EndorsementHistoryOperation`), `BLL_InsertNCBRecovery` (`usp_InsertNCBRecovery`), `BLL_UpdateAgentCommissionPay(..., "PolicyCancel")`. |

---

## 4. Complete Inventory of All 416 `[WebMethod]` Endpoints

| # | File | Line | Method Name | Return Type | Parameters | Stored Procedures / BLL Called |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | `Insurance\AppSearchMethod.aspx.cs` | L26 | `GetCustVehicleNo` | `string[]` | `string prefix` | `BLL_CustVehicle, BLL_obj, BLL_SerachcustVehicle` |
| 2 | `Insurance\AppSearchMethod.aspx.cs` | L45 | `GetCustName` | `string[]` | `string prefix` | `BLL_Customer, BLL_obj, BLL_SearchCustName` |
| 3 | `Insurance\AppSearchMethod.aspx.cs` | L64 | `GetAgentName` | `string[]` | `string prefix` | `BLL_Agent, BLL_obj, BLL_SearchAgentName` |
| 4 | `Insurance\AppSearchMethod.aspx.cs` | L85 | `GetPolicyNo` | `string[]` | `string prefix` | `BLL_Transaction, BLL_obj, BLL_searchPolicyNo` |
| 5 | `Insurance\AppSearchMethod.aspx.cs` | L105 | `GetPolicyNoByCheqe` | `string[]` | `string prefix` | `BLL_Transaction, BLL_obj, BLL_SearchPolicyNobyCheque` |
| 6 | `Insurance\AppSearchMethod.aspx.cs` | L124 | `checkVehicleNo` | `string` | `string vehNo, string FinancialYear` | `BLL_CustVehicle, BLL_CheckRegistrationNo, BLL_ViewAppTransaction` |
| 7 | `Insurance\AppSearchMethod.aspx.cs` | L140 | `getNewAppEntry` | `string` | `` | `BLL_ViewAppTransaction, BLL_obj, BLL_APPEntryPopUp` |
| 8 | `Insurance\AppSearchMethod.aspx.cs` | L154 | `pie_Premium_Summary1` | `string` | `` | `BLL_DashBoard, BLL_PolicyType_Summary, BLL_ODPremium_Summary` |
| 9 | `Insurance\AppSearchMethod.aspx.cs` | L185 | `pie_ODPremium_Summary` | `string` | `` | `BLL_DashBoard, BLL_ODPremium_Summary, BLL_ODNetPremium_Summary` |
| 10 | `Insurance\AppSearchMethod.aspx.cs` | L225 | `pie_ODNetPremium_Summary` | `string` | `` | `BLL_DashBoard, BLL_ODNetPremium_Summary, BLL_ODNetMonthlyPremium` |
| 11 | `Insurance\AppSearchMethod.aspx.cs` | L257 | `pie_ODNetMonthlyPremium` | `string` | `` | `BLL_DashBoard, BLL_ODNetMonthlyPremium, BLL_ODNetDailyPremium` |
| 12 | `Insurance\AppSearchMethod.aspx.cs` | L288 | `pie_ODNetDailyPremium` | `string` | `` | `BLL_DashBoard, BLL_ODNetDailyPremium, BLL_PolicyMode_Summary` |
| 13 | `Insurance\AppSearchMethod.aspx.cs` | L319 | `PolicyMode_Premium_Summary1` | `string` | `` | `BLL_DashBoard, BLL_PolicyMode_Summary, BLL_BusinessType_Summary` |
| 14 | `Insurance\AppSearchMethod.aspx.cs` | L351 | `businesstype_Premium_Summary1` | `string` | `` | `BLL_DashBoard, BLL_BusinessType_Summary, BLL_ProductType_Summary` |
| 15 | `Insurance\AppSearchMethod.aspx.cs` | L385 | `ProductType_Premium_Summary1` | `string` | `` | `BLL_DashBoard, BLL_ProductType_Summary, BLL_DashBoardInsuranceCompany` |
| 16 | `Insurance\AppSearchMethod.aspx.cs` | L418 | `DashBoardInsuranceCompany` | `string` | `` | `BLL_DashBoard, BLL_DashBoardInsuranceCompany` |
| 17 | `Insurance\ImageHandler.ashx.cs` | L35 | `GetImageFile` | `byte[]` | `string fileName` | `Direct / Helper` |
| 18 | `Insurance\SendPushNotiForBdayWish.aspx.cs` | L91 | `InsertPushNotiRenewal` | `string` | `string ExternalId, string Status` | `BLL_CustVehicle, BLL_InsertPushNotiRenewal` |
| 19 | `Insurance\SendPushNotiRenewal.aspx.cs` | L103 | `InsertPushNotiRenewal` | `string` | `string ExternalId, string Status` | `BLL_CustVehicle, BLL_InsertPushNotiRenewal` |
| 20 | `Insurance\Service.asmx.cs` | L45 | `GetVehicleDetails` | `string` | `string vehicleNumber` | `sp_AppDocumentType, sp_APPInsuranceCompany` |
| 21 | `Insurance\Service.asmx.cs` | L94 | `SelectDocumentType` | `void` | `` | `sp_AppDocumentType, sp_APPInsuranceCompany, sp_AppSelectHelp` |
| 22 | `Insurance\Service.asmx.cs` | L123 | `SelectInsuranceCompany` | `void` | `` | `sp_APPInsuranceCompany, sp_AppSelectHelp, sp_SelectVehicleInsurance` |
| 23 | `Insurance\Service.asmx.cs` | L148 | `SelectInsuranceCompanyNew` | `void` | `` | `sp_APPInsuranceCompany, sp_AppSelectHelp, sp_SelectVehicleInsurance` |
| 24 | `Insurance\Service.asmx.cs` | L176 | `SelectHelp` | `void` | `` | `sp_AppSelectHelp, sp_SelectVehicleInsurance, sp_InsertReferenceCustomer, sp_InsertCustomerReferenceImg` |
| 25 | `Insurance\Service.asmx.cs` | L205 | `SelectVehicleInsurance` | `void` | `` | `sp_SelectVehicleInsurance, sp_InsertReferenceCustomer, sp_InsertCustomerReferenceImg, sp_InsertHelpInfo` |
| 26 | `Insurance\Service.asmx.cs` | L236 | `InsertReferenceCustomer` | `void` | `string CustName, string ContactNo, string[] photos` | `sp_InsertReferenceCustomer, sp_InsertCustomerReferenceImg, sp_InsertHelpInfo` |
| 27 | `Insurance\Service.asmx.cs` | L283 | `InsertHelpInfo` | `void` | `String HelpId` | `sp_InsertHelpInfo, Sp_InsertAppClaim, sp_InsertClaimImg` |
| 28 | `Insurance\Service.asmx.cs` | L318 | `InsertClaimAssistance` | `void` | `int InsuranceCompanyId, DateTime ClaimsDate, string RegistrationNo, DateTime DateOfAcci...` | `Sp_InsertAppClaim, sp_InsertClaimImg, sp_AppSelectRewardPoint` |
| 29 | `Insurance\Service.asmx.cs` | L381 | `SelectRevertPoint` | `void` | `` | `sp_AppSelectRewardPoint, sp_ReminderPolicyReport, sp_SelectReminderPolicyReportContent` |
| 30 | `Insurance\Service.asmx.cs` | L410 | `SelectReminderPolicyReport` | `void` | `` | `sp_ReminderPolicyReport, sp_SelectReminderPolicyReportContent, sp_SelectLanguage` |
| 31 | `Insurance\Service.asmx.cs` | L443 | `SelectReminderPolicyReportRegNo` | `void` | `` | `sp_SelectReminderPolicyReportContent, sp_SelectLanguage, sp_SelectLanguageProduct` |
| 32 | `Insurance\Service.asmx.cs` | L475 | `SelectLanguage` | `void` | `` | `sp_SelectLanguage, sp_SelectLanguageProduct, sp_ChkloginCustomer` |
| 33 | `Insurance\Service.asmx.cs` | L504 | `SelectLanguageProduct` | `void` | `int LanguageId` | `sp_SelectLanguageProduct, sp_ChkloginCustomer, sp_SelectDocumentImgDetails` |
| 34 | `Insurance\Service.asmx.cs` | L537 | `CheckLoginCustomer` | `void` | `string MoblieNo1, string MoblieNo2` | `sp_ChkloginCustomer, sp_SelectDocumentImgDetails` |
| 35 | `Insurance\Service.asmx.cs` | L585 | `SelectDocumentImgDetails` | `void` | `` | `sp_SelectDocumentImgDetails, sp_InsertAppCustPolicyinfodoc` |
| 36 | `Insurance\Service.asmx.cs` | L618 | `InsertCustPolicyinfoedocsNew` | `void` | `int DocumentTypeId, string InsuranceCompanyId, string VehicleInsuranceId, string DocNo,...` | `sp_InsertAppCustPolicyinfodoc, sp_InsertAppDocument_Img, sp_InsertAppDocument_PolicyImg` |
| 37 | `Insurance\Service.asmx.cs` | L799 | `APPHelpReport` | `void` | `` | `sp_APPHelpReport, sp_DeleteCustomerPolicyInfo, sp_selectCustomerPolicyDetails` |
| 38 | `Insurance\Service.asmx.cs` | L828 | `DeleteCustomerPolicyInfo` | `void` | `int CustpolicyinfoId` | `sp_DeleteCustomerPolicyInfo, sp_selectCustomerPolicyDetails, sp_selectAppDocumentImg` |
| 39 | `Insurance\Service.asmx.cs` | L854 | `selectCustomerPolicyDetails` | `void` | `` | `sp_selectCustomerPolicyDetails, sp_selectAppDocumentImg, Sp_SelectCustomerPolicyDetailsDoc` |
| 40 | `Insurance\Service.asmx.cs` | L888 | `selectAppDocumentImg` | `void` | `` | `sp_selectAppDocumentImg, Sp_SelectCustomerPolicyDetailsDoc, sp_ReminderPolicyEntryPopUp` |
| 41 | `Insurance\Service.asmx.cs` | L920 | `SelectCustomerPolicyDetailsDoc` | `void` | `` | `Sp_SelectCustomerPolicyDetailsDoc, sp_ReminderPolicyEntryPopUp, sp_InsertHelpforRenewalPolicy` |
| 42 | `Insurance\Service.asmx.cs` | L953 | `ReminderEntryPopUp` | `void` | `` | `sp_ReminderPolicyEntryPopUp, sp_InsertHelpforRenewalPolicy, sp_SignUpAppCustomer` |
| 43 | `Insurance\Service.asmx.cs` | L987 | `InsertHelpInfoforRenewalPolicy` | `void` | `` | `sp_InsertHelpforRenewalPolicy, sp_SignUpAppCustomer, sp_ChkloginRefCustomer` |
| 44 | `Insurance\Service.asmx.cs` | L1022 | `InsertSignUpCustomer` | `void` | `string APPCustomerName, string ContactNo, string ContactNo2, string EmailId, string Add...` | `sp_SignUpAppCustomer, sp_ChkloginRefCustomer` |
| 45 | `Insurance\Service.asmx.cs` | L1059 | `CheckLoginAPPRefCustomer` | `void` | `string ContactNo` | `sp_ChkloginRefCustomer, sp_PolicyType` |
| 46 | `Insurance\Service.asmx.cs` | L1109 | `SelectPolicyType` | `void` | `` | `sp_PolicyType, Sp_SelectPolicyTypeByVehtype, sp_ProductType` |
| 47 | `Insurance\Service.asmx.cs` | L1145 | `` | `unknown` | `` | `Sp_SelectPolicyTypeByVehtype, sp_ProductType, sp_PolicyMode` |
| 48 | `Insurance\Service.asmx.cs` | L1172 | `SelectProductType` | `void` | `` | `sp_ProductType, sp_PolicyMode, sp_InsertAppTransaction` |
| 49 | `Insurance\Service.asmx.cs` | L1202 | `SelectPolicyMode` | `void` | `` | `sp_PolicyMode, sp_InsertAppTransaction` |
| 50 | `Insurance\Service.asmx.cs` | L1233 | `InsertAppTransaction` | `void` | `string PolicyType, string Name, string ContactNo, double ODDiscount, double NCB, double...` | `sp_InsertAppTransaction, sp_InsertTransaction_Img` |
| 51 | `Insurance\Service.asmx.cs` | L1315 | `InsertAppTransactionNew1` | `void` | `string PolicyType, string Name, string ContactNo, double ODDiscount, double NCB, double...` | `sp_InsertAppTransaction1, sp_InsertTransaction_Img` |
| 52 | `Insurance\Service.asmx.cs` | L1409 | `InsertAppTransactionpdf` | `void` | `string PolicyType, string Name, string ContactNo, double ODDiscount, double NCB, double...` | `sp_InsertAppTransaction1, sp_InsertTransaction_Img` |
| 53 | `Insurance\Service.asmx.cs` | L1538 | `InsertAppTransactionpdfnew` | `void` | `string PolicyType, string Name, string ContactNo, double ODDiscount, double NCB, double...` | `sp_InsertAppTransaction1, sp_InsertTransaction_Img` |
| 54 | `Insurance\Service.asmx.cs` | L1655 | `InsertAppAgent` | `void` | `int SalesExId, string AgentFName, string AgentMName, string AgentLName, string MobileNo...` | `SP_InsertAppAgent, SP_InsertAppAgentAadharCard, SP_InsertAppAgentPancard` |
| 55 | `Insurance\Service.asmx.cs` | L1850 | `InsertAppAgent` | `void` | `int SalesExId, string AgentFName, string AgentMName, string AgentLName, string MobileNo...` | `SP_InsertAppAgent, SP_InsertAppAgentAadharCard, SP_InsertAppAgentPancard` |
| 56 | `Insurance\Service.asmx.cs` | L2056 | `` | `unknown` | `` | `Sp_InsertAppTransctiondetailsNew` |
| 57 | `Insurance\Service.asmx.cs` | L2158 | `public void InsertAppTransctiondetailsNew(string OtherAgentN` | `unknown` | `` | `Sp_InsertAppTransctiondetailsNew` |
| 58 | `Insurance\Service.asmx.cs` | L2346 | `public void InsertAppTransctiondetailsNew_1(string OtherAgen` | `unknown` | `` | `Sp_InsertAppTransctiondetailsNew1` |
| 59 | `Insurance\Service.asmx.cs` | L2504 | `public void InsertAppTransctiondetailsNew_21(string OtherAge` | `unknown` | `` | `Sp_InsertAppTransctiondetailsNew_21` |
| 60 | `Insurance\Service.asmx.cs` | L2653 | `InsertAppMIS` | `void` | `int UserId, int salesexecutiveId, DateTime MISDate, string policypdf, string Quotationp...` | `Sp_InsertAppMISEntry, Sp_InsertMIS_policypdf, Sp_InsertMIS_Quatationpdf` |
| 61 | `Insurance\Service.asmx.cs` | L2918 | `Insertappquatationtransentry` | `void` | `int AgentId, int UserRoleId, string RegistrationNo, string MakeModel, string policypdf,...` | `sp_Insertappquatationtransentry, sp_insertappquotationpdf, sp_InsertappquotationRcPdf, sp_insertappquotationimg` |
| 62 | `Insurance\Service.asmx.cs` | L3032 | `selectVehicleSubType` | `void` | `int Veh_Type_ID` | `sp_AppVehicle_Sub_Type, Sp_SelectPolicyTypeByVehtype, sp_AppVehicle_Type` |
| 63 | `Insurance\Service.asmx.cs` | L3060 | `SelectPolicyTypeByVehtype` | `void` | `int Veh_Type_ID` | `Sp_SelectPolicyTypeByVehtype, sp_AppVehicle_Type, sp_FuelType` |
| 64 | `Insurance\Service.asmx.cs` | L3089 | `selectVehicle_Type1` | `void` | `` | `sp_AppVehicle_Type, sp_FuelType, sp_AppVehicle_Make` |
| 65 | `Insurance\Service.asmx.cs` | L3116 | `SelectAllFuel` | `void` | `` | `sp_FuelType, sp_AppVehicle_Make, sp_selectVehicleMakeByType` |
| 66 | `Insurance\Service.asmx.cs` | L3145 | `` | `unknown` | `` | `sp_AppVehicle_Make, sp_selectVehicleMakeByType, sp_selectVehicleVariantByModel, sp_AppVehicle_model` |
| 67 | `Insurance\Service.asmx.cs` | L3176 | `` | `unknown` | `` | `sp_selectVehicleMakeByType, sp_AppVehicle_Make, sp_selectVehicleVariantByModel, sp_AppVehicle_model (+1 more)` |
| 68 | `Insurance\Service.asmx.cs` | L3207 | `selectVehicleModel` | `void` | `int VehicleMakeId` | `sp_selectVehicleVariantByModel, sp_AppVehicle_model, Sp_SelectVehicleTypeForQuaotation, Sp_SelectVehicleSubTypeForQuaotation` |
| 69 | `Insurance\Service.asmx.cs` | L3238 | `SelectVehicleTypeForQuaotation` | `void` | `` | `Sp_SelectVehicleTypeForQuaotation, Sp_SelectVehicleSubTypeForQuaotation, Sp_SelectVehicleMakeForQuaotation` |
| 70 | `Insurance\Service.asmx.cs` | L3270 | `SelectVehicleSubTypeForQuaotation` | `void` | `` | `Sp_SelectVehicleSubTypeForQuaotation, Sp_SelectVehicleMakeForQuaotation, sp_AppVehicle_Make, Sp_SelectVehicleModelForQuaotation` |
| 71 | `Insurance\Service.asmx.cs` | L3297 | `` | `unknown` | `` | `Sp_SelectVehicleMakeForQuaotation, sp_AppVehicle_Make, Sp_SelectVehicleModelForQuaotation, Sp_SelectVehicleVarianceForQuaotation` |
| 72 | `Insurance\Service.asmx.cs` | L3324 | `SelectVehicleMakeForQuaotation` | `void` | `string opr` | `Sp_SelectVehicleMakeForQuaotation, sp_AppVehicle_Make, Sp_SelectVehicleModelForQuaotation, Sp_SelectVehicleVarianceForQuaotation (+2 more)` |
| 73 | `Insurance\Service.asmx.cs` | L3352 | `SelectVehicleModelForQuaotation` | `void` | `` | `Sp_SelectVehicleModelForQuaotation, Sp_SelectVehicleVarianceForQuaotation, sp_selectVehicleVariantByModel, sp_AppVehicleModel` |
| 74 | `Insurance\Service.asmx.cs` | L3380 | `SelectVehicleVarianceForQuaotation` | `void` | `` | `Sp_SelectVehicleVarianceForQuaotation, sp_selectVehicleVariantByModel, sp_AppVehicleModel, sp_AppVehicleVaraintswithtype` |
| 75 | `Insurance\Service.asmx.cs` | L3407 | `AppVehicleModelNew` | `void` | `int VehicleMakeId, int Veh_Type_ID` | `sp_selectVehicleVariantByModel, sp_AppVehicleModel, sp_AppVehicleVaraintswithtype, sp_State` |
| 76 | `Insurance\Service.asmx.cs` | L3441 | `selectVehicleVariantType` | `void` | `int ModelId, int VehTypeId` | `sp_AppVehicleVaraintswithtype, sp_State, sp_District` |
| 77 | `Insurance\Service.asmx.cs` | L3470 | `selectState` | `void` | `` | `sp_State, sp_District` |
| 78 | `Insurance\Service.asmx.cs` | L3499 | `selectDistrict` | `void` | `int stateid` | `sp_District, sp_AppSelectEmp` |
| 79 | `Insurance\Service.asmx.cs` | L3529 | `UploadFile` | `string` | `byte[] f, string fileName` | `sp_AppSelectEmp, sp_AppSelectUserRole` |
| 80 | `Insurance\Service.asmx.cs` | L3575 | `SelectSalesExicutive` | `void` | `` | `sp_AppSelectEmp, sp_AppSelectUserRole, app_sp_ViewAppTransaction` |
| 81 | `Insurance\Service.asmx.cs` | L3602 | `AppSelectUserRole` | `void` | `` | `sp_AppSelectUserRole, app_sp_ViewAppTransaction, app_sp_ViewAppTransactionSE` |
| 82 | `Insurance\Service.asmx.cs` | L3628 | `ViewAppTransaction` | `void` | `DateTime fromdate, DateTime todate` | `app_sp_ViewAppTransaction, app_sp_ViewAppTransactionSE, app_Sp_MISHistory` |
| 83 | `Insurance\Service.asmx.cs` | L3660 | `ViewAppTransactionSE` | `void` | `DateTime fromdate, DateTime todate, int SalesExecutiveId` | `app_sp_ViewAppTransactionSE, app_Sp_MISHistory, sp_AppMonthlyAgentcommAgentwiserpt` |
| 84 | `Insurance\Service.asmx.cs` | L3691 | `ViewMISHistory` | `void` | `int SalesExecutiveId` | `app_Sp_MISHistory, sp_AppMonthlyAgentcommAgentwiserpt, sp_AgentcommAgentwiserpt` |
| 85 | `Insurance\Service.asmx.cs` | L3724 | `MonthlyAgentcommAgentwiserpt` | `void` | `` | `sp_AppMonthlyAgentcommAgentwiserpt, sp_AgentcommAgentwiserpt, sp_appSerachVehDetails` |
| 86 | `Insurance\Service.asmx.cs` | L3758 | `AgentcommAgentwiserpt` | `void` | `int AgentId, DateTime fromdate, DateTime todate, int UserRoleId` | `sp_AgentcommAgentwiserpt, sp_appSerachVehDetails` |
| 87 | `Insurance\Service.asmx.cs` | L3798 | ` ` | `unknown` | `` | `sp_appSerachVehDetails, sp_SearchVehicleNoapp` |
| 88 | `Insurance\Service.asmx.cs` | L3829 | `appSerachVehDetails` | `void` | `string RegistrationNo, string FinancialYear` | `sp_appSerachVehDetails, sp_SearchVehicleNoapp, sp_appSerachCustNameDetails` |
| 89 | `Insurance\Service.asmx.cs` | L3858 | `SearchVehicleNoapp` | `void` | `string SerachText` | `sp_SearchVehicleNoapp, sp_appSerachCustNameDetails, sp_SearchCustNameapp` |
| 90 | `Insurance\Service.asmx.cs` | L3890 | `appSerachCustNameDetails` | `void` | `string CustName` | `sp_appSerachCustNameDetails, sp_SearchCustNameapp, sp_AppLoginnew` |
| 91 | `Insurance\Service.asmx.cs` | L3918 | `SearchCustNameapp` | `void` | `string SerachText` | `sp_SearchCustNameapp, sp_AppLoginnew` |
| 92 | `Insurance\Service.asmx.cs` | L3951 | `AppLogin` | `void` | `string UserName, string Password` | `sp_AppLoginnew, sp_GetImageByID` |
| 93 | `Insurance\Service.asmx.cs` | L4013 | `GetImageByID` | `void` | `int TransID` | `sp_GetImageByID, sp_GetPolicyPdfById, sp_AppAgentCommisionRpt, sp_AppAgentCommisionRptforApp` |
| 94 | `Insurance\Service.asmx.cs` | L4042 | `GetPolicyPdfByID` | `void` | `int TransID` | `sp_GetPolicyPdfById, sp_AppAgentCommisionRpt, sp_AppAgentCommisionRptforApp` |
| 95 | `Insurance\Service.asmx.cs` | L4071 | `AppAgentCommisionRpt` | `void` | `` | `sp_AppAgentCommisionRpt, sp_AppAgentCommisionRptforApp, sp_AppDashBoardSaleExRpt_new` |
| 96 | `Insurance\Service.asmx.cs` | L4131 | `` | `unknown` | `` | `sp_AppDashBoardSaleExRpt_new, sp_AppDashBoardLocationHeadsalesRpt` |
| 97 | `Insurance\Service.asmx.cs` | L4210 | `AppDashBoardLocationHeadsalesRpt` | `void` | `` | `sp_AppDashBoardLocationHeadsalesRpt, sp_AppDashBoardSaleExRpt` |
| 98 | `Insurance\Service.asmx.cs` | L4270 | `AppDashBoardSaleExRpt` | `void` | `` | `sp_AppDashBoardSaleExRpt, sp_AppFranchiseDashboardRpt` |
| 99 | `Insurance\Service.asmx.cs` | L4331 | `AppFranchiseDashboardRpt` | `void` | `` | `sp_AppFranchiseDashboardRpt, sp_AppDashBoardLocationHeadRpt` |
| 100 | `Insurance\Service.asmx.cs` | L4399 | `AppDashBoardLocationHead` | `void` | `int LocationHeadId` | `sp_AppDashBoardLocationHeadRpt, sp_AppTargetDashBoard` |
| 101 | `Insurance\Service.asmx.cs` | L4462 | `AppTargetDashBoard` | `void` | `int EmpId` | `sp_AppTargetDashBoard, sp_AppDashBoardInsuranceCompany, sp_AgentAppDashBoardMonthlyBusiness` |
| 102 | `Insurance\Service.asmx.cs` | L4515 | `AppDashBoardInsuranceCompany` | `void` | `` | `sp_AppDashBoardInsuranceCompany, sp_AgentAppDashBoardMonthlyBusiness, sp_AgentAppLogin` |
| 103 | `Insurance\Service.asmx.cs` | L4547 | `AgentAppLogin` | `void` | `string UserName, string Password` | `sp_AgentAppLogin, sp_AgentAppLoginNew` |
| 104 | `Insurance\Service.asmx.cs` | L4616 | `AgentAppLoginNew` | `void` | `string UserName, string Password` | `sp_AgentAppLoginNew` |
| 105 | `Insurance\Service.asmx.cs` | L4718 | `DashboardLogin` | `void` | `string UserName, string Password` | `Sp_DashboardLogin, sp_SelectEndorsementType` |
| 106 | `Insurance\Service.asmx.cs` | L4762 | `SelectEndorsementType` | `void` | `` | `sp_SelectEndorsementType` |
| 107 | `Insurance\Service.asmx.cs` | L4792 | `InsertAppEndorsement` | `void` | `int EndorsementTypeId, string TransferorName, DateTime TransferDate, string Inspection,...` | `sp_InsertAppEndorsement` |
| 108 | `Insurance\Service.asmx.cs` | L4993 | `InsertAppEndorsement_20201216` | `void` | `int EndorsementTypeId, string TransferorName, DateTime TransferDate, string Inspection,...` | `sp_InsertAppEndorsement_20201216` |
| 109 | `Insurance\Service.asmx.cs` | L5198 | `InsertAppEndorsement1` | `void` | `int EndorsementTypeId, string TransferorName, DateTime TransferDate, string Inspection,...` | `sp_InsertAppEndorsement1` |
| 110 | `Insurance\Service.asmx.cs` | L5341 | `selectAppAgentSalesExecWise` | `void` | `int EmpId, int UserRole_Id` | `sp_AppDashBoardInsuranceCompany, sp_selectAppAgentSalesExecWise, sp_SelectCircularSubject, sp_SelectCircluarPdfPath` |
| 111 | `Insurance\Service.asmx.cs` | L5372 | `SelectCircularSubject` | `void` | `` | `sp_AppDashBoardInsuranceCompany, sp_SelectCircularSubject, sp_SelectCircluarPdfPath, sp_selectMessageCount` |
| 112 | `Insurance\Service.asmx.cs` | L5403 | `SelectCircluarPdfPath` | `void` | `string subject` | `sp_SelectCircluarPdfPath, sp_selectMessageCount, sp_SelectMessageshow` |
| 113 | `Insurance\Service.asmx.cs` | L5436 | `selectMessageCount` | `void` | `int UserId` | `sp_selectMessageCount, sp_SelectMessageshow, sp_SelectMessage` |
| 114 | `Insurance\Service.asmx.cs` | L5469 | `SelectMessageshow` | `void` | `int MessagedetailId` | `sp_SelectMessageshow, sp_SelectMessage, sp_SelectreadMeassage` |
| 115 | `Insurance\Service.asmx.cs` | L5500 | `SelectMessage` | `void` | `int UserId` | `sp_SelectMessage, sp_SelectreadMeassage, sp_UpdateMessage` |
| 116 | `Insurance\Service.asmx.cs` | L5533 | `SelectreadMeassage` | `void` | `int UserId` | `sp_SelectreadMeassage, sp_UpdateMessage, sp_InsertAppTransactionnew` |
| 117 | `Insurance\Service.asmx.cs` | L5564 | `UpdateMessagestatus` | `void` | `int MessagedetailId` | `sp_UpdateMessage, sp_InsertAppTransactionnew` |
| 118 | `Insurance\Service.asmx.cs` | L5593 | `InsertAppTransactionnew` | `void` | `string PolicyType, string Name, string ContactNo, double ODDiscount, double NCB, double...` | `sp_InsertAppTransactionnew, sp_InsertTransaction_Img, sp_SelectAppcoordinator` |
| 119 | `Insurance\Service.asmx.cs` | L5674 | `SelectAppcoordinator` | `void` | `int AgentId` | `sp_SelectAppcoordinator, sp_ViewQuatationEntry, sp_ViewQuatationEntrySaleEx` |
| 120 | `Insurance\Service.asmx.cs` | L5707 | `ViewQuatationEntryAgent` | `void` | `DateTime FromDate, DateTime Todate, int AgentId` | `sp_ViewQuatationEntry, sp_ViewQuatationEntrySaleEx, sp_SelectQuatationEntry` |
| 121 | `Insurance\Service.asmx.cs` | L5740 | `ViewQuatationEntrySaleEx` | `void` | `DateTime FromDate, DateTime Todate, int SaleExId` | `sp_ViewQuatationEntrySaleEx, sp_SelectQuatationEntry, sp_FranchiseAppLoginnew` |
| 122 | `Insurance\Service.asmx.cs` | L5772 | `SelectQuatationEntry` | `void` | `int QuatationId` | `sp_SelectQuatationEntry, sp_FranchiseAppLoginnew` |
| 123 | `Insurance\Service.asmx.cs` | L5804 | `FranchiseAppLoginnew` | `void` | `string UserName, string Password` | `sp_FranchiseAppLoginnew, sp_DashBoardForFranchaise` |
| 124 | `Insurance\Service.asmx.cs` | L5877 | `DashBoardForFranchaise` | `void` | `int FranchiseId` | `sp_DashBoardForFranchaise, Sp_agentcommforwalletapp` |
| 125 | `Insurance\Service.asmx.cs` | L5911 | `agentcommforwalletapp` | `void` | `int AgentId` | `Sp_agentcommforwalletapp, Sp_AgentCommWalletBalance` |
| 126 | `Insurance\Service.asmx.cs` | L5942 | `agentcommforwalletappUnpaid` | `void` | `int AgentId, string opr` | `Sp_agentcommforwalletapp, Sp_AgentCommWalletBalance, Sp_AgentCommWalletbalForCheque` |
| 127 | `Insurance\Service.asmx.cs` | L5973 | `AgentCommWalletBalance` | `void` | `int AgentId` | `Sp_AgentCommWalletBalance, Sp_AgentCommWalletbalForCheque, Sp_agentcommforwalletapp` |
| 128 | `Insurance\Service.asmx.cs` | L6004 | `AgentCommWalletbalForCheque` | `void` | `int AgentId` | `Sp_AgentCommWalletbalForCheque, Sp_agentcommforwalletapp` |
| 129 | `Insurance\Service.asmx.cs` | L6038 | `agentcommforwalletappDeposit` | `void` | `int AgentId` | `Sp_agentcommforwalletapp, SP_InsertAppAgentHelp` |
| 130 | `Insurance\Service.asmx.cs` | L6069 | `agentcommforwalletappWithdrawl` | `void` | `int AgentId` | `Sp_agentcommforwalletapp, SP_InsertAppAgentHelp` |
| 131 | `Insurance\Service.asmx.cs` | L6099 | `InsertHelpforApp` | `void` | `int SalesExId, string HelpName, int UserRoleId` | `SP_InsertAppAgentHelp, Sp_agentcommforwalletapp, sp_accountpaymentmsg` |
| 132 | `Insurance\Service.asmx.cs` | L6131 | `agentcommforPaidwalletapp` | `void` | `int AgentId` | `Sp_agentcommforwalletapp, sp_accountpaymentmsg, sp_selectPolicyForInstaPay, sp_insertaccountpaymentmsgdetails` |
| 133 | `Insurance\Service.asmx.cs` | L6164 | `AccountPaymentMsgOld` | `void` | `int agentId, int approvestatus, string message, string Amount, int UserRoleId` | `sp_accountpaymentmsg, sp_selectPolicyForInstaPay, sp_insertaccountpaymentmsgdetails, sp_IsInstaPayAlreadyExist` |
| 134 | `Insurance\Service.asmx.cs` | L6240 | `AccountPaymentMsg` | `void` | `int agentId, int approvestatus, string message, string Amount, int UserRoleId` | `sp_IsInstaPayAlreadyExist, sp_accountpaymentmsg, sp_selectPolicyForInstaPayAgain, sp_insertaccountpaymentmsgdetails` |
| 135 | `Insurance\Service.asmx.cs` | L6376 | `AccountPaymentMsg` | `void` | `int agentId, int approvestatus, string message, string Amount, int UserRoleId` | `sp_IsInstaPayInserted, sp_IsInstaPayAlreadyExist, sp_selectPolicyForInstaPayAgain, sp_accountpaymentmsg (+1 more)` |
| 136 | `Insurance\Service.asmx.cs` | L6531 | `AgentRequestedInstaPay` | `void` | `int AgentId, int UserRoleId` | `Sp_AgentRequestedInsta, sp_BusinessType, Sp_GetInsuranceCompanylistforQuotation` |
| 137 | `Insurance\Service.asmx.cs` | L6568 | `SelectAllBusiness` | `void` | `` | `sp_BusinessType, Sp_GetInsuranceCompanylistforQuotation, Sp_SelectQuotation` |
| 138 | `Insurance\Service.asmx.cs` | L6600 | `GetInsuranceCompanylist` | `void` | `` | `Sp_GetInsuranceCompanylistforQuotation, Sp_SelectQuotation, Sp_GetQuotationdata` |
| 139 | `Insurance\Service.asmx.cs` | L6627 | `SelectQuotation` | `void` | `int AgentId, DateTime fromDate, DateTime ToDate, int UserRoleId` | `Sp_SelectQuotation, Sp_GetQuotationdata, Sp_ViewQuotationpdf` |
| 140 | `Insurance\Service.asmx.cs` | L6659 | `GetQuotationData` | `void` | `int AgentId, DateTime fromDate, DateTime ToDate, int UserRoleId` | `Sp_GetQuotationdata, Sp_ViewQuotationpdf, InsertAppQuotationRequest` |
| 141 | `Insurance\Service.asmx.cs` | L6691 | `ViewQuotationpdf` | `void` | `int QuotationId` | `Sp_ViewQuotationpdf, InsertAppQuotationRequest` |
| 142 | `Insurance\Service.asmx.cs` | L6721 | `InsertAppQuotationRequest` | `void` | `DateTime QuatationDate, string InsuranceCompanyId, int AgentId, string[] Pdf, string Pr...` | `InsertAppQuotationRequest, sp_InsertQuotation_Img, sp_InsertQuotation_PDF` |
| 143 | `Insurance\Service.asmx.cs` | L6828 | `SelectAppQuotationcoordinator` | `void` | `int AgentId` | `sp_SelectAppQuotationcoordinator, sp_SelectAppInespectionCoordinator, sp_SelectAppInespectionCoordinatorsales` |
| 144 | `Insurance\Service.asmx.cs` | L6863 | `SelectAppInespectionCoordinator` | `void` | `int AgentId` | `sp_SelectAppInespectionCoordinator, sp_SelectAppInespectionCoordinatorsales, sp_getDataForPolicyEntry` |
| 145 | `Insurance\Service.asmx.cs` | L6892 | `SelectAppInespectionCoordinatorsalesEx` | `void` | `int SalesExId` | `sp_SelectAppInespectionCoordinatorsales, sp_getDataForPolicyEntry, sp_GetQuotationImgById` |
| 146 | `Insurance\Service.asmx.cs` | L6924 | `GetDataForPolicyEntry` | `void` | `int InsuranceCompanyId, int QuatationId` | `sp_getDataForPolicyEntry, sp_GetQuotationImgById, sp_Select_IsQuotationCodeIsExist` |
| 147 | `Insurance\Service.asmx.cs` | L6959 | `GetQuotationImgForPolicyEntry` | `void` | `int QuatationId` | `sp_GetQuotationImgById, sp_Select_IsQuotationCodeIsExist, sp_GetQuotationPdfById` |
| 148 | `Insurance\Service.asmx.cs` | L6994 | `IsQuotationCode_Exist` | `void` | `string QuatationCode` | `sp_Select_IsQuotationCodeIsExist, sp_GetQuotationPdfById, sp_GetAgentById` |
| 149 | `Insurance\Service.asmx.cs` | L7034 | `GetQuotationPdfForPolicyEntry` | `void` | `int QuatationId` | `sp_GetQuotationPdfById, sp_GetAgentById, sp_SelectAppEndorsementCoordinator` |
| 150 | `Insurance\Service.asmx.cs` | L7068 | `GetAgentForPolicyEntry` | `void` | `int AgentId` | `sp_GetAgentById, sp_SelectAppEndorsementCoordinator, Sp_GetQuotationCodeForPolicyEntry1` |
| 151 | `Insurance\Service.asmx.cs` | L7101 | `SelectAppEndorsementCoordinator` | `void` | `int AgentId, int UserRoleId` | `sp_SelectAppEndorsementCoordinator, Sp_GetQuotationCodeForPolicyEntry1, Sp_GetQuotationCodeForPolicyEntry` |
| 152 | `Insurance\Service.asmx.cs` | L7136 | `GetQuotationCodeForManualPolicyEntry1` | `void` | `int UserRoleId, int Id` | `Sp_GetQuotationCodeForPolicyEntry1, Sp_GetQuotationCodeForPolicyEntry, sp_ViewAppEndorsementRequest` |
| 153 | `Insurance\Service.asmx.cs` | L7173 | `GetQuotationCodeForManualPolicyEntry` | `void` | `` | `Sp_GetQuotationCodeForPolicyEntry, sp_ViewAppEndorsementRequest, Sp_ReopenQuotRequest` |
| 154 | `Insurance\Service.asmx.cs` | L7212 | `ViewAppEndorsementRequest` | `void` | `int UserId, DateTime DateFrom, DateTime DateTo` | `sp_ViewAppEndorsementRequest, Sp_ReopenQuotRequest, Sp_UpdateAppQuotReq` |
| 155 | `Insurance\Service.asmx.cs` | L7247 | `ReopenQuotationRequest` | `void` | `int QuatationId` | `Sp_ReopenQuotRequest, Sp_UpdateAppQuotReq` |
| 156 | `Insurance\Service.asmx.cs` | L7280 | `UpdateQuotRequest` | `void` | `int QuatationId, DateTime QuatationDate, string InsuranceCompanyId, int VehicleId, int ...` | `Sp_UpdateAppQuotReq, Sp_UpdateAppQuotReqNew` |
| 157 | `Insurance\Service.asmx.cs` | L7334 | `UpdateQuotRequestNew` | `void` | `int QuatationId, DateTime QuatationDate, string InsuranceCompanyId, int VehicleId, int ...` | `Sp_UpdateAppQuotReqNew, Sp_DeleteQuotationImage` |
| 158 | `Insurance\Service.asmx.cs` | L7393 | `DeleteQuotationImg` | `void` | `int QuotationId` | `Sp_DeleteQuotationImage, Sp_DeleteQuotationPDF, UpdateQuotationImage` |
| 159 | `Insurance\Service.asmx.cs` | L7419 | `DeleteQuotationPDF` | `void` | `int QuotationId` | `Sp_DeleteQuotationPDF, UpdateQuotationImage, sp_InsertQuotation_PDF` |
| 160 | `Insurance\Service.asmx.cs` | L7444 | `UpdateQuotationImg` | `void` | `int QuotationId, string[] ImgPath` | `UpdateQuotationImage, sp_InsertQuotation_PDF` |
| 161 | `Insurance\Service.asmx.cs` | L7485 | `UpdateQuotationPDF` | `void` | `int QuotationId, string[] PDFPath` | `sp_InsertQuotation_PDF, Sp_ViewAppEndorsementAfterApprove, Sp_ViewAppInsuranceCompanyComm` |
| 162 | `Insurance\Service.asmx.cs` | L7528 | `ViewAppEndorsementRequestAfterApprove` | `void` | `int AgentId, DateTime FromDate, DateTime ToDate` | `Sp_ViewAppEndorsementAfterApprove, Sp_ViewAppInsuranceCompanyComm, Sp_ViewAppInsuranceCompanyComm_ST` |
| 163 | `Insurance\Service.asmx.cs` | L7564 | `ViewAppAgentInsuranceCompanyComm` | `void` | `int AgentId, int InsuranceCmpyId, int UserRoleId, int VehTypeId` | `Sp_ViewAppInsuranceCompanyComm, Sp_ViewAppInsuranceCompanyComm_ST, sp_SelectModelByWeight` |
| 164 | `Insurance\Service.asmx.cs` | L7600 | `ViewAppInsuranceCompanyComm` | `void` | `int InsuranceCmpyId, int BranchId, int UserRoleId, int VehTypeId` | `Sp_ViewAppInsuranceCompanyComm_ST, sp_SelectModelByWeight, Sp_SelectGVWFromPolicyType` |
| 165 | `Insurance\Service.asmx.cs` | L7638 | `SelectVehicleModelByWeight` | `void` | `int Make_ID, int Type_ID, int minGVW, int MaxGVW` | `sp_SelectModelByWeight, Sp_SelectGVWFromPolicyType, sp_AppVehicleVaraintswithSubtype` |
| 166 | `Insurance\Service.asmx.cs` | L7677 | `SelectGVWFromPolicyType` | `void` | `int Veh_Type_ID, int PolicyTypeId` | `Sp_SelectGVWFromPolicyType, sp_AppVehicleVaraintswithSubtype, Sp_Franchisecommforwalletapp` |
| 167 | `Insurance\Service.asmx.cs` | L7715 | `SelectAppVehicleVaraintswithSubtype` | `void` | `int Model_ID, int Veh_Type_ID, int minGVW, int MaxGVW` | `sp_AppVehicleVaraintswithSubtype, Sp_Franchisecommforwalletapp` |
| 168 | `Insurance\Service.asmx.cs` | L7753 | `FranchaisecommforwalletappDeposit` | `void` | `int FranchaiseId` | `Sp_Franchisecommforwalletapp` |
| 169 | `Insurance\Service.asmx.cs` | L7785 | `FranchaisecommforwalletappWithdrawl` | `void` | `int FranchaiseId` | `Sp_Franchisecommforwalletapp` |
| 170 | `Insurance\Service.asmx.cs` | L7817 | `FranchaisecommforPaidwalletapp` | `void` | `int FranchaiseId` | `Sp_Franchisecommforwalletapp, Sp_FranchaiseCommWalletBalance` |
| 171 | `Insurance\Service.asmx.cs` | L7848 | `Franchaisecommforwalletapp` | `void` | `int FranchaiseId` | `Sp_Franchisecommforwalletapp, Sp_FranchaiseCommWalletBalance, Sp_FranchaiseCommWalletbalForCheque` |
| 172 | `Insurance\Service.asmx.cs` | L7880 | `FranchaiseCommWalletBalance` | `void` | `int FranchaiseId` | `Sp_FranchaiseCommWalletBalance, Sp_FranchaiseCommWalletbalForCheque, Sp_SelectReferenceTypeByUserRole` |
| 173 | `Insurance\Service.asmx.cs` | L7912 | `FranchaiseCommWalletbalForCheque` | `void` | `int FranchaiseId` | `Sp_FranchaiseCommWalletbalForCheque, Sp_SelectReferenceTypeByUserRole, Sp_SelectAgentbySE` |
| 174 | `Insurance\Service.asmx.cs` | L7945 | `ReferenceTypeByUserRole` | `void` | `int UserRoleId` | `Sp_SelectReferenceTypeByUserRole, Sp_SelectAgentbySE, Sp_AppPolicyReport` |
| 175 | `Insurance\Service.asmx.cs` | L7978 | `SelectInsuranceExecutive` | `void` | `int EmpId` | `Sp_SelectAgentbySE, Sp_AppPolicyReport, sp_AgentAppSignUp` |
| 176 | `Insurance\Service.asmx.cs` | L8013 | `AppPolicyReport` | `void` | `int UserRoleId, int Id` | `Sp_AppPolicyReport, sp_AgentAppSignUp` |
| 177 | `Insurance\Service.asmx.cs` | L8045 | `AppAgentSignUp` | `void` | `string AgentFName, string AgentMName, string AgentLName, string MobileNo, string Addres...` | `sp_AgentAppSignUp, sp_InsertAgentDocumentList` |
| 178 | `Insurance\Service.asmx.cs` | L8194 | `SelectBankList` | `void` | `` | `sp_BankMaster, sp_AppFillTransactionReport, sp_AppFillTransactionReportDetails` |
| 179 | `Insurance\Service.asmx.cs` | L8226 | `AppTransactionReport` | `void` | `DateTime FromDate, DateTime ToDate, int Id, int UserRoleId` | `sp_AppFillTransactionReport, sp_AppFillTransactionReportDetails, sp_AppSelectAllCoordinatorbyUser` |
| 180 | `Insurance\Service.asmx.cs` | L8261 | `AppTransactionReportDetails` | `void` | `int TransactionId` | `sp_AppFillTransactionReportDetails, sp_AppSelectAllCoordinatorbyUser, sp_insert_app_requestedquotationfile` |
| 181 | `Insurance\Service.asmx.cs` | L8290 | `AppSelectAllCoordinator` | `void` | `int Id, int UserRoleId` | `sp_AppSelectAllCoordinatorbyUser, sp_insert_app_requestedquotationfile, sp_selectSelfQuotation` |
| 182 | `Insurance\Service.asmx.cs` | L8325 | `InsertAppRequestedQuotation` | `void` | `string QuotationId, string CompanyId, string FileName, string FilePath` | `sp_insert_app_requestedquotationfile, sp_selectSelfQuotation, sp_AppSelectPAToOwnerDriver` |
| 183 | `Insurance\Service.asmx.cs` | L8363 | `AppSelectRequestedQuotationfile` | `void` | `int Id, int UserRoleId, DateTime FromDate, DateTime ToDate` | `sp_selectSelfQuotation, sp_AppSelectPAToOwnerDriver, sp_InsertAppClaimAssistancenew` |
| 184 | `Insurance\Service.asmx.cs` | L8399 | `AppSelectPAtoOwnerDriver` | `void` | `int InsuranceCompanyId` | `sp_AppSelectPAToOwnerDriver, sp_InsertAppClaimAssistancenew` |
| 185 | `Insurance\Service.asmx.cs` | L8434 | `InsertClaimAssistancenew` | `void` | `int InsuranceCompanyId, DateTime ClaimsDate, string RegistrationNo, DateTime DateOfAcci...` | `sp_InsertAppClaimAssistancenew, sp_InsertappClaimAssistanceImg` |
| 186 | `Insurance\Service.asmx.cs` | L8518 | `SelectClaimAssistance` | `void` | `int AgentId, int UserRoleId, DateTime FromDate, DateTime ToDate` | `sp_SelectClaimAssistance, sp_ShowClaimAssistance, sp_AppDashboardVehicleTypeWiseBussiness` |
| 187 | `Insurance\Service.asmx.cs` | L8557 | `ShowClaimAssistance` | `void` | `int AgentId, int UserRoleId, DateTime FromDate, DateTime ToDate` | `sp_ShowClaimAssistance, sp_AppDashboardVehicleTypeWiseBussiness, sp_AppDashboardProductTypeWiseBussiness` |
| 188 | `Insurance\Service.asmx.cs` | L8593 | `VehicleTypeWiseBusiness` | `void` | `int Id, int UserRoleId, string opr, string FinancialYear` | `sp_AppDashboardVehicleTypeWiseBussiness, sp_AppDashboardProductTypeWiseBussiness, sp_AppSalesExAgentBusiness` |
| 189 | `Insurance\Service.asmx.cs` | L8629 | `ProductTypeWiseBusiness` | `void` | `int Id, int UserRoleId, string opr` | `sp_AppDashboardProductTypeWiseBussiness, sp_AppSalesExAgentBusiness, sp_AppSalesExAgentBusinessMothwise` |
| 190 | `Insurance\Service.asmx.cs` | L8664 | `AppSalesExAgentBusiness` | `void` | `int Id` | `sp_AppSalesExAgentBusiness, sp_AppSalesExAgentBusinessMothwise, sp_AppSalesExAgentBusinessMothwise_3month` |
| 191 | `Insurance\Service.asmx.cs` | L8699 | `AppSalesExAgentBusinessMonthWise` | `void` | `int Id, int Month, string year` | `sp_AppSalesExAgentBusinessMothwise, sp_AppSalesExAgentBusinessMothwise_3month` |
| 192 | `Insurance\Service.asmx.cs` | L8739 | `AppSalesExAgentBusinessMonthWise_3month` | `void` | `int Id, int Month, string year` | `sp_AppSalesExAgentBusinessMothwise_3month, sp_InsertAppChatboard, sp_InsertAppChatboard_Img` |
| 193 | `Insurance\Service.asmx.cs` | L8780 | `InsertAppChatboard` | `void` | `int UserRoleId, int ReferenceAgentId, string ChatText, string ChatByUser, string Regist...` | `sp_InsertAppChatboard, sp_InsertAppChatboard_Img, sp_InsertAppChatboard_Pdf` |
| 194 | `Insurance\Service.asmx.cs` | L8866 | `AppChatDetails` | `void` | `int Id, int UserRoleId` | `sp_AppChatDetails, sp_Selectappchatsearchbyregno, sp_ProcessToInstaPay` |
| 195 | `Insurance\Service.asmx.cs` | L8901 | `Selectappchatsearchbyregno` | `void` | `string RegistrationNo` | `sp_Selectappchatsearchbyregno, sp_ProcessToInstaPay, sp_AppCashDepositeStatus` |
| 196 | `Insurance\Service.asmx.cs` | L8934 | `ProcessToInstaPay` | `void` | `int AgentId` | `sp_ProcessToInstaPay, sp_AppCashDepositeStatus, Sp_AppChatReplyFile` |
| 197 | `Insurance\Service.asmx.cs` | L8968 | `AppCashDepositeStatus` | `void` | `int UserId` | `sp_AppCashDepositeStatus, Sp_AppChatReplyFile, sp_AppFranchiseDashboardProfit` |
| 198 | `Insurance\Service.asmx.cs` | L9002 | `AppChatReplyFile` | `void` | `int ChatId` | `Sp_AppChatReplyFile, sp_AppFranchiseDashboardProfit, sp_UpdateMsgDetailsStatus` |
| 199 | `Insurance\Service.asmx.cs` | L9035 | `AppFranchiseProfitPoints` | `void` | `int Id` | `sp_AppFranchiseDashboardProfit, sp_UpdateMsgDetailsStatus, sp_AppFranchiseAgentPoint` |
| 200 | `Insurance\Service.asmx.cs` | L9084 | `UpdateMsgDetailsStatus` | `void` | `int UserId` | `sp_UpdateMsgDetailsStatus, sp_AppFranchiseAgentPoint, sp_IsInstaPayAlreadyExist_new` |
| 201 | `Insurance\Service.asmx.cs` | L9110 | `AppFranchiseAgentPoint` | `void` | `int Id` | `sp_AppFranchiseAgentPoint, sp_IsInstaPayAlreadyExist_new, sp_InsertAppBilling` |
| 202 | `Insurance\Service.asmx.cs` | L9142 | `IsInstaPayAlreadyExist` | `void` | `int Id, int UserRoleId` | `sp_IsInstaPayAlreadyExist_new, sp_InsertAppBilling, sp_InsertAppBilling_img` |
| 203 | `Insurance\Service.asmx.cs` | L9176 | `InsertAppBillingDetails` | `void` | `int SalesExId, DateTime FromDate, DateTime ToDate, string Remark, double BillingAmount ...` | `sp_InsertAppBilling, sp_InsertAppBilling_img, sp_InsertAppBilling_pdf` |
| 204 | `Insurance\Service.asmx.cs` | L9267 | `saleExPremiumSummaryMonthforwebService` | `void` | `int EmpId` | `sp_saleExPremiumSummaryMonthforwebService, sp_SalesExecutiveMTDBusiness, sp_insertapppolicypremiumdesk` |
| 205 | `Insurance\Service.asmx.cs` | L9300 | `salesExecutiveMTDBusiness` | `void` | `int EmpId` | `sp_SalesExecutiveMTDBusiness, sp_insertapppolicypremiumdesk, sp_insertapppolicypremiumdesk_img` |
| 206 | `Insurance\Service.asmx.cs` | L9332 | `InsertAppPolicyPremiumDesk` | `void` | `int UserRoleId, int AgentId, int SalesExId, string CustomerName, string RegistrationNo,...` | `sp_insertapppolicypremiumdesk, sp_insertapppolicypremiumdesk_img, SelectAppReimbursementType` |
| 207 | `Insurance\Service.asmx.cs` | L9403 | `SelectReimbursmentType` | `void` | `` | `SelectAppReimbursementType, sp_selectendorsementsubtype, Sp_SalesExcommforwalletapp` |
| 208 | `Insurance\Service.asmx.cs` | L9434 | `Select_endorsementsubtype` | `void` | `int EndorsementTypeId` | `sp_selectendorsementsubtype, Sp_SalesExcommforwalletapp` |
| 209 | `Insurance\Service.asmx.cs` | L9468 | `SalesExcommforwalletapp` | `void` | `int EmpId` | `Sp_SalesExcommforwalletapp, Sp_SalesExCommWalletBalance` |
| 210 | `Insurance\Service.asmx.cs` | L9499 | `SalesExcommforwalletappUnpaid` | `void` | `int EmpId` | `Sp_SalesExcommforwalletapp, Sp_SalesExCommWalletBalance, Sp_SalesExCommWalletBalanceNew` |
| 211 | `Insurance\Service.asmx.cs` | L9530 | `SalesExCommWalletBalance` | `void` | `int EmpId` | `Sp_SalesExCommWalletBalance, Sp_SalesExCommWalletBalanceNew, Sp_SalesExCommWalletbalForCheque` |
| 212 | `Insurance\Service.asmx.cs` | L9560 | `SalesExCommWalletBalanceNew` | `void` | `int EmpId` | `Sp_SalesExCommWalletBalanceNew, Sp_SalesExCommWalletbalForCheque, Sp_SalesExcommforwalletapp` |
| 213 | `Insurance\Service.asmx.cs` | L9591 | `SalesExCommWalletbalForCheque` | `void` | `int EmpId` | `Sp_SalesExCommWalletbalForCheque, Sp_SalesExcommforwalletapp` |
| 214 | `Insurance\Service.asmx.cs` | L9625 | `SalesExcommforwalletappDeposit` | `void` | `int EmpId` | `Sp_SalesExcommforwalletapp` |
| 215 | `Insurance\Service.asmx.cs` | L9656 | `SalesExcommforwalletappWithdrawl` | `void` | `int EmpId` | `Sp_SalesExcommforwalletapp` |
| 216 | `Insurance\Service.asmx.cs` | L9688 | `SalesExcommforPaidwalletapp` | `void` | `int EmpId` | `Sp_SalesExcommforwalletapp, sp_insertAppAttendance` |
| 217 | `Insurance\Service.asmx.cs` | L9717 | `SalesExcommforPaidwalletappNew` | `void` | `int EmpId, string Opr` | `Sp_SalesExcommforwalletapp, sp_insertAppAttendance, sp_updateAppAttendance` |
| 218 | `Insurance\Service.asmx.cs` | L9753 | `InsertAppAttendance` | `void` | `int UserRoleId, int EmpId, DateTime IN_DateTime` | `sp_insertAppAttendance, sp_updateAppAttendance, sp_InsertFinalQuotationpdf` |
| 219 | `Insurance\Service.asmx.cs` | L9797 | `UpdateAppAttendance` | `void` | `int AttendanceId, DateTime OUT_DateTime` | `sp_updateAppAttendance, sp_InsertFinalQuotationpdf, sp_AppSelectLocationHeadWiseSalesEx` |
| 220 | `Insurance\Service.asmx.cs` | L9819 | `InsertFinalQuotationpdf` | `void` | `int QuotationId, string QuatationCode, string PDFPath` | `sp_InsertFinalQuotationpdf, sp_AppSelectLocationHeadWiseSalesEx, sp_AppLocationHeadExecutiveBusiness` |
| 221 | `Insurance\Service.asmx.cs` | L9847 | `AppSelectLocationHeadWiseSalesEx` | `void` | `int LocationHeadId` | `sp_AppSelectLocationHeadWiseSalesEx, sp_AppLocationHeadExecutiveBusiness, sp_SelectExecutiveUnclearingBusiness` |
| 222 | `Insurance\Service.asmx.cs` | L9882 | `AppLocationHeadSalesExBusiness` | `void` | `int Id` | `sp_AppLocationHeadExecutiveBusiness, sp_SelectExecutiveUnclearingBusiness, sp_SelectExecutiveUnclearingBusinesscount` |
| 223 | `Insurance\Service.asmx.cs` | L9915 | `AppSelectExecutiveUnclearingBusiness` | `void` | `int Id, string OPR` | `sp_SelectExecutiveUnclearingBusiness, sp_SelectExecutiveUnclearingBusinesscount, sp_SelectExecutiveUnclearingBusinesspopup` |
| 224 | `Insurance\Service.asmx.cs` | L9949 | `AppSelectExecutiveUnclearingBusinesscount` | `void` | `int Id` | `sp_SelectExecutiveUnclearingBusinesscount, sp_SelectExecutiveUnclearingBusinesspopup, sp_insertChequeclearingdoc` |
| 225 | `Insurance\Service.asmx.cs` | L9983 | `AppSelectExecutiveUnclearingBusinessPopUp` | `void` | `int Id` | `sp_SelectExecutiveUnclearingBusinesspopup, sp_insertChequeclearingdoc` |
| 226 | `Insurance\Service.asmx.cs` | L10017 | `InsertAppChequeclearingdoc` | `void` | `int TransactionId, string flag, string[] Doc` | `sp_insertChequeclearingdoc, sp_AppDashBoardSaleExRpt_new` |
| 227 | `Insurance\Service.asmx.cs` | L10087 | `AppDashBoardSaleExRpt_new` | `void` | `int Id` | `sp_AppDashBoardSaleExRpt_new, Sp_InsertAppTransctiondetailsStp` |
| 228 | `Insurance\Service.asmx.cs` | L10118 | `InsertAppTransctiondetailsStp` | `void` | `string OtherAgentName, string insurancecompany, string ProductType, int UserId, int Sal...` | `Sp_InsertAppTransctiondetailsStp, sp_InsertTransaction_Img` |
| 229 | `Insurance\Service.asmx.cs` | L10242 | `SelectPreYaerRenewalExpiryPolicy` | `void` | `int Id, int UserRoleId, int Month, string FinancialYear` | `sp_SelectPreYearRenewal, Sp_InsertPrevYearRenewalStatus` |
| 230 | `Insurance\Service.asmx.cs` | L10282 | `InsertPrevYearRenewalStatus` | `void` | `int TransanctionId, string Remark, string FinancialYear, string RegistrationNo, string ...` | `Sp_InsertPrevYearRenewalStatus` |
| 231 | `Insurance\Service.asmx.cs` | L10325 | `UpdatePrevYearFollowUpStatus` | `void` | `int TransanctionId, int UserRoleId, int Id` | `Sp_InsertPrevYearRenewalStatus` |
| 232 | `Insurance\Service.asmx.cs` | L10368 | `SelectPreYearFollowupData` | `void` | `int UserRoleId, int Id` | `Sp_InsertPrevYearRenewalStatus, Sp_SelectPreYearPolicyPdf, sp_insertRemainingPendingCash` |
| 233 | `Insurance\Service.asmx.cs` | L10411 | `SelectPreYearPolicyPdf` | `void` | `int TransactionId` | `Sp_SelectPreYearPolicyPdf, sp_insertRemainingPendingCash, Sp_insertRemainingPremiumAmt` |
| 234 | `Insurance\Service.asmx.cs` | L10441 | `InsertRemainingPremiumAmt` | `void` | `int[] TransanctionId, double TotalPremium, double PaidPremium, double RemainingPremium,...` | `sp_insertRemainingPendingCash, Sp_insertRemainingPremiumAmt, sp_insertRemainingPremiumAmt_img, sp_UpdateAppPolicyCashStatus` |
| 235 | `Insurance\Service.asmx.cs` | L10540 | `SelectRemainingPremiumPayment` | `void` | `int UserRoleId, int Id` | `sp_RemainingPremiumPayment, sp_SelectRefTypeDirectByRegNo, sp_RenewalWrongAgentName` |
| 236 | `Insurance\Service.asmx.cs` | L10576 | `SelectRefTypeDirectByRegNo` | `void` | `string RegistrationNo, string FinancialYear` | `sp_SelectRefTypeDirectByRegNo, sp_RenewalWrongAgentName, sp_SelectPaidAmtForRemainingPremiumByTransactionId` |
| 237 | `Insurance\Service.asmx.cs` | L10605 | `RenewalWrongAgentName` | `void` | `string RegistrationNo, string FinancialYear` | `sp_RenewalWrongAgentName, sp_SelectPaidAmtForRemainingPremiumByTransactionId, sp_SelectCreditsofAgentExecutive` |
| 238 | `Insurance\Service.asmx.cs` | L10634 | `SelectPaidAmtForRemainingPremiumByTransactionId` | `void` | `int TransanctionId` | `sp_SelectPaidAmtForRemainingPremiumByTransactionId, sp_SelectCreditsofAgentExecutive` |
| 239 | `Insurance\Service.asmx.cs` | L10664 | `SelectCreditsofAgentExecutive` | `void` | `int UserRoleId, int Id` | `sp_SelectCreditsofAgentExecutive, sp_AppShortfallAmountReport` |
| 240 | `Insurance\Service.asmx.cs` | L10699 | `IsCreditAssign` | `void` | `int UserRoleId, int Id` | `sp_SelectCreditsofAgentExecutive, sp_AppShortfallAmountReport, sp_RemainingPremiumPaymentFromTwoDay` |
| 241 | `Insurance\Service.asmx.cs` | L10740 | `AppShortfallAmountReport` | `void` | `int UserRoleId, int Id, string opr` | `sp_AppShortfallAmountReport, sp_RemainingPremiumPaymentFromTwoDay, sp_UpdateAppTransactionAfterPendingCash` |
| 242 | `Insurance\Service.asmx.cs` | L10771 | `AppDepositDuePopup` | `void` | `int UserRoleId, int Id` | `sp_RemainingPremiumPaymentFromTwoDay, sp_UpdateAppTransactionAfterPendingCash, sp_SelectMonth` |
| 243 | `Insurance\Service.asmx.cs` | L10806 | `UpdateAppTransactionAfterPendingCash` | `void` | `Double Premium, Double CashPaidAmt, Double CashShortAmt, string CashType, string CashSt...` | `sp_UpdateAppTransactionAfterPendingCash, sp_SelectMonth, sp_SelectYear` |
| 244 | `Insurance\Service.asmx.cs` | L10841 | `AppSelectMonth` | `void` | `` | `sp_SelectMonth, sp_SelectYear, sp_PaymentModeAllowed` |
| 245 | `Insurance\Service.asmx.cs` | L10870 | `AppSelectFinancialYear` | `void` | `` | `sp_SelectYear, sp_PaymentModeAllowed, sp_AppIsActiveUSer` |
| 246 | `Insurance\Service.asmx.cs` | L10898 | `PaymentModeAllowed` | `void` | `int SalesExId, int UserRoleId` | `sp_PaymentModeAllowed, sp_AppIsActiveUSer, sp_insertLoginHistory` |
| 247 | `Insurance\Service.asmx.cs` | L10929 | `AppIsActiveUser` | `void` | `string UserName, string UserPassword` | `sp_AppIsActiveUSer, sp_insertLoginHistory, sp_insertAppPolicyRequestEntry` |
| 248 | `Insurance\Service.asmx.cs` | L10960 | `InsertLoginHistory` | `void` | `int UserId, string UserName, string UserRoleId, string IP_add, DateTime LoginDate` | `sp_insertLoginHistory, sp_insertAppPolicyRequestEntry, sp_ViewquatationAppPolicy` |
| 249 | `Insurance\Service.asmx.cs` | L10994 | `InsertAppPolicyRequestEntry` | `void` | `int AgentId, int UserRoleId, string RegistrationNo, string Nominee, string PaymentMode,...` | `sp_insertAppPolicyRequestEntry, sp_ViewquatationAppPolicy, sp_viewQuatationSendDoc, sp_FuelTypeByVehiId` |
| 250 | `Insurance\Service.asmx.cs` | L11022 | `ViewquatationAppPolicy` | `void` | `` | `sp_ViewquatationAppPolicy, sp_viewQuatationSendDoc, sp_FuelTypeByVehiId` |
| 251 | `Insurance\Service.asmx.cs` | L11048 | `viewQuatationSendDoc` | `void` | `int QuatationId` | `sp_viewQuatationSendDoc, sp_FuelTypeByVehiId, Sp_InsertAppTransctiondetailsNew2` |
| 252 | `Insurance\Service.asmx.cs` | L11075 | `FuelTypeByVehiId` | `void` | `int Veh_Type_ID` | `sp_FuelTypeByVehiId, Sp_InsertAppTransctiondetailsNew2` |
| 253 | `Insurance\Service.asmx.cs` | L11106 | `public void InsertAppTransctiondetailsNew_2(string OtherAgen` | `unknown` | `` | `Sp_InsertAppTransctiondetailsNew2` |
| 254 | `Insurance\Service.asmx.cs` | L11257 | `public void InsertAppTransctiondetailsNew_3(string OtherAgen` | `unknown` | `` | `Sp_InsertAppTransctiondetailsNew3` |
| 255 | `Insurance\Service.asmx.cs` | L11412 | `selectRTOfromRegistration` | `void` | `string REG_code` | `sp_selectRTOfromRegistration, SelectAgentGirdForRto1, sp_SelectAgentGird1` |
| 256 | `Insurance\Service.asmx.cs` | L11442 | `SelectAgentGirdForRtoNo` | `void` | `int AgentId, int ProductType, int PolicyType, int InsuranceCompanyId, int VehiTypeId, i...` | `SelectAgentGirdForRto1, sp_SelectAgentGird1` |
| 257 | `Insurance\Service.asmx.cs` | L11485 | `SelectAgentGird` | `void` | `int AgentId, int ProductType, int PolicyType, int InsuranceCompanyId, int VehiTypeId, i...` | `sp_SelectAgentGird1, SelectAgentGirdMake_App` |
| 258 | `Insurance\Service.asmx.cs` | L11527 | `SelectAgentGirdMake` | `void` | `int ProductType, int PolicyType, int InsuranceCompanyId, int VehiTypeId` | `SelectAgentGirdMake_App, SelectAgentGirdForRto, sp_SelectAgentGird` |
| 259 | `Insurance\Service.asmx.cs` | L11566 | `SelectAgentGirdForRtoNo_ncb` | `void` | `int AgentId, int ProductType, int PolicyType, int InsuranceCompanyId, int VehiTypeId, i...` | `SelectAgentGirdForRto, sp_SelectAgentGird` |
| 260 | `Insurance\Service.asmx.cs` | L11608 | `SelectAgentGird_ncb` | `void` | `int AgentId, int ProductType, int PolicyType, int InsuranceCompanyId, int VehiTypeId, i...` | `sp_SelectAgentGird, sp_SelectSalesExecutiveCommissionGridnew` |
| 261 | `Insurance\Service.asmx.cs` | L11658 | `SalesExecutiveCommissionGrid` | `void` | `int EmpId, int InsuranceCompanyid, int PolicyType, int ProductType, int FuelTypeId, int...` | `sp_SelectSalesExecutiveCommissionGridnew` |
| 262 | `Insurance\Service.asmx.cs` | L11701 | `SalesExecutiveCommissionGrid_ncb` | `void` | `int EmpId, int InsuranceCompanyid, int PolicyType, int ProductType, int FuelTypeId, int...` | `sp_SelectSalesExecutiveCommissionGridnew, Sp_SelectAgentBranchName, sp_SelectStandardAgentForGrid` |
| 263 | `Insurance\Service.asmx.cs` | L11747 | `SelectAgentBranchName` | `void` | `int AgentId` | `Sp_SelectAgentBranchName, sp_SelectStandardAgentForGrid, sp_selectFranchiseBroker` |
| 264 | `Insurance\Service.asmx.cs` | L11780 | `SelectStandardAgentForGrid` | `void` | `int BranchId` | `sp_SelectStandardAgentForGrid, sp_selectFranchiseBroker, sp_ViewIDVReuestedorPendingData` |
| 265 | `Insurance\Service.asmx.cs` | L11813 | `selectFranchiseBroker` | `void` | `` | `sp_selectFranchiseBroker, sp_ViewIDVReuestedorPendingData, sp_InsertIDVRequest` |
| 266 | `Insurance\Service.asmx.cs` | L11843 | `ViewIDVReuestedorPendingData` | `void` | `int SalesExId, string Opr` | `sp_ViewIDVReuestedorPendingData, sp_InsertIDVRequest, sp_InsertIDVRequestImg` |
| 267 | `Insurance\Service.asmx.cs` | L11878 | `InsertIDVRequest` | `void` | `DateTime RequestDate, string InsuranceCompanyId, string[] photos, int SalesEx_Id, strin...` | `sp_InsertIDVRequest, sp_InsertIDVRequestImg, sp_InsertAppQuotationEntry` |
| 268 | `Insurance\Service.asmx.cs` | L11943 | `InsertAppQuotationEntry` | `void` | `string QuatationCode, string ProductName, string Title, string MgfYear, string RTOId, s...` | `sp_InsertAppQuotationEntry` |
| 269 | `Insurance\Service.asmx.cs` | L12030 | `UpdateClearSelfQutation` | `void` | `int QuatationId, string Opr` | `sp_UpdateClearSelfQutation, sp_SelectCashBackAppRequest, Sp_SelectPolicyTypeByGVW` |
| 270 | `Insurance\Service.asmx.cs` | L12063 | `UpdateSelectCashBackAppRequest` | `void` | `int TransanctionId` | `sp_SelectCashBackAppRequest, Sp_SelectPolicyTypeByGVW, Sp_SelectAgentbySE` |
| 271 | `Insurance\Service.asmx.cs` | L12097 | `SelectPolicyTypeByGVW` | `void` | `string GVW, string OPR` | `Sp_SelectPolicyTypeByGVW, Sp_SelectAgentbySE, sp_GetTopExectiveImg` |
| 272 | `Insurance\Service.asmx.cs` | L12130 | `SelectAgentbydetails` | `void` | `int AgentId, string Opr` | `Sp_SelectAgentbySE, sp_GetTopExectiveImg, GetTopAgentImg` |
| 273 | `Insurance\Service.asmx.cs` | L12162 | `GetTopExectiveImg` | `void` | `` | `sp_GetTopExectiveImg, GetTopAgentImg, sp_AppVehicle_Type` |
| 274 | `Insurance\Service.asmx.cs` | L12191 | `GetTopAgentImg` | `void` | `` | `GetTopAgentImg, sp_AppVehicle_Type, sp_selectVehicleMakeByType, sp_AppVehicle_MakefrQuotationApp` |
| 275 | `Insurance\Service.asmx.cs` | L12221 | `SelectVehicleType` | `void` | `` | `sp_AppVehicle_Type, sp_selectVehicleMakeByType, sp_AppVehicle_MakefrQuotationApp, sp_AppVehicle_Make` |
| 276 | `Insurance\Service.asmx.cs` | L12251 | `selectVehicleMakeByType` | `void` | `` | `sp_selectVehicleMakeByType, sp_AppVehicle_MakefrQuotationApp, sp_AppVehicle_Make, sp_SelectAppMakeforGCV` |
| 277 | `Insurance\Service.asmx.cs` | L12283 | `selectVehicleMakeByTypeNew` | `void` | `string opr` | `sp_selectVehicleMakeByType, sp_AppVehicle_Make, sp_SelectAppMakeforGCV, sp_SelectAppMakeforMiss_D` |
| 278 | `Insurance\Service.asmx.cs` | L12317 | `SelectAppMakeforGCV` | `void` | `` | `sp_SelectAppMakeforGCV, sp_SelectAppMakeforMiss_D, sp_SelectAppMakeforPCV` |
| 279 | `Insurance\Service.asmx.cs` | L12348 | `SelectAppMakeforMiss_D` | `void` | `` | `sp_SelectAppMakeforMiss_D, sp_SelectAppMakeforPCV, sp_SelectAppMakeforPvtCar` |
| 280 | `Insurance\Service.asmx.cs` | L12379 | `SelectAppMakeforPCV` | `void` | `` | `sp_SelectAppMakeforPCV, sp_SelectAppMakeforPvtCar, sp_SelectAppMakeforTwo_Wheeler` |
| 281 | `Insurance\Service.asmx.cs` | L12411 | `SelectAppMakeforPvtCar` | `void` | `` | `sp_SelectAppMakeforPvtCar, sp_SelectAppMakeforTwo_Wheeler, sp_selectVehicleVariantByModel, sp_AppVehicle_model` |
| 282 | `Insurance\Service.asmx.cs` | L12443 | `SelectAppMakeforTwo_Wheeler` | `void` | `` | `sp_SelectAppMakeforTwo_Wheeler, sp_selectVehicleVariantByModel, sp_AppVehicle_model, sp_AppVehicleModel` |
| 283 | `Insurance\Service.asmx.cs` | L12474 | `` | `unknown` | `` | `sp_selectVehicleVariantByModel, sp_AppVehicle_model, sp_AppVehicleModel, sp_AppVehicleVaraintswithSubtype_frQuotApp` |
| 284 | `Insurance\Service.asmx.cs` | L12506 | `` | `unknown` | `` | `sp_selectVehicleVariantByModel, sp_AppVehicleModel, sp_AppVehicleVaraintswithSubtype_frQuotApp, sp_AppVehicleVaraintswithtype` |
| 285 | `Insurance\Service.asmx.cs` | L12538 | `selectVehicleVariantSubType` | `void` | `int ModelId, int VehSubTypeId` | `sp_selectVehicleVariantByModel, sp_AppVehicleVaraintswithSubtype_frQuotApp, sp_AppVehicleVaraintswithtype, sp_selectVehicleModelName` |
| 286 | `Insurance\Service.asmx.cs` | L12571 | `` | `unknown` | `` | `sp_AppVehicleVaraintswithtype, sp_selectVehicleModelName, sp_SelectIDVDetails` |
| 287 | `Insurance\Service.asmx.cs` | L12603 | `selectVehicleModeldetails` | `void` | `int VehicleModelId` | `sp_selectVehicleModelName, sp_SelectIDVDetails, sp_APPInsuranceCompany` |
| 288 | `Insurance\Service.asmx.cs` | L12635 | `SelectIDVDetails` | `void` | `int VariantID` | `sp_SelectIDVDetails, sp_APPInsuranceCompany, sp_selectAPPInsuranceCompanyId` |
| 289 | `Insurance\Service.asmx.cs` | L12663 | `` | `unknown` | `` | `sp_APPInsuranceCompany, sp_selectAPPInsuranceCompanyId, sp_AppLoginforQuatation` |
| 290 | `Insurance\Service.asmx.cs` | L12692 | `selectAPPInsuranceCompanyId` | `void` | `int InsuranceCompanyId` | `sp_selectAPPInsuranceCompanyId, sp_AppLoginforQuatation` |
| 291 | `Insurance\Service.asmx.cs` | L12721 | `` | `unknown` | `` | `sp_AppLoginforQuatation, sp_SelectAppDiscount` |
| 292 | `Insurance\Service.asmx.cs` | L12795 | `SelectAppDiscount` | `void` | `int Age, int Make_ID, int Model_ID, int InsuranceCompanyId` | `sp_SelectAppDiscount, sp_SelectAppDiscountNew` |
| 293 | `Insurance\Service.asmx.cs` | L12844 | `SelectAppDiscountNew` | `void` | `string Age, int Model_ID, int InsuranceCompanyId, string NCB, int ClusterId` | `sp_SelectAppDiscountNew, sp_SelectAppDiscountNew1` |
| 294 | `Insurance\Service.asmx.cs` | L12895 | `SelectAppDiscountNew1` | `void` | `string Age, int Model_ID, int InsuranceCompanyId, string NCB, int ClusterId, string Zer...` | `sp_SelectAppDiscountNew1, sp_SelectZeroDep` |
| 295 | `Insurance\Service.asmx.cs` | L12950 | `SelectZeroDep` | `void` | `int InsuranceCompanyId, int Make_ID, int P_Age` | `sp_SelectZeroDep, sp_SelectZeroDepsegmentwise, sp_selectZeroDepModelIdWise` |
| 296 | `Insurance\Service.asmx.cs` | L12982 | `SelectZeroDepSegmentwise` | `void` | `int InsuranceCompanyId, int Make_ID, int P_Age, int SegmentId` | `sp_SelectZeroDepsegmentwise, sp_selectZeroDepModelIdWise, sp_selectAppRto` |
| 297 | `Insurance\Service.asmx.cs` | L13016 | `SelectZeroDepModelIdwise` | `void` | `int InsuranceCompanyId, int Make_ID, int P_Age, int Model_Id, int FuelTypeId` | `sp_selectZeroDepModelIdWise, sp_selectAppRto, sp_SelectRTOByID` |
| 298 | `Insurance\Service.asmx.cs` | L13056 | `selectAppRto` | `void` | `` | `sp_selectAppRto, sp_SelectRTOByID, sp_InsertAppQuotationEntry` |
| 299 | `Insurance\Service.asmx.cs` | L13086 | `SelectRTOByID` | `void` | `int RTOId` | `sp_SelectRTOByID, sp_InsertAppQuotationEntry` |
| 300 | `Insurance\Service.asmx.cs` | L13115 | `` | `unknown` | `` | `sp_InsertAppQuotationEntry` |
| 301 | `Insurance\Service.asmx.cs` | L13203 | `CheckQuatationTitle` | `void` | `string Title` | `sp_CheckQuatationTitle, sp_GenrateQuatationCode, sp_AppODDiscountSelectcomapny` |
| 302 | `Insurance\Service.asmx.cs` | L13241 | `GenrateQuatationCode` | `void` | `` | `sp_GenrateQuatationCode, sp_AppODDiscountSelectcomapny` |
| 303 | `Insurance\Service.asmx.cs` | L13276 | `AppODDiscountSelectcomapny` | `void` | `` | `sp_AppODDiscountSelectcomapny, sp_FuelType` |
| 304 | `Insurance\Service.asmx.cs` | L13306 | `` | `unknown` | `` | `sp_AppODDiscountSelectcomapny, sp_FuelType, sp_SelectAppDiscWithFueltype` |
| 305 | `Insurance\Service.asmx.cs` | L13333 | `` | `unknown` | `` | `sp_FuelType, sp_SelectAppDiscWithFueltype, sp_SelectAppDiscWithFueltypeGCV` |
| 306 | `Insurance\Service.asmx.cs` | L13363 | `SelectAppDiscWithFueltype` | `void` | `string Age, int Model_ID, int InsuranceCompanyId, string NCB, int ClusterId, string Zer...` | `sp_SelectAppDiscWithFueltype, sp_SelectAppDiscWithFueltypeGCV` |
| 307 | `Insurance\Service.asmx.cs` | L13407 | `SelectAppDiscWithFueltypeGCV` | `void` | `string Age, int Model_ID, int InsuranceCompanyId, string NCB, int ClusterId, string Zer...` | `sp_SelectAppDiscWithFueltypeGCV, Sp_SelectMakeModelvarientForQuotation, sp_selectSelfQuotation` |
| 308 | `Insurance\Service.asmx.cs` | L13454 | `SelectMakeModelvarientForQuotation` | `void` | `int Make_ID, int Model_ID, int Variant_ID` | `Sp_SelectMakeModelvarientForQuotation, sp_selectSelfQuotation, sp_insert_app_requestedquotationfile` |
| 309 | `Insurance\Service.asmx.cs` | L13486 | `` | `unknown` | `` | `sp_selectSelfQuotation, sp_insert_app_requestedquotationfile` |
| 310 | `Insurance\Service.asmx.cs` | L13522 | ` ` | `unknown` | `` | `sp_insert_app_requestedquotationfile, sp_AppSelectCompanyFromType` |
| 311 | `Insurance\Service.asmx.cs` | L13559 | `AppGetRequestedQuotationfile` | `void` | `int QuotationId` | `sp_insert_app_requestedquotationfile, sp_AppSelectCompanyFromType, sp_SelectInsuranceCompanyZeroDep` |
| 312 | `Insurance\Service.asmx.cs` | L13597 | `AppSelectCompanyFromType` | `void` | `string Opr` | `sp_AppSelectCompanyFromType, sp_SelectInsuranceCompanyZeroDep, sp_SelectDaysForBreakingPolicy` |
| 313 | `Insurance\Service.asmx.cs` | L13629 | `selectInsuranceCompanyZerodep` | `void` | `int CompanyId` | `sp_SelectInsuranceCompanyZeroDep, sp_SelectDaysForBreakingPolicy, sp_SelectZeroDepExtraAmount` |
| 314 | `Insurance\Service.asmx.cs` | L13658 | `SelectDaysForBreakingPolicy` | `void` | `DateTime ExpiryDate` | `sp_SelectDaysForBreakingPolicy, sp_SelectZeroDepExtraAmount, sp_SelectAppDiscDiclineOrNot` |
| 315 | `Insurance\Service.asmx.cs` | L13689 | `SelectZeroDepExtraAmount` | `void` | `int InsuranceCompanyId, int Make_Id, int Model_Id, int VehicleType_Id` | `sp_SelectZeroDepExtraAmount, sp_SelectAppDiscDiclineOrNot, sp_ODDiscountCondition` |
| 316 | `Insurance\Service.asmx.cs` | L13723 | `SelectAppDiscDiclineOrNot` | `void` | `int Make_ID, int Model_ID, int InsuranceCompanyId, string NCB, int ClusterId, string Ze...` | `sp_SelectAppDiscDiclineOrNot, sp_ODDiscountCondition, sp_FuelTypeByVehiId` |
| 317 | `Insurance\Service.asmx.cs` | L13768 | `SelectODDiscountCondition` | `void` | `int InsuranceCompanyId, string opr` | `sp_ODDiscountCondition, sp_FuelTypeByVehiId, sp_SelectIDVDetailsForGCV` |
| 318 | `Insurance\Service.asmx.cs` | L13806 | `SelectFuelTypeByVehicleTypeId` | `void` | `int VehicleTypeId` | `sp_FuelTypeByVehiId, sp_SelectIDVDetailsForGCV, Sp_Select_Insurancecompanywisetowingchanges` |
| 319 | `Insurance\Service.asmx.cs` | L13837 | `SelectIDVDetailsForGCV` | `void` | `int VariantID, string Opr` | `sp_SelectIDVDetailsForGCV, Sp_Select_Insurancecompanywisetowingchanges, sp_SelectZeroDepMultiAddOn_New` |
| 320 | `Insurance\Service.asmx.cs` | L13868 | `SelectTowingChargesByCompanyId` | `void` | `int InsuranceCompanyId, string Opr, string Selection` | `Sp_Select_Insurancecompanywisetowingchanges, sp_SelectZeroDepMultiAddOn_New, Sp_AppSelectBodyType` |
| 321 | `Insurance\Service.asmx.cs` | L13901 | `SelectAddOnNEW` | `void` | `int InsuranceCompanyId, int MakeID, int Model_Id, int Age, int Fueltypeid, int Business...` | `sp_SelectZeroDepMultiAddOn_New, Sp_AppSelectBodyType, sp_AppVehicleVariantTypeForGCV` |
| 322 | `Insurance\Service.asmx.cs` | L13944 | `SelectAppBodyType` | `void` | `int Veh_Type_ID` | `Sp_AppSelectBodyType, sp_AppVehicleVariantTypeForGCV, sp_AppSelectTPRateForTwoWheeler` |
| 323 | `Insurance\Service.asmx.cs` | L13979 | `selectVehicleVariantTypeForGCV` | `void` | `int ModelId, int VehTypeId, string Body_Type` | `sp_AppVehicleVariantTypeForGCV, sp_AppSelectTPRateForTwoWheeler, sp_AppSelectTPRateForPCV` |
| 324 | `Insurance\Service.asmx.cs` | L14013 | `AppSelectTPRateForTwoWheeler` | `void` | `int Age, int VehTypeId, double CCValue` | `sp_AppSelectTPRateForTwoWheeler, sp_AppSelectTPRateForPCV, sp_AppSelectTPRateForBUS` |
| 325 | `Insurance\Service.asmx.cs` | L14046 | `AppSelectTPRateForPCV` | `void` | `int Age, int VehTypeId, double CCValue` | `sp_AppSelectTPRateForPCV, sp_AppSelectTPRateForBUS, sp_AppSelectTPRateForThreeWheeler` |
| 326 | `Insurance\Service.asmx.cs` | L14082 | `AppSelectTPRateForBUS` | `void` | `int Age, int VehTypeId, string Bus_Type` | `sp_AppSelectTPRateForBUS, sp_AppSelectTPRateForThreeWheeler, Sp_SelectBusType` |
| 327 | `Insurance\Service.asmx.cs` | L14116 | `AppSelectTPRateForThreeWheeler` | `void` | `int Age, int VehTypeId` | `sp_AppSelectTPRateForThreeWheeler, Sp_SelectBusType, Sp_AppSelectVersion` |
| 328 | `Insurance\Service.asmx.cs` | L14151 | `SelectBusType` | `void` | `string Opr` | `Sp_SelectBusType, Sp_AppSelectVersion, Sp_GetQuotationCodeForSelfRequestedQuotation` |
| 329 | `Insurance\Service.asmx.cs` | L14180 | `AppSelectVersion` | `void` | `` | `Sp_AppSelectVersion, Sp_GetQuotationCodeForSelfRequestedQuotation` |
| 330 | `Insurance\Service.asmx.cs` | L14210 | `GetQuotationCodeForSelfQuotation` | `void` | `int UserRoleId, int Id, int VehicleTypeId, int InsuranceCompanyId` | `Sp_GetQuotationCodeForSelfRequestedQuotation, Sp_AppSelectVersion, sp_SelectCashBackAppRequest` |
| 331 | `Insurance\Service.asmx.cs` | L14244 | ` ` | `unknown` | `` | `Sp_AppSelectVersion, sp_SelectCashBackAppRequest, sp_InsertIDVRequest` |
| 332 | `Insurance\Service.asmx.cs` | L14272 | `SelectCashBackAppRequest` | `void` | `int SalesEx_id, string Opr` | `sp_SelectCashBackAppRequest, sp_InsertIDVRequest` |
| 333 | `Insurance\Service.asmx.cs` | L14303 | `InsertCashBackAppRequest` | `void` | `string Opr, int TransanctionId, string[] photos` | `sp_InsertIDVRequest, sp_SelectCashBackAppRequest, sp_SelectSalesExecutiveCommissionGridnew` |
| 334 | `Insurance\Service.asmx.cs` | L14366 | `SelectSalesExecutiveCommissionGridnew` | `void` | `int EmpId, int InsuranceCompanyid, int PolicyType, int ProductType, int FuelTypeId, int...` | `sp_SelectSalesExecutiveCommissionGridnew, SP_SelectstandardAgentforFranchaiseCommission` |
| 335 | `Insurance\Service.asmx.cs` | L14406 | `SelectFranchiseCommission` | `void` | `int FranchiseId, int InsuranceCompanyid, string ReferenceType, string PolicyType, strin...` | `SP_SelectstandardAgentforFranchaiseCommission, SP_SelectstandardAgentforFranchaiseCommission_ncb` |
| 336 | `Insurance\Service.asmx.cs` | L14454 | `SelectFranchiseCommission_ncb` | `void` | `int FranchiseId, int InsuranceCompanyid, string ReferenceType, string PolicyType, strin...` | `SP_SelectstandardAgentforFranchaiseCommission_ncb, sp_SelectCommVehAge` |
| 337 | `Insurance\Service.asmx.cs` | L14511 | `SelectCommVehAge` | `void` | `int InsuranceCompanyid, int PolicyTypeId, int ProductTypeId` | `sp_SelectCommVehAge, sp_SelectYearSlab, sp_FillTransactionAllBranchNew` |
| 338 | `Insurance\Service.asmx.cs` | L14542 | `SelectYearSlab` | `void` | `int InsuranceCompanyid, int Year, string Opr` | `sp_SelectYearSlab, sp_FillTransactionAllBranchNew, sp_SelectPrevRenewalByAgentbyCount` |
| 339 | `Insurance\Service.asmx.cs` | L14574 | `ViewPolicyPoint` | `void` | `string VehNo` | `sp_FillTransactionAllBranchNew, sp_SelectPrevRenewalByAgentbyCount, sp_SelectEwalletBalance` |
| 340 | `Insurance\Service.asmx.cs` | L14606 | `SelectPrevRenewalByAgentSalesEXbyCount` | `void` | `int Id, string FinancialYearOld, string FinancialYear, int Month, string Opr` | `sp_SelectPrevRenewalByAgentbyCount, sp_SelectEwalletBalance, sp_Champanion` |
| 341 | `Insurance\Service.asmx.cs` | L14639 | `SelectEwalletBalanceByAgent` | `void` | `int AgentId` | `sp_SelectEwalletBalance, sp_Champanion` |
| 342 | `Insurance\Service.asmx.cs` | L14676 | `SelectChampanion` | `void` | `` | `sp_Champanion, Sp_InsertAppTransctiondetailsNew4` |
| 343 | `Insurance\Service.asmx.cs` | L14709 | `public void InsertAppTransctiondetailsNew_4(string OtherAgen` | `unknown` | `` | `Sp_InsertAppTransctiondetailsNew4` |
| 344 | `Insurance\Service.asmx.cs` | L14883 | `public void InsertAppTransctiondetailsNew_5(string OtherAgen` | `unknown` | `` | `Sp_InsertAppTransctiondetailsNew5` |
| 345 | `Insurance\Service.asmx.cs` | L15056 | `public void InsertAppTransctiondetailsNew_6(string OtherAgen` | `unknown` | `` | `Sp_InsertAppTransctiondetailsNew6` |
| 346 | `Insurance\Service.asmx.cs` | L15234 | `public void InsertAppTransctiondetailsNew_7(string OtherAgen` | `unknown` | `` | `Sp_InsertAppTransctiondetailsNew7` |
| 347 | `Insurance\Service.asmx.cs` | L15415 | `public void InsertAppTransctiondetailsNew_8(string OtherAgen` | `unknown` | `` | `Sp_InsertAppTransctiondetailsNew8` |
| 348 | `Insurance\Service.asmx.cs` | L15611 | `SelectNCBData` | `void` | `int InsuranceCompanyId, int PolicyTypeId, int ProductTypeId, int VehiTypeId` | `sp_ncbSelectforGrid, Sp_SelectPolicyTypeByVehtypeNew, sp_CutNPayGridMiuns` |
| 349 | `Insurance\Service.asmx.cs` | L15643 | `SelectPolicyTypeByVehtypeNew` | `void` | `int InsuranceCompanyId, int VehiTypeId` | `Sp_SelectPolicyTypeByVehtypeNew, sp_CutNPayGridMiuns, sp_InsertTransaction_Img` |
| 350 | `Insurance\Service.asmx.cs` | L15676 | `CutNPayGridMiuns` | `void` | `` | `sp_CutNPayGridMiuns, sp_InsertTransaction_Img, sp_InsertTransaction_PDF` |
| 351 | `Insurance\Service.asmx.cs` | L15709 | `SaveAppPolicyImg` | `void` | `string img, int TransId` | `sp_InsertTransaction_Img, sp_InsertTransaction_PDF, Sp_InsertAppMISEntry1` |
| 352 | `Insurance\Service.asmx.cs` | L15740 | `SaveAppPolicyPDF` | `void` | `string pdfFile1, int TransId` | `sp_InsertTransaction_PDF, Sp_InsertAppMISEntry1, Sp_InsertMIS_Quatationpdf` |
| 353 | `Insurance\Service.asmx.cs` | L15767 | `InsertAppMIS1` | `void` | `int UserId, int salesexecutiveId, DateTime MISDate, string[] policypdf, string[] Quotat...` | `Sp_InsertAppMISEntry1, Sp_InsertMIS_Quatationpdf, Sp_InsertMIS_policypdf` |
| 354 | `Insurance\Service.asmx.cs` | L15919 | `SaveAppSupportImg` | `void` | `string[] img, int SupportId` | `sp_Insert_SupportAPPfiles, sp_PE_Insert_CalliberPolicyId` |
| 355 | `Insurance\Service.asmx.cs` | L15958 | `SaveAppSupportPDF` | `void` | `string[] pdfFile1, int SupportId` | `sp_Insert_SupportAPPfiles, sp_PE_Insert_CalliberPolicyId` |
| 356 | `Insurance\Service.asmx.cs` | L15997 | `PE_Insert_CalliberPolicyId` | `void` | `string FinancialYear` | `sp_PE_Insert_CalliberPolicyId` |
| 357 | `Insurance\Service.asmx.cs` | L16031 | `public void PE_UpdateCalliberPolicy(int requestId, string sr` | `unknown` | `` | `Direct / Helper` |
| 358 | `Insurance\Service.asmx.cs` | L16365 | `public void InsertAppTransctiondetailsNew_NM(string OtherAge` | `unknown` | `` | `Sp_InsertAppTransctiondetailsNew4_NM` |
| 359 | `Insurance\VehicleService.asmx.cs` | L23 | `HelloWorld` | `string` | `` | `Direct / Helper` |
| 360 | `Insurance\VehicleService.asmx.cs` | L30 | `GetVehicleDetails` | `string` | `string vehicleNumber, string blacklistCheck, bool splitAddress` | `Direct / Helper` |
| 361 | `Insurance\Clerk\DashBoradBranchPremium.aspx.cs` | L81 | `GetChartDataBranch` | `List<BranchDetails>` | `` | `BLL_DashBoard, BLL_DashBoradBranchPremiumSummary` |
| 362 | `Insurance\Clerk\DashBoradMotorPremiumaspx.aspx.cs` | L186 | `GetChartData` | `List<VehicleDetails>` | `DataTable dtReport` | `BLL_DashBoard, BLL_SelectYear, BLL_SelectProductNetPermiumbyMotar` |
| 363 | `Insurance\Clerk\DashBoradNonMotorPremium.aspx.cs` | L31 | `GetChartDataNonMotor` | `List<VehicleDetails>` | `` | `BLL_DashBoard, BLL_DashBoardNonMotorSummery, BLL_SelectProductNetPermiumbyNonMotar` |
| 364 | `Insurance\Clerk\Dashboard_PrevYearRenewalStatus.aspx.cs` | L39 | `GetChartData` | `List<RenewalSatusDetails>` | `` | `BLL_DashBoard, BLL_SelectPreYearStatusGraph, BLL_SelectMonth` |
| 365 | `Insurance\Clerk\GraphicalDashBoard.aspx.cs` | L36 | `GetChartData` | `List<VehicleDetails>` | `` | `BLL_DashBoard, BLL_vehicleType_Summary, BLL_BusinessType_Summary` |
| 366 | `Insurance\Clerk\GraphicalDashBoard.aspx.cs` | L66 | `GetChartDataBusiness` | `List<BusinessDetails>` | `` | `BLL_DashBoard, BLL_BusinessType_Summary, BLL_PolicyMode_Summary` |
| 367 | `Insurance\Clerk\GraphicalDashBoard.aspx.cs` | L92 | `GetChartDataPolicy` | `List<PolicyDetails>` | `` | `BLL_DashBoard, BLL_PolicyMode_Summary` |
| 368 | `Insurance\Clerk\GraphicalDashBoardLocHead.aspx.cs` | L33 | `GetChartData` | `List<VehicleDetails>` | `` | `BLL_DashBoard, BLL_DashBoardVehicleTypeLocHead, BLL_BusinessType_SummaryLocHead` |
| 369 | `Insurance\Clerk\GraphicalDashBoardLocHead.aspx.cs` | L63 | `GetChartDataBusiness` | `List<BusinessDetails>` | `` | `BLL_DashBoard, BLL_BusinessType_SummaryLocHead, BLL_DashBoardPolicyModeLocHead` |
| 370 | `Insurance\Clerk\GraphicalDashBoardLocHead.aspx.cs` | L89 | `GetChartDataPolicy` | `List<PolicyDetails>` | `` | `BLL_DashBoard, BLL_DashBoardPolicyModeLocHead` |
| 371 | `Insurance\Clerk\Location.aspx.cs` | L132 | `pie_Premium_Summary1` | `string[]` | `` | `BLL_DashBoard, BLL_PolicyType_Summary, BLL_ODPremium_Summary` |
| 372 | `Insurance\Clerk\Location.aspx.cs` | L149 | `pie_ODNetPremium_Summary` | `string[]` | `` | `BLL_DashBoard, BLL_ODPremium_Summary` |
| 373 | `Insurance\Clerk\MIS_RequestExective.aspx.cs` | L236 | `` | `unknown` | `` | `BLL_Agent, BLL_obj, BLL_searchAppAgentSalesExecWise` |
| 374 | `Insurance\Clerk\SearchMethods.aspx.cs` | L34 | `GetCustVehicleNo` | `string[]` | `string prefix` | `BLL_CustVehicle, BLL_obj, BLL_SerachcustVehicle` |
| 375 | `Insurance\Clerk\SearchMethods.aspx.cs` | L53 | `GetCustByVehicleNo` | `string[]` | `string prefix` | `BLL_CustVehicle, BLL_obj, BLL_SerachcustByVehicle` |
| 376 | `Insurance\Clerk\SearchMethods.aspx.cs` | L73 | `GetQuatationNo` | `string[]` | `string prefix` | `BLL_CustVehicle, BLL_obj, BLL_SearchByQutationNo` |
| 377 | `Insurance\Clerk\SearchMethods.aspx.cs` | L92 | `GetCustName` | `string[]` | `string prefix` | `BLL_Customer, BLL_obj, BLL_SearchCustName` |
| 378 | `Insurance\Clerk\SearchMethods.aspx.cs` | L111 | `GetAgentName` | `string[]` | `string prefix` | `BLL_Agent, BLL_obj, BLL_SearchAgentName` |
| 379 | `Insurance\Clerk\SearchMethods.aspx.cs` | L153 | `GetPOSPName` | `string[]` | `string prefix` | `BLL_ProfitReport, BLL_obj, BLL_SearchPOSPName` |
| 380 | `Insurance\Clerk\SearchMethods.aspx.cs` | L179 | `GetFranchiseName` | `string[]` | `string prefix` | `BLL_Agent, BLL_obj, BLL_SearchtxtName` |
| 381 | `Insurance\Clerk\SearchMethods.aspx.cs` | L198 | `GetFranchiseAgentName` | `string[]` | `string prefix` | `BLL_Agent, BLL_obj, BLL_SearchtxtName` |
| 382 | `Insurance\Clerk\SearchMethods.aspx.cs` | L217 | `GetSalesExName` | `string[]` | `string prefix` | `BLL_Agent, BLL_obj, BLL_SearchtxtName` |
| 383 | `Insurance\Clerk\SearchMethods.aspx.cs` | L237 | `SearchtextAgentName` | `string[]` | `string prefix` | `BLL_Agent, BLL_obj, BLL_SearchtextAgentName` |
| 384 | `Insurance\Clerk\SearchMethods.aspx.cs` | L257 | `SearchtextEmpName` | `string[]` | `string prefix` | `BLL_Agent, BLL_obj, BLL_SearchtextEmpName` |
| 385 | `Insurance\Clerk\SearchMethods.aspx.cs` | L278 | `GetPolicyNo` | `string[]` | `string prefix` | `BLL_Transaction, BLL_obj, BLL_searchPolicyNo` |
| 386 | `Insurance\Clerk\SearchMethods.aspx.cs` | L298 | `GetPolicyNoByCheqe` | `string[]` | `string prefix` | `BLL_Transaction, BLL_obj, BLL_SearchPolicyNobyCheque` |
| 387 | `Insurance\Clerk\SearchMethods.aspx.cs` | L320 | `checkVehicleNo` | `string` | `string vehNo, string FinancialYear` | `BLL_CustVehicle, BLL_CheckRegistrationNo, BLL_InsertPushNotiRenewal` |
| 388 | `Insurance\Clerk\SearchMethods.aspx.cs` | L336 | `InsertPushNotiRenewal` | `string` | `string ExternalId, string Status` | `BLL_CustVehicle, BLL_InsertPushNotiRenewal, BLL_ViewAppTransaction` |
| 389 | `Insurance\Clerk\SearchMethods.aspx.cs` | L353 | `getNewAppEntry` | `string` | `` | `BLL_ViewAppTransaction, BLL_obj, BLL_APPEntryPopUp` |
| 390 | `Insurance\Clerk\SearchMethods.aspx.cs` | L362 | `getNewAppEntryOp` | `string` | `` | `BLL_ViewAppTransaction, BLL_obj, BLL_APPEntryPopUp` |
| 391 | `Insurance\Clerk\SearchMethods.aspx.cs` | L388 | `getPendingEntryOp` | `string` | `` | `BLL_ViewAppTransaction, BLL_SelectOperatorPendingEntry, BLL_InsuranceCompCreditsDaysPendingEntry` |
| 392 | `Insurance\Clerk\SearchMethods.aspx.cs` | L412 | `getPendingInwardOp` | `string` | `` | `BLL_ViewAppTransaction, BLL_InsuranceCompCreditsDaysPendingEntry, BLL_ChatBoard` |
| 393 | `Insurance\Clerk\SearchMethods.aspx.cs` | L440 | `getNewChatOp` | `string` | `` | `BLL_ChatBoard, BLL_SelectChat, BLL_WebNotification` |
| 394 | `Insurance\Clerk\SearchMethods.aspx.cs` | L467 | `getAdminNotification` | `string` | `` | `BLL_WebNotification, BLL_SelectWebNotification, BLL_ViewAppTransaction` |
| 395 | `Insurance\Clerk\SearchMethods.aspx.cs` | L482 | `getNewAppEndorsementEntry` | `string` | `` | `BLL_ViewAppTransaction, BLL_obj, BLL_EndorsementReadStatus` |
| 396 | `Insurance\Clerk\SearchMethods.aspx.cs` | L493 | `getNewMISAppEntry` | `string` | `` | `BLL_ViewMISTransction, BLL_APPMISEntryPopUp, BLL_DashBoard` |
| 397 | `Insurance\Clerk\SearchMethods.aspx.cs` | L502 | `chart_Premium_Summary` | `ArrayList` | `` | `BLL_DashBoard, BLL_Premium_Summary, BLL_PolicyType_Summary` |
| 398 | `Insurance\Clerk\SearchMethods.aspx.cs` | L520 | `pie_Premium_Summary` | `ArrayList` | `` | `BLL_DashBoard, BLL_PolicyType_Summary, BLL_ODPremium_Summary` |
| 399 | `Insurance\Clerk\SearchMethods.aspx.cs` | L536 | `pie_Premium_Summary1` | `string` | `` | `BLL_DashBoard, BLL_PolicyType_Summary, BLL_ODPremium_Summary` |
| 400 | `Insurance\Clerk\SearchMethods.aspx.cs` | L567 | `pie_ODPremium_Summary` | `string` | `` | `BLL_DashBoard, BLL_ODPremium_Summary, BLL_PolicyMode_Summary` |
| 401 | `Insurance\Clerk\SearchMethods.aspx.cs` | L599 | `PolicyMode_Premium_Summary` | `ArrayList` | `` | `BLL_DashBoard, BLL_PolicyMode_Summary, BLL_BusinessType_Summary` |
| 402 | `Insurance\Clerk\SearchMethods.aspx.cs` | L616 | `businesstype_Premium_Summary` | `ArrayList` | `` | `BLL_DashBoard, BLL_BusinessType_Summary, BLL_ProductType_Summary` |
| 403 | `Insurance\Clerk\SearchMethods.aspx.cs` | L633 | `ProductType_Premium_Summary` | `ArrayList` | `` | `BLL_DashBoard, BLL_ProductType_Summary, BLL_ODNetPremium_Summary` |
| 404 | `Insurance\Clerk\SearchMethods.aspx.cs` | L651 | `pie_ODNetPremium_Summary` | `string` | `` | `BLL_DashBoard, BLL_ODNetPremium_Summary, BLL_ODNetMonthlyPremium` |
| 405 | `Insurance\Clerk\SearchMethods.aspx.cs` | L683 | `pie_ODNetMonthlyPremium` | `string` | `` | `BLL_DashBoard, BLL_ODNetMonthlyPremium, BLL_ODNetDailyPremium` |
| 406 | `Insurance\Clerk\SearchMethods.aspx.cs` | L714 | `pie_ODNetDailyPremium` | `string` | `` | `BLL_DashBoard, BLL_ODNetDailyPremium, BLL_PolicyMode_Summary` |
| 407 | `Insurance\Clerk\SearchMethods.aspx.cs` | L745 | `PolicyMode_Premium_Summary1` | `string` | `` | `BLL_DashBoard, BLL_PolicyMode_Summary, BLL_BusinessType_Summary` |
| 408 | `Insurance\Clerk\SearchMethods.aspx.cs` | L777 | `businesstype_Premium_Summary1` | `string` | `` | `BLL_DashBoard, BLL_BusinessType_Summary, BLL_ProductType_Summary` |
| 409 | `Insurance\Clerk\SearchMethods.aspx.cs` | L811 | `ProductType_Premium_Summary1` | `string` | `` | `BLL_DashBoard, BLL_ProductType_Summary, BLL_DashBoardInsuranceCompany` |
| 410 | `Insurance\Clerk\SearchMethods.aspx.cs` | L844 | `DashBoardInsuranceCompany` | `string` | `` | `BLL_DashBoard, BLL_DashBoardInsuranceCompany, BLL_ViewAppAgentTransction` |
| 411 | `Insurance\Clerk\SearchMethods.aspx.cs` | L876 | `getNewAgentAppEntry` | `string` | `` | `BLL_ViewAppAgentTransction, BLL_APPAgentEntryPopUp, BLL_DashBoard` |
| 412 | `Insurance\Clerk\SearchMethods.aspx.cs` | L886 | `pie_Premium_Summary_Vehicle` | `ArrayList` | `` | `BLL_DashBoard, BLL_vehicleType_Summary, BLL_ViewAppTransaction` |
| 413 | `Insurance\Clerk\SearchMethods.aspx.cs` | L903 | `getserverInactive` | `string` | `` | `BLL_ViewAppTransaction, BLL_obj, BLL_APPEntryPopUp` |
| 414 | `Insurance\Clerk\SearchMethods.aspx.cs` | L938 | `SearchtextEmpCode` | `string[]` | `string prefix` | `BLL_Agent, BLL_obj, BLL_SearchtextEmpCode` |
| 415 | `Insurance\Clerk\rpt_POSP_Invoice.aspx.cs` | L360 | `GetPOSPName` | `string[]` | `string prefix, int POSPType_Id` | `BLL_ProfitReport, BLL_obj, BLL_searchPOSP_Agent` |
| 416 | `Insurance\Clerk\rpt_POSP_InvoiceReport.aspx.cs` | L97 | `GetPOSPName` | `string[]` | `string prefix, int POSPType_Id` | `BLL_ProfitReport, BLL_obj, BLL_searchPOSP_Agent` |
