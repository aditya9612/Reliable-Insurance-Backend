# Phase 13 Renewal CRM & Performance Engine Parity

**Generated At**: 2026-10-07
**Component**: Policy Renewal Lifecycle, Telecaller CRM & Performance Analytics

---

### 1. Legacy Renewal Process vs Phase 13 Architecture

In the legacy ASP.NET application:
- Telecallers accessed `Clerk/PreYearRenawalentry.aspx` to manually review expiring policies.
- Statuses were updated directly via `Sp_UpdatePreYearRenewalStatus`.
- Follow-up entries were added via `Sp_InsertFollowPreYearRenewalStatus` with no audit history table.
- Financial Year was calculated via fragile string manipulation.
- Reports were sent via synchronous ASP.NET email triggers (`Clerk/SendRenewalReport.aspx.cs`).

In Phase 13:
- Fully asynchronous REST API endpoints with strict role-based access control.
- Immutable audit history tracked in `tbl_renewal_followup_history`.
- Rigorous Indian Financial Year arithmetic (`April 1 – March 31`).
- Multi-tenant tenant/branch/agent scoping preventing cross-tenant data leaks.
- Background asynchronous scanner `daily_renewal_expiry_check` (Celery/Cron) automated scheduling.

---

### 2. Multi-Tenant Scoping Rules for Renewals

1. **Global Administrators (`GLOBAL_ADMIN_ROLES`: `OWNER`, `ADMIN`, `IT SUPPORT`)**:
   - Cross-branch visibility into all expiring policies and telecaller follow-ups.
   - Unrestricted filtering by `branch_id`, `agent_id`, or `executive_id`.

2. **Branch Users / Managers (`BRANCH_MANAGER`, `BRANCH_USER`)**:
   - Strictly scoped to policies belonging to their assigned `current_user.BranchId`.

3. **POSP Agents (`AGENT`, `POSP`)**:
   - Strictly scoped to policies where `Transaction.AgentId == current_user.partner_user_id` (or `current_user.UserId`).

4. **Sales Executives / Employees (`SALES`, `EMPLOYEE`)**:
   - Strictly scoped to policies assigned to their `current_user.emp_id` (or `current_user.UserId`).

---

### 3. Analytics & Dashboard Metrics

Endpoint `GET /api/v1/renewals/dashboard?financial_year=YYYY-YYYY` aggregates:

1. **Executive Breakdown (`ExecutiveRenewalCount`)**:
   - Groups by `ExecutiveId` and calculates total policies in `Follow`, `Done`, `Lost`, and `Vehicle` status.

2. **Company Breakdown (`InsurerRenewalCount`)**:
   - Groups by `InsuranceCompany`.
   - Computes total due count, renewed count (`Done`), and retention rate percentage:
     $$\text{retention\_rate\_pct} = \frac{\text{renewed\_count}}{\text{due\_count}} \times 100.0$$

3. **Overall Summary Metrics**:
   - `total_target_count`
   - `follow_up_count`
   - `renewed_done_count`
   - `lost_count`
   - `vehicle_sold_count`
   - `overall_retention_rate_pct`
