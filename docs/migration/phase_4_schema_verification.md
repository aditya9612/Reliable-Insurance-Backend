# Phase 4A — Read-Only Legacy Production Schema Verification Report

**Database Catalog**: `brahmainsurance` (MySQL 8.0 on Port 3309)  
**Target Repository**: `Reliable-Insurance-Backend`  
**Execution Mode**: **READ-ONLY SCHEMA INTROSPECTION**  
**Verification Date**: October 2026  
**Status**: **COMPLETE — STOP CONDITION REACHED (AWAITING REVIEW & APPROVAL)**  

---

## 1. Production Access Safety Verification

In accordance with the strict database access rules, the legacy production database was used **strictly for read-only schema and metadata introspection**.

| Safety Check Item | Status | Verification Detail |
|---|---|---|
| **Read-only inspection performed** | **YES** | Queried `information_schema.TABLES`, `information_schema.COLUMNS`, `SHOW CREATE TABLE`, `SHOW INDEX`, and `information_schema.ROUTINES`. |
| **Any write operation performed** | **NO** | Zero INSERT, UPDATE, DELETE, REPLACE, UPSERT, MERGE executed. |
| **Any stored procedure called** | **NO** | Zero stored procedures executed or called. (Routine SQL definitions were inspected read-only via `information_schema.ROUTINES`). |
| **Any DDL executed** | **NO** | Zero CREATE, ALTER, DROP, TRUNCATE, RENAME executed on production. |
| **Any migration executed against production** | **NO** | Zero Alembic migrations connected to or executed on production. |
| **Any production data modified** | **NO** | Zero production records modified. |
| **Sensitive customer/financial data read** | **NO** | Zero customer, policy, or financial records retrieved. |
| **Credential Safety** | **COMPLIANT** | Zero legacy credentials written to `.env`, `.env.example`, Python source, tests, documentation, or Git history. |

---

## 2. Executive Summary & Key Schema Discoveries

Phase 4A read-only introspection against `brahmainsurance` resolved all table-naming, column-naming, and structural discrepancies between the prompt, the legacy audit documents (`03_DATABASE_SCHEMA_AUDIT.md`), and the C# DTOs.

### Major Findings:
1. **Physical Table Naming Quirks & Resolution**:
   - **Vehicle Type**: Two tables exist: `tbl_vehicletype` (20 rows, legacy prototype containing mixed vehicle/make data) and **`tbl_vehicle_type`** (8 rows, canonical motor vehicle category table).
   - **Vehicle Make**: `tbl_make` does NOT exist. Two tables exist: `tbl_vehiclemake` (182 rows, legacy) and **`tbl_vehicle_make`** (284 rows, active production table with class capability flags).
   - **Vehicle Model**: Neither `tbl_model` nor `tbl_vehiclemodel` exists. The actual physical table is **`tbl_vehicle_model`** (3,794 rows, PK `Model_ID`).
   - **Vehicle Variant**: `tbl_variant` does NOT exist. Two tables exist: `tbl_vehiclevariant` (3,907 rows, legacy) and **`tbl_vehicle_variants`** (27,983 rows, active production catalog with 91 columns including regional IDV pricing).
   - **RTO Master**: `tbl_rtomaster` does NOT exist. The actual physical table is **`tbl_rto`** (1,367 rows, PK `RTOId`).
   - **Insurance Company**: The physical table is **`tbl_insurancecompany`** (37 rows, 22 columns, PK `InsuranceCompanyId`).
2. **Production Referential Proof from `tbl_vehicledetails` (Phase 2 Model)**:
   Analysis of the verified 209,429-row motor asset registry table (`tbl_vehicledetails`) proves beyond doubt which tables are actively linked in production:
   - `tbl_vehicledetails.Veh_Type_ID` (range 0–8) joins to **`tbl_vehicle_type.Veh_Type_ID`** (IDs 1–8).
   - `tbl_vehicledetails.Make_ID` (range 0–651) joins to **`tbl_vehicle_make.Make_ID`** (AUTO_INCREMENT 653).
   - `tbl_vehicledetails.Model_ID` (range 0–5094) joins to **`tbl_vehicle_model.Model_ID`** (AUTO_INCREMENT 5095).
   - `tbl_vehicledetails.Variant_ID` (range 0–40099) joins to **`tbl_vehicle_variants.Variant_ID`** (AUTO_INCREMENT 40256).
   - `tbl_vehicledetails.RTOId` (range 0–1253) joins to **`tbl_rto.RTOId`** (AUTO_INCREMENT 1372).
   - `tbl_transaction.InsuranceCompanyId` joins to **`tbl_insurancecompany.InsuranceCompanyId`** (AUTO_INCREMENT 39).
3. **Database Constraints & Engine**:
   - Zero physical foreign keys exist in MySQL.
   - All tables use `ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_general_ci ROW_FORMAT=Dynamic`.

---

## 3. Verified Physical Schema Specifications

---

### 3.1 Entity: Vehicle Type

#### Physical Table: `tbl_vehicle_type` (Canonical Operational Table)
- **Status**: **ACTIVE PRODUCTION ENTITY** (Linked directly to `tbl_vehicledetails.Veh_Type_ID`)
- **Row Count**: 8 rows
- **Primary Key**: `Veh_Type_ID` (INT AUTO_INCREMENT)
- **Engine / Options**: `InnoDB`, `CHARSET=utf8`, `COLLATE=utf8_general_ci`, `ROW_FORMAT=Dynamic`

| # | Column Name | MySQL Data Type | Nullable | Default | Key | Extra | Business Notes |
|---|---|---|---|---|---|---|---|
| 1 | `Veh_Type_ID` | `int(11)` | NO | NULL | PRI | `auto_increment` | Primary Key (1=CAR, 2=GCV, 3=PCV TAXI, 4=TWO-WHEELER, 5=MISC-D, 6=BUS, 7=THREE-WHEELER GCV, 8=THREE-WHEELER PCV) |
| 2 | `Veh_Type_Name` | `varchar(255)` | YES | NULL | | | Canonical category name |
| 3 | `IsAppQuotation` | `int(11)` | YES | `0` | | | Quotation engine availability flag |
| 4 | `PolicyTypeSAIBA` | `varchar(200)` | YES | `'0'` | | | Core brokerage SAIBA mapping |
| 5 | `VantagePolicyType` | `varchar(200)` | YES | `'0'` | | | External aggregator mapping |
| 6 | `Comprehensive` | `varchar(200)` | YES | NULL | | | Comprehensive policy product slug |
| 7 | `TP` | `varchar(200)` | YES | NULL | | | Third-party policy product slug |
| 8 | `Saod` | `varchar(200)` | YES | NULL | | | Standalone Own Damage product slug |
| 9 | `VehicleType` | `varchar(200)` | YES | NULL | | | Broad classification (Private, Commercial, Bike, Bus) |
| 10 | `NatureOfUse` | `varchar(200)` | YES | NULL | | | Underwriting usage (Private, Good Carrying, Passenger Carrying, Miscellaneous) |

- **Indexes**:
  - `PRIMARY` on (`Veh_Type_ID`) [Unique]

---

#### Physical Table: `tbl_vehicletype` (Legacy Alternate Table)
- **Status**: **LEGACY LOOKUP TABLE**
- **Row Count**: 20 rows
- **Primary Key**: `VehicleTypeId` (INT AUTO_INCREMENT)

| # | Column Name | MySQL Data Type | Nullable | Default | Key | Extra | Business Notes |
|---|---|---|---|---|---|---|---|
| 1 | `VehicleTypeId` | `int(11)` | NO | NULL | PRI | `auto_increment` | Primary Key |
| 2 | `VehicleType` | `varchar(255)` | YES | NULL | | | Mixed strings (contains vehicles & manufacturers like TATA, BAJAJ) |
| 3 | `isdeleted` | `varchar(255)` | YES | NULL | | | Legacy soft-delete flag ('0' = active) |

- **Conflict & Resolution**:
  - *Conflict*: Audit and prompt referenced `tbl_vehicletype`.
  - *Resolution*: `tbl_vehicletype` is a legacy table with 20 rows containing unnormalized data. The actual operational table driving underwriting and foreign-keyed by `tbl_vehicledetails` is **`tbl_vehicle_type`** (8 rows). Both schemas are fully documented; `tbl_vehicle_type` is the authoritative domain model.

---

### 3.2 Entity: Vehicle Make

#### Physical Table: `tbl_vehicle_make` (Canonical Production Table)
- **Status**: **ACTIVE PRODUCTION ENTITY** (Linked directly to `tbl_vehicledetails.Make_ID`)
- **Row Count**: 284 rows (AUTO_INCREMENT: 653)
- **Primary Key**: `Make_ID` (INT AUTO_INCREMENT)
- **Engine / Options**: `InnoDB`, `CHARSET=utf8`, `COLLATE=utf8_general_ci`, `ROW_FORMAT=Dynamic`

| # | Column Name | MySQL Data Type | Nullable | Default | Key | Extra | Business Notes |
|---|---|---|---|---|---|---|---|
| 1 | `Make_ID` | `int(11)` | NO | NULL | PRI | `auto_increment` | Primary Key |
| 2 | `Make_Name` | `varchar(255)` | YES | NULL | | | Manufacturer name (e.g. MARUTI, TATA, HYUNDAI) |
| 3 | `R_Make_ID` | `int(11)` | YES | NULL | | | Reference / Reliance mapping Make ID |
| 4 | `GCV` | `varchar(255)` | YES | NULL | | | Goods Carrying Vehicle capability flag ('1'/'0') |
| 5 | `Misc_D` | `varchar(255)` | YES | NULL | | | Miscellaneous-D capability flag ('1'/'0') |
| 6 | `PCV` | `varchar(255)` | YES | NULL | | | Passenger Carrying Vehicle capability flag ('1'/'0') |
| 7 | `PvtCar` | `varchar(255)` | YES | NULL | | | Private Car capability flag ('1'/'0') |
| 8 | `Two_Wheeler` | `varchar(255)` | YES | NULL | | | Two-Wheeler capability flag ('1'/'0') |
| 9 | `Bus` | `varchar(255)` | YES | NULL | | | Bus capability flag ('1'/'0') |
| 10 | `Three_Wheeler` | `varchar(255)` | YES | NULL | | | Three-Wheeler GCV capability flag ('1'/'0') |
| 11 | `Three_Wheeler_Pcv` | `varchar(255)` | YES | NULL | | | Three-Wheeler PCV capability flag ('1'/'0') |
| 12 | `isdeleted` | `int(11)` | NO | `0` | | | Soft delete flag (`0` = active, `1` = deleted) |

- **Indexes**:
  - `PRIMARY` on (`Make_ID`) [Unique]

---

#### Physical Table: `tbl_vehiclemake` (Legacy Alternate Table)
- **Status**: **LEGACY LOOKUP TABLE**
- **Row Count**: 182 rows (AUTO_INCREMENT: 241)
- **Columns**: `VehicleMakeId` (`int(11)` PK AI), `CompanyName` (`varchar(255)`), `VehicleTypeId` (`int(11)`), `isdeleted` (`varchar(255)`).
- **Conflict & Resolution**:
  - *Conflict*: Prompt cited `tbl_make`; audit cited `tbl_vehiclemake`.
  - *Resolution*: The physical production table is **`tbl_vehicle_make`** (with underscore). Stored procedures (`sp_AppVehicle_Make`, `sp_VehicleMakeNew`) and `tbl_vehicledetails.Make_ID` all bind to `tbl_vehicle_make.Make_ID`.

---

### 3.3 Entity: Vehicle Model

#### Physical Table: `tbl_vehicle_model`
- **Status**: **ACTIVE PRODUCTION ENTITY** (Linked directly to `tbl_vehicledetails.Model_ID`)
- **Row Count**: 3,794 rows (AUTO_INCREMENT: 5095)
- **Primary Key**: `Model_ID` (INT AUTO_INCREMENT)
- **Engine / Options**: `InnoDB`, `CHARSET=utf8`, `COLLATE=utf8_general_ci`, `ROW_FORMAT=Dynamic`

| # | Column Name | MySQL Data Type | Nullable | Default | Key | Extra | Business Notes |
|---|---|---|---|---|---|---|---|
| 1 | `Model_ID` | `int(11)` | NO | NULL | PRI | `auto_increment` | Primary Key |
| 2 | `Make_ID` | `int(11)` | YES | NULL | MUL | | Logical reference to `tbl_vehicle_make.Make_ID` |
| 3 | `Model_Name` | `varchar(255)` | YES | NULL | | | Model name (e.g. SWIFT, I20, CITY) |
| 4 | `R_Make_ID` | `int(11)` | YES | NULL | | | Reference Make ID |
| 5 | `Type` | `int(11)` | YES | NULL | | | Logical reference to `tbl_vehicle_type.Veh_Type_ID` |
| 6 | `SegmentId` | `int(11)` | NO | NULL | | | Vehicle segment code |
| 7 | `isdeleted` | `int(11)` | NO | `0` | | | Soft delete flag (`0` = active, `1` = deleted) |

- **Indexes**:
  - `PRIMARY` on (`Model_ID`) [Unique]
  - `tbl_Vehicle_Make` on (`Make_ID`) [Non-Unique]

- **Conflict & Resolution**:
  - *Conflict*: Prompt requested `tbl_model`; audit referenced `tbl_vehiclemodel`.
  - *Resolution*: Neither exists. The actual physical table in MySQL is **`tbl_vehicle_model`** with primary key **`Model_ID`**.

---

### 3.4 Entity: Vehicle Variant

#### Physical Table: `tbl_vehicle_variants` (Canonical Production Catalog)
- **Status**: **ACTIVE PRODUCTION ENTITY** (Linked directly to `tbl_vehicledetails.Variant_ID`)
- **Row Count**: 27,983 rows (AUTO_INCREMENT: 40256)
- **Total Column Count**: 91 columns
- **Primary Key**: `Variant_ID` (INT AUTO_INCREMENT)
- **Engine / Options**: `InnoDB`, `CHARSET=utf8`, `COLLATE=utf8_general_ci`, `ROW_FORMAT=Dynamic`

#### Core Vehicle Specification Columns (1–28):
| # | Column Name | MySQL Data Type | Nullable | Default | Key | Extra | Business Notes |
|---|---|---|---|---|---|---|---|
| 1 | `Variant_ID` | `int(11)` | NO | NULL | PRI | `auto_increment` | Primary Key |
| 2 | `Veh_Type_ID` | `int(11)` | YES | NULL | MUL | | Logical ref -> `tbl_vehicle_type.Veh_Type_ID` |
| 3 | `Veh_Sub_Type_ID` | `int(11)` | YES | NULL | MUL | | Logical ref -> `tbl_vehicle_sub_type.Veh_Sub_Type_ID` |
| 4 | `Model_ID` | `int(11)` | YES | NULL | MUL | | Logical ref -> `tbl_vehicle_model.Model_ID` |
| 5 | `Make_Tac_Code` | `varchar(255)` | YES | NULL | | | Tariff Advisory Committee (TAC) Make Code |
| 6 | `Model_Tac_Code` | `varchar(255)` | YES | NULL | | | TAC Model Code |
| 7 | `Variance` | `varchar(255)` | YES | NULL | | | Variant descriptor (e.g. VXI, ZXI, SPORTZ) |
| 8 | `Tac_Code` | `varchar(255)` | YES | NULL | | | Combined TAC Code |
| 9 | `Wheels` | `varchar(255)` | YES | NULL | | | Number of wheels |
| 10 | `Manufacturing_Year` | `varchar(255)` | YES | NULL | | | Production year |
| 11 | `Operated_By` | `varchar(255)` | YES | NULL | | | Fuel / propulsion type |
| 12 | `Amp` | `varchar(255)` | YES | NULL | | | Battery amp rating (EV / commercial) |
| 13 | `CC` | `varchar(255)` | YES | NULL | | | Cubic Capacity (e.g. "1197") |
| 14 | `Unit_Name` | `varchar(255)` | YES | NULL | | | Unit measurement |
| 15 | `Battery_Manufacturer` | `varchar(255)` | YES | NULL | | | Battery manufacturer name |
| 16 | `Gross_Weight` | `varchar(255)` | YES | NULL | | | Gross Vehicle Weight (GVW) |
| 17 | `Seating_Capacity` | `varchar(255)` | YES | NULL | | | Certified passenger capacity |
| 18 | `Carrying_Capacity` | `varchar(255)` | YES | NULL | | | Payload carrying capacity (tons/kg) |
| 19 | `Body_Type` | `varchar(255)` | YES | NULL | | | Body type classification |
| 20 | `Min_Seating_Capacity` | `varchar(255)` | YES | NULL | | | Minimum seats |
| 21 | `Max_Seating_Capacity` | `varchar(255)` | YES | NULL | | | Maximum seats |
| 22 | `Min_carrying_Capacity` | `varchar(255)` | YES | NULL | | | Minimum payload |
| 23 | `Max_carrying_Capacity` | `varchar(255)` | YES | NULL | | | Maximum payload |
| 24 | `Is_In_Black_Listed` | `varchar(255)` | YES | NULL | | | Underwriting decline / blacklist flag |
| 25 | `IsObsolete` | `varchar(255)` | YES | NULL | | | Obsolete model flag |
| 26 | `IsImported` | `varchar(255)` | YES | NULL | | | CBU / imported vehicle flag |
| 27 | `Vehicle_Segment_Name` | `varchar(255)` | YES | NULL | | | Segment description (Hatchback, SUV, etc.) |
| 28 | `COM_Segment` | `varchar(255)` | YES | NULL | | | Commercial segment |

#### Ex-Showroom Regional Pricing Matrix Columns (29–85):
Includes 57 regional ex-showroom price columns (Body, Model, Chassis) across 19 major cities:
- `ExMumbai_Body_Price`, `ExMumbai_Model_Price`, `ExMumbai_Chasis_Price`
- `ExNewDelhi_Body_Price`, `ExNewDelhi_Model_Price`, `ExNewDelhi_Chasis_Price`
- `ExBangalore_Body_Price`, `ExBangalore_Model_Price`, `ExBangalore_Chasis_Price`
- `ExKolkatta_Body_Price`, `ExKolkatta_Model_Price`, `ExKolkatta_Chasis_Price`
- `ExAhmedabad_Body_Price`, `ExAhmedabad_Model_Price`, `ExAhmedabad_Chasis_Price`
- `ExChandigarh_Body_Price`, `ExChandigarh_Model_Price`, `ExChandigarh_Chasis_Price`
- `ExShimla_Body_Price`, `ExShimla_Model_Price`, `ExShimla_Chasis_Price`
- `ExFaridabad_Body_Price`, `ExFaridabad_Model_Price`, `ExFaridabad_Chasis_Price`
- `ExLucknow_Body_Price`, `ExLucknow_Model_Price`, `ExLucknow_Chasis_Price`
- `ExDehradun_Body_Price`, `ExDehradun_Model_Price`, `ExDehradun_Chasis_Price`
- `ExKohima_Body_Price`, `ExKohima_Model_Price`, `ExKohima_Chasis_Price`
- `ExPatna_Body_Price`, `ExPatna_Model_Price`, `ExPatna_Chasis_Price`
- `ExChennai_Body_Price`, `ExChennai_Model_Price`, `ExChennai_Chasis_Price`
- `ExThiruvananthapuram_Body_Price`, `ExThiruvananthapuram_Model_Price`, `ExThiruvananthapuram_Chasis_Price`
- `ExHyderabad_Body_Price`, `ExHyderabad_Model_Price`, `ExHyderabad_Chasis_Price`
- `ExBhopal_Body_Price`, `ExBhopal_Model_Price`, `ExBhopal_Chasis_Price`
- `ExRaipur_Body_Price`, `ExRaipur_Model_Price`, `ExRaipur_Chasis_Price`
- `ExJaipur_Body_Price`, `ExJaipur_Model_Price`, `ExJaipur_Chasis_Price`
- `ExPanaji_Body_Price`, `ExPanaji_Model_Price`, `ExPanaji_Chasis_Price`

#### Metadata & Mapping Reference Columns (86–91):
| # | Column Name | MySQL Data Type | Nullable | Default | Key | Extra | Business Notes |
|---|---|---|---|---|---|---|---|
| 86 | `Last_Updated_Date` | `varchar(255)` | YES | NULL | | | Last update string |
| 87 | `Mfg_BuildIn` | `varchar(255)` | YES | NULL | | | Domestic vs imported assembly |
| 88 | `ModelStatus` | `varchar(255)` | YES | NULL | | | Active status string |
| 89 | `R_Make_ID` | `int(11)` | YES | NULL | | | Reliance Make ID |
| 90 | `R_Model_ID` | `int(11)` | YES | NULL | | | Reliance Model ID |
| 91 | `Make_Id` | `int(11)` | NO | `0` | | | Redundant direct make ID reference |

- **Indexes**:
  - `PRIMARY` on (`Variant_ID`) [Unique]
  - `tbl_Vehicle_Model` on (`Model_ID`) [Non-Unique]
  - `tbl_vehicle_sub_type` on (`Veh_Sub_Type_ID`) [Non-Unique]
  - `tbl_vehicle_type` on (`Veh_Type_ID`) [Non-Unique]

---

#### Physical Table: `tbl_vehiclevariant` (Legacy Alternate Table)
- **Status**: **LEGACY LOOKUP TABLE**
- **Row Count**: 3,907 rows (AUTO_INCREMENT: 4695)
- **Columns**: `VehicleModelId` (`int(11)` PK AI), `VehicleModelName` (`varchar(255)`), `SeatsCapacity` (`varchar(255)`), `EnginePower` (`varchar(255)`), `VehicleWeight` (`varchar(255)`), `VehicleMakeId` (`int(11)`), `isdeleted` (`varchar(255)`).
- **Conflict & Resolution**:
  - *Conflict*: Prompt requested `tbl_variant`; audit cited `tbl_vehiclevariant`.
  - *Resolution*: The production system uses **`tbl_vehicle_variants`** (plural with underscores, 27,983 rows, 91 columns) as its active vehicle catalog. All modern policy bookings (`Sp_InsertAppTransctiondetailsNew_8`) and `tbl_vehicledetails.Variant_ID` link to `tbl_vehicle_variants.Variant_ID`.

---

### 3.5 Entity: RTO Master

#### Physical Table: `tbl_rto`
- **Status**: **ACTIVE PRODUCTION ENTITY** (Linked directly to `tbl_vehicledetails.RTOId`)
- **Row Count**: 1,367 rows (AUTO_INCREMENT: 1372)
- **Primary Key**: `RTOId` (INT AUTO_INCREMENT)
- **Engine / Options**: `InnoDB`, `CHARSET=utf8`, `COLLATE=utf8_general_ci`, `ROW_FORMAT=Dynamic`

| # | Column Name | MySQL Data Type | Nullable | Default | Key | Extra | Business Notes |
|---|---|---|---|---|---|---|---|
| 1 | `RTOId` | `int(11)` | NO | NULL | PRI | `auto_increment` | Primary Key |
| 2 | `RTOLocation` | `varchar(255)` | NO | NULL | | | RTO city/office name (e.g. "MUMBAI CENTRAL", "PUNE") |
| 3 | `District` | `varchar(255)` | NO | NULL | | | District name |
| 4 | `REG_code` | `varchar(255)` | YES | NULL | | | RTO registration prefix (e.g. "MH01", "MH12", "DL01") |
| 5 | `State_ID_FK` | `int(11)` | YES | NULL | | | State foreign ID reference |
| 6 | `zone` | `varchar(255)` | YES | NULL | | | Tariff zone ('A' or 'B') for motor OD rating |
| 7 | `ClusterId` | `int(11)` | NO | NULL | | | Commercial underwriting cluster ID |
| 8 | `isdeleted` | `int(11)` | YES | NULL | | | Soft delete flag (`0` = active, `1` = deleted) |
| 9 | `StateId` | `int(11)` | YES | NULL | | | Operational State ID (1=Maharashtra, 4=Gujarat, etc.) |
| 10 | `RTOWithLocation` | `varchar(100)` | YES | `'0'` | | | Composite display label helper |

- **Indexes**:
  - `PRIMARY` on (`RTOId`) [Unique]

- **Conflict & Resolution**:
  - *Conflict*: Prompt cited `tbl_rtomaster`; audit cited `tbl_rto` (`RTOId`, `RTOCode`, `RTOName`, `StateId`).
  - *Resolution*: The physical table name is **`tbl_rto`**. Physical column names are `RTOId`, `RTOLocation`, `District`, `REG_code`, `StateId`, `zone`, `ClusterId`, `isdeleted`.

---

### 3.6 Entity: Insurance Company

#### Physical Table: `tbl_insurancecompany`
- **Status**: **ACTIVE PRODUCTION ENTITY** (Linked directly to `tbl_transaction.InsuranceCompanyId`)
- **Row Count**: 37 rows (AUTO_INCREMENT: 39)
- **Primary Key**: `InsuranceCompanyId` (INT AUTO_INCREMENT)
- **Engine / Options**: `InnoDB`, `CHARSET=utf8`, `COLLATE=utf8_general_ci`, `ROW_FORMAT=Dynamic`

| # | Column Name | MySQL Data Type | Nullable | Default | Key | Extra | Business Notes |
|---|---|---|---|---|---|---|---|
| 1 | `InsuranceCompanyId` | `int(11)` | NO | NULL | PRI | `auto_increment` | Primary Key |
| 2 | `InsuranceCompany` | `varchar(255)` | YES | NULL | | | Company name (e.g. "RELIANCE GENERAL INSURANCE", "BAJAJ ALLIANZ") |
| 3 | `BranchName` | `varchar(255)` | YES | NULL | | | Underwriter branch name |
| 4 | `BranchCode` | `varchar(255)` | YES | NULL | | | Underwriter branch code |
| 5 | `NCB` | `varchar(255)` | NO | NULL | | | NCB support configuration flag |
| 6 | `Cluster` | `varchar(255)` | NO | NULL | | | Rating cluster flag |
| 7 | `ZeroDeep` | `varchar(255)` | NO | NULL | | | Zero Depreciation availability flag |
| 8 | `isdeleted` | `varchar(255)` | YES | NULL | | | Soft delete flag ('0' = active, '1' = deleted) |
| 9 | `IsAppQuotation` | `varchar(255)` | NO | NULL | | | Mobile app quotation flag ('1'/'0') |
| 10 | `MailId` | `varchar(300)` | YES | NULL | | | Underwriter contact email |
| 11 | `CompImgPath` | `varchar(255)` | NO | NULL | | | Underwriter logo asset path |
| 12 | `LedgerMId` | `int(11)` | NO | NULL | | | Chart of Accounts link -> `tbl_ledgermaster.LedgerMId` |
| 13 | `ShortName` | `varchar(255)` | NO | NULL | | | Short abbreviation (e.g. "RGICL", "BAGIC", "HDFC ERGO") |
| 14 | `CreditDays` | `int(11)` | NO | `0` | | | Reconciliation payment credit period |
| 15 | `PolicyNo` | `varchar(500)` | NO | NULL | | | Policy format / prefix mask |
| 16 | `len` | `int(11)` | NO | NULL | | | Policy number length validation |
| 17 | `InsurerSAIBA` | `varchar(200)` | YES | `'0'` | | | SAIBA underwriter identifier |
| 18 | `InsurerBranchAutoCodeSAIBA` | `text` | YES | `'0'` | | | SAIBA auto-branch code |
| 19 | `PE_CompanyName` | `varchar(100)` | YES | `'-'` | | | PolicyEngine portal company name |
| 20 | `VantageInsurance` | `varchar(200)` | YES | `'0'` | | | Vantage aggregator identifier |
| 21 | `VantageBranch` | `varchar(100)` | YES | `'0'` | | | Vantage branch code |
| 22 | `VantageBranchAddress` | `varchar(300)` | YES | `'0'` | | | Vantage branch office address |

- **Indexes**:
  - `PRIMARY` on (`InsuranceCompanyId`) [Unique]

- **Conflict & Resolution**:
  - *Conflict*: Audit documented idealized DTO names (`CompanyId`, `CompanyName`, `ShortCode`, `PortalUrl`).
  - *Resolution*: The actual physical column names in MySQL are `InsuranceCompanyId`, `InsuranceCompany`, `ShortName`, `LedgerMId`, `MailId`, etc., exactly matching `sp_InsuranceCompany` and `sp_APPInsuranceCompany`.

---

## 4. Supporting Master Table: Vehicle Sub-Type

#### Physical Table: `tbl_vehicle_sub_type`
- **Status**: **ACTIVE SUPPORTING ENTITY** (Linked between `tbl_vehicle_type` and `tbl_vehicle_variants`)
- **Row Count**: 65 rows (AUTO_INCREMENT: 66)
- **Primary Key**: `Veh_Sub_Type_ID` (INT AUTO_INCREMENT)

| # | Column Name | MySQL Data Type | Nullable | Default | Key | Extra | Business Notes |
|---|---|---|---|---|---|---|---|
| 1 | `Veh_Sub_Type_ID` | `int(11)` | NO | NULL | PRI | `auto_increment` | Primary Key |
| 2 | `Veh_Sub_Type_Name` | `varchar(255)` | YES | NULL | | | Sub-type name (e.g. "Hatchback", "Sedan", "3-Wheeler Auto") |
| 3 | `Veh_Type_ID` | `int(11)` | YES | NULL | MUL | | Logical reference -> `tbl_vehicle_type.Veh_Type_ID` |

- **Indexes**:
  - `PRIMARY` on (`Veh_Sub_Type_ID`) [Unique]
  - `tbl_Vehicle_Type` on (`Veh_Type_ID`) [Non-Unique]

---

## 5. Summary Table Mapping Matrix for Phase 4 Implementation

| Master Entity | Physical Table in MySQL | Primary Key | Column Count | Active Row Count | Verified Active Flag / Filter | Logical Foreign Key in Insured Asset (`tbl_vehicledetails`) |
|---|---|---|---|---|---|---|
| **Vehicle Type** | `tbl_vehicle_type` | `Veh_Type_ID` | 10 | 8 | Active by default (8 rows) | `Veh_Type_ID` |
| **Vehicle Sub-Type** | `tbl_vehicle_sub_type` | `Veh_Sub_Type_ID` | 3 | 65 | Active by default | `Veh_Sub_Type_ID` |
| **Vehicle Make** | `tbl_vehicle_make` | `Make_ID` | 12 | 284 | `isdeleted = 0` | `Make_ID` |
| **Vehicle Model** | `tbl_vehicle_model` | `Model_ID` | 7 | 3,794 | `isdeleted = 0` | `Model_ID` |
| **Vehicle Variant** | `tbl_vehicle_variants` | `Variant_ID` | 91 | 27,983 | `ModelStatus` / `IsObsolete` | `Variant_ID` |
| **RTO Master** | `tbl_rto` | `RTOId` | 10 | 1,367 | `isdeleted = 0` | `RTOId` |
| **Insurance Company** | `tbl_insurancecompany` | `InsuranceCompanyId` | 22 | 37 | `isdeleted = 0 AND LedgerMId <> 0` | `tbl_transaction.InsuranceCompanyId` |

---

## 6. Critical Stop Condition & Next Steps

In strict accordance with the migration safety protocol:
- **Zero code, models, or repositories have been created.**
- **Zero Alembic migrations have been generated.**
- **Zero modifications have been made to `reliable_insurance_dev`.**
- **Phase 4 execution is STOPPED, awaiting review and approval of this verified schema report.**
