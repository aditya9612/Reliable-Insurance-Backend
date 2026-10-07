# Phase 7 — Policy Booking & Transaction Engine Final Migration Report

**Repository**: `Reliable-Insurance-Backend`  
**Phase**: `Phase 7 — Policy Booking & Transaction Engine`  
**Status**: `PHASE 7 COMPLETE — VERIFIED PARITY`

---

## 1. Executive Summary
Phase 7 completes the full audit, design, FastAPI implementation, golden parity verification, and end-to-end validation of the legacy **Policy Booking & Transaction Engine**. Every legacy policy booking workflow—including direct operator/underwriter booking (`PE_TransactionEntry.aspx.cs`, `PolicyTransactionNew.aspx.cs`), mobile/web staged proposals (`tbl_transactionappnew`), 3-tier verification gates (Cashier, Accountant, Owner), quotation-to-policy conversion (`tbl_app_quatationentry` and `tbl_app_quotationrequest`), multi-instrument payment collection (`tbl_transactionpayment`), multi-bucket commission + 5% TDS (`tbl_agentcommissionpayment`, `tbl_franchisecommission`), Cut & Pay deductions (`tbl_cutnpaycommpayable`), and double-entry ledger postings (`tbl_account` `AccTransId = 1, 2, 3`)—has been migrated into a single atomic, concurrency-safe, `Decimal`-strict service and REST API layer at `/api/v1/policies`.

## 2. Production Safety Confirmation
- **Database Isolation**: All implementation, schema checks, and automated tests executed exclusively against `localhost:3306/reliable_insurance_dev` (`app/core/config.py` startup validator blocks any connection to `brahmainsurance` or `103.149.199.250`).
- **Zero Production Access**: `0` runtime, migration, or test connections were made to the legacy production database during Stage B, Stage C, or Stage D.
- **Synthetic Data Only**: All unit, integration, golden parity, concurrency, and E2E tests use 100% synthetic test fixtures (`TEST_CUSTOMER_001`, `TEST_VEHICLE_001`, `TEST_QUOTATION_001`, `TEST_POLICY_001`, `G7-01..G7-25`) with zero production PII.

## 3. Legacy Policy Booking Entry Points Audited
| Legacy Entry Point | Legacy Layer | Business Role | FastAPI Target |
|---|---|---|---|
| `Clerk/PE_TransactionEntry.aspx.cs` | ASP.NET WebForms | Primary policy proposal & booking entry, inward no allocation, commission/payment/ledger orchestration | `POST /api/v1/policies/book`, `POST /api/v1/policies/preview` |
| `Clerk/PolicyTransactionNew.aspx.cs` | ASP.NET WebForms | Enhanced booking screen with Self-Quotation (`SELFQUO`) & Assisted Quotation (`QUOTATION`) prefill and update | `POST /api/v1/policies/book`, `PUT /api/v1/policies/{transaction_id}` |
| `Clerk/Check_AppTransactionEntry.aspx.cs` | ASP.NET WebForms | Cashier verification of staged proposals (`IsCheckByCashier = 1`) | `POST /api/v1/policies/proposals/{trans_id}/approve` (`stage="CASHIER"`) |
| `Clerk/Account_Check_AppTransactionEntry.aspx.cs` | ASP.NET WebForms | Accountant verification (`IsCheckByAccountant = 1`) | `POST /api/v1/policies/proposals/{trans_id}/approve` (`stage="ACCOUNTANT"`) |
| `Clerk/Owner_Check_AppTransactionEntry.aspx.cs` | ASP.NET WebForms | Owner / Director verification (`IsCheckByOwner = 1`) | `POST /api/v1/policies/proposals/{trans_id}/approve` (`stage="OWNER"`) |
| `Service.asmx.cs` (`InsertTransactionAppNew`, `GetTransactionDetails`, etc.) | ASMX Web Service | Mobile/Partner staged proposal submission & policy lookup | `POST /api/v1/policies/proposals`, `GET /api/v1/policies` |
| `App_Code/DAL_Operations.cs` | ADO.NET Data Layer | Stored procedure wrapper for transaction, payment, commission, and ledger tables | `PolicyBookingRepository` (`app/repositories/policy_booking.py`) |

## 4. Tables & Columns Mapped
1. **`tbl_transaction` (166 columns, PK: `TransanctionId`)**: Core booked policy ledger preserving exact legacy physical column names (`TransanctionId`, `InwardNo`, `ODPermium`, `TPPermium`, `NetPermium`, `FinalPremium`, `GST`, `NCB`, `NCBAmount`, `ODDiscount`, `ODDisAmount`, `AddOnRate`, `AddOnPermium`, `IsNill`, `PaidAmount`, `OutStandingAmount`, `CutnPay`, `CutnPayAmount`, `TStatus`, `PendingStatus`, `IdempotencyKey`, `QuotationCode`, `AgentId`, `SalesExId`, `FranchiseId`, `BranchId`, `isdeleted`).
2. **`tbl_transactionappnew` (146 columns, PK: `TransId`)**: Staged mobile/web policy proposal table including 3-tier verification flags (`IsCheckByCashier`, `CashierCheckDate`, `IsCheckByAccountant`, `AccountantCheckDate`, `IsCheckByOwner`, `OwnerCheckDate`).
3. **`tbl_transactionpayment` (25 columns, PK: `PaymentId`)**: Split payment instrument rows (`TransanctionId`, `PaymentType`, `PaidAmount`, `DocNo`, `DocDate`, `BankName`, `BankBranch`, `IsPaidToCompany`, `Status`, `isdeleted`).
4. **`tbl_agentcommissionpayment` (26 columns, PK: `CommPayId`)**: Agent commission and TDS payable record (`TransanctionId`, `AgentId`, `ODPremium`, `NetPremium`, `CommAmt`, `TDSPer`, `TDSAmt`, `NetCommAmt`, `PaidAmt`, `BalAmt`, `Status`, `isdeleted`).
5. **`tbl_franchisecommission` (21 columns, PK: `FranchiseCommId`)**: Franchise commission split and company-vs-agent profit margin (`TransanctionId`, `FranchiseId`, `AgentId`, `ODCommPer`, `ODCommAmt`, `NetCommPer`, `NetCommAmt`, `TPCommPer`, `TPCommAmt`, `TotalCommAmt`, `TDSPer`, `TDSAmt`, `NetPayableAmt`, `ProfitMarginAmt`, `isdeleted`).
6. **`tbl_cutnpaycommpayable` (15 columns, PK: `CutnPayId`)**: Cut & Pay upfront commission deduction and residual payable tracking (`TransanctionId`, `AgentId`, `PayableAmount`, `DeductedAmount`, `BalanceAmount`, `Status`, `isdeleted`).
7. **`tbl_account` (17 columns, PK: `AccountId`)**: Double-entry accounting ledger (`TransanctionId`, `AccTransId`, `CustomerId`, `AgentId`, `Amount`, `Narration`, `TransDate`, `BranchId`, `isdeleted`).

## 5. Stored Procedures Mapped
All 26 legacy stored procedures documented in `docs/migration/phase_7_transaction_sp_mapping.md` are mapped to `PolicyBookingRepository` and `PolicyBookingService`:
- **Booking & Update**: `Sp_Transaction_2025`, `Sp_Transaction_2024`, `Sp_UpdateTransaction_2025`, `sp_UpdatePolicyNo`, `sp_DeleteTransactionByTransId`
- **Inward & Duplicate Checks**: `sp_GetMaxInwardNo`, `sp_UpdateInwardNo`, `sp_CheckPolicyNoExist`, `sp_CheckDuplicateTransaction`
- **Quotation Prefill**: `sp_GetSelfQuotationForPolicy`, `sp_GetAppQuotationForPolicy`, `sp_UpdateQuotationPolicyStatus`
- **Staged Proposals & Approvals**: `Sp_InsertTransactionAppNew`, `Sp_UpdateTransactionAppNew`, `sp_GetTransactionAppNewById`, `sp_UpdateCashierCheckStatus`, `sp_UpdateAccountantCheckStatus`, `sp_UpdateOwnerCheckStatus`
- **Payments, Commissions & Ledger**: `sp_InsertTransactionPayment`, `sp_GetPaymentsByTransactionId`, `sp_InsertAgentCommissionPayment`, `sp_InsertFranchiseCommission`, `sp_InsertCutnPayCommPayable`, `sp_InsertAccountEntry`, `sp_ReverseAccountEntriesByTransId`, `sp_SearchPolicyTransactions`

## 6. Quotation-to-Policy Conversion Rules
- **Pathway 1 (`SELF_QUOTATION`)**: Reads `tbl_app_quatationentry` by `QuatationId`. Preserves `AtotalOwnDamPremium` (`ODPermium`), `BtotalLiabilityPremium` (`TPPermium`), `TotalPremium` (`NetPermium`), `GST18` (`GST`), `finalPrmium` (`FinalPremium`), `NoClaimBonus` (`NCBAmount`), `OD` (`ODDisAmount`), and `QuatationCode` (`SRQ...`). Zero double-subtraction of OD discount or NCB.
- **Pathway 2 (`ASSISTED_REQUEST`)**: Reads `tbl_app_quotationrequest` + `tbl_insurancecompanyquotation`, links `QuotationCode` (`QRQ...`), and revalidates underwriting or rating inputs.
- **Pathway 3 (`RATING_ENGINE` / `DIRECT_UNDERWRITING`)**: Executes `RatingEngineService.calculate_premium` or deterministic direct underwriting formula revalidation.

## 7. Premium / NCB / GST Revalidation Rules
- **Strict `Decimal` Arithmetic**: All calculations use `Decimal` with `ROUND_HALF_UP` to `0.01`.
- **Product Type Rules**:
  - `product_type_id == 1` (Package/Comprehensive): Both OD and TP components allowed.
  - `product_type_id == 2` (Liability Only / Act Only): Rejects positive `od_premium`, `ncb_percent`, `ncb_amount`, `od_discount_percent`, or `addon_premium` with `422 Unprocessable Entity`.
  - `product_type_id == 3` (Standalone OD / SAOD): Rejects positive `tp_premium` with `422 Unprocessable Entity`.
- **NCB Eligibility & Slabs**: Valid slabs `{0, 20, 25, 35, 45, 50}%`. Mandatory `0%` when `business_type_id == 1` (New) or `claim_in_previous_policy == True`.
- **Split GCV vs Standard 18% GST**:
  - Standard vehicles (`PVT`, `TW`, `PCV`, `MISC`, etc.): `GST = round_2dp(NetPermium * 18%)`.
  - Goods Carrying Vehicles (`GCV`): `12%` on Basic TP (`basic_tp_premium * 12%`) + `18%` on `(NetPermium - basic_tp_premium)`.
- **Anti-Tamper Gate**: Client-supplied `net_premium`, `gst_amount`, or `final_premium` deviating by more than `±₹1.00` from server-recomputed figures is rejected with `422 Unprocessable Entity`.

## 8. Inward Number Strategy & Concurrency Design
- **Format**: `INW-{BranchId}-{YYYY}-{Seq:06d}` (e.g., `INW-101-2026-000001`).
- **Concurrency Safety**: `PolicyBookingRepository.allocate_inward_no` executes `SELECT InwardNo FROM tbl_transaction WHERE InwardNo LIKE :prefix ORDER BY InwardNo DESC LIMIT 1 FOR UPDATE` inside the active transaction boundary, serializing concurrent allocations per branch/year and preventing burned numbers on rollback.

## 9. Payment Dependency Rules
- **Supported Modes**: `CASH`, `CHEQUE`, `ONLINE`, `NEFT`, `RTGS`, `UPI`, `CREDIT_CARD`, `DEBIT_CARD`, `DD`, `EWALLET`.
- **Instrument Validation**: `CHEQUE` and `DD` require `docno`, `docdate`, and `bankname` (`422` if missing).
- **Cut & Pay Accounting**:
  - Effective settled amount = `TotalPaid + CutnPayAmount`.
  - `OutStandingAmount = FinalPremium - (TotalPaid + CutnPayAmount)`.
  - Overpayment (`TotalPaid + CutnPayAmount > FinalPremium + ₹1.00`) is rejected with `422`.
- **Status Derivation**:
  - `OutStandingAmount == 0.00` $\rightarrow$ `TStatus = "Booked"`, `PendingStatus = 0`.
  - `OutStandingAmount > 0.00` $\rightarrow$ `TStatus = "Pending"`, `PendingStatus = 1`.

## 10. Commission Dependency Rules
- **Multi-Bucket Formula**:
  - `ODCommAmt = round_2dp(ODPermium * ODCommPer / 100)`
  - `NetCommAmt = round_2dp(NetPermium * NetCommPer / 100)`
  - `TPCommAmt = round_2dp(TPPermium * TPCommPer / 100)`
  - `GrossComm = ODCommAmt + NetCommAmt + TPCommAmt + ExtraAmount` (or headline `agent_comm_percent` fallback on `NetPermium`).
- **TDS Deduction**: `TDSAmt = round_2dp(GrossComm * TDSPer / 100)` (default `5.00%`); `NetPayableComm = GrossComm - TDSAmt`.
- **Franchise Profit Margin**: `ProfitMarginAmt = FranchiseGrossComm - GrossComm`.
- **Double-Entry Ledger (`tbl_account`)**:
  - `AccTransId = 1`: Policy Receivable (`+FinalPremium`)
  - `AccTransId = 2`: Payment Receipt (`+PaidAmount`)
  - `AccTransId = 3`: Commission Expense (`-NetPayableComm`, preserving legacy negative sign convention).

## 11. Role / Branch / Principal Access Matrix
| Capability | Authorized Roles | Branch & Principal Enforcement |
|---|---|---|
| **Book / Update Policy** | `POLICY_BOOKING_WRITE_ROLES` (`ADMIN`, `HR ADMIN`, `OPERATOR`, `BACKOFFICE`, ` telecaller`, `CASHIER`, `ACCOUNT`, `MANAGER`, `BRANCH MANAGER`, etc.) | Non-global roles pinned to `user.BranchId` |
| **Create / Update Staged Proposal** | `POLICY_PROPOSAL_WRITE_ROLES` (includes `AGENT`, `BQP`, `SALES EXECUTIVE`, `FRANCHISE`, `SUB FRANCHISE`, plus write roles) | Server-side principal pinning (`agent_id`, `emp_id`, `franchise_id`) |
| **Approve Proposal Stage** | Cashier (`CASHIER`, `ADMIN`, `HR ADMIN`), Accountant (`ACCOUNT`, `ACCOUNTANT`, `ADMIN`, `HR ADMIN`), Owner (`ADMIN`, `HR ADMIN`, `DIRECTOR`, `OWNER`) | Strict stage-specific role check |
| **Record Subsequent Payment** | `POLICY_PAYMENT_WRITE_ROLES` (`CASHIER`, `ACCOUNT`, `ACCOUNTANT`, `OPERATOR`, `ADMIN`, `HR ADMIN`, `BRANCH MANAGER`) | Branch-scoped |
| **Cancel / Soft-Delete Policy** | `POLICY_DELETE_ROLES` (`ADMIN`, `HR ADMIN`, `ACCOUNT`, `BRANCH MANAGER`) | Branch-scoped + reverses `tbl_account` |
| **Read / Search Policies** | `POLICY_BOOKING_READ_ROLES` | Global roles: all branches; Branch staff: `BranchId`; Agent/Sales/Franchise: own principal rows only |

## 12. Atomicity & Idempotency Design
- **Single Atomic Savepoint Boundary**: `PolicyBookingService.book_policy` wraps all writes across `tbl_transaction`, `tbl_transactionpayment`, `tbl_agentcommissionpayment`, `tbl_franchisecommission`, `tbl_cutnpaycommpayable`, `tbl_account`, and `tbl_transactionappnew` inside `async with self.session.begin_nested():`. Any failure at any stage rolls back all 6 tables cleanly and releases the row lock without burning an `InwardNo`.
- **3-Layer Duplicate / Idempotency Protection**:
  1. `idempotency_key`: Checked via `SELECT ... FOR UPDATE` on `tbl_transaction.IdempotencyKey` (`409 Conflict` on duplicate).
  2. `policy_no`: Checked via `SELECT ... FOR UPDATE` on `tbl_transaction.PolicyNo` (`409 Conflict` on active duplicate).
  3. `quotation_code`: Checked via `SELECT ... FOR UPDATE` on `tbl_transaction.QuotationCode` (`409 Conflict` if quotation already converted).

## 13. FastAPI Endpoints Implemented
Mounted under `/api/v1/policies` in `app/api/v1/endpoints/policies.py`:
1. `POST /api/v1/policies/preview` — Dry-run calculation of premiums, GST, commissions, TDS, Cut & Pay, and ledger entries (`200 OK`).
2. `POST /api/v1/policies/book` — Atomic 6-table policy booking (`201 Created`).
3. `GET /api/v1/policies` — Paginated, role/branch/principal-scoped policy listing & search (`200 OK`).
4. `GET /api/v1/policies/{transaction_id}` — Detailed policy retrieval with payments, commissions, and ledger rows (`200 OK`).
5. `PUT /api/v1/policies/{transaction_id}` — Atomic policy underwriting & financial update (`200 OK`).
6. `DELETE /api/v1/policies/{transaction_id}` — Soft-delete/cancellation with automatic accounting ledger reversal (`200 OK`).
7. `POST /api/v1/policies/{transaction_id}/payments` — Subsequent payment collection & automatic status promotion to `"Booked"` (`201 Created`).
8. `POST /api/v1/policies/proposals` — Create staged proposal in `tbl_transactionappnew` (`201 Created`).
9. `GET /api/v1/policies/proposals` — List staged proposals with approval filter & principal scoping (`200 OK`).
10. `GET /api/v1/policies/proposals/{trans_id}` — Retrieve staged proposal detail (`200 OK`).
11. `PUT /api/v1/policies/proposals/{trans_id}` — Update staged proposal (`200 OK`).
12. `POST /api/v1/policies/proposals/{trans_id}/approve` — Cashier / Accountant / Owner 3-tier approval workflow (`200 OK`).

## 14. Files Created
- **Stage A Audit & Design Docs (`9` files)**:
  - `docs/migration/phase_7_policy_booking_legacy_audit.md`
  - `docs/migration/phase_7_transaction_sp_mapping.md`
  - `docs/migration/phase_7_premium_ncb_gst_revalidation.md`
  - `docs/migration/phase_7_inward_number.md`
  - `docs/migration/phase_7_payment_dependencies.md`
  - `docs/migration/phase_7_commission_dependencies.md`
  - `docs/migration/phase_7_policy_access_matrix.md`
  - `docs/migration/phase_7_api_contract.md`
  - `docs/migration/phase_7_atomicity_idempotency.md`
- **Stage B Implementation (`4` files)**:
  - `app/schemas/policy.py`
  - `app/repositories/policy_booking.py`
  - `app/services/policy_booking.py`
  - `app/api/v1/endpoints/policies.py`
- **Stage C & D Tests & Parity Reports (`7` files)**:
  - `tests/unit/test_phase7_policy_calculations.py`
  - `tests/integration/test_phase7_policy_booking_api.py`
  - `tests/integration/test_phase7_atomicity_concurrency.py`
  - `tests/integration/test_phase7_golden_parity.py`
  - `tests/integration/test_phase7_e2e.py`
  - `docs/migration/phase_7_golden_parity.md`
  - `docs/migration/phase_7_final_report.md`

## 15. Files Modified
- `app/core/rbac.py` — Added Phase 7 policy booking, proposal, payment, 3-tier approval, delete, and read role sets and helper predicates.
- `app/api/v1/router.py` — Mounted `policies.router` at `/api/v1/policies`.
- `docs/migration/migration_status.md` — Updated Phase 7 status to `COMPLETED — VERIFIED PARITY`.

## 16. Alembic Migrations Created / Applied
- **None required in Phase 7**: All 6 policy booking, staging, payment, commission, and ledger tables (`tbl_transaction`, `tbl_transactionappnew`, `tbl_transactionpayment`, `tbl_agentcommissionpayment`, `tbl_franchisecommission`, `tbl_cutnpaycommpayable`, `tbl_account`) were already provisioned at Alembic head `7bfd3202dcf7` (`43` physical tables in `reliable_insurance_dev`). Zero schema drift.

## 17. Unit Test Summary
- **File**: `tests/unit/test_phase7_policy_calculations.py`
- **Result**: `8/8 passed` (`100%`)
- **Coverage**: `ROUND_HALF_UP` quantization, standard 18% vs GCV split 12%+18% GST, NCB slab validation, Liability-Only and SAOD mutual exclusion, multi-bucket commission + 5% TDS, franchise profit margin, Cut & Pay balance validation, and double-entry ledger generation (`AccTransId = 1, 2, 3`).

## 18. Integration Test Summary
- **File**: `tests/integration/test_phase7_policy_booking_api.py`
- **Result**: `10/10 passed` (`100%`)
- **Coverage**: `401` unauthenticated rejection, `403` restricted role rejection (`CLAIM`, `pOLICY VIEW`), Agent blocked from direct `/book` (`403`) while permitted on `/proposals` (`201`) with server-side `agent_id` pinning, 3-tier Cashier/Accountant/Owner approval workflow and conversion to `tbl_transaction`, branch isolation (`Branch 101` vs `Branch 102`), principal isolation (`Agent A` vs `Agent B`), subsequent payment settlement (`Pending -> Booked`), and policy cancellation with ledger reversal.

## 19. Atomicity Rollback Test Summary
- **File**: `tests/integration/test_phase7_atomicity_concurrency.py`
- **Result**: `4/4 parameterized failure stages passed` (`AFTER_TRANSACTION_INSERT`, `AFTER_PAYMENT_INSERT`, `AFTER_COMMISSION_INSERT`, `AFTER_LEDGER_INSERT`)
- **Verified Outcome**: Injected failure at every downstream stage leaves `0` orphan rows across all 6 tables (`tbl_transaction`, `tbl_transactionpayment`, `tbl_franchisecommission`, `tbl_agentcommissionpayment`, `tbl_cutnpaycommpayable`, `tbl_account`) and does not burn the branch's `InwardNo` sequence (`#000001` allocated cleanly on the subsequent valid booking).

## 20. Concurrency Test Summary
- **File**: `tests/integration/test_phase7_atomicity_concurrency.py`
- **Result**: `2/2 passed` (`test_concurrent_inward_no_generation_produces_unique_monotonic_numbers` & `test_duplicate_policy_no_idempotency_key_and_quotation_rejected_409`)
- **Verified Outcome**: Concurrent booking requests in the same branch and year produce strictly unique, gap-free monotonic inward numbers (`INW-303-2026-000001` through `INW-303-2026-000005`), and duplicate `policy_no`, `idempotency_key`, or already-converted `quotation_id` are deterministically rejected with `409 Conflict`.

## 21. Golden Parity Test Summary (`25/25` Cases)
- **Files**: `tests/integration/test_phase7_golden_parity.py`, `docs/migration/phase_7_golden_parity.md`
- **Result**: `15/15 test functions passed` covering all `25/25` golden scenarios (`G7-01` through `G7-25`):
  - `G7-01..G7-10`: All vehicle categories (`PVT` Comprehensive/Liability/SAOD, `TW` Comprehensive/Liability, `GCV <=12T`, `GCV >12T`, `PCV 4W`, `PCV 3W`, `MISC-D`)
  - `G7-11..G7-14`: NCB (`0%`, `20%`, `25%`, `35%`, `50%`), Zero-Dep, IMT-23, Towing, RSA, PA Owner/Driver, LL Paid Driver
  - `G7-15..G7-17`: Self-Quotation conversion, Assisted Quotation conversion, Staged Proposal 3-tier approval conversion
  - `G7-18..G7-22`: Multi-bucket commission + 5% TDS, headline commission fallback, Franchise split & profit margin, Cut & Pay full & partial deductions
  - `G7-23..G7-25`: E-Wallet + partial Cash + subsequent settlement, multi-instrument split payment, and policy cancellation with ledger reversal.

## 22. End-to-End Test Summary
- **File**: `tests/integration/test_phase7_e2e.py`
- **Result**: `1/1 passed` (`100%`)
- **Verified Pipeline**:
  1. Created `TEST_CUSTOMER_001` via `POST /api/v1/customers` (`201 Created`).
  2. Created `TEST_VEHICLE_001` (`MH12E2E1001`) via `POST /api/v1/customers/{id}/vehicles` (`201 Created`).
  3. Created `TEST_QUOTATION_001` via `POST /api/v1/quotations/self` (`201 Created`).
  4. Retrieved policy prefill via `GET /api/v1/quotations/self/{id}/policy-prefill` (`200 OK`).
  5. Previewed policy financials via `POST /api/v1/policies/preview` (`200 OK`).
  6. Verified anti-tamper rejection (`422`) when submitting tampered `final_premium`.
  7. Booked `TEST_POLICY_001` atomically via `POST /api/v1/policies/book` (`201 Created`) and verified `tbl_transaction`, `tbl_transactionpayment`, `tbl_agentcommissionpayment`, `tbl_franchisecommission`, and `tbl_account` (`AccTransId = 1, 2, 3`).
  8. Settled remaining balance via `POST /api/v1/policies/{id}/payments` (`201 Created`) and verified automatic promotion from `"Pending"` to `"Booked"`.

## 23. Numerical Discrepancy Summary
- **Maximum Discrepancy Across All 25 Golden Cases (`G7-01..G7-25`)**: `₹0.00` (`Decimal("0.00")`) across `ODPermium`, `TPPermium`, `NetPermium`, `GST`, `FinalPremium`, `CommAmt`, `TDSAmt`, `NetCommAmt`, `ProfitMarginAmt`, `CutnPayAmount`, `PaidAmount`, `OutStandingAmount`, and `tbl_account.Amount`.

## 24. Legacy Defects Discovered & How Handled
1. **Non-Atomic Multi-SP Booking (`PE_TransactionEntry.aspx.cs`)**: Legacy executed 5–7 separate `DAL_Operations` calls without a shared database transaction, leaving orphan rows on partial failure. **Handled**: Wrapped entire 6-table booking flow in a single atomic SQLAlchemy savepoint transaction (`session.begin_nested()`).
2. **Race Condition in `sp_UpdateInwardNo`**: Legacy read `MAX(InwardNo)` without row locking, causing duplicate `InwardNo` under concurrent requests. **Handled**: Replaced with `SELECT ... FOR UPDATE` row-locked sequence allocation inside the transaction boundary.
3. **Client-Side Financial Tampering**: Legacy trusted hidden form fields for `NetPermium`, `GST`, and `FinalPremium`. **Handled**: Added mandatory server-side revalidation with `±₹1.00` rounding tolerance and `422` rejection on tamper.
4. **Missing Server-Side Role & Principal Checks on Proposal/Booking Pages (`GAP-5F-01..05`)**: Legacy relied on UI menu hiding. **Handled**: Enforced `require_roles(...)`, branch scoping, and server-side principal pinning on all 12 endpoints.

## 25. Deferred Items for Phase 8 (Payments) & Phase 9 (Commission/Accounting)
- **Phase 8 (Payments & Cheques)**: Post-booking cheque clearance/bounce state machine (`ChequeBounce`, penalty charges), bulk insurer payment reconciliation, and partner E-Wallet top-up/lock ledger management.
- **Phase 9 (Commission & Accounting)**: Bulk monthly agent/franchise commission payout vouchers, TDS certificate/advice batch generation, and general ledger trial balance / voucher reports.

## 26. Final Status

PHASE 7 COMPLETE — VERIFIED PARITY
