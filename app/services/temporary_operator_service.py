"""
Phase 29 Service Layer:
Temporary Operator Role & Workload Delegation Master.
Physical Tables:
1. tbl_tempararyoperator (TemporaryOperator)
"""
import asyncio
from datetime import datetime
from typing import List, Optional, Tuple, Dict, Set
import logging
from fastapi import HTTPException, status
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.temporary_operator import TemporaryOperator
from app.models.profile import Employee
from app.models.user import User, UserRole
from app.core.rbac import (
    PrincipalContext,
    is_global_admin_role,
    TEMPORARY_OPERATOR_ADMIN_ROLES,
    TEMPORARY_OPERATOR_SUPERVISORY_ROLES,
    OPERATOR_ROLES,
)
from app.schemas.temporary_operator import (
    TemporaryOperatorCreate,
    TemporaryOperatorUpdate,
    TemporaryOperatorResponse,
    TemporaryOperatorListResponse,
    EffectiveOperatorResponse,
    EligibleOperatorResponse,
)

logger = logging.getLogger(__name__)

# Mutex to ensure concurrency-safe delegation creation and prevent duplicate active overlaps
_DELEGATION_WRITE_LOCK = asyncio.Lock()


class TemporaryOperatorService:
    """Service orchestrating temporary operator assignment, workload delegation, and effective operator resolution."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def _get_operator_names(self, operator_ids: List[int]) -> Dict[int, str]:
        """Fetch employee/user display names for a set of operator IDs."""
        if not operator_ids:
            return {}
        names: Dict[int, str] = {}
        unique_ids = list(set(operator_ids))

        # 1. Try Employee table first (EmpId matching operator_id)
        emp_query = select(Employee).where(
            Employee.EmpId.in_(unique_ids),
            Employee.isdeleted != "1",
        )
        emp_result = await self.db.execute(emp_query)
        for emp in emp_result.scalars().all():
            display = emp.full_name or emp.UserName or f"Operator #{emp.EmpId}"
            names[emp.EmpId] = display

        # 2. For remaining unmatched IDs, check tbl_user
        remaining_ids = [oid for oid in unique_ids if oid not in names]
        if remaining_ids:
            user_query = select(User).where(User.UserId.in_(remaining_ids))
            user_result = await self.db.execute(user_query)
            for usr in user_result.scalars().all():
                names[usr.UserId] = usr.UserName or f"Operator #{usr.UserId}"

        return names

    async def _resolve_operator_info(self, operator_id: int) -> Tuple[bool, Optional[int], str, bool]:
        """
        Resolves operator metadata: (exists, branch_id, role_name, is_active).
        Checks tbl_user first, then tbl_employee.
        """
        # Check tbl_user
        u_stmt = (
            select(User, UserRole.UserRole)
            .outerjoin(UserRole, User.UserRoleId == UserRole.UserRoleId)
            .where(User.UserId == operator_id)
        )
        u_res = await self.db.execute(u_stmt)
        u_row = u_res.first()
        if u_row:
            user_obj, role_name = u_row
            return (True, user_obj.BranchId, (role_name or "").strip().upper(), user_obj.is_active)

        # Check tbl_employee
        e_stmt = (
            select(Employee, UserRole.UserRole)
            .outerjoin(UserRole, Employee.UserRoleId == UserRole.UserRoleId)
            .where(Employee.EmpId == operator_id)
        )
        e_res = await self.db.execute(e_stmt)
        e_row = e_res.first()
        if e_row:
            emp_obj, role_name = e_row
            is_active = str(emp_obj.isdeleted).strip() != "1"
            return (True, emp_obj.BranchId, (role_name or "").strip().upper(), is_active)

        return (False, None, "", False)

    def _validate_operator_management_access(
        self,
        principal: PrincipalContext,
        target_branch_id: Optional[int],
        per_operator_id: int,
    ) -> None:
        """
        Enforces RBAC and multi-tenant branch isolation for operator delegation management.
        - Global Admin (OWNER, ADMIN, IT SUPPORT): unrestricted cross-branch write authority.
        - Supervisory (OPERATOR HEAD, SUPERVISOR, MANAGER, HOD): restricted to their own branch.
        - Operator (OPERATOR, FRANCHISE OPERATOR): can only delegate their own workload within their branch.
        - Other roles: HTTP 403 Forbidden.
        """
        role = (principal.role_name or "").strip().upper()

        if is_global_admin_role(role) or role in TEMPORARY_OPERATOR_ADMIN_ROLES:
            return

        if role in TEMPORARY_OPERATOR_SUPERVISORY_ROLES:
            if (
                principal.branch_id is not None
                and target_branch_id is not None
                and principal.branch_id != target_branch_id
            ):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=(
                        f"Access denied: Supervisory users can only manage operator delegations "
                        f"for their own branch ({principal.branch_id}). Target operator branch is {target_branch_id}."
                    ),
                )
            return

        if role in OPERATOR_ROLES:
            caller_ids = {principal.user_id, principal.emp_id, principal.employee_id}
            caller_ids.discard(None)
            if per_operator_id not in caller_ids:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: Operators are only permitted to delegate their own workload.",
                )
            if (
                principal.branch_id is not None
                and target_branch_id is not None
                and principal.branch_id != target_branch_id
            ):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Access denied: Cannot delegate to an operator outside your branch ({principal.branch_id}).",
                )
            return

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied: Role '{principal.role_name}' is not authorized to manage operator delegations.",
        )

    def _validate_operator_read_access(
        self,
        principal: PrincipalContext,
        target_branch_id: Optional[int],
        per_operator_id: int,
        temp_operator_id: int,
    ) -> None:
        """Enforces RBAC and branch/user scoping when viewing delegation details."""
        role = (principal.role_name or "").strip().upper()

        if is_global_admin_role(role) or role in TEMPORARY_OPERATOR_ADMIN_ROLES:
            return

        if role in TEMPORARY_OPERATOR_SUPERVISORY_ROLES:
            if (
                principal.branch_id is not None
                and target_branch_id is not None
                and principal.branch_id != target_branch_id
            ):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Access denied: Cannot view operator delegations outside your branch ({principal.branch_id}).",
                )
            return

        if role in OPERATOR_ROLES:
            caller_ids = {principal.user_id, principal.emp_id, principal.employee_id}
            caller_ids.discard(None)
            if per_operator_id not in caller_ids and temp_operator_id not in caller_ids:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: Operators may only view delegations involving their own assignments.",
                )
            return

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied: Role '{principal.role_name}' is not authorized to view operator delegations.",
        )

    def _is_active(self, delegation: TemporaryOperator, as_of: Optional[datetime] = None) -> bool:
        if delegation.isdeleted == 1:
            return False
        check_time = as_of or datetime.utcnow()
        if delegation.ValidFrom and delegation.ValidFrom > check_time:
            return False
        if delegation.ValidUpTo and delegation.ValidUpTo < check_time:
            return False
        return True

    def _normalize_valid_up_to(self, dt: Optional[datetime]) -> Optional[datetime]:
        """Ensures that midnight dates (00:00:00) are inclusive of the full calendar day."""
        if dt is None:
            return None
        if dt.hour == 0 and dt.minute == 0 and dt.second == 0 and dt.microsecond == 0:
            return dt.replace(hour=23, minute=59, second=59, microsecond=999999)
        return dt

    async def create_delegation(
        self,
        payload: TemporaryOperatorCreate,
        principal: PrincipalContext,
    ) -> TemporaryOperatorResponse:
        """
        Creates a temporary operator delegation assignment with strict RBAC, branch isolation,
        anti-chaining, and anti-circularity verification.
        Legacy Parity:
        - `adm_TemporaryOperator.aspx.cs:btnTranfer_Click`
        - Stored Procedure `Sp_TempararyOperator` with `P_Opr = 'Insert'`
        """
        if payload.per_operator_id == payload.temp_operator_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Permanent Operator and Temporary Operator cannot be the same user.",
            )

        # 1. Verify existence and operator roles for both parties
        per_exists, per_branch, per_role, per_active = await self._resolve_operator_info(payload.per_operator_id)
        if per_exists:
            if not per_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Permanent Operator #{payload.per_operator_id} account is inactive.",
                )
            if per_role and per_role not in OPERATOR_ROLES and per_role not in TEMPORARY_OPERATOR_ADMIN_ROLES:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"User #{payload.per_operator_id} does not have an OPERATOR role (assigned role: {per_role}).",
                )

        temp_exists, temp_branch, temp_role, temp_active = await self._resolve_operator_info(payload.temp_operator_id)
        if temp_exists:
            if not temp_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Temporary Operator #{payload.temp_operator_id} account is inactive.",
                )
            if temp_role and temp_role not in OPERATOR_ROLES and temp_role not in TEMPORARY_OPERATOR_ADMIN_ROLES:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"User #{payload.temp_operator_id} does not have an OPERATOR role (assigned role: {temp_role}).",
                )

        # 2. Enforce branch matching between permanent and temporary operator
        if per_branch is not None and temp_branch is not None and per_branch != temp_branch:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Cross-branch operator delegation prohibited: Permanent Operator belongs to Branch {per_branch}, "
                    f"whereas Temporary Operator belongs to Branch {temp_branch}."
                ),
            )

        target_branch = per_branch if per_branch is not None else temp_branch

        # 3. Enforce caller management authorization & branch isolation
        self._validate_operator_management_access(principal, target_branch, payload.per_operator_id)

        now = datetime.utcnow()
        valid_from = payload.valid_from or now
        valid_up_to = self._normalize_valid_up_to(payload.valid_up_to or now)

        async with _DELEGATION_WRITE_LOCK:
            # Reset transaction snapshot to read latest committed state
            await self.db.rollback()

            # 4. Anti-circularity check: Check if temp_operator has an active delegation to per_operator
            circ_query = (
                select(TemporaryOperator)
                .where(
                    TemporaryOperator.Per_OperatorId == payload.temp_operator_id,
                    TemporaryOperator.Temp_OperatorId == payload.per_operator_id,
                    TemporaryOperator.isdeleted == 0,
                    or_(TemporaryOperator.ValidUpTo == None, TemporaryOperator.ValidUpTo >= valid_from),
                    or_(TemporaryOperator.ValidFrom == None, TemporaryOperator.ValidFrom <= valid_up_to),
                )
                .with_for_update()
            )
            circ_res = await self.db.execute(circ_query)
            if circ_res.scalars().first():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"Circular delegation prohibited: Operator #{payload.temp_operator_id} already has an active "
                        f"delegation to Operator #{payload.per_operator_id}."
                    ),
                )

            # 5. Anti-chaining check: Check if temp_operator has currently delegated away their own workload
            chain_query = (
                select(TemporaryOperator)
                .where(
                    TemporaryOperator.Per_OperatorId == payload.temp_operator_id,
                    TemporaryOperator.isdeleted == 0,
                    or_(TemporaryOperator.ValidUpTo == None, TemporaryOperator.ValidUpTo >= valid_from),
                    or_(TemporaryOperator.ValidFrom == None, TemporaryOperator.ValidFrom <= valid_up_to),
                )
                .with_for_update()
            )
            chain_res = await self.db.execute(chain_query)
            if chain_res.scalars().first():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"Chained delegation prohibited: Cannot assign Operator #{payload.temp_operator_id} as a substitute "
                        f"because they have already delegated their own workload to another operator."
                    ),
                )

            # Check if per_operator is currently acting as a temporary operator for another operator
            chain_query_per = (
                select(TemporaryOperator)
                .where(
                    TemporaryOperator.Temp_OperatorId == payload.per_operator_id,
                    TemporaryOperator.isdeleted == 0,
                    or_(TemporaryOperator.ValidUpTo == None, TemporaryOperator.ValidUpTo >= valid_from),
                    or_(TemporaryOperator.ValidFrom == None, TemporaryOperator.ValidFrom <= valid_up_to),
                )
                .with_for_update()
            )
            chain_res_per = await self.db.execute(chain_query_per)
            if chain_res_per.scalars().first():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"Chained delegation prohibited: Operator #{payload.per_operator_id} is currently acting as a "
                        f"temporary operator for another operator and cannot re-delegate duties."
                    ),
                )

            # 6. Check for existing active overlapping delegation for this permanent operator
            overlap_query = (
                select(TemporaryOperator)
                .where(
                    TemporaryOperator.Per_OperatorId == payload.per_operator_id,
                    TemporaryOperator.isdeleted == 0,
                )
                .with_for_update()
            )
            overlap_res = await self.db.execute(overlap_query)
            existing_delegations = overlap_res.scalars().all()

            for ed in existing_delegations:
                e_from = ed.ValidFrom or now
                e_to = self._normalize_valid_up_to(ed.ValidUpTo or now)
                if not (valid_up_to < e_from or valid_from > e_to):
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=(
                            f"An active delegation already exists for Permanent Operator {payload.per_operator_id} "
                            f"(Delegation ID: {ed.ID}, Temporary Operator: {ed.Temp_OperatorId}, "
                            f"Valid: {ed.ValidFrom} to {ed.ValidUpTo})."
                        ),
                    )

            delegation = TemporaryOperator(
                Per_OperatorId=payload.per_operator_id,
                Temp_OperatorId=payload.temp_operator_id,
                ValidFrom=valid_from,
                ValidUpTo=valid_up_to,
                CreateUser=principal.username,
                CreateDate=now,
                isdeleted=0,
            )
            self.db.add(delegation)
            await self.db.commit()
            await self.db.refresh(delegation)

        logger.info(
            "AUDIT: Temporary Operator Delegation created by '%s' (UserId=%s, Role=%s, Branch=%s): "
            "Permanent Operator #%s -> Temporary Operator #%s (Valid: %s to %s, DelegationID: %s)",
            principal.username,
            principal.user_id,
            principal.role_name,
            principal.branch_id,
            delegation.Per_OperatorId,
            delegation.Temp_OperatorId,
            delegation.ValidFrom,
            delegation.ValidUpTo,
            delegation.ID,
        )

        names = await self._get_operator_names([delegation.Per_OperatorId, delegation.Temp_OperatorId])
        return TemporaryOperatorResponse(
            ID=delegation.ID,
            Per_OperatorId=delegation.Per_OperatorId,
            per_operator_name=names.get(delegation.Per_OperatorId),
            Temp_OperatorId=delegation.Temp_OperatorId,
            temp_operator_name=names.get(delegation.Temp_OperatorId),
            ValidFrom=delegation.ValidFrom,
            ValidUpTo=delegation.ValidUpTo,
            CreateUser=delegation.CreateUser,
            CreateDate=delegation.CreateDate,
            isdeleted=delegation.isdeleted,
            UpdatedUser=delegation.UpdatedUser,
            UpdatedDate=delegation.UpdatedDate,
            is_active=self._is_active(delegation, now),
        )

    async def list_delegations(
        self,
        principal: PrincipalContext,
        per_operator_id: Optional[int] = None,
        temp_operator_id: Optional[int] = None,
        active_only: bool = False,
        skip: int = 0,
        limit: int = 50,
    ) -> TemporaryOperatorListResponse:
        """
        Lists temporary operator delegations with multi-tenant branch and role scoping.
        Legacy Parity:
        - `adm_TemporaryOperator.aspx.cs:fillGrid`
        - Stored Procedure `Sp_TempararyOperator` with `P_Opr = 'Select'`
        """
        role = (principal.role_name or "").strip().upper()
        is_global_admin = is_global_admin_role(role) or role in TEMPORARY_OPERATOR_ADMIN_ROLES
        is_supervisor = role in TEMPORARY_OPERATOR_SUPERVISORY_ROLES
        is_operator = role in OPERATOR_ROLES

        if not (is_global_admin or is_supervisor or is_operator):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: Role '{principal.role_name}' is not authorized to list operator delegations.",
            )

        query = select(TemporaryOperator).where(TemporaryOperator.isdeleted == 0)

        # Non-admin operators can only see delegations involving themselves
        if is_operator and not is_supervisor and not is_global_admin:
            caller_ids = {principal.user_id, principal.emp_id, principal.employee_id}
            caller_ids.discard(None)
            query = query.where(
                or_(
                    TemporaryOperator.Per_OperatorId.in_(caller_ids),
                    TemporaryOperator.Temp_OperatorId.in_(caller_ids),
                )
            )

        # Non-admin supervisory users are restricted to operators belonging to their branch
        if is_supervisor and not is_global_admin and principal.branch_id is not None:
            # Query operator IDs in this branch from tbl_user and tbl_employee
            u_branch_sub = select(User.UserId).where(User.BranchId == principal.branch_id)
            e_branch_sub = select(Employee.EmpId).where(Employee.BranchId == principal.branch_id, Employee.isdeleted != "1")
            query = query.where(
                or_(
                    TemporaryOperator.Per_OperatorId.in_(u_branch_sub),
                    TemporaryOperator.Per_OperatorId.in_(e_branch_sub),
                )
            )

        if per_operator_id is not None and per_operator_id > 0:
            query = query.where(TemporaryOperator.Per_OperatorId == per_operator_id)
        if temp_operator_id is not None and temp_operator_id > 0:
            query = query.where(TemporaryOperator.Temp_OperatorId == temp_operator_id)

        now = datetime.utcnow()
        if active_only:
            query = query.where(
                or_(TemporaryOperator.ValidFrom == None, TemporaryOperator.ValidFrom <= now),
                or_(TemporaryOperator.ValidUpTo == None, TemporaryOperator.ValidUpTo >= now),
            )

        count_query = select(func.count()).select_from(query.subquery())
        total_res = await self.db.execute(count_query)
        total = total_res.scalar_one()

        query = query.order_by(TemporaryOperator.ID.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)
        records = result.scalars().all()

        all_ids: List[int] = []
        for r in records:
            all_ids.extend([r.Per_OperatorId, r.Temp_OperatorId])
        names = await self._get_operator_names(all_ids)

        items = [
            TemporaryOperatorResponse(
                ID=r.ID,
                Per_OperatorId=r.Per_OperatorId,
                per_operator_name=names.get(r.Per_OperatorId),
                Temp_OperatorId=r.Temp_OperatorId,
                temp_operator_name=names.get(r.Temp_OperatorId),
                ValidFrom=r.ValidFrom,
                ValidUpTo=r.ValidUpTo,
                CreateUser=r.CreateUser,
                CreateDate=r.CreateDate,
                isdeleted=r.isdeleted,
                UpdatedUser=r.UpdatedUser,
                UpdatedDate=r.UpdatedDate,
                is_active=self._is_active(r, now),
            )
            for r in records
        ]

        return TemporaryOperatorListResponse(items=items, total=total)

    async def get_delegation_by_id(
        self, delegation_id: int, principal: PrincipalContext
    ) -> TemporaryOperatorResponse:
        """Retrieves a single delegation record by primary key with branch authorization."""
        record = await self.db.get(TemporaryOperator, delegation_id)
        if not record or record.isdeleted == 1:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Temporary operator delegation {delegation_id} not found.",
            )

        _, per_branch, _, _ = await self._resolve_operator_info(record.Per_OperatorId)
        self._validate_operator_read_access(
            principal, per_branch, record.Per_OperatorId, record.Temp_OperatorId
        )

        now = datetime.utcnow()
        names = await self._get_operator_names([record.Per_OperatorId, record.Temp_OperatorId])
        return TemporaryOperatorResponse(
            ID=record.ID,
            Per_OperatorId=record.Per_OperatorId,
            per_operator_name=names.get(record.Per_OperatorId),
            Temp_OperatorId=record.Temp_OperatorId,
            temp_operator_name=names.get(record.Temp_OperatorId),
            ValidFrom=record.ValidFrom,
            ValidUpTo=record.ValidUpTo,
            CreateUser=record.CreateUser,
            CreateDate=record.CreateDate,
            isdeleted=record.isdeleted,
            UpdatedUser=record.UpdatedUser,
            UpdatedDate=record.UpdatedDate,
            is_active=self._is_active(record, now),
        )

    async def update_delegation(
        self,
        delegation_id: int,
        payload: TemporaryOperatorUpdate,
        principal: PrincipalContext,
    ) -> TemporaryOperatorResponse:
        """Updates validity window of an existing delegation with RBAC enforcement."""
        record = await self.db.get(TemporaryOperator, delegation_id)
        if not record or record.isdeleted == 1:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Temporary operator delegation {delegation_id} not found.",
            )

        _, per_branch, _, _ = await self._resolve_operator_info(record.Per_OperatorId)
        self._validate_operator_management_access(principal, per_branch, record.Per_OperatorId)

        if payload.valid_from is not None:
            record.ValidFrom = payload.valid_from
        if payload.valid_up_to is not None:
            record.ValidUpTo = self._normalize_valid_up_to(payload.valid_up_to)

        record.UpdatedUser = principal.username
        record.UpdatedDate = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(record)

        logger.info(
            "AUDIT: Temporary Operator Delegation #%s updated by '%s': Valid=%s to %s",
            delegation_id,
            principal.username,
            record.ValidFrom,
            record.ValidUpTo,
        )

        now = datetime.utcnow()
        names = await self._get_operator_names([record.Per_OperatorId, record.Temp_OperatorId])
        return TemporaryOperatorResponse(
            ID=record.ID,
            Per_OperatorId=record.Per_OperatorId,
            per_operator_name=names.get(record.Per_OperatorId),
            Temp_OperatorId=record.Temp_OperatorId,
            temp_operator_name=names.get(record.Temp_OperatorId),
            ValidFrom=record.ValidFrom,
            ValidUpTo=record.ValidUpTo,
            CreateUser=record.CreateUser,
            CreateDate=record.CreateDate,
            isdeleted=record.isdeleted,
            UpdatedUser=record.UpdatedUser,
            UpdatedDate=record.UpdatedDate,
            is_active=self._is_active(record, now),
        )

    async def revoke_delegation(
        self,
        delegation_id: int,
        principal: PrincipalContext,
    ) -> dict:
        """
        Soft-deletes (revokes) a temporary operator delegation assignment with strict RBAC.
        Legacy Parity:
        - `adm_TemporaryOperator.aspx.cs:AppTransGrid_RowDeleting`
        - Stored Procedure `Sp_TempararyOperator` with `P_Opr = 'Delete'`
        """
        record = await self.db.get(TemporaryOperator, delegation_id)
        if not record or record.isdeleted == 1:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Temporary operator delegation {delegation_id} not found or already revoked.",
            )

        _, per_branch, _, _ = await self._resolve_operator_info(record.Per_OperatorId)
        self._validate_operator_management_access(principal, per_branch, record.Per_OperatorId)

        record.isdeleted = 1
        record.UpdatedUser = principal.username
        record.UpdatedDate = datetime.utcnow()

        await self.db.commit()

        logger.info(
            "AUDIT: Temporary Operator Delegation #%s revoked (soft-deleted) by '%s' (UserId=%s, Role=%s)",
            delegation_id,
            principal.username,
            principal.user_id,
            principal.role_name,
        )

        return {
            "success": True,
            "message": "Temporary operator delegation revoked successfully.",
            "id": delegation_id,
        }

    async def resolve_effective_operator(
        self,
        operator_id: int,
        principal: Optional[PrincipalContext] = None,
        as_of: Optional[datetime] = None,
    ) -> EffectiveOperatorResponse:
        """
        Resolves the effective operator for a given operator ID at a specified point in time.
        If the operator has delegated their duties to a temporary operator whose validity window
        covers the query date, returns the temporary operator ID.
        Otherwise, returns the permanent operator ID.
        """
        check_time = as_of or datetime.utcnow()

        if principal:
            _, per_branch, _, _ = await self._resolve_operator_info(operator_id)
            role = (principal.role_name or "").strip().upper()
            if not is_global_admin_role(role) and role not in TEMPORARY_OPERATOR_ADMIN_ROLES:
                if role in TEMPORARY_OPERATOR_SUPERVISORY_ROLES:
                    if (
                        principal.branch_id is not None
                        and per_branch is not None
                        and principal.branch_id != per_branch
                    ):
                        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail=f"Access denied: Cannot resolve operator outside your branch ({principal.branch_id}).",
                        )
                elif role in OPERATOR_ROLES:
                    caller_ids = {principal.user_id, principal.emp_id, principal.employee_id}
                    caller_ids.discard(None)
                    if operator_id not in caller_ids:
                        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail="Access denied: Operators may only resolve their own effective delegation status.",
                        )

        # Check if this operator is a permanent operator with an active delegation
        query = (
            select(TemporaryOperator)
            .where(
                TemporaryOperator.Per_OperatorId == operator_id,
                TemporaryOperator.isdeleted == 0,
                or_(TemporaryOperator.ValidFrom == None, TemporaryOperator.ValidFrom <= check_time),
                or_(TemporaryOperator.ValidUpTo == None, TemporaryOperator.ValidUpTo >= check_time),
            )
            .order_by(TemporaryOperator.ID.desc())
        )

        result = await self.db.execute(query)
        active_delegation = result.scalars().first()

        names = await self._get_operator_names([operator_id])

        if active_delegation:
            temp_names = await self._get_operator_names([active_delegation.Temp_OperatorId])
            logger.info(
                "AUDIT: Effective operator lookup for Operator #%s at %s -> Delegated to Temporary Operator #%s (DelegationID=%s)",
                operator_id,
                check_time,
                active_delegation.Temp_OperatorId,
                active_delegation.ID,
            )
            return EffectiveOperatorResponse(
                requested_operator_id=operator_id,
                effective_operator_id=active_delegation.Temp_OperatorId,
                delegation_active=True,
                delegation_id=active_delegation.ID,
                delegation_role="TEMPORARY",
                permanent_operator_name=names.get(operator_id),
                temporary_operator_name=temp_names.get(active_delegation.Temp_OperatorId),
                valid_from=active_delegation.ValidFrom,
                valid_up_to=active_delegation.ValidUpTo,
            )

        logger.info(
            "AUDIT: Effective operator lookup for Operator #%s at %s -> No active delegation (Effective=%s)",
            operator_id,
            check_time,
            operator_id,
        )
        return EffectiveOperatorResponse(
            requested_operator_id=operator_id,
            effective_operator_id=operator_id,
            delegation_active=False,
            delegation_id=None,
            delegation_role="PERMANENT",
            permanent_operator_name=names.get(operator_id),
            temporary_operator_name=None,
            valid_from=None,
            valid_up_to=None,
        )

    async def list_eligible_operators(self, principal: Optional[PrincipalContext] = None) -> List[EligibleOperatorResponse]:
        """
        Lists staff members with operator roles eligible for assignment or delegation.
        Legacy Parity:
        - `adm_TemporaryOperator.aspx.cs:bindSales`
        - Queries employees and filters `UserRole='OPERATOR'`.
        """
        query = (
            select(Employee, UserRole.UserRole)
            .outerjoin(UserRole, Employee.UserRoleId == UserRole.UserRoleId)
            .where(
                Employee.isdeleted != "1",
                or_(
                    UserRole.UserRole.ilike("%OPERATOR%"),
                    UserRole.code.ilike("%OPERATOR%"),
                    Employee.UserRoleId.in_([6, 19, 54]),  # Standard operator role IDs in ERP
                ),
            )
        )

        # Non-admin supervisory users are scoped to their branch
        if principal:
            role = (principal.role_name or "").strip().upper()
            if not is_global_admin_role(role) and role not in TEMPORARY_OPERATOR_ADMIN_ROLES and principal.branch_id is not None:
                query = query.where(Employee.BranchId == principal.branch_id)

        query = query.order_by(Employee.EmpFName, Employee.EmpLName)
        result = await self.db.execute(query)
        rows = result.all()

        eligible = []
        for emp, role_name in rows:
            name = emp.full_name or emp.UserName or f"Employee #{emp.EmpId}"
            eligible.append(
                EligibleOperatorResponse(
                    emp_id=emp.EmpId,
                    emp_name=name,
                    user_role=role_name or "OPERATOR",
                )
            )

        # Fallback if no matching records found
        if not eligible:
            fallback_q = select(Employee).where(Employee.isdeleted != "1")
            if principal and principal.branch_id is not None and not is_global_admin_role(principal.role_name or ""):
                fallback_q = fallback_q.where(Employee.BranchId == principal.branch_id)
            fallback_q = fallback_q.limit(50)
            fb_res = await self.db.execute(fallback_q)
            for emp in fb_res.scalars().all():
                eligible.append(
                    EligibleOperatorResponse(
                        emp_id=emp.EmpId,
                        emp_name=emp.full_name or emp.UserName or f"Employee #{emp.EmpId}",
                        user_role="OPERATOR",
                    )
                )

        return eligible
