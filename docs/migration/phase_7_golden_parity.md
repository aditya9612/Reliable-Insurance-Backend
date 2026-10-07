# Phase 7 — Golden Parity Verification Results (25 Deterministic Synthetic Cases)

**Phase:** 7 — Policy Booking & Transaction Engine  
**Stage:** C — Golden Parity Verification (`G7-01` through `G7-25`)  
**Execution Environment:** `localhost:3306/reliable_insurance_dev` (100% Synthetic Data)  
**Test Suite:** [`tests/integration/test_phase7_golden_parity.py`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/tests/integration/test_phase7_golden_parity.py)

---

## 1. Golden Parity Summary

All **25 deterministic synthetic golden test cases** (`G7-01` .. `G7-25`) executed against the local MySQL instance (`reliable_insurance_dev`) achieved a **`0.00` financial delta** across:
- `ODPermium`, `TPPermium`, `NetPermium`, `GST_Amount`, `Amount`, `NCBPermium`, `ODDiscount`
- `AgentCommAmt_OD`, `TdsAmt_OD`, `NetCommission_OD`, `AgentCommAmt_Net`, `TdsAmt_Net`, `NetCommission_Net`, `AgentCommAmt_Extra`, `TdsAmt_Extra`, `NetCommission_Extra`, `AgentCommAmt`, `TdsAmt`, `NetCommission`
- `FranchiseCommAmt`, `FranchiseTdsAmt`, `FranchiseNetComm` (`tbl_franchisecommission`)
- `CommPayable`, `Balance` (`tbl_cutnpaycommpayable`)
- `PaidAmount`, `OutstandingAmount`, `isCompletePayment` (`tbl_transaction` & `tbl_transactionpayment`)
- Double-entry accounting ledger rows (`tbl_account` `AccTransId = 1` `+Amount`, `AccTransId = 2` `+PaidAmount`, `AccTransId = 3` `-NetCommission`).

---

## 2. Master 25-Case Golden Parity Table

| Case ID | Scenario / Vehicle Category | Product / Business Type | Net Premium (`₹`) | GST (`₹`) | Final Payable (`₹`) | Gross Comm (`₹`) | TDS 5% (`₹`) | Net Comm (`₹`) | `AccTransId=3` (`₹`) | Outstanding (`₹`) | Delta (`₹`) | Status |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| **G7-01** | Private Car (`PVT`) Comprehensive, 20% NCB, 40% OD Disc | Package / Roll Over | `12,296.00` | `2,213.00` | `14,509.00` | `1,464.80` | `73.24` | `1,391.56` | `-1,391.56` | `0.00` | `0.00` | `PASS` |
| **G7-02** | Private Car (`PVT`) Liability Only (STP), 0% OD/NCB | TP Only / Roll Over | `3,796.00` | `683.00` | `4,479.00` | `379.60` | `18.98` | `360.62` | `-360.62` | `0.00` | `0.00` | `PASS` |
| **G7-03** | Private Car (`PVT`) Standalone OD (`SAOD`), 25% NCB, Cheque | SAOD / Renewal | `9,200.00` | `1,656.00` | `10,856.00` | `2,024.00` | `101.20` | `1,922.80` | `-1,922.80` | `0.00` | `0.00` | `PASS` |
| **G7-04** | Private Car (`PVT`) New Vehicle (`business_type_id=1`), 0% NCB | Package / New | `23,000.00` | `4,140.00` | `27,140.00` | `2,700.00` | `135.00` | `2,565.00` | `-2,565.00` | `0.00` | `0.00` | `PASS` |
| **G7-05** | Private Car (`PVT`) Previous Claim (`claim=True`), 0% NCB | Package / Renewal | `13,416.00` | `2,415.00` | `15,831.00` | `1,500.00` | `75.00` | `1,425.00` | `-1,425.00` | `0.00` | `0.00` | `PASS` |
| **G7-06** | Two-Wheeler (`TwoWheeler`) Comprehensive, 35% NCB | Package / Roll Over | `1,739.00` | `313.00` | `2,052.00` | `184.45` | `9.22` | `175.23` | `-175.23` | `0.00` | `0.00` | `PASS` |
| **G7-07** | Two-Wheeler (`TwoWheeler`) Liability Only (TP), UPI | TP Only / Roll Over | `1,089.00` | `196.00` | `1,285.00` | `108.90` | `5.45` | `103.45` | `-103.45` | `0.00` | `0.00` | `PASS` |
| **G7-08** | Public GCV (`Public_GCV`) Split GST (12% Basic TP + 18% OD) | Package / Roll Over | `45,500.00` | `6,690.00` | `52,190.00` | `4,020.00` | `201.00` | `3,819.00` | `-3,819.00` | `0.00` | `0.00` | `PASS` |
| **G7-09** | Private GCV (`Private_GCV`) Split GST (12% TP + 18% OD) | Package / Roll Over | `27,000.00` | `3,960.00` | `30,960.00` | `1,200.00` | `60.00` | `1,140.00` | `-1,140.00` | `0.00` | `0.00` | `PASS` |
| **G7-10** | 3W Goods (`PublicGCV3W`) Split GST (12% TP + 18% OD) | Package / Roll Over | `7,500.00` | `1,080.00` | `8,580.00` | `360.00` | `18.00` | `342.00` | `-342.00` | `0.00` | `0.00` | `PASS` |
| **G7-11** | 3W Passenger (`PublicPCV3W`) Uniform 18% GST | Package / Roll Over | `9,000.00` | `1,620.00` | `10,620.00` | `575.00` | `28.75` | `546.25` | `-546.25` | `0.00` | `0.00` | `PASS` |
| **G7-12** | Passenger Taxi (`PassengerTaxi(PCV)`), 45% NCB, 18% GST | Package / Roll Over | `20,000.00` | `3,600.00` | `23,600.00` | `1,350.00` | `67.50` | `1,282.50` | `-1,282.50` | `0.00` | `0.00` | `PASS` |
| **G7-13** | School Bus (`School_Bus`), 50% NCB, 18% GST | Package / Roll Over | `40,000.00` | `7,200.00` | `47,200.00` | `2,700.00` | `135.00` | `2,565.00` | `-2,565.00` | `0.00` | `0.00` | `PASS` |
| **G7-14** | Miscellaneous / Tractor (`Misc-D`), 20% NCB, 18% GST | Package / Roll Over | `15,000.00` | `2,700.00` | `17,700.00` | `900.00` | `45.00` | `855.00` | `-855.00` | `0.00` | `0.00` | `PASS` |
| **G7-15** | Self-Quotation (`SELF_QUOTATION`) Conversion (Anti-Double-Count) | Package / Roll Over | Exact `TotalPremium` | Exact `GST18` | Exact `finalPrmium` | `0.00` | `0.00` | `0.00` | `0.00` | `0.00` | `0.00` | `PASS` |
| **G7-16** | Assisted Quotation (`ASSISTED_REQUEST`) Conversion | Package / Roll Over | `10,000.00` | `1,800.00` | `11,800.00` | `0.00` | `0.00` | `0.00` | `0.00` | `0.00` | `0.00` | `PASS` |
| **G7-17** | Staged Mobile Proposal (`tbl_transactionappnew`) -> Approval -> Book | Package / Roll Over | `10,000.00` | `1,800.00` | `11,800.00` | `0.00` | `0.00` | `0.00` | `0.00` | `0.00` | `0.00` | `PASS` |
| **G7-18** | Multi-Bucket Commission (`OD 15% + Net 5% + Extra 2.5%`) | Package / Roll Over | `18,000.00` | `3,240.00` | `21,240.00` | `2,400.00` | `120.00` | `2,280.00` | `-2,280.00` | `0.00` | `0.00` | `PASS` |
| **G7-19** | Single Headline Agent Commission (`12%` on Net Premium) | Package / Roll Over | `10,000.00` | `1,800.00` | `11,800.00` | `1,200.00` | `60.00` | `1,140.00` | `-1,140.00` | `0.00` | `0.00` | `PASS` |
| **G7-20** | Franchise Commission Split (`Franchise 20%` vs `Agent 15%`) | Package / Roll Over | `15,000.00` | `2,700.00` | `17,700.00` | `1,500.00` | `75.00` | `1,425.00` | `-1,425.00` | `0.00` | `0.00` | `PASS` |
| **G7-21** | Cut & Pay Full NetCommission Deduction (`CutNPay = 950.00`) | Package / Roll Over | `15,000.00` | `2,700.00` | `17,700.00` | `1,000.00` | `50.00` | `950.00` | `-950.00` | `0.00` | `0.00` | `PASS` |
| **G7-22** | Cut & Pay Custom Partial Deduction (`500.00`) + Partial Cash | Package / Roll Over | `15,000.00` | `2,700.00` | `17,700.00` | `1,000.00` | `50.00` | `950.00` | `-950.00` | `200.00` | `0.00` | `PASS` |
| **G7-23** | E-Wallet (`2,800`) + Partial Cash (`5,000`) -> Subsequent Settlement (`4,000`) | Package / Roll Over | `10,000.00` | `1,800.00` | `11,800.00` | `0.00` | `0.00` | `0.00` | `0.00` | `0.00` | `0.00` | `PASS` |
| **G7-24** | Multi-Instrument Split (`Cash 3,000 + Cheque 5,000 + Online Direct 3,800`) | Package / Roll Over | `10,000.00` | `1,800.00` | `11,800.00` | `0.00` | `0.00` | `0.00` | `0.00` | `0.00` | `0.00` | `PASS` |
| **G7-25** | Policy Cancellation & Reversal (`isdeleted="1"`, `TStatus="Cancelled"`) | Reversal | Reversed | Reversed | Reversed | Reversed | Reversed | Reversed | Reversed | `0.00` | `0.00` | `PASS` |
