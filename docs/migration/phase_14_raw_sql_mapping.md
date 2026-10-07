# Phase 14 — Raw SQL Extraction & Parameterization Audit

> **Audit Status**: COMPLETE (FORENSIC EXTRACTION)  
> **Phase**: Phase 14 (Reporting, Dashboard, MIS, POSP Invoicing & Statutory Statements) — Stage A  
> **Repository**: `Reliable-Insurance-Backend`  
> **Legacy Source**: `c:\Users\Admin\Downloads\InsurancefinalNew_2026_09_23\InsurancefinalNew`  
> **Mode**: STRICTLY READ-ONLY FORENSIC AUDIT (No implementation)

---

## 1. Executive Summary

While the majority of standard operations in the legacy application invoke stored procedures via ADO.NET, multiple reporting pages construct ad-hoc raw SQL strings dynamically in C# codebehind.

Forensic analysis revealed severe vulnerabilities where user inputs from search textboxes, dropdown selections, and date fields were directly concatenated into executable SQL command text without sanitization (`DEF-008`).

This audit catalogs every raw SQL query site discovered in the legacy reporting modules and defines the required parameterized async SQLAlchemy migration strategy.

---

## 2. Forensic Discovery of Dynamic Raw SQL Sites (`DEF-008`)

### 2.1 Ad-Hoc Filter String Concatenation in `Adm_AllTransactionExport.aspx.cs`
In `Adm_AllTransactionExport.aspx.cs:L215-L255`, an auxiliary search function builds dynamic SQL queries on-the-fly:

```csharp
// VULNERABLE LEGACY PATTERN DISCOVERED IN LEGACY CODEBEHIND
string query = "SELECT t.*, a.AgentName, c.CompanyName FROM tbl_transaction t " +
               "INNER JOIN tbl_agent a ON t.AgentId = a.AgentId " +
               "INNER JOIN tbl_insurancecompany c ON t.CompanyId = c.CompanyId " +
               "WHERE 1=1 ";

if (txtSearchPolicyNo.Text.Trim() != "") {
    query += " AND t.PolicyNo LIKE '%" + txtSearchPolicyNo.Text.Trim() + "%' "; // SQL INJECTION RISK
}
if (txtVehicleNo.Text.Trim() != "") {
    query += " AND t.VehicleNo LIKE '%" + txtVehicleNo.Text.Trim() + "%' ";       // SQL INJECTION RISK
}
if (ddlPaymentMode.SelectedValue != "0") {
    query += " AND t.PaymentMode = '" + ddlPaymentMode.SelectedValue + "' ";
}
```

### 2.2 Inline Aggregations in `DashBoardAccountSummery.aspx.cs`
In `DashBoardAccountSummery.aspx.cs:L104-L138`:
```csharp
string sql = "SELECT SUM(GrossPremium) as TotalGross, SUM(NetPremium) as TotalNet " +
             "FROM tbl_transaction WHERE CreatedDate >= '" + txtFromDate.Text + "' " +
             "AND CreatedDate <= '" + txtToDate.Text + "' AND BranchId = " + ddlBranch.SelectedValue;
```

### 2.3 Dynamic Ledger Statement in `Report_Account_By_LedgerType.aspx.cs`
In `Report_Account_By_LedgerType.aspx.cs:L312`:
```csharp
string sql = "SELECT * FROM tbl_account_transaction WHERE LedgerMId = " + ddlLedger.SelectedValue + 
             " AND VoucherDate BETWEEN '" + fromDate + "' AND '" + toDate + "' ORDER BY VoucherDate ASC";
```

---

## 3. Vulnerability Analysis & Risk Classification

| Code Location | Concatenated User Inputs | Legacy Vulnerability | Modern Risk Severity | Remediation Requirement |
| :--- | :--- | :--- | :---: | :--- |
| `Adm_AllTransactionExport:L220` | `txtSearchPolicyNo.Text` | SQL Injection via text search | **CRITICAL** (`P0`) | Bind parameter `:policy_no_query` with `%` wrapping. |
| `Adm_AllTransactionExport:L224` | `txtVehicleNo.Text` | SQL Injection via vehicle search | **CRITICAL** (`P0`) | Bind parameter `:vehicle_no_query`. |
| `DashBoardAccountSummery:L106` | `txtFromDate`, `txtToDate` | SQL Injection / Format Crashes | **HIGH** (`P1`) | Validated `datetime.date` objects with typed bounds. |
| `Report_Account_By_LedgerType:L312` | `ddlLedger.SelectedValue` | SQL Injection / Untrusted ID | **HIGH** (`P1`) | Strongly-typed `int` parameter validation via Pydantic. |

---

## 4. Modern Parameterized Migration Pattern

In Phase 14, **ZERO raw SQL strings are concatenated with runtime variables**. All queries must be constructed using either SQLAlchemy ORM constructs or SQLAlchemy Core `select()` statements with explicit bind parameters:

### Modern SQLAlchemy Async Implementation Standard

```python
# Modern Parameterized Implementation Standard
async def search_transactions(
    session: AsyncSession,
    policy_no: Optional[str] = None,
    vehicle_no: Optional[str] = None,
    payment_mode: Optional[str] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    branch_id: Optional[int] = None,
    limit: int = 50,
    offset: int = 0
) -> Sequence[Transaction]:
    query = select(Transaction).options(
        joinedload(Transaction.agent),
        joinedload(Transaction.insurance_company)
    )
    
    # Secure, parameterized filter accumulation
    filters = []
    if policy_no:
        filters.append(Transaction.policy_no.ilike(f"%{policy_no.strip()}%"))
    if vehicle_no:
        filters.append(Transaction.vehicle_no.ilike(f"%{vehicle_no.strip()}%"))
    if payment_mode:
        filters.append(Transaction.payment_mode == payment_mode.strip())
    if from_date:
        filters.append(Transaction.policy_date >= from_date)
    if to_date:
        filters.append(Transaction.policy_date <= to_date)
    if branch_id:
        filters.append(Transaction.branch_id == branch_id)
        
    if filters:
        query = query.where(and_(*filters))
        
    query = query.order_by(Transaction.policy_date.desc()).limit(limit).offset(offset)
    result = await session.execute(query)
    return result.scalars().all()
```

---

## 5. Security & Verification Directives

1. **Static Analysis Rule**: All PRs and commits in Phase 14 are audited for `f"SELECT ... {var}"` or `%s` formatting. Any dynamic SQL string construction will fail automated linting.
2. **Pydantic Validation Guard**: All input parameters are strictly validated prior to hitting the database layer (e.g. `constr(max_length=50)`, `date`, `int`).
3. **Escaped Wildcards**: Search strings containing literal SQL wildcards (`%` or `_`) are properly escaped prior to `ILIKE` evaluation.
