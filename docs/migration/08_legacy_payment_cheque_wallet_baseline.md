# 08 — Legacy Payment, Cheque, Reconciliation & E-Wallet Baseline (Phase 8)

> **Audit Status**: CONFIRMED FROM CODE
> **Primary Evidence**:
> - `API\AllMaster.cs` (Lines 682–785 — `API_TransactionPayment`, `API_Account`, `API_PremiumReceipt`, `API_PremiumBatchwise`, `API_accountpremiumreceivingmultientry`, `API_ClearingAccount`)
> - `Insurance\Clerk\PolicyTransactionNew.aspx.cs` (Lines 1158–1205, 1288–1406, 1608–1765)
> - `Insurance\Clerk\PE_TransactionEntry.aspx.cs` (Lines 9620–9812, 10141–10200)
> - `Insurance\Clerk\CashierApprovalNew.aspx.cs` (Lines 3700–4100, 5780–5800)
> - `Insurance\Clerk\adm_AppTransactionCashApproval.aspx.cs` & `adm_AppTransactionCashApprovalNew.aspx.cs` (Lines 1240–2020)
> - `Insurance\Clerk\AccountantApproval.aspx.cs` (Lines 1000–1130)
> - `Insurance\Clerk\ViewAppTransEwalletApproval.aspx.cs` (Lines 1–500)
> - `Insurance\Clerk\Rpt_viewChequeClearing.aspx.cs`, `Insurance\Clerk\Rpt_ChequeClearingByadmin.aspx.cs`, `Insurance\Adm_LockChequeEntry.aspx.cs`
> - `Insurance\POSP_MultiEntryIdealPayment.aspx.cs`, `Insurance\Clerk\IdealPaymentReceipt.aspx.cs`

---

## 1. Supported Payment Modes

Across App Requests (`AppPolicyRequestNew1_2026.aspx.cs`), Clerk Booking (`PolicyTransactionNew.aspx.cs`), and Post-Entry (`PE_TransactionEntry.aspx.cs`), the following payment modes are used:

| Payment Mode String | Initial Approval Flags in `InsertTransactionPayment` (`PolicyTransactionNew.aspx.cs` L1168–1195) | Downstream Approval & Accounting Pipeline |
| :--- | :--- | :--- |
| `"CASH"` | `CashierApproval = 0`<br>`AccountantApproval = 0`<br>`OwnerApproval = 0` | Requires Pre-Premium Cash Approval (`IsAccountApproval`), Pending Cash / Branch Cash Deposit (`IsActivePendingCash`, `PremiumCashToBank`), and Cashier Approval (`CashierApproval`). |
| `"CHEQUE"` | `CashierApproval = 1`<br>`AccountantApproval = 0`<br>`OwnerApproval = 0` | Posts provisional unclear commission entries (`AccTransId = 3`, `"Policy account for unclear amount"`). Requires Cheque Clearing / Accountant Approval (`AccountantApproval = 1`). Can be Bounced/Returned. |
| `"E-WALLET"` | `CashierApproval = 1`<br>`AccountantApproval = 1`<br>`OwnerApproval = 1` | Checks agent wallet balance (`BLL_AgentCommWalletBalance`) and posts 4 immediate `AccTransId = 1` ledger entries in `InsertAccount()`, plus E-Wallet Account Approval in `ViewAppTransEwalletApproval.aspx.cs`. |
| `"ONLINE TO RELIABLE"` | `CashierApproval = 1`<br>`AccountantApproval = 1`<br>`OwnerApproval = 1` | Handled via `OnlintoRAEntry` (`PE_TransactionEntry.aspx.cs` L10141): supports `"CUT AND PAY"`, `"Full Payment"`, and `"Pass On"`, and reconciles RA bank receipt to insurer payment (`Cheque` / `Broker Online` / `Online From RA` / `Float`). |
| `"ONLINE TO INSURANCE COMPANY"` | `CashierApproval = 1`<br>`AccountantApproval = 1`<br>`OwnerApproval = 1` | Customer/Agent pays insurer directly online. Updates inward status (`UpateInwardStatus`) and triggers commission accrual (`AccTransId = 3`) & `API_AgentCommPayment`. |
| `"ONLINE TO BROKER"` | `CashierApproval = 1`<br>`AccountantApproval = 1`<br>`OwnerApproval = 1` | Customer/Agent pays co-broker directly online. Tracked under Cash/Online approval (`adm_NcbRecovery.aspx.cs` L653). |
| `"EMI"` | `CashierApproval = 1`<br>`AccountantApproval = 1`<br>`OwnerApproval = 1` | Financed premium via `ViewAppTransactionAccountApprovalEMI.aspx.cs`; triggers commission accrual (`AccTransId = 3`) & `API_AgentCommPayment`. |

---

## 2. Payment Approval Flags & Multi-Stage Cash/Online State Tracking

**Evidence**: `API\AllMaster.cs` (`API_TransactionPayment` L682–709) and `Insurance\Clerk\adm_NcbRecovery.aspx.cs` (Lines 414–755)

Every policy transaction tracks **7 boolean/integer payment lifecycle flags** alongside `CashStatus` and `QuatationCode`:

1. **`IsAccountApproval`** (`dt.Rows[0][79]`):
   - `0` = `"Pending"` (Pre-Premium Cash Approval pending)
   - `1` = `"Done"`
2. **`CashStatus`** (`dt.Rows[0][80]`):
   - `"Cash In Hand"`, `"Deposited"`, etc.
   - If `CashStatus == "Cash In Hand" && IsAccountApproval == 1 && isCompletePayment == 0 && IsActivePendingCash == 0` -> Pending Cash status is `"Pending"`.
   - If `IsAccountApproval == 1 && isCompletePayment == 0 && IsActivePendingCash == 1` -> Pending Cash status is `"Done"` (`adm_NcbRecovery.aspx.cs` L592–599).
3. **`isCompletePayment`** (`dt.Rows[0][81]`):
   - Indicates full settlement of the transaction payment.
4. **`IsActivePendingCash`** (`dt.Rows[0][82]`):
   - Tracks whether branch cash in hand has been batched/activated for deposit.
5. **`CashierApproval`** (`dt.Rows[0][83]`):
   - Set to `1` when Cashier approves cash/online receipt (`CashierApproval.aspx.cs` / `CashierApprovalNew.aspx.cs` / `adm_AppTransactionCashApprovalNew.aspx.cs`).
6. **`PremiumCashToBank`** (`dt.Rows[0][84]`):
   - Tracks branch cash deposit into bank (`"BRANCHCASH"` vs `"DONE_BRANCHCASH"` in `BLL_VehicleHistory`).
7. **`OnlinePaymentToCompany`** (`dt.Rows[0][85]`):
   - For `"ONLINE TO INSURANCE COMPANY"` or `"CASH"`:
     - If `OnlinePaymentToCompany == "1"` -> Displayed as `"Paid To Online"`.
     - Else -> Displayed as `"CCD Cheque"` (Company CD / Cheque payment to insurer — `adm_NcbRecovery.aspx.cs` L426–437).
8. **`IsCustomerChequeNo`** (`dt.Rows[0][87]`):
   - Tracks whether customer cheque was used (`"CUSTCHEQUE"` in `BLL_VehicleHistory`).

---

## 3. Cut & Pay vs Full Payment / Pass On (Cash & Online to Reliable)

**Evidence**: `Insurance\AppPolicyRequestNew1_2026.aspx.cs` (Lines 2170–2185), `Insurance\Clerk\PE_TransactionEntry.aspx.cs` (Lines 10141–10190), `Insurance\Clerk\adm_NcbRecovery.aspx.cs` (Lines 510–563)

When an Agent submits an App Policy Request with Cash or Online to Reliable payment, `lblCash_Type` (`CashType`) is one of:
- **`"CUT AND PAY"`** (or `"Cut and Pay"`):
  - The agent deducts their net commission up-front and remits only the net difference (`ShortFallAmt` / `DepositAmt`) to Reliable Associates.
  - **Cut & Pay TDS Formula** (`AppPolicyRequestNew1_2026.aspx.cs` L2173–2176, `FranchiseAppPolicyRequest.aspx.cs` L1354–1356):
    $$\text{CutNPayTds} = \frac{\text{CutNPAY2} \times \text{tds}}{100}$$
  - In `OnlintoRAEntry` (`PE_TransactionEntry.aspx.cs` L10161–10174):
    - Calls `bll_obj.BLL_PaymentApproval(0, TransactionId, "ONLINETORA")`.
    - If `cutnpay != 0`, calls `UpdateTransactionOfCutNPay(cutnpay)`.
- **`"Full Payment"`** (or `"Full Payement"`, `"FullPayment"`, `"FULLPAYMENT"`, `"Pass On"`, `"PASS ON"`):
  - The agent/customer remits the **full gross proposal amount** to Reliable Associates, and the agent's commission is subsequently credited/paid out via Commission Payout (`"AgentCommProcess"`).
  - In `OnlintoRAEntry` (`PE_TransactionEntry.aspx.cs` L10177–10188):
    - Calls `bll_obj.BLL_PaymentApproval(0, TransactionId, "ONLINETORA")`.
    - Calls `CashGoToPayment()`.
  - Look at `adm_NcbRecovery.aspx.cs` (Lines 1021–1036):
    - On NCB/Policy Approval (`btn_Approve_Click`):
      - If `lblCashType.Text == "Full Payement"` *(note exact spelling `"Full Payement"`)* -> Calls `BLL_UpdateAgentCommissionPay(TransId, "AgentCommProcess")`.
      - Else (Cut & Pay) -> Calls `BLL_UpdateAgentCommissionPay(TransId, "AgentCommPay")` (marks commission as already paid!).

---

## 4. Cheque Lifecycle: Unclear Provisioning, Clearing, Bounce & Lock Mechanism

### 4.1 Cheque Booking — Unclear Amount Provisioning (`AccTransId = 3`)
**Evidence**: `PolicyTransactionNew.aspx.cs` (Lines 1319–1406)
When a policy is booked with `ddl_Reference.SelectedIndex == 1` (Agent) and `ddl_PaymentMode.SelectedValue == "CHEQUE"`:
1. **Agent Unclear Entry**:
   - Looks up Agent's ledger via `BLL_SelectLedgerforNetComm(AgentId)`.
   - Inserts `API_Account` with `AccTransId = 3`, `LedgerMId = LedgerMID`, `amount = -Math.Round(Cacl_NetComm, 0)`, `Narration = "Policy account for unclear amount"`, `Doc_No = Convert.ToInt32(txt_docno.Value)`, `PaymentType = "CHEQUE"`.
2. **Reliable Associates (`FranchiseId = 1`) Unclear Entry**:
   - Looks up RA ledger via `BLL_SelectLedgerforFranchise(1)`.
   - Inserts `API_Account` with `AccTransId = 3`, `LedgerMId = LedgerMID_RA`, `amount = -Math.Round(Cacl_NetComm_RA, 0)`, `Narration = "Policy account for unclear amount"`.
3. **Sub-Franchise (`hdn_FranchiseId != "1"`) Unclear Entry**:
   - Looks up Franchise ledger via `BLL_SelectLedgerforFranchise(franchaiseId)`.
   - Inserts `API_Account` with `AccTransId = 3`, `LedgerMId = LedgerMID_Fr`, `amount = -Math.Round(Cacl_NetComm_Fr, 0)`, `Narration = "Policy account for unclear amount"`.

### 4.2 Cheque Clearing & Accountant Approval
**Evidence**: `Insurance\Clerk\AccountantApproval.aspx.cs` (L1000–1130), `Insurance\Clerk\Rpt_viewChequeClearing.aspx.cs`, `Insurance\Clerk\Rpt_ChequeClearingByadmin.aspx.cs`
- Accountant reviews pending cheques (`AccountantApproval == 0`).
- Upon clearing, updates `AccountantApproval = 1`, `AccountantApprovalDate = DateTime.Now`, and moves commission from unclear/provisional to active ledger / `API_ClearingAccount`.

### 4.3 Cheque Lock Enforcement (`Adm_LockChequeEntry.aspx.cs` & `Log_In.aspx.cs`)
**Evidence**: `Insurance\Log_In.aspx.cs` (Lines 155–185), `Insurance\Adm_LockChequeEntry.aspx.cs`
- The system includes a mechanism (`BLL_LockChequeClearingCount(userName)`) to detect overdue uncleared cheques and redirect users to `Adm_LockChequeEntry.aspx` (or `adm_LockCashEntry1.aspx`, `adm_LockPendingTansEntry.aspx`).

---

## 5. E-Wallet Architecture & Accounting Entries

### 5.1 E-Wallet Balance Check
**Evidence**: `PolicyTransactionNew.aspx.cs` (Lines 1288–1311)
- Stored procedure wrapper: `BLL_Transaction.BLL_AgentCommWalletBalance(AgentId)` returns single scalar integer/float balance (`dt1.Rows[0][0]`).
- Validation: `if (balance > Convert.ToInt32(txtPaymentAmt.Value))` (must be strictly greater than `txtPaymentAmt`).

### 5.2 E-Wallet Policy Booking Ledger Entries (`InsertAccount()` in `PolicyTransactionNew.aspx.cs` L1608–1765)
When `ddl_PaymentMode.SelectedValue == "E-WALLET"`, `InsertAccount()` posts **4 `API_Account` rows** (all with `AccTransId = 1` and `Doc_No = 0`):

| Entry # | `AccTransId` | `LedgerMId` | `amount` | `Narration` | `ReferenceAgentId` | Purpose |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1** | `1` | `1161` (Hardcoded Commission/Wallet Control Ledger) | `-(txtPaymentAmt)` | `"E-Wallet Payment Used For <RegNo> Policy Generation"` | `AgentId` | Credits/reduces Control Ledger `1161` by payment amount. |
| **2** | `1` | `LedgerMID_ra` (`BLL_SelectLedgerforFranchise(1)`) | `+(txtPaymentAmt)` | `"E-Wallet Payment Used For <RegNo> Policy Generation"` | `AgentId` | Debits RA Franchise Ledger (`FranchiseId=1`). |
| **3** | `1` | `LedgerMID_ra` (`BLL_SelectLedgerforFranchise(1)`) | `-(txtPaymentAmt)` | `"Cheque Policy commision"` | `AgentId` | Offsets RA Franchise Ledger (`FranchiseId=1`). |
| **4** | `1` | `LedgerMID` (`BLL_SelectLedgerforNetComm(AgentId)`) | `-(txtPaymentAmt)` *(or `+` depending on branch)* | `"Cheque Policy commision"` | `AgentId` | Adjusts Agent's Net Commission Ledger (`LedgerMID`) for the wallet utilization. |

### 5.3 App E-Wallet Approval Workflow (`ViewAppTransEwalletApproval.aspx.cs`)
**Evidence**: `Insurance\Clerk\ViewAppTransEwalletApproval.aspx.cs` (Lines 51–116, 143–276, 339–357, 435–500)
1. **Queue Selection**: Calls `BLL_ViewAppTransaction.BLL_ViewAppTransactionAccountApprovalEWALLET(RoleId)`.
2. **Wallet Usage Breakdown**: Calls `BLL_selectEwalletBalanceApprovedetails(agentId)` and sums `EWalletUsedamt` in the grid footer (`dt.AsEnumerable().Sum(row => row.Field<double>("EWalletUsedamt"))` — L351).
3. **RA Payment Mode Mapping on Approval (`btn_Upload_Click` L435–498)**:
   - Requires non-empty `txtRemark.Text`.
   - Calls `BLL_UpdateAppPolicyAccountApproval1(ChequeNo, RAPaymentMode, UrlLink, TransId, ModeCode, Remark, BankLedgerName, CashBackAmt)`:
     - If `ddl_RApayment == "Cheque"` -> `ModeCode = "Cheque"`, passes `txtlblRaCheque.Text` and `ddlfromlegder3.SelectedItem.Text`.
     - If `ddl_RApayment == "Broker Online"` or `"Online From RA"` -> `ModeCode = "OlRA"`, passes `lblurllinks.Text`.
     - Else -> `ModeCode = "Float"`.
