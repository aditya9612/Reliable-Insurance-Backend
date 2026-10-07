"""
Service for Phase 13 Block A — Vehicle RC & KYC Verification.
Coordinates the audited 3-Tier Lookup Cascade:
Tier 1: Internal System (sp_VehicleHistoryForRC)
Tier 2: Local Cache (sp_Select_vehiclenorc_details)
Tier 3: External Provider (APIClub / Signzy / Mock)
"""
from typing import Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.vehicle_rc import VehicleRCRepository
from app.providers.base import VehicleRCProvider
from app.schemas.integrations import VehicleRCData, VehicleRCLookupResponse


class VehicleRCService:
    """Service managing advisory vehicle registration lookups and cache persistence."""

    def __init__(self, session: AsyncSession, provider: VehicleRCProvider) -> None:
        self.session = session
        self.repo = VehicleRCRepository(session)
        self.provider = provider

    async def lookup_vehicle_rc(
        self,
        registration_number: str,
        force_refresh: bool = False,
        requested_by: str = "SYSTEM",
    ) -> VehicleRCLookupResponse:
        """
        Executes the 3-Tier Cascade:
        1. If not force_refresh: Check Internal System (prior policies/vehicles)
        2. If not force_refresh: Check Local RC Cache table (tbl_vehiclenorc_details)
        3. If not found in Tier 1 or Tier 2: Call External Provider, persist to Cache
        """
        clean_reg = registration_number.strip().upper().replace(" ", "").replace("-", "")

        # Tier 1: Check Internal Broker System
        if not force_refresh:
            sys_history = await self.repo.get_system_history(clean_reg)
            if sys_history:
                return VehicleRCLookupResponse(
                    source="INTERNAL_SYSTEM",
                    data=sys_history,
                )

        # Tier 2: Check Local RC Cache Table
        if not force_refresh:
            cached = await self.repo.get_cached_rc(clean_reg)
            if cached:
                cached_dto = VehicleRCData.model_validate(cached)
                return VehicleRCLookupResponse(
                    source="LOCAL_CACHE",
                    data=cached_dto,
                )

        # Tier 3: Call External Provider
        try:
            external_data = await self.provider.lookup_rc(clean_reg)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"External vehicle RC provider error: {str(e)}",
            )

        if not external_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Vehicle registration details not found for {clean_reg}",
            )

        # Persist into Local RC Cache table
        saved_entity = await self.repo.save_rc_details(external_data, created_by=requested_by)
        await self.session.commit()
        saved_dto = VehicleRCData.model_validate(saved_entity)

        return VehicleRCLookupResponse(
            source="EXTERNAL_PROVIDER",
            data=saved_dto,
        )
