# Phase 0 → Phase 10 Forensic Parity Audit: Database, Schema & Stored Procedure Parity Matrix

**Audit Date**: 2026-10-07  
**Repository**: `Reliable-Insurance-Backend`  
**Primary Baseline Reference**: `docs/migration/03_legacy_database_inventory.md`, `docs/migration/04_legacy_stored_procedure_map.md`  
**Audit Mode**: **READ-ONLY FORENSIC PARITY AUDIT**

---

## 1. Legacy Schema & Persistence Inventory vs New SQLAlchemy ORM

Per `docs/migration/03_legacy_database_inventory.md` and `docs/migration/04_legacy_stored_procedure_map.md`:
- **Legacy `AllMaster.cs` DTO Classes**: 188 `API_*` classes
- **Legacy Inline Raw-SQL Tables**: 36 physical MySQL tables directly queried in C#
- **Legacy Stored Procedures**: 943 unique stored procedures invoked across 2,338 call sites in `DAL_Operations.cs`
- **Legacy Inline Raw SQL Queries**: 124 inline SQL command strings (`19` in `DAL_Operations.cs` + `105` in page code-behind / handlers)
- **New Backend SQLAlchemy 2.0 Models**: 46 ORM model classes across 8 model modules (`app/models/user.py`, `masters.py`, `customer.py`, `vehicle.py`, `quotation.py`, `policy_booking.py`, `payment_engine.py`, `commission_accounting.py`, `claims_endorsement.py`) managed by 7 Alembic migrations (`alembic/versions/0001_baseline_schema.py` through `0007_phase10_claims_endorsement.py`).

---

## 2. Legacy Column Spelling & Typo Compatibility Audit (Section 9)

A critical requirement for shared/migrated MySQL schema compatibility is preserving exact legacy physical column names where `AllMaster.cs` and stored procedures contain historical typos.

| Legacy Field / Column Name | Legacy Table & `AllMaster.cs` Class | New SQLAlchemy Model & Attribute | Physical Column Mapping in `app/models/*` | Status | Evidence |
|---|---|---|---|---|---|
| **`TransanctionId`** *(extra `n`)* | `tbl_paymentdetails` (`API_PaymentDetail`), `tbl_CutAndPayPayment` (`API_CutAndPayPayment`) | `PaymentDetail.transaction_id`, `CutAndPayPayment.transaction_id` | `mapped_column("TransanctionId", Integer, ...)` | `PARITY` | `app/models/payment_engine.py:L32, L104`, `alembic/versions/0005_phase8_payment_engine.py` |
| **`ODPermium`** *(transposed `er`)* | `tbl_transaction` (`API_Transaction`), `tbl_quotationtransaction` (`API_QuotationTransaction`) | `PolicyTransaction.od_premium`, `QuotationTransaction.od_premium` | `mapped_column("ODPermium", Numeric(15, 2), ...)` | `PARITY` | `app/models/policy_booking.py:L58`, `app/models/quotation.py:L92` |
| **`TPPermium`** *(transposed `er`)* | `tbl_transaction` (`API_Transaction`), `tbl_quotationtransaction` (`API_QuotationTransaction`) | `PolicyTransaction.tp_premium`, `QuotationTransaction.tp_premium` | `mapped_column("TPPermium", Numeric(15, 2), ...)` | `PARITY` | `app/models/policy_booking.py:L59`, `app/models/quotation.py:L93` |
| **`NetPermium`** *(transposed `er`)* | `tbl_transaction` (`API_Transaction`), `tbl_quotationtransaction` (`API_QuotationTransaction`) | `PolicyTransaction.net_premium`, `QuotationTransaction.net_premium` | `mapped_column("NetPermium", Numeric(15, 2), ...)` | `PARITY` | `app/models/policy_booking.py:L62`, `app/models/quotation.py:L96` |
| **`NCBPermium`** *(transposed `er`)* | `tbl_transaction` (`API_Transaction`), `tbl_quotationtransaction` (`API_QuotationTransaction`) | `PolicyTransaction.ncb_premium`, `QuotationTransaction.ncb_premium` | `mapped_column("NCBPermium", Numeric(15, 2), ...)` | `PARITY` | `app/models/policy_booking.py:L61`, `app/models/quotation.py:L95` |
| **`finalPrmium`** *(missing `e`, lowercase `f`)* | `tbl_transaction` (`API_Transaction`), `tbl_quotationtransaction` (`API_QuotationTransaction`) | `PolicyTransaction.final_premium`, `QuotationTransaction.final_premium` | `mapped_column("finalPrmium", Numeric(15, 2), ...)` | `PARITY` | `app/models/policy_booking.py:L65`, `app/models/quotation.py:L99` |
| **`QuatationCode`** *(`a` instead of `o`)* | `tbl_quotation` (`API_Quotation`) | `Quotation.quotation_code` | `mapped_column("QuatationCode", String(64), ...)` | `PARITY` | `app/models/quotation.py:L26` |
| **`ChaiseNo`** *(`Chaise` instead of `Chassis`)* | `tbl_custvehicle` (`API_CustomerVehicle`) | `CustomerVehicle.chassis_no` | `mapped_column("ChaiseNo", String(64), ...)` | `PARITY` | `app/models/vehicle.py:L36` |
| **`MoblieNo1`** *(transposed `li`)* | `tbl_customer` (`API_Customer`) | `Customer.mobile_no_1` | `mapped_column("MoblieNo1", String(20), ...)` | `PARITY` | `app/models/customer.py:L25` |
| **`ProfitofNetCommision`** *(single `s`)* | `tbl_transaction` (`API_Transaction`) | `PolicyTransaction.profit_of_net_commission` | `mapped_column("ProfitofNetCommision", Numeric(15, 2), ...)` | `PARITY` | `app/models/policy_booking.py:L91` |
| **`totalCommision`** *(single `s`, lowercase `t`)* | `tbl_transaction` (`API_Transaction`) | `PolicyTransaction.total_commission` | `mapped_column("totalCommision", Numeric(15, 2), ...)` | `PARITY` | `app/models/policy_booking.py:L92` |

---

## 3. Physical Table Parity Matrix (Legacy Tables vs FastAPI SQLAlchemy Models)

| Legacy Table / `API_*` Entity | Legacy Evidence (`03_legacy_database_inventory.md`) | New SQLAlchemy Model & Physical Table | Alembic Migration & Model File | Status |
|---|---|---|---|---|
| `tbl_user` / `API_User` | `Log_In.aspx.cs`, `AllMaster.cs` | `User` (`tbl_user`) | `app/models/user.py`, `0001_baseline_schema.py` | `PARITY` |
| `tbl_role` / `API_Role` | `AllMaster.cs` | `Role` (`tbl_role`) | `app/models/user.py`, `0001_baseline_schema.py` | `PARITY` |
| `tbl_userrights` / `API_UserRights` | `adm_UserRights.aspx.cs`, `AllMaster.cs` | `UserRight` (`tbl_userrights`) | `app/models/user.py`, `0001_baseline_schema.py` | `PARITY` |
| `tbl_loginhistory` / `API_LoginHistory` | `Log_In.aspx.cs`, `AllMaster.cs` | *Not modeled (structured application audit logs used)* | N/A | `MISSING` (`GAP-P5-002`) |
| `tbl_state`, `tbl_city`, `tbl_branch`, `tbl_rto` | `AllMaster.cs`, `DAL_Operations.cs` | `State` (`tbl_state`), `City` (`tbl_city`), `Branch` (`tbl_branch`), `RTO` (`tbl_rto`) | `app/models/masters.py`, `0002_phase5_customer_vehicle_masters.py` | `PARITY` |
| `tbl_insurancecompany`, `tbl_policytype`, `tbl_vehicletype`, `tbl_make`, `tbl_model`, `tbl_addon`, `tbl_bank`, `tbl_financier` | `AllMaster.cs`, `DAL_Operations.cs` | `InsuranceCompany`, `PolicyType`, `VehicleType`, `Make`, `Model`, `AddOnMaster`, `BankMaster`, `FinancierMaster` | `app/models/masters.py`, `0002_phase5_customer_vehicle_masters.py` | `PARITY` |
| `tbl_employee`, `tbl_agent`, `tbl_franchise`, `tbl_subagent`, `tbl_teamleader`, `tbl_salesmanager` | `AllMaster.cs`, `PolicyTransactionNew.aspx.cs` | `Employee` (`tbl_employee`), `Agent` (`tbl_agent`), `Franchise` (`tbl_franchise`), `SubAgent` (`tbl_subagent`) | `app/models/masters.py`, `0002_phase5_customer_vehicle_masters.py` | `PARITY` |
| `tbl_customer` / `API_Customer` | `DAL_Operations.cs` (`sp_InsertCustomer`), `AllMaster.cs` | `Customer` (`tbl_customer`) | `app/models/customer.py`, `0002_phase5_customer_vehicle_masters.py` | `PARITY` |
| `tbl_custvehicle` / `API_CustomerVehicle` | `DAL_Operations.cs` (`sp_InsertCustVehicle`), `AllMaster.cs` | `CustomerVehicle` (`tbl_custvehicle`) | `app/models/vehicle.py`, `0002_phase5_customer_vehicle_masters.py` | `PARITY` |
| `tbl_checkvehicledetails` / `API_CheckVehicleDetails` | `RC_CheckVehicleDtl.aspx.cs` (Signzy cache) | *Not modeled (Deferred to Phase 12)* | N/A | `MISSING` (`GAP-P5-001`) |
| `tbl_quotation` / `API_Quotation` | `Qt_QuotationRequest.aspx.cs`, `AllMaster.cs` | `Quotation` (`tbl_quotation`) | `app/models/quotation.py`, `0003_phase6_quotation_rating.py` | `PARITY` |
| `tbl_quotationtransaction` / `API_QuotationTransaction` | `SelfQuotationRequest.aspx.cs`, `AllMaster.cs` | `QuotationTransaction` (`tbl_quotationtransaction`) | `app/models/quotation.py`, `0003_phase6_quotation_rating.py` | `PARITY` |
| `tbl_tariffmaster` / `API_TariffMaster` | `SelfQuotationRequest*.aspx.cs`, `AllMaster.cs` | `TariffMaster` (`tbl_tariffmaster`) | `app/models/quotation.py`, `0003_phase6_quotation_rating.py` | `PARITY` |
| `tbl_financialyear` / `API_FinancialYear` | `PolicyTransactionNew.aspx.cs`, `AllMaster.cs` | `FinancialYear` (`tbl_financialyear`) | `app/models/policy_booking.py`, `0004_phase7_policy_booking.py` | `PARITY` |
| `tbl_transaction` / `API_Transaction` | `PolicyTransactionNew.aspx.cs`, `PE_TransactionEntry.aspx.cs`, `AllMaster.cs` | `PolicyTransaction` (`tbl_transaction`) | `app/models/policy_booking.py`, `0004_phase7_policy_booking.py` | `PARITY` |
| `tbl_OtherPolicyDetails` / `API_OtherPolicyDetails` | `PolicyTransactionNew.aspx.cs:L1545`, `AllMaster.cs` | `OtherPolicyDetails` (`tbl_OtherPolicyDetails`) | `app/models/policy_booking.py`, `0004_phase7_policy_booking.py` | `PARITY` |
| `tbl_policyaddon` / `API_PolicyAddOn` | `PolicyTransactionNew.aspx.cs`, `AllMaster.cs` | `PolicyAddOn` (`tbl_policyaddon`) | `app/models/policy_booking.py`, `0004_phase7_policy_booking.py` | `PARITY` |
| `tbl_policydocument` / `API_PolicyDocument` | `PolicyTransactionNew.aspx.cs`, `AllMaster.cs` | `PolicyDocument` (`tbl_policydocument`) | `app/models/policy_booking.py`, `0004_phase7_policy_booking.py` | `PARITY` |
| `tbl_paymentdetails` / `API_PaymentDetail` | `PolicyTransactionNew.aspx.cs:L1640`, `AllMaster.cs` | `PaymentDetail` (`tbl_paymentdetails`) | `app/models/payment_engine.py`, `0005_phase8_payment_engine.py` | `PARITY` |
| `tbl_CutAndPayPayment` / `API_CutAndPayPayment` | `PolicyTransactionNew.aspx.cs:L1715`, `AllMaster.cs` | `CutAndPayPayment` (`tbl_CutAndPayPayment`) | `app/models/payment_engine.py`, `0005_phase8_payment_engine.py` | `PARITY` |
| `tbl_unclearchequecharges` / `API_UnclearChequeCharges` | `Adm_UnclearCheque.aspx.cs`, `AllMaster.cs` | `UnclearChequeCharge` (`tbl_unclearchequecharges`) | `app/models/payment_engine.py`, `0005_phase8_payment_engine.py` | `PARITY` |
| `tbl_multipletransactions` & `Sp_SettlementTransaction` | `Adm_SettlementTransaction.aspx.cs`, `AllMaster.cs` | `InsurerReconciliation` (`tbl_reconciliation`) & `MultipleTransaction` (`tbl_multipletransactions`) | `app/models/payment_engine.py`, `0005_phase8_payment_engine.py` | `PARITY` |
| `tbl_franchisewallet` / `API_Wallet` | `Adm_FranchiseWallet.aspx.cs`, `AllMaster.cs` | `WalletAccount` (`tbl_wallet_accounts`), `WalletTopupRequest` (`tbl_franchisewallet`), `WalletTransaction` (`tbl_wallet_transactions`), `WalletLock` (`tbl_wallet_locks`) | `app/models/payment_engine.py`, `0005_phase8_payment_engine.py` | `INTENTIONAL HARDENING` (Adds balance/lock control tables alongside `tbl_franchisewallet`) |
| `tbl_CommissionPercentage` / `API_CommissionPercentage` | `adm_CommissionMaster.aspx.cs`, `AllMaster.cs` | `CommissionPercentage` (`tbl_CommissionPercentage`), `CommissionAccrual` (`tbl_commission_accrual`), `CommissionPayout` (`tbl_commission_payout`), `CommissionPayoutItem` (`tbl_commission_payout_item`) | `app/models/commission_accounting.py`, `0006_phase9_commission_accounting.py` | `INTENTIONAL HARDENING` |
| `tbl_TDSMaster` / `API_TDSMaster` | `AllMaster.cs`, `DAL_Operations.cs` | `TDSMaster` (`tbl_TDSMaster`) | `app/models/commission_accounting.py`, `0006_phase9_commission_accounting.py` | `PARITY` |
| `tbl_LedgerMaster` / `API_LedgerMaster` | `AllMaster.cs`, `09_legacy_commission_accounting_baseline.md` | `LedgerMaster` (`tbl_LedgerMaster`) | `app/models/commission_accounting.py`, `0006_phase9_commission_accounting.py` | `DEVIATION` (`GAP-P10-002` synthetic ledger IDs `1000..2201` vs legacy `1161, 2113, 1930, 1878`) |
| `tbl_account` / `API_Account` | `PolicyTransactionNew.aspx.cs:L1575`, `AllMaster.cs` | `AccountEntry` (`tbl_account`) | `app/models/commission_accounting.py`, `0006_phase9_commission_accounting.py` | `DEVIATION` (`GAP-P10-002` `AccTransId 1..18` vs legacy `1..3`) |
| `tbl_voucher` / `API_Voucher` | `VoucherEntry.aspx.cs`, `AllMaster.cs` | `Voucher` (`tbl_voucher`) | `app/models/commission_accounting.py`, `0006_phase9_commission_accounting.py` | `PARITY` |
| `tbl_claims`, `tbl_claimdocument`, `tbl_surveyor` | `Clerk/CL_ClaimNew.aspx.cs`, `AllMaster.cs` | `Claim` (`tbl_claims`), `ClaimDocument` (`tbl_claimdocument`), `Surveyor` (`tbl_surveyor`) | `app/models/claims_endorsement.py`, `0007_phase10_claims_endorsement.py` | `PARITY` (Core tables) |
| `API_SpotServe`, `API_GarageServe`, `API_ClaimQuotation`, `tbl_claim_quotation_img`, `API_FinalBill`, `tbl_claim_finalbill_doc`, `tbl_claimaudiolist` | `Clerk/CL_ClaimNew.aspx.cs` (`10_legacy_claims_baseline.md` Sec 2) | Consolidated into `Claim` (`tbl_claims`) + `ClaimDocument` (`tbl_claimdocument`); separate garage/quotation/audio sub-tables omitted | `app/models/claims_endorsement.py` | `MISSING` (`GAP-P10-004`) |
| `tbl_endorsement` / `API_Endorsement` | `Endorsment_Request.aspx.cs`, `AppEndorsementforApproval.aspx.cs` | `Endorsement` (`tbl_endorsement`) | `app/models/claims_endorsement.py`, `0007_phase10_claims_endorsement.py` | `PARITY` (Table; note `GAP-P10-003` on 9 vs 22 endorsement types) |
| `tbl_ncbtransaction` / `API_NCBTransaction` | `adm_NcbRecovery.aspx.cs`, `AllMaster.cs` | `NCBTransaction` (`tbl_ncbtransaction`) | `app/models/claims_endorsement.py`, `0007_phase10_claims_endorsement.py` | `PARITY` |
| `tbl_policycancel` / `API_PolicyCancel` | `adm_PolicyCancel.aspx.cs`, `AllMaster.cs` | `PolicyCancellation` (`tbl_policycancel`) | `app/models/claims_endorsement.py`, `0007_phase10_claims_endorsement.py` | `PARITY` |

---

## 4. Stored Procedure & Raw SQL Replacement Audit (Section 10)

| Legacy Persistence Category | Legacy Count (`01_*`, `04_*`) | New Backend Implementation | Forensic Status & Notes |
|---|---|---|---|
| **Authentication & RBAC SPs** (`sp_CheckLogIn`, `Sp_GetSubMenuByRoleId`, `sp_GetUserRights`, etc.) | ~38 SPs | `app/repositories/user.py`, `app/services/auth.py`, `app/core/rbac.py` | `PARITY` for login & RBAC; `MISSING` for `USP_UpdateOTP` & `Sp_InsertLoginHistory` (`GAP-P5-002`). |
| **Customer, Vehicle & Master SPs** (`sp_InsertCustomer`, `sp_UpdateCustomer`, `sp_InsertCustVehicle`, `Sp_AllMasterDetails`, etc.) | ~195 SPs | `app/repositories/customer.py`, `vehicle.py`, `masters.py` | `PARITY` for CRUD & search; `MISSING` for `Sp_InsertCheckVehicleDetails` Signzy cache (`GAP-P5-001`). |
| **Quotation & Rating SPs** (`Sp_InsertQuotation`, `Sp_InsertQuotationTransaction`, `Sp_DeleteQuotationTransaction`, tariff lookups) | ~82 SPs | `app/repositories/quotation.py`, `app/services/rating.py`, `app/services/quotation.py` | `PARITY` on persistence; `DEVIATION` on post-`2025-09-23` GCV 5% TP GST (`GAP-P6-001`) and rounding (`GAP-P6-002`). |
| **Policy Booking & Transaction SPs** (`Sp_InsertTransaction`, `Sp_UpdateTransaction`, `Sp_InsertOtherPolicyDetails`, `sp_FilterAllTransaction`, etc.) | ~210 SPs | `app/repositories/policy_booking.py`, `app/services/policy_booking.py` | `PARITY` on core booking & filtering; `MISSING` on `USP_InsertTellyCallerAchievement`, `USP_UpdateRenewalPolicyStatus`, and health member SPs (`GAP-P7-003`, `GAP-P7-004`). |
| **Payment, Cheque, Recon & Wallet SPs** (`Sp_InsertPaymentDetail`, `Sp_InsertCutAndPayPayment`, `Sp_InsertUnclearChequeCharges`, `Sp_SettlementTransaction`, `Sp_InsertWallet`, `sp_UpdateWalletApproveStatus`) | ~115 SPs | `app/repositories/payment_engine.py`, `app/services/payment_engine.py` | `PARITY` on payment, cheque, recon, and wallet flows; `MISSING` on `Sp_LockChequeClearingCount` (`GAP-P8-001`). |
| **Commission, Accounting, Voucher & Ledger SPs** (`Sp_InsertAccount`, `Sp_InsertVoucher`, `sp_GetFranchiseDataForCommision`, `Sp_GetCommissionPercentage`, etc.) | ~145 SPs | `app/repositories/commission_accounting.py`, `app/services/commission_accounting.py` | `DEVIATION` on `AccTransId` codes (`1..18` vs `1..3`) and system `LedgerMId` values (`GAP-P10-002`). |
| **Claims, Endorsement, NCB Recovery & Cancellation SPs** (`Sp_InsertClaims`, `Sp_Update*ByEndorsment` x22, `Sp_InsertNcbTransaction`, `Sp_UpdateTransByNCB`, `Sp_UpdateTransactionByPolicyCancel`) | ~98 SPs | `app/repositories/claims_endorsement.py`, `app/services/claims_endorsement.py` | `DEVIATION` on `settle_claim` ledger posting (`GAP-P10-001`) and 9 vs 22 endorsement types (`GAP-P10-003`); `MISSING` on claims sub-entity SPs (`GAP-P10-004`). |
| **Reporting, HR/Payroll, Attendance, Target & Utility SPs** (Deferred to Phases 11–15) | ~60 SPs | Deferred to Phases 11–15 | `MISSING` (`GAP-P11-001`). |
| **124 Inline Raw SQL Queries** (`19` in `DAL_Operations.cs` + `105` in `.aspx.cs` / `.ashx.cs`) | 124 queries | Replaced by parameterized SQLAlchemy 2.0 ORM queries in `app/repositories/*` | `LEGACY DEFECT MITIGATED` (`DEF-008` — 100% SQL injection elimination). |
| **Unextracted MySQL Stored Procedure SQL Bodies** | 943 SP bodies | Reconstructed from C# `DAL_Operations.cs` call sites and `DataReader` bindings | `UNKNOWN — EVIDENCE NOT AVAILABLE` (`GAP-UNK-001`). |
