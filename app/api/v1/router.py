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
api_router.include_router(quotations.router, prefix="/quotations", tags=["quotations"])

# Mount Policy Booking & Transaction Engine endpoints at /api/v1/policies
api_router.include_router(policies.router, prefix="/policies", tags=["policies"])

# Mount Phase 8 Payments, Cheques, Reconciliation & E-Wallet endpoints
api_router.include_router(payments.payments_router, prefix="/payments", tags=["payments"])
api_router.include_router(payments.reconciliation_router, prefix="/reconciliation", tags=["reconciliation"])
api_router.include_router(payments.wallets_router, prefix="/wallets", tags=["wallets"])

# Mount Phase 9 Commission, Payout & Accounting Engine endpoints
api_router.include_router(
    commission_accounting.commissions_router,
    prefix="/commissions",
    tags=["commissions"],
)
api_router.include_router(
    commission_accounting.commission_payouts_router,
    prefix="/commission-payouts",
    tags=["commission-payouts"],
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

# Mount Phase 11 Document, File Handling, ZIP & Policy Parser Webhook endpoints
api_router.include_router(
    documents.documents_router,
    prefix="/documents",
    tags=["documents"],
)
api_router.include_router(
    documents.entity_documents_router,
)




