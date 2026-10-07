# Phase 7 — Policy Booking & Transaction Engine: REST API Contract

**Phase:** 7 — Policy Booking & Transaction Engine  
**Stage:** A8 — FastAPI Endpoint & Pydantic v2 Schema Specification  
**Base Prefix:** `/api/v1/policies`

---

## 1. Endpoint Summary

| # | Method & Path | Status Code | Purpose | Auth / Role Gate |
|---:|---|---:|---|---|
| 1 | `POST /api/v1/policies/preview` | `200 OK` | Preview & revalidate full policy financials (Premium, NCB, OD Discount, GST, Commission, Cut & Pay, Payment Balance, Accounting Entries) without writing to DB. | `POLICY_PROPOSAL_WRITE_ROLES` |
| 2 | `POST /api/v1/policies/proposals` | `201 Created` | Submit a staged Policy Proposal (`tbl_transactionappnew`, `Sp_InsertAppTransctiondetailsNew8` parity). | `POLICY_PROPOSAL_WRITE_ROLES` |
| 3 | `GET /api/v1/policies/proposals` | `200 OK` | List staged Policy Proposals with branch & principal scope filtering. | `POLICY_BOOKING_READ_ROLES` |
| 4 | `GET /api/v1/policies/proposals/{trans_id}` | `200 OK` | Retrieve a single staged Policy Proposal by `TransId`. | `POLICY_BOOKING_READ_ROLES` |
| 5 | `POST /api/v1/policies/proposals/{trans_id}/approve` | `200 OK` | Approve or reject a staged proposal at `CASHIER`, `ACCOUNTANT`, or `OWNER` gate. | Stage-specific approval roles |
| 6 | `POST /api/v1/policies/book` | `201 Created` | Atomically book a policy transaction (`tbl_transaction` + `InwardNo` + `tbl_transactionpayment` + commission tables + `tbl_account` `AccTransId=1,2,3`). | `POLICY_BOOKING_WRITE_ROLES` |
| 7 | `GET /api/v1/policies` | `200 OK` | List/search booked policies (`tbl_transaction`) with pagination and scope isolation. | `POLICY_BOOKING_READ_ROLES` |
| 8 | `GET /api/v1/policies/{transaction_id}` | `200 OK` | Get full booked policy detail including payment instruments, commission rows, and accounting entries. | `POLICY_BOOKING_READ_ROLES` |
| 9 | `PUT /api/v1/policies/{transaction_id}` | `200 OK` | Update policy underwriting metadata (`PolicyNo`, dates, status, commission adjustment). | `POLICY_BOOKING_WRITE_ROLES` |
| 10 | `POST /api/v1/policies/{transaction_id}/payments` | `201 Created` | Record an additional payment instrument (`tbl_transactionpayment`) against an existing policy and update `PaidAmount` / `OutstandingAmount` / `tbl_account`. | `POLICY_PAYMENT_WRITE_ROLES` |
| 11 | `POST /api/v1/policies/{transaction_id}/cancel` | `200 OK` | Cancel / soft-delete a booked policy (`isdeleted=1`, `TStatus="Cancelled"`) and reverse associated payment, commission, and accounting rows atomically. | `POLICY_DELETE_ROLES` |

---

## 2. Core Request & Response Contracts

### 2.1 `POST /api/v1/policies/preview` & `POST /api/v1/policies/book`

#### Request Schema (`PolicyBookingCreateRequest`)
All monetary and percentage fields are strictly `Decimal` (no `float`):
- **Linkage & Identity:**
  - `idempotency_key: Optional[str]` (optional client key to prevent duplicate submission)
  - `customer_id: int` (required for `/book`; optional for `/preview`)
  - `cust_veh_id: int` (required for `/book`; optional for `/preview`)
  - `quotation_id: Optional[int]` (optional link to Phase 6 `tbl_app_quatationentry.QuatationId` or `tbl_app_quotationrequest.QuatationId`)
  - `quotation_source_type: Optional[Literal["SELF_QUOTATION", "ASSISTED_REQUEST"]]`
  - `proposal_trans_id: Optional[int]` (optional link to staged `tbl_transactionappnew.TransId`)
- **Underwriting & Policy Metadata:**
  - `insurance_company_id: int`
  - `policy_type_id: int = 1` (`1`=Package/Comprehensive, `2`=TP Only, `3`=SAOD)
  - `product_type_id: int = 1` (`1`=Comprehensive, `2`=Liability Only STP, `3`=SAOD)
  - `business_type_id: int = 3` (`1`=New, `2`=Renewal, `3`=Roll Over)
  - `policy_no: Optional[str]` (unique per active insurer when provided)
  - `trans_date: Optional[date]` (defaults to `date.today()`)
  - `cn_issue_date: Optional[date]`
  - `risk_start_date: date`
  - `expiry_date: Optional[date]` (defaults to `risk_start_date + 1 year - 1 day`)
  - `vehicle_category: str = "PVT"`
  - `gcv_split_tp_gst: bool = True`
  - `claim_in_previous_policy: bool = False`
- **Rating / Premium Inputs (Either `calculation_input` OR Quotation Prefill OR Direct Underwriting Figures):**
  - `calculation_input: Optional[PremiumCalculationRequest]`
  - `sum_insured_idv: Optional[Decimal]`
  - `gvw: Decimal = Decimal("0.00")`
  - `od_premium: Optional[Decimal]` (`ODPermium`)
  - `tp_premium: Optional[Decimal]` (`TPPermium`)
  - `basic_tp_premium: Optional[Decimal]` (used for GCV 12% GST split when direct figures are supplied)
  - `net_premium: Optional[Decimal]` (`NetPermium`)
  - `gst_amount: Optional[Decimal]` (`GST_Amount`)
  - `final_premium: Optional[Decimal]` (`Amount`)
  - `ncb_percent: Decimal = Decimal("0.00")`
  - `ncb_amount: Decimal = Decimal("0.00")` (`NCBPermium`)
  - `od_discount_percent: Decimal = Decimal("0.00")` (`ODDiscount`)
  - `addon_rate_percent: Decimal = Decimal("0.00")` (`AddOnRate`)
  - `addon_premium: Decimal = Decimal("0.00")` (`AddOn`)
  - `is_nill_dep: bool = False` (`IsNill`)
  - `imt23_amount: Decimal = Decimal("0.00")` (`Imt23`)
  - `towing_amount: Decimal = Decimal("0.00")` (`TowingChargesAmt`)
  - `rsa_amount: Decimal = Decimal("0.00")` (`RoadSidePremium`)
  - `pa_owner_driver: Decimal = Decimal("0.00")` (`PACovertoOwner`)
  - `ll_paid_driver: Decimal = Decimal("0.00")` (`LegalLiabilitytoPaidDriver`)
  - `pa_driver_cleaner: Decimal = Decimal("0.00")` (`PACoverDriverCleaner`)
  - `allow_underwriting_override: bool = False`
  - `validate_statutory_gst: bool = True`
- **Commission Inputs (`CommissionInput`):**
  - `agent_id: Optional[int]`
  - `sales_ex_id: Optional[int]`
  - `franchise_id: Optional[int]`
  - `location_head_id: Optional[int]`
  - `agent_comm_percent: Decimal = Decimal("0.00")`
  - `agent_comm_od_percent: Decimal = Decimal("0.00")`
  - `agent_comm_net_percent: Decimal = Decimal("0.00")`
  - `agent_comm_extra_percent: Decimal = Decimal("0.00")`
  - `tds_percent: Decimal = Decimal("5.00")`
  - `commission_on_full_net: bool = False`
- **Payment Inputs:**
  - `policy_mode_id: int = 1`
  - `cutnpay_enabled: bool = False` (`CutNPay`)
  - `cutnpay_amount: Optional[Decimal] = None`
  - `ewallet_amount_used: Decimal = Decimal("0.00")`
  - `online_payment_to_company: Decimal = Decimal("0.00")`
  - `payments: List[PaymentInstrumentCreateRequest] = []`

#### Response Schema (`PolicyBookingResponse`)
- `transaction_id: int` (`TransanctionId`)
- `inward_no: str` (`InwardNo`)
- `trans_date: date`
- `branch_id: int`
- `financial_year: str`
- `customer_id: int`
- `cust_veh_id: int`
- `insurance_company_id: int`
- `policy_type_id: int`
- `product_type_id: int`
- `business_type_id: int`
- `policy_no: Optional[str]`
- `risk_start_date: Optional[date]`
- `expiry_date: Optional[date]`
- `due_date: Optional[date]` (`DeuDate`)
- `quotation_code: Optional[str]` (`QuatationCode`)
- `proposal_trans_id: Optional[int]` (`TransId`)
- `t_status: str` (`TStatus`)
- `pending_status: str` (`pendingStatus`)
- `premium_summary: PolicyPremiumSummary` (`sum_insured_idv`, `od_premium`, `tp_premium`, `net_premium`, `gst_amount`, `final_premium`, `ncb_percent`, `ncb_amount`, `od_discount_percent`, `addon_premium`, `imt23_amount`, `towing_amount`, `pa_owner_driver`, `ll_paid_driver`)
- `commission_summary: PolicyCommissionSummary` (`agent_comm_od_percent`, `agent_comm_od_amount`, `tds_od_amount`, `net_comm_od_amount`, `agent_comm_net_percent`, `agent_comm_net_amount`, `tds_net_amount`, `net_comm_net_amount`, `agent_comm_extra_percent`, `agent_comm_extra_amount`, `tds_extra_amount`, `net_comm_extra_amount`, `total_gross_commission`, `tds_percent`, `total_tds_amount`, `total_net_commission`, `franchise_comm_id`, `cutnpay_payable_id`, `agent_comm_pay_id`)
- `payment_summary: PolicyPaymentSummary` (`gross_payable_amount`, `cutnpay_enabled`, `cutnpay_deduction`, `ewallet_amount_used`, `online_payment_to_company`, `required_payable_amount`, `paid_amount`, `outstanding_amount`, `is_complete_payment`, `payments: List[PaymentInstrumentResponse]`)
- `accounting_entries: List[AccountingEntryResponse]` (`account_id`, `acc_trans_id`, `transaction_type`, `amount`, `credit`, `debit`, `final_balance`, `description`)

---

## 3. HTTP Error Semantics

| Scenario | HTTP Status | Error Detail |
|---|---:|---|
| Unauthenticated / Missing or invalid JWT | `401 Unauthorized` | `"Not authenticated"` |
| Caller's role is not in endpoint's allowed role set | `403 Forbidden` | `"Role '...' is not authorized for this resource"` |
| Cross-branch customer/vehicle/policy access by non-global role | `403 Forbidden` | `"Access denied: Resource belongs to another branch"` |
| Cross-principal (`AgentId` / `EmpId` / `FranchiseId`) access | `403 Forbidden` | `"Access denied: Policy is outside your ownership scope"` |
| Customer, Vehicle, Quotation, Proposal, or Policy not found | `404 Not Found` | `"Customer/Vehicle/Quotation/Policy not found"` |
| Duplicate `PolicyNo` for active insurer, or Quotation/Proposal already consumed into an active policy | `409 Conflict` | `"Duplicate PolicyNo ..."` or `"Quotation ... is already booked"` |
| Invalid NCB slab, NCB on new/claimed policy, `NetPermium != ODPermium + TPPermium`, GST mismatch, overpayment, negative amount, or missing cheque details | `422 Unprocessable Entity` | Detailed mathematical or business validation message |
