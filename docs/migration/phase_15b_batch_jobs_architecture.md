# PHASE 15B — BATCH JOBS & OPERATIONAL TASKS ARCHITECTURE
## Background Automation, Scheduled Workflows, and System Hygiene

---

### 1. Executive Summary
Phase 15B establishes a resilient operational batch processing architecture for **Reliable-Insurance-Backend**. In the legacy ASP.NET system, background maintenance was performed either via manual invocation through administrative `.aspx` pages or legacy Windows Scheduled Tasks executing SQL queries directly.

The modernized Phase 15B operational subsystem provides:
1. **Native Async Execution**: Native asynchronous coroutines defined in `app/tasks/operational_tasks.py` and executed via `UtilityService` within the FastAPI ASGI event loop.
2. **On-Demand Admin Execution**: Authenticated REST API triggers defined in `/api/v1/batch-tasks/*` guarded by canonical RBAC (`OWNER`, `ADMIN`, `IT SUPPORT`).
3. **Audit Trail & Idempotency**: Comprehensive structured logging, error trapping, transaction scoping via `AsyncSession`, and structured summary metrics.

---

### 2. Operational Batch Job Catalog

| Job ID | Job Name | Legacy Source Reference | Cadence | Execution Channel | Target Function |
|---|---|---|---|---|---|
| **`JOB-01`** | Overdue Cheque Login Lock | `Adm_LockChequeEntry.aspx.cs` (`LBR-069`) | Daily (02:00 IST) & On-Demand | `POST /api/v1/batch-tasks/overdue-cheque-lock/run` | `UtilityService.enforce_overdue_cheque_locks` |
| **`JOB-02`** | Birthday Greeting Dispatch | `SendPushNotiForBdayWish.aspx.cs` | Daily (08:00 IST) & On-Demand | `POST /api/v1/batch-tasks/birthday-greetings/dispatch` | `UtilityService.dispatch_birthday_greetings` |
| **`JOB-03`** | Stale E-Wallet Reservation Lock Cleanup | Security & Concurrency Hygiene | Hourly & On-Demand | `POST /api/v1/batch-tasks/wallet-locks/cleanup` | `UtilityService.cleanup_stale_wallet_locks` |
| **`JOB-04`** | Ephemeral Temporary Storage Purge | System Storage Hygiene | Daily (03:00 IST) & On-Demand | `POST /api/v1/batch-tasks/storage/ephemeral-cleanup` | `UtilityService.cleanup_ephemeral_storage` |

---

### 3. Detailed Job Specifications

#### 3.1 `JOB-01`: Overdue Cheque User Login Lock (`LBR-069`)
- **Business Rationale**:
  Under legacy business rule `LBR-069`, when policies are booked against cheque payments, the cheque must be deposited and cleared within a strict aging window (default: 15 calendar days). If a cheque remains uncleared or unapproved by the cashier beyond this threshold, the user account of the staff member or agent who originated the transaction is deactivated to prevent further unauthorized bookings until the financial anomaly is reconciled.
- **Workflow & Algorithm**:
  1. Calculate cutoff timestamp: $\text{Cutoff} = \text{now}() - \Delta(\text{threshold\_days})$.
  2. Query `tbl_transactionpayment` joined with `tbl_transaction` where:
     - `PaymentType ILIKE '%cheque%'`
     - `CashierApproval == 0` OR `CashierApproval IS NULL`
     - `CreateDate <= Cutoff`
  3. Extract all unique policy creators (`tbl_transaction.CreateUser`).
  4. For each identified user:
     - Query `tbl_user` where `UserName = :uname` AND `isdeleted != '1'`.
     - Set `isdeleted = '1'`, `UpdateUser = 'SYSTEM (LBR-069: N overdue cheques)'`, and `UpdateDate = now()`.
     - Login attempts via `AuthService.authenticate` immediately fail with `401 Unauthorized` (`User account is inactive or disabled`).
  5. Return execution summary: `{ "scanned_records": N, "locked_users_count": M, "users_locked": [...] }`.
  6. Idempotency guaranteed: already deactivated accounts (`isdeleted == '1'`) are skipped.

#### 3.2 `JOB-02`: Partner & Customer Birthday Greeting Dispatch
- **Business Rationale**:
  Automates daily birthday greetings to active POSP agents, franchise partners, and customers, preserving legacy CRM engagement behavior from `SendPushNotiForBdayWish.aspx.cs`.
- **Legacy Template Parity**:
  `"Happy Birthday Dear Partner {name} ! We hope your special day is as fantastic as you are. Thanks- Reliable Assurance."`
- **Workflow & Algorithm**:
  1. Determine current calendar day and month: $(\text{today.month}, \text{today.day})$.
  2. Query active partners and customers:
     - `tbl_customer` matching `EXTRACT(MONTH FROM DateOfBirth) = today.month` AND `EXTRACT(DAY FROM DateOfBirth) = today.day`.
     - `tbl_employee` and `tbl_agent` matching birthday criteria.
  3. Render personalized message substituting recipient display name.
  4. Dispatch via `NotificationService` (mocked in dev/test, SMS/Push gateway in production).
  5. Record delivery status and summary counts.

#### 3.3 `JOB-03`: Stale E-Wallet Reservation Lock Cleanup
- **Business Rationale**:
  During multi-step policy bookings, e-wallet balances are held under an ephemeral distributed lock in Redis. If an agent's browser session disconnects or an external insurer API times out, the lock may remain in a pending state.
- **Workflow & Algorithm**:
  1. Scan Redis key registry for reservation keys older than 15 minutes (`TTL <= 0` or stale lease).
  2. Release reservation locks and reconcile balance counter to ensure zero leakage.

#### 3.4 `JOB-04`: Ephemeral Temporary Storage Purge
- **System Hygiene**:
  1. Scans `storage_data/temp/`, `storage_data/exports/`, and `storage_data/uploads/staging/`.
  2. Purges files older than 24 hours while strictly preserving permanent attachments in `storage_data/documents/` and `storage_data/policies/`.

---

### 4. Native Async Coroutine Registration (`app/tasks/operational_tasks.py`)
All tasks are exposed in `app/tasks/operational_tasks.py` as native async functions that manage session lifecycle and return structured Pydantic models:
```python
async def run_overdue_cheque_lock_task(threshold_days: int = 15) -> OverdueChequeLockResult:
    async with async_session_factory() as session:
        service = UtilityService(session)
        return await service.enforce_overdue_cheque_locks(threshold_days=threshold_days)

async def run_birthday_greetings_dispatch_task(target_date: Optional[date] = None) -> BirthdayGreetingDispatchResult:
    async with async_session_factory() as session:
        service = UtilityService(session)
        return await service.dispatch_birthday_greetings(target_date=target_date)

async def run_wallet_locks_cleanup_task() -> OperationalCleanupResult:
    async with async_session_factory() as session:
        service = UtilityService(session)
        return await service.cleanup_stale_wallet_locks()

async def run_ephemeral_storage_cleanup_task(retention_hours: int = 24) -> OperationalCleanupResult:
    async with async_session_factory() as session:
        service = UtilityService(session)
        return await service.cleanup_ephemeral_storage(retention_hours=retention_hours)
```
Scheduled invocation is driven externally via Kubernetes CronJob, systemd timer, or scheduled runner sending authenticated HTTP POST requests with Bearer tokens to `/api/v1/batch-tasks/*`.
