# Migration Status & Phase Tracking
## Reliable Assurance Backend Migration (C# .NET 4.0 → FastAPI)

### Overall Status: PHASE 10 COMPLETED — VERIFIED PARITY (AWAITING APPROVAL FOR PHASE 11)

---

## 1. Phase Progression Matrix

| Phase | Description | Status | Verification & Safety Summary |
|---|---|---|---|
| **Phase 0** | Read-Only Verification | **APPROVED (CONDITIONAL)** | Introspected live DB (`brahmainsurance`); cataloged 166-col `tbl_transaction`, `tbl_vehicledetails`, 0 FKs, 1 trigger, 1,855 SP calls vs 1,980 MySQL SPs; documented 90 missing SPs as UNKNOWN. |
| **Phase 1** | FastAPI Foundation | **APPROVED** | Independent local development DB (`reliable_insurance_dev`); async SQLAlchemy 2.0 + aiomysql; local Redis foundation; JWT + dual-mode bcrypt/plaintext verification; X-Request-ID + structured logging + centralized exception handlers; 20/20 automated tests passing; production database completely isolated (REFERENCE ONLY). |
| **Phase 2** | DB Models & Repositories | **APPROVED** | Strict mapping of physical column names (`TransanctionId`, `ODPermium`, `TPPermium`, `NetPermium`, `TStatus`, `CustVehId`, `RegistrationNo`, `ChaiseNo`, `MoblieNo1`, `IsNill`) across 10 tables; 0 physical foreign keys; Alembic migration `b84657b131fa` applied to local `reliable_insurance_dev` with DYNAMIC row format & utf8; 10 async repositories implemented; 36/36 automated tests passing (100%). |
| **Phase 3** | Authentication & RBAC | **APPROVED** | User (`tbl_user`, 13 cols) & Role (`tbl_userrole`, 4 cols) models; Alembic migration `56635abf39f0` applied to local `reliable_insurance_dev`; `UserRepository` & `RoleRepository`; `AuthService` dual-mode bcrypt/plaintext verification with local automatic bcrypt upgrade; `/api/v1/auth/login`, `/me`, and `/admin-check`; `require_roles` RBAC dependency; branch scoping foundation; 52/52 automated tests passing (100%). |
| **Phase 4A**| Read-Only Legacy Production Schema Verification | **COMPLETED** | Read-only live DB introspection of legacy MySQL `brahmainsurance`; resolved schema discrepancies across all 7 master tables (`tbl_vehicle_type` 10 cols, `tbl_vehicle_sub_type` 3 cols, `tbl_vehicle_make` 12 cols, `tbl_vehicle_model` 7 cols, `tbl_vehicle_variants` 91 cols including 57 regional prices, `tbl_rto` 10 cols, `tbl_insurancecompany` 22 cols); 0 modifications to production; report saved to `docs/migration/phase_4_schema_verification.md`. |
| **Phase 4B**| Local Master Schema Implementation | **PASS (FINAL AUDIT)** | 7 verified SQLAlchemy 2.0 models in `app/models/master.py`; 0 physical foreign keys; Alembic migration `cfb1bd63a8ff` applied to local `reliable_insurance_dev` bringing total local tables to 20; 7 async repositories implemented in `app/repositories/master.py`; 16 new tests added; 68/68 automated tests passing (100%); zero connections to legacy production; Final Parity Audit passed with documentation notes (`docs/migration/phase_4b_final_parity_audit.md`). |
| **Phase 4C**| Master Data Services & Caching | *PENDING APPROVAL* | Redis caching layer, master lookup endpoints, pagination, and dropdown APIs. |
| **Phase 5A**| Customer & Vehicle Read-Only Audit | **COMPLETED** | Read-only schema & behavior audit of `tbl_customer` (221k rows, 38 cols) and `tbl_vehicledetails` (213k rows, 32 cols); confirmed `CustomerId` join key, 0 physical FKs; discovered non-unique `RegistrationNo` (scoped strictly to `FinancialYear`); cataloged 561 SP references and C# service methods; report saved to `docs/migration/phase_5a_customer_vehicle_audit.md`. |
| **Phase 5B**| Customer & Vehicle Schema Parity & Repositories | **COMPLETED** | Verified `tbl_customer` 3 secondary indexes (`CustomerCode_UNIQUE` prefix 100, `Fk5_ClientId_idx`, `Fk18_BranchId_idx`); additive Alembic migration `6502a09489d3`; `CustomerRepository` (search by name, branch scoping, non-unique mobile); `VehicleRepository` (search by registration, chassis, customer ID, financial year duplicate check); 17 new tests; 85/85 tests passing (100%); report saved to `docs/migration/phase_5b_customer_vehicle_repository.md`. |
| **Phase 5C**| Customer & Vehicle Legacy CRUD Contract Audit | **COMPLETED (STOPPED)** | Comprehensive evidence-based audit of legacy C# code (`DAL_Operations.cs`, `PolicyTransactionNew.aspx.cs`, `SearchMethods.aspx.cs`, `Service.asmx.cs`) and MySQL routines (`sp_InsertCustomer`, `sp_UpdateCustomer`, `sp_generateCustomerCode`, `Sp_VehicleDetails_2026`, `Sp_UpdateVehicleDetails`, `sp_CheckRegistrationNoNew`, `sp_DeleteCustvehicleDetailsbyCustvehId`); input parameters, defaults, casing transforms, registration uniqueness, atomic transaction gaps documented; report saved to `docs/migration/phase_5c_customer_vehicle_crud_contract.md`. |
| **Phase 5D**| Customers & Vehicles Services & REST APIs | **COMPLETED** | Customer & Vehicle Pydantic schemas (`CustomerCreate`, `CustomerUpdate`, `CustomerResponse`, `VehicleCreate`, `VehicleUpdate`, `VehicleResponse`); `CustomerService` (collision-free `CustomerCode`, uppercase normalization, address fallback); `VehicleService` (`FinancialYear` required, master validation, `sp_CheckRegistrationNo` renewal logic); 4 REST endpoints mounted at `/api/v1/customers`; 22 new tests; 107/107 tests passing (100%); report saved to `docs/migration/phase_5d_customer_vehicle_create_update.md`. |
| **Phase 5E**| Customer Code Historical Parity & Anomaly Audit | **HISTORICAL EXCEPTION — DOCUMENTED** | Read-only historical audit of 221,159 records in `brahmainsurance.tbl_customer`; verified 221,158 records (99.99955%) match `CustomerCode == CustomerId`; investigated single mismatch (`******158`, 0.00045%) down to C# source `PE_TransactionEntry.aspx.cs` abandoned intake and form reset; confirmed FastAPI strategy `CustomerCode = str(CustomerId)` is 100% sound; 107/107 tests green; report in `docs/migration/phase_5e_customer_code_historical_parity.md`. |
| **Phase 5F**| Role → API → Table → CRUD → Branch/Owner Access Audit | **COMPLETED (STOPPED)** | Comprehensive read-only audit of all 56 `tbl_userrole` definitions, 3,818 `tbl_user` distribution, 936 `tbl_role_privilege` menu mappings, 574 `Clerk/*.aspx.cs` pages, and 287 `Service.asmx` WebMethods; proved legacy `Clerk.Master.cs` only hides UI menus with zero server-side URL authorization and zero auth on `Service.asmx`; documented 12 authorization gaps (`GAP-5F-01`..`12`) for Phase 5G; 107/107 tests passing (100%). |
| **Phase 5G**| Customer/Vehicle Role, Branch & Principal Authorization Hardening + Read/Search APIs | **COMPLETED (STOPPED)** | Centralized verified 56-role catalog in `app/core/rbac.py`; removed phantom `SUPERADMIN` and `BranchId in (0, None)` admin assumptions (`GAP-5F-02`); enforced active-role check rejecting `role.isdeleted == '1'` (`GAP-5F-04`); resolved server-side `agent_id`, `emp_id`, `employee_id`, `franchise_id` principal context (`GAP-5F-03`); enforced `require_roles(*CUSTOMER_VEHICLE_WRITE_ROLES)` on Customer/Vehicle write APIs (`GAP-5F-01`); implemented authenticated branch-scoped `GET /api/v1/customers`, `GET /api/v1/customers/{id}`, `GET /api/v1/customers/{id}/vehicles`, and `GET /api/v1/vehicles` (`GAP-5F-09`); 25 new tests added; 132/132 tests passing (100%); report in `docs/migration/phase_5g_customer_vehicle_authorization.md`. |
| **Phase 6** | Quotation & Rating Engine | **COMPLETED (STOPPED)** | Stage A audit & design (`6` markdown specs) + Stage B implementation: 23 SQLAlchemy 2.0 models in `app/models/quotation.py`; Alembic migration `7bfd3202dcf7` applied to local `reliable_insurance_dev` (43 total tables); `QuotationRepository`, `RatingEngineService` (`Decimal`-only across all 9 vehicle categories, `±15%` IDV band, GVW > 12000 loading, IMT-23 15%, Own Premises 33%, Anti-Theft cap, Reliance 90% OD discount cap, NCB slabs, Zero-Dep/Towing, split GCV GST), `QuotationService` (Self-Quotation `SRQ...` + Assisted Request lifecycle + Phase 7 policy prefill), 15 REST endpoints at `/api/v1/quotations`; 33 new tests added; 165/165 tests passing (100%). |
| **Phase 7** | Policy & Transaction Booking | **COMPLETED — VERIFIED PARITY (STOPPED)** | Stage A audit & design (`9` markdown specs) + Stage B implementation (`PolicyBookingRepository`, `PolicyBookingService`, `app/schemas/policy.py`, 11 REST endpoints at `/api/v1/policies`, row-locked `INW-{BranchId}-{YYYY}-{Seq:06d}` inward number allocation, atomic 6-table booking & rollback, 3-pathway premium/NCB/GST revalidation, multi-bucket commission + 5% TDS, Cut & Pay, double-entry ledger `AccTransId=1,2,3`, 3-tier staged proposal workflow) + Stage C verification: 25/25 golden parity cases (`0.00` discrepancy), full E2E pipeline (`Customer -> Vehicle -> Quotation -> Policy Booking`), 40 new tests added; 205/205 total tests passing (100%). |
| **Phase 8** | Payments, Cheques & Reconciliation Engine | **COMPLETED — VERIFIED PARITY (STOPPED)** | Stage A audit & design (`10` markdown specs) + Stage B implementation (`PaymentEngineRepository`, `PaymentEngineService`, `WalletService`, `app/schemas/payment.py`, 16 REST endpoints across `/api/v1/payments`, `/api/v1/reconciliation`, `/api/v1/wallets`, and `/api/v1/policies/{id}/payments`, 12 payment modes, cheque deposit/clear/bounce/penalty lifecycle, commission hold on bounce, payment reversal & E-Wallet refund, insurer brokerage reconciliation `AccTransId=5`, concurrency-safe E-Wallet top-up/lock/release/debit `AccTransId=10..14`) + Stage C verification: 25/25 golden parity cases (`0.00` discrepancy), 100 concurrent wallet operations (`0` negative balances), full cross-phase E2E journey, 38 new tests added; 243/243 total tests passing (100%). |
| **Phase 9** | Commission & Accounting Engine | **COMPLETED — VERIFIED PARITY (STOPPED)** | Stage A audit & design (`13` markdown specs) + Stage B implementation (`CommissionAccountingRepository`, `CommissionAccountingService`, `app/schemas/commission_accounting.py`, 19 REST endpoints across `/api/v1/commissions`, `/api/v1/commission-payouts`, and `/api/v1/accounting`, multi-bucket Agent & Franchise commission + TDS + overriding `ProfitofNetCommision` spread, Cut & Pay, 6-gate payout eligibility, approval `PaymentStatus=3.00`, atomic commission payouts `AccTransId=6` & reversals `AccTransId=7`, Chart of Accounts `tbl_ledgermaster`, running-balance ledger statements, double-entry vouchers `AccTransId=8,9`, and zero-variance Trial Balance) + Stage C verification: 30/30 golden parity cases (`0.00` discrepancy), 100 concurrent commission payouts (`0` over-disbursements), full cross-phase E2E journey, 32 new tests added; 275/275 total tests passing (100%). |
| **Phase 10**| Claims & Endorsements Engine | **COMPLETED — VERIFIED PARITY (STOPPED)** | Stage A audit & design (`16` markdown specs) + Stage B implementation (`Claim` `tbl_claims`, `ClaimDocument` `tbl_claimdocument`, `PolicyEndorsement` `tbl_appendorsement`, Alembic migration `a10c1a1m5001`, `ClaimsEndorsementRepository`, `ClaimsEndorsementService`, `app/schemas/claims_endorsement.py`, 19 REST endpoints across `/api/v1/claims`, `/api/v1/endorsements`, and `/api/v1/refunds`, 9-state claim lifecycle + surveyor/assessment/IDV cap + `CUSTOMER`/`GARAGE`/`BOTH` settlement `AccTransId=18`, 9 endorsement types + `UpdateEntryStatus` sync + premium/GST/NCB recalculation `AccTransId=15` + commission adjustment/recovery `AccTransId=16` + refund approval `AccTransId=17`) + Stage C verification: 21/21 golden parity cases (`CL10-01`..`CL10-10`, `EN10-01`..`EN10-11`, `0.00` discrepancy), atomic fault-injection rollback, concurrent race protection, full Phases 5→10 E2E journey, 14 new test suites added; 289/289 total tests passing (100%). |
| **Phase 11**| Documents & Storage | *PENDING* | S3 / MinIO presigned uploads/downloads, dynamic multi-file ZIP streaming. |
| **Phase 12**| External Integrations | *PENDING* | Signzy, Attestr, HiCaliber OCR, SMS gateways (Fast2SMS, IndiaText). |
| **Phase 13**| Background Jobs | *PENDING* | Celery / Celery Beat daily renewal notices, birthday wishes, temporary image cleanup. |
| **Phase 14**| Reporting & Exports | *PENDING* | Transaction logs, POSP invoices, TDS advice, OpenXML/Excel and PDF generation. |
| **Phase 15**| Compatibility Adapters | *PENDING* | ASMX request/response adapters for mobile app clients. |
| **Phase 16**| Full Parity Testing | *PENDING* | End-to-end golden dataset comparisons between legacy and FastAPI. |
| **Phase 17**| Dual-Run Verification | *PENDING* | Live side-by-side traffic validation against shared database. |
| **Phase 18**| Production Cutover | *PENDING* | Cutover mobile and API traffic to FastAPI. |

---

## 2. Environment Architecture & Database Isolation Policy

```
[Legacy Production Infrastructure]
Database: brahmainsurance (Remote Legacy Reference Server)
Role: REFERENCE & AUDIT ONLY
Status: READ-ONLY ACCESS STRICTLY LIMITED TO AUDIT PHASES (Phase 0, Phase 4A, Phase 5A, Phase 5E, Phase 5F, Phase 6 Stage A complete)
Rules: No writes, no schema modifications, no Alembic migrations, no runtime connections

[New FastAPI Backend Infrastructure]
Database: reliable_insurance_dev on localhost:3306 (MySQL 8.0)
Role: RUNTIME DEVELOPMENT DATABASE
Status: ACTIVE & VERIFIED (46 tables present, Alembic head a10c1a1m5001)
Cache: Redis on localhost:6379/0
Rules: Complete autonomy; independent local development schema
Safety Guard: Enforced validator in app.core.config rejects any production IP or DB name
```

---

## 3. Key Verification Records Preserved
- `docs/migration/phase_0_verification.md`: Complete audit findings, physical column discrepancies, stored procedure inventory.
- `docs/migration/phase_1_foundation.md`: Phase 1 implementation details, safety checks, test results.
- `docs/migration/database_mapping.md`: Phase 2 physical database mapping, PKs, column naming quirks, logical relationships.
- `docs/migration/repository_mapping.md`: Phase 2 repository architecture, data access operations, models covered.
- `docs/migration/phase_2_models_repositories.md`: Phase 2 completion report, migration history, test results.
- `docs/migration/phase_3_auth_rbac.md`: Phase 3 completion report, auth architecture, RBAC, password migration.
- `docs/migration/phase_4_schema_verification.md`: Phase 4A read-only live schema verification report.
- `docs/migration/phase_4b_master_models.md`: Phase 4B master models, Alembic migration, repositories, and test verification report.
- `docs/migration/phase_4b_final_parity_audit.md`: Phase 4B final parity, safety & regression audit report.
- `docs/migration/phase_5a_customer_vehicle_audit.md`: Phase 5A customer & vehicle read-only legacy schema and behavior audit report.
- `docs/migration/phase_5b_customer_vehicle_repository.md`: Phase 5B customer & vehicle schema parity and repository foundation report.
- `docs/migration/phase_5c_customer_vehicle_crud_contract.md`: Phase 5C customer & vehicle legacy CRUD contract audit report.
- `docs/migration/phase_5d_customer_vehicle_create_update.md`: Phase 5D customer & vehicle create/update services and REST API report.
- `docs/migration/phase_5d_post_implementation_parity_review.md`: Phase 5D post-implementation parity review (CustomerCode, registration validation, master integrity).
- `docs/migration/phase_5e_customer_code_historical_parity.md`: Phase 5E / 5E-Final customer code historical parity & single-mismatch investigation report.
- `docs/migration/phase_5f_role_api_table_access_matrix.md`: Phase 5F complete Role → API → Table → CRUD → Branch/Owner access matrix.
- `docs/migration/phase_5f_role_summary.md`: Phase 5F per-role capability, scope, and financial authority profiles.
- `docs/migration/phase_5f_authorization_gap_register.md`: Phase 5F legacy & FastAPI authorization gap register (`GAP-5F-01` through `GAP-5F-12`).
- `docs/migration/phase_5g_customer_vehicle_authorization.md`: Phase 5G Customer/Vehicle role, branch & principal authorization hardening + read/search APIs report.
- `docs/migration/phase_6_quotation_legacy_audit.md`: Phase 6 Stage A legacy quotation & rating entry points, physical table schemas, and lifecycle audit.
- `docs/migration/phase_6_quotation_sp_mapping.md`: Phase 6 Stage A complete mapping of 35+ quotation & rating stored procedures.
- `docs/migration/phase_6_premium_calculation_sequence.md`: Phase 6 Stage A 9-step deterministic motor rating sequence and formulas.
- `docs/migration/phase_6_quotation_access_matrix.md`: Phase 6 Stage A role, branch, and principal ownership matrix for quotation & rating flows.
- `docs/migration/phase_6_rating_rules.md`: Phase 6 Stage A statutory & business rating rules catalog.
- `docs/migration/phase_6_api_contract.md`: Phase 6 Stage A FastAPI REST API contract specification for `/api/v1/quotations`.
- `docs/migration/phase_6_parity_results.md`: Phase 6 Stage B golden parity test matrix (`0.00` discrepancy across all 9 vehicle categories) and verification report.
- `docs/migration/phase_7_policy_booking_legacy_audit.md`: Phase 7 Stage A legacy policy booking entry points, 6 physical tables, and workflow audit.
- `docs/migration/phase_7_transaction_sp_mapping.md`: Phase 7 Stage A complete mapping of 26 transaction, proposal, payment, commission, and ledger stored procedures.
- `docs/migration/phase_7_premium_ncb_gst_revalidation.md`: Phase 7 Stage A server-side premium, OD discount, NCB, add-on, and split GCV vs standard 18% GST revalidation specification.
- `docs/migration/phase_7_inward_number.md`: Phase 7 Stage A inward number generation & concurrency-safe row-locking specification (`INW-{BranchId}-{YYYY}-{Seq:06d}`).
- `docs/migration/phase_7_payment_dependencies.md`: Phase 7 Stage A payment collection modes, Cut & Pay deduction, and status transition specification.
- `docs/migration/phase_7_commission_dependencies.md`: Phase 7 Stage A multi-bucket commission, 5% TDS, franchise profit margin, and Cut & Pay payable specification.
- `docs/migration/phase_7_policy_access_matrix.md`: Phase 7 Stage A role, branch, and principal ownership matrix across all 56 roles.
- `docs/migration/phase_7_api_contract.md`: Phase 7 Stage A FastAPI REST API contract specification for `/api/v1/policies`.
- `docs/migration/phase_7_atomicity_idempotency.md`: Phase 7 Stage A atomic 6-table transaction boundary, rollback, and 3-layer idempotency specification.
- `docs/migration/phase_7_golden_parity.md`: Phase 7 Stage C golden parity test specification and `25/25` (`0.00` discrepancy) verification report.
- `docs/migration/phase_7_final_report.md`: Phase 7 Stage D final migration report.
- `docs/migration/phase_8_payment_legacy_audit.md`: Phase 8 Stage A legacy payment, cheque, bounce, reconciliation, and wallet audit report.
- `docs/migration/phase_8_payment_sp_mapping.md`: Phase 8 Stage A complete mapping of 22 payment, cheque, reconciliation, and wallet stored procedures.
- `docs/migration/phase_8_payment_state_machine.md`: Phase 8 Stage A payment instrument, policy status, and wallet lock state machine specification.
- `docs/migration/phase_8_cheque_lifecycle.md`: Phase 8 Stage A cheque & DD receipt, bank deposit, and clearance lifecycle specification.
- `docs/migration/phase_8_cheque_bounce.md`: Phase 8 Stage A cheque dishonor/bounce, penalty assessment, policy reopening, and commission hold specification.
- `docs/migration/phase_8_reconciliation.md`: Phase 8 Stage A insurer payment & brokerage statement reconciliation specification.
- `docs/migration/phase_8_wallet.md`: Phase 8 Stage A partner E-Wallet sub-ledger, top-up, lock/release, debit, and refund specification.
- `docs/migration/phase_8_payment_access_matrix.md`: Phase 8 Stage A role, branch, and principal ownership matrix across all 56 roles.
- `docs/migration/phase_8_api_contract.md`: Phase 8 Stage A FastAPI REST API contract for `/api/v1/payments`, `/api/v1/reconciliation`, and `/api/v1/wallets`.
- `docs/migration/phase_8_atomicity_idempotency.md`: Phase 8 Stage A single unit-of-work atomicity, rollback, row-locking, and idempotency specification.
- `docs/migration/phase_8_golden_parity.md`: Phase 8 Stage C golden parity test matrix (`P8-01` .. `P8-25`, `0.00` discrepancy) and verification report.
- `docs/migration/phase_8_final_report.md`: Phase 8 Stage D final migration report.
- `docs/migration/phase_9_commission_legacy_audit.md`: Phase 9 Stage A legacy commission, TDS, Cut & Pay, payout, voucher, and accounting audit report.
- `docs/migration/phase_9_commission_sp_mapping.md`: Phase 9 Stage A complete mapping of commission, payout, ledger, voucher, and trial balance stored procedures.
- `docs/migration/phase_9_commission_state_machine.md`: Phase 9 Stage A commission payable, approval, partial/full payout, hold, and reversal state machine specification.
- `docs/migration/phase_9_agent_commission_and_tds.md`: Phase 9 Stage A multi-bucket (`OD`, `Net`, `Extra`) Agent commission and TDS formula specification.
- `docs/migration/phase_9_franchise_commission.md`: Phase 9 Stage A Franchise overriding commission and `ProfitofNetCommision` spread specification.
- `docs/migration/phase_9_cut_and_pay.md`: Phase 9 Stage A Cut & Pay upfront commission deduction and hold/release specification.
- `docs/migration/phase_9_commission_payout_and_reversal.md`: Phase 9 Stage A 6-gate commission payout eligibility, atomic disbursement (`AccTransId=6`), and contra reversal (`AccTransId=7`) specification.
- `docs/migration/phase_9_accounting_ledger_and_trial_balance.md`: Phase 9 Stage A Chart of Accounts (`tbl_ledgermaster`), running-balance ledger statements, and zero-variance Trial Balance specification.
- `docs/migration/phase_9_vouchers.md`: Phase 9 Stage A double-entry journal/payment/receipt/contra voucher (`AccTransId=8`) and voucher reversal (`AccTransId=9`) specification.
- `docs/migration/phase_9_access_matrix.md`: Phase 9 Stage A role, branch, and principal ownership access matrix across all 56 roles.
- `docs/migration/phase_9_api_contract.md`: Phase 9 Stage A FastAPI REST API contract for `/api/v1/commissions`, `/api/v1/commission-payouts`, and `/api/v1/accounting`.
- `docs/migration/phase_9_atomicity_idempotency_concurrency.md`: Phase 9 Stage A single unit-of-work atomicity, rollback, idempotency, and concurrency specification.
- `docs/migration/phase_9_golden_parity.md`: Phase 9 Stage C golden parity test matrix (`C9-01` .. `C9-30`, `0.00` discrepancy) and verification report.
- `docs/migration/phase_9_final_report.md`: Phase 9 Stage D final migration report.
- `docs/migration/phase_10_claims_legacy_audit.md`: Phase 10 Stage A legacy claims entry points, tables (`tbl_claims`, `tbl_claimdocument`), and workflow audit.
- `docs/migration/phase_10_claim_sp_mapping.md`: Phase 10 Stage A complete mapping of 11 claim stored procedures.
- `docs/migration/phase_10_claim_state_machine.md`: Phase 10 Stage A 9-state claim lifecycle state machine specification.
- `docs/migration/phase_10_claim_settlement.md`: Phase 10 Stage A claim loss assessment, IDV cap, and `CUSTOMER`/`GARAGE`/`BOTH` settlement (`AccTransId=18`) specification.
- `docs/migration/phase_10_endorsement_legacy_audit.md`: Phase 10 Stage A legacy endorsement & policy correction (`UpdateEntry`) entry points and `tbl_appendorsement` audit.
- `docs/migration/phase_10_endorsement_sp_mapping.md`: Phase 10 Stage A complete mapping of 10 endorsement and policy modification stored procedures.
- `docs/migration/phase_10_endorsement_state_machine.md`: Phase 10 Stage A 5-state endorsement lifecycle and `UpdateEntryStatus` synchronization specification.
- `docs/migration/phase_10_policy_modification.md`: Phase 10 Stage A per-type field allowlists, immutable guards, and before/after snapshot specification.
- `docs/migration/phase_10_premium_recalculation.md`: Phase 10 Stage A server-side endorsement premium, NCB, and GST delta recalculation specification.
- `docs/migration/phase_10_commission_adjustment.md`: Phase 10 Stage A endorsement Agent/Franchise commission delta and paid-commission recovery (`AccTransId=16`) specification.
- `docs/migration/phase_10_payment_refund_impact.md`: Phase 10 Stage A endorsement additional receivable (`AccTransId=15`) and excess refund approval (`AccTransId=17`) specification.
- `docs/migration/phase_10_accounting_adjustment.md`: Phase 10 Stage A double-entry accounting rules (`AccTransId=15,16,17,18`) and Trial Balance integration specification.
- `docs/migration/phase_10_access_matrix.md`: Phase 10 Stage A role, branch, and principal ownership matrix across all 56 roles.
- `docs/migration/phase_10_api_contract.md`: Phase 10 Stage A FastAPI REST API contract for `/api/v1/claims`, `/api/v1/endorsements`, and `/api/v1/refunds`.
- `docs/migration/phase_10_atomicity_idempotency.md`: Phase 10 Stage A single unit-of-work atomicity, rollback, row-locking, and idempotency specification.
- `docs/migration/phase_10_golden_parity.md`: Phase 10 Stage C golden parity test matrix (`CL10-01`..`CL10-10`, `EN10-01`..`EN10-11`, `0.00` discrepancy) and verification report.
- `docs/migration/phase_10_final_report.md`: Phase 10 Stage D final migration report.
