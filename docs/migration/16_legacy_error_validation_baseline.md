# 16 — Legacy Error Handling & Validation Baseline

> **Forensic Classification**: `CONFIRMED FROM CODE`  
> **Scope**: Exception handling patterns in `DAL_Operations.cs`, `BLL_Operations.cs`, `Service.asmx.cs`, `ExceptionLogging.cs`, and UI/API input validation rules.

---

## 1. Layered Exception Handling Architecture

### 1.1 Data Access Layer (`DAL_Operations.cs`)
Across the 124,758 lines of `Insurance_DAL/DAL_Operations.cs`, four distinct `try/catch` patterns are used:

| Pattern | Code Structure | Return Value on Exception | Frequency / Impact |
|---|---|---|---|
| **Pattern A: Rethrow (`throw ex;`)** | `try { ... } catch (Exception ex) { throw ex; } finally { conn.Close(); }` | Rethrows exception (resets stack trace due to `throw ex;` instead of `throw;`) | Majority of `Select` / `Insert` methods |
| **Pattern B: Silent `false` / `0` Return** | `try { ... } catch (Exception) { return false; }` or `return 0;` | Returns `0` or `false` without logging | Used in several boolean/integer helper methods; caller cannot distinguish DB crash from "0 rows affected" |
| **Pattern C: Empty `DataTable` / `DataSet` Return** | `DataTable dt = new DataTable(); try { ... } catch (Exception ex) { ExceptionLogging.SendErrorToText(ex); } return dt;` | Returns empty `DataTable` (`dt.Rows.Count == 0`) | Caller treats DB query failure as "no records found" |
| **Pattern D: File Logging via `ExceptionLogging.SendErrorToText(ex)`** | Logs exception details to `~/ExceptionDetailsFile/dd-MM-yy.txt` via `HttpContext.Current.Server.MapPath` | Logs and either rethrows or swallows | Used in `DAL_Operations.cs` and WebForms code-behind |

### 1.2 File-Based Exception Logger (`ExceptionLogging.cs`)
- **File**: `InsurancefinalNew/App_Code/ExceptionLogging.cs` (and `Insurance_DAL/ExceptionLogging.cs`)
- **Mechanism**:
  - Resolves directory `~/ExceptionDetailsFile/` using `context.Server.MapPath("~/ExceptionDetailsFile/")`.
  - Creates daily log file named `DateTime.Today.ToString("dd-MM-yy") + ".txt"`.
  - Appends:
    - `Exception Line No` (extracted from `ex.StackTrace.Substring(ex.StackTrace.Length - 7, 7)`)
    - `Error Message` (`ex.GetType().Name.ToString()`)
    - `Exception Type` (`ex.GetType().ToString()`)
    - `Error Location` (`ex.Message.ToString()`)
    - `Error Page Url` (`HttpContext.Current.Request.Url.ToString()`)
- **Concurrency Note**: Uses `StreamWriter sw = File.AppendText(filepath)` without a thread lock (`lock`), which can throw `IOException` under simultaneous exceptions.

---

## 2. ASMX Web Service Error & Response Envelope (`Service.asmx.cs`)

`Service.asmx.cs` exposes 416 `[WebMethod]` endpoints returning either serialized JSON strings (via `JavaScriptSerializer` or `JsonConvert.SerializeObject`), `DataSet`/`DataTable` XML, or custom wrapper DTOs (`API_Success<T>`).

### 2.1 `API_Success<T>` Response Wrapper
- **File**: `Insurance_Service/API_Success.cs`
- **Structure**:
  ```csharp
  public class API_Success<T>
  {
      public string Status { get; set; }      // "Success", "Fail", "Failed", "Error", "1", "0"
      public string Message { get; set; }     // Human-readable status or exception message
      public T Data { get; set; }             // Payload (List<API_*>, string, int, or null)
  }
  ```
- **Inconsistent Status Literals Across Endpoints (`CONFIRMED FROM CODE`)**:
  - Some WebMethods return `Status = "Success"` / `Status = "Fail"`.
  - Others return `Status = "True"` / `Status = "False"`.
  - Others return raw scalar strings (`"1"`, `"0"`, `"Successfully Inserted"`, `"Error"`, or `ex.Message`).
  - HTTP status code is almost always `200 OK` even when business validation fails or an exception is caught inside the WebMethod (`catch (Exception ex)` sets `Message = ex.Message` inside the 200 response payload).

---

## 3. Domain Validation Baseline (Code-Behind & API)

### 3.1 Customer & Vehicle Validation
| Field / Rule | Legacy Validation Logic | Evidence |
|---|---|---|
| **Mobile Number** | Checked for non-empty and 10-digit length in UI (`txtMobileNo.Text.Length == 10`), though legacy DB contains historical rows that may not strictly conform. | `PolicyTransactionNew.aspx.cs`, `adm_Customer.aspx.cs` |
| **Email Address** | Optional in most internal clerk flows; checked against basic format or non-empty in POS/Self-Quotation flows. | `SelfQuotationRequest.aspx.cs` |
| **Registration Number (`VehRegNo`)** | Checked for non-empty unless vehicle is marked `"NEW"` (`rbtnNewVehicle`). Uniqueness checked via `USP_SelectVehicleByRegNo`. | `PolicyTransactionNew.aspx.cs`, `adm_VehicleDetails.aspx.cs` |
| **Engine & Chassis Number (`EngineNo`, `ChaiseNo`)** | Required in full policy entry (`PE_TransactionEntry.aspx.cs`); stored in `tblcustvehicle`. Note legacy spelling `ChaiseNo`. | `PE_TransactionEntry.aspx.cs` |
| **Customer Duplicate Check** | Checked via `USP_SelectCustomerByMobileOrEmail` or `USP_CheckCustomerExist`. | `DAL_Operations.cs` |

### 3.2 Quotation & Rating Validation
| Field / Rule | Legacy Validation Logic | Evidence |
|---|---|---|
| **Mandatory Rating Inputs** | Insurance Company, Policy Type (`Package`/`Comprehensive`, `Liability`/`TP`, `SAOD`), Vehicle Type/SubClass, RTO, Manufacture Year, Registration Date. | `Qt_QuotationRateCalculation.aspx.cs`, `SelfQuotationRequest.aspx.cs` |
| **IDV Required for OD** | If Policy Type is `Package` or `SAOD`, `IDV > 0` and `ODRate > 0` are required. For `Liability`/`TP`, `IDV` and `ODRate` are forced to `0`. | `Qt_QuotationRateCalculation.aspx.cs:L350-L520` |
| **NCB Slab Values** | Restricted to standard percentage slabs (`0`, `20`, `25`, `35`, `45`, `50`). Forced to `0` on `Liability`/`TP` policies. | `Qt_QuotationRateCalculation.aspx.cs` |

### 3.3 Policy Booking & Financial Validation
| Field / Rule | Legacy Validation Logic | Evidence |
|---|---|---|
| **Policy Number Uniqueness** | Checked via `BLL_CheckPolicyNoExist(txtPolicyNo.Text)` (`USP_SelectPolicyNoExist`). | `PolicyTransactionNew.aspx.cs:L1190` |
| **Policy Dates** | `PolicyStartDate`, `PolicyEndDate`, and `PolicyIssueDate` parsed via `DateTime.ParseExact(..., "dd/MM/yyyy", CultureInfo.InvariantCulture)` or `Convert.ToDateTime()`. | `PolicyTransactionNew.aspx.cs:L1120-L1140` |
| **Payment Total vs Gross Premium** | Sum of `ViewState["PaymentDetails"]` rows must match `GrossPremium` (`txtFinalPremium`), or in Cut-and-Pay (`PayMode == "Cut & Pay"`), payment must equal `GrossPremium - AgentCommission + TDS`. | `PolicyTransactionNew.aspx.cs:L1250-L1295` |
| **E-Wallet Balance Check** | `if (balance > Convert.ToInt32(txtPaymentAmt.Value))` — requires strictly greater integer balance than payment amount. | `PolicyTransactionNew.aspx.cs:L1293` |
| **NCB Recovery Completion Check** | Blocks duplicate NCB recovery if `BLL_selectNcbrecoveryTransId(TransId, "Completed")` returns rows (`dt.Rows.Count > 0`). | `adm_NcbRecovery.aspx.cs:L1076` |
| **Policy Cancellation Check** | Blocks duplicate cancellation if `BLL_SelectAccountantApprovalByPolicynoCancel` indicates policy is already cancelled. | `adm_PolicyCancel.aspx.cs:L825` |
