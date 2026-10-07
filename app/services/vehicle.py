from datetime import datetime
from typing import Optional, Sequence
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import is_global_admin_role, is_global_read_role
from app.models.vehicle import VehicleDetails
from app.models.user import User
from app.repositories.vehicle import VehicleRepository
from app.repositories.customer import CustomerRepository
from app.repositories.master import (
    VehicleTypeRepository,
    VehicleSubTypeRepository,
    VehicleMakeRepository,
    VehicleModelRepository,
    VehicleVariantRepository,
    RTORepository,
)
from app.schemas.vehicle import VehicleCreate, VehicleUpdate


class VehicleService:
    """
    Business service layer for Vehicle Asset Registry operations.
    Enforces customer ownership verification, FY-scoped registration uniqueness (sp_CheckRegistrationNo),
    master foreign key integrity checks, branch jurisdiction, and immutable field protection.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.vehicle_repo = VehicleRepository(session)
        self.customer_repo = CustomerRepository(session)
        self.veh_type_repo = VehicleTypeRepository(session)
        self.veh_sub_type_repo = VehicleSubTypeRepository(session)
        self.make_repo = VehicleMakeRepository(session)
        self.model_repo = VehicleModelRepository(session)
        self.variant_repo = VehicleVariantRepository(session)
        self.rto_repo = RTORepository(session)

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

    async def _validate_master_ids(
        self,
        veh_type_id: Optional[int] = None,
        veh_sub_type_id: Optional[int] = None,
        make_id: Optional[int] = None,
        model_id: Optional[int] = None,
        variant_id: Optional[int] = None,
        rto_id: Optional[int] = None,
    ) -> None:
        """Validates existence of foreign master entities in application layer (since DB has 0 physical FKs)."""
        if veh_type_id and veh_type_id > 0:
            if not await self.veh_type_repo.exists(veh_type_id):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Vehicle type ID {veh_type_id} does not exist",
                )
        if veh_sub_type_id and veh_sub_type_id > 0:
            if not await self.veh_sub_type_repo.exists(veh_sub_type_id):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Vehicle sub-type ID {veh_sub_type_id} does not exist",
                )
        if make_id and make_id > 0:
            if not await self.make_repo.exists(make_id):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Vehicle make ID {make_id} does not exist",
                )
        if model_id and model_id > 0:
            if not await self.model_repo.exists(model_id):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Vehicle model ID {model_id} does not exist",
                )
        if variant_id and variant_id > 0:
            if not await self.variant_repo.exists(variant_id):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Vehicle variant ID {variant_id} does not exist",
                )
        if rto_id and rto_id > 0:
            if not await self.rto_repo.exists(rto_id):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"RTO ID {rto_id} does not exist",
                )

    async def create_vehicle(
        self, customer_id: int, payload: VehicleCreate, current_user: User
    ) -> VehicleDetails:
        """
        Registers a new motor vehicle asset under a policyholder customer.
        - Enforces customer existence and active status.
        - Checks registration duplicate in current FinancialYear (sp_CheckRegistrationNo).
        - Validates master IDs (Veh_Type_ID, Make_ID, Model_ID, Variant_ID, RTOId).
        - Enforces branch scoping.
        """
        # 1. Verify customer exists
        customer = await self.customer_repo.get_by_id(customer_id)
        if not customer or customer.isdeleted == "1":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Customer with ID {customer_id} does not exist",
            )

        # 2. Branch scoping check
        is_admin = self._is_admin(current_user)
        if not is_admin and customer.BranchId != current_user.BranchId:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: You do not have access to customers from other branches",
            )

        # 3. Check duplicate RegistrationNo within the specified FinancialYear
        reg_no = payload.registration_no
        fy = payload.financial_year
        if reg_no:
            existing = await self.vehicle_repo.check_registration_in_fy(reg_no, fy)
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Vehicle with registration number '{reg_no}' already exists in financial year '{fy}'",
                )

        # 4. Master FK existence validation
        await self._validate_master_ids(
            veh_type_id=payload.veh_type_id,
            veh_sub_type_id=payload.veh_sub_type_id,
            make_id=payload.make_id,
            model_id=payload.model_id,
            variant_id=payload.variant_id,
            rto_id=payload.rto_id,
        )

        # 5. Resolve branch
        if is_admin:
            branch_id = payload.branch_id if payload.branch_id is not None else (customer.BranchId or current_user.BranchId or 0)
        else:
            branch_id = current_user.BranchId

        now = datetime.utcnow()
        username = current_user.UserName or f"user_{current_user.UserId}"

        # 6. Construct VehicleDetails entity
        vehicle = VehicleDetails(
            CustomerId=customer_id,
            RegistrationNo=reg_no,
            ChaiseNo=payload.chaise_no,
            EngineNo=payload.engine_no,
            MfgMonth=payload.mfg_month,
            MfgYear=payload.mfg_year,
            Ex_ShowroomPrice=payload.ex_showroom_price or "",
            FuelTypeId=payload.fuel_type_id,
            Veh_Type_ID=payload.veh_type_id,
            Veh_Sub_Type_ID=payload.veh_sub_type_id,
            Make_ID=payload.make_id,
            Model_ID=payload.model_id,
            Variant_ID=payload.variant_id,
            VehiclePurDate=payload.vehicle_pur_date,
            SeatsCapacity=payload.seats_capacity,
            EnginePower=payload.engine_power,
            TransTonnageCapacity=payload.trans_tonnage_capacity or "",
            VehicleWeight=payload.vehicle_weight,
            VehicleRegDate=payload.vehicle_reg_date or now,
            RTOId=payload.rto_id,
            BranchId=branch_id,
            CorporateClientId=payload.corporate_client_id if payload.corporate_client_id is not None else 1,
            CreateDate=now,
            CreatedUser=username,
            UpdatedDate=now,
            UpdatedUser=username,
            Extra1=payload.extra1,
            Extra2=payload.extra2,
            FinancialYear=fy,
            VehicleVariant=payload.vehicle_variant,
            isdeleted="0",
        )

        self.session.add(vehicle)
        await self.session.commit()
        await self.session.refresh(vehicle)
        return vehicle

    async def update_vehicle(
        self, customer_id: int, vehicle_id: int, payload: VehicleUpdate, current_user: User
    ) -> VehicleDetails:
        """
        Updates an existing vehicle asset following Sp_UpdateVehicleDetails allowlist.
        - Verifies customer and vehicle existence.
        - Verifies vehicle belongs to the given customer.
        - Enforces branch scoping.
        - Checks registration duplicate in current FY if registration number is updated.
        - Protects immutable fields (CustomerId, FinancialYear, BranchId, CorporateClientId, VehicleVariant, CreateDate, CreatedUser, isdeleted).
        """
        customer = await self.customer_repo.get_by_id(customer_id)
        if not customer or customer.isdeleted == "1":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Customer with ID {customer_id} does not exist",
            )

        vehicle = await self.vehicle_repo.get_by_id(vehicle_id)
        if not vehicle or vehicle.isdeleted == "1":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Vehicle with ID {vehicle_id} does not exist",
            )

        if vehicle.CustomerId != customer_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Vehicle {vehicle_id} does not belong to customer {customer_id}",
            )

        is_admin = self._is_admin(current_user)
        if not is_admin and vehicle.BranchId != current_user.BranchId:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: You do not have access to vehicles from other branches",
            )

        update_data = payload.model_dump(exclude_unset=True)

        # Duplicate registration check if RegistrationNo is changed
        if "registration_no" in update_data and update_data["registration_no"]:
            new_reg = update_data["registration_no"]
            if new_reg != vehicle.RegistrationNo:
                existing = await self.vehicle_repo.check_registration_in_fy(new_reg, vehicle.FinancialYear)
                conflict = any(v.CustVehId != vehicle_id for v in existing)
                if conflict:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Vehicle with registration number '{new_reg}' already exists in financial year '{vehicle.FinancialYear}'",
                    )

        # Master FK validations if any updated
        await self._validate_master_ids(
            veh_type_id=update_data.get("veh_type_id"),
            veh_sub_type_id=update_data.get("veh_sub_type_id"),
            make_id=update_data.get("make_id"),
            model_id=update_data.get("model_id"),
            variant_id=update_data.get("variant_id"),
            rto_id=update_data.get("rto_id"),
        )

        field_map = {
            "registration_no": "RegistrationNo",
            "chaise_no": "ChaiseNo",
            "engine_no": "EngineNo",
            "mfg_month": "MfgMonth",
            "mfg_year": "MfgYear",
            "ex_showroom_price": "Ex_ShowroomPrice",
            "fuel_type_id": "FuelTypeId",
            "veh_type_id": "Veh_Type_ID",
            "veh_sub_type_id": "Veh_Sub_Type_ID",
            "make_id": "Make_ID",
            "model_id": "Model_ID",
            "variant_id": "Variant_ID",
            "vehicle_pur_date": "VehiclePurDate",
            "seats_capacity": "SeatsCapacity",
            "engine_power": "EnginePower",
            "trans_tonnage_capacity": "TransTonnageCapacity",
            "vehicle_weight": "VehicleWeight",
            "vehicle_reg_date": "VehicleRegDate",
            "rto_id": "RTOId",
            "extra1": "Extra1",
            "extra2": "Extra2",
        }

        for pydantic_field, model_attr in field_map.items():
            if pydantic_field in update_data:
                setattr(vehicle, model_attr, update_data[pydantic_field])

        # Audit update
        vehicle.UpdatedDate = datetime.utcnow()
        vehicle.UpdatedUser = current_user.UserName or f"user_{current_user.UserId}"

        await self.session.commit()
        await self.session.refresh(vehicle)
        return vehicle

    async def list_customer_vehicles(
        self,
        customer_id: int,
        current_user: User,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[VehicleDetails]:
        """
        Lists all active vehicles belonging to a customer after verifying customer existence
        and branch jurisdiction.
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
                    detail="Access denied: Customer belongs to a different branch jurisdiction.",
                )

        return await self.vehicle_repo.list_by_customer_id(
            customer_id,
            offset=offset,
            limit=limit,
        )

    async def search_vehicles(
        self,
        current_user: User,
        *,
        reg_no: Optional[str] = None,
        financial_year: Optional[str] = None,
        branch_id: Optional[int] = None,
        offset: int = 0,
        limit: int = 20,
    ) -> Sequence[VehicleDetails]:
        """
        Searches active vehicle records across or within financial years.
        Preserves legacy non-uniqueness of RegistrationNo across FinancialYear values
        by returning a sequence of matching rows rather than scalar_one_or_none.
        Non-global roles are strictly restricted to current_user.BranchId.
        """
        if self._can_read_all_branches(current_user):
            effective_branch_id = branch_id
        else:
            effective_branch_id = current_user.BranchId

        return await self.vehicle_repo.search_vehicles(
            reg_no=reg_no,
            financial_year=financial_year,
            branch_id=effective_branch_id,
            offset=offset,
            limit=limit,
        )


