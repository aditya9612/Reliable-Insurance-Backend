# 14 — Legacy Financial & Mathematical Rules Baseline (Phases 6–10)

> **Audit Status**: CONFIRMED FROM CODE
> **Primary Evidence**: `SelfQuotationRequest.aspx.cs`, `SelfQuotationRequest3_W_GCV.aspx.cs`, `SelfQuotationRequest3_W_PCV.aspx.cs`, `SelfQuotationRequestMISC_D.aspx.cs`, `adm_PolicyDetails.aspx.cs`, `PolicyTransactionNew.aspx.cs`, `PE_TransactionEntry.aspx.cs`, `AppPolicyRequestNew1_2026.aspx.cs`, `adm_NonMotarTransaction.aspx.cs`, `AppEndorsementforApproval.aspx.cs`, `adm_PolicyCancel.aspx.cs`

---

## 1. Numeric Data Types & Rounding Semantics

1. **Floating-Point Representation**:
   - All monetary and percentage fields in `API\AllMaster.cs`, `BLL`, `DAL`, and `.aspx.cs` code-behind use C# **`double`** (`System.Double`, IEEE 754 binary64), **NOT** `decimal`!
2. **Rounding Function (`Math.Round`)**:
   - The legacy codebase uses `Math.Round(value)` and `Math.Round(value, 0)` without specifying `MidpointRounding`.
   - In .NET 4.0, `Math.Round(double)` defaults to **`MidpointRounding.ToEven` (Banker's Rounding)**.
3. **Integer Division Quirk in Public GCV Tonnage Formula**:
   - In `SelfQuotationRequest.aspx.cs` (Line 994):
     ```csharp
     int Weight = int.Parse(txtGVW.Text);
     int AdditionalPremium = (((Weight - 12000) * 27) / 100);
     ```
     Because `Weight` is `int`, `((Weight - 12000) * 27) / 100` truncates toward zero using **integer division** before being added to `double basicpremium`.

---

## 2. Master Formula Table — Rating & Quotation (Phase 6)

| Calculation Step | Exact Formula in C# | Evidence (`File:Line`) |
| :--- | :--- | :--- |
| **1. IDV 15% Depreciation** | $\text{idv15per} = \text{Math.Round}\left(\frac{\text{idv} \times 15}{100}\right)$<br>$\text{IDV} = \text{idv} - \text{idv15per}$ | `SelfQuotationRequest.aspx.cs`: L395–396, L758–759 |
| **2. Vehicle Age Cap** | $\text{Age} = (\text{AgeFromDB} > 10) \; ? \; 11 : \text{AgeFromDB}$ | `SelfQuotationRequest.aspx.cs`: L913–916 |
| **3. Basic OD Premium** | $\text{basicpremium} = \text{Math.Round}\left(\frac{\text{IDV} \times \text{basicrate}}{100}\right)$ | `SelfQuotationRequest.aspx.cs`: L985 |
| **4. GCV Extra Tonnage (>12,000 kg)** | $\text{AdditionalPremium} = (\text{Weight} > 12000) \; ? \; \lfloor\frac{(\text{Weight} - 12000) \times 27}{100}\rfloor : 0$ | `SelfQuotationRequest.aspx.cs`: L992–996 |
| **5. OD Discount Amount** | $\text{OD50percentage} = \text{Math.Round}\left(\frac{\text{ODDisc} \times (\text{basicpremium} + \text{AdditionalPremium})}{100}\right)$ | `SelfQuotationRequest.aspx.cs`: L1003 |
| **6. OD After Discount** | $\text{ODafterDiscount} = (\text{basicpremium} - \text{OD50percentage}) + \text{AdditionalPremium}$ | `SelfQuotationRequest.aspx.cs`: L1004 |
| **7. IMT-23 Loading (15%)** | $\text{ExtraIMT} = (\text{IMT23} == \text{"Yes"}) \; ? \; \text{Math.Round}(\text{ODafterDiscount} \times 0.15) : 0$ | `SelfQuotationRequest.aspx.cs`: L1006–1014 |
| **8. No Claim Bonus (NCB)** | $\text{noclaimbonus} = \text{Math.Round}\left(\frac{((\text{basicpremium} + \text{AdditionalPremium} - \text{OD50percentage}) + \text{ExtraIMT}) \times \text{bonus}}{100}\right)$ | `SelfQuotationRequest.aspx.cs`: L1033 |
| **9. Zero Dep Premium** | $\text{ZeroDepPremium} = \frac{\text{IDV} \times \text{AddOnRate}}{100}$ | `SelfQuotationRequest.aspx.cs`: L1038 |
| **10. Part A Total (`TotalA`)** | - **Public GCV**: $\text{Math.Round}(((\text{basicpremium} + \text{AdditionalPremium} - \text{OD50percentage}) - \text{noclaimbonus}) + \text{ExtraIMT} + \text{TowingRate})$<br>- **MISC-D**: $\text{Math.Round}(\text{netdamagedpremium} + \text{ZeroDepPremium} + \text{ExtraIMT})$ | `SelfQuotationRequest.aspx.cs`: L1040, L1059<br>`SelfQuotationRequestMISC_D.aspx.cs`: L624 |
| **11. Part B Total (`TotalB`)** | $\text{TotalB} = \text{Math.Round}(\text{liabilitypremium} + \text{PAtoOwnerDriver} + \text{liabilityPaidDriver} + \text{PAPaidDriver} + \text{Cleaner} + \text{Passengers})$<br>where $\text{liabilityPaidDriver} = 50$, $\text{Cleaner} = 50 \times \text{Count}$ | `SelfQuotationRequest.aspx.cs`: L1076–1125 |
| **12. Quotation GST & Final Premium** | - $\text{SubPartB} = \text{Math.Round}(\text{PAtoOwnerDriver} + \text{liabilityPaidDriver} + \text{PAPaidDriver} + \text{Cleaner})$<br>- $\text{GSTTotalB} = \text{Math.Round}\left(\frac{(\text{TotalB} - \text{SubPartB}) \times 12}{100}\right)$ (12% on Basic TP)<br>- $\text{GSTTotalA} = \text{Math.Round}\left(\frac{\text{TotalA} \times 18}{100} + \text{Math.Round}\left(\frac{(\text{TotalB} - \text{liabilitypremium}) \times 18}{100}\right)\right)$<br>- $\text{FinalPremium} = \text{Math.Round}(\text{TotalA} + \text{TotalB}) + \text{Math.Round}(\text{GSTTotalA} + \text{GSTTotalB})$ | `SelfQuotationRequest.aspx.cs`: L1127–1186 |

---

## 3. Master Formula Table — Back-Office Policy GST & Totals (Phase 7)

**Evidence**: `adm_PolicyDetails.aspx.cs` (Lines 622–785), `MotorTransactionEntry.aspx.cs` (Lines 1750–2105), `PolicyTransactionNew.aspx.cs` (Lines 2330–2545)

| Vehicle Category | Risk Start Date (`RS_Date`) Condition | TP GST Formula (`TP_Comm`) | OD GST Formula (`Od_Comm`) | Add-On / PA / LL GST Formula (`GST`) | Net Premium (`txt_NetPremium`) | Proposal / Gross Amount (`txt_ProposalAmt`) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **GCV (`VehicleTypeId == 2`) & 3W GCV (`VehicleTypeId == 7`)** | `RS_Date >= 2025-09-23` | $\frac{R \times 5}{100}$ **(5%)** | $\frac{P \times 18}{100}$ **(18%)** | $\frac{(\text{PA} + \text{ImT17} + \text{Leg}) \times 18}{100}$ **(18%)** | $\text{Math.Round}(R + P + \text{PA} + \text{ImT17} + \text{Leg})$ | $\text{Math.Round}(R + P + \text{TP\_Comm} + \text{Od\_Comm} + \text{Total} + \text{GST})$ |
| **GCV (`VehicleTypeId == 2`) & 3W GCV (`VehicleTypeId == 7`)** | `RS_Date < 2025-09-23` | $\frac{R \times 12}{100}$ **(12%)** | $\frac{P \times 18}{100}$ **(18%)** | $\frac{(\text{PA} + \text{ImT17} + \text{Leg}) \times 18}{100}$ **(18%)** | $\text{Math.Round}(R + P + \text{PA} + \text{ImT17} + \text{Leg})$ | $\text{Math.Round}(R + P + \text{TP\_Comm} + \text{Od\_Comm} + \text{Total} + \text{GST})$ |
| **All Other Vehicles (`1, 3, 4, 5, 6, 8`)** | Any Date | $\frac{(R + P) \times 18}{100}$ **(18% combined)** | Included in $G = \frac{(R+P)\times 18}{100}$ | $\frac{(\text{PA} + \text{ImT17} + \text{Leg}) \times 18}{100}$ **(18%)** | $\text{Math.Round}(R + P + \text{PA} + \text{ImT17} + \text{Leg})$ | $\text{Math.Round}(R + P + G + \text{Total} + \text{GST})$ |

---

## 4. Master Formula Table — Commission, TDS, Profit & Endorsement (Phases 8–10)

| Rule Name | Exact Formula in C# | Evidence (`File:Line`) |
| :--- | :--- | :--- |
| **1. Total Net Commission Across 4 Bases** | $\text{Cacl\_NetComm} = \text{NetComm}_{\text{TP}} + \text{NetComm}_{\text{TP\_Extra}} + \text{NetComm}_{\text{OD}} + \text{NetComm}_{\text{Net}}$ | `PolicyTransactionNew.aspx.cs`: L1068–1105 |
| **2. Sub-Franchise Net Profit** | $\text{ProfitofNetCommision}_{\text{Fr}} = \text{Math.Round}(\text{Cacl\_NetComm\_Fr} - \text{Cacl\_NetComm}, 0)$ | `PolicyTransactionNew.aspx.cs`: L1513–1514 |
| **3. Reliable Associates (`FranchiseId=1`) Net Profit** | - Agent Business: $\text{Math.Round}(\text{Cacl\_NetComm\_RA} - \text{Cacl\_NetComm}, 0)$<br>- Non-Agent Business: $\text{Math.Round}(\text{Cacl\_NetComm\_RA} - \text{Cacl\_NetComm\_Fr}, 0)$ | `PolicyTransactionNew.aspx.cs`: L1584–1594 |
| **4. Cut & Pay TDS** | $\text{CutNPayTds} = \frac{\text{CutNPAY2} \times \text{tds}}{100}$ | `AppPolicyRequestNew1_2026.aspx.cs`: L2175 |
| **5. Non-Motor TDS (15% Fixed)** | $\text{txt\_tds} = \text{Math.Round}(\text{CommissionAmt} \times 0.15, 0)$ | `adm_NonMotarTransaction.aspx.cs`: L604 |
| **6. Endorsement Insurer Payable (`txtCmpAmt`)** | $\text{txtCmpAmt} = \text{Math.Round}(\text{txtPaidAmount} - \text{txt\_paidAmt})$ | `AppEndorsementforApproval.aspx.cs`: L154 |
| **7. Policy Issuance Double-Entry Balance** | $(+\text{AgentComm2021}_{\text{Ledger } 1161}) + (-\text{AgnetTds2021}_{\text{Ledger } 2113}) + (-\text{NetCommission}_{\text{AgentLedger}}) = 0$ | `PE_TransactionEntry.aspx.cs`: L9645–9723 |
