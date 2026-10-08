from typing import Optional, Sequence, Dict, Any, List
from decimal import Decimal
from sqlalchemy import select, and_, or_, func, desc
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
    Branch,
    StateMaster,
    DistrictMaster,
    BankMaster,
    FuelType,
    Financier,
    Surveyor,
)
from app.models.quotation import (
    AddonExtraAmt,
    ZeroDep,
    ZeroDepNewAddonRate,
    PAToOwnerDriver,
    InsuranceCompanyWiseTowingChanges,
    AppODDiscount,
    QuotDamagePremium,
    InsuranceCompanyByVehicleType,
)


class VehicleTypeRepository(BaseRepository[VehicleType]):
    """Data access repository for tbl_vehicle_type."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(VehicleType, session)

    async def list_all(self, offset: int = 0, limit: int = 100) -> Sequence[VehicleType]:
        query = select(VehicleType).order_by(VehicleType.Veh_Type_ID).offset(offset).limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_by_name(self, name: str) -> Optional[VehicleType]:
        query = select(VehicleType).where(VehicleType.Veh_Type_Name == name)
        result = await self.session.execute(query)
        return result.scalars().first()

    async def list_for_quotation(self) -> Sequence[VehicleType]:
        query = select(VehicleType).where(VehicleType.IsAppQuotation == 1).order_by(VehicleType.Veh_Type_ID)
        result = await self.session.execute(query)
        return result.scalars().all()


class VehicleSubTypeRepository(BaseRepository[VehicleSubType]):
    """Data access repository for tbl_vehicle_sub_type."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(VehicleSubType, session)

    async def list_all(self, offset: int = 0, limit: int = 100) -> Sequence[VehicleSubType]:
        query = select(VehicleSubType).order_by(VehicleSubType.Veh_Sub_Type_ID).offset(offset).limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def list_by_type_id(self, veh_type_id: int) -> Sequence[VehicleSubType]:
        query = select(VehicleSubType).where(VehicleSubType.Veh_Type_ID == veh_type_id).order_by(VehicleSubType.Veh_Sub_Type_Name)
        result = await self.session.execute(query)
        return result.scalars().all()


class VehicleMakeRepository(BaseRepository[VehicleMake]):
    """Data access repository for tbl_vehicle_make."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(VehicleMake, session)

    async def list_active(
        self,
        category: Optional[str] = None,
        search: Optional[str] = None,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[VehicleMake]:
        conditions = [VehicleMake.isdeleted == 0]

        if category:
            cat_upper = category.strip().upper()
            if cat_upper in ("CAR", "PVTCAR", "PRIVATE CAR"):
                conditions.append(VehicleMake.PvtCar == "1")
            elif cat_upper in ("TWO_WHEELER", "2W", "TWOWHEELER"):
                conditions.append(VehicleMake.Two_Wheeler == "1")
            elif cat_upper in ("GCV", "GOODS"):
                conditions.append(VehicleMake.GCV == "1")
            elif cat_upper in ("PCV", "PASSENGER"):
                conditions.append(VehicleMake.PCV == "1")
            elif cat_upper in ("BUS",):
                conditions.append(VehicleMake.Bus == "1")
            elif cat_upper in ("3W", "THREE_WHEELER"):
                conditions.append(or_(VehicleMake.Three_Wheeler == "1", VehicleMake.Three_Wheeler_Pcv == "1"))
            elif cat_upper in ("MISC", "MISC_D"):
                conditions.append(VehicleMake.Misc_D == "1")

        if search:
            conditions.append(VehicleMake.Make_Name.like(f"{search.strip()}%"))

        query = select(VehicleMake).where(and_(*conditions)).order_by(VehicleMake.Make_Name).offset(offset).limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all()


class VehicleModelRepository(BaseRepository[VehicleModel]):
    """Data access repository for tbl_vehicle_model."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(VehicleModel, session)

    async def list_by_make_id(
        self,
        make_id: Optional[int] = None,
        search: Optional[str] = None,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[VehicleModel]:
        conditions = [VehicleModel.isdeleted == 0]
        if make_id is not None:
            conditions.append(VehicleModel.Make_ID == make_id)
        if search:
            conditions.append(VehicleModel.Model_Name.like(f"{search.strip()}%"))

        query = select(VehicleModel).where(and_(*conditions)).order_by(VehicleModel.Model_Name).offset(offset).limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all()


class VehicleVariantRepository(BaseRepository[VehicleVariant]):
    """Data access repository for tbl_vehicle_variants."""

    # 19 regional pricing columns prefix mapping
    REGIONAL_CITY_MAP: Dict[str, str] = {
        "MUMBAI": "ExMumbai",
        "NEWDELHI": "ExNewDelhi",
        "DELHI": "ExNewDelhi",
        "BANGALORE": "ExBangalore",
        "BENGALURU": "ExBangalore",
        "KOLKATTA": "ExKolkatta",
        "KOLKATA": "ExKolkatta",
        "AHMEDABAD": "ExAhmedabad",
        "CHANDIGARH": "ExChandigarh",
        "SHIMLA": "ExShimla",
        "FARIDABAD": "ExFaridabad",
        "LUCKNOW": "ExLucknow",
        "DEHRADUN": "ExDehradun",
        "KOHIMA": "ExKohima",
        "PATNA": "ExPatna",
        "CHENNAI": "ExChennai",
        "THIRUVANANTHAPURAM": "ExThiruvananthapuram",
        "KERALA": "ExThiruvananthapuram",
        "HYDERABAD": "ExHyderabad",
        "BHOPAL": "ExBhopal",
        "RAIPUR": "ExRaipur",
        "JAIPUR": "ExJaipur",
        "PANAJI": "ExPanaji",
        "GOA": "ExPanaji",
    }

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(VehicleVariant, session)

    async def list_by_model_id(self, model_id: int, offset: int = 0, limit: int = 100) -> Sequence[VehicleVariant]:
        return await self.list_by_filters(model_id=model_id, offset=offset, limit=limit)

    async def list_by_filters(
        self,
        model_id: Optional[int] = None,
        veh_type_id: Optional[int] = None,
        veh_sub_type_id: Optional[int] = None,
        search: Optional[str] = None,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[VehicleVariant]:
        conditions = []
        if model_id is not None:
            conditions.append(VehicleVariant.Model_ID == model_id)
        if veh_type_id is not None:
            conditions.append(VehicleVariant.Veh_Type_ID == veh_type_id)
        if veh_sub_type_id is not None:
            conditions.append(VehicleVariant.Veh_Sub_Type_ID == veh_sub_type_id)
        if search:
            conditions.append(VehicleVariant.Variance.like(f"{search.strip()}%"))

        query = select(VehicleVariant)
        if conditions:
            query = query.where(and_(*conditions))
        query = query.order_by(VehicleVariant.Variance).offset(offset).limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def resolve_regional_price(
        self,
        variant_id: int,
        city_or_rto: str,
    ) -> Dict[str, Any]:
        """Resolves city-specific ex-showroom pricing from the 91-column variant matrix."""
        variant = await self.get_by_id(variant_id)
        if not variant:
            return {
                "variant_id": variant_id,
                "variance": None,
                "market_region": city_or_rto,
                "ex_showroom_body_price": None,
                "ex_showroom_model_price": None,
                "ex_showroom_chasis_price": None,
                "effective_ex_showroom_price": Decimal("0.00"),
            }

        normalized_city = city_or_rto.strip().upper().replace(" ", "").replace("-", "")
        col_prefix = self.REGIONAL_CITY_MAP.get(normalized_city, "ExMumbai")

        body_price_val = getattr(variant, f"{col_prefix}_Body_Price", None)
        model_price_val = getattr(variant, f"{col_prefix}_Model_Price", None)
        chasis_price_val = getattr(variant, f"{col_prefix}_Chasis_Price", None)

        def _parse_dec(val: Optional[str]) -> Optional[Decimal]:
            if not val:
                return None
            try:
                cleaned = str(val).replace(",", "").strip()
                return Decimal(cleaned)
            except Exception:
                return None

        body_dec = _parse_dec(body_price_val)
        model_dec = _parse_dec(model_price_val)
        chasis_dec = _parse_dec(chasis_price_val)

        # Fallback hierarchy: Model Price -> Body Price -> Chasis Price
        effective = model_dec or body_dec or chasis_dec or Decimal("0.00")

        return {
            "variant_id": variant.Variant_ID,
            "variance": variant.Variance,
            "market_region": col_prefix.replace("Ex", ""),
            "ex_showroom_body_price": body_dec,
            "ex_showroom_model_price": model_dec,
            "ex_showroom_chasis_price": chasis_dec,
            "effective_ex_showroom_price": effective,
        }


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

    async def list_active(
        self,
        search: Optional[str] = None,
        state_id: Optional[int] = None,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[RTOMaster]:
        conditions = [or_(RTOMaster.isdeleted == 0, RTOMaster.isdeleted.is_(None))]
        if state_id is not None:
            conditions.append(or_(RTOMaster.StateId == state_id, RTOMaster.State_ID_FK == state_id))
        if search:
            s = f"{search.strip()}%"
            conditions.append(
                or_(
                    RTOMaster.REG_code.like(s),
                    RTOMaster.RTOLocation.like(s),
                    RTOMaster.District.like(s),
                )
            )

        query = select(RTOMaster).where(and_(*conditions)).order_by(RTOMaster.REG_code, RTOMaster.RTOLocation).offset(offset).limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all()


class InsuranceCompanyRepository(BaseRepository[InsuranceCompany]):
    """Data access repository for tbl_insurancecompany."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(InsuranceCompany, session)

    async def list_active(
        self,
        search: Optional[str] = None,
        is_app_quotation_only: bool = False,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[InsuranceCompany]:
        conditions = [
            InsuranceCompany.isdeleted == "0",
            InsuranceCompany.LedgerMId != 0,
        ]
        if is_app_quotation_only:
            conditions.append(InsuranceCompany.IsAppQuotation == "1")
        if search:
            conditions.append(InsuranceCompany.InsuranceCompany.like(f"{search.strip()}%"))

        query = select(InsuranceCompany).where(and_(*conditions)).order_by(InsuranceCompany.InsuranceCompany).offset(offset).limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def list_by_vehicle_type(self, veh_type_id: int) -> Sequence[InsuranceCompany]:
        """Returns active insurance companies configured for the given vehicle type."""
        # Query join with tbl_insurancecompanybyvehicletype
        query = (
            select(InsuranceCompany)
            .join(
                InsuranceCompanyByVehicleType,
                InsuranceCompany.InsuranceCompanyId == InsuranceCompanyByVehicleType.InsuranceCompanyId,
            )
            .where(
                InsuranceCompany.isdeleted == "0",
                InsuranceCompany.LedgerMId != 0,
                InsuranceCompanyByVehicleType.IsDelete == 0,
            )
        )
        if veh_type_id == 1:
            query = query.where(InsuranceCompanyByVehicleType.PVT_CAR == 1)
        elif veh_type_id == 2:
            query = query.where(InsuranceCompanyByVehicleType.GCV == 1)
        elif veh_type_id == 3:
            query = query.where(InsuranceCompanyByVehicleType.PCV == 1)
        elif veh_type_id == 4:
            query = query.where(InsuranceCompanyByVehicleType.Two_Wheeler == 1)
        elif veh_type_id == 6:
            query = query.where(InsuranceCompanyByVehicleType.Bus == 1)
        elif veh_type_id in (7, 8):
            query = query.where(InsuranceCompanyByVehicleType.Three_Wheeler == 1)

        query = query.order_by(InsuranceCompany.InsuranceCompany)
        result = await self.session.execute(query)
        return result.scalars().all()


# ---------------------------------------------------------------------------
# BLOCK 2: Underwriting / Rating Lookup Repositories
# ---------------------------------------------------------------------------

class AddonRepository:
    """Repository for querying Add-on and Zero-Dep rates."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_addons(
        self,
        insurance_company_id: Optional[int] = None,
        veh_type_id: Optional[int] = None,
        make_id: Optional[int] = None,
        model_id: Optional[int] = None,
        age: Optional[int] = None,
    ) -> Sequence[AddonExtraAmt]:
        conditions = [or_(AddonExtraAmt.IsDeleted == 0, AddonExtraAmt.IsDeleted.is_(None))]
        if insurance_company_id is not None:
            conditions.append(AddonExtraAmt.InsuranceCompanyId == insurance_company_id)
        if veh_type_id is not None:
            conditions.append(AddonExtraAmt.VehiceTypeId == veh_type_id)
        if make_id is not None and make_id > 0:
            conditions.append(or_(AddonExtraAmt.makeId == make_id, AddonExtraAmt.makeId == 0))
        if model_id is not None and model_id > 0:
            conditions.append(or_(AddonExtraAmt.ModelId == model_id, AddonExtraAmt.ModelId == 0))
        if age is not None:
            conditions.append(or_(AddonExtraAmt.Age == age, AddonExtraAmt.Age == 0))

        query = select(AddonExtraAmt).where(and_(*conditions)).order_by(AddonExtraAmt.ExtraAddonId)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def list_zero_dep_rates(
        self,
        insurance_company_id: Optional[int] = None,
        make_id: Optional[int] = None,
        model_id: Optional[int] = None,
    ) -> Sequence[ZeroDep]:
        conditions = [ZeroDep.Isdelete == 0]
        if insurance_company_id is not None:
            conditions.append(ZeroDep.InsuranceCompanyId == insurance_company_id)
        if make_id is not None:
            conditions.append(ZeroDep.Make_ID == make_id)
        if model_id is not None:
            conditions.append(ZeroDep.Model_Id == model_id)

        query = select(ZeroDep).where(and_(*conditions)).order_by(ZeroDep.ZerodepId)
        result = await self.session.execute(query)
        return result.scalars().all()


class PAToOwnerDriverRepository(BaseRepository[PAToOwnerDriver]):
    """Data access repository for tbl_patoownerdriver."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(PAToOwnerDriver, session)

    async def list_by_company(self, insurance_company_id: Optional[int] = None) -> Sequence[PAToOwnerDriver]:
        conditions = [or_(PAToOwnerDriver.IsDeleted == 0, PAToOwnerDriver.IsDeleted.is_(None))]
        if insurance_company_id is not None:
            conditions.append(PAToOwnerDriver.InsuranceCompanyId == insurance_company_id)

        query = select(PAToOwnerDriver).where(and_(*conditions)).order_by(PAToOwnerDriver.PAToOwnerDriverId)
        result = await self.session.execute(query)
        return result.scalars().all()


class TowingRateRepository(BaseRepository[InsuranceCompanyWiseTowingChanges]):
    """Data access repository for tbl_insurancecompanywisetowingchanges."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(InsuranceCompanyWiseTowingChanges, session)

    async def list_by_company(self, insurance_company_id: Optional[int] = None) -> Sequence[InsuranceCompanyWiseTowingChanges]:
        conditions = [or_(InsuranceCompanyWiseTowingChanges.IsDelete == 0, InsuranceCompanyWiseTowingChanges.IsDelete.is_(None))]
        if insurance_company_id is not None:
            conditions.append(InsuranceCompanyWiseTowingChanges.InsuranceCompanyId == insurance_company_id)

        query = select(InsuranceCompanyWiseTowingChanges).where(and_(*conditions)).order_by(InsuranceCompanyWiseTowingChanges.Id)
        result = await self.session.execute(query)
        return result.scalars().all()


class NCBRepository:
    """Repository for querying standard and insurer-configured NCB slabs."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_standard_ncb_slabs(self) -> List[Dict[str, Any]]:
        """Returns the standard IRDAI motor NCB slab ladder."""
        return [
            {"slab_code": "0", "ncb_percentage": Decimal("0.00"), "step_order": 1, "description": "0% NCB (New vehicle or claim in previous year)"},
            {"slab_code": "20", "ncb_percentage": Decimal("20.00"), "step_order": 2, "description": "20% NCB (1 claim-free year)"},
            {"slab_code": "25", "ncb_percentage": Decimal("25.00"), "step_order": 3, "description": "25% NCB (2 consecutive claim-free years)"},
            {"slab_code": "35", "ncb_percentage": Decimal("35.00"), "step_order": 4, "description": "35% NCB (3 consecutive claim-free years)"},
            {"slab_code": "45", "ncb_percentage": Decimal("45.00"), "step_order": 5, "description": "45% NCB (4 consecutive claim-free years)"},
            {"slab_code": "50", "ncb_percentage": Decimal("50.00"), "step_order": 6, "description": "50% NCB (5+ consecutive claim-free years — Maximum)"},
        ]


# ---------------------------------------------------------------------------
# BLOCK 3: Organizational / Reference Repositories
# ---------------------------------------------------------------------------

class BranchRepository(BaseRepository[Branch]):
    """Data access repository for tbl_branch."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Branch, session)

    async def list_active(
        self,
        search: Optional[str] = None,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[Branch]:
        conditions = [Branch.isdeleted == 0]
        if search:
            conditions.append(
                or_(
                    Branch.BranchName.like(f"{search.strip()}%"),
                    Branch.BranchCode.like(f"{search.strip()}%"),
                )
            )

        query = select(Branch).where(and_(*conditions)).order_by(Branch.BranchName).offset(offset).limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_by_code(self, branch_code: str) -> Optional[Branch]:
        query = select(Branch).where(Branch.BranchCode == branch_code, Branch.isdeleted == 0)
        result = await self.session.execute(query)
        return result.scalars().first()


class StateRepository(BaseRepository[StateMaster]):
    """Data access repository for tbl_state."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(StateMaster, session)

    async def list_active(
        self,
        search: Optional[str] = None,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[StateMaster]:
        conditions = [StateMaster.isdeleted == 0]
        if search:
            conditions.append(StateMaster.StateName.like(f"{search.strip()}%"))

        query = select(StateMaster).where(and_(*conditions)).order_by(StateMaster.StateName).offset(offset).limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all()


class DistrictRepository(BaseRepository[DistrictMaster]):
    """Data access repository for tbl_district."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(DistrictMaster, session)

    async def list_by_state(
        self,
        state_id: Optional[int] = None,
        search: Optional[str] = None,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[DistrictMaster]:
        conditions = [DistrictMaster.isdeleted == 0]
        if state_id is not None:
            conditions.append(DistrictMaster.StateID == state_id)
        if search:
            conditions.append(DistrictMaster.DistrictName.like(f"{search.strip()}%"))

        query = select(DistrictMaster).where(and_(*conditions)).order_by(DistrictMaster.DistrictName).offset(offset).limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all()


class BankRepository(BaseRepository[BankMaster]):
    """Data access repository for tbl_bank."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(BankMaster, session)

    async def list_active(
        self,
        search: Optional[str] = None,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[BankMaster]:
        conditions = [BankMaster.isdeleted == 0]
        if search:
            conditions.append(BankMaster.BankName.like(f"{search.strip()}%"))

        query = select(BankMaster).where(and_(*conditions)).order_by(BankMaster.BankName).offset(offset).limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all()


class FuelTypeRepository(BaseRepository[FuelType]):
    """Data access repository for tbl_fueltype."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(FuelType, session)

    async def list_active(self, offset: int = 0, limit: int = 100) -> Sequence[FuelType]:
        query = select(FuelType).where(
            (FuelType.isdeleted == None) | (FuelType.isdeleted != "1")  # noqa: E711
        ).order_by(FuelType.FuelTypeId).offset(offset).limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_by_name(self, fuel_type: str) -> Optional[FuelType]:
        query = select(FuelType).where(
            FuelType.FuelType.ilike(fuel_type),
            (FuelType.isdeleted == None) | (FuelType.isdeleted != "1"),  # noqa: E711
        )
        result = await self.session.execute(query)
        return result.scalars().first()

    async def create_fuel_type(self, fuel_type: str) -> FuelType:
        item = FuelType(FuelType=fuel_type, isdeleted="0")
        self.session.add(item)
        await self.session.flush()
        return item


class FinancierRepository(BaseRepository[Financier]):
    """Data access repository for tbl_financier."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Financier, session)

    async def list_active(
        self,
        branch_id: Optional[int] = None,
        search: Optional[str] = None,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[Financier]:
        query = select(Financier).where(
            (Financier.isdeleted == None) | (Financier.isdeleted != "1")  # noqa: E711
        )
        if branch_id is not None:
            query = query.where(Financier.BranchId == branch_id)
        if search:
            query = query.where(Financier.FinancierName.ilike(f"%{search}%"))

        query = query.order_by(Financier.FinancierId).offset(offset).limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def create_financier(
        self,
        name: str,
        branch_id: Optional[int] = None,
        contact_no: Optional[str] = None,
        email_id: Optional[str] = None,
        address: Optional[str] = None,
    ) -> Financier:
        item = Financier(
            FinancierName=name,
            BranchId=branch_id,
            ContactNo=contact_no,
            EmailId=email_id,
            Address=address,
            isdeleted="0",
        )
        self.session.add(item)
        await self.session.flush()
        return item


class SurveyorRepository(BaseRepository[Surveyor]):
    """Data access repository for tbl_surveyor."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Surveyor, session)

    async def list_active(
        self,
        branch_id: Optional[int] = None,
        search: Optional[str] = None,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[Surveyor]:
        query = select(Surveyor).where(
            (Surveyor.isdeleted == None) | (Surveyor.isdeleted != "1")  # noqa: E711
        )
        if branch_id is not None:
            query = query.where(Surveyor.BranchId == branch_id)
        if search:
            s = f"%{search}%"
            query = query.where(Surveyor.SurveyorName.ilike(s) | Surveyor.LicenseNo.ilike(s))

        query = query.order_by(Surveyor.SurveyorId).offset(offset).limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_by_license(self, license_no: str) -> Optional[Surveyor]:
        query = select(Surveyor).where(
            Surveyor.LicenseNo == license_no,
            (Surveyor.isdeleted == None) | (Surveyor.isdeleted != "1"),  # noqa: E711
        )
        result = await self.session.execute(query)
        return result.scalars().first()
