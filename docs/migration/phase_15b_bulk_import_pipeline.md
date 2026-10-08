# PHASE 15B — BULK POLICY MIS IMPORT PIPELINE
## Excel & CSV Staging, Data Cleaning, and Reconciliation Architecture

---

### 1. Executive Summary
Legacy ASP.NET page `adm_ImportTransAgentPolicyMIS.aspx.cs` permitted administrative staff and branch managers to bulk-upload motor and non-motor policy portfolios generated outside the core portal. These records were staged into database table `tbl_importagentpolicy` using `OleDbDataReader` or raw Excel interop, suffering from rigid column order dependencies and brittle data conversions.

Phase 15B delivers a resilient, high-performance bulk ingestion pipeline implemented in `UtilityService.parse_and_stage_policy_mis` and exposed via `/api/v1/imports/policy-mis/*`.

---

### 2. Supported Formats & Parsing Engine

- **File Formats**:
  - Comma-Separated Values (`.csv`) with automatic UTF-8 / Latin-1 decoding.
  - Microsoft Excel OpenXML (`.xlsx`) via `openpyxl`.
  - Microsoft Excel 97-2004 (`.xls`) compatibility.
- **Normalization Engine**:
  Column headers are cleaned by stripping whitespace, converting to lowercase, and eliminating punctuation. Dynamic alias mappings resolve legacy header discrepancies:

| Target Schema Column | Accepted Header Variations | Format / Cleaning Rule |
|---|---|---|
| `PolicyNo` | `policyno`, `policy_no`, `policy no`, `policy_number`, `policynumber` | Trimmed string |
| `AgentCode` | `agentcode`, `agent_code`, `agent code`, `agentid`, `posp_code` | Upper-case trimmed string |
| `CustomerName` | `customername`, `customer_name`, `customer name`, `insured_name`, `client` | Trimmed string |
| `GrossPremium` | `grosspremium`, `gross_premium`, `gross premium`, `total_premium` | Stripped `₹`, commas; cast to Decimal |
| `NetPremium` | `netpremium`, `net_premium`, `net premium`, `od_premium` | Stripped `₹`, commas; cast to Decimal |
| `ODPremium` | `odpremium`, `od_premium`, `od premium`, `own_damage` | Stripped `₹`, commas; cast to Decimal |
| `TPPremium` | `tppremium`, `tp_premium`, `tp premium`, `third_party` | Stripped `₹`, commas; cast to Decimal |
| `CommissionAmount` | `commissionamount`, `commission_amount`, `commission`, `payout` | Stripped `₹`, commas; cast to Decimal |
| `CommissionPercent` | `commissionpercent`, `commission_percent`, `commission %`, `payout %` | Stripped `%`, commas; cast to Decimal |
| `VehicleNo` | `vehicleno`, `vehicle_no`, `vehicle no`, `reg_no`, `registration_no` | Upper-case stripped string |
| `IssueDate` | `issuedate`, `issue_date`, `policy_date`, `booking_date` | ISO 8601 or `DD/MM/YYYY` parsed |
| `ExpiryDate` | `expirydate`, `expiry_date`, `end_date` | ISO 8601 or `DD/MM/YYYY` parsed |

---

### 3. Pipeline Flow & Database Staging

```
[Uploaded File (.csv / .xlsx)]
           │
           ▼
[Format Detection & Header Normalization]
           │
           ▼
[Row-by-Row Sanitization & Parsing]
           ├── Valid Row   ──► Staged Row Record
           └── Invalid Row ──► Error Captured in Batch Audit Log
           │
           ▼
[Bulk Insert into `tbl_importagentpolicy`]
           ├── BatchId = UUID4
           ├── IsProcess = '0'
           ├── CreateDate = UTC Timestamp
           └── CreateUser = Authenticated Principal
           │
           ▼
[API Response: Batch ID, Total Rows, Staged Rows, Error Rows, Warnings]
```

---

### 4. Database Schema: `tbl_importagentpolicy`

```sql
CREATE TABLE `tbl_importagentpolicy` (
  `ImportId` INT AUTO_INCREMENT PRIMARY KEY,
  `BatchId` VARCHAR(50) NOT NULL,
  `AgentCode` VARCHAR(50) NULL,
  `PolicyNo` VARCHAR(100) NULL,
  `CustomerName` VARCHAR(255) NULL,
  `VehicleNo` VARCHAR(50) NULL,
  `GrossPremium` DECIMAL(18,2) NULL DEFAULT 0.00,
  `NetPremium` DECIMAL(18,2) NULL DEFAULT 0.00,
  `ODPremium` DECIMAL(18,2) NULL DEFAULT 0.00,
  `TPPremium` DECIMAL(18,2) NULL DEFAULT 0.00,
  `CommissionAmount` DECIMAL(18,2) NULL DEFAULT 0.00,
  `CommissionPercent` DECIMAL(5,2) NULL DEFAULT 0.00,
  `IssueDate` DATETIME NULL,
  `ExpiryDate` DATETIME NULL,
  `CompanyId` INT NULL,
  `BranchId` INT NULL,
  `IsProcess` VARCHAR(10) DEFAULT '0',
  `ProcessDate` DATETIME NULL,
  `Remarks` TEXT NULL,
  `CreateDate` DATETIME DEFAULT CURRENT_TIMESTAMP,
  `CreateUser` VARCHAR(100) NULL,
  INDEX `idx_import_batch` (`BatchId`),
  INDEX `idx_import_agent` (`AgentCode`),
  INDEX `idx_import_policy` (`PolicyNo`),
  INDEX `idx_import_process` (`IsProcess`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

---

### 5. Verification & Validation Metrics

1. **Format Resilience**: Successfully handles files with leading/trailing blank rows, mixed currency formats (e.g. `₹ 12,450.50`), and scientific notation strings.
2. **Error Isolation**: Bad rows (e.g., non-numeric premiums or corrupted date strings) do not abort the entire batch; errors are recorded with row indices for administrative review.
3. **Audit Trail**: Every staged record retains the operator's user ID and timestamp for reconciliation.
