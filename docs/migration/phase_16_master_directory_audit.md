# PHASE 16 — MASTER DIRECTORY AUDIT
## Reliable-Insurance-Backend: Auxiliary Reference Masters (`tbl_fueltype`, `tbl_financier`, `tbl_surveyor`)

---

### 1. Executive Summary & Purpose
During Phase 4B and Phase 12, the primary vehicle masters (`VehicleType`, `VehicleSubType`, `VehicleMake`, `VehicleModel`, `VehicleVariant`), geographical masters (`StateMaster`, `DistrictMaster`, `RTOMaster`), and core financial/branch references (`Branch`, `BankMaster`, `InsuranceCompany`) were successfully migrated.

This audit evaluates the three remaining auxiliary reference tables identified in Phase 15 Stage A:
1. `tbl_fueltype` (Motor Rating & Vehicle Identity Reference)
2. `tbl_financier` (Vehicle Hypothecation & Loan Provider Directory)
3. `tbl_surveyor` (Motor Claims Loss Assessor Directory)

---

### 2. Forensic Analysis of Auxiliary Master Tables

#### 2.1 Vehicle Fuel Type Master (`tbl_fueltype`)
- **Physical Table**: `tbl_fueltype`
- **Primary Key**: `FuelTypeId` (INT, autoincrement)
- **Columns**:
  - `FuelTypeId`: `int(11) NOT NULL AUTO_INCREMENT` (PK)
  - `FuelType`: `varchar(50) NOT NULL` (e.g., `"Petrol"`, `"Diesel"`, `"CNG"`, `"LPG"`, `"Electric"`, `"Hybrid"`)
  - `isdeleted`: `varchar(10) NOT NULL DEFAULT '0'`
  - `CreateDate`: `datetime NULL`
- **Indexes**: Primary key (`FuelTypeId`), active index (`isdeleted`).
- **Active / Deleted Flag**: `isdeleted = '0'` (active), `'1'` (soft-deleted).
- **Legacy Call Sites & Stored Procedures**:
  - `mst_FuelType.aspx.cs`: WebForms administrative UI for listing and adding fuel types.
  - `Sp_SelectQuotationById` / `Sp_SelectQuotationById1`: Joins `tbl_fueltype` to display vehicle fuel on quotation sheets.
  - `PE_TransactionEntry.aspx.cs`: Dropdown binding `ddl_FuelType` on policy entry form.
  - `DAL_Operations.cs:L40988` (`sp_insertclusterwisebrokergrid`): Filters commission by `FuelTypeId`.
- **Downstream Usage**:
  - `tbl_custvehicle.FuelTypeId`: Core vehicle rating parameter determining OD and TP bi-fuel kits (`LBR-032`).
  - Rating Engine (`app/services/quotation.py`): Determines CNG/LPG kit liability surcharge (flat ₹60 TP) and green vehicle rating.
- **Access & Scoping**:
  - **Read Scope**: Universal / Global (all authenticated roles can read).
  - **Write Scope**: Global Admin (`OWNER`, `ADMIN`, `IT SUPPORT`).
- **Modern REST Contract Recommendation**:
  - `GET /api/v1/masters/fuel-types` (Cached read-only dropdown endpoint).
  - Full CRUD is **not required**; a static lookup endpoint satisfies 100% of operational workflows.

#### 2.2 Vehicle Financier / Bank Master (`tbl_financier`)
- **Physical Table**: `tbl_financier`
- **Primary Key**: `FinancierId` (INT, autoincrement)
- **Columns**:
  - `FinancierId`: `int(11) NOT NULL AUTO_INCREMENT` (PK)
  - `FinancierName`: `varchar(255) NOT NULL` (e.g., `"HDFC Bank Ltd"`, `"State Bank of India"`, `"Bajaj Finance"`)
  - `BranchId`: `int(11) NULL` (Associated operational branch)
  - `ContactNo`: `varchar(50) NULL`
  - `EmailId`: `varchar(100) NULL`
  - `Address`: `varchar(255) NULL`
  - `isdeleted`: `varchar(10) NOT NULL DEFAULT '0'`
  - `CreateDate`: `datetime NULL`
- **Indexes**: Primary key (`FinancierId`), branch index (`BranchId`), active index (`isdeleted`).
- **Active / Deleted Flag**: `isdeleted = '0'` (active), `'1'` (soft-deleted).
- **Legacy Call Sites & Stored Procedures**:
  - `mst_Financier.aspx.cs`: WebForms UI for maintaining financier bank directory.
  - `PE_TransactionEntry.aspx.cs` (L1200): Hypothecation bank dropdown binding (`ddl_Financier`).
  - `PolicyTransactionNew.aspx.cs` (L2300): Policy booking hypothecation endorsement storage.
- **Downstream Usage**:
  - `tbl_transaction.FinancierId` (Hypothecation endorsement on Certificate of Insurance).
  - Endorsement Type 8 (`Hypothecation Addition / Deletion`).
- **Access & Scoping**:
  - **Read Scope**: Branch-scoped or Global (operational roles booking policies with loan hypothecation).
  - **Write Scope**: Global Admin (`OWNER`, `ADMIN`) or Location Head.
- **Modern REST Contract Recommendation**:
  - `GET /api/v1/masters/financiers?branch_id=...&search=...`
  - `POST /api/v1/masters/financiers` (Admin only)
  - `PUT /api/v1/masters/financiers/{id}` (Admin only)

#### 2.3 Motor Claims Surveyor Master (`tbl_surveyor`)
- **Physical Table**: `tbl_surveyor`
- **Primary Key**: `SurveyorId` (INT, autoincrement)
- **Columns**:
  - `SurveyorId`: `int(11) NOT NULL AUTO_INCREMENT` (PK)
  - `SurveyorName`: `varchar(100) NOT NULL`
  - `ContactNo`: `varchar(50) NULL`
  - `EmailId`: `varchar(100) NULL`
  - `LicenseNo`: `varchar(50) NULL` (IRDA Claims Surveyor SLA License)
  - `LicenseExpiryDate`: `date NULL`
  - `Address`: `varchar(255) NULL`
  - `City`: `varchar(100) NULL`
  - `StateId`: `int(11) NULL`
  - `BranchId`: `int(11) NULL`
  - `BankId`: `int(11) NULL`
  - `AccountNo`: `varchar(50) NULL`
  - `IFSC_Code`: `varchar(50) NULL`
  - `isdeleted`: `varchar(10) NOT NULL DEFAULT '0'`
  - `CreateDate`: `datetime NULL`
  - `UpdateDate`: `datetime NULL`
- **Indexes**: Primary key (`SurveyorId`), license unique index (`LicenseNo`), branch index (`BranchId`), active index (`isdeleted`).
- **Active / Deleted Flag**: `isdeleted = '0'` (active), `'1'` (soft-deleted).
- **Legacy Call Sites & Stored Procedures**:
  - `mst_Surveyor.aspx.cs`: WebForms directory for independent IRDA licensed claims loss assessors.
  - `CL_ClaimNew.aspx.cs` (L240): Spot and garage surveyor appointment during claim intimation.
  - `DAL_Operations.cs:L27810` (`Sp_GarageSurvey_Operations`): Records garage survey report and appointed surveyor.
  - `DAL_Operations.cs:L27751` (`Sp_Spot_Servey_Operations`): Records spot survey details and appointed surveyor.
  - `SearchMethods.aspx.cs:L22` (`GetSurveyorName`): Migrated in Phase 12 autocomplete (`/api/v1/search/autocomplete?category=surveyor`).
- **Downstream Usage**:
  - `tbl_claims` / `tbl_claimdocument`: Assigned surveyor for assessment report generation and survey fee disbursements.
- **Access & Scoping**:
  - **Read Scope**: Claims executives (`CLAIM`, `CLA`, `INSP CO-ORDINATION`), Branch Managers, Admins.
  - **Write Scope**: Global Admin or Claims Manager.
- **Modern REST Contract Recommendation**:
  - `GET /api/v1/masters/surveyors?branch_id=...&search=...`
  - `GET /api/v1/masters/surveyors/{id}`
  - `POST /api/v1/masters/surveyors` (Admin/Claims Manager)
  - `PUT /api/v1/masters/surveyors/{id}` (Admin/Claims Manager)
  - `DELETE /api/v1/masters/surveyors/{id}` (Soft-delete)

---

### 3. Master Directory Coverage Summary

| Table | Domain | Columns | Current Status | Recommended Action in Phase 16B | Downstream Module Impact |
|---|---|:---:|:---:|---|---|
| `tbl_fueltype` | Motor Rating | 4 | **UNMODELED** | Model `FuelType` + Cache `GET /api/v1/masters/fuel-types` | Quotations, Rating Engine, Vehicle Specs |
| `tbl_financier` | Policy Underwriting | 8 | **UNMODELED** | Model `Financier` + CRUD `GET/POST/PUT /api/v1/masters/financiers` | Policy Booking, Endorsements (Hypothecation) |
| `tbl_surveyor` | Claims Assessment | 16 | **UNMODELED** | Model `Surveyor` + CRUD `GET/POST/PUT/DELETE /api/v1/masters/surveyors` | Claims Intimation, Survey Reports, Inspections |

No other unaccounted-for reference master tables exist in the legacy database schema.
