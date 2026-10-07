from typing import Optional, Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.base import BaseRepository
from app.models.master import (
    VehicleType,
    VehicleSubType,
    VehicleMake,
    VehicleModel,
    VehicleVariant,
    RTOMaster,
    InsuranceCompany,
)


class VehicleTypeRepository(BaseRepository[VehicleType]):
    """Data access repository for tbl_vehicle_type."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(VehicleType, session)

    async def get_by_name(self, name: str) -> Optional[VehicleType]:
        query = select(VehicleType).where(VehicleType.Veh_Type_Name == name)
        result = await self.session.execute(query)
        return result.scalars().first()


class VehicleSubTypeRepository(BaseRepository[VehicleSubType]):
    """Data access repository for tbl_vehicle_sub_type."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(VehicleSubType, session)

    async def list_by_type_id(self, veh_type_id: int) -> Sequence[VehicleSubType]:
        query = select(VehicleSubType).where(VehicleSubType.Veh_Type_ID == veh_type_id)
        result = await self.session.execute(query)
        return result.scalars().all()


class VehicleMakeRepository(BaseRepository[VehicleMake]):
    """Data access repository for tbl_vehicle_make."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(VehicleMake, session)

    async def list_active(self, offset: int = 0, limit: int = 100) -> Sequence[VehicleMake]:
        query = select(VehicleMake).where(VehicleMake.isdeleted == 0).offset(offset).limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all()


class VehicleModelRepository(BaseRepository[VehicleModel]):
    """Data access repository for tbl_vehicle_model."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(VehicleModel, session)

    async def list_by_make_id(self, make_id: int, offset: int = 0, limit: int = 100) -> Sequence[VehicleModel]:
        query = select(VehicleModel).where(
            VehicleModel.Make_ID == make_id,
            VehicleModel.isdeleted == 0
        ).offset(offset).limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all()


class VehicleVariantRepository(BaseRepository[VehicleVariant]):
    """Data access repository for tbl_vehicle_variants."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(VehicleVariant, session)

    async def list_by_model_id(self, model_id: int, offset: int = 0, limit: int = 100) -> Sequence[VehicleVariant]:
        query = select(VehicleVariant).where(
            VehicleVariant.Model_ID == model_id
        ).offset(offset).limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all()


class RTORepository(BaseRepository[RTOMaster]):
    """Data access repository for tbl_rto."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(RTOMaster, session)

    async def get_by_reg_code(self, reg_code: str) -> Optional[RTOMaster]:
        query = select(RTOMaster).where(
            RTOMaster.REG_code == reg_code,
            RTOMaster.isdeleted == 0
        )
        result = await self.session.execute(query)
        return result.scalars().first()

    async def list_active(self, offset: int = 0, limit: int = 100) -> Sequence[RTOMaster]:
        query = select(RTOMaster).where(RTOMaster.isdeleted == 0).offset(offset).limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all()


class InsuranceCompanyRepository(BaseRepository[InsuranceCompany]):
    """Data access repository for tbl_insurancecompany."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(InsuranceCompany, session)

    async def list_active(self, offset: int = 0, limit: int = 100) -> Sequence[InsuranceCompany]:
        query = select(InsuranceCompany).where(
            InsuranceCompany.isdeleted == "0",
            InsuranceCompany.LedgerMId != 0
        ).offset(offset).limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all()
