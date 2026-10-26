"""
Legacy Mobile ASMX Compatibility Router (GAP-P1-001 & GAP-P1-002).
Mounts directly at root /Service.asmx for backward compatibility with field mobile clients.
Exact contract mirrors:
- POST /Service.asmx/AppLogin
- POST /Service.asmx/AgentAppLoginNew
- POST /Service.asmx/CheckLoginCustomer
- POST /Service.asmx/SelectEwalletBalanceByAgent
"""
import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, Request, status, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.core.security import decode_access_token
from app.core.rbac import (
    resolve_principal_context,
    is_global_admin_role,
    is_global_read_role,
    AGENT_PRINCIPAL_ROLES,
    WALLET_ADMIN_WRITE_ROLES,
)
from app.models.user import User, UserRole
from app.models.profile import Agent, Employee
from app.models.customer import Customer
from app.models.ledger import LedgerMaster
from app.repositories.login_history import LoginHistoryRepository
from app.repositories.user import UserRepository
from app.repositories.role import RoleRepository
from app.repositories.payment_engine import PaymentEngineRepository
from app.services.auth import AuthService
from app.schemas.asmx_compat import (
    API_AgentResponse,
    API_AgentNewResponse,
    API_CustomerAppResponse,
    API_EwalletBalanceResponse,
)

logger = logging.getLogger("reliable.asmx_compat")

router = APIRouter()


async def _parse_asmx_payload(request: Request) -> Dict[str, Any]:
    """
    Extracts payload from JSON body, URL-encoded form data, or query params.
    Safely handles malformed input and returns an empty dictionary on error.
    """
    content_type = request.headers.get("content-type", "").lower()
    data: Dict[str, Any] = {}

    if "application/json" in content_type:
        try:
            body = await request.json()
            if isinstance(body, dict):
                data = body
        except Exception:
            data = {}
    elif "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
        try:
            form = await request.form()
            data = dict(form)
        except Exception:
            data = {}
    else:
        # Fallback: attempt JSON first, then form data, then query params
        try:
            body = await request.json()
            if isinstance(body, dict):
                data = body
        except Exception:
            try:
                form = await request.form()
                data = dict(form)
            except Exception:
                data = dict(request.query_params)

    return data


def _extract_param(data: Dict[str, Any], candidate_keys: List[str]) -> Optional[str]:
    """
    Extracts a value for candidate keys with case-insensitivity.
    Detects and rejects conflicting duplicate parameters safely.
    """
    found_values = []
    for k in candidate_keys:
        if k in data and data[k] is not None:
            found_values.append(str(data[k]).strip())

    if not found_values:
        return None

    # If multiple conflicting values exist for the same logical parameter, flag as conflict
    if len(set(found_values)) > 1:
        return "__CONFLICT__"

    return found_values[0]


def _get_client_ip(request: Request) -> Optional[str]:
    """Extracts client IP address respecting X-Forwarded-For."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


async def _require_authenticated_user(
    request: Request,
    session: AsyncSession,
) -> User:
    """
    Extracts and validates required Bearer authentication for ASMX compatibility endpoints.
    Enforces that callers must be actively authenticated with valid credentials.
    Raises HTTPException(401) on missing, malformed, expired, or inactive credentials.
    """
    auth_header = request.headers.get("authorization")
    if not auth_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided",
            headers={"WWW-Authenticate": "Bearer"},
        )

    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = parts[1]
    payload = decode_access_token(token)
    subject = payload.get("sub")
    if not subject:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = int(subject)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_repo = UserRepository(session)
    user = await user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive or disabled",
            headers={"WWW-Authenticate": "Bearer"},
        )

    role_repo = RoleRepository(session)
    role: Optional[UserRole] = None
    if user.UserRoleId is not None:
        role = await role_repo.get_by_id(user.UserRoleId)
        if not role or not role.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Assigned user role is inactive or disabled",
                headers={"WWW-Authenticate": "Bearer"},
            )

    await resolve_principal_context(session, user, role)
    return user



@router.post(
    "/AppLogin",
    response_model=List[API_AgentResponse],
    summary="Legacy Mobile AppLogin Endpoint",
    description="Authenticates mobile POSP agent. Returns a 1-element JSON array matching legacy API_Agent DTO.",
)
async def app_login(
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> List[API_AgentResponse]:
    """
    Exact legacy ASMX AppLogin handler.
    Source: Service.asmx.cs L3951-L4010.
    """
    payload = await _parse_asmx_payload(request)
    username = _extract_param(payload, ["UserName", "username", "Username"])
    password = _extract_param(payload, ["Password", "password"])
    ip_address = _get_client_ip(request)

    # Fail closed on missing, empty, or conflicting parameters
    if not username or not password or username == "__CONFLICT__" or password == "__CONFLICT__":
        clean_user = "" if username == "__CONFLICT__" or not username else username
        return [
            API_AgentResponse(
                UserId=0,
                SalesExecutiveId=0,
                CoordinatorId=0,
                AgentId=0,
                UserName=clean_user,
                Password="",
                Coordinator="",
                UserRoleId="",
                OldVersion=None,
                NewVersion=None,
            )
        ]

    auth_service = AuthService(session)
    user, role, error = await auth_service.authenticate(username, password)
    history_repo = LoginHistoryRepository(session)

    if error or not user:
        try:
            found_user = await auth_service.user_repo.get_by_username(username)
            uid = found_user.UserId if found_user else None
            await history_repo.create_log(
                user_id=uid,
                username=username,
                action="FAILED_LOGIN",
                fun_perform="ASMX AppLogin Failed",
                ip_address=ip_address,
                remark=f"Failed reason: {error}",
            )
            await session.commit()
        except Exception as ex:
            logger.warning(f"Failed to record ASMX login failure audit: {ex}")

        # Exact legacy failure contract: 1-element list with zero IDs
        return [
            API_AgentResponse(
                UserId=0,
                SalesExecutiveId=0,
                CoordinatorId=0,
                AgentId=0,
                UserName=username,
                Password="",
                Coordinator="",
                UserRoleId="",
                OldVersion=None,
                NewVersion=None,
            )
        ]

    # Audit successful authentication
    try:
        await history_repo.create_log(
            user_id=user.UserId,
            username=user.UserName,
            action="LOGIN",
            fun_perform="ASMX AppLogin Success",
            ip_address=ip_address,
        )
        await session.commit()
    except Exception as ex:
        logger.warning(f"Failed to record ASMX login success audit: {ex}")

    # Resolve linked POSP Agent record
    agent_stmt = select(Agent).where(
        or_(Agent.UserId == user.UserId, Agent.AgentCode == user.UserName),
        Agent.isdeleted != "1",
    )
    agent_res = await session.execute(agent_stmt)
    agent = agent_res.scalars().first()

    agent_id = agent.AgentId if agent else 0
    sales_exec_id = (agent.SalesExecutiveId if agent and agent.SalesExecutiveId else 0)
    coord_id = (agent.CoordinatorId if agent and agent.CoordinatorId else 0)

    # Resolve Coordinator full name
    coord_name = "General"
    if coord_id > 0:
        emp_stmt = select(Employee).where(Employee.EmpId == coord_id, Employee.isdeleted != "1")
        emp_res = await session.execute(emp_stmt)
        emp = emp_res.scalars().first()
        if emp and emp.full_name:
            coord_name = emp.full_name

    role_id_str = str(user.UserRoleId or "")

    return [
        API_AgentResponse(
            UserId=user.UserId,
            SalesExecutiveId=sales_exec_id,
            CoordinatorId=coord_id,
            AgentId=agent_id,
            UserName=user.UserName or username,
            Password="",  # STRICT SECURITY: NEVER RETURN PASSWORD OR HASH
            Coordinator=coord_name,
            UserRoleId=role_id_str,
            OldVersion=None,
            NewVersion=None,
        )
    ]


@router.post(
    "/AgentAppLoginNew",
    response_model=List[API_AgentNewResponse],
    summary="Legacy Mobile AgentAppLoginNew Endpoint",
    description="Authenticates mobile POSP agent. Returns a 1-element JSON array matching legacy API_AgentNew DTO.",
)
async def agent_app_login_new(
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> List[API_AgentNewResponse]:
    """
    Exact legacy ASMX AgentAppLoginNew handler.
    Source: Service.asmx.cs L4616-L4706.
    """
    payload = await _parse_asmx_payload(request)
    username = _extract_param(payload, ["UserName", "username", "Username"])
    password = _extract_param(payload, ["Password", "password"])
    ip_address = _get_client_ip(request)

    # Fail closed on missing, empty, or conflicting parameters
    if not username or not password or username == "__CONFLICT__" or password == "__CONFLICT__":
        clean_user = "" if username == "__CONFLICT__" or not username else username
        return [
            API_AgentNewResponse(
                UserId=0,
                SalesExecutiveId=0,
                CoordinatorId=0,
                AgentId=0,
                UserName=clean_user,
                Password="",
                Coordinator="",
                UserRoleId="",
                OldVersion=None,
                NewVersion=None,
                FranchaiseId=0,
                BranchId=0,
                FullName="",
                MobileNo="",
                MailId="",
            )
        ]

    auth_service = AuthService(session)
    user, role, error = await auth_service.authenticate(username, password)
    history_repo = LoginHistoryRepository(session)

    if error or not user:
        try:
            found_user = await auth_service.user_repo.get_by_username(username)
            uid = found_user.UserId if found_user else None
            await history_repo.create_log(
                user_id=uid,
                username=username,
                action="FAILED_LOGIN",
                fun_perform="ASMX AgentAppLoginNew Failed",
                ip_address=ip_address,
                remark=f"Failed reason: {error}",
            )
            await session.commit()
        except Exception as ex:
            logger.warning(f"Failed to record ASMX login failure audit: {ex}")

        # Exact legacy failure contract: 1-element list with zero IDs
        return [
            API_AgentNewResponse(
                UserId=0,
                SalesExecutiveId=0,
                CoordinatorId=0,
                AgentId=0,
                UserName=username,
                Password="",
                Coordinator="",
                UserRoleId="",
                OldVersion=None,
                NewVersion=None,
                FranchaiseId=0,
                BranchId=0,
                FullName="",
                MobileNo="",
                MailId="",
            )
        ]

    # Audit successful authentication
    try:
        await history_repo.create_log(
            user_id=user.UserId,
            username=user.UserName,
            action="LOGIN",
            fun_perform="ASMX AgentAppLoginNew Success",
            ip_address=ip_address,
        )
        await session.commit()
    except Exception as ex:
        logger.warning(f"Failed to record ASMX login success audit: {ex}")

    # Resolve linked POSP Agent record
    agent_stmt = select(Agent).where(
        or_(Agent.UserId == user.UserId, Agent.AgentCode == user.UserName),
        Agent.isdeleted != "1",
    )
    agent_res = await session.execute(agent_stmt)
    agent = agent_res.scalars().first()

    agent_id = agent.AgentId if agent else 0
    sales_exec_id = (agent.SalesExecutiveId if agent and agent.SalesExecutiveId else 0)
    coord_id = (agent.CoordinatorId if agent and agent.CoordinatorId else 0)
    franchise_id = (agent.FranchiseId if agent and agent.FranchiseId else 0)
    branch_id = (agent.BranchId if agent and agent.BranchId else (user.BranchId or 0))
    full_name = agent.full_name if agent else (user.UserName or "")
    mobile_no = agent.MobileNo if agent and agent.MobileNo else (user.mobile_no or "")
    mail_id = agent.EmailId if agent and agent.EmailId else ""

    # Resolve Coordinator full name
    coord_name = "General"
    if coord_id > 0:
        emp_stmt = select(Employee).where(Employee.EmpId == coord_id, Employee.isdeleted != "1")
        emp_res = await session.execute(emp_stmt)
        emp = emp_res.scalars().first()
        if emp and emp.full_name:
            coord_name = emp.full_name

    role_id_str = str(user.UserRoleId or "")

    return [
        API_AgentNewResponse(
            UserId=user.UserId,
            SalesExecutiveId=sales_exec_id,
            CoordinatorId=coord_id,
            AgentId=agent_id,
            UserName=user.UserName or username,
            Password="",  # STRICT SECURITY: NEVER RETURN PASSWORD OR HASH
            Coordinator=coord_name,
            UserRoleId=role_id_str,
            OldVersion="1.0",
            NewVersion="1.0",
            FranchaiseId=franchise_id,
            BranchId=branch_id,
            FullName=full_name,
            MobileNo=mobile_no,
            MailId=mail_id,
        )
    ]


@router.post(
    "/CheckLoginCustomer",
    response_model=List[API_CustomerAppResponse],
    summary="Legacy Mobile CheckLoginCustomer Endpoint",
    description="Looks up customer profile by primary/secondary mobile numbers. Returns a 1-element JSON array matching legacy API_CustomerApp DTO.",
)
async def check_login_customer(
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> List[API_CustomerAppResponse]:
    """
    Exact legacy ASMX CheckLoginCustomer handler.
    Source: Service.asmx.cs L537-L581.
    """
    payload = await _parse_asmx_payload(request)
    mob1 = _extract_param(payload, ["MoblieNo1", "moblieno1", "mobileno1", "MobileNo1", "MobileNo"])
    mob2 = _extract_param(payload, ["MoblieNo2", "moblieno2", "mobileno2", "MobileNo2"])

    clean_mob1 = "" if not mob1 or mob1 == "__CONFLICT__" else mob1
    clean_mob2 = "" if not mob2 or mob2 == "__CONFLICT__" else mob2

    if not clean_mob1 and not clean_mob2:
        return [
            API_CustomerAppResponse(
                CustomerId=0,
                Name="",
                MoblieNo1="",
                MoblieNo2="",
                EMailId="",
                Address="",
            )
        ]

    # Query matching active customer
    conditions = []
    if clean_mob1:
        conditions.append(Customer.MoblieNo1 == clean_mob1)
        conditions.append(Customer.MoblieNo2 == clean_mob1)
    if clean_mob2:
        conditions.append(Customer.MoblieNo1 == clean_mob2)
        conditions.append(Customer.MoblieNo2 == clean_mob2)

    cust_stmt = (
        select(Customer)
        .where(or_(*conditions), Customer.isdeleted != "1")
        .order_by(Customer.CustomerId.desc())
    )
    cust_res = await session.execute(cust_stmt)
    customer = cust_res.scalars().first()

    if not customer:
        return [
            API_CustomerAppResponse(
                CustomerId=0,
                Name="",
                MoblieNo1=clean_mob1,
                MoblieNo2=clean_mob2,
                EMailId="",
                Address="",
            )
        ]

    # Construct customer display name
    name_parts = [p for p in [customer.CustFName, customer.CustMName, customer.CustLName] if p]
    cust_name = " ".join(name_parts) if name_parts else (customer.CompanyName or "")
    address = customer.ComAddrLine1 or customer.PerAddrLine1 or ""

    return [
        API_CustomerAppResponse(
            CustomerId=customer.CustomerId,
            Name=cust_name,
            MoblieNo1=customer.MoblieNo1 or clean_mob1,
            MoblieNo2=customer.MoblieNo2 or clean_mob2,
            EMailId=customer.EMailId or "",
            Address=address,
        )
    ]


@router.post(
    "/SelectEwalletBalanceByAgent",
    response_model=List[API_EwalletBalanceResponse],
    summary="Legacy Mobile SelectEwalletBalanceByAgent Endpoint",
    description="Returns wallet balance for POSP agent matching legacy sp_SelectEwalletBalance contract. Enforces BOLA/IDOR protection and mandatory authentication.",
)
async def select_ewallet_balance_by_agent(
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> List[API_EwalletBalanceResponse]:
    """
    Exact legacy ASMX SelectEwalletBalanceByAgent handler.
    Source: Service.asmx.cs L14640-L14667.
    Strictly requires authenticated Bearer credentials to prevent unauthenticated BOLA/IDOR.
    """
    # 1. Mandatory Authentication Gate
    user = await _require_authenticated_user(request, session)

    # 2. Extract and validate AgentId parameter
    payload = await _parse_asmx_payload(request)
    agent_id_raw = _extract_param(payload, ["AgentId", "agentid", "agent_id", "Agent_Id"])

    # Fail closed on missing, malformed, non-positive, or conflicting agent ID
    if not agent_id_raw or agent_id_raw == "__CONFLICT__":
        return [
            API_EwalletBalanceResponse(
                Balance=0.0,
                EwalletBalance=0.0,
                AgentId=0,
            )
        ]

    try:
        agent_id = int(agent_id_raw)
    except (ValueError, TypeError):
        return [
            API_EwalletBalanceResponse(
                Balance=0.0,
                EwalletBalance=0.0,
                AgentId=0,
            )
        ]

    if agent_id <= 0:
        return [
            API_EwalletBalanceResponse(
                Balance=0.0,
                EwalletBalance=0.0,
                AgentId=0,
            )
        ]

    # 3. Verify agent exists, is active, and not deleted
    agent_stmt = select(Agent).where(
        Agent.AgentId == agent_id,
        Agent.isdeleted != "1",
        Agent.IsActive == 1,
    )
    agent_res = await session.execute(agent_stmt)
    agent = agent_res.scalars().first()

    if not agent:
        return [
            API_EwalletBalanceResponse(
                Balance=0.0,
                EwalletBalance=0.0,
                AgentId=0,
            )
        ]

    # 4. Mandatory Authorization & BOLA/IDOR Enforcement
    principal = getattr(user, "principal_context", None)
    role_name = (
        getattr(principal, "role_name", None)
        or getattr(user, "role_name", "")
        or ""
    ).strip().upper()

    # Global admin, global read, and wallet admin roles can view any agent's balance
    if not (
        is_global_admin_role(role_name)
        or is_global_read_role(role_name)
        or role_name in WALLET_ADMIN_WRITE_ROLES
    ):
        agent_roles_upper = {r.strip().upper() for r in AGENT_PRINCIPAL_ROLES}
        if role_name in agent_roles_upper:
            bound_agent = getattr(principal, "agent_id", None) or getattr(user, "partner_user_id", None)
            if bound_agent is None and agent.UserId == user.UserId:
                bound_agent = agent.AgentId
            if bound_agent != agent_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: Agent principal can only access its own Agent E-Wallet.",
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: Role '{role_name}' is not authorized to access Agent E-Wallet.",
            )

    # 5. Resolve wallet ledger (tbl_ledgermaster: LedgerTypeId=5 for AGENT, ReferenceId=agent_id)
    ledger_stmt = (
        select(LedgerMaster)
        .where(
            LedgerMaster.LedgerTypeId == 5,
            LedgerMaster.ReferenceId == agent_id,
            or_(LedgerMaster.isdeleted == "0", LedgerMaster.isdeleted.is_(None)),
        )
        .order_by(LedgerMaster.LedgerMId)
        .limit(1)
    )
    ledger_res = await session.execute(ledger_stmt)
    ledger = ledger_res.scalars().first()

    if not ledger:
        balance_val = 0.0
    else:
        repo = PaymentEngineRepository(session)
        settled, locked, available = await repo.compute_wallet_balances(ledger.LedgerMId)
        balance_val = float(available)

    return [
        API_EwalletBalanceResponse(
            Balance=balance_val,
            EwalletBalance=balance_val,
            AgentId=agent_id,
        )
    ]
