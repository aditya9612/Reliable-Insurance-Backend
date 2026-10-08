"""
FastAPI Router for Phase 13 Block A — Vehicle RC & External Integrations.
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.dependencies import get_db, get_current_user
from app.models.user import User
from app.providers import get_vehicle_rc_provider, resolve_vehicle_rc_provider
from app.providers.base import VehicleRCProvider
from app.schemas.integrations import VehicleRCLookupRequest, VehicleRCLookupResponse
from app.services.vehicle_rc_service import VehicleRCService

router = APIRouter()


@router.get(
    "/vehicle-rc/providers",
    status_code=status.HTTP_200_OK,
    summary="List Supported Vehicle RC Providers",
)
async def list_vehicle_rc_providers(
    current_user: User = Depends(get_current_user),
) -> dict:
    """Return configured default and all available Vehicle RC provider adapters."""
    return {
        "default_provider": settings.RC_PROVIDER_TYPE,
        "available_providers": [
            {"id": "mock", "name": "Deterministic Mock RC Provider"},
            {"id": "apiclub", "name": "APIClub v1 RC Info Adapter"},
            {"id": "signzy", "name": "Signzy v3 Detailed Vehicle Search Adapter"},
            {"id": "attestr", "name": "Attestr CheckX v1 Public RC Adapter"},
        ],
    }


@router.post(
    "/vehicle-rc/lookup",
    response_model=VehicleRCLookupResponse,
    status_code=status.HTTP_200_OK,
    summary="Lookup Vehicle Registration (RC) Details",
    description=(
        "Queries vehicle registration details using the 3-Tier Cascade: "
        "Tier 1: Internal System -> Tier 2: Local Cache -> Tier 3: External Provider. "
        "Advisory pre-fill data lookup; failures do not block policy issuance."
    ),
)
async def lookup_vehicle_rc(
    payload: VehicleRCLookupRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    provider: VehicleRCProvider = Depends(get_vehicle_rc_provider),
) -> VehicleRCLookupResponse:
    """Lookup vehicle RC attributes with 3-tier fallback cascade."""
    active_provider = resolve_vehicle_rc_provider(payload.provider) if payload.provider else provider
    service = VehicleRCService(session, active_provider)
    return await service.lookup_vehicle_rc(
        registration_number=payload.registration_number,
        force_refresh=payload.force_refresh,
        requested_by=str(current_user.UserId or "SYSTEM"),
    )
