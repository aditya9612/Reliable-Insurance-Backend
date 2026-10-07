from typing import Optional, List, Any
from fastapi import APIRouter, Depends, Query, Path, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db, get_current_user
from app.models.user import User
from app.services.master_service import MasterService
from app.schemas.master import (
    VehicleTypeResponse,
    VehicleSubTypeResponse,
    VehicleMakeResponse,
    VehicleModelResponse,
    VehicleVariantSummaryResponse,
    VehicleVariantDetailResponse,
    VariantRegionalPriceResponse,
    RTOResponse,
    InsuranceCompanyResponse,
    AddonExtraAmtResponse,
    ZeroDepResponse,
    PAToOwnerDriverResponse,
    TowingRateResponse,
    NCBSlabResponse,
    BranchResponse,
    StateResponse,
    DistrictResponse,
    BankResponse,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# BLOCK 1: Existing 7 Master APIs
# ---------------------------------------------------------------------------

@router.get(
    "/vehicle-types",
    response_model=List[VehicleTypeResponse],
    summary="List vehicle types",
    description="Returns list of motor vehicle category types.",
)
async def list_vehicle_types(
    for_quotation: bool = Query(False, description="Filter only quotation-enabled types"),
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> List[VehicleTypeResponse]:
    service = MasterService(session)
    types = await service.list_vehicle_types(for_quotation=for_quotation, offset=offset, limit=limit)
    return [VehicleTypeResponse.model_validate(t) for t in types]


@router.get(
    "/vehicle-types/{type_id}",
    response_model=VehicleTypeResponse,
    summary="Get vehicle type by ID",
)
async def get_vehicle_type(
    type_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> VehicleTypeResponse:
    service = MasterService(session)
    t = await service.get_vehicle_type(type_id)
    if not t:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle type not found")
    return VehicleTypeResponse.model_validate(t)


@router.get(
    "/vehicle-sub-types",
    response_model=List[VehicleSubTypeResponse],
    summary="List vehicle sub-types",
)
async def list_vehicle_sub_types(
    veh_type_id: Optional[int] = Query(None, description="Filter by parent Vehicle Type ID"),
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> List[VehicleSubTypeResponse]:
    service = MasterService(session)
    sub_types = await service.list_vehicle_sub_types(veh_type_id=veh_type_id, offset=offset, limit=limit)
    return [VehicleSubTypeResponse.model_validate(st) for st in sub_types]


@router.get(
    "/vehicle-sub-types/{sub_type_id}",
    response_model=VehicleSubTypeResponse,
    summary="Get vehicle sub-type by ID",
)
async def get_vehicle_sub_type(
    sub_type_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> VehicleSubTypeResponse:
    service = MasterService(session)
    st = await service.get_vehicle_sub_type(sub_type_id)
    if not st:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle sub-type not found")
    return VehicleSubTypeResponse.model_validate(st)


@router.get(
    "/makes",
    response_model=List[VehicleMakeResponse],
    summary="List vehicle makes",
)
async def list_vehicle_makes(
    category: Optional[str] = Query(None, description="Category filter (e.g. Car, Two_Wheeler, GCV, PCV, Bus)"),
    search: Optional[str] = Query(None, description="Make name prefix search"),
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> List[VehicleMakeResponse]:
    service = MasterService(session)
    makes = await service.list_vehicle_makes(category=category, search=search, offset=offset, limit=limit)
    return [VehicleMakeResponse.model_validate(m) for m in makes]


@router.get(
    "/makes/{make_id}",
    response_model=VehicleMakeResponse,
    summary="Get vehicle make by ID",
)
async def get_vehicle_make(
    make_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> VehicleMakeResponse:
    service = MasterService(session)
    m = await service.get_vehicle_make(make_id)
    if not m:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle make not found")
    return VehicleMakeResponse.model_validate(m)


@router.get(
    "/models",
    response_model=List[VehicleModelResponse],
    summary="List vehicle models",
)
async def list_vehicle_models(
    make_id: Optional[int] = Query(None, description="Filter by parent Make ID"),
    search: Optional[str] = Query(None, description="Model name prefix search"),
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> List[VehicleModelResponse]:
    service = MasterService(session)
    models = await service.list_vehicle_models(make_id=make_id, search=search, offset=offset, limit=limit)
    return [VehicleModelResponse.model_validate(m) for m in models]


@router.get(
    "/models/{model_id}",
    response_model=VehicleModelResponse,
    summary="Get vehicle model by ID",
)
async def get_vehicle_model(
    model_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> VehicleModelResponse:
    service = MasterService(session)
    m = await service.get_vehicle_model(model_id)
    if not m:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle model not found")
    return VehicleModelResponse.model_validate(m)


@router.get(
    "/variants",
    response_model=List[VehicleVariantSummaryResponse],
    summary="List vehicle variants",
)
async def list_vehicle_variants(
    model_id: Optional[int] = Query(None, description="Filter by parent Model ID"),
    veh_type_id: Optional[int] = Query(None, description="Filter by Vehicle Type ID"),
    veh_sub_type_id: Optional[int] = Query(None, description="Filter by Vehicle Sub-Type ID"),
    search: Optional[str] = Query(None, description="Variant name search"),
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> List[VehicleVariantSummaryResponse]:
    service = MasterService(session)
    variants = await service.list_vehicle_variants(
        model_id=model_id,
        veh_type_id=veh_type_id,
        veh_sub_type_id=veh_sub_type_id,
        search=search,
        offset=offset,
        limit=limit,
    )
    return [VehicleVariantSummaryResponse.model_validate(v) for v in variants]


@router.get(
    "/variants/{variant_id}",
    response_model=VehicleVariantDetailResponse,
    summary="Get vehicle variant details (full 91 columns)",
)
async def get_vehicle_variant(
    variant_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> VehicleVariantDetailResponse:
    service = MasterService(session)
    v = await service.get_vehicle_variant(variant_id)
    if not v:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle variant not found")
    return VehicleVariantDetailResponse.model_validate(v)


@router.get(
    "/variants/{variant_id}/price",
    response_model=VariantRegionalPriceResponse,
    summary="Resolve regional ex-showroom price for variant",
    description="Resolves city/RTO ex-showroom price across the 19 regional pricing columns in tbl_vehicle_variants.",
)
async def resolve_variant_price(
    variant_id: int = Path(..., ge=1),
    city: str = Query(..., description="Target city or regional market (e.g. Mumbai, NewDelhi, Bangalore)"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> VariantRegionalPriceResponse:
    service = MasterService(session)
    res = await service.resolve_variant_price(variant_id=variant_id, city_or_rto=city)
    return VariantRegionalPriceResponse(**res)


@router.get(
    "/rtos",
    response_model=List[RTOResponse],
    summary="List RTOs",
)
async def list_rtos(
    search: Optional[str] = Query(None, description="Prefix search by REG_code, RTOLocation, or District"),
    state_id: Optional[int] = Query(None, description="Filter by State ID"),
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> List[RTOResponse]:
    service = MasterService(session)
    rtos = await service.list_rtos(search=search, state_id=state_id, offset=offset, limit=limit)
    return [RTOResponse.model_validate(r) for r in rtos]


@router.get(
    "/rtos/{rto_id}",
    response_model=RTOResponse,
    summary="Get RTO by ID",
)
async def get_rto(
    rto_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> RTOResponse:
    service = MasterService(session)
    r = await service.get_rto(rto_id)
    if not r:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="RTO not found")
    return RTOResponse.model_validate(r)


@router.get(
    "/insurance-companies",
    response_model=List[InsuranceCompanyResponse],
    summary="List insurance companies",
)
async def list_insurance_companies(
    search: Optional[str] = Query(None, description="Company name prefix search"),
    is_app_quotation_only: bool = Query(False, description="Filter only app quotation enabled"),
    veh_type_id: Optional[int] = Query(None, description="Filter by vehicle type eligibility"),
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> List[InsuranceCompanyResponse]:
    service = MasterService(session)
    companies = await service.list_insurance_companies(
        search=search,
        is_app_quotation_only=is_app_quotation_only,
        veh_type_id=veh_type_id,
        offset=offset,
        limit=limit,
    )
    return [InsuranceCompanyResponse.model_validate(c) for c in companies]


@router.get(
    "/insurance-companies/{company_id}",
    response_model=InsuranceCompanyResponse,
    summary="Get insurance company by ID",
)
async def get_insurance_company(
    company_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> InsuranceCompanyResponse:
    service = MasterService(session)
    c = await service.get_insurance_company(company_id)
    if not c:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Insurance company not found")
    return InsuranceCompanyResponse.model_validate(c)


# ---------------------------------------------------------------------------
# BLOCK 2: Underwriting / Rating Lookups
# ---------------------------------------------------------------------------

@router.get(
    "/addons",
    response_model=List[AddonExtraAmtResponse],
    summary="List underwriting add-on rates",
)
async def list_addons(
    insurance_company_id: Optional[int] = Query(None),
    veh_type_id: Optional[int] = Query(None),
    make_id: Optional[int] = Query(None),
    model_id: Optional[int] = Query(None),
    age: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> List[AddonExtraAmtResponse]:
    service = MasterService(session)
    addons = await service.list_addons(
        insurance_company_id=insurance_company_id,
        veh_type_id=veh_type_id,
        make_id=make_id,
        model_id=model_id,
        age=age,
    )
    return [AddonExtraAmtResponse.model_validate(a) for a in addons]


@router.get(
    "/zero-dep-rates",
    response_model=List[ZeroDepResponse],
    summary="List Zero-Depreciation rates",
)
async def list_zero_dep_rates(
    insurance_company_id: Optional[int] = Query(None),
    make_id: Optional[int] = Query(None),
    model_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> List[ZeroDepResponse]:
    service = MasterService(session)
    rates = await service.list_zero_dep_rates(
        insurance_company_id=insurance_company_id,
        make_id=make_id,
        model_id=model_id,
    )
    return [ZeroDepResponse.model_validate(r) for r in rates]


@router.get(
    "/pa-owner-driver",
    response_model=List[PAToOwnerDriverResponse],
    summary="List PA to Owner-Driver rates",
)
async def list_pa_owner_driver(
    insurance_company_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> List[PAToOwnerDriverResponse]:
    service = MasterService(session)
    rates = await service.list_pa_owner_driver_rates(insurance_company_id=insurance_company_id)
    return [PAToOwnerDriverResponse.model_validate(r) for r in rates]


@router.get(
    "/towing-rates",
    response_model=List[TowingRateResponse],
    summary="List towing charges slabs",
)
async def list_towing_rates(
    insurance_company_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> List[TowingRateResponse]:
    service = MasterService(session)
    rates = await service.list_towing_rates(insurance_company_id=insurance_company_id)
    return [TowingRateResponse.model_validate(r) for r in rates]


@router.get(
    "/ncb-slabs",
    response_model=List[NCBSlabResponse],
    summary="List standard NCB slabs",
)
async def list_ncb_slabs(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> List[NCBSlabResponse]:
    service = MasterService(session)
    slabs = await service.list_ncb_slabs()
    return [NCBSlabResponse(**s) for s in slabs]


# ---------------------------------------------------------------------------
# BLOCK 3: Organizational / Reference Masters
# ---------------------------------------------------------------------------

@router.get(
    "/branches",
    response_model=List[BranchResponse],
    summary="List branches",
)
async def list_branches(
    search: Optional[str] = Query(None, description="Prefix search by BranchName or BranchCode"),
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> List[BranchResponse]:
    service = MasterService(session)
    branches = await service.list_branches(search=search, offset=offset, limit=limit)
    return [BranchResponse.model_validate(b) for b in branches]


@router.get(
    "/branches/{branch_id}",
    response_model=BranchResponse,
    summary="Get branch by ID",
)
async def get_branch(
    branch_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> BranchResponse:
    service = MasterService(session)
    b = await service.get_branch(branch_id)
    if not b:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Branch not found")
    return BranchResponse.model_validate(b)


@router.get(
    "/states",
    response_model=List[StateResponse],
    summary="List states",
)
async def list_states(
    search: Optional[str] = Query(None, description="Prefix search by StateName"),
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> List[StateResponse]:
    service = MasterService(session)
    states = await service.list_states(search=search, offset=offset, limit=limit)
    return [StateResponse.model_validate(s) for s in states]


@router.get(
    "/states/{state_id}",
    response_model=StateResponse,
    summary="Get state by ID",
)
async def get_state(
    state_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> StateResponse:
    service = MasterService(session)
    s = await service.get_state(state_id)
    if not s:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="State not found")
    return StateResponse.model_validate(s)


@router.get(
    "/districts",
    response_model=List[DistrictResponse],
    summary="List districts",
)
async def list_districts(
    state_id: Optional[int] = Query(None, description="Filter by parent State ID"),
    search: Optional[str] = Query(None, description="Prefix search by DistrictName"),
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> List[DistrictResponse]:
    service = MasterService(session)
    districts = await service.list_districts(state_id=state_id, search=search, offset=offset, limit=limit)
    return [DistrictResponse.model_validate(d) for d in districts]


@router.get(
    "/districts/{district_id}",
    response_model=DistrictResponse,
    summary="Get district by ID",
)
async def get_district(
    district_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> DistrictResponse:
    service = MasterService(session)
    d = await service.get_district(district_id)
    if not d:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="District not found")
    return DistrictResponse.model_validate(d)


@router.get(
    "/banks",
    response_model=List[BankResponse],
    summary="List commercial banks",
)
async def list_banks(
    search: Optional[str] = Query(None, description="Prefix search by BankName"),
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> List[BankResponse]:
    service = MasterService(session)
    banks = await service.list_banks(search=search, offset=offset, limit=limit)
    return [BankResponse.model_validate(b) for b in banks]


@router.get(
    "/banks/{bank_id}",
    response_model=BankResponse,
    summary="Get bank by ID",
)
async def get_bank(
    bank_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> BankResponse:
    service = MasterService(session)
    b = await service.get_bank(bank_id)
    if not b:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bank not found")
    return BankResponse.model_validate(b)
