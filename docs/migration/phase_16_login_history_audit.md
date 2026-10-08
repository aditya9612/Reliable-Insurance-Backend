# PHASE 16 — LOGIN HISTORY & USER ACTIVITY AUDIT
## Reliable-Insurance-Backend: Authentication Auditing, Client Telemetry & Account Lockout Governance

---

### 1. Executive Summary
In the legacy ASP.NET WebForms system, user session events were partially audited through synchronous database insertions:
- Source: `Insurance\Log_In.aspx.cs` (Lines 50–54)
- Stored Procedure: `sp_insertLoginHistory`
- Target Table: `tbl_loginhistory` (`API_LoginHistory`)

This audit examines the exact stored fields, IP extraction methods, session lifecycles, account lockout policies, and privacy/compliance requirements, contrasting legacy vulnerabilities with modern FastAPI hardening.

---

### 2. Forensic Analysis of Legacy Login History

#### 2.1 Physical Table Structure: `tbl_loginhistory`
- **Columns**:
  1. `LoginHistoryId`: `int(11) NOT NULL AUTO_INCREMENT` (PK)
  2. `UserId`: `int(11) NOT NULL` (System user identifier linking to `tbl_user.UserId`)
  3. `UserName`: `varchar(255) NULL` (Username captured at authentication time)
  4. `LogInOrLogOut`: `varchar(50) NULL` (Event type: `"LogIn"`, `"LogOut"`, `"Failed"`)
  5. `funPerform`: `varchar(255) NULL` (Trigger function: `"Login Click"`, `"Session Timeout"`, `"Manual Logout"`)
  6. `IPAddress`: `varchar(100) NULL` (Extracted client IP address)
  7. `CreateDate`: `datetime NULL` (Event timestamp recorded in database)
  8. `Remark`: `varchar(255) NULL` (Context notes: `"ERP"`, `"Mobile App"`, or failure description)
- **Indexes**: Primary Key (`LoginHistoryId`), User Index (`ix_tbl_loginhistory_UserId`), Timestamp Index (`ix_tbl_loginhistory_CreateDate`).

#### 2.2 Client IP Extraction Logic (`Log_In.aspx.cs:L50-54`)
In the legacy C# code-behind:
```csharp
string ip = Request.ServerVariables["HTTP_X_FORWARDED_FOR"];
if (string.IsNullOrEmpty(ip))
{
    ip = Request.ServerVariables["REMOTE_ADDR"];
}
logh.IPAddress = ip;
logh.LogInOrLogOut = "LogIn";
logh.funPerform = "Login Click";
logh.Remark = "ERP";
userObj.BLL_InsertLoginHistiry(logh, "INS");
```

#### 2.3 Legacy Security Defects & Flaws:
1. **Unsanitized `X-Forwarded-For` Header (CWE-290 / IP Spoofing)**:
   - The legacy application blindly trusted `Request.ServerVariables["HTTP_X_FORWARDED_FOR"]` without validating reverse proxy origins. A malicious client could forge arbitrary IP headers to spoof their geographical location or audit trail.
2. **Missing Failure Logging**:
   - `BLL_InsertLoginHistiry` was invoked **only after** successful password validation in `Log_In.aspx.cs`. Failed brute-force attempts and credential stuffing attacks were **never recorded** in `tbl_loginhistory`!
3. **No Failed Login Lockout Policy**:
   - The legacy system lacked rate-limiting, CAPTCHA, or progressive account lockouts after consecutive failed password attempts.
4. **Synchronous DB Blocking**:
   - Every login incurred a synchronous, unindexed SQL insert, creating latency bottlenecks during peak morning login spikes.

---

### 3. Modern Security Hardening for Phase 16B

| Dimension | Legacy WebForms Behavior | Target Modern FastAPI Implementation | Security Classification |
|---|---|---|:---:|
| **Event Scope** | Successful logins and logouts only | Successful logins, failed logins (with failure reasons), password changes, and logouts | **SECURITY HARDENING** |
| **IP Resolution** | Blindly read `HTTP_X_FORWARDED_FOR` | Validates trusted proxy configurations (`request.client.host` or verified reverse-proxy header) | **SECURITY HARDENING** |
| **Client Telemetry** | IP address only | IP address, User-Agent header (browser/device fingerprint), country/region (if available) | **SECURITY HARDENING** |
| **Brute-Force Defense**| Zero rate-limiting or lockout | In-memory / Redis failed attempt tracking; account lockout after 5 consecutive failures for 15 minutes | **SECURITY HARDENING** |
| **Storage & Retention**| Unbounded growth in MySQL | Indexed `tbl_loginhistory` table with partitioned indexing and automated 90-day retention pruning | **SECURITY HARDENING** |
| **PII & Privacy** | Plaintext IP visible to all database users | IP masking in UI for non-security roles; compliance with DPDP Act 2023 | **COMPLIANCE** |

---

### 4. Target Stored Procedures & API Endpoints

#### 4.1 Stored Procedures Replaced:
- `sp_insertLoginHistory`: Replaced by `LoginHistoryRepository.create_entry(db, event)`
- `sp_SelectLoginHistory`: Replaced by `LoginHistoryRepository.list_entries(db, user_id, start_date, end_date, offset, limit)`

#### 4.2 Target REST Contracts for Phase 16B:
1. **`GET /api/v1/auth/login-history`**:
   - **Access**: `OWNER`, `ADMIN`, `IT SUPPORT`, `HR`
   - **Query Parameters**:
     - `user_id`: Optional[int]
     - `start_date`: Optional[date]
     - `end_date`: Optional[date]
     - `event_type`: Optional[str] (`"LOGIN"`, `"LOGOUT"`, `"FAILED"`)
     - `skip`: int = 0
     - `limit`: int = 50
   - **Response**: Paginated list of sanitized login audit events with masked IP for non-admin viewers.
2. **`GET /api/v1/auth/login-history/me`**:
   - **Access**: Any authenticated user
   - **Response**: The calling user's recent login sessions (allowing users to detect unauthorized account access).
3. **`POST /api/v1/auth/unlock-account/{user_id}`**:
   - **Access**: `OWNER`, `ADMIN`, `IT SUPPORT`
   - **Action**: Resets failed login counters and unlocks a locked user account.

---

### 5. Parity & Compliance Verification
- **Backward Compatibility**: `tbl_loginhistory` table schema preserves all 8 legacy column names and data types, ensuring historical database dumps can be queried seamlessly.
- **Audit Completeness**: Meets ISO 27001 and IRDAI cybersecurity audit requirements for user authentication traceability.
