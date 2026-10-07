# Phase 13 — Role-Based Access Control & Scoping Matrix

> **Audit Status**: COMPLETE (CONFIRMED FROM SESSION CHECKS & BRANCH SCOPING LOGIC)  
> **Phase**: Phase 13 (External Integrations, Notifications & Renewal) — Stage A  
> **Repository**: `Reliable-Insurance-Backend`  
> **Legacy Source**: `InsurancefinalNew` (`PreYearRenewalEntryFollowup.aspx.cs`, `RC_CheckVehicleDtl.aspx.cs`, `adm_sendExcelTomailRenewal.aspx.cs`)  
> **Mode**: STRICTLY READ-ONLY (No permissions or user roles modified)

---

## 1. Overview

This document specifies the Role-Based Access Control (RBAC), multi-tenant branch isolation, and principal scoping rules across all Phase 13 functional domains:
- **Block A**: Vehicle RC & KYC Verification
- **Block B**: SMS & Mobile OTP
- **Block C**: Push Notifications & Internal Messages
- **Block D**: SMTP Email Dispatch & Reports
- **Block E**: Renewal CRM & Dashboard

---

## 2. Legacy User Roles & Hierarchy Mapping

| Legacy Role Name | Legacy Role ID | FastAPI Role Enum | Scope Level | Default Visibility |
| :--- | :--- | :--- | :--- | :--- |
| **Global Admin (Owner, Admin, IT Support)** | `1`, `2`, `28` | `OWNER`, `ADMIN`, `IT SUPPORT` | Global (All Branches) | Unrestricted across all data and actions |
| **Branch Manager** | `3` | `BRANCH_MANAGER` | Branch Scoped | All transactions & telecallers within own branch |
| **Accountant** | `4` | `ACCOUNTANT` | Branch Scoped | Payment receipts, commission statements, bank logs |
| **Clerk / Operator** | `5` | `CLERK` | Branch Scoped | RC lookup, policy entry, renewal follow-up editing |
| **Telecaller** | `6` | `TELECALLER` | Branch / Assigned Scoped | Expiring policy CRM, customer remarks, callback dates |
| **Sales Executive** | `7` | `SALES_EXECUTIVE` | Team Scoped | Assigned agents, team renewal dashboard, performance |
| **Franchisee** | `8` | `FRANCHISEE` | Franchise Scoped | Sub-agents, own booked policies, renewal reminders |
| **Agent / POSP** | `9` | `AGENT`, `POSP` | Principal Scoped | Strictly own booked policies and commission alerts |
| **Customer** | `10` | `CUSTOMER` | Principal Scoped | Own vehicle policies, OTP authentication |

---

## 3. Comprehensive Access Matrix by Feature & Endpoint

| Feature / Operation | Target HTTP Endpoint | Global Admin (Owner/Admin/IT Support) | Branch Manager | Clerk / Operator | Telecaller | Sales Executive | Franchisee | Agent / POSP | Customer / Public | Scoping & Isolation Rule |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **Vehicle RC Lookup** | `POST /api/v1/integrations/vehicle-rc/lookup` | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ | ❌ | Authenticated users only. Lookups are logged with `CreatedBy = user.username`. |
| **Request Mobile OTP** | `POST /api/v1/auth/otp/request` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | Public endpoint (rate-limited by IP and mobile number). |
| **Verify Mobile OTP** | `POST /api/v1/auth/otp/verify` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | Public endpoint (max 3 failed attempts within 5-min TTL window). |
| **Send Ad-hoc SMS** | `POST /api/v1/notifications/sms/send` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | Restricted to Admin/Branch Manager for administrative announcements. |
| **Trigger Push Notification** | `POST /api/v1/notifications/push/send` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | Server-side dispatch only. Client cannot supply raw OneSignal credentials. |
| **Send Renewal Excel Email** | `POST /api/v1/notifications/email/send-renewal-report` | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | Branch-isolated: Clerk can only export/email reports for agents in own branch. |
| **Send Daily InstaPay Email** | `POST /api/v1/notifications/email/send-payment-report` | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | Restricted to Global Admin (Owner/Admin) / Executive Management. |
| **Query Expiring Policies** | `GET /api/v1/renewals/due` | ✅ | ✅ | ✅ | ✅ | ✅ (Assigned) | ✅ (Network) | ✅ (Own) | ❌ | Scoped: Agent sees own policies; Executive sees team; Manager sees branch. |
| **List Telecaller Follow-ups**| `GET /api/v1/renewals/followups` | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | Telecaller sees assigned follow-up queue within their assigned branch. |
| **Record Follow-up Interaction**| `POST /api/v1/renewals/followups` | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | Telecaller updates interaction notes and sets next `followup_date`. |
| **Update Renewal Status** | `PUT /api/v1/renewals/{id}/status` | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | Status transitions (`FOLLOW_UP`, `RENEWED`, `LOST`, `VEHICLE_SOLD`). |
| **View Renewal Dashboard** | `GET /api/v1/renewals/dashboard` | ✅ | ✅ | ❌ | ❌ | ✅ (Assigned) | ❌ | ❌ | ❌ | Executive breakdown scoped to manager's branch or executive's team. |

---

## 4. Multi-Tenant Branch & Principal Isolation Rules

1. **Branch Scoping**:
   - Every non-admin query against `tbl_preyearrenewalstatus` or `tbl_transaction` joins through `tbl_user.BranchId` or `tbl_transaction.BranchId`.
   - A `BRANCH_MANAGER` or `CLERK` in Branch `5` (e.g., Pune) cannot view, modify, or export renewal data for Branch `2` (e.g., Nashik).
2. **Sales Executive Scoping**:
   - `SALES_EXECUTIVE` queries are filtered by `tbl_preyearrenewalstatus.ExecutiveId == current_user.emp_id`.
   - Executive dashboard drilldowns only aggregate agents assigned to that specific executive (`sp_SelectAgentbySE`).
3. **Agent / POSP Scoping**:
   - `AGENT` principals querying `/api/v1/renewals/due` receive only rows where `tbl_transaction.AgentId == current_user.agent_id`.
   - Push notifications and SMS alerts are strictly targeted to the specific agent owning the client policy.
4. **Audit Immutability**:
   - Whenever an RC lookup or renewal status update is executed, the current authenticated user's ID, role, and branch are stamped immutably into `CreatedBy` / `UpdatedBy` audit columns.
