"""
Verified Role-Based Access Control (RBAC) Catalog & Principal Context Resolution.

Source of Truth:
- Phase 5F Audit: docs/migration/phase_5f_role_api_table_access_matrix.md
- Phase 5F Role Summary: docs/migration/phase_5f_role_summary.md
- Phase 5F Gap Register: docs/migration/phase_5f_authorization_gap_register.md

Enforces:
- GAP-5F-01: Explicit role gates for Customer & Vehicle write/read operations.
- GAP-5F-02: Elimination of phantom 'SUPERADMIN' role and 'BranchId in (0, None)' admin checks.
- GAP-5F-03: Server-side principal context resolution (agent_id, emp_id / employee_id, franchise_id).
"""
from dataclasses import dataclass
from typing import Dict, FrozenSet, Optional
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole


@dataclass(frozen=True)
class RoleDefinition:
    """Metadata for a verified legacy role in tbl_userrole."""
    role_id: int
    role_name: str
    role_code: Optional[str]
    is_deleted_in_legacy: bool = False


# Complete verified 56-role catalog from tbl_userrole (Phase 5F)
VERIFIED_ROLE_CATALOG: Dict[int, RoleDefinition] = {
    1: RoleDefinition(1, "OWNER", "OWN"),
    2: RoleDefinition(2, "ADMIN", "ADM"),
    3: RoleDefinition(3, "SUPERVISOR", "SUP"),
    4: RoleDefinition(4, "AGENT", "AGT"),
    5: RoleDefinition(5, "RELATIONSHIP MANAGER", "RSM"),
    6: RoleDefinition(6, "OPERATOR", "OPT"),
    7: RoleDefinition(7, "CASHIER", "CASH"),
    8: RoleDefinition(8, "MANAGER", "MGR"),
    9: RoleDefinition(9, "FRANCHISE", "FRN"),
    10: RoleDefinition(10, "SALES", "SAL"),
    11: RoleDefinition(11, "ACCOUNT", "ACC"),
    12: RoleDefinition(12, "ENDORSEMENT", "END"),
    13: RoleDefinition(13, "CLAIM", "CLM"),
    14: RoleDefinition(14, "QUOT CO-ORDINATOR", "QUT"),
    15: RoleDefinition(15, "INSP CO-ORDINATION", "INS"),
    16: RoleDefinition(16, "FRANCHISE AGENT", "FAGT"),
    17: RoleDefinition(17, "POLICY BAZAR", "PBZ", is_deleted_in_legacy=True),
    18: RoleDefinition(18, "POLICY BAZAR AGENT", "PBAG", is_deleted_in_legacy=True),
    19: RoleDefinition(19, "OPERATOR HEAD", "OH"),
    20: RoleDefinition(20, "FRANCHISE SALES EXECUTIVE", "FSE"),
    21: RoleDefinition(21, "HOD", "HOD"),
    22: RoleDefinition(22, "BACK OFFICE", "BO"),
    23: RoleDefinition(23, "CLAIM", "CLA"),
    24: RoleDefinition(24, "LOCATION HEAD", "LCHD"),
    26: RoleDefinition(26, "HR", "HR"),
    27: RoleDefinition(27, "ACCOUNT HEAD", "ACH"),
    28: RoleDefinition(28, "IT SUPPORT", "ITS"),
    29: RoleDefinition(29, "SHREYANSH OWNER", "SHRO"),
    30: RoleDefinition(30, "CallIng Employee", "CE"),
    31: RoleDefinition(31, "Calling Indivisional", "CI"),
    32: RoleDefinition(32, "Insurance Exective", "IE"),
    33: RoleDefinition(33, "ALL USER", "AUSER"),
    34: RoleDefinition(34, "pOLICY VIEW", "PV"),
    35: RoleDefinition(35, "Freelancer", "FRL"),
    36: RoleDefinition(36, "EMI", "EMI"),
    37: RoleDefinition(37, "BUSINESS HEAD", "BSH"),
    38: RoleDefinition(38, "PRESIDENT", "PRE"),
    39: RoleDefinition(39, "VICE PRESIDENT", "VPR"),
    40: RoleDefinition(40, "STATE HEAD", "STH"),
    41: RoleDefinition(41, "TERRITORY HEAD", "TRH"),
    42: RoleDefinition(42, "AREA HEAD", "ARH"),
    43: RoleDefinition(43, "ZONAL HEAD", "ZNH"),
    44: RoleDefinition(44, "REGIONAL HEAD", "RGH"),
    45: RoleDefinition(45, "DEPUTY REGIONAL HEAD", "DRH"),
    46: RoleDefinition(46, "PROCESS  HEAD", "PRH"),
    47: RoleDefinition(47, "GENERAL MANAGER", "GM"),
    48: RoleDefinition(48, "TEAM LEADER SALES", "TLS"),
    49: RoleDefinition(49, "CIRCLE HEAD", "CRH"),
    50: RoleDefinition(50, "DIVISION HEAD", "DVH"),
    51: RoleDefinition(51, "PROCESS MANAGER", "PRM"),
    52: RoleDefinition(52, "FRANCHISE TYPE 2", "FRT2"),
    53: RoleDefinition(53, "FRANCHISE TYPE 3", "FRT3"),
    54: RoleDefinition(54, "FRANCHISE OPERATOR", "FOPR"),
    55: RoleDefinition(55, "OTHER", "OTH"),
    56: RoleDefinition(56, "Broker partner", "Brp"),
    57: RoleDefinition(57, "CLUSTER HEAD", "CLH"),
}


# ---------------------------------------------------------------------------
# 1. Global / Cross-Branch Administrative & Read Role Sets
# ---------------------------------------------------------------------------

# Verified global administrative roles (cross-branch write & override authority)
# NOTE: Phantom 'SUPERADMIN' role and 'BranchId in (0, None)' checks are eliminated (GAP-5F-02).
GLOBAL_ADMIN_ROLES: FrozenSet[str] = frozenset({
    "OWNER",
    "ADMIN",
    "IT SUPPORT",
})

# Verified global read roles (cross-branch Customer/Vehicle read & search authority)
GLOBAL_READ_ROLES: FrozenSet[str] = frozenset({
    "OWNER",
    "ADMIN",
    "IT SUPPORT",
    "ACCOUNT",
    "ACCOUNT HEAD",
})


# ---------------------------------------------------------------------------
# 2. Customer & Vehicle Write / Read Role Sets (GAP-5F-01, GAP-5F-09)
# ---------------------------------------------------------------------------

# Roles permitted to create/update Customer & Vehicle records in back-office workflows
CUSTOMER_VEHICLE_WRITE_ROLES: FrozenSet[str] = frozenset({
    "OWNER",
    "ADMIN",
    "IT SUPPORT",
    "OPERATOR",
    "OPERATOR HEAD",
    "ALL USER",
    "Freelancer",
    "FRANCHISE",
    "FRANCHISE TYPE 2",
    "FRANCHISE TYPE 3",
    "FRANCHISE OPERATOR",
    "OTHER",
    "ENDORSEMENT",
})

CUSTOMER_VEHICLE_CREATE_ROLES: FrozenSet[str] = CUSTOMER_VEHICLE_WRITE_ROLES
CUSTOMER_VEHICLE_UPDATE_ROLES: FrozenSet[str] = CUSTOMER_VEHICLE_WRITE_ROLES

# All active verified roles permitted to read/search Customer & Vehicle records
# (subject to strict branch scoping for non-global roles)
CUSTOMER_VEHICLE_READ_ROLES: FrozenSet[str] = frozenset(
    defn.role_name
    for defn in VERIFIED_ROLE_CATALOG.values()
    if not defn.is_deleted_in_legacy
)


# ---------------------------------------------------------------------------
# 2B. Quotation & Rating Role Sets (Phase 6)
# ---------------------------------------------------------------------------

QUOTATION_COORDINATOR_ROLES: FrozenSet[str] = frozenset({
    "OWNER",
    "ADMIN",
    "IT SUPPORT",
    "QUOT CO-ORDINATOR",
    "OPERATOR",
    "OPERATOR HEAD",
    "SUPERVISOR",
    "MANAGER",
})

QUOTATION_WRITE_ROLES: FrozenSet[str] = frozenset({
    "OWNER",
    "ADMIN",
    "IT SUPPORT",
    "QUOT CO-ORDINATOR",
    "OPERATOR",
    "OPERATOR HEAD",
    "SUPERVISOR",
    "MANAGER",
    "AGENT",
    "FRANCHISE AGENT",
    "RELATIONSHIP MANAGER",
    "LOCATION HEAD",
    "FRANCHISE",
    "FRANCHISE TYPE 2",
    "FRANCHISE TYPE 3",
    "FRANCHISE OPERATOR",
    "FRANCHISE SALES EXECUTIVE",
    "Insurance Exective",
    "SALES",
    "CallIng Employee",
    "Calling Indivisional",
    "ALL USER",
    "Freelancer",
    "Broker partner",
})

QUOTATION_CALCULATE_ROLES: FrozenSet[str] = QUOTATION_WRITE_ROLES | frozenset({
    "BACK OFFICE",
    "ENDORSEMENT",
    "INSP CO-ORDINATION",
})

# Read access allowed for active roles subject to strict principal/branch scoping
QUOTATION_READ_ROLES: FrozenSet[str] = CUSTOMER_VEHICLE_READ_ROLES

RATING_ADMIN_ROLES: FrozenSet[str] = frozenset({
    "OWNER",
    "ADMIN",
    "IT SUPPORT",
    "QUOT CO-ORDINATOR",
    "OPERATOR HEAD",
})


# ---------------------------------------------------------------------------
# 2C. Policy Booking, Proposal Intake, Payment & Approval Role Sets (Phase 7)
# ---------------------------------------------------------------------------

# Roles permitted to book/update policies directly in tbl_transaction
POLICY_BOOKING_WRITE_ROLES: FrozenSet[str] = CUSTOMER_VEHICLE_WRITE_ROLES

# Roles permitted to preview policy financials or submit staged proposals (tbl_transactionappnew)
POLICY_PROPOSAL_WRITE_ROLES: FrozenSet[str] = (
    POLICY_BOOKING_WRITE_ROLES | QUOTATION_WRITE_ROLES
)

# Roles permitted to record additional payment instruments against a policy
POLICY_PAYMENT_WRITE_ROLES: FrozenSet[str] = POLICY_BOOKING_WRITE_ROLES | frozenset({
    "CASHIER",
    "ACCOUNT",
    "ACCOUNT HEAD",
})

# Approval gate role sets for staged proposals / payments
POLICY_CASHIER_APPROVAL_ROLES: FrozenSet[str] = frozenset({
    "OWNER",
    "ADMIN",
    "IT SUPPORT",
    "CASHIER",
    "ACCOUNT",
    "ACCOUNT HEAD",
    "FRANCHISE",
})

POLICY_ACCOUNTANT_APPROVAL_ROLES: FrozenSet[str] = frozenset({
    "OWNER",
    "ADMIN",
    "IT SUPPORT",
    "ACCOUNT",
    "ACCOUNT HEAD",
})

POLICY_OWNER_APPROVAL_ROLES: FrozenSet[str] = frozenset({
    "OWNER",
    "ADMIN",
    "SHREYANSH OWNER",
})

POLICY_APPROVAL_ROLES: FrozenSet[str] = (
    POLICY_CASHIER_APPROVAL_ROLES
    | POLICY_ACCOUNTANT_APPROVAL_ROLES
    | POLICY_OWNER_APPROVAL_ROLES
)

# Roles permitted to cancel / soft-delete a booked policy transaction and reverse ledger rows
POLICY_DELETE_ROLES: FrozenSet[str] = frozenset({
    "OWNER",
    "ADMIN",
    "IT SUPPORT",
    "ACCOUNT",
    "ACCOUNT HEAD",
})

# All active verified roles permitted to read/list policies within their authorized scope
POLICY_BOOKING_READ_ROLES: FrozenSet[str] = CUSTOMER_VEHICLE_READ_ROLES


# ---------------------------------------------------------------------------
# 2D. Payment, Cheque, Reconciliation & E-Wallet Role Sets (Phase 8)
# ---------------------------------------------------------------------------

# Roles permitted to deposit/clear cheques & DDs
PAYMENT_CLEARANCE_ROLES: FrozenSet[str] = (
    POLICY_CASHIER_APPROVAL_ROLES
    | POLICY_ACCOUNTANT_APPROVAL_ROLES
    | frozenset({"OPERATOR", "OPERATOR HEAD"})
)

# Roles permitted to mark cheques bounced or reverse payment instruments
PAYMENT_BOUNCE_REVERSAL_ROLES: FrozenSet[str] = frozenset({
    "OWNER",
    "ADMIN",
    "IT SUPPORT",
    "CASHIER",
    "ACCOUNT",
    "ACCOUNT HEAD",
    "OPERATOR HEAD",
    "SHREYANSH OWNER",
})

# Roles permitted to execute insurer payment & brokerage reconciliation
RECONCILIATION_WRITE_ROLES: FrozenSet[str] = frozenset({
    "OWNER",
    "ADMIN",
    "IT SUPPORT",
    "ACCOUNT",
    "ACCOUNT HEAD",
    "OPERATOR",
    "OPERATOR HEAD",
})

RECONCILIATION_READ_ROLES: FrozenSet[str] = RECONCILIATION_WRITE_ROLES | frozenset({
    "SUPERVISOR",
    "MANAGER",
    "SHREYANSH OWNER",
    "ALL USER",
})

# Roles permitted to top-up or manually credit/debit partner E-Wallets
WALLET_ADMIN_WRITE_ROLES: FrozenSet[str] = frozenset({
    "OWNER",
    "ADMIN",
    "IT SUPPORT",
    "CASHIER",
    "ACCOUNT",
    "ACCOUNT HEAD",
})

PAYMENT_READ_ROLES: FrozenSet[str] = POLICY_BOOKING_READ_ROLES


# ---------------------------------------------------------------------------
# 3. Principal Context Role Categorization (GAP-5F-03)
# ---------------------------------------------------------------------------

AGENT_PRINCIPAL_ROLES: FrozenSet[str] = frozenset({
    "AGENT",
    "FRANCHISE AGENT",
    "Broker partner",
})

EMPLOYEE_PRINCIPAL_ROLES: FrozenSet[str] = frozenset({
    "RELATIONSHIP MANAGER",
    "LOCATION HEAD",
    "Insurance Exective",
    "SALES",
    "FRANCHISE SALES EXECUTIVE",
    "CallIng Employee",
    "Calling Indivisional",
    "HR",
    "HOD",
    "BUSINESS HEAD",
    "PRESIDENT",
    "VICE PRESIDENT",
    "STATE HEAD",
    "TERRITORY HEAD",
    "AREA HEAD",
    "ZONAL HEAD",
    "REGIONAL HEAD",
    "DEPUTY REGIONAL HEAD",
    "PROCESS  HEAD",
    "GENERAL MANAGER",
    "TEAM LEADER SALES",
    "CIRCLE HEAD",
    "DIVISION HEAD",
    "PROCESS MANAGER",
    "CLUSTER HEAD",
})

FRANCHISE_PRINCIPAL_ROLES: FrozenSet[str] = frozenset({
    "FRANCHISE",
    "FRANCHISE TYPE 2",
    "FRANCHISE TYPE 3",
    "FRANCHISE OPERATOR",
})

# Roles permitted to read/lock/release own or scoped E-Wallets
WALLET_PARTNER_ROLES: FrozenSet[str] = (
    AGENT_PRINCIPAL_ROLES
    | FRANCHISE_PRINCIPAL_ROLES
    | EMPLOYEE_PRINCIPAL_ROLES
    | POLICY_BOOKING_WRITE_ROLES
    | WALLET_ADMIN_WRITE_ROLES
)


# ---------------------------------------------------------------------------
# 4. Commission, Payout, Accounting, Voucher & Trial Balance Role Sets (Phase 9)
# ---------------------------------------------------------------------------

# Roles permitted to run commission & TDS preview or policy commission evaluation
COMMISSION_CALCULATE_ROLES: FrozenSet[str] = (
    POLICY_PROPOSAL_WRITE_ROLES
    | RECONCILIATION_WRITE_ROLES
    | frozenset({"SHREYANSH OWNER"})
)

# Roles permitted to approve commission payables for disbursement
COMMISSION_APPROVAL_ROLES: FrozenSet[str] = frozenset({
    "OWNER",
    "ADMIN",
    "IT SUPPORT",
    "ACCOUNT",
    "ACCOUNT HEAD",
    "SHREYANSH OWNER",
})

# Roles permitted to execute or reverse commission payouts (Agent or Franchise)
COMMISSION_PAYOUT_WRITE_ROLES: FrozenSet[str] = frozenset({
    "OWNER",
    "ADMIN",
    "IT SUPPORT",
    "CASHIER",
    "ACCOUNT",
    "ACCOUNT HEAD",
    "SHREYANSH OWNER",
})

# Roles permitted to read commission records and payables within their authorized scope
COMMISSION_READ_ROLES: FrozenSet[str] = POLICY_BOOKING_READ_ROLES

# Roles permitted to create/reverse accounting vouchers or create master ledgers
ACCOUNTING_VOUCHER_WRITE_ROLES: FrozenSet[str] = frozenset({
    "OWNER",
    "ADMIN",
    "IT SUPPORT",
    "CASHIER",
    "ACCOUNT",
    "ACCOUNT HEAD",
    "SHREYANSH OWNER",
})

# Roles permitted to read accounting ledgers and vouchers within their authorized scope
ACCOUNTING_READ_ROLES: FrozenSet[str] = (
    ACCOUNTING_VOUCHER_WRITE_ROLES
    | frozenset({
        "OPERATOR",
        "OPERATOR HEAD",
        "SUPERVISOR",
        "MANAGER",
        "ALL USER",
    })
    | AGENT_PRINCIPAL_ROLES
    | FRANCHISE_PRINCIPAL_ROLES
    | EMPLOYEE_PRINCIPAL_ROLES
)

# Roles permitted to generate/view branch or global Trial Balance reports
TRIAL_BALANCE_READ_ROLES: FrozenSet[str] = frozenset({
    "OWNER",
    "ADMIN",
    "IT SUPPORT",
    "CASHIER",
    "ACCOUNT",
    "ACCOUNT HEAD",
    "OPERATOR HEAD",
    "SUPERVISOR",
    "MANAGER",
    "SHREYANSH OWNER",
    "ALL USER",
})


# ---------------------------------------------------------------------------
# 5. Claims, Endorsements & Refund Role Sets (Phase 10)
# ---------------------------------------------------------------------------

_SALES_AND_PARTNER_CLAIM_ROLES: FrozenSet[str] = (
    AGENT_PRINCIPAL_ROLES
    | FRANCHISE_PRINCIPAL_ROLES
    | frozenset({
        "RELATIONSHIP MANAGER",
        "LOCATION HEAD",
        "Insurance Exective",
        "SALES",
        "FRANCHISE SALES EXECUTIVE",
        "CallIng Employee",
        "Calling Indivisional",
        "TEAM LEADER SALES",
    })
)

# Roles permitted to intimate claims and attach claim documents
CLAIM_CREATE_ROLES: FrozenSet[str] = (
    GLOBAL_ADMIN_ROLES
    | frozenset({
        "SHREYANSH OWNER",
        "CLAIM",
        "OPERATOR",
        "OPERATOR HEAD",
        "BACK OFFICE",
        "SUPERVISOR",
        "MANAGER",
        "ALL USER",
        "INSP CO-ORDINATION",
    })
    | _SALES_AND_PARTNER_CLAIM_ROLES
)

# Roles permitted to register, assign surveyor, assess, or cancel unapproved claims
CLAIM_UPDATE_ROLES: FrozenSet[str] = frozenset({
    "OWNER",
    "ADMIN",
    "IT SUPPORT",
    "SHREYANSH OWNER",
    "CLAIM",
    "OPERATOR",
    "OPERATOR HEAD",
    "BACK OFFICE",
    "SUPERVISOR",
    "MANAGER",
    "ALL USER",
    "INSP CO-ORDINATION",
})

# Roles permitted to approve, settle, close, reject, reopen, or reverse claim settlements
CLAIM_APPROVE_SETTLE_ROLES: FrozenSet[str] = frozenset({
    "OWNER",
    "ADMIN",
    "IT SUPPORT",
    "SHREYANSH OWNER",
    "CLAIM",
    "OPERATOR HEAD",
    "SUPERVISOR",
    "MANAGER",
    "ACCOUNT",
    "ACCOUNT HEAD",
    "CASHIER",
})

# Roles permitted to read claims (subject to branch/principal scoping; HR excluded)
CLAIM_READ_ROLES: FrozenSet[str] = (
    CLAIM_CREATE_ROLES
    | CLAIM_UPDATE_ROLES
    | CLAIM_APPROVE_SETTLE_ROLES
    | frozenset({"pOLICY VIEW"})
)

# Roles permitted to create, preview, submit, or cancel draft/submitted endorsements
ENDORSEMENT_CREATE_ROLES: FrozenSet[str] = (
    GLOBAL_ADMIN_ROLES
    | frozenset({
        "SHREYANSH OWNER",
        "ENDORSEMENT",
        "OPERATOR",
        "OPERATOR HEAD",
        "BACK OFFICE",
        "SUPERVISOR",
        "MANAGER",
        "ALL USER",
        "QUOT CO-ORDINATOR",
    })
    | _SALES_AND_PARTNER_CLAIM_ROLES
)

# Roles permitted to approve, apply, reject, or reverse endorsements
ENDORSEMENT_APPROVE_APPLY_ROLES: FrozenSet[str] = frozenset({
    "OWNER",
    "ADMIN",
    "IT SUPPORT",
    "SHREYANSH OWNER",
    "ENDORSEMENT",
    "OPERATOR",
    "OPERATOR HEAD",
    "BACK OFFICE",
    "SUPERVISOR",
    "MANAGER",
    "ACCOUNT",
    "ACCOUNT HEAD",
})

# Roles permitted to read endorsements within their authorized scope
ENDORSEMENT_READ_ROLES: FrozenSet[str] = (
    ENDORSEMENT_CREATE_ROLES
    | ENDORSEMENT_APPROVE_APPLY_ROLES
    | frozenset({"CASHIER", "pOLICY VIEW"})
)

# Roles permitted to approve, disburse, or reverse endorsement refunds
REFUND_APPROVE_WRITE_ROLES: FrozenSet[str] = frozenset({
    "OWNER",
    "ADMIN",
    "IT SUPPORT",
    "SHREYANSH OWNER",
    "ACCOUNT",
    "ACCOUNT HEAD",
    "CASHIER",
    "OPERATOR HEAD",
    "MANAGER",
})


# ---------------------------------------------------------------------------
# 6. Document, File Handling, Download, ZIP & Webhook Role Sets (Phase 11)
# ---------------------------------------------------------------------------

# Roles permitted to upload or generate documents within their authorized entity scope
# Read-only roles such as 'pOLICY VIEW' are explicitly excluded from upload/mutation.
DOCUMENT_UPLOAD_ROLES: FrozenSet[str] = (
    POLICY_PROPOSAL_WRITE_ROLES
    | CLAIM_CREATE_ROLES
    | ENDORSEMENT_CREATE_ROLES
    | POLICY_PAYMENT_WRITE_ROLES
    | frozenset({"HR"})
) - frozenset({"pOLICY VIEW"})

# Roles permitted to view metadata, download single files, or download ZIP archives
# (subject to strict entity-level branch and principal ownership checks)
DOCUMENT_READ_ROLES: FrozenSet[str] = CUSTOMER_VEHICLE_READ_ROLES

# Roles permitted to soft-delete or replace documents within their authorized entity scope
DOCUMENT_DELETE_REPLACE_ROLES: FrozenSet[str] = (
    GLOBAL_ADMIN_ROLES
    | CLAIM_UPDATE_ROLES
    | ENDORSEMENT_APPROVE_APPLY_ROLES
    | POLICY_BOOKING_WRITE_ROLES
    | QUOTATION_WRITE_ROLES
    | POLICY_PAYMENT_WRITE_ROLES
) - frozenset({"pOLICY VIEW"})





def _normalize(role_name: Optional[str]) -> str:
    """Normalizes role name for case-insensitive catalog matching while preserving internal spaces."""
    if not role_name:
        return ""
    return role_name.strip().upper()


_GLOBAL_ADMIN_UPPER: FrozenSet[str] = frozenset(_normalize(r) for r in GLOBAL_ADMIN_ROLES)
_GLOBAL_READ_UPPER: FrozenSet[str] = frozenset(_normalize(r) for r in GLOBAL_READ_ROLES)
_QUOTATION_COORD_UPPER: FrozenSet[str] = frozenset(_normalize(r) for r in QUOTATION_COORDINATOR_ROLES)
_AGENT_ROLES_UPPER: FrozenSet[str] = frozenset(_normalize(r) for r in AGENT_PRINCIPAL_ROLES)
_EMPLOYEE_ROLES_UPPER: FrozenSet[str] = frozenset(_normalize(r) for r in EMPLOYEE_PRINCIPAL_ROLES)
_FRANCHISE_ROLES_UPPER: FrozenSet[str] = frozenset(_normalize(r) for r in FRANCHISE_PRINCIPAL_ROLES)


VERIFIED_ROLE_NAMES: FrozenSet[str] = frozenset(
    defn.role_name for defn in VERIFIED_ROLE_CATALOG.values()
)
_VERIFIED_ROLES_UPPER: FrozenSet[str] = frozenset(
    _normalize(defn.role_name) for defn in VERIFIED_ROLE_CATALOG.values()
)


def is_verified_role(role_name: Optional[str]) -> bool:
    """Returns True if role_name is in the verified 56-role catalog from tbl_userrole."""
    norm = _normalize(role_name)
    return bool(norm and norm in _VERIFIED_ROLES_UPPER)


def is_global_admin_role(role_name: Optional[str]) -> bool:
    """
    Returns True ONLY if role_name is a verified global admin role (OWNER, ADMIN, IT SUPPORT).
    Does NOT accept phantom 'SUPERADMIN' and does NOT use BranchId.
    """
    norm = _normalize(role_name)
    return bool(norm and norm in _GLOBAL_ADMIN_UPPER)


def is_global_read_role(role_name: Optional[str]) -> bool:
    """
    Returns True if role_name is authorized for cross-branch Customer/Vehicle read access
    (OWNER, ADMIN, IT SUPPORT, ACCOUNT, ACCOUNT HEAD).
    """
    norm = _normalize(role_name)
    return bool(norm and norm in _GLOBAL_READ_UPPER)


def is_quotation_coordinator_role(role_name: Optional[str]) -> bool:
    """
    Returns True if role_name is authorized for global Quotation Coordinator / Operator queue
    operations (OWNER, ADMIN, IT SUPPORT, QUOT CO-ORDINATOR, OPERATOR, OPERATOR HEAD, SUPERVISOR, MANAGER).
    """
    norm = _normalize(role_name)
    return bool(norm and norm in _QUOTATION_COORD_UPPER)




@dataclass
class PrincipalContext:
    """
    Server-resolved authenticated principal context (GAP-5F-03).
    Never populated from client-supplied headers, query parameters, or request body.
    """
    user_id: int
    username: Optional[str]
    role_id: Optional[int]
    role_name: Optional[str]
    branch_id: Optional[int]
    agent_id: Optional[int] = None
    emp_id: Optional[int] = None
    employee_id: Optional[int] = None
    franchise_id: Optional[int] = None


def _parse_positive_int(val: object) -> Optional[int]:
    """Safely converts an int or numeric string (such as tbl_user.partner_user_id) to a positive int."""
    if val is None:
        return None
    try:
        parsed = int(str(val).strip())
        return parsed if parsed > 0 else None
    except (ValueError, TypeError):
        return None


async def resolve_principal_context(
    session: AsyncSession,
    user: User,
    role: Optional[UserRole],
) -> PrincipalContext:
    """
    Resolves the authenticated user's principal context strictly from server-side
    database relationships.

    Resolution Rules:
    1. Never trusts client-supplied AgentId, EmpId, FranchiseId, BranchId, or UserId.
    2. For Agent roles (AGENT, FRANCHISE AGENT, Broker partner):
       - Resolves agent_id from user.partner_user_id or server-side transaction/agent tables.
    3. For Employee / Sales Executive / Hierarchy roles (RELATIONSHIP MANAGER, LOCATION HEAD, etc.):
       - Resolves emp_id / employee_id from user.partner_user_id or server-side tables.
    4. For Franchise roles (FRANCHISE, FRANCHISE TYPE 2, FRANCHISE TYPE 3, FRANCHISE OPERATOR):
       - Resolves franchise_id from user.partner_user_id or server-side tables.
    5. For roles that do not map to Agent/Employee/Franchise, those identifiers remain None.
    """
    role_name = role.UserRole.strip() if (role and role.UserRole) else None
    norm_role = _normalize(role_name)
    partner_id = _parse_positive_int(getattr(user, "partner_user_id", None))

    agent_id: Optional[int] = None
    emp_id: Optional[int] = None
    franchise_id: Optional[int] = None

    if norm_role in _AGENT_ROLES_UPPER:
        if partner_id is not None:
            agent_id = partner_id
        elif session is not None:
            # Fallback lookup from existing local tables if mapped
            res = await session.execute(
                text(
                    "SELECT AgentId FROM tbl_cutnpaycommpayable "
                    "WHERE AgentId = :uid LIMIT 1"
                ),
                {"uid": user.UserId},
            )
            row = res.first()
            if row and row[0]:
                agent_id = _parse_positive_int(row[0])

    elif norm_role in _EMPLOYEE_ROLES_UPPER:
        if partner_id is not None:
            emp_id = partner_id
        elif session is not None:
            res = await session.execute(
                text(
                    "SELECT SalesExecutiveId, FranchaiseId FROM tbl_transactionappnew "
                    "WHERE UserId = :uid AND SalesExecutiveId IS NOT NULL AND SalesExecutiveId > 0 "
                    "ORDER BY TransId DESC LIMIT 1"
                ),
                {"uid": user.UserId},
            )
            row = res.first()
            if row and row[0]:
                emp_id = _parse_positive_int(row[0])
                if norm_role == "FRANCHISE SALES EXECUTIVE" and row[1]:
                    franchise_id = _parse_positive_int(row[1])

    elif norm_role in _FRANCHISE_ROLES_UPPER:
        if partner_id is not None:
            franchise_id = partner_id
        elif session is not None:
            res = await session.execute(
                text(
                    "SELECT FranchaiseId FROM tbl_transactionappnew "
                    "WHERE UserId = :uid AND FranchaiseId IS NOT NULL AND FranchaiseId > 0 "
                    "ORDER BY TransId DESC LIMIT 1"
                ),
                {"uid": user.UserId},
            )
            row = res.first()
            if row and row[0]:
                franchise_id = _parse_positive_int(row[0])

    context = PrincipalContext(
        user_id=user.UserId,
        username=getattr(user, "UserName", None),
        role_id=getattr(user, "UserRoleId", None),
        role_name=role_name,
        branch_id=getattr(user, "BranchId", None),
        agent_id=agent_id,
        emp_id=emp_id,
        employee_id=emp_id,
        franchise_id=franchise_id,
    )


    # Attach server-resolved context attributes onto User instance
    setattr(user, "user_id", context.user_id)
    setattr(user, "role_id", context.role_id)
    setattr(user, "role_name", context.role_name)
    setattr(user, "role_obj", role)
    setattr(user, "branch_id", context.branch_id)
    setattr(user, "agent_id", context.agent_id)
    setattr(user, "emp_id", context.emp_id)
    setattr(user, "employee_id", context.employee_id)
    setattr(user, "franchise_id", context.franchise_id)
    setattr(user, "principal_context", context)

    return context
