# Phase 14 — Target REST API Endpoint Inventory

> **Audit Status**: COMPLETE (FORENSIC EXTRACTION)  
> **Phase**: Phase 14 (Reporting, Dashboard, MIS, POSP Invoicing & Statutory Statements) — Stage A  
> **Repository**: `Reliable-Insurance-Backend`  
> **Legacy Source**: `c:\Users\Admin\Downloads\InsurancefinalNew_2026_09_23\InsurancefinalNew`  
> **Mode**: STRICTLY READ-ONLY FORENSIC AUDIT (No implementation)

---

## 1. Executive Summary & Status Classification

This inventory specifies the target REST API contracts designed to cover the legacy reporting surface in Phase 14B.

- **Status**: **DESIGNED — PHASE 14B IMPLEMENTATION TARGET** (0% implemented in Stage A; strict audit boundary preserved).
- **Architecture Pipeline**:
  $$\text{Legacy Surface (WebForms/SP/Crystal)} \longrightarrow \text{Target API Contract (Pydantic/FastAPI)} \longrightarrow \text{Phase 14B Implementation}$$

Total Target Endpoints Specified: **27 Endpoints** across 5 functional routers:
1. `/api/v1/dashboards` (5 endpoints) — *DESIGNED — PHASE 14B TARGET*
2. `/api/v1/reports/mis` (3 endpoints) — *DESIGNED — PHASE 14B TARGET*
3. `/api/v1/reports/posp-invoices` (4 endpoints) — *DESIGNED — PHASE 14B TARGET*
4. `/api/v1/reports/accounting` & `/statutory` (8 endpoints) — *DESIGNED — PHASE 14B TARGET*
5. `/api/v1/reports/operations` & `/targets` & `/renewals` (7 endpoints) — *DESIGNED — PHASE 14B TARGET*

---

## 2. API Endpoint Specification Matrix

### 2.1 Dashboards (`/api/v1/dashboards`)

| Method | Endpoint Path | Summary | Allowed Roles | Key Parameters | Response Type |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/dashboards/admin` | Executive 12-Month Performance Matrix | `ADMIN`, `IT SUPPORT`, `ACCOUNT` | `financial_year: str`, `broker: Optional[str]`, `date_mode: Literal["T_Date", "R_Date"]`, `branch_id: Optional[int]` | `AdminDashboardResponse` |
| `GET` | `/api/v1/dashboards/accounts-summary` | Financial Collections & Payout Summary | `ADMIN`, `ACCOUNT` | `from_date: date`, `to_date: date`, `branch_id: Optional[int]` | `AccountsSummaryResponse` |
| `GET` | `/api/v1/dashboards/owner` | High-Level Channel & Broker Business | `ADMIN` | `from_date: date`, `to_date: date` | `OwnerDashboardResponse` |
| `GET` | `/api/v1/dashboards/agent-cut-pay` | Agent Cut & Pay Net Remittance Tracker | `ADMIN`, `ACCOUNT`, `LOCATION HEAD` | `financial_year: str`, `month: Optional[str]`, `branch_id: Optional[int]` | `CutAndPaySummaryResponse` |
| `GET` | `/api/v1/dashboards/agent-outstanding` | Agent Receivables & Overdue Aging | `ADMIN`, `ACCOUNT`, `LOCATION HEAD` | `min_days_overdue: int = 0`, `branch_id: Optional[int]` | `AgentOutstandingResponse` |

### 2.2 MIS Reports & Data Exports (`/api/v1/reports/mis`)

| Method | Endpoint Path | Summary | Allowed Roles | Key Parameters | Response Type |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/reports/mis/transactions` | Query Scoped Transaction Register | `ALL AUTHENTICATED` (Scoped) | `from_date: date`, `to_date: date`, `policy_no: Optional[str]`, `vehicle_no: Optional[str]`, `skip: int = 0`, `limit: int = 50` | `PagedTransactionReportResponse` |
| `GET` | `/api/v1/reports/mis/transactions/export` | Export Transactions to Native Excel / CSV | **`ADMIN`, `IT SUPPORT`, `ACCOUNT` ONLY** | `format: Literal["xlsx", "csv"]`, `from_date: date`, `to_date: date`, `broker: Optional[str]` | `StreamingResponse` (`.xlsx` or `.csv`) |
| `POST`| `/api/v1/reports/mis/reconcile-import` | Reconcile Staged Insurer Policy MIS | `ADMIN`, `IT SUPPORT` | `batch_id: int`, `tolerance: float = 1.00` | `MISReconcileResultResponse` |

### 2.3 POSP & Agent Invoicing (`/api/v1/reports/posp-invoices`)

| Method | Endpoint Path | Summary | Allowed Roles | Key Parameters | Response Type |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/reports/posp-invoices` | List Generated POSP Invoices | `ADMIN`, `ACCOUNT`, `AGENT` (Self) | `financial_year: Optional[str]`, `month: Optional[str]`, `agent_id: Optional[int]`, `skip: int = 0`, `limit: int = 50` | `PagedPospInvoiceResponse` |
| `POST`| `/api/v1/reports/posp-invoices/generate` | Generate New POSP Payout Invoice | `ADMIN`, `ACCOUNT` | Body: `PospInvoiceCreateRequest` (`agent_id`, `amount`, `posp_type`, `month`, `financial_year`) | `PospInvoiceDetailResponse` |
| `GET` | `/api/v1/reports/posp-invoices/{invoice_id}/pdf` | Download Official Invoice PDF | `ADMIN`, `ACCOUNT`, `AGENT` (Self) | Path: `invoice_id: int` | `StreamingResponse` (`application/pdf`) |
| `GET` | `/api/v1/reports/posp-invoices/payout-reconciliation` | Agent Payout Settlement Audit | `ADMIN`, `ACCOUNT` | `from_date: date`, `to_date: date`, `agent_id: Optional[int]`, `status: Optional[str]` | `PayoutReconciliationResponse` |

### 2.4 Statutory & Accounting Reports (`/api/v1/reports/accounting` & `/statutory`)

| Method | Endpoint Path | Summary | Allowed Roles | Key Parameters | Response Type |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/reports/statutory/tds` | Section 194H Statutory TDS Register | `ADMIN`, `ACCOUNT` | `from_date: date`, `to_date: date`, `agent_id: Optional[int]` | `TdsRegisterResponse` |
| `GET` | `/api/v1/reports/statutory/tds/export` | Export TDS Register to Excel | `ADMIN`, `ACCOUNT` | `from_date: date`, `to_date: date`, `agent_id: Optional[int]` | `StreamingResponse` (`.xlsx`) |
| `GET` | `/api/v1/reports/accounting/ledger-summary` | Tier 1 & 2: General Ledger Summaries | `ADMIN`, `ACCOUNT` | `from_date: date`, `to_date: date`, `ledger_type_id: Optional[int]` | `LedgerSummaryResponse` |
| `GET` | `/api/v1/reports/accounting/ledger-statement` | Tier 3: Ledger Detailed Statement | `ADMIN`, `ACCOUNT` | `from_date: date`, `to_date: date`, `ledger_m_id: int` | `LedgerStatementResponse` |
| `GET` | `/api/v1/reports/accounting/vouchers/{voucher_id}` | Tier 4: Fetch Voucher Details / PDF | `ADMIN`, `ACCOUNT` | Path: `voucher_id: int`, `format: Literal["json", "pdf"]` | `VoucherDetailResponse` or `StreamingResponse` |
| `GET` | `/api/v1/reports/accounting/payment-advice` | Agent Payment Advice Statement | `ADMIN`, `ACCOUNT`, `AGENT` (Self) | `financial_year: str`, `month: str`, `agent_id: int` | `PaymentAdviceResponse` |
| `GET` | `/api/v1/reports/accounting/bank-commission-statement` | Bank Bulk Payout Disbursement Sheet | `ADMIN`, `ACCOUNT` | `financial_year: str`, `month: str`, `branch_id: Optional[int]` | `StreamingResponse` (`.xlsx` or `.csv`) |
| `GET` | `/api/v1/reports/accounting/daily-collection` | Cashier Daily Cash & Online Audit | `ADMIN`, `ACCOUNT`, `LOCATION HEAD` | `report_date: date`, `branch_id: Optional[int]` | `DailyCollectionAuditResponse` |

### 2.5 Operations, Targets & Pipeline Reports (`/api/v1/reports/operations`, `/targets`, `/renewals`)

| Method | Endpoint Path | Summary | Allowed Roles | Key Parameters | Response Type |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/reports/operations/commission-reconciliation` | Insurer Commission Audit Statement | `ADMIN`, `ACCOUNT` | `from_date: date`, `to_date: date`, `company_id: Optional[int]` | `CommissionReconcileResponse` |
| `GET` | `/api/v1/reports/operations/bank-reconciliation` | Bank Reconciliation & Uncleared Cheques | `ADMIN`, `ACCOUNT` | `from_date: date`, `to_date: date`, `bank_id: Optional[int]` | `BankReconcileResponse` |
| `GET` | `/api/v1/reports/operations/endorsements` | Endorsements & Financial Deltas Log | `ADMIN`, `OPERATOR`, `LOCATION HEAD` | `from_date: date`, `to_date: date`, `branch_id: Optional[int]` | `PagedEndorsementReportResponse`|
| `GET` | `/api/v1/reports/operations/claims` | Claims Register & Settlement Tracking | `ADMIN`, `OPERATOR`, `LOCATION HEAD` | `from_date: date`, `to_date: date`, `status: Optional[str]` | `PagedClaimsReportResponse` |
| `GET` | `/api/v1/reports/targets/telecaller` | Telecaller Monthly Target Achievement | `ADMIN`, `LOCATION HEAD`, `TELECALLER` | `financial_year: str`, `month: str`, `user_id: Optional[int]` | `TelecallerTargetResponse` |
| `GET` | `/api/v1/reports/targets/executive` | Sales Executive Premium vs Quota | `ADMIN`, `LOCATION HEAD`, `SALES` | `financial_year: str`, `month: str`, `user_id: Optional[int]` | `ExecutiveTargetResponse` |
| `GET` | `/api/v1/reports/renewals/expiring-policies` | Real-Time Expiry Pipeline & Leads | `ADMIN`, `OPERATOR`, `TELECALLER` | `expiry_date: date`, `window_days: int = 30`, `branch_id: Optional[int]` | `ExpiringPoliciesResponse` |

---

## 3. Pydantic Request & Response Schema Contracts (Highlights)

```python
class PospInvoiceCreateRequest(BaseModel):
    agent_id: int
    posp_type: Literal["DIRECT", "POSP"]
    financial_year: str = Field(..., pattern=r"^\d{4}-\d{4}$")
    month: str = Field(..., max_length=20)
    amount: Decimal = Field(..., gt=0)
    custom_invoice_no: Optional[str] = None

class PospInvoiceDetailResponse(BaseModel):
    invoice_id: int
    invoice_no: str
    invoice_date: date
    agent_id: int
    agent_name: str
    posp_type: str
    financial_year: str
    month: str
    amount: Decimal
    gst_amt: Decimal
    grand_total: Decimal
    tds_amount: Decimal
    net_payable: Decimal
    status: str
    created_at: datetime
```
