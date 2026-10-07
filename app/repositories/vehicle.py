from typing import Optional, Sequence
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.vehicle import VehicleDetails
from app.repositories.base import BaseRepository


class VehicleRepository(BaseRepository[VehicleDetails]):
    """
    Data-access repository for Vehicle entity (tbl_vehicledetails).
    No business logic, pure database access.
    Note: RegistrationNo and ChaiseNo are NOT globally unique in legacy data;
    lookups return collections or scope by FinancialYear.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(VehicleDetails, session)

    async def list_by_customer_id(
        self,
        customer_id: int,
        offset: int = 0,
        limit: int = 50,
    ) -> Sequence[VehicleDetails]:
        """Lookup vehicles associated with a given CustomerId."""
        query = (
            select(VehicleDetails)
            .where(
                VehicleDetails.CustomerId == customer_id,
                or_(VehicleDetails.isdeleted != "1", VehicleDetails.isdeleted.is_(None)),
            )
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_by_customer_id(self, customer_id: int) -> Sequence[VehicleDetails]:
        """Backward-compatible lookup for vehicles by CustomerId."""
        return await self.list_by_customer_id(customer_id=customer_id, offset=0, limit=100)

    async def search_by_registration(
        self,
        reg_no: str,
        branch_id: int = 0,
        offset: int = 0,
        limit: int = 50,
    ) -> Sequence[VehicleDetails]:
        """
        Search vehicles by RegistrationNo (exact or partial substring).
        Returns a collection because RegistrationNo is NOT globally unique across financial years.
        Scoped by branch_id if branch_id > 0 (0 returns all branches).
        """
        conditions = [
            VehicleDetails.RegistrationNo.ilike(f"%{reg_no}%"),
            or_(VehicleDetails.isdeleted != "1", VehicleDetails.isdeleted.is_(None)),
        ]
        if branch_id > 0:
            conditions.append(VehicleDetails.BranchId == branch_id)

        query = select(VehicleDetails).where(*conditions).offset(offset).limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def search_vehicles(
        self,
        *,
        reg_no: Optional[str] = None,
        financial_year: Optional[str] = None,
        branch_id: Optional[int] = None,
        offset: int = 0,
        limit: int = 50,
    ) -> Sequence[VehicleDetails]:
        """
        Composite vehicle search/list query supporting RegistrationNo (partial or exact),
        optional FinancialYear, and branch scoping while excluding soft-deleted rows.
        Respects legacy non-uniqueness of RegistrationNo across financial years.
        """
        conditions = [
            or_(VehicleDetails.isdeleted != "1", VehicleDetails.isdeleted.is_(None)),
        ]
        if branch_id is not None and branch_id > 0:
            conditions.append(VehicleDetails.BranchId == branch_id)

        if reg_no and reg_no.strip():
            conditions.append(VehicleDetails.RegistrationNo.ilike(f"%{reg_no.strip()}%"))

        if financial_year and financial_year.strip():
            conditions.append(VehicleDetails.FinancialYear == financial_year.strip())

        query = (
            select(VehicleDetails)
            .where(*conditions)
            .order_by(VehicleDetails.CustVehId.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def search_by_chassis(
        self,
        chassis_no: str,
        offset: int = 0,
        limit: int = 50,
    ) -> Sequence[VehicleDetails]:
        """
        Search vehicles by ChaiseNo (physical typo column).
        Returns a collection because ChaiseNo has high duplicate cardinality ('0', 'NA', renewals).
        """
        query = (
            select(VehicleDetails)
            .where(
                VehicleDetails.ChaiseNo.ilike(f"%{chassis_no}%"),
                or_(VehicleDetails.isdeleted != "1", VehicleDetails.isdeleted.is_(None)),
            )
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def check_registration_in_fy(
        self,
        reg_no: str,
        financial_year: str,
    ) -> Sequence[VehicleDetails]:
        """Check vehicles matching RegistrationNo within a specific FinancialYear."""
        query = select(VehicleDetails).where(
            VehicleDetails.RegistrationNo == reg_no,
            VehicleDetails.FinancialYear == financial_year,
            or_(VehicleDetails.isdeleted != "1", VehicleDetails.isdeleted.is_(None)),
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    # --- Backward-compatible single-entity lookup helpers ---

    async def get_by_registration_no(self, registration_no: str) -> Optional[VehicleDetails]:
        """Backward-compatible lookup for first vehicle by RegistrationNo."""
        query = select(VehicleDetails).where(VehicleDetails.RegistrationNo == registration_no)
        result = await self.session.execute(query)
        return result.scalars().first()

    async def get_by_chassis_no(self, chassis_no: str) -> Optional[VehicleDetails]:
        """Backward-compatible lookup for first vehicle by ChaiseNo."""
        query = select(VehicleDetails).where(VehicleDetails.ChaiseNo == chassis_no)
        result = await self.session.execute(query)
        return result.scalars().first()

    async def get_by_engine_no(self, engine_no: str) -> Optional[VehicleDetails]:
        """Backward-compatible lookup for first vehicle by EngineNo."""
        query = select(VehicleDetails).where(VehicleDetails.EngineNo == engine_no)
        result = await self.session.execute(query)
        return result.scalars().first()
