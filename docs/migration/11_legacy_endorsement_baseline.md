# 11 — Legacy Endorsement, NCB Recovery & Policy Cancellation Baseline (Phase 10B)

> **Audit Status**: CONFIRMED FROM CODE
> **Primary Evidence**:
> - `Insurance\Clerk\AppEndorsementforApproval.aspx.cs` (Lines 1–344 — App Endorsement Approval & Accounting)
> - `Insurance\Clerk\OwnerTransferEndorsement.aspx.cs` (Lines 1–261 — Owner Transfer Endorsement & History)
> - `Insurance\Clerk\adm_NcbRecovery.aspx.cs` (Lines 1–2652 — NCB Recovery, Commission Approval & Rejection)
> - `Insurance\Clerk\adm_PolicyCancel.aspx.cs` (Lines 1–1064 — Policy Cancellation, Commission Reversal & Clearing Account)

---

## 1. Endorsement Workflows Overview

The legacy codebase implements **four distinct post-issuance modification / reversal workflows**:

| Workflow | Entry Page | Stored Procedures / BLL Methods | Accounting Impact (`API_Account` / `API_ClearingAccount`) |
| :--- | :--- | :--- | :--- |
| **1. App Endorsement Request & Cashier/Account Approval** | `Clerk\AppEndorsementforApproval.aspx.cs` | `BLL_ViewAppEndorsementAllApproval`<br>`DAL_InsertAccountDetailsendos`<br>`BLL_EndosementCashierApprovalStatus` | Posts **3 `API_Account` rows** (`AccTransId = 2`, `2`, `1`) using Income Ledger `1878` and Bank/Cash Ledgers. |
| **2. Owner Transfer Endorsement** | `Clerk\OwnerTransferEndorsement.aspx.cs` | `BLL_searchForEndorseByVehicleNo`<br>`BLL_InsertCustomer`<br>`BLL_UpdateEndorsement`<br>`BLL_EndorsementHistoryOpration` | None (Ownership transfer only; creates new `CustomerId` and logs `API_Endorsement` history). |
| **3. NCB Recovery & Policy Verification** | `Clerk\adm_NcbRecovery.aspx.cs` | `BLL_VehicleHistory`<br>`BLL_selectNcbrecoveryTransId`<br>`BLL_InsertNCBRecovery`<br>`BLL_UpdateAgentCommissionPay` | Sends NCB Recovery SMS (`SendSms()`) and records recovery amount (`txt_recovery.Text`). Also hosts Commission Approval (`"AgentCommProcess"` / `"AgentCommPay"`) and Policy Rejection (`"PolicyCancel"`). |
| **4. Policy Cancellation & Commission Reversal** | `Clerk\adm_PolicyCancel.aspx.cs` | `BLL_SelectAccountantApprovalByPolicynoCancel`<br>`BLL_InsertFranchaiseComm` (negative)<br>`BLL_InsertAccountDetails`<br>`BLL_InsertClearingAccountDetails` | Reverses Franchise & Agent commissions by inserting negative `API_franchaiseCommission` rows, **2 `API_Account` rows (`AccTransId = 3`)**, and **1 `API_ClearingAccount` row (`AccTransId = 3`)**. |

---

## 2. Workflow 1: App Endorsement Financial Approval (`AppEndorsementforApproval.aspx.cs`)

**Evidence**: `Insurance\Clerk\AppEndorsementforApproval.aspx.cs` (Lines 39–314)

### 2.1 Endorsement Queue & Margin Calculation (`ViewAppTransGrid_SelectedIndexChanged` L128–156)
1. Loads pending endorsements via `BLL_ViewAppTransaction.BLL_ViewAppEndorsementAllApproval()`.
2. Maps Grid column `Cells[5]` (`NCBRecovery`): `"0"` -> `"NO"`, else `"YES"` (L49–57).
3. When a row is selected:
   - `txt_transid.Value = Cells[1].Text` (Endorsement ID)
   - `txtPaidAmount.Value = Cells[32].Text` (Total Endorsement Amount Received from Customer/Agent)
   - `txt_paidAmt.Value = Cells[34].Text` (Service Charge / Margin Retained)
   - **Company Payable Amount (`txtCmpAmt.Value`)**:
     $$\text{amt} = \text{Math.Round}(\text{Convert.ToDouble}(\text{txtPaidAmount.Value}) - \text{Convert.ToDouble}(\text{txt\_paidAmt.Value}))$$
   - Locks `ddlTransactionType` to `"2"` (`AccTransId = 2`) and `ddltolegder` to **`"1878"`** (`ledgerType = 'INCOME'`, disabled dropdown — L137–139, L201).

### 2.2 Three-Leg Endorsement Accounting Entry (`btnApprove_click` L199–314)
When approved (`ddlfromlegder.SelectedIndex != 0 && ddltolegder.SelectedIndex != 0`), generates `Doc_No` via `BLL_generateDoc_No()` and inserts **3 `API_Account` rows** via `DAL_InsertAccountDetailsendos`:

| Leg # | `AccTransId` | `LedgerMId` | `amount` | `Narration` | `EndorsementId` | `BranchId` |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Leg 1** | `2` | `ddlfromlegder` (`Bank/Cash` receiving ledger) | `+(txtPaidAmount.Value)` | `txt_Narration.Value` | `Convert.ToInt16(txt_transid.Value)` | `1` (Hardcoded) |
| **Leg 2** | `2` | **`1878`** (Hardcoded `INCOME` ledger) | `-(txtCmpAmt.Value)` | `txt_Narration.Value` | `Convert.ToInt16(txt_transid.Value)` | `1` (Hardcoded) |
| **Leg 3** | `1` | `ddlPayTo` (`Bank/Cash` paying ledger) | `-(txtCmpAmt.Value)` | `"Endors Charges Pay to " + txtInsuranceCmp.Value + "For " + txtendorsementType.Value + "," + txtendorsementsubType.Value + "From " + txttransCustname.Value` | `Convert.ToInt16(txt_transid.Value)` | `1` (Hardcoded) |

After inserting the 3 ledger rows, calls `Bll_obj.BLL_EndosementCashierApprovalStatus(Convert.ToInt32(txt_transid.Value))` and alerts `'Payment Approved Successfully'`.

> **Critical Defect Note**: At Lines 228, 257, and 289, `EndorsementId` is cast using **`Convert.ToInt16(txt_transid.Value)`** (`short`), whereas at Line 301 it uses `Convert.ToInt32(txt_transid.Value)`. Once `EndorsementId` exceeds `32,767`, `Convert.ToInt16` throws an unhandled `OverflowException`!

---

## 3. Workflow 2: Owner Transfer Endorsement (`OwnerTransferEndorsement.aspx.cs`)

**Evidence**: `Insurance\Clerk\OwnerTransferEndorsement.aspx.cs` (Lines 114–231)
1. **Lookup**: Searches policy/vehicle by `hfVehNoSearch.Value` and `Session["BranchId"]` via `BLL_CustVehicle.BLL_searchForEndorseByVehicleNo(VehId, BranchId)`.
2. **New Customer Creation**: Generates a new `CustomerCode` (`BLL_generateCustomerCode()`) and inserts a new customer record (`int custId = InsertCustomer()`).
3. **Ownership Rebinding**: Calls `BLL_Endorsement.BLL_UpdateEndorsement(custId, CustVehId, TransId)` (`usp_UpdateEndorsement`) to point the vehicle and policy to the new `custId`.
4. **Endorsement Audit Log**: Inserts `API_Endorsement` via `BLL_EndorsementHistoryOpration(Endos)`:
   - `HistoryID = -1`, `HistoryDate = DateTime.Now`
   - `PolicyId = TransId`, `VehicleId = CustVehId`
   - `PreviousCustomerId = Convert.ToInt32(lblCustId.Text)`
   - `CurrentCustomerId = custId`
   - `CreateUser = "1"`, `UpdateUser = "1"`

---

## 4. Workflow 3: NCB Recovery (`adm_NcbRecovery.aspx.cs`)

**Evidence**: `Insurance\Clerk\adm_NcbRecovery.aspx.cs` (Lines 1072–1091)
1. **Idempotency / Duplicate Check**:
   - Queries `DataTable dt = Bll_obj2.BLL_selectNcbrecoveryTransId(int.Parse(lblTransId.Text));`
2. **Insert & SMS Dispatch**:
   - If `dt.Rows.Count == 0`:
     - Calls `Bll_obj1.BLL_InsertNCBRecovery(int.Parse(lblTransId.Text), int.Parse(lblCustVehId.Text), lblRegNo.Text, lblPolicyNo.Text, Convert.ToDouble(txt_recovery.Text))`
     - Calls `SendSms()` to notify the agent/customer of the NCB recovery demand.
     - Alerts `'recovery Msg Send  Successfully'`.
   - Else (`dt.Rows.Count > 0`):
     - Alerts `'recovery Msg Already Send '`.

---

## 5. Workflow 4: Policy Cancellation & Commission Reversal (`adm_PolicyCancel.aspx.cs`)

**Evidence**: `Insurance\Clerk\adm_PolicyCancel.aspx.cs` (Lines 800–1061)

When a policy is cancelled in `adm_PolicyCancel.aspx.cs`:

### 5.1 Franchise Commission Negation (Lines 800–818)
- Reads the original `API_franchaiseCommission` values (`dtFranch`) and negates every component:
  - `Franch.ProfitofNetCommision = -(Convert.ToDouble(dtFranch.Rows[0][24]))`
  - `netcomm_f = -(Convert.ToDouble(dtFranch.Rows[0][9]))`
  - `netcomm_OD = -(Convert.ToDouble(dtFranch.Rows[0][15]))`
  - `netcomm_Net = -(Convert.ToDouble(dtFranch.Rows[0][19]))`
  - `netcomm_Extra = -(Convert.ToDouble(dtFranch.Rows[0][23]))`
- Inserts the negated franchise commission record via `BLL_Obj1.BLL_InsertFranchaiseComm(Franch)`.

### 5.2 Reversal Ledger & Clearing Entries (`ReturnUnclearingCheque` Lines 888–1061)
For the Agent (and for Sub-Franchise when `FrId != 1`), `ReturnUnclearingCheque(Agentid, netcomm, LedgerMID, tran_id, TransDate11, commPaid, PaymentType)` posts **2 `API_Account` rows** and **1 `API_ClearingAccount` row**:

1. **Narration & `MonthId` Rule Based on `commPaid` and Transaction Month**:
   - Let `monthtoday = TransDate11.Month` and `currentmonth = DateTime.Now.Month`.
   - **If `commPaid == 1`** (Commission was already paid out):
     - `MonthId = 0`
     - If `hidCustVehId.Value != "500"` (Motor): `Narration = "Commission Recoverable for Reg.No " + RegNO`
     - Else (Non-Motor sentinel `"500"`): `Narration = "Commission Recoverable  for Policy.No " + hidPolicyNo.Value`
   - **If `commPaid != 1`** (Commission was unpaid):
     - `MonthId = (monthtoday != currentmonth) ? monthtoday : 0`
     - If `hidCustVehId.Value != "500"`: `Narration = "Cancel policy for Reg.No " + RegNO`
     - Else: `Narration = "Cancel policy for Policy.No " + hidPolicyNo.Value`
2. **Entry 1 (`API_Account` — Reverse Commission Expense `LedgerMId = 1161`)**:
   - `AccTransId = 3`, `LedgerMId = 1161`, `amount = -netcomm` (Note: `netcomm` passed from franchise is already negative or positive depending on caller; reverses original `1161` entry), `TransactionId = tran_id`, `CustVehId = int.Parse(hidCustVehId.Value)`.
3. **Entry 2 (`API_Account` — Debit Agent/Franchise Ledger `LedgerMID`)**:
   - `AccTransId = 3`, `LedgerMId = LedgerMID`, `amount = +netcomm`, `TransactionId = tran_id`.
4. **Entry 3 (`API_ClearingAccount` — Clearing Account Record)**:
   - `AccTransId = 3`, `LedgerMId = LedgerMID`, `amount = netcomm`, `IsNill = 0`, `MonthId = (monthtoday != currentmonth) ? monthtoday : 0`.
   - Inserted via `cashBLL1.BLL_InsertClearingAccountDetails(cashAccount_c11)`.
