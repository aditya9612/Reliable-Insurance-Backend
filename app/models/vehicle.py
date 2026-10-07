from decimal import Decimal
from datetime import datetime, date
from typing import Optional
from sqlalchemy import Integer, String, Text, DateTime, Date, Double, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class VehicleDetails(Base):
    """
    Vehicle Asset Registry Model (Insured Motor Vehicle)
    Physical Table: tbl_vehicledetails
    Physical PK: CustVehId
    Verified Column Count: 32
    Physical Foreign Keys: 0 (Enforced at application layer)
    """
    __tablename__ = "tbl_vehicledetails"
    __table_args__ = {
        "mysql_charset": "utf8",
        "mysql_collate": "utf8_general_ci",
        "mysql_row_format": "DYNAMIC",
    }

    CustVehId: Mapped[int] = mapped_column("CustVehId", Integer, primary_key=True, autoincrement=True)
    CustomerId: Mapped[Optional[int]] = mapped_column("CustomerId", Integer, nullable=True)
    RegistrationNo: Mapped[Optional[str]] = mapped_column("RegistrationNo", String(255), nullable=True)
    ChaiseNo: Mapped[Optional[str]] = mapped_column("ChaiseNo", String(255), nullable=True)
    EngineNo: Mapped[Optional[str]] = mapped_column("EngineNo", String(500), nullable=True)
    MfgMonth: Mapped[Optional[str]] = mapped_column("MfgMonth", String(255), nullable=True)
    MfgYear: Mapped[Optional[str]] = mapped_column("MfgYear", String(255), nullable=True)
    Ex_ShowroomPrice: Mapped[Optional[str]] = mapped_column("Ex_ShowroomPrice", String(255), nullable=True)
    FuelTypeId: Mapped[Optional[int]] = mapped_column("FuelTypeId", Integer, nullable=True)
    Veh_Type_ID: Mapped[Optional[int]] = mapped_column("Veh_Type_ID", Integer, nullable=True)
    Veh_Sub_Type_ID: Mapped[Optional[int]] = mapped_column("Veh_Sub_Type_ID", Integer, nullable=True)
    Make_ID: Mapped[Optional[int]] = mapped_column("Make_ID", Integer, nullable=True)
    Model_ID: Mapped[Optional[int]] = mapped_column("Model_ID", Integer, nullable=True)
    Variant_ID: Mapped[Optional[int]] = mapped_column("Variant_ID", Integer, nullable=True)
    VehiclePurDate: Mapped[Optional[datetime]] = mapped_column("VehiclePurDate", DateTime, nullable=True)
    SeatsCapacity: Mapped[Optional[str]] = mapped_column("SeatsCapacity", String(255), nullable=True)
    EnginePower: Mapped[Optional[str]] = mapped_column("EnginePower", String(500), nullable=True)
    TransTonnageCapacity: Mapped[Optional[str]] = mapped_column("TransTonnageCapacity", String(255), nullable=True)
    VehicleWeight: Mapped[Optional[str]] = mapped_column("VehicleWeight", String(255), nullable=True)
    VehicleRegDate: Mapped[Optional[datetime]] = mapped_column("VehicleRegDate", DateTime, nullable=True)
    RTOId: Mapped[Optional[int]] = mapped_column("RTOId", Integer, nullable=True)
    BranchId: Mapped[Optional[int]] = mapped_column("BranchId", Integer, nullable=True)
    CorporateClientId: Mapped[Optional[int]] = mapped_column("CorporateClientId", Integer, nullable=True)
    CreateDate: Mapped[Optional[datetime]] = mapped_column("CreateDate", DateTime, nullable=True)
    CreatedUser: Mapped[Optional[str]] = mapped_column("CreatedUser", String(255), nullable=True)
    UpdatedDate: Mapped[Optional[datetime]] = mapped_column("UpdatedDate", DateTime, nullable=True)
    UpdatedUser: Mapped[Optional[str]] = mapped_column("UpdatedUser", String(255), nullable=True)
    Extra1: Mapped[Optional[str]] = mapped_column("Extra1", String(255), nullable=True)
    Extra2: Mapped[Optional[str]] = mapped_column("Extra2", String(255), nullable=True)
    isdeleted: Mapped[Optional[str]] = mapped_column("isdeleted", String(255), nullable=True)
    FinancialYear: Mapped[str] = mapped_column("FinancialYear", String(255), nullable=False)
    VehicleVariant: Mapped[Optional[str]] = mapped_column("VehicleVariant", String(255), nullable=True)
