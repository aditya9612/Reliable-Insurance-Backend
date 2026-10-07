# 06 — Legacy Quotation, Rating & Premium Calculation Baseline (Phase 6)

> **Audit Status**: CONFIRMED FROM CODE
> **Primary Evidence**:
> - `Insurance\Clerk\SelfQuotationRequest.aspx.cs` (Lines 890–1550 — Public GCV Self-Quotation)
> - `Insurance\Clerk\SelfQuotationRequest3_W_GCV.aspx.cs` (Lines 414–1005 — 3-Wheeler GCV Self-Quotation)
> - `Insurance\Clerk\SelfQuotationRequest3_W_PCV.aspx.cs` (Lines 414–1005 — 3-Wheeler PCV Self-Quotation)
> - `Insurance\Clerk\SelfQuotationRequestMISC_D.aspx.cs` (Lines 418–1130 — MISC-D Self-Quotation)
> - `Insurance\Clerk\adm_PolicyDetails.aspx.cs` (Lines 340–1050 — Back-Office Policy Rating & GST Engine)
> - `Insurance\Clerk\MotorTransactionEntry.aspx.cs` (Lines 1750–2110)
> - `Insurance\Clerk\PolicyTransactionNew.aspx.cs` (Lines 2330–2550)

---

## 1. Supported Vehicle & Product Rating Categories

**Evidence**: `Insurance\Clerk\adm_PolicyDetails.aspx.cs` (Lines 343–378, 415–447)

| `VehicleTypeId` | Legacy Category Code (`hidCompany_Type.Value`) | Self-Quotation Page | Rating Lookup Key Passed to `BLL_quot_liabilitypremium` / `BLL_quot_damagepremium` |
| :--- | :--- | :--- | :--- |
| `1` | `"PVT"` | `SelfQuotationFirstPage.aspx.cs` / `Service.asmx.cs` | `"PVT"` |
| `2` | `policyPrefix + "_GCV"` (e.g., `"Public_GCV"`, `"Private_GCV"`) | `SelfQuotationRequest.aspx.cs` | `"Public_GCV"` |
| `3` | `"PassengerTaxi(PCV)"` | `Service.asmx.cs` | `"PassengerTaxi(PCV)"` |
| `4` | `"TwoWheeler"` | `Service.asmx.cs` | `"TwoWheeler"` |
| `5` | `"Miss-D"` (or `"MISC-D"`) | `SelfQuotationRequestMISC_D.aspx.cs` | `"MISC-D"` / `"Miss-D"` |
| `6` | `"School_Bus"` | `Service.asmx.cs` | `"School_Bus"` |
| `7` | `"PublicGCV3W"` | `SelfQuotationRequest3_W_GCV.aspx.cs` | `"PublicGCV3W"` |
| `8` | `"PublicPCV3W"` | `SelfQuotationRequest3_W_PCV.aspx.cs` | `"PublicPCV3W"` |

### Product Types (`ProductTypeId` / `ddl_ProductType`)
- **`ProductTypeId = 1`**: **Package / Comprehensive Policy** (Part A Own Damage + Part B Third-Party Liability).
- **`ProductTypeId = 2`**: **Liability / TP Only Policy** (Part B Third-Party Liability only; all Part A Own Damage fields are zeroed out — `SelfQuotationRequest.aspx.cs` L1150–1161, L1269–1286; `adm_PolicyDetails.aspx.cs` L454–475).
- **`ProductTypeId = 3`**: **Standalone OD (SAOD) Policy** (Part A Own Damage only; TP Premium UI hidden — `adm_PolicyDetails.aspx.cs` L478–481).

---

## 2. Step-by-Step Self-Quotation Rating Formulas

### 2.1 Vehicle Age Calculation & Cap (`lblAge`)
**Evidence**: `SelfQuotationRequest.aspx.cs` (Lines 909–922)
1. Calls `DataTable dty = bll_obj1.BLL_SelectMgfyearOfyearmonth(Convert.ToDateTime(txttodate.Text));`
2. Reads `lblAge.Text = dty.Rows[0][0].ToString();`
3. **Age Cap Rule**:
   ```csharp
   if (double.Parse(lblAge.Text) > 10)
   {
       lblAge.Text = "11";
   }
   ```
   *(Any vehicle older than 10 years is mapped to age bracket `"11"` for OD base rate lookup).*

### 2.2 RTO Cluster & Zone Lookup (`lblZone`, `lblClusterId`)
**Evidence**: `SelfQuotationRequest.aspx.cs` (Lines 924–929)
- Calls `bll_obj.BLL_SelectRTOByIDself(int.Parse(ddl_RTO.SelectedItem.Value))`
- Returns `Zone` (`dt.Rows[0][0]`, values `"A"`, `"B"`, or `"C"`) and `ClusterId` (`dt.Rows[0][1]`).

### 2.3 IDV (Insured Declared Value) Calculation & 15% Reduction Rule
**Evidence**: `SelfQuotationRequest.aspx.cs` (L394–402, L757–763), `SelfQuotationRequest3_W_GCV.aspx.cs` (L233–236), `SelfQuotationRequest3_W_PCV.aspx.cs` (L232–235), `SelfQuotationRequestMISC_D.aspx.cs` (L235–238)
- Base IDV (`idv`) is fetched from the master table by Vehicle Age/Variant.
- **15% Depreciation / Reduction Formula**:
  ```csharp
  double idv15per = Math.Round((idv * 15) / 100);
  double IDV = idv - idv15per;
  ```
- In `SelfQuotationRequest.aspx.cs` (L757–763), when a user selects an Insurance Company, the system also checks company-specific IDV variation rules and recalculates `idv - Math.Round((idv * 15) / 100)`.

### 2.4 Part A — Own Damage (OD) Calculation
**Evidence**: `SelfQuotationRequest.aspx.cs` (Lines 956–1060), `SelfQuotationRequest3_W_GCV.aspx.cs` (Lines 530–575), `SelfQuotationRequestMISC_D.aspx.cs` (Lines 540–630)

1. **Basic OD Rate (`lblbasicrate`)**:
   - Fetched via `bll_obj.BLL_quot_damagepremium(Category, double.Parse(lblAge.Text), Zone)` where `Zone` is `"A"`, `"B"`, or `"C"`.
2. **Basic OD Premium (`basicpremium`)**:
   $$\text{basicpremium} = \text{Math.Round}\left(\frac{\text{IDV} \times \text{basicrate}}{100}\right)$$
3. **Additional Tonnage Premium Above 12,000 kg (Public GCV Only)**:
   - **Evidence**: `SelfQuotationRequest.aspx.cs` (Lines 987–1001)
   - If `Weight > 12000` (GVW in kg):
     $$\text{AdditionalPremium} = \lfloor \frac{(\text{Weight} - 12000) \times 27}{100} \rfloor \quad (\text{integer division in C\#})$$
   - Otherwise `AdditionalPremium = 0`.
   - *(Note: Because `Weight` is `int`, `(((Weight - 12000) * 27) / 100)` uses C# integer division!)*
4. **OD Discount (`OD50percentage`) & OD After Discount (`ODafterDiscount`)**:
   - **Evidence**: `SelfQuotationRequest.aspx.cs` (Lines 1003–1004)
   $$\text{OD50percentage} = \text{Math.Round}\left(\frac{\text{ODDisc\%} \times (\text{basicpremium} + \text{AdditionalPremium})}{100}\right)$$
   $$\text{ODafterDiscount} = (\text{basicpremium} - \text{OD50percentage}) + \text{AdditionalPremium}$$
5. **IMT-23 Loading (`ExtraIMT` — 15% on `ODafterDiscount`)**:
   - **Evidence**: `SelfQuotationRequest.aspx.cs` (Lines 1005–1015), `SelfQuotationRequest3_W_GCV.aspx.cs` (Lines 542–550), `SelfQuotationRequest3_W_PCV.aspx.cs` (Lines 531–539), `SelfQuotationRequestMISC_D.aspx.cs` (Lines 551–559)
   - If `ddlIMT23.SelectedItem.Text == "Yes"`:
     $$\text{ExtraIMT} = \text{Math.Round}(\text{ODafterDiscount} \times 0.15)$$
   - Else `ExtraIMT = 0`.
6. **No Claim Bonus (`noclaimbonus`)**:
   - **Evidence**: `SelfQuotationRequest.aspx.cs` (Line 1033)
   - Allowed NCB percentages (`bonus`): `0`, `20`, `25`, `35`, `45`, `50`.
   - In **Public GCV** (`SelfQuotationRequest.aspx.cs` L1033):
     $$\text{noclaimbonus} = \text{Math.Round}\left(\frac{((\text{basicpremium} + \text{AdditionalPremium} - \text{OD50percentage}) + \text{ExtraIMT}) \times \text{bonus}}{100}\right)$$
   - In **3W GCV / 3W PCV** (`SelfQuotationRequest3_W_GCV.aspx.cs` L554–565):
     - Includes `Loading`: `subtotal = Math.Round((basicpremium - OD50percentage) + ExtraIMT);` and `netdamagedpremium = Math.Round(basicpremium - OD50percentage + ExtraIMT + Loading - noclaimbonus);`.
7. **Zero Depreciation / Add-On (`ZeroDepPremium`) & Towing Charges (`Rate`)**:
   - **Evidence**: `SelfQuotationRequest.aspx.cs` (Lines 1038–1060)
   $$\text{ZeroDepPremium} = \frac{\text{IDV} \times \text{AddOnRate}}{100}$$
   - Wait — look at **Line 1040** of `SelfQuotationRequest.aspx.cs`:
     ```csharp
     double TotalA = Math.Round((((basicpremium + AdditionalPremium) - OD50percentage) - noclaimbonus) + ExtraIMT);
     ```
     Notice that in `SelfQuotationRequest.aspx.cs` (Public GCV), `ZeroDepPremium` is computed at L1038 and displayed on the label `lblP_ZeroDepValue.Text` (L1238), **but is NOT added to `TotalA` at L1040**! By contrast, in `SelfQuotationRequestMISC_D.aspx.cs` (Line 624):
     ```csharp
     double TotalA = Math.Round(netdamagedpremium + ZeroDepPremium + ExtraIMT);
     ```
     `ZeroDepPremium` **IS** added to `TotalA` in MISC-D!
   - If `ddlTowingRate.SelectedItem.Value == "1"`, `Rate` is fetched from `BLL_SelectTowingChargesByCompanyId(CompanyId, "SELECT", "0")` (`dt2.Rows[0][2]`) and added:
     $$\text{TotalA} = \text{Math.Round}(\text{TotalA} + \text{Rate})$$

---

### 2.5 Part B — Third-Party Liability & PA / LL Add-Ons
**Evidence**: `SelfQuotationRequest.aspx.cs` (Lines 948–953, 1061–1126)

1. **Basic TP Liability Premium (`liabilitypremium`)**:
   - Fetched via `bll_obj.BLL_quot_liabilitypremium("Public_GCV", Weight, "L")`.
2. **PA to Owner-Driver (`PAtoOwnerDriver`)**:
   - If `ddlindividual.SelectedItem.Text == "Individual"`, `PAtoOwnerDriver = double.Parse(txtPAToOwnere.Text)` (else `0`).
3. **Legal Liability to Paid Driver (`liabilityPaidDriver`)**:
   - If `lbl_Liability1.Text == "YES"`, `liabilityPaidDriver = 50` (flat Rs. 50; else `0`).
4. **PA to Paid Driver (`PAPaidDriver`)**:
   - Look at `SelfQuotationRequest.aspx.cs` Lines 1064 & 1088–1091:
     ```csharp
     double PApaiddriver2 = 0;
     if (ddlPAPaidToDriver.SelectedItem.Text == "YES")
     {
         PAPaidDriver = 60 * PApaiddriver2;
     }
     ```
     *(Because `PApaiddriver2` is initialized to `0` and never updated before L1090, `PAPaidDriver` always evaluates to `0` in `SelfQuotationRequest.aspx.cs`!)*
5. **Legal Liability to Cleaner / Coolies (`Cleaner`)**:
   - If `ddlCleanerCoolies.SelectedItem.Text == "YES"`:
     $$\text{Cleaner} = 50 \times \text{txtCleanerCoolies}$$
6. **Total Part B (`TotalB`)**:
   $$\text{TotalB} = \text{Math.Round}(\text{liabilitypremium} + \text{PAtoOwnerDriver} + \text{liabilityPaidDriver} + \text{PAPaidDriver} + \text{Cleaner} + \text{Passengers})$$

---

### 2.6 GST Split & Final Quotation Premium Calculation
**Evidence**: `SelfQuotationRequest.aspx.cs` (Lines 1127–1188)

In `SelfQuotationRequest.aspx.cs`, GST is split between **12% on Basic TP (`liabilitypremium`)** and **18% on Part A (`TotalA`) + Part B Add-Ons (`SubPartB`)**:

1. **SubPartB (Non-Basic TP Components)**:
   $$\text{SubPartB} = \text{Math.Round}(\text{PAtoOwnerDriver} + \text{liabilityPaidDriver} + \text{PAPaidDriver} + \text{Cleaner})$$
   $$\text{GSTSubPartB} = \text{Math.Round}\left(\frac{\text{SubPartB} \times 18}{100}\right)$$
2. **Basic TP Portion (`TotalBNew`) taxed at 12%**:
   $$\text{TotalBNew} = \text{TotalB} - \text{SubPartB}$$
   $$\text{GSTTotalB} = \text{Math.Round}\left(\frac{\text{TotalBNew} \times 12}{100}\right)$$
3. **If `ProductType == "2"` (TP / Liability Only — L1150–1161)**:
   $$\text{TotalOFAB} = \text{Math.Round}((\text{TotalA} + \text{TotalB}) - \text{TotalA}) = \text{TotalB}$$
   $$\text{GST} = \text{Math.Round}(\text{GSTTotalB} + \text{GSTSubPartB})$$
   $$\text{FinalPremium} = \text{Math.Round}(\text{TotalOFAB} + \text{GST})$$
4. **If `ProductType == "1"` (Package / Comprehensive — L1162–1187)**:
   $$g_1 = \text{Math.Round}(\text{TotalB} - \text{liabilitypremium})$$
   $$g_2 = \text{Math.Round}\left(\frac{g_1 \times 18}{100}\right)$$
   $$\text{GSTTotalA} = \text{Math.Round}\left(\frac{\text{TotalA} \times 18}{100} + g_2\right)$$
   $$\text{TotalOFAB} = \text{Math.Round}(\text{TotalA} + \text{TotalB})$$
   $$\text{GST} = \text{Math.Round}(\text{GSTTotalA} + \text{GSTTotalB})$$
   $$\text{FinalPremium} = \text{Math.Round}(\text{TotalOFAB} + \text{GST})$$

---

## 3. Back-Office Policy Entry Premium & GST Calculation (Including 2025-09-23 GCV GST Rule)

**Evidence**: `Insurance\Clerk\adm_PolicyDetails.aspx.cs` (Lines 622–1035), `Insurance\Clerk\MotorTransactionEntry.aspx.cs` (Lines 1750–2105), `Insurance\Clerk\PolicyTransactionNew.aspx.cs` (Lines 2330–2545), `Insurance\Clerk\PE_TransactionEntry.aspx.cs` (Lines 3915–4055)

When clerks enter or modify policy premium figures (`txt_TPPremium`, `txt_ODPremium`, `txtPACover`, `txtIMT17`, `txtLegalLiability`), the code-behind executes the following exact formulas:

### Case 1: GCV (`HidVehicleTypeId == "2"`) or 3W GCV (`HidVehicleTypeId == "7"`)
- Let:
  - $R = \text{txt\_TPPremium}$
  - $P = \text{txt\_ODPremium}$
  - $E = R + P$
  - $\text{PA} = \text{txtPACover}$
  - $\text{ImT17} = \text{txtIMT17}$ (mapped to `PACoverDriverCleaner` in DB)
  - $\text{Leg} = \text{txtLegalLiability}$
  - $\text{Total} = \text{PA} + \text{ImT17} + \text{Leg}$
- **Date-Driven TP GST Rate (`RS_Date` = Risk Start Date `txt_sdate.Text`)**:
  - **Evidence**: `adm_PolicyDetails.aspx.cs` (Lines 636–644, 718–726, 804–812, 887–895, 970–978)
  ```csharp
  DateTime RS_Date = DateTime.Parse(txt_sdate.Text);
  if (RS_Date >= DateTime.Parse("2025/09/23"))
  {
      TP_Comm = R * 5 / 100;   // 5% GST on Basic TP from 23-Sep-2025 onwards
  }
  else
  {
      TP_Comm = R * 12 / 100;  // 12% GST on Basic TP before 23-Sep-2025
  }
  ```
- **OD & Add-On GST Rates (18%)**:
  $$\text{Od\_Comm} = \frac{P \times 18}{100}$$
  $$G = \text{TP\_Comm} + \text{Od\_Comm}$$
  $$\text{GST} = \frac{\text{Total} \times 18}{100}$$
  $$\text{TotalWithGST} = \text{Total} + \text{GST}$$
- **Output Totals**:
  - **Net Premium (`txt_NetPremium.Value`)**:
    $$\text{NetPremium} = \text{Math.Round}(R + P + \text{PA} + \text{ImT17} + \text{Leg})$$
  - **Total GST (`txtTotalGST.Value`)**:
    $$\text{TotalGSTAmt} = \text{Math.Round}(G + \text{GST})$$
  - **Proposal / Gross Amount (`txt_ProposalAmt.Value`)**:
    $$\text{ProposalAmt} = \text{Math.Round}(R + P + G + \text{Total} + \text{GST})$$

### Case 2: All Other Vehicle Types (`VehicleTypeId` $\notin \{2, 7\}$)
- **18% Uniform GST on TP, OD, and Add-Ons**:
  $$G = \frac{(R + P) \times 18}{100}$$
  $$\text{Total} = \text{PA} + \text{ImT17} + \text{Leg}$$
  $$\text{GST} = \frac{\text{Total} \times 18}{100}$$
  $$\text{NetPremium} = \text{Math.Round}(R + P + \text{Total})$$
  $$\text{TotalGSTAmt} = \text{Math.Round}(G + \text{GST})$$
  $$\text{ProposalAmt} = \text{Math.Round}(R + P + G + \text{Total} + \text{GST})$$

---

## 4. Risk Expiry Date Rule
**Evidence**: `adm_PolicyDetails.aspx.cs` (Lines 609–620)
```csharp
DateTime D1 = DateTime.Parse(txt_sdate.Text);
DateTime DateExpire = D1.AddYears(1);
DateTime DateExpire1 = DateExpire.AddDays(-1);
txt_Expiredate.Value = DateExpire1.ToString();
```
- **Rule**: Default Risk Expiry Date is always **`RiskStartDate + 1 Year - 1 Day`**.

---

## 5. Quotation Persistence & Code Generation (`SaveData`)
**Evidence**: `SelfQuotationRequest.aspx.cs` (Lines 1331–1515)
1. **Quotation Code (`QuatationCode`)**: Generated via `BLL_QuotationSelf.BLL_GetQuotationCodeForSelfQuot()`.
2. **Company-Specific Quotation Title (`Title`)**: Fetched via `BLL_GetQuotationCodeForSelfQuotation(RoleId, EmpId, VehTypeId, CompanyId)`.
3. **Persistence**: Populates `API_QuotationSelf` (`QS`) and calls `BLL_InsertAppQuotationEntry(QS)` (`usp_InsertAppQuotationEntry`).
4. **PDF Link Convention**: `~/PDF_Files/Quotation_<QuotationId>.pdf` (`SelfQuotationRequest.aspx.cs` L1521).
