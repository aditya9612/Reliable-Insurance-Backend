# Phase 14 — Automated Reporting & Scheduled Jobs Forensic Audit

> **Audit Status**: COMPLETE (FORENSIC EXTRACTION)  
> **Phase**: Phase 14 (Reporting, Dashboard, MIS, POSP Invoicing & Statutory Statements) — Stage A  
> **Repository**: `Reliable-Insurance-Backend`  
> **Legacy Source**: `c:\Users\Admin\Downloads\InsurancefinalNew_2026_09_23\InsurancefinalNew`  
> **Mode**: STRICTLY READ-ONLY FORENSIC AUDIT (No implementation)

---

## 1. Executive Summary

In the legacy architecture, administrative summaries and policy expiry alerts were dispatched via scheduled email utilities. However, rather than running inside an asynchronous job queue, these utilities were executed synchronously inside ASP.NET WebForms `Page_Load` event handlers (`SendMailToAutority.aspx.cs`, `SendMailToAutorityDaily.aspx.cs`, `adm_DashboardTodayPolicyExpire.aspx.cs`).

This audit analyzes the legacy dispatch mechanisms, recipient distribution lists, HTML email templates, and defines the modernized Celery Beat scheduled task architecture.

---

## 2. Legacy Dispatch Architecture & Anti-Patterns

### 2.1 The `Page_Load` Trigger Anti-Pattern (`GAP-UNK-13-004`)
In `SendMailToAutority.aspx.cs:L24-L65`:

```csharp
protected void Page_Load(object sender, EventArgs e)
{
    if (!IsPostBack)
    {
        // EXECUTES ON EVERY HTTP GET REQUEST
        SendDailyReportEmail();
    }
}
```

#### Identified Architectural Flaws:
1. **Unauthenticated HTTP Exposure**: Any external crawler, bot, or unauthenticated browser visiting `SendMailToAutority.aspx` triggered an expensive database aggregation query and dispatched emails to senior executives.
2. **Synchronous Thread Blocking**: The ASP.NET request thread was blocked while querying the database, building HTML strings, and connecting to the external SMTP mail server.
3. **No Failure Recovery**: If the SMTP server timed out or bounced, the exception was swallowed in `catch (Exception ex) { }`, with zero retry mechanism or failure alerts.

---

## 3. Dispatched Report Profiles

### 3.1 Daily Executive Business Digest (`SendMailToAutorityDaily.aspx.cs`)
- **Trigger Schedule**: Daily at close of business (21:00 IST / 15:30 UTC).
- **Recipients**: Managing Directors, General Managers, Account Heads.
- **Payload & Metrics**:
  - Total Policies Booked Today (Categorized by 2-Wheeler, Private Car, Commercial Vehicle).
  - Total Net Premium Today (INR).
  - Total Gross Premium Collected Today (INR).
  - Collection Split: Cash vs Cheque vs Online.
  - Sourcing Split: Agent Business vs Direct vs Franchise.
  - Month-to-Date (MTD) Cumulative Premium vs MTD Monthly Target.
- **Email Design**: Clean HTML table with corporate branding header, Medium Turquoise `#48D1CC` headers, and executive summary totals.

### 3.2 Daily Policy Expiry & Renewal Alerts (`adm_DashboardTodayPolicyExpire.aspx.cs`)
- **Trigger Schedule**: Daily morning (08:00 IST / 02:30 UTC).
- **Recipients**: Assigned Telecallers, Branch Managers, Agents.
- **Payload & Metrics**:
  - List of policies expiring in 30 days, 15 days, 7 days, and today.
  - Customer contact details, vehicle registration number, previous insurer, renewal estimated premium.

---

## 4. Proposed Modern Implementation: Headless Scheduling (Celery Beat + Redis)

To remediate legacy `Page_Load` trigger vulnerabilities (`GAP-UNK-13-004`), Phase 14B proposes transitioning all scheduled report generation to headless Celery Beat background tasks. This is classified as a **Proposed Modern Implementation** to replace legacy synchronous HTTP GET triggers:

```
┌─────────────────────┐
│     Celery Beat     │ ── Cron Schedules (IST)
└──────────┬──────────┘
           │ Dispatches Task
           ▼
┌─────────────────────┐
│     Redis Queue     │ ── Message Broker
└──────────┬──────────┘
           │ Consumes Task
           ▼
┌─────────────────────────────────────────────────────────────┐
│                     Celery Worker                           │
│  1. Run Async Aggregation Queries (SQLAlchemy)              │
│  2. Render Jinja2 HTML Email Template                       │
│  3. Attach Generated Excel/PDF Report (if requested)        │
│  4. Dispatch via Email Service (aiosmtplib / AWS SES)       │
│  5. Persist Task Audit Log (tbl_scheduled_job_log)          │
└─────────────────────────────────────────────────────────────┘
```

### 4.1 Celery Beat Schedule Configuration

```python
CELERY_BEAT_SCHEDULE = {
    "dispatch-daily-mis-summary": {
        "task": "app.tasks.reporting.send_daily_mis_summary_email",
        "schedule": crontab(hour=21, minute=0),  # 21:00 IST daily
        "options": {"queue": "reports"},
    },
    "dispatch-daily-policy-expiry-alerts": {
        "task": "app.tasks.reporting.send_daily_policy_expiry_alert",
        "schedule": crontab(hour=8, minute=0),   # 08:00 IST daily
        "options": {"queue": "reports"},
    },
    "dispatch-monthly-commission-digest": {
        "task": "app.tasks.reporting.send_monthly_commission_digest",
        "schedule": crontab(day_of_month=1, hour=6, minute=0), # 1st of every month
        "options": {"queue": "reports"},
    },
}
```

### 4.2 Resilience & Telemetry
1. **Exponential Backoff Retries**: Tasks automatically retry up to 3 times with exponential backoff on transient SMTP network failures (`autoretry_for=(SMTPException,), retry_backoff=True`).
2. **Execution Audit Logging**: Every task execution writes a record to `tbl_scheduled_job_log` with status (`SUCCESS`, `FAILURE`, `RETRY`), recipient count, execution duration, and error trace.
3. **Zero Browser Dependency**: Completely headless; eliminates `Page_Load` vulnerabilities and prevents unintended execution.
