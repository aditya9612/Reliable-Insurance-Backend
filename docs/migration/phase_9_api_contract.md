# Phase 9 — FastAPI REST API Contract Specification (Commission & Accounting Engine)

**Repository**: `Reliable-Insurance-Backend`  
**Phase**: `Phase 9 — Commission & Accounting Engine (Stage A12)`  
**Target Runtime Database**: `localhost:3306/reliable_insurance_dev`

---

## 1. Endpoint Catalog (`/api/v1/commissions`, `/api/v1/commission-payouts`, `/api/v1/accounting`)

All endpoints require a valid Bearer JWT (`401 Unauthorized` if missing/invalid) and enforce role-based and principal/branch scoping (`403 Forbidden` on violation).

| # | HTTP Method & Path | Legacy Operation / SP Equivalent | Role Gate | Purpose |
|---:|---|---|---|---|
| 1 | `POST /api/v1/commissions/calculate` | `PolicyTransactionNew.aspx.cs` commission & TDS calculator | `COMMISSION_CALCULATE_ROLES` | Stateless multi-bucket Agent & Franchise commission, 5% TDS, Cut & Pay, and `ProfitofNetCommision` calculation |
| 2 | `GET /api/v1/commissions` | `sp_GetAgentCommission` | `COMMISSION_READ_ROLES` | List & filter Agent (`tbl_agentcommissionpayment`), Franchise (`tbl_franchisecommission`), and Cut & Pay (`tbl_cutnpaycommpayable`) commission records |
| 3 | `GET /api/v1/commissions/transactions/{transaction_id}` | `PolicyTransactionNew.aspx.cs` / `AgentCommisionApproval.aspx.cs` | `COMMISSION_READ_ROLES` | Full commission, TDS, Cut & Pay, payable balance, and accounting ledger summary for a policy transaction |
| 4 | `POST /api/v1/commissions/{commission_type}/{commission_id}/approve` | `sp_UpdateAgentCommissionApproval` | `COMMISSION_APPROVAL_ROLES` | Approve an Agent (`AGENT`) or Franchise (`FRANCHISE`) commission record for payout (`CommProcessSubmit = 1`) |
| 5 | `POST /api/v1/commissions/transactions/{transaction_id}/release-hold` | `ChequeClearance.aspx.cs` commission hold release | `COMMISSION_APPROVAL_ROLES` | Release `HOLD_CHEQUE_BOUNCE` on Cut & Pay and Agent Commission once policy `OutstandingAmount == 0.00` and cheque is cleared |
| 6 | `POST /api/v1/commissions/{commission_type}/{commission_id}/reverse` | `adm_DeletePolicyTransaction.aspx.cs` commission reversal | `COMMISSION_PAYOUT_WRITE_ROLES` | Reverse an accrued Agent or Franchise commission and post contra reversal entry (`AccTransId = 7`) in `tbl_account` |
| 7 | `GET /api/v1/commission-payouts` | `AgentCommisionApproval.aspx.cs` payout register | `COMMISSION_READ_ROLES` | List commission payout vouchers (`AccTransId = 6`) with principal/branch/date filters |
| 8 | `GET /api/v1/commission-payouts/{doc_no}` | `AgentCommisionApproval.aspx.cs` voucher detail | `COMMISSION_READ_ROLES` | Retrieve single commission payout voucher by `doc_no` (`tbl_account.Doc_No`) |
| 9 | `POST /api/v1/commission-payouts` | `sp_UpdateAgentCommissionApproval` / `sp_UpdateAgentWalletBalance` | `COMMISSION_PAYOUT_WRITE_ROLES` | Execute atomic individual (full or partial) Agent or Franchise commission payout and generate double-entry voucher (`AccTransId = 6`) |
| 10 | `POST /api/v1/commission-payouts/bulk` | `AgentCommisionApproval.aspx.cs::btn_BulkPayout_Click` | `COMMISSION_PAYOUT_WRITE_ROLES` | Execute atomic bulk multi-agent / multi-franchise commission payout batch |
| 11 | `POST /api/v1/commission-payouts/{doc_no}/reverse` | Commission payout clawback / reversal | `COMMISSION_PAYOUT_WRITE_ROLES` | Atomically reverse a commission payout voucher (`AccTransId = 7`), restore unpaid payable balance, and debit E-Wallet if paid via `EWALLET` |
| 12 | `GET /api/v1/accounting/ledgers` | `tbl_ledgermaster` lookup | `ACCOUNTING_READ_ROLES` | List master & partner sub-ledgers (`tbl_ledgermaster`) |
| 13 | `POST /api/v1/accounting/ledgers` | `sp_InsertAccountDetails` ledger provisioning | `ACCOUNTING_VOUCHER_WRITE_ROLES` | Get-or-create a master or partner sub-ledger in `tbl_ledgermaster` |
| 14 | `GET /api/v1/accounting/ledgers/{ledger_m_id}/statement` | `sp_GetLedgerStatement` / `GetWalletLedger` | `ACCOUNTING_READ_ROLES` | Chronological ledger statement with `opening_balance`, `debit_amount`, `credit_amount`, `running_balance`, and `closing_balance` |
| 15 | `GET /api/v1/accounting/trial-balance` | `TrialBalanceReport.aspx.cs` | `TRIAL_BALANCE_READ_ROLES` | Branch or company-wide Trial Balance verifying `Total Debit == Total Credit` (`variance == 0.00`) |
| 16 | `GET /api/v1/accounting/vouchers` | `AccountVoucherEntry.aspx.cs` list | `ACCOUNTING_READ_ROLES` | List double-entry accounting vouchers |
| 17 | `POST /api/v1/accounting/vouchers` | `sp_InsertAccountDetails` voucher creation | `ACCOUNTING_VOUCHER_WRITE_ROLES` | Create a balanced double-entry accounting voucher (`JOURNAL`, `PAYMENT`, `RECEIPT`, `CONTRA`) with concurrency-safe `VCH-...` numbering |
| 18 | `POST /api/v1/accounting/vouchers/{doc_no}/reverse` | `AccountVoucherEntry.aspx.cs` voucher reversal | `ACCOUNTING_VOUCHER_WRITE_ROLES` | Atomically reverse an accounting voucher by posting offsetting Debit/Credit lines |

---

## 2. Core Request & Response Payloads (`app/schemas/commission_accounting.py`)

### 2.1 `POST /api/v1/commissions/calculate` (`CommissionCalculateRequest` $\rightarrow$ `CommissionCalculateResponse`)
- **Request**:
  - `od_premium: Decimal`, `tp_premium: Decimal`, `pa_owner_driver: Decimal = 0.00`, `net_premium: Optional[Decimal] = None`, `gst_amount: Optional[Decimal] = None`, `final_premium: Optional[Decimal] = None`
  - `agent_id: int = 0`, `franchise_id: int = 0`, `sales_ex_id: int = 0`, `location_head_id: int = 0`
  - `agent_comm_percent: Decimal = 0.00`, `agent_comm_od_percent: Decimal = 0.00`, `agent_comm_net_percent: Decimal = 0.00`, `agent_comm_extra_percent: Decimal = 0.00`
  - `franchise_comm_od_percent: Optional[Decimal] = None`, `franchise_comm_net_percent: Optional[Decimal] = None`, `franchise_comm_extra_percent: Optional[Decimal] = None`
  - `tds_percent: Decimal = 5.00`, `include_pa_in_tp_comm: bool = False`, `commission_on_full_net: bool = False`
  - `cutnpay_enabled: bool = False`, `cutnpay_amount: Optional[Decimal] = None`
  - `self_discount: Decimal = 0.00`, `incentive_amount: Decimal = 0.00`
- **Response**:
  - Complete bucket-by-bucket breakdown (`od`, `net`, `extra`), `total_gross_commission`, `total_tds_amount`, `total_net_commission`, `franchise_gross_commission`, `franchise_tds_amount`, `franchise_net_commission`, `profit_of_net_commission`, `cutnpay_deduction`, `agent_remaining_payable`, `customer_required_payable`.

### 2.2 `POST /api/v1/commission-payouts` (`CommissionPayoutCreateRequest` $\rightarrow$ `CommissionPayoutResponse`)
- **Request**:
  - `commission_type: Literal["AGENT", "FRANCHISE"] = "AGENT"`
  - `commission_id: Optional[int] = None` (`AgentCommId` or `FranchiseCommId`)
  - `transaction_id: Optional[int] = None` (alternative lookup by policy `TransanctionId`)
  - `payout_amount: Optional[Decimal] = None` (defaults to full remaining payable balance; supports partial payout when `< remaining_payable`)
  - `payout_mode: Literal["NEFT", "RTGS", "ONLINE", "UPI", "CHEQUE", "CASH", "EWALLET"] = "NEFT"`
  - `payment_ref: Optional[str] = None`
  - `narration: Optional[str] = None`
  - `idempotency_key: Optional[str] = None`
  - `simulate_failure_at: Optional[Literal["AFTER_COMMISSION_UPDATE", "DURING_VOUCHER", "BEFORE_COMMIT"]] = None`
- **Response**:
  - `doc_no: int`, `voucher_no: str`, `commission_type: str`, `commission_id: int`, `transaction_id: int`, `principal_id: int`, `gross_commission: Decimal`, `tds_amount: Decimal`, `total_net_commission: Decimal`, `payout_amount: Decimal`, `cumulative_paid_amount: Decimal`, `remaining_payable_amount: Decimal`, `payout_status: Literal["PAID", "PARTIAL", "REVERSED"]`, `payout_mode: str`, `accounting_entries: List[AccountingEntryResponse]`.
