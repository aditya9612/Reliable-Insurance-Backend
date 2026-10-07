# 10 — Legacy Claims Management Baseline (Phase 10A)

> **Audit Status**: CONFIRMED FROM CODE
> **Primary Evidence**:
> - `Insurance\Clerk\CL_ClaimNew.aspx.cs` (Lines 1–1649)
> - `API\AllMaster.cs` (`API_Claims`, `API_Claims_SpotServe`, `API_Claims_Garage_Serve`, `API_Claims_Quotation`, `API_Claims_FinalBill`)
> - `BLL\BLL_Operations.cs` & `DAL\DAL_Operations.cs` (`DAL_Claims`, `DAL_Claims_SpotServe`, `DAL_Claims_GarageServe`, `DAL_Claims_Quotation`, `DAL_Claims_FinalBill`)

---

## 1. Claims Domain Architecture & Sub-Entities

In the legacy system, a Claim (`ClaimsId`) is the parent aggregate for **five child sub-workflows** managed inside `Insurance\Clerk\CL_ClaimNew.aspx.cs`:

| Sub-Entity / Stage | API DTO Class | BLL / DAL Class | Physical Table / Stored Procedure | File Upload Folder |
| :--- | :--- | :--- | :--- | :--- |
| **1. Claim Master Header** | `API_Claims` | `BLL_Claims` / `DAL_Claims` | `BLL_SelectAllClaimsnew` / `BLL_SelectAll_ClosedClaimsnew` | `~/ClaimPhoto/` |
| **2. Spot Survey (`SpotServe`)** | `API_Claims_SpotServe` | `BLL_Claims_SpotServe` | `BLL_SelectAllspotServey(id)` | `~/ClaimPhoto/` / Spot Survey images |
| **3. Garage Survey (`GarageServe`)** | `API_Claims_Garage_Serve` | `BLL_Claims_GarageServe` | `BLL_SelectAllGarageServey(id)` | Garage Survey images |
| **4. Repair Quotation (`ClaimQuotation`)** | `API_Claims_Quotation` | `BLL_Claims_Quotation` | `BLL_ClaimQuotaionInsert(quot, "INSERT"\|"UPDATE")`<br>`BLL_quotationImageOperation(Claims2, "INSERT")`<br>Raw SQL table: `tbl_claim_quotation_img` | `~/QuotationDoc/` |
| **5. Final Bill (`FinalBill`)** | `API_Claims_FinalBill` | `BLL_Claims_FinalBill` | `BLL_Claim_FINALBILL_Insert(FB, "INSERT"\|"UPDATE")`<br>`BLL_FinalBillDocOperation(FB1, "INSERT")`<br>Raw SQL table: `tbl_claim_finalbill_doc` | `~/Claim_Final_Bill_Doc/` |
| **6. Audio Call Recordings (`ClaimAudio`)** | `API_Claims` | `BLL_Claims` | `BLL_ClaimAudio(Claims4)`<br>`BLL_DAL_ClaimAudioupdate(Claims5)`<br>Raw SQL table: `tbl_claimaudiolist` | `~/Clerk/ClaimAudio/` |

---

## 2. Step-by-Step Claims Workflow & Business Rules

### 2.1 Claim Registration & Assignment (`CL_ClaimNew.aspx.cs` L50–135)
1. **Reference Type (`ddl_Reference`)**:
   - `"Agent"`: Shows Agent dropdown (`divAgt.Visible = true`), auto-populates mapped Sales Executive via `BLL_SelectAgentwiseSalesEx(AgentId)` (L87).
   - `"Direct"`: Hides Agent dropdown (`divAgt.Visible = false`), binds Sales Executives filtered by `(UserRoleId=5) or (UserRole='Location Head')` (L58).
2. **Active vs Closed Claims**:
   - Active claims loaded via `BLL_SelectAllClaimsnew()` (`fillGrid()` L166).
   - Closed claims loaded via `BLL_SelectAll_ClosedClaimsnew()` (`fillGrid_1()` L172).

### 2.2 Spot Survey & Garage Survey (`Save2_Click` L693+)
- Requires `txtDateofsurvey1.Value != ""`, `txt_mobileNoOfServeyour1.Value != ""`, and `txt_surveyourName1.Value != ""`.
- Records surveyor name, mobile number, survey date, and multiple uploaded survey photos.

### 2.3 Claim Repair Quotation Stage (`Save3_Click` L407–555)
- **Mandatory Validation**: `ddl_QuatationStatus.SelectedIndex != 0` (else alerts `'All Fields are Required'`).
- **Insert (`save3.Text != "Update"`)**:
  - Sets `quot.QuotationId = -1`, `quot.ClaimsId = id`, `quot.QuotDate`, `quot.QuotStatus`.
  - Calls `BLL_ClaimQuotaionInsert(quot, "INSERT")` and reads output ID `temp_quotId = quot.outid`.
  - Iterates `HttpContext.Current.Request.Files` (`for (int i = 1; i < count; i++)` where `count = uploads.Count - 2`) and saves each image as `tempid + yyyyMMddHHmmss + "Img" + i + ".jpeg"` in `~/QuotationDoc/`, inserting a row via `BLL_quotationImageOperation(Claims2, "INSERT")`.
- **Update (`save3.Text == "Update"` — L474–549)**:
  - Calls `BLL_ClaimQuotaionInsert(quot, "UPDATE")`.
  - If new files are uploaded (`File3.Value != ""`), executes **raw SQL**:
    - `select * from tbl_claim_quotation_img where QuotationId=` + `temp_quotId`
    - Deletes existing files from `~/QuotationDoc/` via `File.Delete(filePath)`
    - Executes `delete from tbl_claim_quotation_img where QuotationId=` + `temp_quotId`
    - Re-uploads new files and inserts new `tbl_claim_quotation_img` records.

### 2.4 Claim Final Bill Stage (`Save4_Click` L251–406)
- **Mandatory Financial Fields**:
  - `Text_Bill_Amount.Value != ""` -> `FB.BillAmt` (Total Garage Bill Amount)
  - `Text_ICLA.Value != ""` -> `FB.ICLAmt` (Insurance Company Liability Amount / Approved Claim Amount)
  - `Text_ILA.Value != ""` -> `FB.ILAmt` (Insured / Customer Liability Amount)
- **Insert (`BtnsaveFB.Text != "Update"`)**:
  - Calls `BLL_Claim_FINALBILL_Insert(FB, "INSERT")` and captures `temp_FBId = FB.outid`.
  - Saves uploaded bill documents (`for (int i = 2; i < uploads.Count - 1; i++)`) to `~/Claim_Final_Bill_Doc/` as `temp_FBId + yyyyMMddHHmmss + "Img" + i + ".jpeg"` and inserts into `BLL_FinalBillDocOperation(FB1, "INSERT")`.
- **Update (`BtnsaveFB.Text == "Update"` — L321–402)**:
  - Calls `BLL_Claim_FINALBILL_Insert(FB, "UPDATE")`.
  - If `File4.Value != ""`, executes raw SQL `select * from tbl_claim_finalbill_doc where FBId=` + `tempFBID`, deletes old files from `~/ClaimPhoto/` *(Note: deletes from `~/ClaimPhoto/` at L354 even though Insert saved to `~/Claim_Final_Bill_Doc/` at L274!)*, executes `delete from tbl_claim_finalbill_doc where FBId=` + `tempFBID`, and inserts the new files.

### 2.5 Claim Audio Call Recording Stage (`btnSav_Click` L557–692)
- Uploads `.mp3` files (`for (int i = 3; i < uploads.Count; i++)`) to `~/Clerk/ClaimAudio/` named `yyyyMMddHHmmss + i + ".mp3"`.
- If no file is selected on insert, inserts a placeholder record with `Audiopath = "---"` and `Description = txtDescription.Value` (L605).
- On Update with new files, deletes existing files from `~/Clerk/ClaimAudio/` and executes `delete from tbl_claimaudiolist where ClaimsId=` + `id` before inserting new audio records.

---

## 3. Accounting Impact of Claims in Legacy System
- **Forensic Confirmation**: Claims (`CL_ClaimNew.aspx.cs` and `DAL_Claims*`) do **NOT** create `API_Account` (`tbl_accountdetails`) journal entries. Claim amounts (`BillAmt`, `ICLAmt`, `ILAmt`) are tracked purely as operational/reporting records against the policy's `ClaimsId` because claim settlements are paid by the Insurance Company directly to the customer/garage, not from the broker's accounting ledger.

---

## 4. Confirmed Legacy Defects in Claims Module
1. **Thread-Unsafe `static` State Fields (`CL_ClaimNew.aspx.cs` L26–28)**:
   - `private static int id, ClaimTypeId, temp_quotId, temp_FBId, audioclaimid, audioserveid, tempFBID, tempQuotid...` are declared `static` on the `Page` class. Concurrent users working on different claims overwrite `id` and `temp_FBId` across HTTP requests!
2. **Path Mismatch on Final Bill Document Update (`CL_ClaimNew.aspx.cs` L274 vs L354)**:
   - Final Bill documents are saved to `~/Claim_Final_Bill_Doc/` (L274, L365), but on Update the cleanup loop attempts to delete old files from `~/ClaimPhoto/` (L354), leaving orphaned files on disk.
3. **Unparameterized Raw SQL Queries (`CL_ClaimNew.aspx.cs` L343, L361, L493, L512, L627, L646)**:
   - Uses string concatenation for `FBId`, `QuotationId`, and `ClaimsId`.
