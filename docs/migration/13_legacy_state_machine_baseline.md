# 13 — Legacy State Machine Baseline (Phases 5–10)

> **Audit Status**: CONFIRMED FROM CODE
> **Primary Evidence**: `SelfQuotationRequest.aspx.cs`, `PolicyTransactionNew.aspx.cs`, `PE_TransactionEntry.aspx.cs`, `adm_NcbRecovery.aspx.cs`, `ViewAppTransEwalletApproval.aspx.cs`, `AppEndorsementforApproval.aspx.cs`, `adm_PolicyCancel.aspx.cs`, `CL_ClaimNew.aspx.cs`

---

## 1. Quotation State Machine (Phase 6)

```
[Draft Input on UI]
       |
       | GetQuotationPremium(CompanyId)
       v
[Calculated Preview (In-Memory Labels)]
       |
       | btnShow_Onclick / btnEntry1_Click -> SaveData(cmpId)
       | Calls BLL_GetQuotationCodeForSelfQuot() & BLL_InsertAppQuotationEntry(QS)
       v
[Saved Self-Quotation (Quot_type = "SQ", QuatationCode generated)]
       |
       | Referenced by App Policy Request / Clerk Policy Entry (FillQuatationData)
       v
[Converted to Policy Request / Transaction (QuatationCode linked on API_Transaction)]
```

---

## 2. Policy & Inward Transaction State Machine (Phase 7)

**Evidence**: `PolicyTransactionNew.aspx.cs` (L960–1435), `PE_TransactionEntry.aspx.cs` (L9574–9813), `adm_NcbRecovery.aspx.cs` (L1017–1071), `adm_PolicyCancel.aspx.cs` (L820–1060)

```
                  +---------------------------------------+
                  | 1. App Policy Request / MIS Import    |
                  |    (TransId created; PolicyNo blank)  |
                  +---------------------------------------+
                                      |
          +---------------------------+---------------------------+
          | Payment / Pre-Account / E-Wallet / Cheque Approvals   |
          v                                                       v
+-----------------------------------+           +-----------------------------------+
| 2A. Direct Clerk Booking          |           | 2B. Post-Entry Policy Issuance    |
| (`PolicyTransactionNew.aspx.cs`)  |           | (`PE_TransactionEntry.aspx.cs`)   |
| Generates `InwardNo`, inserts     |           | Calls `BLL_UpdatePolicyNo`        |
| `API_Transaction` (`TransactionId`)|          | Calls `BLL_UpdateStatusForInvert` |
+-----------------------------------+           | (except CompanyId 3 & 32 or Cheque)|
          |                                     +-----------------------------------+
          +---------------------------+---------------------------+
                                      |
                                      v
                  +---------------------------------------+
                  | 3. Active / Issued Policy             |
                  | (`PolicyNo` populated; Inward active) |
                  +---------------------------------------+
                                      |
         +----------------------------+----------------------------+
         |                            |                            |
         v                            v                            v
+--------------------+     +----------------------+     +-----------------------+
| 4A. Endorsed       |     | 4B. NCB Recovery     |     | 4C. Cancelled         |
| (`BLL_Update       |     | (`BLL_InsertNCB      |     | (`adm_PolicyCancel` / |
|  Endorsement`)     |     |  Recovery`)          |     |  `"PolicyCancel"`)    |
+--------------------+     +----------------------+     +-----------------------+
```

---

## 3. Payment, Cash & Cheque Approval State Machine (Phase 8)

**Evidence**: `PolicyTransactionNew.aspx.cs` (L1168–1195), `adm_NcbRecovery.aspx.cs` (L414–755), `PE_TransactionEntry.aspx.cs` (L10141–10190)

### 3.1 `API_TransactionPayment` Initial State by `PaymentType`
| `PaymentType` | `CashierApproval` | `AccountantApproval` | `OwnerApproval` | Next Required Transition |
| :--- | :--- | :--- | :--- | :--- |
| `"CASH"` | `0` | `0` | `0` | Pre-Premium Cash Approval (`IsAccountApproval=1`) -> Branch Cash Deposit (`IsActivePendingCash=1`, `PremiumCashToBank=1`) -> Cashier Approval (`CashierApproval=1`). |
| `"CHEQUE"` | `1` | `0` | `0` | Customer Cheque Clearing (`AccountantApproval=1` via `AccountantApproval.aspx.cs` / `Rpt_viewChequeClearing.aspx.cs`) OR Cheque Bounce/Cancel (`ReturnUnclearingCheque`). |
| `"E-WALLET"` | `1` | `1` | `1` | E-Wallet Account Approval (`ViewAppTransEwalletApproval.aspx.cs` -> `BLL_UpdateAppPolicyAccountApproval1` with `"Cheque"`, `"OlRA"`, or `"Float"`). |
| `"ONLINE TO RELIABLE"` | `1` | `1` | `1` | Online-to-RA Approval (`OnlintoRAEntry` -> `BLL_PaymentApproval(..., "ONLINETORA")` -> `UpdateTransactionOfCutNPay` or `CashGoToPayment`). |
| `"ONLINE TO INSURANCE COMPANY"` / `"EMI"` / `"ONLINE TO BROKER"` | `1` | `1` | `1` | Direct insurer/broker settlement; moves directly to `UpateInwardStatus` and commission processing. |

---

## 4. Commission & Payout State Machine (Phase 9)

**Evidence**: `PolicyTransactionNew.aspx.cs` (L1319–1406), `PE_TransactionEntry.aspx.cs` (L9635–10031), `adm_NcbRecovery.aspx.cs` (L322–331, L1017–1071), `adm_PolicyCancel.aspx.cs` (L888–1060)

| State Name | Discriminator / Flag in DB | Entry Trigger | Accounting Entries (`API_Account`) |
| :--- | :--- | :--- | :--- |
| **1. Unclear Cheque Provisional** | `AccTransId = 3`, `Narration = "Policy account for unclear amount"` | Policy booked with `PaymentMode == "CHEQUE"` (`PolicyTransactionNew.aspx.cs` L1319). | Credits (`-netcomm`) posted to Agent Ledger, RA Ledger (`FranchiseId=1`), and Sub-Franchise Ledger. |
| **2. Commission Accrued / In Process (`UNPAID`)** | `PaidStatus == "0"` (`"UNPAID"`); `BLL_UpdateAgentCommissionPay(TransId, "AgentCommProcess")`; `API_AgentCommPayment.PaymentStatus = "1"` | Policy No updated in `PE_TransactionEntry.aspx.cs` (L9866–10028) OR Approved with `"Full Payement"` in `adm_NcbRecovery.aspx.cs` (L1024). | `AccTransId = 3`:<br>- Debit `1161` (`+GrossComm`)<br>- Credit `2113` (`-TDS`)<br>- Credit `AgentLedger` (`-NetComm`) |
| **3. Cut & Pay Settled (`PAID`)** | `PaidStatus == "1"` (`"PAID"`); `BLL_UpdateAgentCommissionPay(TransId, "AgentCommPay")` | Approved in `adm_NcbRecovery.aspx.cs` (L1032) when `lblCashType != "Full Payement"` (i.e. Cut & Pay). | Agent already retained commission from premium remittance. |
| **4. Disbursed / Paid Out (`PAID`)** | `PaidStatus == "1"` (`"PAID"`) | Paid via `AgentCommisionPayment.aspx.cs` / Voucher Entry. | `AccTransId = 1` / `2`: Debits Agent Ledger, Credits Bank/Cash Ledger. |
| **5. Cancelled / Commission Recoverable** | `BLL_UpdateAgentCommissionPay(TransId, "PolicyCancel")`; `ReturnUnclearingCheque` (`adm_PolicyCancel.aspx.cs`) | Policy rejected in `adm_NcbRecovery.aspx.cs` (L1066) or cancelled in `adm_PolicyCancel.aspx.cs` (L888). | Negates `API_franchaiseCommission`. Posts `AccTransId = 3` reversal (`-netcomm` to `1161`, `+netcomm` to `AgentLedger`) + `API_ClearingAccount`. If `commPaid == 1`, narration becomes `"Commission Recoverable for Reg.No ..."`. |

---

## 5. Claims State Machine (Phase 10A)

**Evidence**: `Insurance\Clerk\CL_ClaimNew.aspx.cs` (Lines 165–700)

```
[Claim Intimated / Registered (Active Claim in `BLL_SelectAllClaimsnew`)]
       |
       +---> [Spot Survey Added (`BLL_Claims_SpotServe`)]
       |
       +---> [Garage Survey Added (`BLL_Claims_GarageServe`)]
       |
       +---> [Repair Quotation Uploaded (`BLL_ClaimQuotaionInsert`, `QuotStatus`)]
       |
       +---> [Audio Recordings Logged (`BLL_ClaimAudio`)]
       |
       +---> [Final Bill Submitted (`BLL_Claim_FINALBILL_Insert`: `BillAmt`, `ICLAmt`, `ILAmt`)]
       |
       v
[Claim Closed (`BLL_SelectAll_ClosedClaimsnew`)]
```
