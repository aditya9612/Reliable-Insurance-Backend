# Phase 15B — Batch Task RBAC Security Forensic Reconciliation

**Document**: `docs/migration/phase_15b_batch_task_rbac_reconciliation.md`
**Phase**: 15B — Operational Batch Jobs, Bulk Imports, Staging Utilities & Partner Profiles
**Date**: October 2026
**Status**: APPROVED & RECONCILED

---

## 1. Executive Summary

Finding 4 of the Phase 15B pre-commit audit identified that batch-task endpoints under `/api/v1/batch-tasks/*` relied on generic caller injection (`get_current_user`) without an explicit role barrier.

This document verifies the complete remediation of Finding 4, enforcing canonical administrative roles (`OWNER`, `ADMIN`, `IT SUPPORT`) via `require_roles(...)` across all operational batch endpoints.

---

## 2. Canonical RBAC Role Mapping

From the verified Phase 5F RBAC catalog (`app/core/rbac.py`):
```python
GLOBAL_ADMIN_ROLES: FrozenSet[str] = frozenset({
    "OWNER",
    "ADMIN",
    "IT SUPPORT",
})
```

- **Note on Non-Existent Roles**: There is NO `"DIRECTOR"` role in the verified 56-role catalog in `tbl_userrole`. Speculative role names were eliminated.
- **Enforced Role Gate**: Batch task execution has cross-cutting administrative impact (locking user accounts, firing notification broadcasts, flushing cache locks, cleaning storage artifacts). Therefore, only global administrators are authorized.

---

## 3. Secured Endpoints (`app/api/v1/endpoints/utilities.py`)

All 4 batch task routes inject `require_roles("OWNER", "ADMIN", "IT SUPPORT")`:

```python
@tasks_router.post(
    "/overdue-cheque-lock/run",
    response_model=OverdueChequeLockResult,
    summary="Trigger Overdue Cheque Lock Task (LBR-069)",
)
async def trigger_overdue_cheque_lock(
    threshold_days: int = Query(15, ge=1, le=180),
    current_user: User = Depends(require_roles("OWNER", "ADMIN", "IT SUPPORT")),
    session: AsyncSession = Depends(get_db),
) -> OverdueChequeLockResult:
    ...

@tasks_router.post(
    "/birthday-greetings/dispatch",
    response_model=BirthdayGreetingDispatchResult,
    summary="Trigger Birthday Greeting Dispatch Task",
)
async def trigger_birthday_greetings(
    target_date: Optional[date] = Query(None),
    current_user: User = Depends(require_roles("OWNER", "ADMIN", "IT SUPPORT")),
    session: AsyncSession = Depends(get_db),
) -> BirthdayGreetingDispatchResult:
    ...

@tasks_router.post(
    "/wallet-locks/cleanup",
    response_model=OperationalCleanupResult,
    summary="Trigger E-Wallet Lock Cleanup",
)
async def trigger_wallet_locks_cleanup(
    current_user: User = Depends(require_roles("OWNER", "ADMIN", "IT SUPPORT")),
    session: AsyncSession = Depends(get_db),
) -> OperationalCleanupResult:
    ...

@tasks_router.post(
    "/storage/ephemeral-cleanup",
    response_model=OperationalCleanupResult,
    summary="Trigger Ephemeral Storage Cleanup",
)
async def trigger_storage_cleanup(
    retention_hours: int = Query(24, ge=1, le=720),
    current_user: User = Depends(require_roles("OWNER", "ADMIN", "IT SUPPORT")),
    session: AsyncSession = Depends(get_db),
) -> OperationalCleanupResult:
    ...
```

---

## 4. Security Enforcement Behavior

| Client State | Role | HTTP Status | Detail / Error Message |
|--------------|------|-------------|------------------------|
| Unauthenticated | N/A | `401 Unauthorized` | `Not authenticated` / `Could not validate credentials` |
| Authenticated | `AGENT` | `403 Forbidden` | `Insufficient permissions` |
| Authenticated | `MANAGER` | `403 Forbidden` | `Insufficient permissions` |
| Authenticated | `BRANCH MANAGER` | `403 Forbidden` | `Insufficient permissions` |
| Authenticated | `ADMIN` | `200 OK` | Task result returned successfully |
| Authenticated | `OWNER` | `200 OK` | Task result returned successfully |
| Authenticated | `IT SUPPORT` | `200 OK` | Task result returned successfully |

---

## 5. Verification Test Evidence

Automated integration test `test_batch_tasks_rbac_enforcement` in `tests/integration/test_phase15b_profiles_and_utilities_api.py` verifies:
1. All 4 endpoints return HTTP 401 when called without authorization headers.
2. All 4 endpoints return HTTP 403 when called with `AGENT` credentials.
3. All 4 endpoints return HTTP 403 when called with `MANAGER` credentials.
4. All 4 endpoints return HTTP 200 when called with `ADMIN` credentials.
