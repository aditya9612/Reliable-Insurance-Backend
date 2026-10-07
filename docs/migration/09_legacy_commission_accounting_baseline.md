# 09 — Legacy Commission, TDS, Cut & Pay, Ledger, Voucher & Trial Balance Baseline (Phase 9)

> **Audit Status**: CONFIRMED FROM CODE
> **Primary Evidence**:
> - `Insurance\Clerk\PolicyTransactionNew.aspx.cs` (Lines 1022–1107, 1319–1765, 1788–1950)
> - `Insurance\Clerk\PE_TransactionEntry.aspx.cs` (Lines 9580–10140)
> - `Insurance\Clerk\adm_tdsForAgent.aspx.cs` (Lines 240–285)
> - `Insurance\Clerk\adm_tdsrateforBroker.aspx.cs` (Lines 75–115)
> - `Insurance\Clerk\adm_NonMotarTransaction.aspx.cs` (Line 604)
> - `Insurance\AppPolicyRequestNew1_2026.aspx.cs` (Lines 2170–2180, 5930–5940)
> - `Insurance\Clerk\AgentCommissionRecalculation.aspx.cs` (Lines 4750–4885)
> - `Insurance\Clerk\AgentCommissionRecalculationRS_Date.aspx.cs` (Lines 3685–3815)
> - `Insurance\Clerk\adm_VoucherEntry.aspx.cs` (Lines 270–310)
> - `Insurance\Clerk\adm_NcbRecovery.aspx.cs` (Lines 840–1015)

---

## 1. Three-Tier Commission Hierarchy (RA / Franchise / Agent / Sales Executive)

In the legacy system, every policy transaction computes up to **three parallel commission structures**:

| Tier | Grid / Entity | Entity ID Convention | Commission Table / Model | Profit Calculation Formula |
| :--- | :--- | :--- | :--- | :--- |
| **Tier 1: Reliable Associates (Company / Co-Broker Receivable)** | `GridFillData_RA` | `FranchiseId = 1` (`"RA"` / `"BROKER"`) | `API_franchaiseCommission` (`comm1.FranchiseId = 1`) |- If Agent business (`ddl_Reference.SelectedIndex == 1`):<br>$\text{ProfitComm1} = \text{Math.Round}(\text{Cacl\_NetComm\_RA} - \text{Cacl\_NetComm}, 0)$<br>- Else (Franchise/Direct):<br>$\text{ProfitComm1} = \text{Math.Round}(\text{Cacl\_NetComm\_RA} - \text{Cacl\_NetComm\_Fr}, 0)$<br>*(Confirmed at `PolicyTransactionNew.aspx.cs` L1584–1596)* |
| **Tier 2: Sub-Franchise Payable** | `GridFillData_Fr` | `hdn_FranchiseId != "1"` (`"FRANCHISE"`) | `API_franchaiseCommission` (`comm.FranchiseId = franchaiseId`) | $\text{ProfitComm} = \text{Math.Round}(\text{Cacl\_NetComm\_Fr} - \text{Cacl\_NetComm}, 0)$<br>*(Confirmed at `PolicyTransactionNew.aspx.cs` L1513–1514)* |
| **Tier 3: Agent / POSP / Sales Executive Payable** | `GridFillData` | `AgentId` or `SalesEx_id` | Stored directly on `API_Transaction` (`AgentComm*`, `TdsAmt*`, `NetCommission*`) and `API_AgentCommPayment` | Agent Net Commission = Gross Commission - TDS across all 4 basis components (`TP`, `TP Extra`, `OD`, `Net`). |

---

## 2. Four Commission Calculation Bases (`lblCommissionOn` / `CalcOn`)

**Evidence**: `PolicyTransactionNew.aspx.cs` (Lines 1068–1105, 1469–1509, 1539–1579), `adm_NcbRecovery.aspx.cs` (Lines 276–320)

Commission grids return rates for up to **4 premium bases**, which are stored in separate column groups on `API_Transaction` and `API_franchaiseCommission`:

| Basis Code (`CalcOn` / `AgtCalOn`) | Grid Label (`lblCommissionOn`) | Premium Base Multiplied | `API_Transaction` Fields | `API_franchaiseCommission` Fields |
| :--- | :--- | :--- | :--- | :--- |
| `"1"` | `"TP Premium"` | `TPPermium` (`txt_TPPremium`) | `AgentComm`, `AgentCommAmt`, `TdsAmt`, `NetCommission`, `tat` | `Franchisecomm`, `FranchiseCommAmt`, `FranchiseTdsAmt`, `FranchiseNetComm` |
| Extra | `"TP Premium Extra"` | `TPPermium` (Extra slab) | `AgentComm_Extra`, `AgentCommAmt_Extra`, `TdsAmt_Extra`, `NetCommission_Extra` | `Franchisecomm_Extra`, `FranchiseCommAmt_Extra`, `FranchiseTdsAmt_Extra`, `FranchiseNetComm_Extra` |
| `"2"` | `"OD Premium"` | `ODPermium` (`txt_ODPremium`) | `AgentComm_OD`, `AgentCommAmt_OD`, `TdsAmt_OD`, `NetCommission_OD`, `Tat_OD` | `Franchisecomm_OD`, `FranchiseCommAmt_OD`, `FranchiseTdsAmt_OD`, `FranchiseNetComm_OD` |
| `"3"` | `"Net Premium"` | `NetPermium` (`txt_NetPremium`) | `AgentComm_Net`, `AgentCommAmt_Net`, `TdsAmt_Net`, `NetCommission_Net`, `Tat_Net` | `Franchisecomm_Net`, `FranchiseCommAmt_Net`, `FranchiseTdsAmt_Net`, `FranchiseNetComm_Net` |

### Vehicle Age Slab Lookup for Commission (`lBlslab`, `lblslabapp`)
**Evidence**: `adm_NcbRecovery.aspx.cs` (Lines 810–1005)
1. Checks if vehicle age slabbing is active for `(InsuranceComId, PolicyTypeId, ProductTypeId)` via `BLL_SelectCommVehAge`.
2. Computes vehicle age (`year`) from Manufacturing Month/Year via `BLL_SelectMgfyearOfyearmonth`.
3. Queries RTO-specific age slab first: `BLL_SelectYearSlabrto(InsuranceComId, PolicyTypeId, ProductTypeId, rtoid, year)`.
4. If no RTO-specific slab exists, falls back to `rtoid = 0`: `BLL_SelectYearSlabrto(InsuranceComId, PolicyTypeId, ProductTypeId, 0, year)`.

---

## 3. TDS (Tax Deducted at Source) Rules & Formulas

**Evidence**: `adm_tdsForAgent.aspx.cs` (L245–278), `adm_tdsrateforBroker.aspx.cs` (L81–111), `adm_NonMotarTransaction.aspx.cs` (L604), `AppPolicyRequestNew1_2026.aspx.cs` (L2173–2176), `PE_TransactionEntry.aspx.cs` (L9674)

1. **Configurable TDS Master Tables**:
   - **Agent / Franchise TDS (`adm_tdsForAgent.aspx.cs`)**: Stored via `BLL_Inserttdsforagent(API_tds, "INS"|"UPD")` (`usp_tdsforagent`) keyed by `(BrokerId, InsuranceCompanyId, BranchId, ReferenceType, ValidFrom)` with percentage `TdsCut`.
   - **Broker Receivable TDS (`adm_tdsrateforBroker.aspx.cs`)**: Stored via `BLL_tdsforbroker(API_tds, "insert"|"Update")` (`usp_tdsforbroker`) keyed by `(BrokerId, InsuranceCompanyId, ValidFrom)` with percentage `TdsCut`.
2. **Standard Commission TDS Formula**:
   $$\text{CommissionAmt} = \frac{\text{BasePremium} \times \text{CommRate}}{100}$$
   $$\text{TdsAmt} = \frac{\text{CommissionAmt} \times \text{TdsRate}}{100}$$
   $$\text{NetCommission} = \text{CommissionAmt} - \text{TdsAmt}$$
3. **Cut & Pay TDS Formula** (`AppPolicyRequestNew1_2026.aspx.cs` L2175, `FranchiseAppPolicyRequest.aspx.cs` L1356):
   $$\text{CutNPayTds} = \frac{\text{CutNPAY2} \times \text{tds}}{100}$$
4. **Non-Motor Hardcoded 15% TDS Formula** (`adm_NonMotarTransaction.aspx.cs` L604):
   ```csharp
   txt_tds.Value = Math.Round((Convert.ToDouble(txt_CommissionAmt.Value) * 0.15), 0).ToString();
   ```
5. **Hardcoded TDS Ledger ID (`LedgerMId = 2113`)**:
   - Across the entire codebase (`PE_TransactionEntry.aspx.cs` L9674, L10084; `PE_TransactionEntry_2026.aspx.cs` L9663, L10073; `PolicyNoUpdatePushNoti.aspx.cs` L966, L1068, L1855, L1962, L6669; `viewPolicyDetails.aspx.cs` L1151, L1262, L8634; `AgentCommissionRecalculation.aspx.cs` L4758; `adm_ImportTransAgentPolicyMIS.aspx.cs` L2591; `WebForm3.aspx.cs` L2367), **TDS is ALWAYS posted to `LedgerMId = 2113` (`//tds ledger`)**.

---

## 4. General Ledger Architecture & `AccTransId` Accounting Rules

**Evidence**: `API\AllMaster.cs` (`API_Account` L717–744), `PE_TransactionEntry.aspx.cs` (L9580–10138), `PolicyTransactionNew.aspx.cs` (L1319–1765), `adm_VoucherEntry.aspx.cs` (L277), `AppEndorsementforApproval.aspx.cs` (L211–291)

### 4.1 Single-Column Signed `amount` Convention
The legacy `tbl_accountdetails` (`API_Account`) table does **NOT** have separate `Debit` and `Credit` columns. Instead, it uses a single `double amount` column where:
- **Positive (`+amount`)** represents a **Debit / Inflow / Expense charge** to `LedgerMId`.
- **Negative (`-amount`)** represents a **Credit / Outflow / Liability / Payable accrual** to `LedgerMId`.
- Every balanced multi-leg accounting event sums to $\sum \text{amount} = 0$.

### 4.2 `AccTransId` Transaction Type Codes
| `AccTransId` | Meaning in Legacy System | Confirmed Screens & Workflows |
| :--- | :--- | :--- |
| **`1`** | **Receipt / Payment Inward / E-Wallet Settlement** | `PolicyTransactionNew.aspx.cs` (`InsertAccount` L1620–1742), `CashierApproval.aspx.cs`, `IdealPaymentReceipt.aspx.cs`, `POSP_MultiEntryIdealPayment.aspx.cs`, `AgentCommisionPayment.aspx.cs`, `AppEndorsementforApproval.aspx.cs` (L268). |
| **`2`** | **Payment / Voucher Outflow / Cash Approval / Discount / Endorsement Outflow** | `adm_VoucherEntry.aspx.cs` (L277), `adm_AppTransactionCashApproval.aspx.cs` (L1245–2016), `CashierApprovalNew.aspx.cs` (L3718–4057), `AppEndorsementforApproval.aspx.cs` (L211, L236), `Viewcashbackamount.aspx.cs` (L124). |
| **`3`** | **Journal / Commission Accrual / TDS Deduction / Unclear Cheque / Policy Cancellation / Recalculation** | `PE_TransactionEntry.aspx.cs` (`AccountEntry_2025` L9646–10120), `PolicyTransactionNew.aspx.cs` (Unclear Cheque L1329–1387), `adm_PolicyCancel.aspx.cs` (`ReturnUnclearingCheque` L900–1021), `AgentCommissionRecalculation.aspx.cs` (L4750–4880), `AccountantApproval.aspx.cs` (L1005–1126). |

### 4.3 Hardcoded System Ledger Master IDs (`LedgerMId`)
| `LedgerMId` | Ledger Role / Purpose | Confirmed Code Locations |
| :--- | :--- | :--- |
| **`1161`** | **Policy Commission Expense / E-Wallet Control Ledger** (formerly `596` in commented code) | `PE_TransactionEntry.aspx.cs` (L9650, L10055), `PolicyTransactionNew.aspx.cs` (L1622), `adm_PolicyCancel.aspx.cs` (L903). |
| **`2113`** | **TDS Payable Ledger (`//tds ledger`)** | `PE_TransactionEntry.aspx.cs` (L9674, L10084), `AgentCommissionRecalculation.aspx.cs` (L4758), `viewPolicyDetails.aspx.cs` (L1151). |
| **`1930`** | **Sales Executive / L.Head Commission Expense Ledger** | `PE_TransactionEntry.aspx.cs` (L9750). |
| **`1878`** | **Endorsement Income Ledger (`ledgerType = 'INCOME'`)** | `AppEndorsementforApproval.aspx.cs` (L138, L201). |

---

## 5. Exact Commission & TDS Journal Entries on Policy Issuance (`AccountEntry_2025`)

**Evidence**: `Insurance\Clerk\PE_TransactionEntry.aspx.cs` (Lines 9580–10138)

When a policy is issued (`PaymentMode` $\notin \{\text{"CASH"}, \text{"ONLINE TO RELIABLE"}, \text{"ONLINE TO BROKER"}\}$):

### Case A: `ReferenceType` in `{"Agent", "Franchise Agent", "Insurance Exective"}`
Let:
- $\text{AgentComm2021} = \text{Math.Round}(\text{GrossAgentCommAmt}, 0)$
- $\text{AgnetTds2021} = \text{Math.Round}(\text{AgentTdsAmt}, 0)$
- $\text{NetComm} = \text{Convert.ToDouble}(\text{lbl\_NetCommission.Text})$
- $\text{LedgerMID} = \text{BLL\_SelectLedgerforNetComm}(\text{AgentId})$

The system inserts **3 `API_Account` rows**:
1. **Gross Commission Debit (`LedgerMId = 1161`)**:
   - `AccTransId = 3`, `LedgerMId = 1161`, `amount = +AgentComm2021`, `Narration = "Policy Commission for Reg.No " + Regno`, `PaymentType = ddl_PaymentMode.SelectedItem.Text`.
2. **TDS Credit (`LedgerMId = 2113`)**:
   - `AccTransId = 3`, `LedgerMId = 2113`, `amount = -AgnetTds2021`, `Narration = "Policy Commission for Reg.No " + Regno`, `PaymentType = ddl_PaymentMode.SelectedItem.Text`.
3. **Agent Net Commission Credit (`LedgerMId = LedgerMID`)**:
   - `AccTransId = 3`, `LedgerMId = LedgerMID`, `amount = -NetComm`, `Narration = "Policy Commission for Reg.No " + Regno`, `PaymentType = "E-WALLET"`.

If `ReferenceType == "Franchise Agent"`, it additionally calls `FranchiseAccountEntry()` (L10035) which posts **3 more `AccTransId = 3` rows** for the Franchise (`LedgerMId = 1161` for `+FranchiseComm_Fr`, `LedgerMId = 2113` for `-FranchiseTds_Fr`, and `LedgerMId = LedgerMID_Fr` for `-netcomm_Fr`).

### Case B: `ReferenceType` in `{"Self", "L.Head"}` (and `netcomm > 0`)
Let `LedgerMID_SE` = `BLL_SelectLedgerforSalesExecutive(SalesExId)`. The system inserts **2 `API_Account` rows** (no TDS deduction):
1. **Sales Executive Commission Debit (`LedgerMId = 1930`)**:
   - `AccTransId = 3`, `LedgerMId = 1930`, `amount = +NetComm`, `Narration = "Policy Commission for Reg.No " + Regno`.
2. **Sales Executive Ledger Credit (`LedgerMId = LedgerMID_SE`)**:
   - `AccTransId = 3`, `LedgerMId = LedgerMID_SE`, `amount = -NetComm`, `PaymentType = "E-WALLET"`.

---

## 6. Commission Payout Sub-Ledger (`API_AgentCommPayment`)

**Evidence**: `PE_TransactionEntry.aspx.cs` (`AgentCommissionPaymentTableentry` Lines 9866–10031)

When `(PaymentMode in {"ONLINE TO INSURANCE COMPANY", "EMI", "CHEQUE"}) && (ReferenceType != "Direct")`:
1. Inserts an `API_AgentCommPayment` row via `BLL_InsertAgentCommPayment` with `PaymentStatus = "1"` and `Extra2` role discriminator:
   - `"F"` = Franchise (`Extra1 = AgentId` or `franchaiseId`)
   - `"S"` = Self (`Extra1 = SalesExId`)
   - `"L"` = L.Head (`Extra1 = SalesExId`)
   - `"I"` = Insurance Executive (`Extra1 = AgentId`)
   - `"A"` = Agent (`Extra1 = AgentId`)
2. Calls `BLL_Agent.BLL_UpdateAgentCommissionPay(TransactionId, "AgentCommProcess")`.

---

## 7. Commission Recalculation (`AgentCommissionRecalculation.aspx.cs`)

**Evidence**: `Insurance\Clerk\AgentCommissionRecalculation.aspx.cs` (Lines 4700–4900), `Insurance\Clerk\AgentCommissionRecalculationRS_Date.aspx.cs` (Lines 3650–3820)
- Allows admins to retroactively recalculate Broker, Franchise, and Agent commissions for existing transactions (by transaction date or risk start date `RS_Date`), updating the transaction commission columns and posting updated `AccTransId = 3` rows to `LedgerMId = 1161`, `LedgerMId = 2113` (TDS), and the Agent's `LedgerMID`.
