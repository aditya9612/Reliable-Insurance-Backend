# Phase 15B — PII Masking Serialization Layer Forensic Reconciliation

**Document**: `docs/migration/phase_15b_pii_masking_reconciliation.md`
**Phase**: 15B — Operational Batch Jobs, Bulk Imports, Staging Utilities & Partner Profiles
**Date**: October 2026
**Status**: APPROVED & RECONCILED

---

## 1. Executive Summary

Finding 5 of the Phase 15B pre-commit audit noted that partner profiles (Employees, Agents, Franchises) returned raw Personally Identifiable Information (PII) including PAN numbers, Aadhaar numbers, and bank account numbers to all authorized viewers regardless of privilege level.

This document verifies the complete remediation of Finding 5, establishing a robust, non-mutating **response serialization masking layer** that:
1. Masks sensitive PII for non-privileged viewers (e.g., Branch Managers, Supervisors, Agents).
2. Delivers raw unmasked values to authorized administrative and HR roles (`OWNER`, `ADMIN`, `IT SUPPORT`, `HR`).
3. Preserves database records, session state, and internal calculation integrity without modifying raw stored values.

---

## 2. PII Field Inventory & Standards

| Profile Model | Schema Field | Legacy DB Column | Format | Masking Pattern | Example (Raw -> Masked) |
|---------------|--------------|------------------|--------|-----------------|-------------------------|
| Employee | `PAN_No` | `PAN_No` | 10 chars | First 6 masked, last 4 clear | `ABCDE1234F` -> `XXXXXX234F` |
| Employee | `AadharNo` | `AadharNo` | 12 chars | First 8 masked, last 4 clear | `123456789012` -> `XXXXXXXX9012` |
| Employee | `accountNo` | `accountNo` | 9-18 chars | All but last 4 masked | `98765432101234` -> `XXXXXXXXXX1234` |
| Agent | `PANNo` | `PANNo` | 10 chars | First 6 masked, last 4 clear | `XYZAB5678G` -> `XXXXXX678G` |
| Agent | `AadharNo` | `AadharNo` | 12 chars | First 8 masked, last 4 clear | `987654321098` -> `XXXXXXXX1098` |
| Agent | `accountNo` | `accountNo` | 9-18 chars | All but last 4 masked | `11223344556677` -> `XXXXXXXXXX6677` |
| Franchise | `PAN_No` | `PAN_No` | 10 chars | First 6 masked, last 4 clear | `PQRST9012H` -> `XXXXXX012H` |
| Franchise | `AadharNo` | `AadharNo` | 12 chars | First 8 masked, last 4 clear | `456789012345` -> `XXXXXXXX2345` |
| Franchise | `accountNo` | `accountNo` | 9-18 chars | All but last 4 masked | `99887766554433` -> `XXXXXXXXXX4433` |

---

## 3. Implementation Architecture

### 3.1 Masking Utilities (`app/schemas/profile.py`)
Masking functions operate on string representations and guarantee length preservation:
```python
def mask_pan(val: Optional[str]) -> Optional[str]:
    if not val:
        return val
    s = str(val).strip()
    if len(s) <= 4:
        return "X" * len(s)
    return "X" * (len(s) - 4) + s[-4:]

def mask_aadhar(val: Optional[str]) -> Optional[str]:
    if not val:
        return val
    s = str(val).strip()
    if len(s) <= 4:
        return "X" * len(s)
    return "X" * (len(s) - 4) + s[-4:]

def mask_account_number(val: Optional[str]) -> Optional[str]:
    if not val:
        return val
    s = str(val).strip()
    if len(s) <= 4:
        return "X" * len(s)
    return "X" * (len(s) - 4) + s[-4:]
```

### 3.2 Non-Mutating Schema Copy
To prevent mutating SQLAlchemy model instances in session (which would trigger unintentional database UPDATEs on flush/commit), masking is applied via Pydantic v2 `model_copy(update={...})`:
```python
def mask_employee_pii(emp: EmployeeResponse) -> EmployeeResponse:
    return emp.model_copy(update={
        "PAN_No": mask_pan(emp.PAN_No),
        "AadharNo": mask_aadhar(emp.AadharNo),
        "accountNo": mask_account_number(emp.accountNo),
    })
```

### 3.3 Endpoint Gate (`app/api/v1/endpoints/profiles.py`)
Privilege resolution evaluates the authenticated caller's role:
```python
PRIVILEGED_PII_ROLES = frozenset({"OWNER", "ADMIN", "IT SUPPORT", "HR"})

def is_privileged_for_pii(user: User) -> bool:
    role = (getattr(user, "role_name", None) or "").strip().upper()
    return role in PRIVILEGED_PII_ROLES
```
Applied dynamically across detail, list, create, and update responses for Employees, Agents, and Franchises.

---

## 4. Verification Test Evidence

Automated integration test `test_pii_masking_for_non_privileged_roles` in `tests/integration/test_phase15b_profiles_and_utilities_api.py` verifies:
1. `ADMIN` reads unmasked PAN, Aadhaar, and Bank Account numbers for Employees, Agents, and Franchises.
2. `MANAGER` reads masked values across both detail (`/api/v1/{entity}/{id}`) and list (`/api/v1/{entity}`) endpoints.
3. Direct database queries confirm `tbl_employee.PAN_No`, `AadharNo`, and `accountNo` remain raw, unmasked, and uncorrupted.
