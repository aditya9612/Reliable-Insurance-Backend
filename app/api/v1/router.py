from fastapi import APIRouter
from app.api.v1.endpoints import (
    health,
    auth,
    customers,
    quotations,
    policies,
    payments,
    commission_accounting,
    claims_endorsements,
    documents,
    masters,
    search,
    integrations,
    notifications,
    renewals,
    dashboards,
    reports,
    profiles,
    utilities,
    users,
    admin,
    phase18a,
)

api_router = APIRouter()

# Mount health & diagnostics endpoints directly at /api/v1
api_router.include_router(health.router)

# Mount authentication & RBAC endpoints at /api/v1/auth
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])

# Mount Customer & Vehicle endpoints at /api/v1/customers and /api/v1/vehicles
api_router.include_router(customers.router, prefix="/customers", tags=["customers"])
api_router.include_router(customers.vehicles_router, prefix="/vehicles", tags=["vehicles"])

# Mount Quotation & Rating Engine endpoints at /api/v1/quotations
api_router.include_router(phase18a.quotations_p18a_router, prefix="/quotations", tags=["quotations"])
api_router.include_router(quotations.router, prefix="/quotations", tags=["quotations"])

# Mount Policy Booking & Transaction Engine endpoints at /api/v1/policies
api_router.include_router(policies.router, prefix="/policies", tags=["policies"])

# Mount Phase 8 & 18A Payments, Cheques, Reconciliation & E-Wallet endpoints
api_router.include_router(phase18a.payments_p18a_router, prefix="/payments", tags=["payments"])
api_router.include_router(payments.payments_router, prefix="/payments", tags=["payments"])
api_router.include_router(payments.reconciliation_router, prefix="/reconciliation", tags=["reconciliation"])
api_router.include_router(payments.wallets_router, prefix="/wallets", tags=["wallets"])

# Mount Phase 9 & 18A Commission, Payout & Accounting Engine endpoints
api_router.include_router(
    phase18a.commissions_p18a_router,
    prefix="/commissions",
    tags=["commissions"],
)
api_router.include_router(
    commission_accounting.commissions_router,
    prefix="/commissions",
    tags=["commissions"],
)
api_router.include_router(
    phase18a.commission_payouts_p18a_router,
    prefix="/commission-payouts",
    tags=["commission-payouts"],
)
api_router.include_router(
    commission_accounting.commission_payouts_router,
    prefix="/commission-payouts",
    tags=["commission-payouts"],
)
api_router.include_router(
    phase18a.accounting_p18a_router,
    prefix="/accounting",
    tags=["accounting"],
)
api_router.include_router(
    commission_accounting.accounting_router,
    prefix="/accounting",
    tags=["accounting"],
)

# Mount Phase 10 Claims, Endorsements & Refunds Engine endpoints
api_router.include_router(
    claims_endorsements.claims_router,
    prefix="/claims",
    tags=["claims"],
)
api_router.include_router(
    claims_endorsements.endorsements_router,
    prefix="/endorsements",
    tags=["endorsements"],
)
api_router.include_router(
    claims_endorsements.refunds_router,
    prefix="/refunds",
    tags=["refunds"],
)

# Mount Phase 11 & 18A Document, File Handling, ZIP & Policy Parser Extraction endpoints
api_router.include_router(
    phase18a.documents_p18a_router,
    prefix="/documents",
    tags=["documents"],
)
api_router.include_router(
    documents.documents_router,
    prefix="/documents",
    tags=["documents"],
)
api_router.include_router(
    documents.entity_documents_router,
)

# Mount Phase 12 Master Data & Underwriting Lookups endpoints
api_router.include_router(
    masters.router,
    prefix="/masters",
    tags=["masters"],
)

# Mount Phase 12 Search & Autocomplete endpoints
api_router.include_router(
    search.router,
    prefix="/search",
    tags=["search"],
)

# Mount Phase 13 & 18A External Integrations, Vehicle RC & Geo Check-In endpoints
api_router.include_router(
    phase18a.integrations_p18a_router,
    prefix="/integrations",
    tags=["integrations"],
)
api_router.include_router(
    integrations.router,
    prefix="/integrations",
    tags=["integrations"],
)

# Mount Phase 13 Outbound Notifications & Messaging endpoints
api_router.include_router(
    notifications.router,
    prefix="/notifications",
    tags=["notifications"],
)

# Mount Phase 13 & 18A Policy Renewal Engine & Telecaller CRM endpoints
api_router.include_router(
    phase18a.renewals_p18a_router,
    prefix="/renewals",
    tags=["renewals"],
)
api_router.include_router(
    renewals.router,
    prefix="/renewals",
    tags=["renewals"],
)

# Mount Phase 14 Dashboards & KPI Performance Engine endpoints
api_router.include_router(
    dashboards.router,
    prefix="/dashboards",
    tags=["dashboards"],
)

# Mount Phase 14 & 18A MIS, POSP Invoices, Accounting, Operations & Sales Targets endpoints
api_router.include_router(
    phase18a.reports_p18a_router,
    prefix="/reports",
    tags=["reports"],
)
api_router.include_router(
    reports.router,
    prefix="/reports",
    tags=["reports"],
)

# Mount Phase 15B & 18A Staff Directory, POSP Agents, Sub-Agents & Franchise Profiles endpoints
api_router.include_router(
    profiles.employees_router,
    prefix="/employees",
    tags=["employees"],
)
api_router.include_router(
    phase18a.agents_p18a_router,
    prefix="/agents",
    tags=["agents"],
)
api_router.include_router(
    profiles.agents_router,
    prefix="/agents",
    tags=["agents"],
)
api_router.include_router(
    profiles.franchises_router,
    prefix="/franchises",
    tags=["franchises"],
)

# Mount Phase 15B & 18A Special IDV Overrides, Health Grid, Bulk Imports, Batch Tasks & Inspections endpoints
api_router.include_router(
    utilities.idv_router,
    prefix="/idv-requests",
    tags=["idv-requests"],
)
api_router.include_router(
    utilities.health_members_router,
    prefix="/health-members",
    tags=["health-members"],
)
api_router.include_router(
    utilities.imports_router,
    prefix="/imports",
    tags=["imports"],
)
api_router.include_router(
    phase18a.batch_tasks_p18a_router,
    prefix="/batch-tasks",
    tags=["batch-tasks"],
)
api_router.include_router(
    utilities.batch_tasks_router,
    prefix="/batch-tasks",
    tags=["batch-tasks"],
)
api_router.include_router(
    phase18a.inspections_p18a_router,
    prefix="/inspections",
    tags=["inspections"],
)

# Mount Phase 16B User Management & Account Lifecycle endpoints
api_router.include_router(
    users.router,
    prefix="/users",
    tags=["users"],
)

# Mount Phase 16B & 18A Admin Overview Counters, Dynamic Privileges & Support Portal endpoints
api_router.include_router(
    phase18a.admin_p18a_router,
    prefix="/admin",
    tags=["admin"],
)
api_router.include_router(
    admin.router,
    prefix="/admin",
    tags=["admin"],
)
