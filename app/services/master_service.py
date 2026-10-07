from typing import Optional, Sequence, Dict, Any, List
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.master import (
    VehicleType,
    VehicleSubType,
    VehicleMake,
    VehicleModel,
    VehicleVariant,
    RTOMaster,
    InsuranceCompany,
    Branch,
    StateMaster,
    DistrictMaster,
    BankMaster,
)
from app.repositories.master import (
    VehicleTypeRepository,
    VehicleSubTypeRepository,
    VehicleMakeRepository,
    VehicleModelRepository,
    VehicleVariantRepository,
    RTORepository,
    InsuranceCompanyRepository,
    AddonRepository,
    PAToOwnerDriverRepository,
    TowingRateRepository,
    NCBRepository,
    BranchRepository,
    StateRepository,
    DistrictRepository,
    BankRepository,
)


class MasterService:
    """Service orchestrating master data lookups, hierarchy cascading, and regional pricing."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.vehicle_type_repo = VehicleTypeRepository(session)
        self.vehicle_sub_type_repo = VehicleSubTypeRepository(session)
        self.vehicle_make_repo = VehicleMakeRepository(session)
        self.vehicle_model_repo = VehicleModelRepository(session)
        self.vehicle_variant_repo = VehicleVariantRepository(session)
        self.rto_repo = RTORepository(session)
        self.insurance_company_repo = InsuranceCompanyRepository(session)
        self.addon_repo = AddonRepository(session)
        self.pa_repo = PAToOwnerDriverRepository(session)
        self.towing_repo = TowingRateRepository(session)
        self.ncb_repo = NCBRepository(session)
        self.branch_repo = BranchRepository(session)
        self.state_repo = StateRepository(session)
        self.district_repo = DistrictRepository(session)
        self.bank_repo = BankRepository(session)

    # -----------------------------------------------------------------------
    # BLOCK 1: Vehicle, RTO, and Insurer Masters
    # -----------------------------------------------------------------------

    async def list_vehicle_types(
        self,
        for_quotation: bool = False,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[VehicleType]:
        if for_quotation:
            return await self.vehicle_type_repo.list_for_quotation()
        return await self.vehicle_type_repo.list_all(offset=offset, limit=limit)

    async def get_vehicle_type(self, type_id: int) -> Optional[VehicleType]:
        return await self.vehicle_type_repo.get_by_id(type_id)

    async def list_vehicle_sub_types(
        self,
        veh_type_id: Optional[int] = None,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[VehicleSubType]:
        if veh_type_id is not None:
            return await self.vehicle_sub_type_repo.list_by_type_id(veh_type_id)
        return await self.vehicle_sub_type_repo.list_all(offset=offset, limit=limit)

    async def get_vehicle_sub_type(self, sub_type_id: int) -> Optional[VehicleSubType]:
        return await self.vehicle_sub_type_repo.get_by_id(sub_type_id)

    async def list_vehicle_makes(
        self,
        category: Optional[str] = None,
        search: Optional[str] = None,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[VehicleMake]:
        return await self.vehicle_make_repo.list_active(
            category=category, search=search, offset=offset, limit=limit
        )

    async def get_vehicle_make(self, make_id: int) -> Optional[VehicleMake]:
        return await self.vehicle_make_repo.get_by_id(make_id)

    async def list_vehicle_models(
        self,
        make_id: Optional[int] = None,
        search: Optional[str] = None,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[VehicleModel]:
        return await self.vehicle_model_repo.list_by_make_id(
            make_id=make_id, search=search, offset=offset, limit=limit
        )

    async def get_vehicle_model(self, model_id: int) -> Optional[VehicleModel]:
        return await self.vehicle_model_repo.get_by_id(model_id)

    async def list_vehicle_variants(
        self,
        model_id: Optional[int] = None,
        veh_type_id: Optional[int] = None,
        veh_sub_type_id: Optional[int] = None,
        search: Optional[str] = None,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[VehicleVariant]:
        return await self.vehicle_variant_repo.list_by_filters(
            model_id=model_id,
            veh_type_id=veh_type_id,
            veh_sub_type_id=veh_sub_type_id,
            search=search,
            offset=offset,
            limit=limit,
        )

    async def get_vehicle_variant(self, variant_id: int) -> Optional[VehicleVariant]:
        return await self.vehicle_variant_repo.get_by_id(variant_id)

    async def resolve_variant_price(
        self,
        variant_id: int,
        city_or_rto: str,
    ) -> Dict[str, Any]:
        return await self.vehicle_variant_repo.resolve_regional_price(
            variant_id=variant_id, city_or_rto=city_or_rto
        )

    async def list_rtos(
        self,
        search: Optional[str] = None,
        state_id: Optional[int] = None,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[RTOMaster]:
        return await self.rto_repo.list_active(
            search=search, state_id=state_id, offset=offset, limit=limit
        )

    async def get_rto(self, rto_id: int) -> Optional[RTOMaster]:
        return await self.rto_repo.get_by_id(rto_id)

    async def get_rto_by_reg_code(self, reg_code: str) -> Optional[RTOMaster]:
        return await self.rto_repo.get_by_reg_code(reg_code)

    async def list_insurance_companies(
        self,
        search: Optional[str] = None,
        is_app_quotation_only: bool = False,
        veh_type_id: Optional[int] = None,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[InsuranceCompany]:
        if veh_type_id is not None:
            return await self.insurance_company_repo.list_by_vehicle_type(veh_type_id)
        return await self.insurance_company_repo.list_active(
            search=search,
            is_app_quotation_only=is_app_quotation_only,
            offset=offset,
            limit=limit,
        )

    async def get_insurance_company(self, company_id: int) -> Optional[InsuranceCompany]:
        return await self.insurance_company_repo.get_by_id(company_id)

    # -----------------------------------------------------------------------
    # BLOCK 2: Underwriting / Rating Lookups
    # -----------------------------------------------------------------------

    async def list_addons(
        self,
        insurance_company_id: Optional[int] = None,
        veh_type_id: Optional[int] = None,
        make_id: Optional[int] = None,
        model_id: Optional[int] = None,
        age: Optional[int] = None,
    ) -> Sequence[Any]:
        return await self.addon_repo.list_addons(
            insurance_company_id=insurance_company_id,
            veh_type_id=veh_type_id,
            make_id=make_id,
            model_id=model_id,
            age=age,
        )

    async def list_zero_dep_rates(
        self,
        insurance_company_id: Optional[int] = None,
        make_id: Optional[int] = None,
        model_id: Optional[int] = None,
    ) -> Sequence[Any]:
        return await self.addon_repo.list_zero_dep_rates(
            insurance_company_id=insurance_company_id,
            make_id=make_id,
            model_id=model_id,
        )

    async def list_pa_owner_driver_rates(
        self,
        insurance_company_id: Optional[int] = None,
    ) -> Sequence[Any]:
        return await self.pa_repo.list_by_company(insurance_company_id=insurance_company_id)

    async def list_towing_rates(
        self,
        insurance_company_id: Optional[int] = None,
    ) -> Sequence[Any]:
        return await self.towing_repo.list_by_company(insurance_company_id=insurance_company_id)

    async def list_ncb_slabs(self) -> List[Dict[str, Any]]:
        return await self.ncb_repo.list_standard_ncb_slabs()

    # -----------------------------------------------------------------------
    # BLOCK 3: Organizational / Reference Masters
    # -----------------------------------------------------------------------

    async def list_branches(
        self,
        search: Optional[str] = None,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[Branch]:
        return await self.branch_repo.list_active(search=search, offset=offset, limit=limit)

    async def get_branch(self, branch_id: int) -> Optional[Branch]:
        return await self.branch_repo.get_by_id(branch_id)

    async def list_states(
        self,
        search: Optional[str] = None,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[StateMaster]:
        return await self.state_repo.list_active(search=search, offset=offset, limit=limit)

    async def get_state(self, state_id: int) -> Optional[StateMaster]:
        return await self.state_repo.get_by_id(state_id)

    async def list_districts(
        self,
        state_id: Optional[int] = None,
        search: Optional[str] = None,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[DistrictMaster]:
        return await self.district_repo.list_by_state(
            state_id=state_id, search=search, offset=offset, limit=limit
        )

    async def get_district(self, district_id: int) -> Optional[DistrictMaster]:
        return await self.district_repo.get_by_id(district_id)

    async def list_banks(
        self,
        search: Optional[str] = None,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[BankMaster]:
        return await self.bank_repo.list_active(search=search, offset=offset, limit=limit)

    async def get_bank(self, bank_id: int) -> Optional[BankMaster]:
        return await self.bank_repo.get_by_id(bank_id)
