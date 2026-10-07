"""
Repository for Phase 13 Block A — Vehicle RC & KYC Caching (tbl_vehiclenorc_details).
"""
from typing import Optional
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.integration import VehicleRCDetails
from app.models.vehicle import VehicleDetails
from app.models.transaction import Transaction
from app.models.customer import Customer
from app.repositories.base import BaseRepository
from app.schemas.integrations import VehicleRCData


class VehicleRCRepository(BaseRepository[VehicleRCDetails]):
    """Data-access repository for Vehicle RC Caching and System Vehicle History."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(VehicleRCDetails, session)

    async def get_cached_rc(self, registration_number: str) -> Optional[VehicleRCDetails]:
        """
        Queries local RC cache table tbl_vehiclenorc_details.
        Replaces sp_Select_vehiclenorc_details.
        """
        clean_reg = registration_number.strip().upper().replace(" ", "").replace("-", "")
        stmt = select(VehicleRCDetails).where(
            VehicleRCDetails.license_plate_RegNo == clean_reg
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_system_history(self, registration_number: str) -> Optional[VehicleRCData]:
        """
        Queries existing Reliable Assurance policy/vehicle database.
        Replaces sp_VehicleHistoryForRC.
        """
        clean_reg = registration_number.strip().upper().replace(" ", "").replace("-", "")
        stmt = (
            select(VehicleDetails, Transaction, Customer)
            .outerjoin(Transaction, Transaction.CustVehId == VehicleDetails.CustVehId)
            .outerjoin(Customer, Customer.CustomerId == VehicleDetails.CustomerId)
            .where(
                or_(
                    VehicleDetails.RegistrationNo == clean_reg,
                    VehicleDetails.RegistrationNo == registration_number,
                )
            )
            .order_by(Transaction.ExpiryDate.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        row = result.first()
        if not row or not row[0]:
            return None

        veh: VehicleDetails = row[0]
        tx: Optional[Transaction] = row[1]
        cust: Optional[Customer] = row[2]

        cust_name = ""
        if cust:
            parts = [cust.CustFName or "", cust.CustMName or "", cust.CustLName or ""]
            cust_name = " ".join(p for p in parts if p).strip()

        return VehicleRCData(
            request_id=f"SYS-{veh.CustVehId}",
            license_plate_RegNo=clean_reg,
            owner_name=cust_name or None,
            father_name=None,
            is_financed="YES" if getattr(tx, "BankId", None) else "NO",
            financer=str(getattr(tx, "BankName", "") or ""),
            present_address=getattr(cust, "ComAddrLine1", None),
            permanent_address=getattr(cust, "PermAddrLine1", None),
            insurance_company=str(getattr(tx, "InsuranceCompanyId", "") or ""),
            insurance_policy=getattr(tx, "PolicyNo", None),
            insurance_expiry=getattr(tx, "ExpiryDate", None),
            rc_class=str(getattr(veh, "VehicleTypeId", "")),
            category=str(getattr(veh, "Veh_Type_ID", "")),
            registration_date=getattr(veh, "RegDate", None),
            vehicle_age=None,
            pucc_upto=None,
            pucc_number=None,
            chassis_number=getattr(veh, "ChaiseNo", None),
            engine_number=getattr(veh, "EngineNo", None),
            fuel_type=getattr(veh, "FuelType", None),
            brand_name=getattr(veh, "Make", None),
            brand_model=getattr(veh, "Model", None),
            body_type=getattr(veh, "BodyType", None),
            cubic_capacity=str(getattr(veh, "CubicCapacity", "") or ""),
            gross_weight=str(getattr(veh, "GrossVehicleWeight", "") or ""),
            cylinders=None,
            color=None,
            norms=None,
            fit_up_to=None,
            manufacturing_date=str(getattr(veh, "MfgYear", "") or ""),
            manufacturing_date_formatted=str(getattr(veh, "MfgDate", "") or ""),
            rto_name=getattr(veh, "RTOLocation", None),
            latest_by=None,
            sleeper_capacity="0",
            standing_capacity="0",
            wheelbase=None,
            unladen_weight=None,
            noc_details=None,
            seating_capacity=str(getattr(veh, "SeatingCapacity", "") or ""),
            owner_count="1",
            tax_upto=None,
            tax_paid_upto=None,
            permit_number=None,
            permit_issue_date=None,
            permit_valid_from=None,
            permit_valid_upto=None,
            permit_type=None,
            national_permit_number=None,
            national_permit_upto=None,
            national_permit_issued_by=None,
            rc_status="ACTIVE",
            CreatedDate=getattr(veh, "CreatedDate", None),
            CreatedBy="RELIABLE_SYSTEM",
        )

    async def save_rc_details(self, data: VehicleRCData, created_by: str) -> VehicleRCDetails:
        """
        Inserts or updates local RC cache in tbl_vehiclenorc_details.
        Replaces sp_InsertRCAPIDetails.
        """
        clean_reg = data.license_plate_RegNo.strip().upper().replace(" ", "").replace("-", "")
        existing = await self.get_cached_rc(clean_reg)

        dumped = data.model_dump(exclude_unset=False)
        dumped["license_plate_RegNo"] = clean_reg
        dumped["CreatedBy"] = created_by

        if existing:
            for k, v in dumped.items():
                if hasattr(existing, k) and k != "VehRcId":
                    setattr(existing, k, v)
            await self.session.flush()
            return existing

        new_rec = VehicleRCDetails(**dumped)
        self.session.add(new_rec)
        await self.session.flush()
        return new_rec
