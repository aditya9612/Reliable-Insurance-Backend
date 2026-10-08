# PHASE 15 — BACKGROUND JOBS & SCHEDULERS AUDIT
## Reliable-Insurance-Backend: Post-Phase 14 Scheduled Tasks & Background Operations Audit

---

### 1. Executive Summary
- **Legacy Architecture**: In ASP.NET WebForms (.NET 4.0), background tasks were triggered either via external **Windows Task Scheduler** hitting HTTP endpoints (e.g., `curl http://server/Clerk/SendPushNotiRenewal.aspx`) or via manual admin button clicks on WebForms pages.
- **FastAPI / Modern Architecture**: Celery distributed task queue backed by Redis (`redis://localhost:6379/0`) with Celery Beat scheduler.
- **Phase 13 Baseline**:
  - `daily_renewal_expiry_check`: Automated daily scan for expiring policies (30, 15, 7, 1 days).
  - `daily_payment_report`: Automated daily summary of cash/cheque/online collections.
- **Remaining Post-Phase 14 Background Tasks**: **4 operational batch tasks** identified for implementation in future phases.

---

### 2. Post-Phase 14 Background Job Reconciliation Matrix

| Job Name | Legacy Trigger & File | Modern Target Engine | Frequency | Inputs / Parameters | Output / Side Effect | Current Status | Priority |
|---|---|---|---|---|---|---|:---:|
| **Daily Renewal Expiry Scan** | Windows Task Scheduler hitting `SendPushNotiRenewal.aspx` | Celery Beat (`app.tasks.renewal_tasks`) | Daily (08:00 IST) | Expiry window (30, 15, 7, 1 days) | Updates `tbl_preyearrenewalstatus`, dispatches SMS/Push notifications | **MIGRATED (Phase 13)** | Completed |
| **Daily Payment Collection Report**| Admin button click on `Rpt_DailyCollection.aspx` | Celery Beat (`app.tasks.report_tasks`) | Daily (23:00 IST) | Current date, branch list | Generates collection summary email | **MIGRATED (Phase 13)** | Completed |
| **Overdue Cheque User Login Lock (`LBR-069`)** | Manual button click on `Adm_LockChequeEntry.aspx.cs` | Celery Beat (`app.tasks.cheque_tasks`) | Daily (00:00 IST) | Grace period days (default 15 days), pending cheques | Updates `tbl_user.is_locked = True` for agents with overdue uncleared cheques | **DEFERRED** | **P2** |
| **Customer Birthday Greeting Dispatch** | Windows Task Scheduler hitting `SendPushNotiForBdayWish.aspx.cs` | Celery Beat (`app.tasks.notification_tasks`) | Daily (09:00 IST) | Current day & month | Queries `tbl_customer.DateOfBirth` and dispatches personalized push/SMS | **DEFERRED** | **P2** |
| **Stale E-Wallet Lock & Temp Cleanup** | Manual DB script intervention in legacy | Celery Beat (`app.tasks.cleanup_tasks`) | Hourly | Lock TTL threshold (30 mins) | Releases abandoned wallet transaction locks (`AccTransId=11`) and deletes ephemeral exports | **DEFERRED** | **P2** |
| **Async Bulk Excel MIS Import Processing** | Synchronous loop in `adm_ImportTransAgentPolicyMIS.aspx.cs` | Celery Worker (`app.tasks.import_tasks`)| On-demand (file upload) | Uploaded `.xlsx` file, Staging ID | Validates rows, stages to `tbl_importagentpolicy`, logs validation errors | **DEFERRED** | **P2** |

---

### 3. Detailed Forensic Analysis of Remaining Jobs

#### 3.1 Overdue Cheque User Lock (`LBR-069`)
- **Legacy Behavior**: `Adm_LockChequeEntry.aspx.cs` executes a query against `tbl_transactionpayment` joining `tbl_transaction` and `tbl_user`. If an agent or clerk has accepted a cheque payment whose deposit/clearance date has exceeded the configured grace period without being cleared, their user account status was toggled to blocked.
- **Modern Target Design**: Celery task `enforce_overdue_cheque_locks` running daily at midnight. Performs parameterized query against `tbl_transactionpayment` (`PaymentMode == 'CHEQUE'` and `ChequeStatus == 'PENDING'` and `TransDate < NOW() - INTERVAL 15 DAY`). Toggles `tbl_user.is_active = False` or sets an explicit operational lock flag with an audit log.

#### 3.2 Customer Birthday Greeting Dispatch
- **Legacy Behavior**: `SendPushNotiForBdayWish.aspx.cs` executes `sp_SelectCustomerBirthdayWish` and calls OneSignal REST API to push notifications to mobile app users whose birthday matches the server date.
- **Modern Target Design**: Celery task `dispatch_customer_birthday_wishes` executing daily at 09:00 IST. Consumes the pluggable `NotificationService` implemented in Phase 13, formatting template messages and dispatching dual SMS/Push notifications.

#### 3.3 Stale E-Wallet Lock & Ephemeral Storage Cleanup
- **Legacy Behavior**: Legacy system had no automated cleanup; abandoned wallet top-up locks or stalled transactions required manual database intervention.
- **Modern Target Design**: Celery task `cleanup_stale_wallet_locks_and_storage` executing every hour. Cleans up wallet locks older than 30 minutes where no financial completion occurred, and purges temporary files from `storage_data/` older than 24 hours.

#### 3.4 Async Bulk Excel Policy MIS Import
- **Legacy Behavior**: Synchronous `ClosedXML` read inside `adm_ImportTransAgentPolicyMIS.aspx.cs` looping through thousands of rows in the HTTP request thread, frequently hitting IIS request timeouts.
- **Modern Target Design**: Celery task `process_bulk_policy_mis_file` receiving an uploaded file key, parsing rows asynchronously with OpenPyXL, performing row-level validation, and reporting progress back via task status query.
