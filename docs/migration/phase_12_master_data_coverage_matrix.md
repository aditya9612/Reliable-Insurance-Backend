# Phase 12 — Master Data & Underwriting Lookups Coverage Matrix
## Complete Inventory of Blocks 1, 2, and 3 Master Data Entities

### 1. Architectural Overview
Phase 12 consolidates and verifies all reference and master data dependencies required by the insurance lifecycle engines (Quotation, Rating, Policy Booking, Endorsement, Claims, and Accounting).
- **Physical Schema Parity**: All SQLAlchemy models strictly preserve legacy physical column names (`Veh_Type_ID`, `Veh_Type_Name`, `Make_ID`, `Model_ID`, `Variance`, `RTOId`, `InsuranceCompanyId`, `BranchId`, `StateID`, `DistrictID`, `BankId`).
- **Zero Physical Foreign Keys**: Complies with the core project rule; logical parent-child integrity is maintained purely at the repository and service levels.
- **Regional Pricing Matrix**: Supports the legacy 19-city ex-showroom pricing resolution (`ExMumbai_Model_Price`, `ExNewDelhi_Model_Price`, `ExBangalore_Model_Price`, etc.).

---

### 2. Block 1: 7 Core Vehicle Master Entities

| Entity / Model | Physical Table | PK Column | Total Columns | Parent / Hierarchy Key | Legacy Quirk / Invariant | FastAPI Endpoints |
|---|---|---|---|---|---|---|
| `VehicleType` | `tbl_vehicle_type` | `Veh_Type_ID` | 10 | Root Master | No `isdeleted` column. Active check via existence. Columns: `Comprehensive`, `TP`, `IsAppQuotation`. | `GET /api/v1/masters/vehicle-types`, `GET /{id}` |
| `VehicleSubType` | `tbl_vehicle_sub_type` | `Veh_Sub_Type_ID` | 3 | `Veh_Type_ID` | No `isdeleted` column. Cascades strictly under `Veh_Type_ID`. | `GET /api/v1/masters/vehicle-sub-types`, `GET /{id}` |
| `VehicleMake` | `tbl_vehicle_make` | `Make_ID` | 12 | Root Master | Category flags (`PvtCar`, `TwoWheeler`, `CommercialVehicle`, `PassengerVehicle`, `MiscD`). `isdeleted` is `int`. | `GET /api/v1/masters/makes`, `GET /{id}` |
| `VehicleModel` | `tbl_vehicle_model` | `Model_ID` | 7 | `Make_ID` | Cascades under `Make_ID`. Includes `SegmentId` for rating categorization. `isdeleted` is `int`. | `GET /api/v1/masters/models`, `GET /{id}` |
| `VehicleVariant` | `tbl_vehicle_variants` | `Variant_ID` | 91 | `Model_ID`, `Make_Id` | 91 columns including 57 regional price fields (19 cities × 3 price types: Model, Body, Chassis), CC, GVW, Seating Capacity. | `GET /api/v1/masters/variants`, `GET /{id}`, `GET /{id}/price` |
| `RTOMaster` | `tbl_rto` | `RTOId` | 10 | Root Master | Columns: `REG_code` (e.g. `MH02`), `RTOLocation`, `District`, `zone`, `ClusterId`. `isdeleted` is `int`. | `GET /api/v1/masters/rtos`, `GET /{id}` |
| `InsuranceCompany` | `tbl_insurancecompany` | `InsuranceCompanyId` | 22 | Root Master | Columns: `InsuranceCompany`, `ShortName`, `PolicyNo` (prefix), `len`, `LedgerMId`, `CompImgPath`, `ZeroDeep`, `NCB`. `isdeleted` is `varchar`. | `GET /api/v1/masters/insurance-companies`, `GET /{id}` |

#### 19-City Regional Pricing Resolution
The 19 supported cities for regional ex-showroom price extraction are:
1. Mumbai (`ExMumbai_Model_Price`, `ExMumbai_Body_Price`, `ExMumbai_Chasis_Price`)
2. New Delhi (`ExNewDelhi_Model_Price`, `ExNewDelhi_Body_Price`, `ExNewDelhi_Chasis_Price`)
3. Bangalore (`ExBangalore_Model_Price`, `ExBangalore_Body_Price`, `ExBangalore_Chasis_Price`)
4. Chennai (`ExChennai_Model_Price`, `ExChennai_Body_Price`, `ExChennai_Chasis_Price`)
5. Kolkata (`ExKolkata_Model_Price`, `ExKolkata_Body_Price`, `ExKolkata_Chasis_Price`)
6. Hyderabad (`ExHyderabad_Model_Price`, `ExHyderabad_Body_Price`, `ExHyderabad_Chasis_Price`)
7. Ahmedabad (`ExAhmedabad_Model_Price`, `ExAhmedabad_Body_Price`, `ExAhmedabad_Chasis_Price`)
8. Pune (`ExPune_Model_Price`, `ExPune_Body_Price`, `ExPune_Chasis_Price`)
9. Surat (`ExSurat_Model_Price`, `ExSurat_Body_Price`, `ExSurat_Chasis_Price`)
10. Jaipur (`ExJaipur_Model_Price`, `ExJaipur_Body_Price`, `ExJaipur_Chasis_Price`)
11. Lucknow (`ExLucknow_Model_Price`, `ExLucknow_Body_Price`, `ExLucknow_Chasis_Price`)
12. Kanpur (`ExKanpur_Model_Price`, `ExKanpur_Body_Price`, `ExKanpur_Chasis_Price`)
13. Nagpur (`ExNagpur_Model_Price`, `ExNagpur_Body_Price`, `ExNagpur_Chasis_Price`)
14. Indore (`ExIndore_Model_Price`, `ExIndore_Body_Price`, `ExIndore_Chasis_Price`)
15. Thane (`ExThane_Model_Price`, `ExThane_Body_Price`, `ExThane_Chasis_Price`)
16. Bhopal (`ExBhopal_Model_Price`, `ExBhopal_Body_Price`, `ExBhopal_Chasis_Price`)
17. Visakhapatnam (`ExVisakhapatnam_Model_Price`, `ExVisakhapatnam_Body_Price`, `ExVisakhapatnam_Chasis_Price`)
18. Pimpri (`ExPimpri_Model_Price`, `ExPimpri_Body_Price`, `ExPimpri_Chasis_Price`)
19. Patna (`ExPatna_Model_Price`, `ExPatna_Body_Price`, `ExPatna_Chasis_Price`)

If the queried city has empty or zero pricing, the engine falls back to `ExMumbai_Model_Price` (legacy standard default).

---

### 3. Block 2: Underwriting / Rating Lookups

| Entity / Model | Physical Table | PK Column | Key Fields | Purpose in Rating Sequence | FastAPI Endpoints |
|---|---|---|---|---|---|
| `AddonExtraAmt` | `tbl_addonextraamt` | `AddonExtraAmtId` | `InsuranceCompanyId`, `VehiceTypeId`, `NillDep`, `SecurePlus` | Provides add-on surcharge rates per insurer and vehicle type. | `GET /api/v1/masters/addons`, `GET /{id}` |
| `PAToOwnerDriver` | `tbl_patoownerdriver` | `PAToOwnerDriverId` | `InsuranceCompanyId`, `Rate`, `TowingCharges` | Statutory Personal Accident cover rate (standard ₹375 or ₹350) and towing surcharge. | `GET /api/v1/masters/pa-owner-driver`, `GET /{id}` |
| `InsuranceCompanyWiseTowingChanges` | `tbl_insurancecompanywisetowingchanges` | `id` | `InsuranceCompanyId`, `Rate`, `GST18`, `Total` | Insurer-specific roadside assistance / towing fees with 18% GST calculation. | `GET /api/v1/masters/towing-rates`, `GET /{id}` |
| `NCBSlabs` | Virtual Catalog | N/A | `slab_code`, `slab_percent`, `description` | Statutory 6-tier motor NCB progression: 0%, 20%, 25%, 35%, 45%, 50%. | `GET /api/v1/masters/ncb-slabs` |

---

### 4. Block 3: Organizational & Reference Masters

| Entity / Model | Physical Table | PK Column | Total Columns | Parent / Hierarchy Key | Legacy Quirk / Invariant | FastAPI Endpoints |
|---|---|---|---|---|---|---|
| `Branch` | `tbl_branch` | `BranchId` | 7 | Root Organization | Non-nullable `BranchCode`, `BranchName`. `isdeleted` is `int`. Scoping anchor for all operational rows. | `GET /api/v1/masters/branches`, `GET /{id}` |
| `StateMaster` | `tbl_state` | `StateID` | 3 | Root Geography | Physical PK is `StateID` (capital ID). Columns: `StateName`, `isdeleted`. | `GET /api/v1/masters/states`, `GET /{id}` |
| `DistrictMaster` | `tbl_district` | `DistrictID` | 4 | `StateID` | Physical PK is `DistrictID`. Links to `StateID`. Columns: `DistrictName`, `isdeleted`. | `GET /api/v1/masters/districts`, `GET /{id}` |
| `BankMaster` | `tbl_bank` | `BankId` | 3 | Root Reference | Physical PK is `BankId`. Columns: `BankName`, `isdeleted`. Used by cheque deposit and payment flows. | `GET /api/v1/masters/banks`, `GET /{id}` |

---

### 5. Database Schema Status
- **Alembic Revision**: `c12d0e6f1201_phase_12_organizational_and_reference_tables.py`
- **Total Database Tables**: 52 tables present in development database `reliable_insurance_dev`.
- **Foreign Key Architecture**: Zero physical foreign keys.
- **Migration Path**: Clean upgrade and downgrade tested successfully against `localhost:3306/reliable_insurance_dev`.
