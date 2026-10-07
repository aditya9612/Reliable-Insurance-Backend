# 20 — Consolidated Phase 5 → Phase 10 Legacy Parity Specification

> **Forensic Classification**: `CONFIRMED FROM CODE`  
> **Purpose**: Direct phase-by-phase mapping crafted specifically for auditing the new `Reliable-Insurance-Backend` (FastAPI) implementation against the legacy C#/.NET baseline across **Phase 5 through Phase 10**.

---

## 1. PHASE 5 — Customer + Vehicle + RBAC Baseline

### 1.1 Entities & Legacy Schema Identifiers
- **Customer (`tblcustomer` / `API_Customer`)**:
  - Primary Key: `CustomerId` (`int`)
  - Mandatory/Core Fields: `CustomerName`, `MoblieNo1` (legacy typo in DB/DTO), `MobileNo2`, `EmailId`, `Address`, `PinCode`, `StateId`, `CityId`, `DOB`, `PANNo`, `AadharNo`, `GSTNo`, `CustomerType` (`Individual` / `Corporate`), `CreatedBy`, `BranchId`.
  - Accounting Side-Effect: Creating a customer creates/links a ledger account under `Sundry Debtors` (`tblaccount`).
- **Vehicle (`tblcustvehicle` / `API_Vehicle`)**:
  - Primary Key: `VehicleId` (`int`), Foreign Key: `CustomerId` (`int`)
  - Mandatory/Core Fields: `VehTypeId` (GCV, PCV, Private Car, Two Wheeler, Misc-D), `SubClassId`, `MakeId`, `ModelId`, `VariantId`, `RTOId`, `VehRegNo` (`"NEW"` allowed for unregistered vehicles), `EngineNo`, `ChaiseNo` (legacy typo in DB/DTO), `MfgYear`, `RegDate`, `FuelType`, `CC`, `GVW`, `SeatingCapacity`, `Hypothecation` (`FinancerName`).
  - External Integration: `SignzyVehicleAPI.cs` fetches vehicle master data by `VehRegNo`.
- **RBAC & Organizational Hierarchy**:
  - Roles (`tblrole`): `Admin`, `Branch Manager`, `Accountant`, `Clerk` (Policy Entry / Quotation / Claim), `Telecaller`, `Team Leader`, `Sales Manager`, `Agent` (POS), `Sub-Agent`, `Franchise`.
  - Permission Enforcement: Page-level permissions stored in `tbluserrights` (`View`, `Add`, `Edit`, `Delete`) queried via `USP_SelectUserRightsByUserId`.
  - Branch & Ownership Scoping: `BranchId` isolates branch records; `EmpId` (`TelecallerId`), `TeamLeaderId`, `SalesManagerId`, `AgentId`, `SubAgentId`, and `FranchiseId` track multi-tier hierarchy ownership on every transaction.

---

## 2. PHASE 6 — Quotation + Rating + Premium Calculation Baseline

### 2.1 Rating Formulas by Product Line
1. **Own Damage (Section A)**:
   $$\text{BasicOD} = \text{IDV} \times \frac{\text{ODRate}}{100}$$
   $$\text{ODDiscountAmt} = \text{BasicOD} \times \frac{\text{DiscountRate}}{100}$$
   $$\text{ODAfterDiscount} = \text{BasicOD} - \text{ODDiscountAmt}$$
   - **IMT-23 (GCV / Misc-D)**: $\text{IMT23Amt} = \text{ODAfterDiscount} \times 0.15$ (when IMT-23 is enabled).
   - **Accessories & Bi-Fuel OD**:
     - $\text{ElecAccessoriesOD} = \text{ElecIDV} \times 0.04$
     - $\text{NonElecAccessoriesOD} = \text{NonElecIDV} \times \frac{\text{ODRate}}{100}$
     - $\text{CNGOD} = \text{CNGIDV} \times \frac{\text{ODRate}}{100}$ (or $4\%$)
   - **No Claim Bonus (NCB)**:
     - Allowed Slabs: `0%`, `20%`, `25%`, `35%`, `45%`, `50%`.
     - Applied to $(\text{ODAfterDiscount} + \text{IMT23Amt} + \text{AccessoriesOD})$:
       $$\text{NCBAmt} = (\text{ODAfterDiscount} + \text{IMT23Amt} + \text{AccessoriesOD}) \times \frac{\text{NCBPer}}{100}$$
   - **Add-Ons**:
     - $\text{ZeroDepAmt} = \text{IDV} \times \frac{\text{ZeroDepRate}}{100}$ (added *after* NCB deduction; note **DEF-004** in `SelfQuotationRequest.aspx.cs:L1040` where `ZeroDepPremium` was omitted from GCV `TotalA`).
     - Other Add-ons: `Consumables`, `EngineProtector`, `RTI`, `KeyLock`, `TyreCover`, `RSA`, `NCBProtect`.
   - **Section A Total (`TotalA` / `ODPermium` + `AddonPermium`)**:
     $$\text{TotalA} = (\text{ODAfterDiscount} + \text{IMT23Amt} + \text{AccessoriesOD} - \text{NCBAmt}) + \text{ZeroDepAmt} + \text{OtherAddons}$$

2. **Third-Party / Liability (Section B)**:
   - $\text{BasicTP}$: Flat/slab tariff based on `VehTypeId`, `SubClassId`, and `CC` / `GVW` / `SeatingCapacity`.
   - $\text{CPA}$: Compulsory PA Owner-Driver cover.
   - $\text{LLPaidDriver} = \text{NoOfDrivers} \times \text{LLRate}$ (typically `50` INR per driver).
   - $\text{PAPaidDriver} = \text{NoOfPaidDrivers} \times \text{PARate}$ (note **DEF-005** in `SelfQuotationRequest.aspx.cs:L1064` where `PApaiddriver2` is hardcoded to `0`).
   - $\text{CNGTP} = 60.00$ INR (when Bi-Fuel kit is present).
   - **Section B Total (`TotalB` / `TPPermium`)**:
     $$\text{TotalB} = \text{BasicTP} + \text{CPA} + \text{LLPaidDriver} + \text{PAPaidDriver} + \text{CNGTP} + \text{NFPP}$$

3. **Net Premium, GST & Gross Premium**:
   $$\text{NetPremium} = \text{TotalA} + \text{TotalB}$$
   - **Standard GST (Private Car, Two Wheeler, PCV, Misc-D, Health)**:
     $$\text{GST} = \text{NetPremium} \times 0.18$$
   - **GCV Split GST (Goods Carrying Vehicles)**:
     $$\text{GST} = (\text{BasicTP} \times 0.12) + ((\text{NetPremium} - \text{BasicTP}) \times 0.18)$$
   - **Gross / Final Premium**:
     $$\text{GrossPremium} = \text{Math.Round}(\text{NetPremium} + \text{GST}, 0)$$

---

## 3. PHASE 7 — Policy Booking + Transaction + Inward + Payment & Commission Dependencies

### 3.1 Booking Execution Chain (`PolicyTransactionNew.aspx.cs` & `PE_TransactionEntry.aspx.cs`)
When a policy is booked, the legacy backend executes the following side effects:
1. **Customer Upsert**: `USP_InsertCustomer` / `USP_UpdateCustomer`
2. **Vehicle Upsert**: `USP_InsertCustVehicle` / `USP_UpdateCustVehicle`
3. **Transaction Master Insert**: `USP_InsertTransactionNew` / `USP_InsertTransaction` into `tbltransaction` (storing `ODPermium`, `TPPermium`, `AddonPermium`, `NetPermium`, `GST`, `FinalPermium`, `ComCalOn`, `ComPer`, `ComAmt`, `AgtCalOn`, `AgtPer`, `AgtAmt`, `FRCalOn`, `FRPer`, `FRAmt`, `SubAgtCalOn`, `SubAgtPer`, `SubAgtAmt`, `TStatus = "Pending"`, `FY`).
4. **Payment Split Rows**: Loops over `ViewState["PaymentDetails"]` and calls `USP_InsertTransationDetails` for each payment instrument.
5. **6-Leg Accounting Ledger Posting (`InsertAccount()`)**: Calls `USP_InsertAccountLedgerEntry` 6 times:
   - Customer Account (`Debit = FinalPermium`)
   - Insurance Company Account (`Credit = FinalPermium`)
   - Agent Account (`Credit = AgtAmt`)
   - Franchise Account (`Credit = FRAmt`)
   - Company Commission Account (`Credit = ComAmt`)
   - Sub-Agent Account (`Credit = SubAgtAmt`)
6. **Wallet / Cut-and-Pay Settlement**:
   - If `E-Wallet`: calls `USP_InsertFranchiseEwalletTrans` + `USP_UpdateFranchiseDepositBalance`.
   - If `Cut & Pay`: calls `USP_InsertAgentCutandPayTransaction` + `USP_InsertLedgerDetails`.
7. **Payment Receipt Posting**: Calls `USP_InsertTransactionPayment` + `USP_InsertLedgerDetails`.
8. **Telecaller Target & Renewal Update**: Calls `USP_InsertTellyCallerAchievement` / `USP_UpdateTellyCallerAchievement` and `USP_UpdateRenewalPolicyStatus`.

---

## 4. PHASE 8 — Payments + Cheques + Reconciliation + E-Wallet Baseline

- **Payment Modes**: `Cash`, `Cheque`, `Online`/`NEFT`/`RTGS`/`UPI`, `Card`, `E-Wallet`, `Cut & Pay`.
- **Cheque Clearing & Dishonour (`adm_ChequeReminder.aspx.cs`, `adm_TransactionEntry.aspx.cs`)**:
  - Tracks `ChequeNo`, `ChequeDate`, `BankName`, `ChequeAmt`, `ChequeStatus` (`Pending`, `Cleared`, `Bounced`).
  - Updating cheque status calls `USP_UpdateChequeStatus`.
- **Franchise / POS E-Wallet (`adm_FranchiseDeposit.aspx.cs`, `PolicyTransactionNew.aspx.cs`)**:
  - Deposit top-up requests (`USP_InsertFranchiseDeposit`) require Admin/Accountant approval (`USP_UpdateFranchiseDepositStatus`) before incrementing `tblfranchisedepositbalance`.
  - Policy payment via E-Wallet checks `balance > Convert.ToInt32(txtPaymentAmt.Value)` (note **DEF-009**) and deducts from `tblfranchisedepositbalance`.
- **Cut & Pay (`PolicyTransactionNew.aspx.cs:L1715`)**:
  - Agent/Franchise remits $\text{GrossPremium} - \text{Commission} + \text{TDS}$.

---

## 5. PHASE 9 — Commission + TDS + Cut & Pay + Payout + Ledger + Voucher + Trial Balance

- **Commission Calculation Rules**:
  - Basis `1` (`OD`): $\text{ODPermium} \times \frac{\text{Rate}}{100}$
  - Basis `2` (`Net`): $\text{NetPermium} \times \frac{\text{Rate}}{100}$
  - Basis `3` (`OD+Addon` / `TP`): $(\text{ODPermium} + \text{AddonPermium}) \times \frac{\text{Rate}}{100}$
- **TDS Calculation**:
  - $\text{TDSAmt} = \text{CommissionAmt} \times \frac{\text{TDSPer}}{100}$ (recorded on verification/payout via `USP_InsertAgentCommissionTDS`).
- **Accountant Verification (`adm_TransactionEntry.aspx.cs`)**:
  - Transitions transaction `TStatus` from `"Pending"` to `"Verified"` (`USP_UpdateTransactionVerificationStatus`) and finalizes commission/ledger entries.
- **Vouchers & Double-Entry Ledger (`adm_VoucherEntry.aspx.cs`, `adm_AccountLedger.aspx.cs`, `adm_TrialBalance.aspx.cs`)**:
  - Voucher types: `Receipt`, `Payment`, `Contra`, `Journal`.
  - Every voucher writes balanced Debit and Credit rows into `tblledgerdetails` (`USP_InsertLedgerDetails`) and bill allocations via `USP_InsertVoucherBillDetails`.
  - Running balance = $\text{OpeningBalance} + \sum(\text{Debit} - \text{Credit})$.
  - Trial Balance aggregates total Debits and Credits per account/group via `USP_SelectTrialBalance`.

---

## 6. PHASE 10 — Claims + Endorsements + Policy Modification + Recalculation + Accounting Reversal

- **Claims (`Clerk/CL_ClaimNew.aspx.cs`)**:
  - 3-stage workflow: Intimation (`USP_InsertClaimNew`) $\rightarrow$ Spot Survey (`USP_InsertSpotSurvey`, `~/ClaimPhoto/`) $\rightarrow$ Final Bill & Settlement (`USP_InsertFinalBill`, `~/Claim_Final_Bill_Doc/`).
  - Purely operational tracking; **zero mutation** of `tbltransaction` premiums/commissions and **zero ledger entries**.
- **Endorsements (`Endorsment_Request.aspx.cs`, `AppEndorsementforApproval.aspx.cs`)**:
  - 22 Endorsement Types (`EndorsementId` 1–22).
  - Two-stage workflow: Request (`Status = "Pending"`) $\rightarrow$ Approval (`btnApprove_Click` calls `USP_Update*ByEndorsment` and `USP_UpdateEndorsementStatus` to `"Approved"`).
  - Metadata/attribute updates only (note **DEF-003** where `Convert.ToInt16` overflows at ID > 32,767).
- **NCB Recovery (`adm_NcbRecovery.aspx.cs`)**:
  - Recalculates policy premiums ($\text{NewOD} = \text{OldOD} + \text{NcbRecovAmt}$, $\text{NewNet} = \text{OldNet} + \text{NcbRecovAmt}$, $\text{NewGross} = \text{OldGross} + \text{FinalNormalAmt}$) and recalculates Agent, Franchise (subject to **DEF-001**), and Company commissions.
  - Mutates live policy via `USP_UpdateTransByNCB`, inserts `USP_InsertNcbTransaction` & `USP_InsertNcbTransactionPayment`, and posts accounting entries via `USP_InsertLedgerDetails`.
- **Policy Cancellation (`adm_PolicyCancel.aspx.cs`)**:
  - Marks policy cancelled (`USP_UpdateTransactionByPolicyCancel`), claws back Agent/Franchise/Company commissions, adjusts E-Wallet / Cut-and-Pay balances, and posts reversal ledger entries (`USP_InsertLedgerDetails`).
