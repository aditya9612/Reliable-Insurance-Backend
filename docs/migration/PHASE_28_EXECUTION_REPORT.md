# PHASE 28 EXECUTION REPORT: FRANCHISE AGENT GRID MARGIN OVERRIDE ENGINE

**Project**: `Reliable-Insurance-Backend`  
**Branch**: `tejas-feature`  
**Execution Date**: October 15, 2026  
**Status**: COMPLETE & VERIFIED  

---

## 1. Executive Summary

Phase 28 closes the highest-priority commercial gap in the Reliable Insurance ERP distribution system: the **Franchise Agent Grid Margin Override Engine** (`tbl_franchisegridmargin`).

In the legacy commercial architecture, insurance brokerages distribute policies through regional Franchisees, who in turn manage sub-agents ("Franchise Agents"). While the broker maintains global master commission grids for each insurer and vehicle class, each Franchisee negotiates custom retained margin cuts (`margin`) for sub-agents under their hierarchy. When an agent books or recalculates a policy, the franchise retains the configured margin percentage, and the agent receives `max(0, GrossGrid - Margin)`. If the franchise itself acts as the issuing agent (`IS_FR_As_AgentId == 1`), no margin is deducted.

Phase 28 delivers complete parity with this legacy financial distribution model, providing declarative models, Alembic migrations, Pydantic v2 validation schemas, service layer with multi-tenant franchise isolation, FastAPI RESTful endpoints, and a comprehensive test suite.

---

## 2. Legacy Source Evidence & Discovery

The implementation is backed strictly by verified C# legacy code:

| Legacy Component | Source Location | Description |
|---|---|---|
| **API Model** | `API/AllMaster.cs:3133-3142` (`API_FranchaiseGridMargin`) | Properties: `Id`, `FranchiseId`, `FranchiseAgentId`, `InsuranceCompanyId`, `PolicyTypeId`, `margin`. |
| **BLL Layer** | `BLL/BLL_Operations.cs` (`BLL_FranchiseEmployee`) | Methods: `BLL_franchaiseGridMargin`, `BLL_SelectFranchaiseGridMargin`. |
| **DAL Layer** | `DAL/DAL_Operations.cs:43520-43577` (`DAL_FranchiseEmployee`) | Executes `sp_franchsieGridMargin` with parameters `P_Id`, `P_FranchiseId`, `P_FranchiseAgentId`, `P_InsuranceCompanyId`, `P_PolicyTypeId`, `P_margin`, `P_opr`. |
| **WebForms Administrative UI** | `Insurance/Clerk/adm_FranchiseGridMargin.aspx.cs` (388 lines) | Multi-tenant administrative UI. Enforces Franchise isolation (`RoleId == "9"` locks `ddlFranchise` to `Session["FranchiseId"]`). Supports single-item upsert and batch policy-type apply. |
| **Commission Engine Integration** | `Insurance/Clerk/AgentCommissionRecalculation.aspx.cs:1577-1609, 1869-1895` | `FranchiseAgent_CalculateCommission`: checks `margin` override, subtracts margin from gross grid (`grid = gridValue - Margine`), or passes full grid when franchise operates as agent. |
| **Policy Request / Transaction Entry** | `Insurance/Clerk/PE_TransactionEntry.aspx.cs`, `AppPolicyRequestNew1.aspx.cs` | References `tbl_franchisegridmargin` for commission accounting and payout distribution. |

---

## 3. Database Schema & Alembic Migration

### Physical Table: `tbl_franchisegridmargin`
- **Revision ID**: `l28a0d0e2801`
- **Down Revision**: `k27a0c9d2701`
- **Engine**: MySQL InnoDB, utf8_general_ci, DYNAMIC row format.

```sql
CREATE TABLE tbl_franchisegridmargin (
    Id INT NOT NULL AUTO_INCREMENT,
    FranchiseId INT NOT NULL,
    FranchiseAgentId INT NOT NULL,
    InsuranceCompanyId INT NOT NULL,
    PolicyTypeId INT NOT NULL,
    margin DOUBLE NOT NULL DEFAULT 0.0,
    isdeleted INT NOT NULL DEFAULT 0,
    CreatedUser VARCHAR(100) NULL,
    CreatedDate DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
    UpdatedUser VARCHAR(100) NULL,
    UpdatedDate DATETIME NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (Id),
    INDEX ix_tbl_franchisegridmargin_franchise_id (FranchiseId),
    INDEX ix_tbl_franchisegridmargin_agent_id (FranchiseAgentId),
    INDEX ix_tbl_franchisegridmargin_company_id (InsuranceCompanyId),
    INDEX ix_tbl_franchisegridmargin_policy_type_id (PolicyTypeId),
    INDEX ix_tbl_franchisegridmargin_isdeleted (isdeleted),
    INDEX ix_tbl_franchisegridmargin_lookup (FranchiseId, FranchiseAgentId, InsuranceCompanyId, PolicyTypeId, isdeleted)
);
```

---

## 4. Architecture & Business Logic

### Mathematical Parity: Commission Split
Given a gross commission grid percentage $G$, a configured retained margin $M$, and premium basis $P$:

1. **Franchise Acting as Direct Agent** (`is_franchise_as_agent = True`):
   $$M_{\text{eff}} = 0$$
   $$G_{\text{agent}} = G$$
   $$\text{Payout}_{\text{agent}} = P \times \frac{G_{\text{agent}}}{100}$$
   $$\text{Payout}_{\text{franchise}} = 0$$

2. **Standard Sub-Agent Distribution** (`is_franchise_as_agent = False`):
   $$M_{\text{eff}} = M$$
   $$G_{\text{agent}} = \max(0, G - M_{\text{eff}})$$
   $$\text{Payout}_{\text{franchise}} = P \times \frac{M_{\text{eff}}}{100}$$
   $$\text{Payout}_{\text{agent}} = P \times \frac{G_{\text{agent}}}{100}$$

### Multi-Tenant Franchise Isolation (RBAC)
- **Global Administrative Roles** (`OWNER`, `ADMIN`): Permitted to view, configure, and batch-update margins across all franchises.
- **Franchise Role** (`FRANCHISE`, `RoleId == 9`): Server-side bound to their authenticated `franchise_id`. Any attempt to create, view, or modify margins for another franchise is rejected with `HTTP 403 Forbidden`.

---

## 5. RESTful API Endpoints (`/api/v1/franchise-margins`)

| Method | Route | Description | RBAC Scope |
|---|---|---|---|
| `POST` | `/api/v1/franchise-margins` | Create or update single margin override for an agent, insurer, and policy type. | Admin / Own Franchise |
| `POST` | `/api/v1/franchise-margins/batch` | Batch apply uniform margin override across multiple policy types. | Admin / Own Franchise |
| `GET` | `/api/v1/franchise-margins` | List active margin overrides with filtering and pagination (`skip`, `limit`). | Admin / Own Franchise |
| `GET` | `/api/v1/franchise-margins/lookup` | Direct query for exact active margin override. | Admin / Own Franchise |
| `POST` | `/api/v1/franchise-margins/calculate-split` | Compute net agent grid, franchise retained margin, and payout amounts. | Authenticated |
| `GET` | `/api/v1/franchise-margins/{id}` | Retrieve margin record details by primary key. | Admin / Own Franchise |
| `PUT` | `/api/v1/franchise-margins/{id}` | Update margin override percentage. | Admin / Own Franchise |
| `DELETE`| `/api/v1/franchise-margins/{id}` | Soft delete margin override (`isdeleted = 1`). | Admin / Own Franchise |

---

## 6. Test Verification & Regression Suite

All test suites were executed in small, focused batches against the local MySQL development database.

### 1. Phase 28 Test Suite (`tests/test_phase28_features.py`)
- `test_create_single_margin_override_success`: PASSED
- `test_upsert_existing_margin_override`: PASSED
- `test_batch_upsert_margins`: PASSED
- `test_lookup_margin_endpoint`: PASSED
- `test_get_and_update_margin_by_id`: PASSED
- `test_soft_delete_margin`: PASSED
- `test_calculate_commission_split_with_margin`: PASSED
- `test_calculate_commission_split_without_margin`: PASSED
- `test_calculate_commission_split_franchise_as_agent`: PASSED
- `test_calculate_commission_split_margin_exceeds_gross`: PASSED
- `test_franchise_tenant_isolation`: PASSED
- `test_margin_validation_constraints`: PASSED
**Result**: 12/12 passed (6.36s)

### 2. Regression Suites
- **Phase 27** (`tests/test_phase27_features.py`): 6/6 passed (3.92s)
- **Phase 26** (`tests/test_phase26_features.py`): 10/10 passed (6.49s)
- **Phase 25** (`tests/test_phase25_features.py`): 11/11 passed (6.80s)
- **Phase 9 Concurrency** (`tests/integration/test_phase9_accounting_voucher_concurrency.py`): 2/2 passed (4.76s)
- **Phase 18A Features** (`tests/test_phase18a_remaining_features.py`): 15/15 passed (14.37s)
**Total Test Count**: 56/56 passed (100% pass rate)

---

## 7. Migration Safety & Environment Adherence
- Strictly adhered to `tejas-feature` branch.
- No modifications to legacy source tree `InsurancefinalNew_2026_09_23/`.
- No modifications to `LBR-069`, `alembic/env.py`, or `requirements.txt`.
- No connection attempts to production database `brahmainsurance` (`103.149.199.250:3309`).
- Registered models increased to 135 tables across the ERP backend.
