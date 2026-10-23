# Pre-Deployment Blocker Remediation Plan
**Reliable-Insurance-Backend**  
**Authoritative Baseline:** [`docs/migration/PRODUCTION_READINESS_GAP_ASSESSMENT.md`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/docs/migration/PRODUCTION_READINESS_GAP_ASSESSMENT.md)  
**Execution Date:** 2026-10-21  
**Branch:** `tejas-feature`  
**HEAD Commit:** `84dec83eae70e251d0d40763295425c656307342`  
**Plan Status:** Phase 1A Implemented & Verified (IST Reporting Remediated; Zero Uncommitted Breaking Changes)  

---

## Executive Summary & Plan Purpose

The `Reliable-Insurance-Backend` application has achieved 100% test coverage and feature parity for all active ERP domain logic, financial invariants, and REST API routes (517 baseline tests passing). However, as established in the Production Readiness Gap Assessment, direct production deployment remains **BLOCKED BY EXTERNAL DEPENDENCIES** and operational prerequisites.

This document defines a minimal, non-disruptive, evidence-based remediation plan covering three essential workstreams:
- **Workstream A**: Remediation of Indian Standard Time (`Asia/Kolkata`) day boundaries in executive payment and transaction reporting.
- **Workstream B**: Operational background task execution architecture (recommending a lightweight async CLI runner over heavy Celery overhead).
- **Workstream C**: Actionable verification protocols and ownership checklists for external blockers (DBA schema dump, mobile fleet contract audit, production secret provisioning, and Task Scheduler schedules).

---

## Workstream A: Indian Standard Time (IST) Reporting Remediation

### A.1 Problem Statement & Code Trace

In [`app/tasks/renewal_tasks.py`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/app/tasks/renewal_tasks.py) (lines 59–112), `daily_payment_report` is implemented as:

```python
async def daily_payment_report(
    session: AsyncSession,
    report_date: datetime = None,
) -> Dict[str, Any]:
    if report_date is None:
        report_date = datetime.utcnow()

    start_of_day = datetime(report_date.year, report_date.month, report_date.day, 0, 0, 0)
    end_of_day = start_of_day + timedelta(days=1)
    ...
    payment_stmt = select(...).where(
        TransactionPayment.PaymentDate >= start_of_day,
        TransactionPayment.PaymentDate < end_of_day,
    )
    tx_stmt = select(...).where(
        Transaction.RiskStartdate >= start_of_day,
        Transaction.RiskStartdate < end_of_day,
        ...
    )
```

#### The Reporting Skew Defect:
1. **Timestamp Representation**:
   - `TransactionPayment.PaymentDate` in [`app/services/policy_booking.py`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/app/services/policy_booking.py:L1333) is populated with `now_dt = datetime.utcnow()` (naive UTC).
   - In MySQL, the column is a naive `DATETIME` (`2026-10-21 14:30:00`).
2. **Indian Business Day vs. UTC Day**:
   - An Indian operational business day begins at `00:00:00 IST` (`18:30:00 UTC` of the previous calendar day) and ends at `23:59:59 IST` (`18:29:59 UTC` of the current calendar day).
   - Because `daily_payment_report` truncates `datetime.utcnow()` directly to UTC midnight (`00:00:00 UTC`), any transaction booked between `00:00:00 IST` and `05:30:00 IST` (early morning) is incorrectly attributed to the *previous* calendar day.
   - Any transaction booked after `18:30:00 UTC` (which is already the next business morning in India) is attributed to the current UTC day.

---

### A.2 Minimal Remediation Design

Python 3.11 includes standard library `zoneinfo` (`from zoneinfo import ZoneInfo`). Zero third-party dependencies are required.

#### Architectural Rules:
1. Accept an optional `target_date: Optional[date] = None`. If omitted, determine today's date in `Asia/Kolkata`.
2. Convert the Indian business day boundaries (`00:00:00 IST` to `00:00:00 IST + 1 day`) to naive UTC timestamps to query `TransactionPayment.PaymentDate`.
3. For `Transaction.RiskStartdate` (which represents a pure date without time of day, stored at `00:00:00`), query between `start_date` and `end_date` calendar values.

```mermaid
flowchart LR
    A["Caller / Scheduled Job<br/>(target_date = 2026-10-21)"] --> B["IST Midnight Boundary<br/>2026-10-21 00:00:00 IST"]
    B --> C["Convert to UTC Query Window<br/>2026-10-20 18:30:00 UTC to 2026-10-21 18:30:00 UTC"]
    C --> D["SQL Filter: PaymentDate >= utc_start AND PaymentDate < utc_end"]
    D --> E["Aggregated Daily Metrics (Accurate to IST Business Day)"]
```

#### Proposed Minimal Implementation for `daily_payment_report`:

```python
from datetime import datetime, date, time, timedelta, timezone
from zoneinfo import ZoneInfo
from typing import Dict, Any, Optional

IST = ZoneInfo("Asia/Kolkata")

async def daily_payment_report(
    session: AsyncSession,
    report_date: Optional[date] = None,
) -> Dict[str, Any]:
    """
    Scheduled task to aggregate daily payment instruments and booked transactions
    aligned to Indian Standard Time (IST, UTC+05:30) business boundaries.
    """
    if report_date is None:
        report_date = datetime.now(IST).date()
    elif isinstance(report_date, datetime):
        report_date = report_date.date()

    # 1. Compute IST midnight boundaries
    ist_midnight_start = datetime.combine(report_date, time.min, tzinfo=IST)
    ist_midnight_end = ist_midnight_start + timedelta(days=1)

    # 2. Convert IST boundaries to naive UTC for matching UTC PaymentDate records
    utc_start = ist_midnight_start.astimezone(timezone.utc).replace(tzinfo=None)
    utc_end = ist_midnight_end.astimezone(timezone.utc).replace(tzinfo=None)

    # 3. Query PaymentDate in UTC window
    payment_stmt = (
        select(
            func.count(TransactionPayment.PaymentId),
            func.coalesce(func.sum(TransactionPayment.PaidAmount), 0.0),
        )
        .where(
            TransactionPayment.PaymentDate >= utc_start,
            TransactionPayment.PaymentDate < utc_end,
        )
    )
    payment_res = await session.execute(payment_stmt)
    payment_count, payment_total = payment_res.first()

    # 4. Query RiskStartdate using calendar date boundary
    cal_start = datetime.combine(report_date, time.min)
    cal_end = cal_start + timedelta(days=1)
    tx_stmt = (
        select(
            func.count(Transaction.TransanctionId),
            func.coalesce(func.sum(Transaction.Amount), 0.0),
        )
        .where(
            Transaction.RiskStartdate >= cal_start,
            Transaction.RiskStartdate < cal_end,
            or_(Transaction.isdeleted == "0", Transaction.isdeleted.is_(None)),
        )
    )
    tx_res = await session.execute(tx_stmt)
    tx_count, tx_total = tx_res.first()

    return {
        "report_date": report_date.isoformat(),
        "timezone": "Asia/Kolkata",
        "utc_window_start": utc_start.isoformat(),
        "utc_window_end": utc_end.isoformat(),
        "receipts_count": int(payment_count or 0),
        "receipts_total_amount": float(payment_total or 0.0),
        "payments_count": int(payment_count or 0),
        "payments_total_amount": float(payment_total or 0.0),
        "booked_policies_count": int(tx_count or 0),
        "booked_premium_total": float(tx_total or 0.0),
        "generated_at": datetime.now(IST).isoformat(),
    }
```

---

### A.3 Test Specifications for Workstream A

Create unit tests in `tests/unit/test_phase13_renewal_calculations.py` or `tests/unit/test_daily_reporting_ist.py`:

1. **`test_ist_midnight_boundary_inclusion`**:
   - Insert payment record at `2026-10-20 18:31:00 UTC` (which is `2026-10-21 00:01:00 IST`).
   - Run report for `2026-10-21`.
   - **Assertion**: Payment record is included in the `2026-10-21` report.
2. **`test_ist_midnight_boundary_exclusion`**:
   - Insert payment record at `2026-10-20 18:29:00 UTC` (which is `2026-10-20 23:59:00 IST`).
   - Run report for `2026-10-21`.
   - **Assertion**: Payment record is excluded from `2026-10-21` report and included in `2026-10-20` report.
3. **`test_indian_financial_year_transition`**:
   - Run report across the March 31 / April 1 cutover (`2026-03-31` and `2026-04-01`).
   - **Assertion**: Boundaries transition cleanly without time leakage across financial years.
4. **`test_calendar_year_transition`**:
   - Test December 31 / January 1 boundary.
   - **Assertion**: Month and year boundaries calculate accurately without ValueError.

---

### A.4 Implementation Outcome & Verification Evidence (Phase 1A Completed)

#### 1. Code Changes Applied:
- **[`app/tasks/renewal_tasks.py`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/app/tasks/renewal_tasks.py)**:
  - Imported `date`, `time`, `timezone`, `Optional`, `Union` from `datetime`/`typing`, and `ZoneInfo` from `zoneinfo`.
  - Defined `IST = ZoneInfo("Asia/Kolkata")`.
  - Updated `daily_payment_report(session, report_date)` to compute IST business day interval `[00:00 IST, next-day 00:00 IST)`.
  - Converted IST midnight boundaries to naive UTC timestamps (`utc_payment_start`, `utc_payment_end`) to accurately match naive UTC `PaymentDate` records in MySQL.
  - Retained exact calendar date boundaries (`cal_start`, `cal_end`) for `Transaction.RiskStartdate`.
  - Preserved all existing response dictionary keys while adding `timezone`, `utc_window_start`, and `utc_window_end`.
- **[`tests/unit/test_phase13_renewal_calculations.py`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/tests/unit/test_phase13_renewal_calculations.py)**:
  - Added table cleanup for `tbl_transactionpayment` in test fixture.
  - Implemented 5 focused unit tests covering IST midnight inclusion/exclusion, December-January rollover, March 31 - April 1 financial year transition, naive/aware datetime compatibility, and separate `RiskStartdate` query verification.

#### 2. Verification Test Execution Evidence:
- Focused test suite execution:
  - `pytest -q --tb=short tests/unit/test_phase13_renewal_calculations.py`: **10 passed in 0.96s (100% pass rate)**.
- Regression suite small-batch execution:
  - `tests/integration/test_phase13_renewal_crm_api.py`: **3 passed in 2.27s**.
  - `tests/integration/test_phase13_integrations_api.py`: **8 passed in 4.28s**.
  - `tests/unit/test_phase13_rc_and_providers.py`: **12 passed in 0.43s**.
  - `tests/unit/test_phase13_otp_lifecycle.py`: **5 passed in 1.09s**.
  - `tests/unit/test_phase15b_utilities_calculations.py`: **6 passed in 0.36s**.
  - **Total Verified Tests in Phase 1A**: **44 / 44 PASSED (0 failures, 0 errors, 0 skips)**.

#### 3. Remaining Operational Risks & Mitigation:
- **Historical Data Timestamp Ambiguity**: Legacy .NET C# entries written prior to migration may contain naive timestamps that were stored as local Indian time rather than UTC.
  - *Mitigation*: For historical reports prior to cutover date, an optional query flag or historical boundary handler can be provided if historical reconciliation discrepancies are noted by finance. All transactions booked by the modernized backend strictly follow UTC database persistence, eliminating future ambiguity.

---

## Workstream B: Background Tasks Execution Architecture

### B.1 Codebase Inventory & Findings
The application contains six background tasks:
1. `daily_renewal_expiry_check` ([`app/tasks/renewal_tasks.py`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/app/tasks/renewal_tasks.py))
2. `daily_payment_report` ([`app/tasks/renewal_tasks.py`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/app/tasks/renewal_tasks.py))
3. `enforce_overdue_cheque_locks_task` ([`app/tasks/operational_tasks.py`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/app/tasks/operational_tasks.py))
4. `dispatch_birthday_greetings_task` ([`app/tasks/operational_tasks.py`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/app/tasks/operational_tasks.py))
5. `cleanup_stale_wallet_locks_task` ([`app/tasks/operational_tasks.py`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/app/tasks/operational_tasks.py))
6. `cleanup_ephemeral_storage_task` ([`app/tasks/operational_tasks.py`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/app/tasks/operational_tasks.py))

#### Session Lifecycle Finding:
All six functions accept `session: AsyncSession` directly. None of them currently manage their own session creation, commit, rollback, or connection pool disposal. They rely on an external caller to open and close `AsyncSessionLocal()`.

---

### B.2 Architectural Comparison & Trade-off Matrix

| Evaluation Dimension | Option A: Native Async CLI Runner (cron/systemd) | Option B: Celery + Redis + Celery Beat |
|---|---|---|
| **External Dependencies** | **0 new dependencies**. Uses built-in `asyncio` & existing `aiomysql`. | Adds 5+ dependencies (`celery`, `billiard`, `kombu`, `vine`, `amqp`). |
| **Process Model** | Ephemeral process; executes job, flushes logs, terminates cleanly. | 2 permanent long-running daemons (`celery worker` + `celery beat`). |
| **Async Compatibility** | **100% Native**. Direct `await task_func(session)` inside asyncio loop. | **Impedance Mismatch**. Celery is sync; requires `async_to_sync` or nested event loops per task. |
| **Memory Footprint** | ~35 MB transient RAM per execution; 0 MB idle. | ~180 MB persistent RAM per worker daemon + Redis broker overhead. |
| **Operational Failure Risk** | Standard Linux cron/systemd logging; failure returns exit code 1. | Worker zombie processes, prefork deadlocks, stale broker locks, beat sync drift. |
| **Overlapping Execution Guard** | Linux `flock` or Redis `SET NX EX` distributed lock. | Celery Beat single-instance or Redbeat lock. |
| **Workload Match** | **Perfect**. The ERP only runs 4-5 batch jobs daily. | **Overkill**. Built for high-volume message queues (10,000+ msg/sec). |

### B.3 Architectural Recommendation

> ### **RECOMMENDATION: OPTION A (Native Async CLI Runner via Standard Cron / Systemd)**
>
> 1. Celery is absent from `requirements.txt`. Adding it creates unwarranted infrastructure bloat for a workload of 4 to 5 daily batch jobs.
> 2. Option A natively integrates with SQLAlchemy 2.0 async sessions without clumsy event-loop bridging.
> 3. Option A produces standard UNIX exit codes (`0` on success, `1` on error), allowing native integration with systemd, Docker container health checks, or cloud schedulers (AWS EventBridge, Google Cloud Run Jobs).

---

### B.4 Minimal Implementation Plan for Option A

Create [`app/tasks/runner.py`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/app/tasks/runner.py):

```python
"""
CLI Task Runner for Scheduled Operational Background Jobs.
Usage: python -m app.tasks.runner <task_name> [--param=val]
"""
import sys
import asyncio
import logging
from typing import Dict, Any, Callable
from app.db.session import AsyncSessionLocal
from app.tasks.renewal_tasks import daily_renewal_expiry_check, daily_payment_report
from app.tasks.operational_tasks import (
    enforce_overdue_cheque_locks_task,
    dispatch_birthday_greetings_task,
    cleanup_stale_wallet_locks_task,
    cleanup_ephemeral_storage_task,
)

logger = logging.getLogger("task_runner")

TASK_REGISTRY: Dict[str, Callable] = {
    "daily_renewal_expiry_check": daily_renewal_expiry_check,
    "daily_payment_report": daily_payment_report,
    "enforce_overdue_cheque_locks": enforce_overdue_cheque_locks_task,
    "dispatch_birthday_greetings": dispatch_birthday_greetings_task,
    "cleanup_stale_wallet_locks": cleanup_stale_wallet_locks_task,
    "cleanup_ephemeral_storage": cleanup_ephemeral_storage_task,
}

async def execute_task(task_name: str) -> None:
    if task_name not in TASK_REGISTRY:
        logger.error(f"Unknown task: {task_name}. Available: {list(TASK_REGISTRY.keys())}")
        sys.exit(1)

    task_func = TASK_REGISTRY[task_name]
    logger.info(f"Starting background task: {task_name}")

    async with AsyncSessionLocal() as session:
        try:
            result = await task_func(session)
            await session.commit()
            logger.info(f"Task completed successfully: {task_name}. Result: {result}")
        except Exception as exc:
            await session.rollback()
            logger.exception(f"Task failed with unhandled exception: {task_name} - {exc}")
            sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m app.tasks.runner <task_name>")
        sys.exit(1)
    asyncio.run(execute_task(sys.argv[1]))
```

#### Standard Linux Crontab Configuration:
```cron
# Reliable Insurance ERP Daily Operational Schedule (IST Server Time)
0 7 * * *   cd /opt/reliable-backend && /opt/reliable-backend/venv/bin/python -m app.tasks.runner dispatch_birthday_greetings >> /var/log/reliable/birthdays.log 2>&1
0 8 * * *   cd /opt/reliable-backend && /opt/reliable-backend/venv/bin/python -m app.tasks.runner daily_renewal_expiry_check >> /var/log/reliable/renewals.log 2>&1
30 8 * * *  cd /opt/reliable-backend && /opt/reliable-backend/venv/bin/python -m app.tasks.runner enforce_overdue_cheque_locks >> /var/log/reliable/cheques.log 2>&1
0 23 * * *  cd /opt/reliable-backend && /opt/reliable-backend/venv/bin/python -m app.tasks.runner daily_payment_report >> /var/log/reliable/reports.log 2>&1
*/30 * * * * cd /opt/reliable-backend && /opt/reliable-backend/venv/bin/python -m app.tasks.runner cleanup_stale_wallet_locks >> /var/log/reliable/wallet.log 2>&1
```

---

### B.5 Implementation Outcome & Verification Evidence (Phase 1B Completed)

#### 1. Code Changes Applied:
- **[`app/tasks/runner.py`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/app/tasks/runner.py)**:
  - Created standalone CLI task runner supporting `python -m app.tasks.runner <task_name> [--params]`.
  - Implemented explicit allowlist `TASK_REGISTRY` mapping 6 registered background tasks.
  - Implemented portable, cross-platform file locking (`TaskLock`) to prevent overlapping executions with dual-tier PID liveness check and 4-hour stale lock detection fallback.
  - Manages `AsyncSessionLocal` lifecycle: commits on success, rolls back on exception, cleans up session.
  - Properly disposes database engine connections upon exit via `close_engine()`.
  - Returns deterministic standard exit codes: `0` (Success), `1` (Task Failure), `2` (Lock Contention), `3` (Invalid Task), `4` (CLI Argument Error).
- **[`tests/unit/test_task_runner.py`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/tests/unit/test_task_runner.py)**:
  - Implemented 12 unit tests covering allowlist validation, session commit/rollback, lock acquisition/release, PID liveness retention, dead-PID override, lock contention blocking, CLI argument parsing, and exit codes.

#### 2. Verification Test Execution Evidence:
- `pytest -q --tb=short tests/unit/test_task_runner.py`: **12 passed in 0.62s (100% pass rate)**.
- Live CLI verification:
  - `python -m app.tasks.runner --help`: Exits `0` (`EXIT_SUCCESS`).
  - `python -m app.tasks.runner non_existent_task`: Exits `3` (`EXIT_INVALID_TASK`: rejected before DB session creation).
  - `python -m app.tasks.runner daily_payment_report --report_date=not-a-date`: Exits `4` (`EXIT_INVALID_ARGS`: rejected on parameter validation).
  - `python -m app.tasks.runner cleanup_ephemeral_storage`: Exits `0` (successfully executes and releases lock).
  - `python -m app.tasks.runner daily_payment_report --report_date=2026-10-21`: Exits `0` in 0.35s.

---

## Workstream C: External Dependencies & Deployment Gates

```
+-------------------------------------------------------------------------------------------------------+
|                                    EXTERNAL DEPLOYMENT GATES MATRIX                                   |
+--------------------------+-----------------------+---------------------+------------------------------+
| Gate ID                  | Classification        | Owner Role          | Pre-Deployment Condition     |
+--------------------------+-----------------------+---------------------+------------------------------+
| GATE-DBA-01 (Dump)       | BLOCKED (Prod Access) | Production DBA      | mysqldump --routines         |
| GATE-DBA-02 (Static IDs) | BLOCKED (Prod Access) | Production DBA      | Confirm IDs 110, 108, 243    |
| GATE-MOB-01 (Mobile APK) | BLOCKED (Fleet Audit) | Mobile Team Lead    | Confirm active APK URL       |
| GATE-SEC-01 (Secrets)    | PENDING (Config Gate) | DevOps / SecOps     | Inject live API tokens       |
| GATE-CRN-01 (Schedules)  | VERIFIED (In-Repo)    | Systems Admin       | Export Task Scheduler XML    |
+--------------------------+-----------------------+---------------------+------------------------------+
```

### C.1 Detailed Checklist & Protocol

#### GATE-DBA-01: Live Stored Procedures & Triggers Extraction
- **Classification**: `BLOCKED` (Strict Safety Constraint)
- **Owner**: Authorized Production DBA
- **Protocol**:
  ```bash
  mysqldump -h 103.149.199.250 -P 3309 -u admin_sa -p \
      --routines --no-data --triggers brahmainsurance > brahmainsurance_schema_and_routines.sql
  ```
- **Validation**: Verify that no database-level triggers modify `tbl_transaction`, `tbl_account`, or `tbl_commission` behind the application layer.

#### GATE-DBA-02: Static Configuration ID Confirmation
- **Classification**: `BLOCKED` (Requires Database Query)
- **Owner**: Production DBA / Lead Data Engineer
- **Protocol**:
  ```sql
  -- Verify existence of legacy Web.config magic constants
  SELECT 'Location Head' AS Role, EmpId, EmployeeName FROM tblemployee WHERE EmpId = 110
  UNION ALL
  SELECT 'Standard Sales Exec', EmpId, EmployeeName FROM tblemployee WHERE EmpId = 108
  UNION ALL
  SELECT 'Direct House Agent', AgentId, AgentName FROM tblagent WHERE AgentId = 243
  UNION ALL
  SELECT 'Direct House Franchise', FranchiseId, FranchiseName FROM tblfranchise WHERE FranchiseId = 1015;
  ```
- **Validation**: If IDs differ on target database, update `.env` or master settings before cutover.

#### GATE-MOB-01: Mobile Application Version & Endpoint Contract
- **Classification**: `BLOCKED` (External Fleet Audit)
- **Owner**: Mobile Engineering Lead
- **Protocol**:
  1. Inspect production APK build manifest (`AndroidManifest.xml` / network security config).
  2. Confirm base URL: does it call `/Service.asmx` or `/api/v1`?
  3. If `/Service.asmx`, deploy the following Nginx gateway reverse-proxy adapter rules:
     ```nginx
     location = /Service.asmx/AppLogin {
         proxy_pass http://127.0.0.1:8000/api/v1/auth/login;
     }
     location = /Service.asmx/SelectVehicleType {
         proxy_pass http://127.0.0.1:8000/api/v1/vehicles/types;
     }
     ```

#### GATE-SEC-01: Production Secret Injection & Validation
- **Classification**: `PENDING` (Deployment Gate)
- **Owner**: DevOps Lead
- **Required Secrets Matrix**:
  - `JWT_SECRET_KEY`: Cryptographically random 64-character hex string.
  - `DATABASE_URL`: Production MySQL credentials with connection pooling.
  - `SIGNZY_API_KEY`: Production bearer token for vehicle RC lookup.
  - `ATTESTR_API_KEY`: Production Basic auth token for CheckX lookup.
  - `HICALIBER_API_TOKEN`: Production JWT token for policy extraction.
  - `FAST2SMS_API_KEY` / `INDIATEXT_PASSWORD`: Production SMS gateway credentials.
  - `ONESIGNAL_APP_ID` & `ONESIGNAL_REST_API_KEY`: Production push notification credentials.
  - `SMTP_PASSWORD`: Production application password for automated emails.

---

## 4. Prioritized Implementation Sequence

The remediation should follow this strict three-phase sequence:

```mermaid
flowchart TD
    subgraph Phase_1 ["Phase 1: In-Repo Code Hardening (No External Dependencies)"]
        P1_A["Step 1.1: Implement IST time boundaries in daily_payment_report"]
        P1_B["Step 1.2: Add unit tests for IST midnight and boundary cutovers"]
        P1_C["Step 1.3: Create app/tasks/runner.py CLI runner for background jobs"]
        P1_D["Step 1.4: Add unit test for CLI runner task execution"]
    end

    subgraph Phase_2 ["Phase 2: External Stakeholder Approvals & Data Audit"]
        P2_A["Step 2.1: DBA dumps schema & routines from 103.149.199.250:3309"]
        P2_B["Step 2.2: DBA confirms static IDs 110, 108, 243, 1015"]
        P2_C["Step 2.3: Mobile Lead confirms active APK route contract"]
        P2_D["Step 2.4: Windows Admin provides legacy Task Scheduler XML timings"]
    end

    subgraph Phase_3 ["Phase 3: Staging Deployment & Gateway Cutover"]
        P3_A["Step 3.1: Deploy backend to staging environment with live secrets"]
        P3_B["Step 3.2: Configure systemd cron timers for app/tasks/runner.py"]
        P3_C["Step 3.3: Execute live smoke tests against staging database"]
        P3_D["Step 3.4: Authorize production cutover"]
    end

    Phase_1 --> Phase_2
    Phase_2 --> Phase_3
```

### Phase 1: In-Repo Code Hardening (Ready for Implementation)
- **Task 1.1**: Update `daily_payment_report` in `app/tasks/renewal_tasks.py` to use `ZoneInfo("Asia/Kolkata")` boundaries.
- **Task 1.2**: Add parameterized unit tests in `tests/unit/test_phase13_renewal_calculations.py`.
- **Task 1.3**: Create `app/tasks/runner.py` to encapsulate `AsyncSessionLocal` lifecycle and error logging.
- **Task 1.4**: Execute small-batch test runs to confirm zero regressions across all 517 baseline tests.

### Phase 2: External Stakeholder Verification (Gated)
- Obtain formal sign-offs for `GATE-DBA-01`, `GATE-DBA-02`, `GATE-MOB-01`, and `GATE-CRN-01`.

### Phase 3: Staging Deployment & Final Cutover (Gated)
- Inject production secrets (`GATE-SEC-01`), configure systemd cron jobs, and perform end-to-end UAT.
