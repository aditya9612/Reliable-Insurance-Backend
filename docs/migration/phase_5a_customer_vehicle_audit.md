# Phase 5A — Customer & Vehicle Legacy Schema + Behavior Verification Report
## Reliable Assurance Backend Migration (C# .NET 4.0 → FastAPI)

**Audit Document Version:** 1.0  
**Phase:** 5A — Customer & Vehicle Read-Only Legacy Audit  
**Status:** COMPLETE — STRICT STOP CONDITION REACHED  
**Date:** October 2026  
**Target Local Database:** `reliable_insurance_dev` on `localhost:3306` (MySQL 8.0)  
**Legacy Reference Database:** `brahmainsurance` on `103.149.199.250:3309` (MySQL 8.0, Read-Only Audit)  
**Primary Source of Truth:** Live Database Metadata, Legacy C# Solution (`InsurancefinalNew`), 29 Migration Audit Documents (`migration_audit`)  

---

## 1. Executive Summary

This Phase 5A audit delivers a complete, empirical, read-only analysis of the customer and vehicle domain models: **`tbl_customer`** (221,118 rows) and **`tbl_vehicledetails`** (213,562 rows).

### Key Empirical Findings:
1. **Schema & Primary Keys Verified**:
   - `tbl_customer`: Exactly **38 columns**, PK `CustomerId` (`int(11) AUTO_INCREMENT NOT NULL`).
   - `tbl_vehicledetails`: Exactly **32 columns**, PK `CustVehId` (`int(11) AUTO_INCREMENT NOT NULL`).
2. **Customer → Vehicle Logical Linkage**:
   - `tbl_vehicledetails.CustomerId = tbl_customer.CustomerId`.
   - **Zero physical foreign keys exist in MySQL**. Relational integrity is enforced at the application layer.
   - All 213,562 vehicle rows in production link to a non-null `CustomerId`.
3. **Vehicle → Master Data Linkage**:
   - `tbl_vehicledetails` binds directly to the canonical master tables verified in Phase 4: `Veh_Type_ID`, `Veh_Sub_Type_ID`, `Make_ID`, `Model_ID`, `Variant_ID`, and `RTOId`.
4. **Registration Number Is NOT Globally Unique**:
   - Across 213,562 vehicle records, there are only **169,418 unique registration numbers**.
   - In Reliable Insurance, vehicle uniqueness is enforced **strictly per Financial Year** (`sp_CheckRegistrationNoNew`), allowing renewals across financial years.
5. **Chassis Number Spelling & Cardinality**:
   - The physical column is spelled **`ChaiseNo`** (legacy typo preserved).
   - Only 36,679 unique values exist across 213,562 rows (frequent default values like `'0'` and `'NA'`).
6. **Mobile Number Cardinality**:
   - `MoblieNo1` has only 47,704 unique values across 221,118 customers; multiple customers share phone numbers (corporate clients, family policies, agent defaults).
7. **Customer Code Generation**:
   - `sp_generateCustomerCode` reads `AUTO_INCREMENT FROM information_schema.TABLES` without reservation. `CustomerCode` is indexed with `UNIQUE KEY CustomerCode_UNIQUE (CustomerCode(100))`.
8. **Phase 2 Model Status**:
   - Existing Phase 2 models in `app/models/customer.py` and `app/models/vehicle.py` match physical columns and data types with 100% accuracy.
   - Gap identified: `tbl_customer` in production possesses 3 indexes (`CustomerCode_UNIQUE`, `Fk5_ClientId_idx`, `Fk18_BranchId_idx`) not yet defined in the SQLAlchemy model `__table_args__`.

---

## 2. `tbl_customer` Physical Schema Specification

- **Table Name**: `tbl_customer`
- **Total Columns**: 38
- **Primary Key**: `CustomerId` (`int(11) AUTO_INCREMENT NOT NULL`)
- **Row Count**: 221,118 rows (AUTO_INCREMENT: 224,265)
- **Engine / Options**: `ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_general_ci ROW_FORMAT=Dynamic`

| # | Column Name | MySQL Data Type | Nullable | Default | Key | Extra | Business Notes |
|---|---|---|---|---|---|---|---|
| 1 | `CustomerId` | `int(11)` | NO | NULL | PRI | `auto_increment` | Primary Key |
| 2 | `CustomerCode` | `varchar(255)` | YES | NULL | UNI | | Client unique business code (e.g. "CUST-001") |
| 3 | `initial` | `varchar(255)` | YES | NULL | | | Salutation (Mr., Mrs., Dr., M/S) |
| 4 | `CustFName` | `varchar(300)` | YES | NULL | | | Customer First Name |
| 5 | `CustMName` | `varchar(255)` | YES | NULL | | | Customer Middle Name |
| 6 | `CustLName` | `varchar(255)` | YES | NULL | | | Customer Last Name |
| 7 | `CustomerType` | `varchar(255)` | YES | NULL | | | "Individual" or "Corporate" |
| 8 | `ClientId` | `int(11)` | YES | NULL | MUL | | Link to Corporate Client (`tbl_corporateclient`) |
| 9 | `PerAddrLine1` | `varchar(600)` | YES | NULL | | | Permanent Address Line 1 |
| 10 | `PerAddrLine2` | `varchar(600)` | YES | NULL | | | Permanent Address Line 2 |
| 11 | `PerTalukaId` | `int(11)` | YES | NULL | | | Permanent Taluka / Sub-district ID |
| 12 | `PerDistrictId` | `int(11)` | YES | NULL | | | Permanent District ID |
| 13 | `PerStateId` | `int(11)` | YES | NULL | | | Permanent State ID |
| 14 | `PerPinCode` | `varchar(255)` | YES | NULL | | | Permanent PIN Code |
| 15 | `ComAddrLine1` | `varchar(600)` | YES | NULL | | | Communication Address Line 1 |
| 16 | `ComAddrLine2` | `varchar(600)` | YES | NULL | | | Communication Address Line 2 |
| 17 | `ComTalukaId` | `int(11)` | YES | NULL | | | Communication Taluka ID |
| 18 | `ComDistrictId` | `int(11)` | YES | NULL | | | Communication District ID |
| 19 | `ComStateId` | `int(11)` | YES | NULL | | | Communication State ID |
| 20 | `ComPinCode` | `varchar(255)` | YES | NULL | | | Communication PIN Code |
| 21 | `MoblieNo1` | `varchar(255)` | YES | NULL | | | Primary Contact Mobile (Preserved spelling) |
| 22 | `MoblieNo2` | `varchar(255)` | YES | NULL | | | Secondary Contact Mobile (Preserved spelling) |
| 23 | `Gender` | `varchar(255)` | YES | NULL | | | "Male", "Female", "Other" |
| 24 | `MaritalStatus` | `varchar(255)` | YES | NULL | | | "Single", "Married", etc. |
| 25 | `PAN_No` | `varchar(255)` | YES | NULL | | | Permanent Account Number |
| 26 | `AadharNo` | `varchar(255)` | YES | NULL | | | Aadhaar Number (12 digits) |
| 27 | `DateOfBirth` | `date` | YES | NULL | | | Date of Birth |
| 28 | `EMailId` | `varchar(255)` | YES | NULL | | | Email Address |
| 29 | `NomineeName` | `varchar(255)` | YES | NULL | | | Policy Nominee Full Name |
| 30 | `BranchId` | `int(11)` | YES | NULL | MUL | | Branch Ownership Scope (`tbl_branch`) |
| 31 | `CreateDate` | `datetime` | YES | NULL | | | Record creation timestamp |
| 32 | `CreateUser` | `varchar(255)` | YES | NULL | | | Username / User ID of creator |
| 33 | `UpdateDate` | `datetime` | YES | NULL | | | Record last update timestamp |
| 34 | `UpdateUser` | `varchar(255)` | YES | NULL | | | Username / User ID of updater |
| 35 | `Extra1` | `varchar(255)` | YES | NULL | | | Legacy metadata extension 1 |
| 36 | `Extra2` | `varchar(255)` | YES | NULL | | | Legacy metadata extension 2 |
| 37 | `CompanyName` | `varchar(255)` | YES | NULL | | | Corporate Employer / Entity Name |
| 38 | `isdeleted` | `varchar(255)` | YES | NULL | | | Soft-delete flag (`'0'` = active, `'1'` = deleted) |

### `tbl_customer` Indexes in Production:
1. `PRIMARY` on (`CustomerId`) [Unique]
2. `CustomerCode_UNIQUE` on (`CustomerCode`(100)) [Unique]
3. `Fk5_ClientId_idx` on (`ClientId`) [Non-Unique]
4. `Fk18_BranchId_idx` on (`BranchId`) [Non-Unique]

---

## 3. `tbl_vehicledetails` Physical Schema Specification

- **Table Name**: `tbl_vehicledetails`
- **Total Columns**: 32
- **Primary Key**: `CustVehId` (`int(11) AUTO_INCREMENT NOT NULL`)
- **Row Count**: 213,562 rows (AUTO_INCREMENT: 216,959)
- **Engine / Options**: `ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_general_ci ROW_FORMAT=Dynamic`

| # | Column Name | MySQL Data Type | Nullable | Default | Key | Extra | Business Notes |
|---|---|---|---|---|---|---|---|
| 1 | `CustVehId` | `int(11)` | NO | NULL | PRI | `auto_increment` | Primary Key |
| 2 | `CustomerId` | `int(11)` | YES | NULL | | | Logical reference -> `tbl_customer.CustomerId` |
| 3 | `RegistrationNo` | `varchar(255)` | YES | NULL | | | Registration plate number (e.g. MH01AB1234) |
| 4 | `ChaiseNo` | `varchar(255)` | YES | NULL | | | Chassis number (Preserved legacy typo) |
| 5 | `EngineNo` | `varchar(500)` | YES | NULL | | | Vehicle engine number |
| 6 | `MfgMonth` | `varchar(255)` | YES | NULL | | | Manufacturing month (e.g. "January" or "01") |
| 7 | `MfgYear` | `varchar(255)` | YES | NULL | | | Manufacturing year (e.g. "2022") |
| 8 | `Ex_ShowroomPrice` | `varchar(255)` | YES | NULL | | | Ex-Showroom price for IDV rating |
| 9 | `FuelTypeId` | `int(11)` | YES | NULL | | | Fuel type ID -> `tbl_fueltype.FuelTypeId` |
| 10 | `Veh_Type_ID` | `int(11)` | YES | NULL | | | Category -> `tbl_vehicle_type.Veh_Type_ID` |
| 11 | `Veh_Sub_Type_ID`| `int(11)` | YES | NULL | | | Sub-type -> `tbl_vehicle_sub_type.Veh_Sub_Type_ID` |
| 12 | `Make_ID` | `int(11)` | YES | NULL | | | Manufacturer -> `tbl_vehicle_make.Make_ID` |
| 13 | `Model_ID` | `int(11)` | YES | NULL | | | Vehicle Model -> `tbl_vehicle_model.Model_ID` |
| 14 | `Variant_ID` | `int(11)` | YES | NULL | | | Catalog Variant -> `tbl_vehicle_variants.Variant_ID` |
| 15 | `VehiclePurDate` | `datetime` | YES | NULL | | | Vehicle purchase date |
| 16 | `SeatsCapacity` | `varchar(255)` | YES | NULL | | | Seating capacity |
| 17 | `EnginePower` | `varchar(500)` | YES | NULL | | | CC / Engine power displacement |
| 18 | `TransTonnageCapacity`| `varchar(255)`| YES | NULL | | | Commercial tonnage / carrying capacity |
| 19 | `VehicleWeight` | `varchar(255)` | YES | NULL | | | Gross Vehicle Weight (GVW) |
| 20 | `VehicleRegDate` | `datetime` | YES | NULL | | | Date of initial vehicle registration |
| 21 | `RTOId` | `int(11)` | YES | NULL | | | RTO Office -> `tbl_rto.RTOId` |
| 22 | `BranchId` | `int(11)` | YES | NULL | | | Branch Ownership Scope (`tbl_branch`) |
| 23 | `CorporateClientId`| `int(11)` | YES | NULL | | | Fleet / Corporate owner client ID |
| 24 | `CreateDate` | `datetime` | YES | NULL | | | Record creation timestamp |
| 25 | `CreatedUser` | `varchar(255)` | YES | NULL | | | Username / User ID of creator |
| 26 | `UpdatedDate` | `datetime` | YES | NULL | | | Record last update timestamp |
| 27 | `UpdatedUser` | `varchar(255)` | YES | NULL | | | Username / User ID of updater |
| 28 | `Extra1` | `varchar(255)` | YES | NULL | | | Metadata extension 1 |
| 29 | `Extra2` | `varchar(255)` | YES | NULL | | | Metadata extension 2 |
| 30 | `isdeleted` | `varchar(255)` | YES | NULL | | | Soft-delete flag (`'0'` = active, `'1'` = deleted) |
| 31 | `FinancialYear` | `varchar(255)` | **NO** | NULL | | | Fiscal policy period (e.g. "2024-2025") |
| 32 | `VehicleVariant` | `varchar(255)` | YES | NULL | | | Text variant descriptor string |

### `tbl_vehicledetails` Indexes in Production:
1. `PRIMARY` on (`CustVehId`) [Unique]
*(Zero secondary indexes or unique indexes exist on `tbl_vehicledetails` in production)*.

---

## 4. Customer → Vehicle Relationship

- **Relationship Type**: Logical One-to-Many (`1 : N`)
- **Joining Key**:
  $$\text{tbl\_customer.CustomerId} = \text{tbl\_vehicledetails.CustomerId}$$
- **Physical Foreign Key**: **NONE (0 constraints)**.
- **Production Data Analysis**:
  - `tbl_customer.CustomerId` range: 3 to 224,264.
  - `tbl_vehicledetails.CustomerId` range: 2 to 224,264.
  - Zero vehicle records have `CustomerId IS NULL` or `CustomerId = 0`.
  - While one customer may own multiple vehicles (e.g., commercial transport operators or multi-car families), in the historical transaction pipeline a separate vehicle asset row was created per policy booking.
- **Referential Integrity Rule**: Any application-level cascade, delete, or join must be enforced in repository/service code without expecting database-level foreign key cascades.

---

## 5. Vehicle → Master Relationships

Empirical proof from production stored procedures (`sp_searchForEndorseByVehicleNo`, `sp_SelectByVehicleSearchNew`, `sp_VehicleHistoryQualityCheck`):

```sql
FROM tbl_vehicledetails CV
INNER JOIN tbl_vehicle_type     VT ON VT.Veh_Type_ID     = CV.Veh_Type_ID
INNER JOIN tbl_vehicle_sub_type VST ON VST.Veh_Sub_Type_ID = CV.Veh_Sub_Type_ID
INNER JOIN tbl_vehicle_make     VM ON VM.Make_ID         = CV.Make_ID
INNER JOIN tbl_vehicle_model    VMD ON VMD.Model_ID       = CV.Model_ID
INNER JOIN tbl_vehicle_variants VV ON VV.Variant_ID     = CV.Variant_ID
LEFT  JOIN tbl_rto              RTO ON RTO.RTOId         = CV.RTOId
LEFT  JOIN tbl_fueltype         FT ON FT.FuelTypeId     = CV.FuelTypeId
```

| Vehicle Foreign Key Column | Target Master Table | Target Primary Key | Production Range in `tbl_vehicledetails` |
|---|---|---|---|
| `Veh_Type_ID` | `tbl_vehicle_type` | `Veh_Type_ID` | 0 – 8 |
| `Veh_Sub_Type_ID` | `tbl_vehicle_sub_type` | `Veh_Sub_Type_ID` | 0 – 112 |
| `Make_ID` | `tbl_vehicle_make` | `Make_ID` | 0 – 651 |
| `Model_ID` | `tbl_vehicle_model` | `Model_ID` | 0 – 5,094 |
| `Variant_ID` | `tbl_vehicle_variants` | `Variant_ID` | 0 – 40,099 |
| `RTOId` | `tbl_rto` | `RTOId` | 0 – 1,253 |
| `FuelTypeId` | `tbl_fueltype` | `FuelTypeId` | 0 – 10 |

---

## 6. Stored Procedure Usage Map

A scan of all 1,980 procedures in `brahmainsurance` revealed **561 routines** that query or manipulate `tbl_customer` or `tbl_vehicledetails`.

### Core CRUD & Lookup Procedures:

| Procedure Name | Target Table(s) | Operation | Parameters | Business Purpose |
|---|---|---|---|---|
| `sp_InsertCustomer` | `tbl_customer` | INSERT | IN 35 params, OUT `P_CustomerId` INT | Primary retail customer intake; sets `isdeleted = '0'`, returns `last_insert_id()`. |
| `sp_UpdateCustomer` | `tbl_customer` | UPDATE | IN 34 params (`CustomerId` + fields) | Updates retail client demographics and addresses. |
| `sp_generateCustomerCode` | `tbl_customer` | READ | OUT `P_CustomerCode` INT | Reads `AUTO_INCREMENT FROM information_schema.TABLES` to generate client code. |
| `Sp_VehicleDetails` | `tbl_vehicledetails` | INSERT | IN 29 params, OUT `P_CustVehId` INT | Primary insured vehicle insertion; sets `isdeleted = '0'`, returns `last_insert_id()`. |
| `Sp_VehicleDetails_2026` | `tbl_vehicledetails` | INSERT | IN 30 params, OUT `P_CustVehId` INT | Modernized vehicle intake with `FinancialYear` and `VehicleVariant` strings. |
| `Sp_UpdateVehicleDetails` | `tbl_vehicledetails` | UPDATE | IN 23 params (`CustVehId` + fields) | Updates vehicle technical specifications and RTO info. |
| `sp_CheckRegistrationNo` | `tbl_vehicledetails` | SELECT | IN `P_RegistrationNo`, `P_FinancialYear`, OUT `P_ReturnMsg` | Counts vehicles in `FinancialYear`; returns 0 if available, 1 if duplicate. |
| `sp_CheckRegistrationNoNew` | `tbl_vehicledetails`, `tbl_transaction` | SELECT | IN `P_RegistrationNo`, `P_FinancialYear`, OUT `P_ReturnMsg` | Inner joins active transaction master to confirm active policy in `FinancialYear`. |
| `sp_SearchCustName` | `tbl_customer` | SELECT | IN `P_SerachText` VARCHAR(20), `P_BranchId` INT | Substring search on `Concat(CustFName,' ',CustMName,' ',CustLName)` scoped by `BranchId`. |
| `sp_SearchCustNameapp` | `tbl_customer` | SELECT | IN `P_SerachText` VARCHAR(20) | Mobile app substring search on customer name across all branches. |
| `sp_SearchByVehicleNo` | `tbl_vehicledetails` | SELECT | IN `P_SerachText` VARCHAR(50), `P_BranchId` INT | Substring search on `RegistrationNo` with branch scoping. |
| `sp_SearchVehicleNoapp` | `tbl_vehicledetails`, `tbl_transaction` | SELECT | IN `P_SerachText` VARCHAR(20) | Mobile app vehicle search joined with active transactions. |
| `sp_SelectByVehicleSearchNew` | `tbl_vehicledetails`, `tbl_customer` | SELECT | IN `P_CustVehId` INT, `P_BranchId` INT | Full hydrated join of vehicle details + owner customer record by `CustVehId`. |
| `sp_DeleteCustvehicleDetailsbyCustvehId` | `tbl_vehicledetails` | DELETE | IN `P_CustVehId` INT | Physical deletion of orphan vehicle record before transaction submission. |
| `sp_AlreadyExistVehicleNo` | `tbl_vehicledetails` | DUAL | IN `P_RegNo`, `P_opr` ("SEL"/"DEL"), `P_CustVehId` | Checks or deletes vehicle if not linked to any policy in current calendar year. |

---

## 7. Legacy API / Service Usage Map

Mapped directly from `Insurance\Service.asmx.cs`, `DAL\DAL_Operations.cs`, and `BLL\BLL_Operations.cs`:

| Legacy API / Method | DAL Operation | Stored Procedure | Request Parameters | Response / Behavior |
|---|---|---|---|---|
| `Service.asmx: SearchCustNameapp` | `DAL_Operations: SearchCustNameapp` | `sp_SearchCustNameapp` | `SerachText` (string) | JSON array of `{CustomerId, CustName}` |
| `Service.asmx: appSerachCustNameDetails` | `DAL_Operations: sp_appSerachCustNameDetails` | `sp_appSerachCustNameDetails` | `CustName` (string) | Full customer profile and address attributes |
| `SearchMethods.aspx: GetCustomers` | `BLL_SelectCustomerName` | `sp_SearchCustName` | `SerachText`, `BranchId` | Autocomplete list filtered by user's branch |
| `PolicyTransactionNew.aspx: SaveCustomer` | `DAL_InsertCustomer` | `sp_InsertCustomer` | `API_Customer` DTO | Returns generated integer `CustomerId` |
| `PolicyTransactionNew.aspx: UpdateCustomer` | `DAL_UpdateCustomer` | `sp_UpdateCustomer` | `API_Customer` DTO | Returns boolean success |
| `PolicyTransactionNew.aspx: CheckRegNo` | `DAL_CheckRegistrationNoNew` | `sp_CheckRegistrationNoNew` | `RegistrationNo`, `FinancialYear` | Returns `0` (clean) or `1` (duplicate) |
| `PolicyTransactionNew.aspx: SaveVehicle` | `DAL_InsertVehicleDetails` | `Sp_VehicleDetails` / `_2026` | `API_CustVehicle` DTO | Returns generated integer `CustVehId` |
| `PolicyTransactionNew.aspx: UpdateVehicle` | `DAL_UpdateVehicleDetails` | `Sp_UpdateVehicleDetails` | `API_CustVehicle` DTO | Returns boolean success |
| `Service.asmx: Sp_InsertAppTransctiondetailsNew8` | Direct ADO.NET staging | `Sp_InsertAppTransctiondetailsNew8` | Proposal payload with customer + vehicle info | Inserts proposal into `tbl_transactionappnew` |

---

## 8. Customer Create/Update Behavior

1. **Required Fields (Empirical & Procedure Contract)**:
   - `CustFName`: First name (cannot be blank for valid policy issuance).
   - `MoblieNo1`: Mandatory for SMS delivery and customer tracking.
   - `CustomerType`: "Individual" or "Corporate".
   - `BranchId`: Mandatory integer linking customer to servicing branch.
2. **Optional Demographic & Compliance Fields**:
   - `CustMName`, `CustLName`, `initial`.
   - `PAN_No`: Required if annual cash premium exceeds ₹50,000 (tax compliance).
   - `AadharNo`: Optional in older records; increasingly captured for KYC.
   - `DateOfBirth`: Used for life/driver risk profiling.
   - `NomineeName`: Beneficial for personal accident coverage.
   - `PerAddr*` / `ComAddr*`: Address lines and taluka/district/state/pin pointers.
3. **Duplicate Detection**:
   - The legacy backend **does NOT block customer creation on duplicate mobile or PAN**.
   - Multiple customer records frequently share `MoblieNo1` or `PAN_No`.
   - Uniqueness is strictly enforced **only** on `CustomerCode` (`UNIQUE KEY CustomerCode_UNIQUE`).
4. **Soft-Delete Semantics**:
   - Newly inserted customers are marked with `isdeleted = '0'`.
   - Update queries do not modify `isdeleted`.

---

## 9. Vehicle Create/Update Behavior

1. **Required Fields**:
   - `CustomerId`: Mandatory integer linking vehicle to customer.
   - `RegistrationNo`: Vehicle registration plate string.
   - `ChaiseNo`: Chassis number.
   - `EngineNo`: Engine number.
   - `FinancialYear`: **Physical NOT NULL column in MySQL**. Required for audit and tax ledger partitioning (e.g. "2024-2025").
   - `Veh_Type_ID`, `Make_ID`, `Model_ID`, `Variant_ID`: Master category and catalog pointers.
2. **Optional Fields**:
   - `MfgMonth`, `MfgYear`, `VehiclePurDate`, `VehicleRegDate`.
   - `Ex_ShowroomPrice`, `SeatsCapacity`, `EnginePower`, `VehicleWeight`, `TransTonnageCapacity`.
   - `RTOId`, `CorporateClientId`, `BranchId`, `VehicleVariant`.
3. **Duplicate Detection Rules**:
   - Handled exclusively via `sp_CheckRegistrationNoNew`:
     - Checks if `RegistrationNo` is already attached to an active transaction (`tbl_transaction.isdeleted = 0`) in the **same `FinancialYear`**.
     - If yes, issuance is flagged as duplicate.
     - If in a different `FinancialYear`, registration is permitted (representing annual policy renewal).

---

## 10. `RegistrationNo` Behavior

- **MySQL Column**: `RegistrationNo varchar(255) DEFAULT NULL`.
- **Global Uniqueness**: **FALSE**. Out of 213,562 vehicle rows, only 169,418 unique registration numbers exist.
- **Normalization & Format**:
  - The database does **not** enforce regex or alphanumeric cleaning.
  - Formats vary historically:
    - Standard: `MH01AB1234`, `MH-01-AB-1234`, `MH 01 AB 1234`.
    - New vehicles: `NEW`, `NEW VEHICLE`, `UNREGISTERED`.
  - In OCR / third-party ingestion (`tbl_pe_calliber_policy`), registration is split into 4 components (`MH`, `01`, `AB`, `1234`) and concatenated without hyphens.
- **Search Behavior**:
  - `sp_SearchByVehicleNo`: `RegistrationNo LIKE Concat('%', P_SerachText, '%')`.
  - Case-insensitive due to `utf8_general_ci` collation.

---

## 11. `ChaiseNo` Behavior

- **Physical Column Name**: **`ChaiseNo`** (`varchar(255)`).
- **Typo Preservation Non-Negotiable**: Must **NOT** be renamed to `ChassisNo` in models, migrations, or database queries.
- **Global Uniqueness**: **FALSE**. Only 36,679 unique chassis numbers across 213,562 rows.
- **Dummy & Fallback Values**: In complete policies with pending RC verification, values like `'0'`, `'NA'`, `'CHASSIS'`, `'NEW'` appear repeatedly.

---

## 12. Mobile / Search Behavior

- **Physical Columns**: `MoblieNo1` (`varchar(255)`), `MoblieNo2` (`varchar(255)`).
- **Typo Preservation**: Physical name `MoblieNo1` (with 'li') preserved verbatim.
- **Primary vs. Secondary**: `MoblieNo1` is the authoritative customer communication phone. `MoblieNo2` is optional alternate contact.
- **Uniqueness**: **NOT UNIQUE** (47,704 unique numbers across 221,118 rows).
- **Search Logic**:
  - Name Search: `sp_SearchCustName` executes `WHERE Concat(CustFName,' ',CustMName,' ',CustLName) LIKE Concat('%', P_SerachText, '%') AND BranchId = P_BranchId AND isdeleted = 0`.
  - Mobile App Search: `sp_SearchCustNameapp` executes identical name substring matching across all branches without branch limitation.

---

## 13. Status / Delete Semantics

- **`tbl_customer.isdeleted`**:
  - Datatype: `varchar(255)`.
  - Active value: `'0'`. Deleted value: `'1'`.
  - Production verification: 100% of customer records (221,118 rows) are marked `'0'`.
- **`tbl_vehicledetails.isdeleted`**:
  - Datatype: `varchar(255)`.
  - Active value: `'0'`. Deleted value: `'1'`.
  - Production verification: 213,560 rows are `'0'`, 2 rows are `'1'`.
- **Physical Deletes**: Physical `DELETE FROM tbl_vehicledetails` occurs in `sp_DeleteCustvehicleDetailsbyCustvehId` and `sp_AlreadyExistVehicleNo` when cleaning up unbooked draft vehicle entries.

---

## 14. Branch / Ownership Semantics

- **Physical Ownership Columns**:
  - `tbl_customer.BranchId` (`int(11) NULL`, indexed via `Fk18_BranchId_idx`).
  - `tbl_vehicledetails.BranchId` (`int(11) NULL`).
- **Authorization Scoping in Stored Procedures**:
  ```sql
  WHERE BranchId = (CASE WHEN P_BranchId = 0 THEN BranchId ELSE P_BranchId END)
  ```
  - `P_BranchId = 0`: Super-admin / Headquarters mode — returns records across all branches.
  - `P_BranchId > 0`: Branch User / Operator mode — strictly restricted to records created within that branch.
  - Mobile App APIs: Deliberately bypass branch scoping to enable field POSP agents and brokers to search and renew existing customers across corporate branches.

---

## 15. Phase 2 Model Gap Matrix

Comparison between current Phase 2 models in `Reliable-Insurance-Backend` and the verified production schema:

| Entity | Model File | Phase 2 Column Count | Production Column Count | Discrepancy Classification | Detailed Finding |
|---|---|---|---|---|---|
| **Customer** | `app/models/customer.py` | 38 | 38 | **INDEX MISMATCH (DOCUMENTATION ONLY)** | All 38 column names, types, and nullabilities are an **EXACT MATCH**. Production has 3 secondary indexes (`CustomerCode_UNIQUE`, `Fk5_ClientId_idx`, `Fk18_BranchId_idx`) not yet specified in `__table_args__`. |
| **VehicleDetails** | `app/models/vehicle.py` | 32 | 32 | **EXACT MATCH** | All 32 columns match physical database exactly. `FinancialYear` correctly mapped as `Mapped[str] = mapped_column(..., nullable=False)`. Zero missing columns. Zero unverified indexes. |

---

## 16. Business Logic Boundaries

To maintain strict domain isolation, the following business logic **MUST NOT** be implemented in Phase 5:
- **Premium Calculation**: OD discount formula, TP rates, add-on costs.
- **GST Calculation**: 18% tax calculation and rounding logic.
- **NCB Progression**: No Claim Bonus percentage grids (0% to 50%).
- **Quotation Generation**: Insurer pricing aggregations.
- **Policy Inward Generation**: `sp_generateInwardNo` or sequential booking numbers.
- **Payment Processing**: Cashier/Accountant cheque clearing or wallet deductions.
- **Commission Ledger**: Ledger postings to `tbl_account` or `tbl_franchisecommission`.

---

## 17. Production Access Safety Audit

| Safety Audit Item | Verification Status | Details |
|---|---|---|
| **Read-Only Access Only** | **VERIFIED** | Connected strictly for schema introspection; zero writes executed. |
| **Queries Executed** | **VERIFIED** | `SHOW CREATE TABLE`, `SHOW INDEX`, `information_schema.COLUMNS`, `information_schema.TABLES`, `information_schema.ROUTINES`, `SHOW CREATE PROCEDURE`, safe `COUNT(*)`. |
| **Sensitive Data Retained** | **ZERO** | Zero customer names, phone numbers, addresses, or PANs were retrieved or persisted. |
| **Stored Procedures Executed** | **ZERO** | Zero procedures called; routine definitions inspected read-only via `information_schema.ROUTINES`. |
| **Credentials Persisted** | **ZERO** | Zero production credentials written to repository, `.env`, tests, or Git history. |

---

## 18. Open Questions & Architectural Considerations for Phase 5B

1. **Customer Code Generation Strategy**:
   - In legacy C#, `sp_generateCustomerCode` reads `AUTO_INCREMENT FROM information_schema.TABLES`. Under concurrent requests, this causes race conditions.
   - *Phase 5B Recommendation*: Generate `CustomerCode` sequentially using a concurrency-safe atomic sequence table, or generate formatted prefixed codes (`CUST-{id}`) inside a transactional session flush.
2. **Deletion Protocol in FastAPI Service**:
   - Legacy system has both soft-delete (`isdeleted = '0'`) and physical deletes for orphan vehicle entries.
   - *Phase 5B Recommendation*: Endpoints should standardise on soft-delete (`isdeleted = '1'`), with a dedicated cleanup service for abandoned vehicle drafts.
3. **Database Index Synchronization**:
   - `CustomerCode_UNIQUE`, `Fk5_ClientId_idx`, and `Fk18_BranchId_idx` exist in production `tbl_customer`.
   - *Phase 5B Recommendation*: Add these 3 indexes to `Customer` model `__table_args__` and generate an additive Alembic migration in Phase 5B.

---

## 19. Recommendations for Phase 5B Implementation Roadmap

When authorized to begin **Phase 5B — Customer & Vehicle Implementation**:
1. **Schema & Migration**:
   - Update `Customer` model with verified indexes (`CustomerCode_UNIQUE`, `Fk5_ClientId_idx`, `Fk18_BranchId_idx`).
   - Create additive Alembic migration `add_customer_indexes` against local `reliable_insurance_dev`.
2. **Repository Layer**:
   - Implement `CustomerRepository` (`get_by_id`, `get_by_code`, `search_by_name`, `get_by_mobile`, `list_by_branch`).
   - Implement `VehicleRepository` (`get_by_id`, `get_by_registration`, `check_registration_duplicate_in_fy`, `list_by_customer_id`).
3. **Pydantic Schemas**:
   - `CustomerCreate`, `CustomerUpdate`, `CustomerResponse` (clean Python field names with field aliases to physical columns).
   - `VehicleCreate`, `VehicleUpdate`, `VehicleResponse`.
4. **Service Layer**:
   - `CustomerService`: Concurrency-safe code generation, duplicate mobile warnings (non-blocking), branch isolation enforcement.
   - `VehicleService`: `FinancialYear` duplicate check, master ID validation.
5. **API Endpoints**:
   - `/api/v1/customers` (CRUD + search with JWT branch scoping).
   - `/api/v1/vehicles` (CRUD + registration lookup).
6. **Automated Test Suite**:
   - Unit tests for customer/vehicle schema validation.
   - Integration tests verifying CRUD, branch filtering, and registration duplicate checks.

---

## Strict Stop Condition Enforced
Phase 5A audit is **COMPLETE**.  
Execution is **STOPPED**. No models, repositories, services, APIs, migrations, or database changes will be created without your explicit authorization.
