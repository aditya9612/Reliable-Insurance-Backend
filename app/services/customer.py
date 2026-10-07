from datetime import datetime
from typing import Optional, Sequence
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import is_global_admin_role, is_global_read_role
from app.models.customer import Customer
from app.models.user import User
from app.repositories.customer import CustomerRepository
from app.schemas.customer import CustomerCreate, CustomerUpdate


class CustomerService:
    """
    Business service layer for Customer operations.
    Enforces legacy normalization rules, branch scoping, immutable field protection,
    and race-condition-free customer code generation.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.customer_repo = CustomerRepository(session)

    def _is_admin(self, current_user: User) -> bool:
        """
        Determines if the current user has unrestricted global administrative write access.
        Verified global admin roles from Phase 5F: OWNER, ADMIN, IT SUPPORT.
        Does NOT treat BranchId in (0, None) or phantom 'SUPERADMIN' as admin (GAP-5F-02).
        """
        role = getattr(current_user, "role_name", None)
        return is_global_admin_role(role)

    def _can_read_all_branches(self, current_user: User) -> bool:
        """
        Determines if the current user has cross-branch read/search access.
        Verified global read roles from Phase 5F: OWNER, ADMIN, IT SUPPORT, ACCOUNT, ACCOUNT HEAD.
        """
        role = getattr(current_user, "role_name", None)
        return is_global_read_role(role)

    async def create_customer(
        self, payload: CustomerCreate, current_user: User
    ) -> Customer:
        """
        Creates a new customer entity following legacy sp_InsertCustomer contracts.
        - Generates atomic, collision-free CustomerCode based on CustomerId if not supplied.
        - Mirrors permanent address into communication address if omitted.
        - Enforces branch scoping based on authenticated user context.
        - Guarantees transaction atomicity.
        """
        # 1. Branch scoping resolution
        is_admin = self._is_admin(current_user)
        if is_admin:
            branch_id = payload.branch_id if payload.branch_id is not None else (current_user.BranchId or 0)
        else:
            branch_id = current_user.BranchId

        # 2. Duplicate CustomerCode check if explicitly provided by client
        if payload.customer_code:
            existing_code = await self.customer_repo.get_by_code(payload.customer_code.strip())
            if existing_code:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Customer code '{payload.customer_code}' already exists",
                )

        # 3. Communication address fallback (legacy code-behind parity)
        com_line1 = payload.com_addr_line1 or payload.per_addr_line1
        com_line2 = payload.com_addr_line2 or payload.per_addr_line2
        com_taluka = payload.com_taluka_id if payload.com_taluka_id else payload.per_taluka_id
        com_dist = payload.com_district_id if payload.com_district_id else payload.per_district_id
        com_state = payload.com_state_id if payload.com_state_id else payload.per_state_id
        com_pin = payload.com_pin_code or payload.per_pin_code

        now = datetime.utcnow()
        username = current_user.UserName or f"user_{current_user.UserId}"

        # 4. Construct Customer entity
        customer = Customer(
            CustomerCode=payload.customer_code.strip() if payload.customer_code else None,
            initial=payload.initial,
            CustFName=payload.cust_f_name,
            CustMName=payload.cust_m_name,
            CustLName=payload.cust_l_name,
            CustomerType=payload.customer_type or "Individual",
            ClientId=payload.client_id if payload.client_id is not None else 1,
            PerAddrLine1=payload.per_addr_line1,
            PerAddrLine2=payload.per_addr_line2,
            PerTalukaId=payload.per_taluka_id,
            PerDistrictId=payload.per_district_id,
            PerStateId=payload.per_state_id,
            PerPinCode=payload.per_pin_code,
            ComAddrLine1=com_line1,
            ComAddrLine2=com_line2,
            ComTalukaId=com_taluka,
            ComDistrictId=com_dist,
            ComStateId=com_state,
            ComPinCode=com_pin,
            MoblieNo1=payload.moblie_no1,
            MoblieNo2=payload.moblie_no2,
            Gender=payload.gender or "Male",
            MaritalStatus=payload.marital_status,
            PAN_No=payload.pan_no,
            AadharNo=payload.aadhar_no,
            DateOfBirth=payload.date_of_birth,
            EMailId=payload.email_id,
            NomineeName=payload.nominee_name,
            BranchId=branch_id,
            CreateDate=now,
            CreateUser=username,
            UpdateDate=now,
            UpdateUser=username,
            Extra1=payload.extra1,
            Extra2=payload.extra2,
            CompanyName=payload.company_name,
            isdeleted="0",
        )

        # 5. Atomic flush and CustomerCode generation
        self.session.add(customer)
        await self.session.flush()

        if not customer.CustomerCode:
            customer.CustomerCode = str(customer.CustomerId)
            await self.session.flush()

        await self.session.commit()
        await self.session.refresh(customer)
        return customer

    async def update_customer(
        self, customer_id: int, payload: CustomerUpdate, current_user: User
    ) -> Customer:
        """
        Updates an existing customer entity following legacy sp_UpdateCustomer contracts.
        - Enforces strict branch jurisdiction.
        - Protects immutable fields (CustomerId, CustomerCode, CreateDate, CreateUser, CompanyName, isdeleted).
        - Stamps UpdateDate and UpdateUser audit metadata.
        """
        customer = await self.customer_repo.get_by_id(customer_id)
        if not customer or customer.isdeleted == "1":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Customer with ID {customer_id} not found",
            )

        is_admin = self._is_admin(current_user)
        if not is_admin and customer.BranchId != current_user.BranchId:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: You do not have access to customers from other branches",
            )

        update_data = payload.model_dump(exclude_unset=True)

        field_map = {
            "initial": "initial",
            "cust_f_name": "CustFName",
            "cust_m_name": "CustMName",
            "cust_l_name": "CustLName",
            "customer_type": "CustomerType",
            "client_id": "ClientId",
            "per_addr_line1": "PerAddrLine1",
            "per_addr_line2": "PerAddrLine2",
            "per_taluka_id": "PerTalukaId",
            "per_district_id": "PerDistrictId",
            "per_state_id": "PerStateId",
            "per_pin_code": "PerPinCode",
            "com_addr_line1": "ComAddrLine1",
            "com_addr_line2": "ComAddrLine2",
            "com_taluka_id": "ComTalukaId",
            "com_district_id": "ComDistrictId",
            "com_state_id": "ComStateId",
            "com_pin_code": "ComPinCode",
            "moblie_no1": "MoblieNo1",
            "moblie_no2": "MoblieNo2",
            "gender": "Gender",
            "marital_status": "MaritalStatus",
            "pan_no": "PAN_No",
            "aadhar_no": "AadharNo",
            "date_of_birth": "DateOfBirth",
            "email_id": "EMailId",
            "nominee_name": "NomineeName",
            "extra1": "Extra1",
            "extra2": "Extra2",
        }

        for pydantic_field, model_attr in field_map.items():
            if pydantic_field in update_data:
                setattr(customer, model_attr, update_data[pydantic_field])

        # BranchId can be reassigned only by administrators
        if is_admin and "branch_id" in update_data and update_data["branch_id"] is not None:
            customer.BranchId = update_data["branch_id"]

        # Audit update
        customer.UpdateDate = datetime.utcnow()
        customer.UpdateUser = current_user.UserName or f"user_{current_user.UserId}"

        await self.session.commit()
        await self.session.refresh(customer)
        return customer

    async def get_customer(
        self, customer_id: int, current_user: User
    ) -> Customer:
        """
        Retrieves a single active customer by CustomerId with branch jurisdiction enforcement.
        Global read roles (OWNER, ADMIN, IT SUPPORT, ACCOUNT, ACCOUNT HEAD) can access any branch;
        all other roles are restricted to current_user.BranchId.
        """
        customer = await self.customer_repo.get_by_id(customer_id)
        if not customer or customer.isdeleted == "1":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Customer with ID {customer_id} not found.",
            )

        if not self._can_read_all_branches(current_user):
            if customer.BranchId != current_user.BranchId:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: You do not have permission to view customers outside your branch.",
                )

        return customer

    async def search_customers(
        self,
        current_user: User,
        *,
        name: Optional[str] = None,
        mobile: Optional[str] = None,
        pan: Optional[str] = None,
        customer_code: Optional[str] = None,
        branch_id: Optional[int] = None,
        offset: int = 0,
        limit: int = 20,
    ) -> Sequence[Customer]:
        """
        Searches active customers with bounded pagination and server-enforced branch scoping.
        Non-global roles are strictly pinned to current_user.BranchId regardless of query input.
        """
        if self._can_read_all_branches(current_user):
            effective_branch_id = branch_id
        else:
            effective_branch_id = current_user.BranchId

        return await self.customer_repo.search_customers(
            name=name,
            mobile=mobile,
            pan=pan,
            customer_code=customer_code,
            branch_id=effective_branch_id,
            offset=offset,
            limit=limit,
        )


