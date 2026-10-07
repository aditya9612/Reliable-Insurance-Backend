# 07 — Legacy Policy Booking, Transaction & Inward Baseline (Phase 7)

> **Audit Status**: CONFIRMED FROM CODE
> **Primary Evidence**:
> - `Insurance\Clerk\PolicyTransactionNew.aspx.cs` (Lines 860–1950 — Direct Clerk Motor Policy Booking)
> - `Insurance\Clerk\PE_TransactionEntry.aspx.cs` (Lines 3900–4800, 9570–10200 — Post-Entry / App Policy Issuance & Accounting)
> - `Insurance\Clerk\PE_TransactionEntry_2026.aspx.cs` (Lines 3900–4800, 9570–10200)
> - `Insurance\AppPolicyRequestNew1_2026.aspx.cs` (Lines 2100–2250, 5850–6050 — Mobile/Web App Policy Request)
> - `Insurance\Clerk\adm_NonMotarTransaction.aspx.cs` & `NonMotorPolicyDetails.aspx.cs` (Non-Motor Policy Booking)
> - `Insurance\Clerk\PolicyNoUpdatePushNoti.aspx.cs` (Lines 900–2050, 6600–6750 — Policy No Update & Push Notification)
> - `API\AllMaster.cs` (Lines 476–627 — `API_Transaction`)

---

## 1. Policy Booking Entry Flows in Legacy System

The legacy system supports **four distinct policy booking pipelines**:

| Pipeline | Entry Page(s) / Service | Workflow Sequence | Target Database Operations |
| :--- | :--- | :--- | :--- |
| **1. Direct Clerk Motor Policy Entry** | `Clerk\PolicyTransactionNew.aspx.cs`<br>`Clerk\PolicyTransactionNew1.aspx.cs`<br>`Clerk\MotorTransactionEntry.aspx.cs`<br>`Clerk\NewPolicyEntry.aspx.cs` | Single-screen entry of Customer + Vehicle + Policy + Commission Calculation + Payment Mode -> Click Save (`btnSave_Click`). | 1. `InsertCustomer()` (`BLL_InsertCustomer`)<br>2. `InsertCustVehicle(custId)` (`BLL_InsertVehicleDetails`)<br>3. `InsertTransaction(custId, vehId)` (`BLL_InsertTransaction`)<br>4. Conditional `InsertAccount()` / Unclear Cheque `AccTransId=3` entries<br>5. `InsertFranchiseDetails(transId)` (`BLL_InsertFranchaiseComm`)<br>6. `InsertTransactionPayment(transId)` (`BLL_TransactionPaymentOpration`) |
| **2. Multi-Step Wizard Policy Entry** | `Clerk\adm_CustomerDetails.aspx.cs` -> `Clerk\adm_VehicleDetails.aspx.cs` -> `Clerk\adm_PolicyDetails.aspx.cs` | Stores intermediate `DataTable` state in `Session["dtTransaction"]`, `Session["dtCustomer"]`, and `Session["dtVehicle"]` across pages before final commit. | Commits Customer, Vehicle, Transaction, Payment, and Commission rows on final step. |
| **3. App Policy Request -> Post-Entry (`PE_TransactionEntry`)** | `AppPolicyRequestNew1_2026.aspx.cs` / `Service.asmx.cs` -> Approvals -> `Clerk\PE_TransactionEntry.aspx.cs` (`AccountEntry_2025`) | Agent/Executive submits request via App/Web (`TransId`). After Cash/Cheque/E-Wallet/Account Pre-Approval, Policy Entry operator issues policy number in `PE_TransactionEntry.aspx.cs`. | Updates Policy No (`BLL_UpdatePolicyNo`), updates Inward status (`BLL_UpdateStatusForInvert`), posts Commission & TDS ledger rows (`AccTransId = 3`), updates Sales Target (`BLL_Updatetargetachieved`), and inserts `API_AgentCommPayment`. |
| **4. Non-Motor Policy Booking** | `Clerk\adm_NonMotarTransaction.aspx.cs`<br>`Clerk\NonMotorPolicyDetails.aspx.cs` | Captures `InsuranceTypeId`, `InsuranceSubTypeId`, `SumInsured`, `NetPermium`, `GST`, and calculates 15% TDS (`Math.Round(CommissionAmt * 0.15, 0)` at L604). | Inserts `API_Transaction` with `MotorOrNonMotor = "NONMOTOR"` (or `CustVehId = 500` sentinel used in `adm_PolicyCancel.aspx.cs` L905). |

---

## 2. Core Transaction Entity (`API_Transaction`) & Field Rules

**Evidence**: `API\AllMaster.cs` (Lines 476–627), `PolicyTransactionNew.aspx.cs` (Lines 960–1116)

| Field Name (Exact Spelling) | C# Type | Source / Assignment in `InsertTransaction` | Business Rule / Notes |
| :--- | :--- | :--- | :--- |
| `TransactionId` | `int` | Returned by `BLL_InsertTransaction(Trans)` | Primary key of the policy transaction. |
| `InwardNo` | `string` | `generateInwardNo()` -> `txt_InwardNo.Value` | Generated immediately prior to `BLL_InsertTransaction` via `BLL_Transaction.BLL_generateInwardNo()`. |
| `TransDate` | `DateTime` | `Convert.ToDateTime(Txt_Date.Value)` | Policy booking / inward date. |
| `BranchId` | `int` | `Convert.ToInt32(ddl_Branch.SelectedValue)` | Branch owning the policy. |
| `PolicyTypeId` | `int` | `Convert.ToInt32(ddl_PType.SelectedValue)` | Foreign key to Policy Type master (`API_PolicyType`). |
| `CustomerId` | `int` | `CustID` (returned from `InsertCustomer()`) | Foreign key to Customer. |
| `CustVehId` | `int` | `VehId` (returned from `InsertCustVehicle(CustID)`) | Foreign key to Customer Vehicle (`500` used as sentinel for Non-Motor in cancellation). |
| `InsuranceCompanyId` | `int` | `Convert.ToInt32(ddl_company.SelectedValue)` | Insurer ID (Note: Company IDs `2`, `3`, `32` have special hardcoded rules in C#!). |
| `PolicyNo` | `string` | `txt_PolicyNo.Value` | Insurer policy number (may be blank/pending at inward stage and updated later via `BLL_UpdatePolicyNo`). |
| `PolicyModeId` | `int` | `Convert.ToInt32(ddl_PolicyMode.SelectedValue)` | Policy mode (Note: if `SelectedIndex == 3`, `txt_LeadNo` is enabled — L850). |
| `Lead_No` | `string` | `txt_LeadNo.Value` | Lead reference number when `PolicyMode` requires a lead. |
| `ProductTypeId` | `int` | `Convert.ToInt32(rdl_PolicyProduct.SelectedValue)` | `1` = Package/Comprehensive, `2` = TP/Liability, `3` = SAOD. |
| `BusinessTypeId` | `int` | `Convert.ToInt32(rdl_Business.SelectedValue)` | Rollover / New / Renewal business type (`API_BusinessType`). |
| `AgentId` | `int` | If `ddl_Agent.SelectedIndex != 0` -> `ddl_Agent.SelectedItem.Value`; **else falls back to `ddl_Sales.SelectedValue`** (L977–983) | **Critical Rule**: When no Agent is selected (e.g., Direct business), `Trans.AgentId` is populated with `SalesEx_id`! |
| `SalesEx_id` | `int` | `Convert.ToInt32(ddl_Sales.SelectedValue)` | Assigned Sales Executive Employee ID. |
| `RiskStartdate`, `ExpiryDate` | `DateTime` | `txt_sdate.Text`, `txt_Expiredate.Value` | Policy risk period (`ExpiryDate = RiskStartdate + 1 Year - 1 Day`). |
| `SumInsured` | `double` | `Convert.ToDouble(txt_suminsured.Value)` | IDV (Motor) or Sum Insured (Non-Motor). |
| `Imt23`, `Imt47` | `string` | `ddl_Imt23.SelectedValue`, `ddl_Imt47.SelectedValue` (`"Yes"` / `"No"`) | IMT-23 and IMT-47 endorsement flags. |
| `AddOn`, `AddOnRate` | `string`, `double` | `ddl_AddOn.SelectedValue` | Zero-Dep / Add-On selection and rate. |
| `TowingChargesAmt` | `double` | `Convert.ToDouble(txt_Towing.Value)` | Extra towing cover amount. |
| `NCB`, `NCBPermium` | `double` | `txt_NCB.Value`, `txt_NCBPremium.Value` | NCB percentage and NCB discount amount (`NCBPermium` spelling). |
| `ODDiscount` | `double` | `Convert.ToDouble(txt_ODDiscount.Value)` | OD Discount percentage. |
| `ODPermium`, `TPPermium`, `NetPermium` | `double` | `txt_ODPremium.Text`, `txt_TPPremium.Text`, `txt_NetPremium.Value` | Basic OD, Basic TP, and Net Premium (`OD + TP + PA + IMT17 + LL`) before GST. |
| `ProPosalAmt` | `double` | `Convert.ToDouble(txt_ProposalAmt.Value)` | Gross / Total Premium inclusive of GST. |
| `PACovertoOwner`, `PACoverDriverCleaner`, `LegalLiabilitytoPaidDriver` | `double` | `txtPACover`, `txtIMT17`, `txtLegalLiability` | Note: `txtIMT17` is stored in `PACoverDriverCleaner` (`PE_TransactionEntry.aspx.cs` L4788). |
| `ReferenceType` | `string` | `ddl_Reference.SelectedValue` | Values: `"Agent"`, `"Direct"`, `"Franchise"`, `"Franchise Agent"`, `"Self"`, `"L.Head"`, `"Insurance Exective"`, `"Tele Sales"`, `"By Customer"`. |
| `AgentComm`, `AgentCommAmt`, `TdsAmt`, `NetCommission` | `double` | Populated from `GridFillData` where `lblCommissionOn == "TP Premium"` | Commission % / Gross / TDS / Net on **TP Premium**. |
| `AgentComm_Extra`, `AgentCommAmt_Extra`, `TdsAmt_Extra`, `NetCommission_Extra` | `double` | Populated where `lblCommissionOn == "TP Premium Extra"` | Commission on **TP Premium Extra**. |
| `AgentComm_OD`, `AgentCommAmt_OD`, `TdsAmt_OD`, `NetCommission_OD` | `double` | Populated where `lblCommissionOn == "OD Premium"` | Commission on **OD Premium**. |
| `AgentComm_Net`, `AgentCommAmt_Net`, `TdsAmt_Net`, `NetCommission_Net` | `double` | Populated where `lblCommissionOn == "Net Premium"` | Commission on **Net Premium**. |
| `MotorOrNonMotor` | `string` | `"MOTOR"` (or `"NONMOTOR"`) | Line of business discriminator. |
| `FinancialYear` | `string` | `GetFinancialYear(Convert.ToDateTime(Txt_Date.Value))` | Formatted as `"YYYY-YYYY"` (e.g., `"2025-2026"`). |
| `TStatus` | `string` | `txt_Status.Value.ToUpper()` | Transaction status string. |

---

## 3. Financial Year Derivation Rules (And Confirmed March Boundary Bug)

### 3.1 Standard Rule (`PolicyTransactionNew.aspx.cs` L1119–1129 & `adm_NcbRecovery.aspx.cs` L23–28)
```csharp
protected string GetFinancialYear(DateTime PolicyDate)
{
    int year;
    if (PolicyDate.Month <= 3)
        year = PolicyDate.Year - 1;
    else
        year = PolicyDate.Year;
    string FinancialYear = year.ToString() + "-" + (year + 1).ToString();
    return FinancialYear;
}
```
- Months **January (`1`), February (`2`), and March (`3`)** map to `(Year - 1)-(Year)` (e.g., March 2026 -> `"2025-2026"`).
- Months **April (`4`) through December (`12`)** map to `(Year)-(Year + 1)` (e.g., April 2026 -> `"2026-2027"`).

### 3.2 Confirmed Legacy Defect in `PE_TransactionEntry.aspx.cs` (Lines 9820–9832)
In `AgentCommissionPaymentTableentry()` (`PE_TransactionEntry.aspx.cs` L9823):
```csharp
int currentMonth = DateTime.Now.Month;
int year = (DateTime.Now.Year);
if (currentMonth >= 3)
{
    string curryear = year + "-" + ((year) + 1);
    FYear = curryear;
}
else
{
    string curryear = (year - 1) + "-" + (year);
    FYear = curryear;
}
```
- **Forensic Finding**: Using `currentMonth >= 3` instead of `currentMonth > 3` (or `>= 4`) causes **March (`currentMonth == 3`)** to be assigned to the **next** financial year (`year + "-" + (year + 1)`) during renewal status updates and sales target updates (`BLL_Updatetargetachieved`)!

---

## 4. Hardcoded Insurer & Vehicle Special Cases During Booking

### 4.1 GCV + HDFC ERGO (`ddlVehicle == "2" && InsuranceCompanyid == 2 && PolicyTypeId > 18`)
**Evidence**: `PolicyTransactionNew.aspx.cs` (Lines 1033–1063, 1788–1857, 1889–1915)
- When booking a GCV (`VehicleType == 2`) with `InsuranceCompanyId == 2` and `PolicyTypeId > 18`:
  1. Invokes `GCVHDFCBankCalculatin(Flag)` where `Flag` is `"BROKER"`, `"AGENT"`, `"FRANCHISE"`, or `"FRANCHISE AGENT"`.
  2. Looks up commission rate strictly by `OD_Discount` range via `BLL_OD_Discount_Calculation.BLL_GetDiscountByRange(OD_Discount, Flag)`.
  3. Zeroes out TP, TP Extra, and OD commission fields (`Trans.AgentComm = 0`, `Trans.AgentComm_Extra = 0`, `Trans.AgentComm_OD = 0`) and applies the commission strictly on **`"Net Premium"`** (`Trans.AgentComm_Net`, `Trans.AgentCommAmt_Net`, `Trans.TdsAmt_Net`, `Trans.NetCommission_Net`).

### 4.2 Insurer ID `3` and `32` Exclusion from Automatic Inward Status Update
**Evidence**: `PE_TransactionEntry.aspx.cs` (Lines 9609–9619)
```csharp
if (int.Parse(ddl_company.SelectedItem.Value) != 3)
{
    if (int.Parse(ddl_company.SelectedItem.Value) != 32)
    {
        if (ddl_PaymentMode.SelectedItem.Text == "CASH" || ddl_PaymentMode.SelectedItem.Text == "ONLINE TO RELIABLE" || ddl_PaymentMode.SelectedItem.Text == "ONLINE TO INSURANCE COMPANY" || ddl_PaymentMode.SelectedItem.Text == "EMI" || ddl_PaymentMode.SelectedItem.Text == "ONLINE TO BROKER")
        {
            UpateInwardStatus(int.Parse(HidTransactionId.Value));
        }
    }
}
```
- **Rule**: When updating the Policy Number in `PE_TransactionEntry.aspx.cs`, `UpateInwardStatus` (`BLL_UpdateStatusForInvert`) is **skipped** if `InsuranceCompanyId` is `3` or `32`, or if the payment mode is `"CHEQUE"` / `"E-WALLET"`.

---

## 5. Booking Pre-Conditions & Commission Dependencies (`btnSave_Click`)

**Evidence**: `PolicyTransactionNew.aspx.cs` (Lines 1282–1442)

1. **Reliable Associates (Broker/Company) Commission Grid Mandatory**:
   - `if (GridFillData_RA.Rows.Count > 0)` is a hard gate for **all** policy bookings.
   - If `GridFillData_RA.Rows.Count == 0`, booking is blocked with alert: `'Commission Condition Not Fount for  Reliable Associates!'` (L1436).
2. **Agent Commission Grid Mandatory When `ReferenceType` is Agent (`ddl_Reference.SelectedIndex == 1`)**:
   - `if (GridFillData.Rows.Count > 0)` is required.
   - If `GridFillData.Rows.Count == 0`, booking is blocked with alert: `'Commission Condition Not Fount for this Agent!'` (L1417).
3. **E-Wallet Balance Gate When `PaymentMode == "E-WALLET"`**:
   - Calls `BLL_Transaction.BLL_AgentCommWalletBalance(AgentId)`.
   - Checks `if (balance > Convert.ToInt32(txtPaymentAmt.Value))` (strictly greater than `>`, integer comparison — L1293!).
   - If `balance <= PaymentAmt`, booking is blocked with alert: `'E-wallet Balace is Low than Your Payment Amount!'` (L1309).

---

## 6. Sales Executive Target & Renewal Follow-Up Side Effects on Policy Issuance

**Evidence**: `PE_TransactionEntry.aspx.cs` (`AgentCommissionPaymentTableentry` Lines 9834–9865)

Whenever a policy number is issued in `PE_TransactionEntry.aspx.cs`:
1. **Renewal Status Update**:
   - Checks `BLL_RenewalDashboard.BLL_UpdatePreYearRenewalStatus(Regno, FYear, "Select")`.
   - If a previous-year renewal follow-up exists, calls `BLL_UpdateAppPolicyCashStatus1(Regno, FYear, "Update")`.
2. **Sales Executive Target Achievement Update**:
   - Calls `BLL_Target.BLL_Updatetargetachieved(target)` with `EmpId = ddl_Sales`, `AchievedTargetAmount = NetPremium`, `month = DateTime.Now.ToString("MMMM")`, `financialYear = FYear`.
   - Inserts an audit row via `BLL_TargetHistory.BLL_InsertTargetHistory(target1)` with `Description = "created Policy for " + Regno + " - " + year + " - " + month`.
