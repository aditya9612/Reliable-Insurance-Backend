# 03 — Legacy Database & Entity Inventory

> **Audit Status**: CONFIRMED FROM CODE & CONFIGURATION (`UNKNOWN — EVIDENCE NOT AVAILABLE` for live MySQL DDL not committed to source control)
> **Database Engine**: MySQL (`MySql.Data` v6.9.9.0)
> **Database Name**: `brahmainsurance` (Port `3309`)

---

## 1. Database Connectivity & Execution Architecture

**Evidence**: `Insurance\Web.config` (L15), `DAL\dbConnection.cs` (L1–42), `Insurance\Service.asmx.cs` (L35)

1. **Connection String (`dbInsuranceCon`)**:
   - `server=localhost; user id=root; password=***MASKED***; database=brahmainsurance; port=3309; pooling=false; default command Timeout=4200; Allow User Variables=True`
2. **Connection Pooling Disabled**:
   - `pooling=false` forces a physical TCP/MySQL handshake on every query execution.
3. **Command Timeout**:
   - `default command Timeout=4200` (70 minutes), masking slow/unindexed reporting and recalculation queries.
4. **Zero `.sql` Schema Files in Repository**:
   - Forensic scan of the entire workspace confirmed **0 `.sql` files**. Table DDL, indexes, foreign keys, triggers, and stored procedure SQL bodies exist exclusively inside the live MySQL server instance (`brahmainsurance`) and are therefore marked **`UNKNOWN — EVIDENCE NOT AVAILABLE`** where not directly visible in C# inline SQL or ADO.NET parameter bindings.

---

## 2. Database Tables Confirmed from Inline SQL Queries (10 Tables)

Although 95%+ of database operations use Stored Procedures, **19 raw SQL queries** in C# code directly reference **10 physical table names** in `brahmainsurance`:

| # | Physical Table Name (Lower-cased) | Evidence Classification | Confirmed Source Locations (`File:Line`) |
| :--- | :--- | :--- | :--- |
| 1 | `tbl_claim_finalbill_doc` | CONFIRMED FROM CODE (Raw SQL) | Insurance\Clerk\CL_ClaimNew.aspx.cs:L1595, Insurance\Clerk\CL_ClaimNew.aspx.cs:L343, Insurance\Clerk\CL_ClaimNew.aspx.cs:L361 |
| 2 | `tbl_claim_quotation_img` | CONFIRMED FROM CODE (Raw SQL) | Insurance\Clerk\CL_ClaimNew.aspx.cs:L1557, Insurance\Clerk\CL_ClaimNew.aspx.cs:L493, Insurance\Clerk\CL_ClaimNew.aspx.cs:L512 |
| 3 | `tbl_claimassistance` | CONFIRMED FROM CODE (Raw SQL) | Insurance\Clerk\CL_ClaimNew.aspx.cs:L952 |
| 4 | `tbl_claimassistanceimg` | CONFIRMED FROM CODE (Raw SQL) | Insurance\Clerk\CL_ClaimNew.aspx.cs:L1025, Insurance\Clerk\CL_ClaimNew.aspx.cs:L1044 |
| 5 | `tbl_claimaudiolist` | CONFIRMED FROM CODE (Raw SQL) | Insurance\Clerk\CL_ClaimNew.aspx.cs:L627, Insurance\Clerk\CL_ClaimNew.aspx.cs:L646 |
| 6 | `tbl_claimimg` | CONFIRMED FROM CODE (Raw SQL) | Insurance\Clerk\CL_ClaimNew.aspx.cs:L1517, Insurance\Clerk\adm_Claims.aspx.cs:L85 |
| 7 | `tbl_claims` | CONFIRMED FROM CODE (Raw SQL) | Insurance\Clerk\adm_Claims.aspx.cs:L233 |
| 8 | `tbl_endorsementimages` | CONFIRMED FROM CODE (Raw SQL) | Insurance\Clerk\adm_EndorsmentReport.aspx.cs:L120, Insurance\Clerk\adm_EndorsmentReport.aspx.cs:L186 |
| 9 | `tbl_importagentpolicy` | CONFIRMED FROM CODE (Raw SQL) | Insurance\Clerk\adm_ImportTransAgentPolicyMIS.aspx.cs:L195, Insurance\WebForm3.aspx.cs:L199 |
| 10 | `tbl_user` | CONFIRMED FROM CODE (Raw SQL) | DAL\DAL_Operations.cs:L20223 |

---

## 3. Critical Legacy Field Naming & Spelling Quirks (Parity-Critical)

The legacy C# codebase and stored procedure parameters contain numerous pervasive misspellings that **MUST** be accounted for when mapping legacy data or API payloads:

| Legacy Identifier (Exact Spelling) | Standard Meaning | Found In Class / Table / SP Parameter | Evidence (`File:Line`) |
| :--- | :--- | :--- | :--- |
| `TransanctionId` / `transanctionid` | `TransactionId` | `API_TransactionPayment`, `API_PremiumBatchwise`, `API_accountpremiumreceivingmultientry`, `API_franchaiseCommission`, `API_AgentCommPayment` | `API\AllMaster.cs`: L698, L763, L774, L1215, L1491 |
| `ODPermium` | `ODPremium` | `API_Transaction.ODPermium`, `P_ODPermium` | `API\AllMaster.cs`: L505; `DAL\DAL_Operations.cs`: L2165 |
| `TPPermium` | `TPPremium` | `API_Transaction.TPPermium`, `P_TPPermium` | `API\AllMaster.cs`: L506; `DAL\DAL_Operations.cs`: L2166 |
| `NetPermium` | `NetPremium` | `API_Transaction.NetPermium`, `P_NetPermium` | `API\AllMaster.cs`: L507; `DAL\DAL_Operations.cs`: L2167 |
| `NCBPermium` | `NCBPremium` | `API_Transaction.NCBPermium`, `P_NCBPermium` | `API\AllMaster.cs`: L503; `DAL\DAL_Operations.cs`: L2163 |
| `finalPrmium` | `FinalPremium` | `API_QuotationSelf.finalPrmium` | `API\AllMaster.cs`: L2360; `SelfQuotationRequest.aspx.cs`: L1482 |
| `QuatationCode` | `QuotationCode` | `API_Transaction.QuatationCode`, `API_QuotationSelf.QuatationCode` | `API\AllMaster.cs`: L526, L2316 |
| `ChaiseNo` | `ChassisNo` | `API_CustVehicle.ChaiseNo`, `P_ChaiseNo` | `API\AllMaster.cs`: L412; `PolicyTransactionNew.aspx.cs`: L931 |
| `MoblieNo` / `MoblieNo1` / `MoblieNo2` | `MobileNo` / `MobileNo1` / `MobileNo2` | `API_Employee`, `API_Customer`, `P_MoblieNo1` | `API\AllMaster.cs`: L217, L458, L459 |
| `IntensiveAmount` | `IncentiveAmount` | `API_Transaction.IntensiveAmount` | `API\AllMaster.cs`: L567 |
| `deudate` | `DueDate` | `API_Transaction.deudate` | `API\AllMaster.cs`: L573 |
| `ExGird` / `lbl_SelfGird` | `ExGrid` / `SelfGrid` | `API_Transaction.ExGird`, `adm_NcbRecovery.aspx.cs` | `API\AllMaster.cs`: L574; `adm_NcbRecovery.aspx.cs`: L335 |
| `EletricAccessories` | `ElectricAccessories` | `API_QuotationSelf.EletricAccessories` | `SelfQuotationRequest.aspx.cs`: L1456 |
| `CNGFulekits` / `FuleTypeId` | `CNGFuelKits` / `FuelTypeId` | `API_QuotationSelf.CNGFulekits`, `API_GridDecline.FuleTypeId` | `API\AllMaster.cs`: L37; `SelfQuotationRequest.aspx.cs`: L1457 |
| `TStatus` | `TransactionStatus` | `API_Transaction.TStatus` | `API\AllMaster.cs`: L520 |
| `ProfitofNetCommision` / `totalCommision` | `ProfitOfNetCommission` / `TotalCommission` | `API_franchaiseCommission`, `API_AgentCommPayment` | `PolicyTransactionNew.aspx.cs`: L1514; `PE_TransactionEntry.aspx.cs`: L9892 |

---

## 4. Complete Entity / DTO Class Catalog (`API\AllMaster.cs` — 188 Classes)

| # | Class Name | Base Class | Line Range | Property Count | Key Properties (Exact Names & Types) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | `API_LoginHistory` | `-` | L9–L23 | 10 | `UserId` (int), `UserRoleId` (int), `UserName` (string), `ReferenceId` (int), `LoginDate` (DateTime), `Remark` (string), `LogInOrLogOut` (string), `funPerform` (string) ... (+2 more, total 10 fields) |
| 2 | `API_GridDecline` | `-` | L24–L42 | 12 | `DeclineId` (int), `DeclineDate` (DateTime), `InsuranceCompanyId` (int), `MakeId` (int), `PolicyTypeId` (int), `ModelId` (int), `RtoId` (int), `ProductTypeId` (int) ... (+4 more, total 12 fields) |
| 3 | `API_BusinessType` | `-` | L43–L47 | 2 | `BTypeID` (int), `BusinessType` (string) |
| 4 | `API_PolicyType` | `-` | L48–L55 | 5 | `PTypeID` (int), `PolicyType` (string), `Veh_Type_ID` (int), `Min_GCV_GW` (double), `Max_GCV_GVW` (double) |
| 5 | `API_FuelMater` | `-` | L56–L60 | 2 | `fuelID` (int), `fuelType` (string) |
| 6 | `API_RTOMaster` | `-` | L61–L68 | 5 | `RTO_ID` (int), `RTO_Location` (string), `StateId` (int), `District` (string), `REG_code` (string) |
| 7 | `API_VehicleType` | `-` | L69–L73 | 2 | `VehicleTypeId` (int), `VehicleType` (string) |
| 8 | `API_VehicleMake` | `API_VehicleType` | L74–L90 | 11 | `VehicleMakeId` (int), `CompanyName` (string), `Rmakeid` (string), `GCV` (int), `Misc_D` (int), `PCV` (int), `PvtCar` (int), `Two_Wheeler` (int) ... (+3 more, total 11 fields) |
| 9 | `API_VehicleVariant` | `API_VehicleMake` | L91–L132 | 38 | `VehicleModelId` (int), `VehicleModelName` (string), `VehicleMakeId` (int), `SeatsCapacity` (string), `EnginePower` (string), `VehicleWeight` (string), `Variant_ID` (int), `Veh_Type_ID` (int) ... (+30 more, total 38 fields) |
| 10 | `API_BranchType` | `-` | L133–L137 | 2 | `BranchTypeId` (int), `BranchType` (string) |
| 11 | `API_Branch` | `API_BranchType` | L138–L146 | 5 | `BranchId` (int), `BranchCode` (string), `BranchName` (string), `Address` (string), `ContactNo` (string) |
| 12 | `API_BankMaster` | `-` | L147–L151 | 2 | `BankId` (int), `BankName` (string) |
| 13 | `API_LocationMaster` | `-` | L152–L156 | 2 | `LocationId` (int), `Location` (string) |
| 14 | `API_categaory` | `-` | L157–L161 | 2 | `categaoryId` (int), `categaoryName` (string) |
| 15 | `API_BankAccount` | `API_BankMaster` | L162–L177 | 12 | `BankAccountId` (int), `AccountNo` (string), `BankBranch` (string), `IfscCode` (string), `ReferenceId` (int), `UserRoleId` (int), `CreateUser` (string), `CreateDate` (DateTime) ... (+4 more, total 12 fields) |
| 16 | `API_UserRole` | `-` | L178–L182 | 2 | `UserRoleId` (int), `UserRole` (string) |
| 17 | `API_SalesType` | `-` | L183–L187 | 2 | `SalesTypeId` (int), `Description` (string) |
| 18 | `API_reliablecompanymst` | `-` | L188–L194 | 3 | `RCompanyId` (int), `RCompany` (string), `Prefix` (string) |
| 19 | `API_Address` | `-` | L195–L200 | 3 | `StateID` (int), `DistrictID` (int), `TalukaID` (int) |
| 20 | `API_Employee` | `-` | L201–L321 | 104 | `EmpId` (int), `UserName` (string), `UserPassword` (string), `EmpCode` (string), `EmpFName` (string), `EmpMName` (string), `EmpLName` (string), `AddrLine1` (string) ... (+96 more, total 104 fields) |
| 21 | `API_Hie_Desn` | `-` | L322–L333 | 5 | `DesnId` (int), `DesnName` (string), `ClassId` (int), `FuncId` (int), `UserRoleId` (int) |
| 22 | `API_AgentPayemtInvoice` | `-` | L334–L353 | 11 | `InvoiceId` (int), `InvoiceNo` (string), `IMonth` (int), `Iyear` (string), `AgentId` (int), `AccountDate` (DateTime), `DocNo` (string), `Amount` (double) ... (+3 more, total 11 fields) |
| 23 | `API_PolicyMode` | `-` | L354–L359 | 2 | `PolicyId` (int), `PolicyMode` (string) |
| 24 | `API_commvehAge` | `-` | L360–L368 | 6 | `Id` (int), `InsuranceCompanyId` (int), `PolicyTypeId` (int), `ProductTypeId` (int), `CreatedUser` (string), `createdDate` (DateTime) |
| 25 | `API_Slab` | `-` | L369–L379 | 8 | `Id` (int), `InsuranceCompanyId` (int), `Slab` (string), `fromslab` (string), `toslab` (string), `PolicyTypeId` (int), `ProductTypeId` (int), `RtoId` (int) |
| 26 | `API_Product` | `-` | L380–L384 | 2 | `ProductId` (int), `ProductType` (string) |
| 27 | `API_Designation` | `-` | L385–L389 | 2 | `DesignationId` (int), `DesignationType` (string) |
| 28 | `API_InsuranceCompany` | `-` | L390–L397 | 5 | `InsuranceCompanyId` (int), `InsuranceCompany` (string), `BranchName` (string), `BranchCode` (string), `MailId` (string) |
| 29 | `API_LedgerType` | `-` | L398–L407 | 6 | `LedgerTypeId` (int), `LedgerType` (string), `CreateUser` (string), `CreateDate` (DateTime), `UpdateUser` (string), `UpdateDate` (DateTime) |
| 30 | `API_CustVehicle` | `API_Customer` | L408–L435 | 24 | `CustVehId` (int), `RegistrationNo` (string), `ChaiseNo` (string), `EngineNo` (string), `MfgMonth` (string), `MfgYear` (string), `Ex_ShowroomPrice` (string), `FuelTypeId` (int) ... (+16 more, total 24 fields) |
| 31 | `API_Customer` | `-` | L436–L475 | 37 | `CustomerId` (int), `initial` (string), `CustFName` (string), `CustMName` (string), `CustLName` (string), `CustomerType` (string), `ClientId` (int), `CustomerCode` (string) ... (+29 more, total 37 fields) |
| 32 | `API_Transaction` | `-` | L476–L628 | 120 | `TransactionId` (int), `InwardNo` (string), `TransDate` (DateTime), `BranchId` (int), `PolicyTypeId` (int), `CustomerId` (int), `CustVehId` (int), `PolicyNo` (string) ... (+112 more, total 120 fields) |
| 33 | `API_TransactionFile` | `-` | L629–L641 | 8 | `Id` (int), `TransFileName` (string), `TransFilePath` (string), `TransFileType` (string), `TransactionId` (int), `Flag` (string), `TransType` (string), `Extra` (string) |
| 34 | `API_LedgerMaster` | `-` | L642–L655 | 10 | `LedgerMId` (int), `LedgerTypeId` (int), `LedgerName` (string), `LedgerGroupId` (int), `ReferenceId` (int), `BranchId` (int), `CreateDate` (DateTime), `CreateUser` (string) ... (+2 more, total 10 fields) |
| 35 | `API_CorporateClient` | `-` | L656–L668 | 10 | `ClientId` (int), `CompanyName` (string), `AddressLine1` (string), `AddressLine2` (string), `DistrictID` (int), `StateID` (int), `TalukaID` (int), `ContactNo` (string) ... (+2 more, total 10 fields) |
| 36 | `API_AppClientUSer` | `-` | L669–L681 | 8 | `AppClientId` (int), `ClientId` (int), `AppUser` (string), `AppPassword` (string), `CreateUser` (string), `CreateDate` (DateTime), `UpdateUser` (string), `UpdateDate` (DateTime) |
| 37 | `API_TransactionPayment` | `-` | L682–L711 | 25 | `PaymentId` (int), `PaymentDate` (DateTime), `PaymentType` (string), `PaymentDetails` (string), `bankname` (string), `docno` (string), `PaidAmount` (double), `CashierApproval` (int) ... (+17 more, total 25 fields) |
| 38 | `API_AccTransType` | `-` | L712–L716 | 2 | `AccTransId` (int), `AccTransType` (string) |
| 39 | `API_Account` | `API_AccTransType` | L717–L744 | 24 | `AccountId` (int), `FromledgerID` (int), `ToledgerID` (int), `AccountDate` (DateTime), `LedgerMId` (int), `amount` (double), `Narration` (string), `ReferenceCustId` (int) ... (+16 more, total 24 fields) |
| 40 | `API_PremiumReceipt` | `-` | L745–L756 | 8 | `ReceiptId` (int), `LedgerType` (string), `LedgerMId` (int), `ReceiptDate` (DateTime), `ReferenceId` (int), `amount` (double), `Narration` (string), `BalAmt` (double) |
| 41 | `API_PremiumBatchwise` | `-` | L757–L768 | 8 | `rowId` (int), `Batchid` (int), `BatchAmt` (double), `Date` (DateTime), `transanctionid` (int), `PremiumAmt` (double), `Apppaid` (double), `cut_pass` (double) |
| 42 | `API_accountpremiumreceivingmultientry` | `-` | L769–L784 | 7 | `Id` (int), `AccountId` (int), `PendingCashId` (int), `TransanctionId` (int), `AccountDate` (DateTime), `Amount` (double), `LedgerMid` (int) |
| 43 | `API_ClearingAccount` | `API_AccTransType` | L785–L810 | 22 | `AccountId` (int), `FromledgerID` (int), `ToledgerID` (int), `AccountDate` (DateTime), `LedgerMId` (int), `amount` (double), `Narration` (string), `ReferenceCustId` (int) ... (+14 more, total 22 fields) |
| 44 | `API_Commission` | `-` | L811–L825 | 11 | `CommissionId` (int), `FormulaName` (string), `ReferenceType` (string), `InsuranceCompany` (string), `PolicyType` (string), `ProductType` (string), `CommissionCalculateOn` (string), `FlatRate` (string) ... (+3 more, total 11 fields) |
| 45 | `API_Endorsement` | `-` | L826–L880 | 48 | `HistoryID` (int), `HistoryDate` (DateTime), `PolicyId` (int), `VehicleId` (int), `PreviousCustomerId` (int), `CurrentCustomerId` (int), `Extra1` (string), `Extra2` (string) ... (+40 more, total 48 fields) |
| 46 | `API_EndorsementPdf` | `-` | L881–L889 | 3 | `PdfId` (int), `EndorsementId` (int), `pdfName` (string) |
| 47 | `API_Endorsementimages` | `-` | L890–L896 | 4 | `EndorsementImagesId` (int), `EndorsementId` (int), `EndorsementDate` (DateTime), `EndorsementImagePath` (string) |
| 48 | `API_PolicyPdf` | `-` | L897–L902 | 3 | `TransanctionId` (int), `uploadDate` (DateTime), `filePath` (string) |
| 49 | `API_appMobGird` | `-` | L903–L910 | 5 | `Id` (int), `GridText` (string), `filePath` (string), `CreateUser` (string), `VaildFromDate` (DateTime) |
| 50 | `API_OutStandingAmount` | `-` | L911–L928 | 15 | `OutstandingId` (int), `OutStandingDate` (DateTime), `TransanctionId` (int), `CustomerId` (int), `AgentId` (int), `EmpId` (int), `LedgerMId` (int), `OutstandingAmount` (double) ... (+7 more, total 15 fields) |
| 51 | `API_Customersupporttype` | `-` | L929–L936 | 3 | `CustSupporttypeId` (int), `CustSupporttype` (string), `isdeleted` (string) |
| 52 | `API_Document_type` | `-` | L937–L959 | 18 | `DocumenttypeId` (int), `Document_type` (string), `InsuranceCompany` (string), `DocNo` (string), `BeneficiaryName` (string), `RegistrationNo` (string), `Amount` (string), `ExpiryDate` (string) ... (+10 more, total 18 fields) |
| 53 | `API_CallStatus` | `-` | L960–L967 | 3 | `CallStatusId` (int), `CallStatus` (string), `isdeleted` (string) |
| 54 | `API_Claims` | `-` | L968–L1020 | 42 | `ClaimAudioId` (int), `Audiopath` (string), `Description` (string), `ClaimImgPath` (string), `ClaimImgDate` (DateTime), `ClaimImgId` (int), `ClaimsId` (int), `CustomerId` (int) ... (+34 more, total 42 fields) |
| 55 | `API_Claims_Spot_Serve` | `-` | L1021–L1031 | 6 | `SpotSurveyId` (int), `ClaimsId` (int), `SurveyorName` (string), `MobileNo` (string), `SurveyDate` (DateTime), `isdeleted` (string) |
| 56 | `API_Claims_Garage_Serve` | `-` | L1032–L1042 | 6 | `GarageSurveyId` (int), `ClaimsId` (int), `SurveyorName` (string), `MobileNo` (string), `SurveyDate` (DateTime), `isdeleted` (string) |
| 57 | `API_Claims_Quotation` | `-` | L1043–L1055 | 7 | `QuotationId` (int), `ClaimsId` (int), `QuotStatus` (int), `QuotDate` (DateTime), `outid` (int), `QuotImgId` (int), `QuotImgPath` (string) |
| 58 | `API_Claims_FinalBill` | `-` | L1056–L1070 | 9 | `FBDocId` (int), `FBillDocPath` (string), `FBId` (int), `ClaimsId` (int), `FBillDate` (DateTime), `BillAmt` (double), `ICLAmt` (double), `ILAmt` (double) ... (+1 more, total 9 fields) |
| 59 | `API_CallRecord` | `-` | L1071–L1082 | 8 | `CallRecordId` (int), `CustomerId` (int), `CallDate` (DateTime), `CustSupporttypeId` (int), `GPSLoacation` (string), `isdeleted` (string), `Longitude` (string), `Latitute` (string) |
| 60 | `API_CallRecordHistory` | `-` | L1083–L1093 | 7 | `CallRecordHistoryId` (int), `CallRecordId` (int), `RecordHistoryDate` (DateTime), `CallAction` (string), `CallForwordPerson` (string), `CallStatusId` (int), `isdeleted` (string) |
| 61 | `API_CustPolicyinfoEdocs` | `-` | L1094–L1106 | 9 | `CustpolicyinfoId` (int), `DocumentTypeId` (int), `CustomerId` (int), `InsuranceCompanyId` (int), `DocNo` (string), `BeneficiaryName` (string), `RegistrationNo` (string), `Amount` (double) ... (+1 more, total 9 fields) |
| 62 | `API_RewardPoint` | `-` | L1107–L1115 | 6 | `RewardPointId` (int), `RefCustId` (int), `RewardDate` (DateTime), `RewardPointGet` (int), `RewardPointUtilizes` (int), `PointBalance` (int) |
| 63 | `API_Help_And_Record` | `-` | L1116–L1130 | 10 | `CustHelpHistoryId` (int), `CustHelpId` (int), `HelpHistoryDate` (DateTime), `HelpAction` (string), `HelpForwordPerson` (string), `CallStatusId` (int), `isdeleted` (string), `HelpAttachmentId` (int) ... (+2 more, total 10 fields) |
| 64 | `API_CustomerHelpType` | `-` | L1131–L1136 | 2 | `HelpId` (int), `HelpType` (string) |
| 65 | `API_CustomerHelp` | `-` | L1137–L1144 | 4 | `CustHelpId` (int), `CustomerId` (int), `HelpId` (int), `CustDate` (DateTime) |
| 66 | `API_CustomerApp` | `-` | L1145–L1155 | 6 | `CustomerId` (decimal), `Name` (string), `MoblieNo1` (string), `MoblieNo2` (string), `EMailId` (string), `Address` (string) |
| 67 | `API_StatusMessage` | `-` | L1156–L1160 | 2 | `Status` (string), `StatusMessage` (string) |
| 68 | `API_Customernew` | `-` | L1161–L1166 | 1 | `CustomerId` (decimal) |
| 69 | `API_MyDocument` | `-` | L1167–L1204 | 28 | `DocumenttypeId` (int), `CustomerId` (int), `VehicleInsuranceId` (int), `InsuranceCompanyId` (int), `DocNo` (int), `DocumentName` (string), `PolicyNo` (int), `PolicyName` (string) ... (+20 more, total 28 fields) |
| 70 | `API_CustomerReference` | `-` | L1205–L1219 | 11 | `RefCustId` (int), `CustomerId` (int), `CustName` (string), `ContactNo` (string), `BirthDate` (DateTime), `CustReferenceImgid` (int), `CustrefImgDate` (DateTime), `CustrefImgpath` (string) ... (+3 more, total 11 fields) |
| 71 | `API_CustomerAPPNew` | `-` | L1220–L1229 | 6 | `APPCustomerId` (decimal), `APPCustomerName` (string), `ContactNo` (string), `ContactNo1` (string), `EmailId` (string), `Address` (string) |
| 72 | `API_PaymentMode` | `-` | L1230–L1234 | 2 | `PaymentModeId` (int), `PaymentMode` (string) |
| 73 | `API_DashBoard` | `-` | L1235–L1240 | 3 | `Particular` (string), `ODPremium` (double), `NetPremium` (double) |
| 74 | `API_AgentCommPayment` | `-` | L1241–L1262 | 17 | `AgentCommId` (int), `FromDate` (DateTime), `ToDate` (DateTime), `TransanctionId` (int), `BranchName` (string), `AgentName` (string), `PremiumAmount` (double), `NetCommission` (double) ... (+9 more, total 17 fields) |
| 75 | `API_Agent` | `-` | L1263–L1278 | 10 | `UserId` (decimal), `SalesExecutiveId` (decimal), `CoordinatorId` (decimal), `AgentId` (decimal), `UserName` (string), `Password` (string), `Coordinator` (string), `UserRoleId` (string) ... (+2 more, total 10 fields) |
| 76 | `API_AgentNew` | `-` | L1279–L1299 | 15 | `UserId` (decimal), `SalesExecutiveId` (decimal), `CoordinatorId` (decimal), `AgentId` (decimal), `UserName` (string), `Password` (string), `Coordinator` (string), `UserRoleId` (string) ... (+7 more, total 15 fields) |
| 77 | `API_Dashboard` | `-` | L1300–L1311 | 2 | `UserId` (decimal), `UserRoleId` (string) |
| 78 | `API_Agentcomm` | `-` | L1312–L1326 | 8 | `totalAgentComm` (double), `Paid` (double), `Unpaid` (double), `currentBusiness` (double), `MonthlyBusiness` (double), `Monthlydirect` (double), `walletBalance` (double), `Yearly_Bussiness` (double) |
| 79 | `API_Executivecomm` | `-` | L1327–L1341 | 10 | `totalAgentComm` (double), `Paid` (double), `Unpaid` (double), `currentBusiness` (double), `MonthlyBusiness` (double), `Monthlydirect` (double), `walletBalance` (double), `Yearly_Bussiness` (double) ... (+2 more, total 10 fields) |
| 80 | `API_FranchiseAppProfit` | `-` | L1342–L1351 | 3 | `Agent_Point` (double), `Self_Point` (double), `total_Profit` (double) |
| 81 | `API_APPTarget` | `-` | L1352–L1362 | 4 | `YearAssignTarget` (double), `MonthlyAssignTaregt` (double), `YearAchievedTargetAmount` (double), `MonthlyAchievedTaret` (double) |
| 82 | `API_Vehicle_Type` | `-` | L1363–L1369 | 2 | `Vehicle_Type_Id` (int), `Vehicle_Type_Name` (string) |
| 83 | `API_Vehicle_SubType` | `-` | L1370–L1377 | 3 | `Veh_Sub_Type_ID` (int), `Veh_Sub_Type_Name` (string), `Veh_Type_ID` (int) |
| 84 | `API_Model` | `-` | L1378–L1389 | 6 | `ModelId` (int), `Makeid` (int), `ModelName` (string), `Rmakeid` (string), `Type` (int), `SegmentId` (int) |
| 85 | `API_ODDiscount` | `API_VehicleVariant` | L1390–L1400 | 6 | `AppODDiscount` (int), `NewVehicle` (string), `ZerotoFive` (string), `fivetoTen` (string), `Greaterthen10` (string), `InsuranceCompanyId` (int) |
| 86 | `API_Zerodep` | `API_VehicleVariant` | L1401–L1412 | 7 | `ZerodepId` (int), `Type` (int), `Age` (int), `NillDep` (string), `SecurePlus` (string), `SPremium` (string), `InsuranceCompanyId` (int) |
| 87 | `api_circular` | `-` | L1413–L1421 | 4 | `circularid` (int), `circulardate` (DateTime), `subject` (string), `pdfpath` (string) |
| 88 | `API_Message` | `-` | L1422–L1431 | 7 | `MessagedetailId` (int), `Messagedate` (DateTime), `userId` (int), `MessageID` (int), `readStatus` (int), `Message` (string), `Flag` (string) |
| 89 | `API_NonMotorEndorsmentSubType` | `-` | L1432–L1438 | 3 | `EndorsementSubTypeId` (int), `EndorsementTypeId` (int), `EndorsementType` (string) |
| 90 | `API_Class` | `-` | L1439–L1444 | 2 | `ClassId` (int), `Class` (string) |
| 91 | `API_NonMotorProduct` | `API_Class` | L1445–L1450 | 3 | `productId` (int), `ProductType` (string), `ProductCode` (string) |
| 92 | `API_NonTransaction` | `-` | L1451–L1509 | 54 | `TransactionId` (int), `InwardNo` (string), `TransDate` (DateTime), `BranchId` (int), `CoverNote` (string), `PolicyTypeId` (int), `CustomerId` (int), `CustVehId` (int) ... (+46 more, total 54 fields) |
| 93 | `API_Target` | `-` | L1510–L1526 | 13 | `financialYear` (string), `month` (string), `AchievedTargetAmount` (double), `EmpId` (int), `targetmonth` (string), `AnnualAmount` (string), `createuser` (string), `updateuser` (string) ... (+5 more, total 13 fields) |
| 94 | `API_TargetHistory` | `-` | L1527–L1535 | 4 | `TargetHistoryDate` (DateTime), `EmpId` (int), `Description` (string), `Amount` (double) |
| 95 | `API_franchise` | `-` | L1536–L1599 | 52 | `UserName` (string), `UserPassword` (string), `FranchaiseId` (int), `initial` (string), `FranFName` (string), `FranMName` (string), `FranLName` (string), `FranCode` (string) ... (+44 more, total 52 fields) |
| 96 | `API_franchaiseCommission` | `-` | L1600–L1646 | 32 | `FranchiseCommId` (int), `TransanctionId` (int), `FranchiseId` (int), `AgentId` (int), `FranchaiseDate` (DateTime), `tat` (double), `Franchisecomm` (double), `FranchiseCommAmt` (double) ... (+24 more, total 32 fields) |
| 97 | `API_new_franchaiseCommission` | `-` | L1647–L1693 | 32 | `FranchiseCommId` (int), `TransanctionId` (int), `FranchiseId` (int), `AgentId` (int), `FranchaiseDate` (DateTime), `tat` (double), `Franchisecomm` (double), `FranchiseCommAmt` (double) ... (+24 more, total 32 fields) |
| 98 | `API_SignUp` | `-` | L1694–L1700 | 3 | `FranchiseId` (decimal), `oldversion` (string), `newversion` (string) |
| 99 | `API_SignUpNew` | `-` | L1701–L1714 | 11 | `UserId` (decimal), `SalesExecutiveId` (decimal), `CoordinatorId` (decimal), `AgentId` (decimal), `UserName` (string), `Password` (string), `Coordinator` (string), `UserRoleId` (string) ... (+3 more, total 11 fields) |
| 100 | `APIAPPODDiscount` | `-` | L1715–L1753 | 28 | `AppODDiscountId` (int), `MakeId` (int), `Fueltypeid` (int), `Model_ID` (int), `InsuranceCompanyId` (int), `BusinessTypeId` (int), `Decline` (int), `NCB` (string) ... (+20 more, total 28 fields) |
| 101 | `API_tbl_agentcommissionpaymenttransactiondtl` | `-` | L1754–L1768 | 9 | `Trans_dtl_Id` (int), `TransanctionId` (int), `AgentCommId` (int), `AgentId` (int), `PremiumAmount` (double), `NetCommission` (double), `TransDate` (DateTime), `isdeleted` (string) ... (+1 more, total 9 fields) |
| 102 | `API_tbl_insurancecompanyquotation` | `-` | L1769–L1784 | 9 | `QuotationId` (int), `InsuranceCompanyId` (int), `TransctionId` (int), `agentId` (int), `QuotationFile` (string), `EmpId` (int), `Remark` (string), `isdeleted` (Boolean) ... (+1 more, total 9 fields) |
| 103 | `API_FranchiseAgentComm` | `-` | L1785–L1812 | 23 | `FAComissionId` (int), `AgentId` (int), `InsuranceCompanyId` (int), `Tat` (string), `Comission` (double), `Min_Commission` (double), `Max_Commission` (double), `ReferenceType` (string) ... (+15 more, total 23 fields) |
| 104 | `API_AgentDocumentList` | `-` | L1813–L1824 | 6 | `AgentDocId` (int), `DocId` (int), `RefereranceCode` (string), `Ref_Type` (string), `DocImagePath` (string), `Flag` (string) |
| 105 | `API_NonMotorCommission` | `-` | L1825–L1847 | 16 | `InsuranceCompanyId` (int), `InsuranceTypeId` (int), `InsuranceSubTypeId` (int), `TypeSubTypeId` (int), `ReferanceId` (int), `CreateDate` (DateTime), `CreateUser` (int), `UpdateDate` (DateTime) ... (+8 more, total 16 fields) |
| 106 | `API_PAToOwnerDriver` | `-` | L1848–L1856 | 4 | `PAToOwnerDriverId` (int), `InsuranceCompanyId` (int), `Rate` (double), `TowingCharges` (double) |
| 107 | `API_StsticInformation` | `-` | L1857–L1873 | 11 | `Id` (int), `InsuranceCompanyId` (int), `VehicleTypeId` (int), `PolicyTypeId` (int), `ProductTypeId` (int), `Commission` (double), `ExtraAmt_RA` (double), `ExtraAmt_AGT` (double) ... (+3 more, total 11 fields) |
| 108 | `API_ZeroDepSegment` | `-` | L1874–L1887 | 8 | `ZerodepId` (int), `Make_ID` (int), `Model_ID` (int), `Age` (int), `NillDep` (string), `SecurePlus` (string), `SPremium` (string), `InsuranceCompanyId` (int) |
| 109 | `API_agentwisesummery` | `-` | L1888–L1905 | 13 | `AgentWiseSummeryId` (int), `AgentId` (int), `AgentNetSum` (double), `BankUTRNo` (string), `AgentWiseDate` (DateTime), `DifferenceAmount` (double), `CheckName` (string), `InvSeries` (string) ... (+5 more, total 13 fields) |
| 110 | `API_AddOnExtraAmt` | `-` | L1906–L1920 | 9 | `ExtraAddonId` (int), `InsuranceCompanyId` (int), `VehicleTypeId` (int), `MakeId` (int), `ModelId` (int), `Age` (string), `NillDep` (double), `SecurePlus` (double) ... (+1 more, total 9 fields) |
| 111 | `API_cutnpaycommpayable` | `-` | L1921–L1933 | 9 | `CutNPayCommPayId` (int), `TransactionId` (int), `SalesExId` (int), `AgentId` (int), `CustomerId` (int), `PolicyNo` (string), `Balance` (double), `CommPayable` (double) ... (+1 more, total 9 fields) |
| 112 | `API_zerodepnewaddonrate` | `-` | L1934–L1951 | 14 | `AddOnId` (int), `Model_ID` (int), `MakeID` (int), `InsuranceCompanyId` (int), `Fueltypeid` (int), `BusinessTypeId` (int), `ClusterId` (int), `PRVDetails` (int) ... (+6 more, total 14 fields) |
| 113 | `API_TransactionEntryRemark` | `-` | L1952–L1962 | 7 | `RemarkId` (int), `TransDate` (DateTime), `TransId` (int), `QuatationCode` (string), `Remark` (string), `UserRoleId` (int), `Quot_Type` (string) |
| 114 | `API_Transactionappnew` | `-` | L1963–L1985 | 17 | `TransId` (int), `insurancecompany` (string), `UserId` (int), `SalesExecutiveId` (int), `ContactNo` (string), `ProductType` (string), `PolicyMode` (string), `PaymentMode` (string) ... (+9 more, total 17 fields) |
| 115 | `API_nonmotorinsurancetype` | `-` | L1986–L1994 | 5 | `InsuranceTypeId` (int), `InsuranceType` (string), `InsuranceCompanyId` (int), `IsDeleted` (int), `Flag` (string) |
| 116 | `API_nonmotorinsurancesubtype` | `-` | L1995–L2003 | 5 | `InsuranceSubTypeId` (int), `InsuranceSubType` (string), `InsuranceTypeId` (int), `Flag` (string), `IsDeleted` (int) |
| 117 | `API_nonmotortypeofinsurancesubtype` | `-` | L2004–L2013 | 6 | `TypeSubTypeId` (int), `TypeOfSubType` (string), `InsuranceTypeId` (int), `InsuranceSubTypeId` (int), `Flag` (string), `IsDeleted` (int) |
| 118 | `API_RawDataForPolicy` | `-` | L2014–L2042 | 19 | `RegNo` (string), `AgentId` (int), `InsuranceCompanyId` (int), `ReferenceType` (string), `PolicyTypeId` (int), `ProductTypeId` (int), `TransDate` (DateTime), `OD_Discount` (double) ... (+11 more, total 19 fields) |
| 119 | `API_accountdebit` | `-` | L2043–L2063 | 15 | `Account_Id` (int), `LedgerMId` (int), `BranchId` (int), `isdeleted` (int), `Narration` (string), `Doc_No` (string), `CreatedUser` (string), `Extra1` (string) ... (+7 more, total 15 fields) |
| 120 | `API_cashback` | `-` | L2064–L2079 | 9 | `cashbackId` (int), `TransactionId` (int), `CustomerId` (int), `CustVehId` (int), `cashbackamount` (double), `TransDate` (DateTime), `CreatedDate` (DateTime), `CreatedUser` (string) ... (+1 more, total 9 fields) |
| 121 | `API_BrokerCommission` | `-` | L2080–L2110 | 23 | `BroCommId` (int), `InsuranceCompanyId` (int), `FranchiseId` (int), `CustVehId` (int), `BranchId` (int), `PolicyTypeId` (int), `ProductTypeId` (int), `StateId` (int) ... (+15 more, total 23 fields) |
| 122 | `API_Claimassistance` | `-` | L2111–L2131 | 18 | `ClaimAssistanceId` (int), `ClaimNo` (string), `ClaimNoUpdateDate` (DateTime), `ClaimNoUpdateUser` (string), `InsuranceCompanyId` (int), `IntimationDate` (DateTime), `VehNo` (string), `DateofAccident` (DateTime) ... (+10 more, total 18 fields) |
| 123 | `API_AgentComm` | `-` | L2132–L2140 | 5 | `Commission` (double), `Commission_OD` (double), `Commission_Net` (double), `CommissionId` (int), `OD_Discount` (double) |
| 124 | `API_InsuranceCompanyPortal` | `-` | L2141–L2154 | 5 | `tbl_Id` (int), `InsuranceCompanyId` (int), `PortalId` (string), `PersonName` (string), `BrokerId` (int) |
| 125 | `API_Targetnew` | `-` | L2155–L2170 | 10 | `financialYear` (string), `month` (string), `EmpId` (int), `targetmonth` (string), `createdate` (DateTime), `AchievedTargetAmount` (double), `TargetAchievdedId` (int), `assignamnt` (double) ... (+2 more, total 10 fields) |
| 126 | `API_WebNotification` | `-` | L2171–L2179 | 2 | `NotId` (int), `NotMessege` (string) |
| 127 | `API_AppchatBorad` | `-` | L2180–L2192 | 8 | `UserRoleId` (int), `ReferenceAgentId` (int), `ChatText` (string), `ChatByUser` (string), `Remark` (string), `Reply` (string), `CoordinatorId` (int), `Registration` (string) |
| 128 | `API_Commissiongetfrominsurancecompany` | `-` | L2193–L2213 | 16 | `InsuranceCompanyId` (int), `PolicyNo` (string), `PortalId` (string), `TransactionId` (int), `CustomerId` (int), `VehicleId` (int), `IRDA_Percent` (double), `IRDA_Amount` (double) ... (+8 more, total 16 fields) |
| 129 | `API_tds` | `-` | L2214–L2225 | 7 | `tdsId` (int), `BrokerId` (int), `InsuranceCompanyId` (int), `ReferenceType` (string), `TdsCut` (double), `ValidFrom` (DateTime), `BranchId` (int) |
| 130 | `API_SelfDiscount` | `-` | L2226–L2241 | 10 | `SelfDiscId` (int), `BrokerId` (int), `BranchId` (int), `ReferenceType` (string), `SelfDiscount` (double), `ValidFrom` (DateTime), `CreatedUser` (string), `CreatedDate` (DateTime) ... (+2 more, total 10 fields) |
| 131 | `API_AppAttendance` | `-` | L2242–L2249 | 1 | `AttendanceId` (int) |
| 132 | `API_HROrganization` | `-` | L2250–L2264 | 8 | `OrganizationId` (int), `OrganizationName` (string), `Address` (string), `MobileNo` (string), `CreatedDate` (DateTime), `CreateUser` (string), `UpdateDate` (DateTime), `UpdatedUser` (string) |
| 133 | `API_HRdeparmentmaster` | `-` | L2265–L2276 | 8 | `DeparmentId` (int), `OrganizationId` (int), `Dname` (string), `Dlocation` (string), `CreatedDate` (DateTime), `CreateUser` (string), `UpdateDate` (DateTime), `UpdatedUser` (string) |
| 134 | `API_HRfaciltitymaster` | `-` | L2277–L2284 | 3 | `FaciltiyId` (int), `Name` (string), `percentage` (string) |
| 135 | `API_hrholidaymaster` | `-` | L2285–L2297 | 8 | `HolidayId` (int), `EmployeeID` (int), `HolidayDesc` (string), `HolidayDate` (DateTime), `CreatedDate` (DateTime), `CreateUser` (string), `UpdateDate` (DateTime), `UpdatedUser` (string) |
| 136 | `API_hrContactperson` | `-` | L2298–L2314 | 10 | `ContactpersonId` (int), `ContactFName` (string), `ContactMName` (string), `ContactLName` (string), `MobileNo` (string), `Address` (string), `CreatedDate` (DateTime), `CreateUser` (string) ... (+2 more, total 10 fields) |
| 137 | `API_HRDesignationMaster` | `-` | L2315–L2325 | 2 | `DesignationId` (int), `Designation` (string) |
| 138 | `API_HRworkingTime` | `-` | L2326–L2347 | 11 | `timeinfoId` (int), `EmployeeID` (int), `DepartMentID` (int), `workingHours` (string), `offday` (string), `overtime` (string), `ExtraDay` (string), `CreateDate` (DateTime) ... (+3 more, total 11 fields) |
| 139 | `API_TempararyOperator` | `-` | L2348–L2360 | 7 | `ID` (int), `Per_OperatorId` (int), `Temp_OperatorId` (int), `CreateDate` (DateTime), `CreateUser` (string), `ValidFrom` (DateTime), `ValidUpTo` (DateTime) |
| 140 | `API_Hrsalarystructuredef` | `-` | L2361–L2379 | 10 | `SalaryStructureDefId` (int), `salaryStructure` (string), `InActive` (string), `RateOnGross` (string), `Remark` (string), `OrganizationId` (int), `CreatedDate` (DateTime), `CreateUser` (string) ... (+2 more, total 10 fields) |
| 141 | `API_HrAdvance` | `-` | L2380–L2407 | 22 | `HrAdvanceId` (int), `EmpId` (int), `OrganizationId` (int), `TotalAdvance` (double), `TotalInterest` (double), `TotalReceipts` (double), `TotalRecovered` (double), `TotalDeu` (double) ... (+14 more, total 22 fields) |
| 142 | `API_HRLeave` | `-` | L2408–L2431 | 19 | `LeaveId` (int), `OrganizationId` (int), `DeparmentId` (int), `EmpId` (int), `LeaveTypeId` (int), `ApplicationDate` (DateTime), `FromDate` (DateTime), `ToDate` (DateTime) ... (+11 more, total 19 fields) |
| 143 | `API_HRLeaveType` | `-` | L2432–L2440 | 2 | `LeaveTypeId` (int), `LeaveType` (string) |
| 144 | `API_HRWorkingDetails` | `-` | L2441–L2467 | 20 | `MonthlyWorkingId` (int), `OrganizationId` (int), `DeparmentId` (int), `EmpId` (int), `Month` (string), `Year` (string), `totalNoOfDays` (double), `Sunday` (double) ... (+12 more, total 20 fields) |
| 145 | `API_HRupdateEmployee` | `-` | L2468–L2549 | 65 | `EmpId` (int), `EmpFName` (string), `EmpMName` (string), `EmpLName` (string), `Address` (string), `Gender` (string), `MaritalStatus` (string), `MoblieNo` (string) ... (+57 more, total 65 fields) |
| 146 | `API_HREmployee` | `-` | L2550–L2609 | 48 | `EmpId` (int), `EmpFName` (string), `EmpMName` (string), `EmpLName` (string), `Address` (string), `Gender` (string), `MaritalStatus` (string), `MoblieNo` (string) ... (+40 more, total 48 fields) |
| 147 | `API_HRInsertworkinghistory` | `-` | L2610–L2635 | 17 | `WorkingHistoryId` (int), `EmployeeID` (int), `DepartMentID` (int), `CompanyName` (string), `CompanyAddres` (string), `CompanyMobileNo` (string), `PreQualification` (string), `PreExprience` (string) ... (+9 more, total 17 fields) |
| 148 | `API_HRFamilyDetails` | `-` | L2636–L2651 | 7 | `FamilyId` (int), `EmployeeID` (int), `FName` (string), `Occuption` (string), `ContactNo` (string), `Designation` (string), `Relation` (string) |
| 149 | `API_HRRefernceDetails` | `-` | L2652–L2666 | 7 | `ReferenceId` (int), `EmployeeID` (int), `ReferenceName` (string), `Address` (string), `ContactNo` (string), `Designation` (string), `MailId` (string) |
| 150 | `API_HREmpProfile` | `-` | L2667–L2675 | 3 | `ProfileId` (int), `EmployeeID` (int), `FilePath` (string) |
| 151 | `API_HRAdvancemaster` | `-` | L2676–L2691 | 10 | `AdvanceId` (int), `OrganizationId` (int), `DeparmentId` (int), `EmpId` (int), `AdvanceDate` (DateTime), `AdvanceAmt` (double), `InstallmentMonth` (int), `FinancialYear` (string) ... (+2 more, total 10 fields) |
| 152 | `API_HRAdvanceDetails` | `-` | L2692–L2703 | 5 | `AdvanceDtlId` (int), `AdvanceId` (int), `MonthId` (int), `FYear` (string), `Amount` (double) |
| 153 | `API_PreYearRenewalStatus` | `-` | L2704–L2723 | 14 | `TransanctionId` (int), `Remark` (string), `FinancialYear` (string), `isdeleted` (int), `CreatedDate` (DateTime), `RegistrationNo` (string), `InsuranceCompany` (string), `TotalPremium` (double) ... (+6 more, total 14 fields) |
| 154 | `APT_AppTransaction` | `-` | L2724–L2818 | 86 | `OtherAgentName` (string), `insurancecompany` (string), `ProductType` (string), `UserId` (int), `SalesExecutiveId` (int), `FranchaiseId` (int), `Initial` (string), `Name` (string) ... (+78 more, total 86 fields) |
| 155 | `API_agentexecutivecredits` | `-` | L2819–L2836 | 10 | `Id` (int), `ReferenceId` (int), `UserRoleId` (int), `Days` (int), `Credits` (double), `ReferenceType` (string), `CreateDate` (DateTime), `CreateUser` (string) ... (+2 more, total 10 fields) |
| 156 | `API_CashierBankDetails` | `-` | L2837–L2857 | 13 | `Id` (int), `PRefrenceId` (int), `TransanctionId` (int), `BankDate` (DateTime), `ReferenceType` (string), `ReferanceId` (int), `Narration` (string), `amount` (double) ... (+5 more, total 13 fields) |
| 157 | `API_tansactionusedewalletdata` | `-` | L2858–L2886 | 9 | `Id` (int), `TransactionId` (int), `UsedAmount` (double), `PendingStatus` (int), `ReferenceType` (string), `ReferenceId` (int), `Paymentdate` (DateTime), `CreatedUser` (string) ... (+1 more, total 9 fields) |
| 158 | `API_ClusterMaster` | `-` | L2887–L2899 | 8 | `ClusterMId` (int), `InsuranceCompanyId` (int), `CreateUser` (string), `CreateDate` (DateTime), `ClusterName` (string), `ClusterDetailsId` (int), `RtoId` (int), `StateId` (int) |
| 159 | `API_clusterwisebrokergrid` | `-` | L2900–L2921 | 18 | `GridId` (int), `GridValue` (double), `CalOn` (string), `ODDiscount` (double), `ValidFrom` (DateTime), `ReferenceType` (string), `BrokerId` (int), `InsuranceCompanyId` (int) ... (+10 more, total 18 fields) |
| 160 | `API_CallingImportDatat` | `-` | L2922–L2942 | 16 | `CallingImportId` (int), `RegistrationNo` (string), `RegistrationType` (string), `RegnDate` (DateTime), `OwnerName` (string), `FatherName` (string), `PermanentAddress` (string), `ChassisNo` (string) ... (+8 more, total 16 fields) |
| 161 | `API_TransSummary` | `-` | L2943–L2955 | 9 | `TransId` (int), `TransDate` (DateTime), `ValueDate` (DateTime), `CHQNO` (string), `Narration` (string), `Amount` (double), `DRCR` (string), `Balance` (string) ... (+1 more, total 9 fields) |
| 162 | `API_salesregistration` | `-` | L2956–L2980 | 19 | `salesRegId` (int), `InvoiceNo` (string), `RegistrationType` (string), `SalesDate` (DateTime), `RCompanyId` (int), `SalesTypeId` (int), `SalesType` (string), `ClientMasterId` (int) ... (+11 more, total 19 fields) |
| 163 | `API_AppQuotationRequest` | `-` | L2981–L3005 | 20 | `InsuranceCompanyId` (string), `AgentId` (int), `ProductType` (string), `QuatationDate` (DateTime), `Zerodepth` (string), `PolicyMode` (string), `MobileNo` (string), `NCB` (string) ... (+12 more, total 20 fields) |
| 164 | `API_ClientMaster` | `-` | L3006–L3025 | 11 | `_ClientMasterId` (int), `Description` (string), `InsuranceCompanyId` (int), `Address` (string), `PanNo` (string), `GST` (string), `CGST` (double), `SGST` (double) ... (+3 more, total 11 fields) |
| 165 | `API_clusterwiseAgentgrid` | `-` | L3026–L3048 | 19 | `GridId` (int), `GridValue` (double), `CalOn` (string), `ODDiscount` (double), `ValidFrom` (DateTime), `ReferenceType` (string), `AgentId` (int), `BrokerId` (int) ... (+11 more, total 19 fields) |
| 166 | `API_AgentService` | `-` | L3049–L3063 | 11 | `UserId` (decimal), `SalesExecutiveId` (decimal), `CoordinatorId` (decimal), `AgentId` (decimal), `UserName` (string), `Password` (string), `Coordinator` (string), `UserRoleId` (string) ... (+3 more, total 11 fields) |
| 167 | `API_ODDISCOUNT` | `-` | L3064–L3069 | 1 | `ODDiscount` (string) |
| 168 | `API_ODDISCOUNTDECLINE` | `-` | L3070–L3074 | 1 | `ODDecline` (string) |
| 169 | `API_QuatationTitle` | `-` | L3075–L3079 | 1 | `count` (string) |
| 170 | `API_QuatationCode` | `-` | L3080–L3085 | 1 | `QuatationCode` (string) |
| 171 | `API_Recondata` | `-` | L3086–L3106 | 16 | `InsuranceCompanyId` (int), `PolicyNo` (string), `RegistrationNo` (string), `ClientName` (string), `accounting_period` (DateTime), `PortalId` (string), `PortalDescription` (string), `ODPremium` (double) ... (+8 more, total 16 fields) |
| 172 | `API_matchrecondata` | `-` | L3107–L3118 | 7 | `ReconId` (int), `TransactionId` (int), `CreatedDate` (DateTime), `CreatedUser` (string), `ReconGrid` (double), `ReconComm` (double), `BrokerId` (int) |
| 173 | `API_Computerinventry` | `-` | L3119–L3132 | 10 | `Id` (int), `DeviceId` (string), `formation` (string), `Processor` (string), `RAM` (string), `Storage1` (string), `Monitor` (string), `KeyBoradMouse` (string) ... (+2 more, total 10 fields) |
| 174 | `API_FranchaiseGridMargin` | `-` | L3133–L3145 | 6 | `Id` (int), `FranchiseId` (int), `FranchiseAgentId` (int), `InsuranceCompanyId` (int), `PolicyTypeId` (int), `margin` (double) |
| 175 | `API_vehiclenorc_details` | `-` | L3146–L3210 | 54 | `VehRcId` (int), `request_id` (string), `license_plate_RegNo` (string), `owner_name` (string), `father_name` (string), `is_financed` (string), `financer` (string), `present_address` (string) ... (+46 more, total 54 fields) |
| 176 | `API_vehiclenorc_details` | `-` | L3211–L3283 | 61 | `VehRcId` (int), `rc_regn_no` (string), `rc_rto_code` (string), `rc_regn_dt` (DateTime), `rc_owner_sr` (string), `rc_registered_at` (string), `rc_fit_upto` (string), `rc_tax_upto` (string) ... (+53 more, total 61 fields) |
| 177 | `API_QuotationSelf` | `-` | L3284–L3358 | 57 | `QuatationCode` (string), `ProductName` (string), `Title` (string), `MgfYear` (string), `RTOId` (int), `Zone` (string), `InsuranceCompanyId` (int), `Veh_Type_ID` (int) ... (+49 more, total 57 fields) |
| 178 | `API_agentCreation` | `-` | L3359–L3373 | 9 | `SalesExId` (int), `AgentFName` (string), `AgentMName` (string), `AgentLName` (string), `MobileNo` (string), `UserId` (int), `EmailId` (string), `NickName` (string) ... (+1 more, total 9 fields) |
| 179 | `API_SupportApp` | `-` | L3374–L3394 | 12 | `SupportId` (int), `SupportTypeId` (int), `SupportDate` (DateTime), `UserId` (int), `UserRoleId` (int), `Remark` (string), `UpdateBy` (string), `UpdateDate` (DateTime) ... (+4 more, total 12 fields) |
| 180 | `API_SupportAPPFile` | `-` | L3395–L3404 | 5 | `Id` (int), `SupportFileName` (string), `SupportFilePath` (string), `SupportFileType` (string), `SupportId` (int) |
| 181 | `APT_AppMISTransaction` | `-` | L3405–L3424 | 14 | `UserId` (int), `salesexecutiveId` (int), `MISDate` (DateTime), `PaymentMode` (string), `PaymentDetails1` (string), `PaymentDetails2` (string), `Amount` (double), `UserRoleId` (int) ... (+6 more, total 14 fields) |
| 182 | `API_IdealPaymentReceipt` | `-` | L3425–L3438 | 9 | `Id` (int), `Ideal_Doc_No` (string), `PaymentDate` (DateTime), `POSPType_Id` (int), `POSP_Id` (int), `Ideal_Amount` (double), `Ideal_NEFTNo` (string), `CreatedBy` (string) ... (+1 more, total 9 fields) |
| 183 | `API_POSO_Invoice` | `-` | L3439–L3453 | 10 | `POSO_InvoiceId` (int), `POSO_InvoiceNo` (string), `POSO_InvoiceDate` (DateTime), `POSPType_Id` (int), `POSP_Id` (int), `Invoice_Amount` (double), `GSTAmt` (double), `GrandTotal` (double) ... (+2 more, total 10 fields) |
| 184 | `API_POSP_AgentDocumentList` | `-` | L3454–L3466 | 7 | `POSP_DocId` (int), `DocId` (int), `Agent_POSP_Id` (int), `Doc_Type` (string), `DocImagePath` (string), `Flag` (string), `InsertDate` (DateTime) |
| 185 | `API_Calliber_Policy` | `-` | L3467–L3638 | 158 | `calliber_policyId` (int), `Request_Id` (int), `insurer` (string), `product` (string), `product_type` (string), `product_sub_type` (string), `product_category` (string), `policy_category` (string) ... (+150 more, total 158 fields) |
| 186 | `API_pe_extraction_new` | `-` | L3639–L3707 | 62 | `Id` (string), `policy_identifier` (string), `is_error` (string), `ncb` (string), `FileName` (string), `insurer` (string), `body_idv` (string), `org_type` (string) ... (+54 more, total 62 fields) |
| 187 | `API_ImportAgentPolicy` | `-` | L3708–L3738 | 23 | `Id` (string), `DateOfInsurance` (string), `BrokerName` (string), `ClientName` (string), `VehicleType` (string), `VehicleNumber` (string), `PolicyNumber` (string), `Segments` (string) ... (+15 more, total 23 fields) |
| 188 | `API_ImportAgentPolicy` | `-` | L3739–L3806 | 42 | `Id` (string), `DateOfInsurance` (string), `BrokerName` (string), `ClientName` (string), `VehicleType` (string), `VehicleNumber` (string), `PolicyNumber` (string), `Segments` (string) ... (+34 more, total 42 fields) |

---

## 5. Complete Register of Inline / Raw SQL Queries (19 Queries)

| # | File | Line | Raw SQL Query |
| :--- | :--- | :--- | :--- |
| 1 | `DAL\DAL_Operations.cs` | L20223 | `SELECT UserId,UserName FROM tbl_user` |
| 2 | `Insurance\WebForm3.aspx.cs` | L199 | `SELECT DateOfInsurance, BrokerName, ClientName, VehicleType, VehicleNumber, PolicyNumber, Segments, Insuran...` |
| 3 | `Insurance\Clerk\CL_ClaimNew.aspx.cs` | L343 | `select * from tbl_claim_finalbill_doc where FBId=` |
| 4 | `Insurance\Clerk\CL_ClaimNew.aspx.cs` | L361 | `delete from  tbl_claim_finalbill_doc where FBId=` |
| 5 | `Insurance\Clerk\CL_ClaimNew.aspx.cs` | L493 | `select * from tbl_claim_quotation_img where QuotationId=` |
| 6 | `Insurance\Clerk\CL_ClaimNew.aspx.cs` | L512 | `delete from  tbl_claim_quotation_img where QuotationId=` |
| 7 | `Insurance\Clerk\CL_ClaimNew.aspx.cs` | L627 | `select ClaimsId,Audiopath from tbl_claimaudiolist where ClaimsId=` |
| 8 | `Insurance\Clerk\CL_ClaimNew.aspx.cs` | L646 | `delete from  tbl_claimaudiolist where ClaimsId=` |
| 9 | `Insurance\Clerk\CL_ClaimNew.aspx.cs` | L952 | `select InsuranceCompanyId from tbl_claimassistance where ClaimAssistanceId=` |
| 10 | `Insurance\Clerk\CL_ClaimNew.aspx.cs` | L1025 | `select ClaimAssistanceId,ImgPath from tbl_claimassistanceimg where ClaimAssistanceId=` |
| 11 | `Insurance\Clerk\CL_ClaimNew.aspx.cs` | L1044 | `delete from  tbl_claimassistanceimg where ClaimAssistanceId=` |
| 12 | `Insurance\Clerk\CL_ClaimNew.aspx.cs` | L1517 | `select * from tbl_claimimg where ClaimsId=` |
| 13 | `Insurance\Clerk\CL_ClaimNew.aspx.cs` | L1557 | `select * from tbl_claim_quotation_img where QuotationId=` |
| 14 | `Insurance\Clerk\CL_ClaimNew.aspx.cs` | L1595 | `select * from tbl_claim_finalbill_doc where FBId=` |
| 15 | `Insurance\Clerk\adm_Claims.aspx.cs` | L85 | `select * from tbl_claimimg where ClaimsId=` |
| 16 | `Insurance\Clerk\adm_Claims.aspx.cs` | L233 | `select CustomerId,InsuranceCompanyId from tbl_claims where ClaimsId=` |
| 17 | `Insurance\Clerk\adm_EndorsmentReport.aspx.cs` | L120 | `SELECT * FROM tbl_endorsementimages where EndorsementId=` |
| 18 | `Insurance\Clerk\adm_EndorsmentReport.aspx.cs` | L186 | `SELECT * FROM tbl_endorsementimages where EndorsementId=` |
| 19 | `Insurance\Clerk\adm_ImportTransAgentPolicyMIS.aspx.cs` | L195 | `SELECT DateOfInsurance, BrokerName, ClientName, VehicleType, VehicleNumber, PolicyNumber, Segments, Insuran...` |
