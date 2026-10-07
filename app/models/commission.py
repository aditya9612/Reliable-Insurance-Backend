from decimal import Decimal
from datetime import datetime, date
from typing import Optional
from sqlalchemy import Integer, String, Text, DateTime, Date, Double, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class FranchiseCommission(Base):
    """
    Franchise & Partner Commission Ledger Model
    Physical Table: tbl_franchisecommission
    Physical PK: FranchiseCommId
    Verified Column Count: 29
    Physical Foreign Keys: 0 (Enforced at application layer)
    """
    __tablename__ = "tbl_franchisecommission"
    __table_args__ = {
        "mysql_charset": "utf8",
        "mysql_collate": "utf8_general_ci",
        "mysql_row_format": "DYNAMIC",
    }

    FranchiseCommId: Mapped[int] = mapped_column("FranchiseCommId", Integer, primary_key=True, autoincrement=True)
    FranchiseDate: Mapped[Optional[datetime]] = mapped_column("FranchiseDate", DateTime, nullable=True)
    TransanctionId: Mapped[Optional[int]] = mapped_column("TransanctionId", Integer, nullable=True)
    FranchiseId: Mapped[Optional[int]] = mapped_column("FranchiseId", Integer, nullable=True)
    AgentId: Mapped[Optional[int]] = mapped_column("AgentId", Integer, nullable=True)
    tat: Mapped[Optional[Decimal]] = mapped_column("tat", Double(asdecimal=True), nullable=True)
    Franchisecomm: Mapped[Optional[Decimal]] = mapped_column("Franchisecomm", Double(asdecimal=True), nullable=True)
    FranchiseCommAmt: Mapped[Optional[Decimal]] = mapped_column("FranchiseCommAmt", Double(asdecimal=True), nullable=True)
    FranchiseTdsAmt: Mapped[Optional[Decimal]] = mapped_column("FranchiseTdsAmt", Double(asdecimal=True), nullable=True)
    FranchiseNetComm: Mapped[Optional[Decimal]] = mapped_column("FranchiseNetComm", Double(asdecimal=True), nullable=True)
    FCommissionPaid: Mapped[Optional[Decimal]] = mapped_column("FCommissionPaid", Double(asdecimal=True), nullable=True)
    isdeleted: Mapped[Optional[int]] = mapped_column("isdeleted", Integer, nullable=True)
    Franchisecomm_OD: Mapped[Optional[Decimal]] = mapped_column("Franchisecomm_OD", Double(asdecimal=True), nullable=True)
    FranchiseCommAmt_OD: Mapped[Optional[Decimal]] = mapped_column("FranchiseCommAmt_OD", Double(asdecimal=True), nullable=True)
    FranchiseTdsAmt_OD: Mapped[Optional[Decimal]] = mapped_column("FranchiseTdsAmt_OD", Double(asdecimal=True), nullable=True)
    FranchiseNetComm_OD: Mapped[Optional[Decimal]] = mapped_column("FranchiseNetComm_OD", Double(asdecimal=True), nullable=True)
    Franchisecomm_Net: Mapped[Optional[Decimal]] = mapped_column("Franchisecomm_Net", Double(asdecimal=True), nullable=True)
    FranchiseCommAmt_Net: Mapped[Optional[Decimal]] = mapped_column("FranchiseCommAmt_Net", Double(asdecimal=True), nullable=True)
    FranchiseTdsAmt_Net: Mapped[Optional[Decimal]] = mapped_column("FranchiseTdsAmt_Net", Double(asdecimal=True), nullable=True)
    FranchiseNetComm_Net: Mapped[Optional[Decimal]] = mapped_column("FranchiseNetComm_Net", Double(asdecimal=True), nullable=True)
    Franchisecomm_Extra: Mapped[Optional[Decimal]] = mapped_column("Franchisecomm_Extra", Double(asdecimal=True), nullable=True)
    FranchiseCommAmt_Extra: Mapped[Optional[Decimal]] = mapped_column("FranchiseCommAmt_Extra", Double(asdecimal=True), nullable=True)
    FranchiseTdsAmt_Extra: Mapped[Optional[Decimal]] = mapped_column("FranchiseTdsAmt_Extra", Double(asdecimal=True), nullable=True)
    FranchiseNetComm_Extra: Mapped[Optional[Decimal]] = mapped_column("FranchiseNetComm_Extra", Double(asdecimal=True), nullable=True)
    ProfitofNetCommision: Mapped[Optional[Decimal]] = mapped_column("ProfitofNetCommision", Double(asdecimal=True), nullable=True)
    GridValidDate: Mapped[Optional[datetime]] = mapped_column("GridValidDate", DateTime, nullable=True)
    BrokerId: Mapped[int] = mapped_column("BrokerId", Integer, nullable=False)
    SelfDiscount: Mapped[Decimal] = mapped_column("SelfDiscount", Double(asdecimal=True), nullable=False)
    IntensiveAmount: Mapped[Decimal] = mapped_column("IntensiveAmount", Double(asdecimal=True), nullable=False)





class AgentCommissionPayment(Base):
    """
    Agent Commission Payment Settlement Model
    Physical Table: tbl_agentcommissionpayment
    Physical PK: AgentCommId
    Verified Column Count: 20
    Physical Foreign Keys: 0 (Enforced at application layer)
    """
    __tablename__ = "tbl_agentcommissionpayment"
    __table_args__ = {
        "mysql_charset": "utf8",
        "mysql_collate": "utf8_general_ci",
        "mysql_row_format": "DYNAMIC",
    }

    AgentCommId: Mapped[int] = mapped_column("AgentCommId", Integer, primary_key=True, autoincrement=True)
    FromDate: Mapped[Optional[datetime]] = mapped_column("FromDate", DateTime, nullable=True)
    ToDate: Mapped[Optional[datetime]] = mapped_column("ToDate", DateTime, nullable=True)
    TransanctionId: Mapped[Optional[int]] = mapped_column("TransanctionId", Integer, nullable=True)
    BranchName: Mapped[Optional[str]] = mapped_column("BranchName", String(255), nullable=True)
    AgentName: Mapped[Optional[str]] = mapped_column("AgentName", String(255), nullable=True)
    PremiumAmount: Mapped[Optional[Decimal]] = mapped_column("PremiumAmount", Double(asdecimal=True), nullable=True)
    NetCommission: Mapped[Optional[Decimal]] = mapped_column("NetCommission", Double(asdecimal=True), nullable=True)
    totalCommision: Mapped[Optional[Decimal]] = mapped_column("totalCommision", Double(asdecimal=True), nullable=True)
    AdvAmt: Mapped[Optional[Decimal]] = mapped_column("AdvAmt", Double(asdecimal=True), nullable=True)
    NetAmount: Mapped[Optional[Decimal]] = mapped_column("NetAmount", Double(asdecimal=True), nullable=True)
    PaymentStatus: Mapped[Optional[Decimal]] = mapped_column("PaymentStatus", Double(asdecimal=True), nullable=True)
    Narration: Mapped[Optional[str]] = mapped_column("Narration", String(255), nullable=True)
    Extra1: Mapped[Optional[str]] = mapped_column("Extra1", String(255), nullable=True)
    Extra2: Mapped[Optional[str]] = mapped_column("Extra2", String(255), nullable=True)
    isdeleted: Mapped[Optional[str]] = mapped_column("isdeleted", String(255), nullable=True)
    NetCommission_OD: Mapped[Optional[Decimal]] = mapped_column("NetCommission_OD", Double(asdecimal=True), nullable=True)
    NetCommission_Net: Mapped[Optional[Decimal]] = mapped_column("NetCommission_Net", Double(asdecimal=True), nullable=True)
    NetCommission_Extra: Mapped[Optional[Decimal]] = mapped_column("NetCommission_Extra", Double(asdecimal=True), nullable=True)
    TransDate: Mapped[Optional[datetime]] = mapped_column("TransDate", DateTime, nullable=True)





class CutNPayCommPayable(Base):
    """
    Cut & Pay Commission Deduction Ledger Model
    Physical Table: tbl_cutnpaycommpayable
    Physical PK: CutNPayCommPayId
    Verified Column Count: 11
    Physical Foreign Keys: 0 (Enforced at application layer)
    """
    __tablename__ = "tbl_cutnpaycommpayable"
    __table_args__ = {
        "mysql_charset": "utf8",
        "mysql_collate": "utf8_general_ci",
        "mysql_row_format": "DYNAMIC",
    }

    CutNPayCommPayId: Mapped[int] = mapped_column("CutNPayCommPayId", Integer, primary_key=True, autoincrement=True)
    TransactionId: Mapped[Optional[int]] = mapped_column("TransactionId", Integer, nullable=True)
    PolicyNo: Mapped[Optional[str]] = mapped_column("PolicyNo", String(255), nullable=True)
    CustomerId: Mapped[Optional[int]] = mapped_column("CustomerId", Integer, nullable=True)
    AgentId: Mapped[Optional[int]] = mapped_column("AgentId", Integer, nullable=True)
    SalesExId: Mapped[Optional[int]] = mapped_column("SalesExId", Integer, nullable=True)
    Balance: Mapped[Optional[Decimal]] = mapped_column("Balance", Double(asdecimal=True), nullable=True)
    CommPayable: Mapped[Optional[Decimal]] = mapped_column("CommPayable", Double(asdecimal=True), nullable=True)
    Flag: Mapped[Optional[str]] = mapped_column("Flag", String(255), nullable=True)
    Isdeleted: Mapped[Optional[int]] = mapped_column("Isdeleted", Integer, nullable=True)
    CreatedDate: Mapped[Optional[datetime]] = mapped_column("CreatedDate", DateTime, nullable=True)
