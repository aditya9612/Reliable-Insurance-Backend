# Phase 5C — Customer & Vehicle Legacy CRUD Contract Audit

**Target Repository**: `Reliable-Insurance-Backend`  
**Phase**: 5C — Customer & Vehicle Legacy CRUD Contract Audit  
**Execution Mode**: AUDIT ONLY — STRICT STOP CONDITION ENFORCED  
**Runtime Database**: `localhost:3306/reliable_insurance_dev` (Local development only; zero production connections)  
**Date**: October 2026  

---

## 1. Objective & Scope

The purpose of Phase 5C is to audit and establish an evidence-backed operational contract for all Customer and Vehicle CRUD, search, and validation flows based on the legacy C# codebase (`InsurancefinalNew`) and MySQL stored procedures (`brahmainsurance`) before designing FastAPI REST APIs or business service layers in Phase 5D.

This audit establishes the concrete data pipeline:
```
LEGACY STORED PROCEDURE / C# CALLER
                ↓
INPUT PARAMETERS & TYPES
                ↓
VALIDATION, DEFAULTS & CASING TRANSFORMS
                ↓
DATABASE READ / WRITE OPERATIONS
                ↓
DOMAIN RULES & REGISTRATION UNIQUENESS
                ↓
ERROR & DUPLICATE BEHAVIORS
                ↓
OUTPUT & RESPONSE CONTRACTS
```

---

## 2. Evidence Sources

The findings in this specification are directly derived from the following audited sources:
1. **Legacy C# Data Access Layer**: `InsurancefinalNew\DAL\DAL_Operations.cs` (lines 7430–8535, 16390–16410)
2. **Legacy C# Business Logic Layer**: `InsurancefinalNew\BLL\BLL_Operations.cs` (lines 1600–1720)
3. **Legacy C# Presentation Layer**:
   - `InsurancefinalNew\Insurance\Clerk\PolicyTransactionNew.aspx.cs` (lines 66–75, 860–975, 1290–1340)
   - `InsurancefinalNew\Insurance\Clerk\SearchMethods.aspx.cs` (lines 20–130, 320–335)
   - `InsurancefinalNew\Insurance\Clerk\AgentCommissionUseWallet.aspx.cs` (lines 460–485)
   - `InsurancefinalNew\Insurance\Service.asmx.cs` (lines 3855–3950)
4. **Legacy C# DTO Classes**: `InsurancefinalNew\API\AllMaster.cs` (`API_Customer` lines 436–475, `API_CustVehicle` lines 408–435)
5. **Stored Procedure Definitions**: Introspected routine definitions captured in `phase5a_routines.json` (561 routines) and Phase 5A audit report (`docs/migration/phase_5a_customer_vehicle_audit.md`)
6. **Local Verified Schema**: Local development database `reliable_insurance_dev` (`tbl_customer` 38 cols, `tbl_vehicledetails` 32 cols, 0 physical FKs, Alembic migrations `b84657b131fa` and `6502a09489d3`).

---

## 3. Customer Create Contract (`sp_InsertCustomer`)

### 3.1 Procedure Signature & Parameter Specification

- **Procedure Name**: `sp_InsertCustomer`
- **Total Parameters**: 37 (36 `IN` parameters, 1 `OUT` parameter `P_CustomerId`)
- **Physical Target Table**: `tbl_customer` (38 columns)
- **Primary Callers**:
  - `PolicyTransactionNew.aspx.cs: InsertCustomer()` via `BLL_InsertCustomer` → `DAL_InsertCustomer`
  - `NewPolicyEntry.aspx.cs`, `MotorTransactionEntry.aspx.cs`, `ManualPolicyTransaction.aspx.cs`

| Legacy Parameter | DB Column | Data Type | Required | Nullable | Default Value | Transform / Casing | Mutable on Update | Evidence in Source | Notes |
|---|---|---|---|---|---|---|---|---|---|
| `P_CustomerCode` | `CustomerCode` | `varchar(100)` | YES | YES | Generated int | Stringified next auto-increment | YES | `PolicyTransactionNew:867` | Indexed with prefix 100 UNIQUE |
| `P_initial` | `initial` | `varchar(100)` | NO | YES | `""` | Dropdown text | YES | `PolicyTransactionNew:868` | e.g. "Mr.", "Mrs.", "M/S" |
| `P_CustFName` | `CustFName` | `varchar(300)` | YES | YES | `""` | `.ToUpper()` | YES | `PolicyTransactionNew:869` | Primary first name / entity name |
| `P_CustMName` | `CustMName` | `varchar(100)` | NO | YES | `""` | `.ToUpper()` | YES | `PolicyTransactionNew:870` | Middle name |
| `P_CustLName` | `CustLName` | `varchar(100)` | NO | YES | `""` | `.ToUpper()` | YES | `PolicyTransactionNew:871` | Last name / surname |
| `P_CustomerType` | `CustomerType` | `varchar(50)` | YES | YES | `"Individual"` | Radio value | YES | `PolicyTransactionNew:874` | "Individual" or "Corporate" |
| `P_ClientId` | `ClientId` | `int(11)` | NO | YES | `1` | Integer literal | YES | `PolicyTransactionNew:875` | Defaults to 1 for retail clients |
| `P_PerAddrLine1` | `PerAddrLine1` | `varchar(600)` | NO | YES | `""` | `.ToUpper()` | YES | `PolicyTransactionNew:872` | Permanent address line 1 |
| `P_PerAddrLine2` | `PerAddrLine2` | `varchar(600)` | NO | YES | `""` | `.ToUpper()` | YES | `PolicyTransactionNew:873` | Permanent address line 2 |
| `P_PerTalukaId` | `PerTalukaId` | `int(11)` | NO | YES | `0` | Dropdown ID | YES | `PolicyTransactionNew:876` | Ptr to taluka master |
| `P_PerDistrictId`| `PerDistrictId`| `int(11)` | NO | YES | `0` | Dropdown ID | YES | `PolicyTransactionNew:877` | Ptr to district master |
| `P_PerStateId` | `PerStateId` | `int(11)` | NO | YES | `0` | Dropdown ID | YES | `PolicyTransactionNew:878` | Ptr to state master |
| `P_PerPinCode` | `PerPinCode` | `varchar(100)` | NO | YES | `""` | As-is digits | YES | `PolicyTransactionNew:879` | PIN / Postal code |
| `P_ComAddrLine1` | `ComAddrLine1` | `varchar(600)` | NO | YES | `""` | `.ToUpper()` | YES | `PolicyTransactionNew:880` | Mirrored from permanent in UI |
| `P_ComAddrLine2` | `ComAddrLine2` | `varchar(600)` | NO | YES | `""` | `.ToUpper()` | YES | `PolicyTransactionNew:881` | Mirrored from permanent in UI |
| `P_ComTalukaId` | `ComTalukaId` | `int(11)` | NO | YES | `0` | Dropdown ID | YES | `PolicyTransactionNew:882` | Mirrored from permanent |
| `P_ComDistrictId`| `ComDistrictId`| `int(11)` | NO | YES | `0` | Dropdown ID | YES | `PolicyTransactionNew:883` | Mirrored from permanent |
| `P_ComStateId` | `ComStateId` | `int(11)` | NO | YES | `0` | Dropdown ID | YES | `PolicyTransactionNew:884` | Mirrored from permanent |
| `P_ComPinCode` | `ComPinCode` | `varchar(100)` | NO | YES | `""` | As-is digits | YES | `PolicyTransactionNew:885` | Mirrored from permanent |
| `P_MoblieNo1` | `MoblieNo1` | `varchar(100)` | YES | YES | `""` | As-is digits | YES | `PolicyTransactionNew:886` | Primary contact mobile |
| `P_MoblieNo2` | `MoblieNo2` | `varchar(100)` | NO | YES | `""` | As-is digits | YES | `PolicyTransactionNew:887` | Alternate contact mobile |
| `P_Gender` | `Gender` | `varchar(100)` | NO | YES | `"Male"` | Dropdown val | YES | `PolicyTransactionNew:888` | "Male", "Female", "Other" |
| `P_MaritalStatus`| `MaritalStatus`| `varchar(100)`| NO | YES | `NULL` | Empty `""` → `NULL` | YES | `DAL_Operations:8406` | Explicit ternary transform |
| `P_PAN_No` | `PAN_No` | `varchar(100)` | NO | YES | `""` | As-is string | YES | `PolicyTransactionNew:896` | Income tax PAN (not uppercased) |
| `P_AadharNo` | `AadharNo` | `varchar(100)` | NO | YES | `""` | `.ToUpper()` | YES | `PolicyTransactionNew:899` | 12-digit Aadhaar |
| `P_DateOfBirth` | `DateOfBirth` | `date` | NO | YES | `NULL` | `DateTime` parse | YES | `PolicyTransactionNew:902` | `txt_DateOfBirth != ""` |
| `P_EmailId` | `EMailId` | `varchar(100)` | NO | YES | `""` | `.ToUpper()` | YES | `PolicyTransactionNew:904` | Uppercased email string |
| `P_NomineeName` | `NomineeName` | `varchar(100)` | NO | YES | `""` | `.ToUpper()` | YES | `PolicyTransactionNew:905` | Nominee name |
| `P_BranchId` | `BranchId` | `int(11)` | YES | YES | Session val | Int parse | YES | `PolicyTransactionNew:906` | From `Session["BranchId"]` |
| `P_CreateDate` | `CreateDate` | `datetime` | YES | YES | Server Now | `DateTime.Now` | **NO** | `PolicyTransactionNew:908` | Immutable audit column |
| `P_CreateUser` | `CreateUser` | `varchar(100)` | YES | YES | Session user| String | **NO** | `PolicyTransactionNew:907` | From `Session["UserName"]` |
| `P_UpdateDate` | `UpdateDate` | `datetime` | YES | YES | Server Now | `DateTime.Now` | YES | `PolicyTransactionNew:910` | Set on insert & update |
| `P_UpdateUser` | `UpdateUser` | `varchar(100)` | YES | YES | Session user| String | YES | `PolicyTransactionNew:909` | Set on insert & update |
| `P_Extra1` | `Extra1` | `varchar(100)` | NO | YES | `""` | Anniversary date | YES | `PolicyTransactionNew:915` | If Married, stores anniversary |
| `P_Extra2` | `Extra2` | `varchar(100)` | NO | YES | `""` | Empty string | YES | `PolicyTransactionNew:921` | Reserved metadata |
| `P_CompanyName` | `CompanyName` | `varchar(100)` | NO | YES | `""` | Textbox val | **NO** | `PolicyTransactionNew:922` | Omitted from `sp_UpdateCustomer` |
| `OUT P_CustomerId`| `CustomerId` | `int(11)` | — | NO | Generated PK| `last_insert_id()`| — | `DAL_Operations:8427` | Returned as scalar int |
| *(Internal SP)* | `isdeleted` | `varchar(255)`| — | YES | `'0'` | Hardcoded `'0'` | — | `sp_InsertCustomer` SQL | Set to `'0'` by SP insert |

### 3.2 Key Behavioral Discoveries

1. **Case Normalization**:
   - The legacy application aggressively converts strings to **UPPERCASE** in UI code-behind: `CustFName`, `CustMName`, `CustLName`, `PerAddrLine1`, `PerAddrLine2`, `ComAddrLine1`, `ComAddrLine2`, `AadharNo`, `EmailId`, `NomineeName`.
   - `PAN_No` is surprisingly **NOT** uppercased in `PolicyTransactionNew.aspx.cs` (lines 890–897).
2. **Marital Status & Extra1 Pairing**:
   - `MaritalStatus`: C# DAL converts empty string `""` to `null` before sending to MySQL (`cust.MaritalStatus != "" ? cust.MaritalStatus : null`).
   - `Extra1`: In `PolicyTransactionNew.aspx.cs:912`, if `ddlMaritalStatus.SelectedIndex == 2` (Married), `Extra1` stores the customer's **wedding anniversary date** (`txtanniversary.Value`).
3. **Address Duplication**:
   - In standard retail intake, communication address fields (`ComAddr*`) are completely duplicated from permanent address fields (`PerAddr*`) in code-behind.
4. **Duplicate Mobile Allowance**:
   - Neither `sp_InsertCustomer` nor C# code-behind performs any duplicate check on `MoblieNo1` or `PAN_No`. Multiple customers with identical mobile numbers are accepted without error.
5. **Soft-Delete State**:
   - Every inserted customer is marked with `isdeleted = '0'`.

---

## 4. Customer Code Generation Contract (`sp_generateCustomerCode`)

### 4.1 Legacy Mechanism & Structural Defect

```sql
CREATE DEFINER=`root`@`localhost` PROCEDURE `sp_generateCustomerCode`(OUT `P_CustomerCode` INT)
BEGIN
SET P_CustomerCode = (SELECT AUTO_INCREMENT FROM information_schema.TABLES
                      WHERE TABLE_SCHEMA = "brahmainsurance" AND TABLE_NAME = "tbl_customer");
END
```

### 4.2 Call Sequence & Race Condition Flow

```
1. User A loads form → generateCustomerCode() → reads AUTO_INCREMENT (e.g., 224265)
2. User B loads form → generateCustomerCode() → reads AUTO_INCREMENT (224265)
3. User A submits → sp_InsertCustomer(CustomerCode='224265') → SUCCESS (AUTO_INCREMENT becomes 224266)
4. User B submits → sp_InsertCustomer(CustomerCode='224265') → FAILS: Duplicate entry '224265' for key 'CustomerCode_UNIQUE'
```

- **Evidence of Legacy Awareness**:
  Inside `sp_InsertCustomer`, the legacy developers had commented out an attempted database-level fix:
  ```sql
  /*
  Declare IsCustCodePresent varchar(100);
  set IsCustCodePresent=(SELECT CustomerCode FROM tbl_customer WHERE CustomerCode = P_CustomerCode);
  if(IsCustCodePresent<>"") then
    P_CustomerCode=CustomerCode+1;
  end if;
  */
  ```
- **Modernization Contract for Phase 5D**:
  - The API MUST NOT rely on client-supplied `CustomerCode` read beforehand from `information_schema`.
  - In Phase 5D, `CustomerCode` must either be generated within an atomic database transaction or formatted reliably after flush (`CUST-{CustomerId}`).

---

## 5. Customer Update Contract (`sp_UpdateCustomer`)

### 5.1 Procedure Signature & Parameter Specification

- **Procedure Name**: `sp_UpdateCustomer`
- **Total Parameters**: 34 `IN` parameters (0 `OUT` parameters; returns boolean success via rows affected)
- **Primary Caller**: `DAL_Operations.cs: DAL_UpdateCustomer(API_Customer cust)` (line 8454)

| Legacy Parameter | Target DB Column | Updatable | Handling of NULL / Empty | Notes |
|---|---|---|---|---|
| `P_CustomerId` | `CustomerId` | — (Key) | Identifies record to update | `WHERE CustomerId = P_CustomerId` |
| `P_CustomerCode`| `CustomerCode` | YES | Updates column | Protected by `CustomerCode_UNIQUE` index |
| `P_initial` | `initial` | YES | Updates column | Salutation |
| `P_CustFName` | `CustFName` | YES | Updates column | First name |
| `P_CustMName` | `CustMName` | YES | Updates column | Middle name |
| `P_CustLName` | `CustLName` | YES | Updates column | Last name |
| `P_CustomerType`| `CustomerType` | YES | Updates column | "Individual" / "Corporate" |
| `P_ClientId` | `ClientId` | YES | Updates column | Corporate client linkage |
| `P_PerAddrLine1`| `PerAddrLine1` | YES | Updates column | Address line 1 |
| `P_PerAddrLine2`| `PerAddrLine2` | YES | Updates column | Address line 2 |
| `P_PerTalukaId` | `PerTalukaId` | YES | Updates column | Taluka ID |
| `P_PerDistrictId`| `PerDistrictId`| YES | Updates column | District ID |
| `P_PerStateId` | `PerStateId` | YES | Updates column | State ID |
| `P_PerPinCode` | `PerPinCode` | YES | Updates column | PIN code |
| `P_ComAddrLine1`| `ComAddrLine1` | YES | Updates column | Communication address line 1 |
| `P_ComAddrLine2`| `ComAddrLine2` | YES | Updates column | Communication address line 2 |
| `P_ComTalukaId` | `ComTalukaId` | YES | Updates column | Communication taluka ID |
| `P_ComDistrictId`| `ComDistrictId`| YES | Updates column | Communication district ID |
| `P_ComStateId` | `ComStateId` | YES | Updates column | Communication state ID |
| `P_ComPinCode` | `ComPinCode` | YES | Updates column | Communication PIN code |
| `P_MoblieNo1` | `MoblieNo1` | YES | Updates column | Primary mobile |
| `P_MoblieNo2` | `MoblieNo2` | YES | Updates column | Secondary mobile |
| `P_Gender` | `Gender` | YES | Updates column | Gender |
| `P_MaritalStatus`| `MaritalStatus`| YES | Empty `""` → `NULL` | Same ternary transform as insert |
| `P_PAN_No` | `PAN_No` | YES | Updates column | PAN number |
| `P_AadharNo` | `AadharNo` | YES | Updates column | Aadhaar number |
| `P_DateOfBirth` | `DateOfBirth` | YES | Updates column | DOB date |
| `P_EmailId` | `EMailId` | YES | Updates column | Email |
| `P_NomineeName` | `NomineeName` | YES | Updates column | Nominee name |
| `P_BranchId` | `BranchId` | YES | Updates column | Can reassign branch |
| `P_UpdateDate` | `UpdateDate` | YES | `DateTime.Now` | Audit timestamp |
| `P_UpdateUser` | `UpdateUser` | YES | Current user | Audit user |
| `P_Extra1` | `Extra1` | YES | Anniversary / metadata | Metadata 1 |
| `P_Extra2` | `Extra2` | YES | Metadata | Metadata 2 |
| *(Excluded)* | `CreateDate` | **IMMUTABLE** | Not present in parameter list | Preserved |
| *(Excluded)* | `CreateUser` | **IMMUTABLE** | Not present in parameter list | Preserved |
| *(Excluded)* | `CompanyName` | **IMMUTABLE** | **Omitted from `sp_UpdateCustomer`** | **Cannot be updated via this SP** |
| *(Excluded)* | `isdeleted` | **UNMODIFIED**| Not updated | State preserved |

### 5.2 Endorsement Customer Update (`sp_UpdateCustomerDataForEndorsment`)

In mid-term endorsement / vehicle ownership transfers (`OwnerTransferEndorsement.aspx.cs`), a separate dedicated routine is used:
```sql
CREATE PROCEDURE sp_UpdateCustomerDataForEndorsment(
  IN P_CustomerId INT,
  IN P_CustomerName VARCHAR(500),
  IN P_MobileNo VARCHAR(50),
  IN P_opr VARCHAR(50),
  IN P_UpdateUser VARCHAR(100)
)
BEGIN
  UPDATE tbl_Customer SET
    CustFName = P_CustomerName,
    CustMName = "TRANSFER",
    MoblieNo1 = P_MobileNo,
    UpdateDate = CURRENT_TIMESTAMP,
    UpdateUser = P_UpdateUser
  WHERE CustomerId = P_CustomerId;
END
```
- **Domain Behavior**: Overwrites `CustFName` with the new owner's full name, sets `CustMName` to literal `"TRANSFER"`, updates `MoblieNo1`, and records audit metadata.

---

## 6. Customer Search Contract

### 6.1 Audit Comparison of Search Routines

| Operation | Calling API / Page | Input Parameters | Search Expression | Branch Rule | Deleted Filter | Ordering | Result Fields |
|---|---|---|---|---|---|---|---|
| `sp_SearchCustName` | `SearchMethods.aspx: GetCustName` | `P_SerachText` varchar(20), `P_BranchId` int | `Concat(CustFName,' ',CustMName,' ',CustLName) LIKE '%search%'` | Scoped: `BranchId = P_BranchId` | `isdeleted = 0` | `CustFName ASC` | `CustomerId`, `CustName` |
| `sp_SearchCustNameapp` | `Service.asmx: SearchCustNameapp` | `P_SerachText` varchar(20) | `Concat(CustFName,' ',CustMName,' ',CustLName) LIKE '%search%'` | **Unscoped**: all branches | `isdeleted = 0` | `CustFName ASC` | `CustomerId`, `CustName` |
| `sp_appSerachCustNameDetails` | `Service.asmx: appSerachCustNameDetails`| `P_CustName` varchar(100) | `Concat(CustFName,' ',CustMName,' ',CustLName) = P_CustName` | **Unscoped**: all branches | `T.isdeleted = 0` | None | `TransanctionId`, `CustName`, `RegistrationNo`, `filePath` |
| `sp_SelectCustomerName` | `PolicyTransactionNew.aspx` | `P_CustomerId` int, `P_BranchId` int | `CustomerId = P_CustomerId` | Passed but ignored in SP query | None | None | 38 customer columns + vehicle catalog joins |

### 6.2 Key Behavioral Rules
1. **Branch Scoping**:
   - Internal WebForms users are strictly scoped to their assigned `BranchId` via `sp_SearchCustName`.
   - Field POSP and mobile application agents execute cross-branch searches via `sp_SearchCustNameapp` (allowing renewals across corporate branches).
2. **Name Concatenation**:
   - Full name search matches against space-concatenated `CustFName`, `CustMName`, and `CustLName`.
3. **Pagination & Limits**:
   - Legacy stored procedures implement **zero LIMIT or OFFSET pagination clauses**. All matching records are returned to the caller.

---

## 7. Vehicle Create Contract (`Sp_VehicleDetails` / `Sp_VehicleDetails_2026`)

### 7.1 Parameter Specification & Column Mapping

- **Procedure Name**: `Sp_VehicleDetails_2026` (modernized with `FinancialYear` and `VehicleVariant`)
- **Total Parameters**: 31 (30 `IN` parameters, 1 `OUT` parameter `P_CustVehId`)
- **Target Table**: `tbl_vehicledetails` (32 columns)
- **Primary Callers**:
  - `PolicyTransactionNew.aspx.cs: InsertCustVehicle(int CustID)` via `BLL_InsertVehicleDetails_2026`
  - `PE_TransactionEntry_2026.aspx.cs`

| Legacy Parameter | DB Column | Data Type | Classification | Default / Value in Source | Transform / Casing | Notes |
|---|---|---|---|---|---|---|
| `P_CustomerId` | `CustomerId` | `int(11)` | REQUIRED | Linked from customer create | As-is int | Logical reference to `tbl_customer.CustomerId` |
| `P_RegistrationNo` | `RegistrationNo` | `varchar(50)` | REQUIRED | Textbox input | `.ToUpper()` | e.g. "MH12AB1234" |
| `P_ChaiseNo` | `ChaiseNo` | `varchar(50)` | REQUIRED | Textbox input | `.ToUpper()` | Physical typo column preserved |
| `P_EngineNo` | `EngineNo` | `varchar(500)`| REQUIRED | Textbox input | `.ToUpper()` | Engine serial number |
| `P_MfgMonth` | `MfgMonth` | `varchar(50)` | OPTIONAL | Dropdown month | Value as-is | e.g. "January" or "01" |
| `P_MfgYear` | `MfgYear` | `varchar(50)` | REQUIRED | Textbox year | `.ToUpper()` | e.g. "2022" |
| `P_Ex_ShowroomPrice`| `Ex_ShowroomPrice`| `varchar(50)`| DEFAULTED | Hardcoded `""` in DAL | As-is string | Stored as empty string in retail UI |
| `P_FuelTypeId` | `FuelTypeId` | `int(11)` | REQUIRED | Dropdown ID | Int parse | Ptr to `tbl_fueltype` |
| `P_Veh_Type_ID` | `Veh_Type_ID` | `int(11)` | REQUIRED | Dropdown ID | Int parse | Ptr to `tbl_vehicle_type` |
| `P_Veh_Sub_Type_ID`| `Veh_Sub_Type_ID`| `int(11)` | REQUIRED | Dropdown ID | Int parse | Ptr to `tbl_vehicle_sub_type` |
| `P_Make_ID` | `Make_ID` | `int(11)` | REQUIRED | Dropdown ID | Int parse | Ptr to `tbl_vehicle_make` |
| `P_Model_ID` | `Model_ID` | `int(11)` | REQUIRED | Dropdown ID | Int parse | Ptr to `tbl_vehicle_model` |
| `P_Variant_ID` | `Variant_ID` | `int(11)` | REQUIRED | Dropdown ID | Int parse | Ptr to `tbl_vehicle_variants` |
| `P_VehiclePurDate` | `VehiclePurDate` | `datetime` | REQUIRED | Proposal Date | `Convert.ToDateTime` | Date of purchase |
| `P_SeatsCapacity` | `SeatsCapacity` | `varchar(50)` | OPTIONAL | Textbox seats | `.ToUpper()` | e.g. "5" |
| `P_EnginePower` | `EnginePower` | `varchar(500)`| OPTIONAL | Textbox CC/power | `.ToUpper()` | e.g. "1197" |
| `P_TransTonnageCapacity`| `TransTonnageCapacity`| `varchar(50)`| DEFAULTED | Hardcoded `""` in DAL | Empty string | Commercial tonnage |
| `P_VehicleWeight` | `VehicleWeight` | `varchar(50)` | OPTIONAL | Textbox weight | `.ToUpper()` | Gross vehicle weight |
| `P_VehicleRegDate` | `VehicleRegDate` | `datetime` | DEFAULTED | Current server timestamp | `DateTime.Now` | Set at time of booking |
| `P_RTOId` | `RTOId` | `int(11)` | REQUIRED | Hardcoded `1` in form | Int literal | Defaulted to 1 in standard form |
| `P_BranchId` | `BranchId` | `int(11)` | REQUIRED | `Session["BranchId"]` | Int parse | User branch |
| `P_CorporateClientId`| `CorporateClientId`| `int(11)` | DEFAULTED | Hardcoded `1` in form | Int literal | Defaulted to 1 |
| `P_CreateDate` | `CreateDate` | `datetime` | DEFAULTED | `DateTime.Now` | Timestamp | Audit column |
| `P_CreatedUser` | `CreatedUser` | `varchar(50)` | REQUIRED | `Session["UserName"]` | String | Audit column |
| `P_UpdatedDate` | `UpdatedDate` | `datetime` | DEFAULTED | `DateTime.Now` | Timestamp | Audit column |
| `P_UpdatedUser` | `UpdatedUser` | `varchar(50)` | REQUIRED | `Session["UserName"]` | String | Audit column |
| `P_Extra1` | `Extra1` | `varchar(50)` | DEFAULTED | `""` | Empty string | Metadata 1 |
| `P_Extra2` | `Extra2` | `varchar(50)` | DEFAULTED | `""` | Empty string | Metadata 2 |
| `P_FinancialYear` | `FinancialYear` | `varchar(50)` | **REQUIRED** | Current Fiscal Period | e.g. "2024-2025"| **Physical NOT NULL in DB** |
| `P_VehicleVariant` | `VehicleVariant` | `varchar(300)`| OPTIONAL | Catalog text | Text descriptor | String variant name |
| `OUT P_CustVehId` | `CustVehId` | `int(11)` | GENERATED | `last_insert_id()` | Scalar int | Primary Key |
| *(Internal SP)* | `isdeleted` | `varchar(255)`| DEFAULTED | Hardcoded `'0'` | String `'0'` | Soft-delete flag |

---

## 8. Vehicle Update Contract (`Sp_UpdateVehicleDetails`)

### 8.1 Parameter Specification & Mutability

- **Procedure Name**: `Sp_UpdateVehicleDetails`
- **Total Parameters**: 24 `IN` parameters (0 `OUT` parameters; returns boolean success)
- **Primary Caller**: `DAL_Operations.cs: DAL_UpdateVehicleDetails(API_CustVehicle CustVehicle)` (line 7927)

```sql
UPDATE tbl_VehicleDetails SET
  RegistrationNo = P_RegistrationNo,
  ChaiseNo = P_ChaiseNo,
  EngineNo = P_EngineNo,
  MfgMonth = P_MfgMonth,
  MfgYear = P_MfgYear,
  Ex_ShowroomPrice = P_Ex_ShowroomPrice,
  FuelTypeId = P_FuelTypeId,
  Veh_Type_ID = P_Veh_Type_ID,
  Veh_Sub_Type_ID = P_Veh_Sub_Type_ID,
  Make_ID = P_Make_ID,
  Model_ID = P_Model_ID,
  Variant_ID = P_Variant_ID,
  VehiclePurDate = P_VehiclePurDate,
  SeatsCapacity = P_SeatsCapacity,
  EnginePower = P_EnginePower,
  TransTonnageCapacity = P_TransTonnageCapacity,
  VehicleWeight = P_VehicleWeight,
  VehicleRegDate = P_VehicleRegDate,
  RTOId = P_RTOId,
  UpdatedDate = current_date(),
  UpdatedUser = P_UpdatedUser,
  Extra1 = P_Extra1,
  Extra2 = P_Extra2
WHERE CustVehId = P_CustVehId;
```

### 8.2 Mutability Analysis

1. **Mutable Fields**:
   - Technical specifications (`RegistrationNo`, `ChaiseNo`, `EngineNo`, `MfgMonth`, `MfgYear`, `Ex_ShowroomPrice`, `SeatsCapacity`, `EnginePower`, `TransTonnageCapacity`, `VehicleWeight`, `VehiclePurDate`, `VehicleRegDate`).
   - Catalog pointers (`FuelTypeId`, `Veh_Type_ID`, `Veh_Sub_Type_ID`, `Make_ID`, `Model_ID`, `Variant_ID`, `RTOId`).
   - Audit & metadata (`UpdatedUser`, `Extra1`, `Extra2`).
2. **Immutable Fields**:
   - `CustomerId`: Owner client is **IMMUTABLE** (ownership changes are processed via `sp_UpdateCustomerDataForEndorsment` or proposal transfer).
   - `FinancialYear`: Fiscal period of record is **IMMUTABLE** in this update procedure.
   - `BranchId` & `CorporateClientId`: Branch assignment is **IMMUTABLE** in this procedure.
   - `VehicleVariant`: Text descriptor is **IMMUTABLE** in this procedure.
   - `CreateDate` & `CreatedUser`: Original intake audit fields are preserved.
3. **Database Date Override**:
   - `UpdatedDate` is overridden directly in SQL using `current_date()`, ignoring any client-provided timestamp.

---

## 9. Registration Number Validation Contract (`sp_CheckRegistrationNoNew` & `sp_CheckRegistrationNo`)

### 9.1 Exact Stored Procedure Logic

#### A. Policy-Linked Validation (`sp_CheckRegistrationNoNew`)
```sql
CREATE PROCEDURE sp_CheckRegistrationNoNew(
  IN P_RegistrationNo VARCHAR(100),
  IN P_FinancialYear VARCHAR(100),
  OUT P_ReturnMsg INT
)
BEGIN
  SET @usercount = (
    SELECT COUNT(V.RegistrationNo)
    FROM tbl_transaction T
    INNER JOIN tbl_vehicledetails V ON T.CustVehId = V.CustVehId
    WHERE V.RegistrationNo = P_RegistrationNo
      AND T.FinancialYear = P_FinancialYear
      AND V.isdeleted = 0
  );

  IF (@usercount = 0) THEN
    SET P_ReturnMsg = 0; -- Available / Valid to book
  ELSE
    SET P_ReturnMsg = 1; -- Duplicate / Active policy already exists in this FY
  END IF;
END
```

#### B. Asset Registry Validation (`sp_CheckRegistrationNo`)
```sql
CREATE PROCEDURE sp_CheckRegistrationNo(
  IN P_RegistrationNo VARCHAR(100),
  IN P_FinancialYear VARCHAR(100),
  OUT P_ReturnMsg INT
)
BEGIN
  SET @usercount = (
    SELECT COUNT(RegistrationNo)
    FROM tbl_Vehicledetails
    WHERE RegistrationNo = P_RegistrationNo
      AND FinancialYear = P_FinancialYear
      AND isdeleted = 0
  );

  IF (@usercount = 0) THEN
    SET P_ReturnMsg = 0; -- Available
  ELSE
    SET P_ReturnMsg = 1; -- Duplicate vehicle asset in this FY
  END IF;
END
```

### 9.2 Registration Validation Contract Matrix

| Validation Context | Procedure Used | Target Condition | Return Value = 0 | Return Value = 1 | Business Outcome |
|---|---|---|---|---|---|
| **Retail Proposal Booking** | `sp_CheckRegistrationNo` | `tbl_vehicledetails` matching `RegistrationNo` + `FinancialYear` + `isdeleted=0` | Available | Exists | Blocks duplicate registration entry in current financial year |
| **Transaction Audit / Payout** | `sp_CheckRegistrationNoNew` | `tbl_transaction` joined to `tbl_vehicledetails` matching `FinancialYear` | No policy found | Active policy found | Verifies active policy in FY before releasing agent wallet commission |
| **Annual Renewal Workflow** | Both | Same `RegistrationNo`, different `FinancialYear` (e.g. FY 24-25 vs FY 25-26) | Available | N/A | **Permits annual policy renewals** across subsequent financial years |

> [!IMPORTANT]
> `RegistrationNo` is **NOT globally unique**. It is scoped strictly per `FinancialYear`.  
> Models and migrations **MUST NEVER** apply a global `UNIQUE (RegistrationNo)` constraint.

---

## 10. Vehicle Search Contract

### 10.1 Stored Procedure Behavior

| Procedure | Calling API | Input Parameters | Search Criteria | Branch Filter | Deleted Filter | Results / Shape |
|---|---|---|---|---|---|---|
| `sp_SearchByVehicleNo` | `SearchMethods.aspx: GetCustVehicleNo` | `P_SerachText` varchar(50), `P_BranchId` int | `RegistrationNo LIKE '%search%'` | Scoped: `BranchId = (CASE WHEN P_BranchId=0 THEN BranchId ELSE P_BranchId END)` | None | `CustVehId`, `RegistrationNo` (hardcoded to `'2021-2022'`) |
| `sp_SearchVehicleNoapp` | `Service.asmx: SearchVehicleNoapp` | `P_SerachText` varchar(20) | `C.RegistrationNo LIKE '%search%'` (inner joins `tbl_transaction`) | **Unscoped**: all branches | None | `CustVehId`, `RegistrationNo` |
| `sp_SelectByVehicleSearchNew` | `DAL_SelectByVehicleSearchnew` | `P_CustVehId` int, `P_BranchId` int | Exact match: `CV.CustVehId = P_CustVehId` | None | None | Hydrated join: Vehicle details (18 cols) + Customer details (20 cols) + Corporate client |
| `sp_SelectByVehiclenew` | `BLL_GetAppVehicleDetails` | `P_RegistrationNo` varchar(50) | Exact match on `RegistrationNo` | None | None | Full vehicle technical specifications |

---

## 11. Vehicle Delete Contract (`sp_DeleteCustvehicleDetailsbyCustvehId` & `sp_AlreadyExistVehicleNo`)

### 11.1 Physical Deletion Evidence

#### A. Draft Vehicle Deletion (`sp_DeleteCustvehicleDetailsbyCustvehId`)
```sql
CREATE PROCEDURE sp_DeleteCustvehicleDetailsbyCustvehId(IN P_CustVehId INT)
BEGIN
  DELETE FROM tbl_vehicledetails WHERE CustVehId = P_CustVehId;
END
```
- **Execution**: **PHYSICAL DELETE** (`DELETE FROM tbl_vehicledetails`).
- **Authorization Checks**: Zero branch or user ownership checks.
- **Foreign Key Impact**: Works seamlessly because MySQL has **0 physical foreign keys**.

#### B. Duplicate Cleanup Deletion (`sp_AlreadyExistVehicleNo`)
```sql
CREATE PROCEDURE sp_AlreadyExistVehicleNo(P_RegNo VARCHAR(50), P_opr VARCHAR(50), P_CustVehId INT)
BEGIN
  DECLARE V_CustVehId INT;
  DECLARE V_CountOfTrans INT;

  IF (P_opr = "SEL") THEN
    SET V_CustVehId = (SELECT CustVehId FROM tbl_vehicleDetails
                       WHERE RegistrationNo LIKE CONCAT("%", P_RegNo, "%")
                         AND YEAR(CreateDate) = YEAR(CURRENT_DATE));
    IF (V_CustVehId > 0) THEN
      SET V_CountOfTrans = (SELECT COUNT(CustVehId) FROM tbl_transaction WHERE CustVehId = V_CustVehId);
      IF (V_CountOfTrans = 0) THEN
        SELECT * FROM tbl_vehicleDetails WHERE RegistrationNo LIKE CONCAT("%", P_RegNo, "%")
          AND YEAR(CreateDate) = YEAR(CURRENT_DATE);
      END IF;
    END IF;
  END IF;

  IF (P_opr = "DEL") THEN
    DELETE FROM tbl_vehicleDetails WHERE CustVehId = P_CustVehId;
  END IF;
END
```
- **Domain Purpose**: Detects unbooked orphan vehicle records created during the current calendar year with 0 transactions in `tbl_transaction`. If unbooked, permits physical deletion (`P_opr = "DEL"`).

---

## 12. Branch / Ownership Security Contract

### 12.1 Caller Types & Security Rules

| Caller Type | Authentication Source | Branch Authorization Rule | User Ownership Rule | Client Ownership Rule | Evidence |
|---|---|---|---|---|---|
| **HQ Admin / SuperAdmin** | ASP.NET Session (`UserRoleId = 1`) | Unrestricted: passes `BranchId = 0` to search procedures, viewing all branch data | Can view/edit records created by all users | Can assign any `ClientId` | `SearchMethods:59`, `sp_SearchCustName:320` |
| **Branch Operator / Clerk** | ASP.NET Session (`BranchId = N`) | Strictly scoped: search restricted to `BranchId = Session["BranchId"]` | `CreateUser` captured from session; cannot see other branches | Scoped to assigned corporate clients | `PolicyTransactionNew:906`, `SearchMethods:95` |
| **Field POSP / Broker (Mobile)**| ASMX / HTTP POST (Credentials / Token) | **Cross-branch search permitted**: mobile procedures (`sp_SearchCustNameapp`, `sp_SearchVehicleNoapp`) omit `BranchId` filter | Tied to POSP / Agent ID (`AgentId`) | Scoped to POSP clients | `Service.asmx:3864`, `Service.asmx:3924` |

### 12.2 Security Modernization Requirements for Phase 5D
1. **Never trust client-provided BranchId**:
   - In legacy WebForms, `BranchId` was taken from `Session["BranchId"]`, but in ASMX APIs, it was often passed as a request parameter.
   - In Phase 5D FastAPI, `branch_id` MUST be extracted from validated JWT claims (`current_user.branch_id`), NOT accepted as a client request payload for authorization scoping.
2. **Never trust client-provided UserId**:
   - `CreateUser` and `UpdateUser` MUST be derived from authenticated JWT identity (`current_user.username`).

---

## 13. Error & Duplicate Contract

| Condition | Legacy DB Layer Reaction | Legacy App Layer Reaction | Domain Rule for Phase 5D |
|---|---|---|---|
| **Duplicate `CustomerCode`** | MySQL Error 1062 (Unique index violation on `CustomerCode_UNIQUE`) | `MySqlException` thrown; unhandled or displayed as DB error | Prevent race conditions via atomic sequence generation |
| **Duplicate `MoblieNo1`** | **Allowed** (No unique index) | Persists successfully; returned as collection | **Allow duplicate mobile**; return collection in search |
| **Duplicate `RegistrationNo` (Same FY)** | Blocked by procedure (`sp_CheckRegistrationNo` returns `1`) | Form displays `"Vehicle No already exists"` | Validate against `(RegistrationNo, FinancialYear, isdeleted=0)` |
| **Duplicate `RegistrationNo` (Diff FY)**| **Allowed** (`sp_CheckRegistrationNo` returns `0`) | Persists successfully | **Permit renewals** across financial years |
| **Duplicate `ChaiseNo`** | **Allowed** (No unique index) | Persists successfully | **Allow duplicates** (fallback values like '0', 'NA' common) |
| **Invalid `CustomerId` on Vehicle Create** | **Allowed** (0 physical FKs) | Saves orphan vehicle | Validate `customer_id` exists before vehicle insert |
| **Invalid Master IDs** (`Make_ID`, etc.) | **Allowed** (0 physical FKs) | Saves orphan master pointers | Validate master IDs exist in repository before flush |
| **Deleted Record Update** | **Allowed** (No `isdeleted` check in update SPs) | Updates record regardless of delete flag | Exclude soft-deleted records from update queries |

---

## 14. Transaction & Atomicity Contract

### 14.1 Legacy Non-Atomic Transaction Chain

In `PolicyTransactionNew.aspx.cs` (lines 1296–1317), retail booking executes as discrete separate operations without a wrapping database transaction:

```csharp
int custId = InsertCustomer();               // DB Connection 1: Inserts into tbl_customer & commits
int vehId = InsertCustVehicle(custId);       // DB Connection 2: Inserts into tbl_vehicledetails & commits
int transId = InsertTransaction(custId, vehId); // DB Connection 3: Inserts into tbl_transaction & commits
InsertAccount();                             // DB Connection 4: Inserts into tbl_account & commits
InsertTransactionPayment(transId);          // DB Connection 5: Inserts payment record & commits
```

- **Vulnerability**: If `InsertTransaction` or payment fails, `Customer` and `Vehicle` records remain orphaned in the database.
- **Phase 5D Requirement**: All multi-step intake operations in FastAPI MUST execute within a single atomic SQLAlchemy `AsyncSession` transaction (`session.commit()` with automatic rollback on error).

---

## 15. Unknown & Requires-Verification Items

| # | Item | Current Knowledge | Missing Evidence | Risk | Required Verification Method |
|---|---|---|---|---|---|
| 1 | **Communication vs Permanent Address UI Logic** | C# code-behind duplicates permanent address into communication address | Unknown if any legacy UI allows distinct communication address entry | Low | Inspect other intake pages (`Old_CustomerDetails.aspx`, `NonMotorCustomerDetails.aspx`) |
| 2 | **Hardcoded FY in `sp_SearchByVehicleNo`** | Procedure has literal `FinancialYear = '2021-2022'` in SQL | Unknown whether legacy updated this annually or abandoned procedure | Medium | Verify if newer callers use `sp_SelectByVehicleSearchNew` instead |
| 3 | **PAN Format Validation** | C# code-behind does not uppercase or regex-validate `PAN_No` | Unknown if client JavaScript performs regex validation | Low | Check client `.aspx` JavaScript validators |
| 4 | **Corporate Client Assignment** | `ClientId` and `CorporateClientId` default to `1` in standard forms | Unknown exact lookup procedure for corporate fleet accounts | Medium | Inspect fleet transaction pages (`PE_TransactionEntry.aspx`) |

---

## 16. Phase 5D Implementation Preconditions

Before implementing Phase 5D (Services, Pydantic Schemas, and REST Endpoints):
1. **Schema Stability**: Model and index parity achieved in Phase 5B (`CustomerCode_UNIQUE`, `Fk5_ClientId_idx`, `Fk18_BranchId_idx`) remains the approved baseline.
2. **DTO to Pydantic Mapping**: Pydantic schemas must reflect the validated fields:
   - `CustomerCreate` / `CustomerUpdate` (with uppercase normalization).
   - `VehicleCreate` / `VehicleUpdate` (with `FinancialYear` required and `ChaiseNo` preserved).
3. **Sequence Generation Strategy**: Design concurrency-safe code generation to replace `sp_generateCustomerCode`.
4. **Service-Layer Branch Scoping**: Integrate FastAPI JWT dependency `require_roles` / `current_user` to supply authenticated `branch_id` and `username`.
5. **Atomic Intake Unit of Work**: Wrap customer + vehicle registration in a single transactional session.

---

## 17. Strict Stop Condition Enforced

Phase 5C audit is **COMPLETE**.  
**Execution is STOPPED before implementation.** No REST APIs, Pydantic schemas, or CRUD service endpoints have been created.
