# Phase 15B — Task Execution Model Forensic Reconciliation

**Document**: `docs/migration/phase_15b_task_execution_reconciliation.md`
**Phase**: 15B — Operational Batch Jobs, Bulk Imports, Staging Utilities & Partner Profiles
**Date**: October 2026
**Status**: APPROVED & RECONCILED

---

## 1. Executive Summary

During the Phase 15B forensic audit, Finding 2 identified an architectural documentation contradiction:
- Several planning documents discussed a Celery-based worker queue (`@shared_task`, `celery_app`).
- The actual codebase implementation in `app/tasks/operational_tasks.py` and `app/services/utility_service.py` executes tasks as **native Python `async`/`await` coroutines** invoked via authenticated administrative REST endpoints (`/api/v1/batch-tasks/*`).

This reconciliation explicitly confirms that:
1. **The application does NOT use Celery or `@shared_task`**.
2. No phantom Celery worker infrastructure has been fabricated.
3. Native async coroutines provide deterministic, ACID-compliant, transaction-safe execution within the FastAPI ASGI process.
4. External orchestration (e.g., Kubernetes CronJob, systemd timer, or scheduled runner) invokes these batch tasks via authenticated HTTP POST requests with JWT Bearer tokens.

---

## 2. Architectural Comparison

```
========================================================================================
DIMENSION               SPECULATIVE DESIGN (CELERY)       IMPLEMENTED REALITY (NATIVE ASYNC)
========================================================================================
Execution Driver        Celery Worker Process             FastAPI ASGI Event Loop Coroutine
Task Decorator          @shared_task                      Native async def coroutine
Trigger Mechanism       Redis Celery Broker Message       HTTP POST with JWT Bearer Auth
Transaction Scope       Separate Celery DB Session        In-request AsyncSession with rollback
Observability           Celery Flower / Broker Monitor    FastAPI Standard Structured Logging
RBAC Enforcement        External queue permissions        require_roles("OWNER", "ADMIN", "IT SUPPORT")
External Dependencies   Celery, Kombu, RabbitMQ/Redis     Native FastAPI / SQLAlchemy AsyncSession
========================================================================================
```

---

## 3. Implemented Task Functions (`app/tasks/operational_tasks.py`)

All operational batch tasks are defined as native coroutines that instantiate `UtilityService` with a managed database session:

1. **`run_overdue_cheque_lock_task(threshold_days: int = 15)`**:
   - Scans `tbl_transactionpayment` for uncleared cheques exceeding `threshold_days`.
   - Resolves originating user from `tbl_transaction.CreateUser`.
   - Atomically sets `isdeleted = '1'` in `tbl_user` to block login (LBR-069 parity).
   - Commits session and returns structured `OverdueChequeLockResult`.

2. **`run_birthday_greetings_dispatch_task(target_date: Optional[date] = None)`**:
   - Scans `tbl_customer`, `tbl_employee`, and `tbl_agent` for matching birth month/day.
   - Dispatches notifications via `NotificationService` (mocked in test/dev).
   - Returns structured `BirthdayGreetingDispatchResult`.

3. **`run_wallet_locks_cleanup_task()`**:
   - Releases expired e-wallet distributed locks in local Redis (`localhost:6379/0`).
   - Returns structured `OperationalCleanupResult`.

4. **`run_ephemeral_storage_cleanup_task(retention_hours: int = 24)`**:
   - Prunes temporary export artifacts from local storage directory exceeding retention window.
   - Prevents disk saturation on reporting export volumes.
   - Returns structured `OperationalCleanupResult`.

---

## 4. Verification and Parity

- All 4 batch tasks are fully tested and functional without requiring Celery daemon processes.
- All documentation files referencing Celery have been updated to reflect the native async coroutine execution model.
