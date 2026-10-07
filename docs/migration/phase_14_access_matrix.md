# Phase 14 — Access Control Matrix & Role Permissions

> **Audit Status**: COMPLETE (FORENSIC EXTRACTION)  
> **Phase**: Phase 14 (Reporting, Dashboard, MIS, POSP Invoicing & Statutory Statements) — Stage A  
> **Repository**: `Reliable-Insurance-Backend`  
> **Legacy Source**: `c:\Users\Admin\Downloads\InsurancefinalNew_2026_09_23\InsurancefinalNew`  
> **Mode**: STRICTLY READ-ONLY FORENSIC AUDIT (No implementation)

---

## 1. Executive Summary

Access control across reporting, dashboards, and exports is governed by a dual-layer security model:
1. **Endpoint & Feature Authorization**: Which user roles are allowed to access specific reporting screens, invoke generation endpoints, or trigger bulk exports.
2. **Row-Level Data Scoping**: What subset of the database records a given user can see based on their organizational tenancy (Global, Branch, Franchise, Operator, or Self).

This audit establishes the definitive security and access control matrix for all Phase 14 modules.

---

## 2. Multi-Tier Organizational Data Scoping

Every reporting query executed in the modernized backend must inject the caller's organizational boundary into the SQLAlchemy filter predicates:

```
┌─────────────────────────────────────────────────────────────┐
│                      GLOBAL TENANCY                         │
│             (ADMIN, IT SUPPORT, ACCOUNT)                    │
│   Unrestricted access to all branches, brokers, & agents    │
└──────────────────────────────┬──────────────────────────────┘
                               │
            ┌──────────────────┴──────────────────┐
            ▼                                     ▼
┌─────────────────────────────┐       ┌─────────────────────────────┐
│       BRANCH TENANCY        │       │      FRANCHISE TENANCY      │
│  (LOCATION HEAD, BR. MGR)   │       │         (FRANCHISE)         │
│ Filter: BranchId == user.br │       │ Filter: FranchiseId == u.fr │
└───────────┬─────────────────┘       └─────────────┬───────────────┘
            │                                       │
            ▼                                       ▼
┌─────────────────────────────┐       ┌─────────────────────────────┐
│      OPERATOR TENANCY       │       │        AGENT TENANCY        │
│    (OPERATOR, TELECALLER)   │       │        (AGENT, POSP)        │
│ Filter: CreatedBy == u.name │       │  Filter: AgentId == user.id │
└─────────────────────────────┘       └─────────────────────────────┘
```

---

## 3. Comprehensive RBAC Permissions Matrix

The table below details permissions across all 11 user roles for every reporting domain.

### Legend:
- `V`: **View** on-screen data / execute interactive grid queries within authorized scope.
- `E`: **Export** file downloads (`.xlsx`, `.csv`). Strictly gated to authorized finance/super-admin roles.
- `G`: **Generate** new documents (e.g. POSP Invoices, Payment Vouchers).
- `—`: **No Access** (HTTP 403 Forbidden).

| Report / Dashboard Module | Scope Filter Applied | `ADMIN` | `IT SUPPORT` | `ACCOUNT` | `LOCATION HEAD` | `OPERATOR` | `FRANCHISE` | `SALES` | `TELECALLER` | `AGENT` / `POSP` |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Admin Main Dashboard** | Global | V, E | V, E | V, E | — | — | — | — | — | — |
| **Accounts Summary Dashboard** | Global | V, E | V | V, E | — | — | — | — | — | — |
| **Owner Dashboard** | Global | V | — | — | — | — | — | — | — | — |
| **Agent Cut & Pay Dashboard** | Branch / Global | V, E | V | V, E | V | — | — | — | — | — |
| **Agent Outstanding Receivables** | Branch / Global | V, E | V | V, E | V | — | — | — | — | — |
| **MIS Transaction Search (View)** | Role-Scoped | V | V | V | V | V | V | V | V | V |
| **MIS Transaction Export (File)** | Global Only | **V, E** | **V, E** | **V, E** | **—** | **—** | **—** | **—** | **—** | **—** |
| **POSP Invoice Generator** | Global | V, G | — | V, G | — | — | — | — | — | — |
| **POSP Invoice Query & Download** | Scoped (Self/All) | V, E | V | V, E | V | — | V | — | — | V (Self) |
| **4-Tier General Ledger** | Global | V, E | — | V, E | — | — | — | — | — | — |
| **Voucher Print (Payment/Receipt)**| Global | V, E, G| — | V, E, G| — | — | — | — | — | — |
| **TDS Statutory Report** | Global | V, E | — | V, E | — | — | — | — | — | — |
| **Bank Commission Statement** | Global | V, E | — | V, E | — | — | — | — | — | — |
| **Payment Advice Statement** | Global / Self | V, E | — | V, E | — | — | — | — | — | V (Self) |
| **Daily Cash & Online Audit** | Branch / Global | V, E | — | V, E | V | — | — | — | — | — |
| **Insurer Reconciliation** | Global | V, E | V | V, E | — | — | — | — | — | — |
| **Bank Reconciliation** | Global | V, E | — | V, E | — | — | — | — | — | — |
| **Endorsement Audit Report** | Scoped | V, E | V | V | V | V | V | — | — | — |
| **Claims Register Report** | Scoped | V, E | V | V | V | V | V | — | — | — |
| **Telecaller Target Performance** | Branch / Global | V, E | — | — | V | — | — | V | V (Self) | — |
| **Executive Target Performance** | Branch / Global | V, E | — | — | V | — | — | V (Self)| — | — |
| **Renewal Expiry Report** | Scoped | V, E | V | — | V | V | V | V | V | V (Self) |

---

## 4. Critical Security Gates & Guardrails

1. **Export Gating Enforcement**:
   - `Adm_AllTransactionExport.aspx.cs:L48` establishes that data export is an administrative privilege. In FastAPI, `require_roles(["ADMIN", "IT SUPPORT", "ACCOUNT"])` is strictly bound to all `/api/v1/reports/*/export` routes.
2. **Column Masking Enforcement**:
   - Non-admin responses must strictly serialize through public DTO schemas (`PublicTransactionReportRow`) that omit internal brokerage profit, insurer gross commission percentages, and audit remarks.
3. **Multi-Tenant Leak Prevention**:
   - For `LOCATION HEAD`, `branch_id` must be derived directly from the authenticated JWT token claim, never accepted as an untrusted client query parameter.
   - For `AGENT` / `POSP`, `agent_id` must be bound to `current_user.agent_id`.
