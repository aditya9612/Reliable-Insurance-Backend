from typing import Optional
from sqlalchemy import Integer, String, Text, Index, text
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class VehicleType(Base):
    """
    Motor Vehicle Category Master Model
    Physical Table: tbl_vehicle_type
    Physical PK: Veh_Type_ID
    Verified Column Count: 10
    Physical Foreign Keys: 0
    """
    __tablename__ = "tbl_vehicle_type"
    __table_args__ = {
        "mysql_charset": "utf8",
        "mysql_collate": "utf8_general_ci",
        "mysql_row_format": "DYNAMIC",
    }

    Veh_Type_ID: Mapped[int] = mapped_column("Veh_Type_ID", Integer, primary_key=True, autoincrement=True)
    Veh_Type_Name: Mapped[Optional[str]] = mapped_column("Veh_Type_Name", String(255), nullable=True)
    IsAppQuotation: Mapped[Optional[int]] = mapped_column("IsAppQuotation", Integer, nullable=True, server_default=text("0"))
    PolicyTypeSAIBA: Mapped[Optional[str]] = mapped_column("PolicyTypeSAIBA", String(200), nullable=True, server_default=text("'0'"))
    VantagePolicyType: Mapped[Optional[str]] = mapped_column("VantagePolicyType", String(200), nullable=True, server_default=text("'0'"))
    Comprehensive: Mapped[Optional[str]] = mapped_column("Comprehensive", String(200), nullable=True)
    TP: Mapped[Optional[str]] = mapped_column("TP", String(200), nullable=True)
    Saod: Mapped[Optional[str]] = mapped_column("Saod", String(200), nullable=True)
    VehicleType: Mapped[Optional[str]] = mapped_column("VehicleType", String(200), nullable=True)
    NatureOfUse: Mapped[Optional[str]] = mapped_column("NatureOfUse", String(200), nullable=True)


class VehicleSubType(Base):
    """
    Motor Vehicle Sub-Type Normalizer Master Model
    Physical Table: tbl_vehicle_sub_type
    Physical PK: Veh_Sub_Type_ID
    Verified Column Count: 3
    Physical Foreign Keys: 0
    """
    __tablename__ = "tbl_vehicle_sub_type"
    __table_args__ = (
        Index("tbl_Vehicle_Type", "Veh_Type_ID"),
        {
            "mysql_charset": "utf8",
            "mysql_collate": "utf8_general_ci",
            "mysql_row_format": "DYNAMIC",
        },
    )

    Veh_Sub_Type_ID: Mapped[int] = mapped_column("Veh_Sub_Type_ID", Integer, primary_key=True, autoincrement=True)
    Veh_Sub_Type_Name: Mapped[Optional[str]] = mapped_column("Veh_Sub_Type_Name", String(255), nullable=True)
    Veh_Type_ID: Mapped[Optional[int]] = mapped_column("Veh_Type_ID", Integer, nullable=True)


class VehicleMake(Base):
    """
    Motor Vehicle Manufacturer / Make Master Model
    Physical Table: tbl_vehicle_make
    Physical PK: Make_ID
    Verified Column Count: 12
    Physical Foreign Keys: 0
    """
    __tablename__ = "tbl_vehicle_make"
    __table_args__ = {
        "mysql_charset": "utf8",
        "mysql_collate": "utf8_general_ci",
        "mysql_row_format": "DYNAMIC",
    }

    Make_ID: Mapped[int] = mapped_column("Make_ID", Integer, primary_key=True, autoincrement=True)
    Make_Name: Mapped[Optional[str]] = mapped_column("Make_Name", String(255), nullable=True)
    R_Make_ID: Mapped[Optional[int]] = mapped_column("R_Make_ID", Integer, nullable=True)
    GCV: Mapped[Optional[str]] = mapped_column("GCV", String(255), nullable=True)
    Misc_D: Mapped[Optional[str]] = mapped_column("Misc_D", String(255), nullable=True)
    PCV: Mapped[Optional[str]] = mapped_column("PCV", String(255), nullable=True)
    PvtCar: Mapped[Optional[str]] = mapped_column("PvtCar", String(255), nullable=True)
    Two_Wheeler: Mapped[Optional[str]] = mapped_column("Two_Wheeler", String(255), nullable=True)
    Bus: Mapped[Optional[str]] = mapped_column("Bus", String(255), nullable=True)
    Three_Wheeler: Mapped[Optional[str]] = mapped_column("Three_Wheeler", String(255), nullable=True)
    Three_Wheeler_Pcv: Mapped[Optional[str]] = mapped_column("Three_Wheeler_Pcv", String(255), nullable=True)
    isdeleted: Mapped[int] = mapped_column("isdeleted", Integer, nullable=False, server_default=text("0"))


class VehicleModel(Base):
    """
    Motor Vehicle Model Master Model
    Physical Table: tbl_vehicle_model
    Physical PK: Model_ID
    Verified Column Count: 7
    Physical Foreign Keys: 0
    """
    __tablename__ = "tbl_vehicle_model"
    __table_args__ = (
        Index("tbl_Vehicle_Make", "Make_ID"),
        {
            "mysql_charset": "utf8",
            "mysql_collate": "utf8_general_ci",
            "mysql_row_format": "DYNAMIC",
        },
    )

    Model_ID: Mapped[int] = mapped_column("Model_ID", Integer, primary_key=True, autoincrement=True)
    Make_ID: Mapped[Optional[int]] = mapped_column("Make_ID", Integer, nullable=True)
    Model_Name: Mapped[Optional[str]] = mapped_column("Model_Name", String(255), nullable=True)
    R_Make_ID: Mapped[Optional[int]] = mapped_column("R_Make_ID", Integer, nullable=True)
    Type: Mapped[Optional[int]] = mapped_column("Type", Integer, nullable=True)
    SegmentId: Mapped[int] = mapped_column("SegmentId", Integer, nullable=False)
    isdeleted: Mapped[int] = mapped_column("isdeleted", Integer, nullable=False, server_default=text("0"))


class VehicleVariant(Base):
    """
    Motor Vehicle Variant Specification and Pricing Catalog Model
    Physical Table: tbl_vehicle_variants
    Physical PK: Variant_ID
    Verified Column Count: 91
    Physical Foreign Keys: 0
    """
    __tablename__ = "tbl_vehicle_variants"
    __table_args__ = (
        Index("tbl_Vehicle_Model", "Model_ID"),
        Index("tbl_vehicle_sub_type", "Veh_Sub_Type_ID"),
        Index("tbl_vehicle_type", "Veh_Type_ID"),
        {
            "mysql_charset": "utf8",
            "mysql_collate": "utf8_general_ci",
            "mysql_row_format": "DYNAMIC",
        },
    )

    # Core Vehicle Attributes (1-28)
    Variant_ID: Mapped[int] = mapped_column("Variant_ID", Integer, primary_key=True, autoincrement=True)
    Veh_Type_ID: Mapped[Optional[int]] = mapped_column("Veh_Type_ID", Integer, nullable=True)
    Veh_Sub_Type_ID: Mapped[Optional[int]] = mapped_column("Veh_Sub_Type_ID", Integer, nullable=True)
    Model_ID: Mapped[Optional[int]] = mapped_column("Model_ID", Integer, nullable=True)
    Make_Tac_Code: Mapped[Optional[str]] = mapped_column("Make_Tac_Code", String(255), nullable=True)
    Model_Tac_Code: Mapped[Optional[str]] = mapped_column("Model_Tac_Code", String(255), nullable=True)
    Variance: Mapped[Optional[str]] = mapped_column("Variance", String(255), nullable=True)
    Tac_Code: Mapped[Optional[str]] = mapped_column("Tac_Code", String(255), nullable=True)
    Wheels: Mapped[Optional[str]] = mapped_column("Wheels", String(255), nullable=True)
    Manufacturing_Year: Mapped[Optional[str]] = mapped_column("Manufacturing_Year", String(255), nullable=True)
    Operated_By: Mapped[Optional[str]] = mapped_column("Operated_By", String(255), nullable=True)
    Amp: Mapped[Optional[str]] = mapped_column("Amp", String(255), nullable=True)
    CC: Mapped[Optional[str]] = mapped_column("CC", String(255), nullable=True)
    Unit_Name: Mapped[Optional[str]] = mapped_column("Unit_Name", String(255), nullable=True)
    Battery_Manufacturer: Mapped[Optional[str]] = mapped_column("Battery_Manufacturer", String(255), nullable=True)
    Gross_Weight: Mapped[Optional[str]] = mapped_column("Gross_Weight", String(255), nullable=True)
    Seating_Capacity: Mapped[Optional[str]] = mapped_column("Seating_Capacity", String(255), nullable=True)
    Carrying_Capacity: Mapped[Optional[str]] = mapped_column("Carrying_Capacity", String(255), nullable=True)
    Body_Type: Mapped[Optional[str]] = mapped_column("Body_Type", String(255), nullable=True)
    Min_Seating_Capacity: Mapped[Optional[str]] = mapped_column("Min_Seating_Capacity", String(255), nullable=True)
    Max_Seating_Capacity: Mapped[Optional[str]] = mapped_column("Max_Seating_Capacity", String(255), nullable=True)
    Min_carrying_Capacity: Mapped[Optional[str]] = mapped_column("Min_carrying_Capacity", String(255), nullable=True)
    Max_carrying_Capacity: Mapped[Optional[str]] = mapped_column("Max_carrying_Capacity", String(255), nullable=True)
    Is_In_Black_Listed: Mapped[Optional[str]] = mapped_column("Is_In_Black_Listed", String(255), nullable=True)
    IsObsolete: Mapped[Optional[str]] = mapped_column("IsObsolete", String(255), nullable=True)
    IsImported: Mapped[Optional[str]] = mapped_column("IsImported", String(255), nullable=True)
    Vehicle_Segment_Name: Mapped[Optional[str]] = mapped_column("Vehicle_Segment_Name", String(255), nullable=True)
    COM_Segment: Mapped[Optional[str]] = mapped_column("COM_Segment", String(255), nullable=True)

    # Regional Ex-Showroom Price Matrix (29-85)
    ExMumbai_Body_Price: Mapped[Optional[str]] = mapped_column("ExMumbai_Body_Price", String(255), nullable=True)
    ExMumbai_Model_Price: Mapped[Optional[str]] = mapped_column("ExMumbai_Model_Price", String(255), nullable=True)
    ExMumbai_Chasis_Price: Mapped[Optional[str]] = mapped_column("ExMumbai_Chasis_Price", String(255), nullable=True)
    ExNewDelhi_Body_Price: Mapped[Optional[str]] = mapped_column("ExNewDelhi_Body_Price", String(255), nullable=True)
    ExNewDelhi_Model_Price: Mapped[Optional[str]] = mapped_column("ExNewDelhi_Model_Price", String(255), nullable=True)
    ExNewDelhi_Chasis_Price: Mapped[Optional[str]] = mapped_column("ExNewDelhi_Chasis_Price", String(255), nullable=True)
    ExBangalore_Body_Price: Mapped[Optional[str]] = mapped_column("ExBangalore_Body_Price", String(255), nullable=True)
    ExBangalore_Model_Price: Mapped[Optional[str]] = mapped_column("ExBangalore_Model_Price", String(255), nullable=True)
    ExBangalore_Chasis_Price: Mapped[Optional[str]] = mapped_column("ExBangalore_Chasis_Price", String(255), nullable=True)
    ExKolkatta_Body_Price: Mapped[Optional[str]] = mapped_column("ExKolkatta_Body_Price", String(255), nullable=True)
    ExKolkatta_Model_Price: Mapped[Optional[str]] = mapped_column("ExKolkatta_Model_Price", String(255), nullable=True)
    ExKolkatta_Chasis_Price: Mapped[Optional[str]] = mapped_column("ExKolkatta_Chasis_Price", String(255), nullable=True)
    ExAhmedabad_Body_Price: Mapped[Optional[str]] = mapped_column("ExAhmedabad_Body_Price", String(255), nullable=True)
    ExAhmedabad_Model_Price: Mapped[Optional[str]] = mapped_column("ExAhmedabad_Model_Price", String(255), nullable=True)
    ExAhmedabad_Chasis_Price: Mapped[Optional[str]] = mapped_column("ExAhmedabad_Chasis_Price", String(255), nullable=True)
    ExChandigarh_Body_Price: Mapped[Optional[str]] = mapped_column("ExChandigarh_Body_Price", String(255), nullable=True)
    ExChandigarh_Model_Price: Mapped[Optional[str]] = mapped_column("ExChandigarh_Model_Price", String(255), nullable=True)
    ExChandigarh_Chasis_Price: Mapped[Optional[str]] = mapped_column("ExChandigarh_Chasis_Price", String(255), nullable=True)
    ExShimla_Body_Price: Mapped[Optional[str]] = mapped_column("ExShimla_Body_Price", String(255), nullable=True)
    ExShimla_Model_Price: Mapped[Optional[str]] = mapped_column("ExShimla_Model_Price", String(255), nullable=True)
    ExShimla_Chasis_Price: Mapped[Optional[str]] = mapped_column("ExShimla_Chasis_Price", String(255), nullable=True)
    ExFaridabad_Body_Price: Mapped[Optional[str]] = mapped_column("ExFaridabad_Body_Price", String(255), nullable=True)
    ExFaridabad_Model_Price: Mapped[Optional[str]] = mapped_column("ExFaridabad_Model_Price", String(255), nullable=True)
    ExFaridabad_Chasis_Price: Mapped[Optional[str]] = mapped_column("ExFaridabad_Chasis_Price", String(255), nullable=True)
    ExLucknow_Body_Price: Mapped[Optional[str]] = mapped_column("ExLucknow_Body_Price", String(255), nullable=True)
    ExLucknow_Model_Price: Mapped[Optional[str]] = mapped_column("ExLucknow_Model_Price", String(255), nullable=True)
    ExLucknow_Chasis_Price: Mapped[Optional[str]] = mapped_column("ExLucknow_Chasis_Price", String(255), nullable=True)
    ExDehradun_Body_Price: Mapped[Optional[str]] = mapped_column("ExDehradun_Body_Price", String(255), nullable=True)
    ExDehradun_Model_Price: Mapped[Optional[str]] = mapped_column("ExDehradun_Model_Price", String(255), nullable=True)
    ExDehradun_Chasis_Price: Mapped[Optional[str]] = mapped_column("ExDehradun_Chasis_Price", String(255), nullable=True)
    ExKohima_Body_Price: Mapped[Optional[str]] = mapped_column("ExKohima_Body_Price", String(255), nullable=True)
    ExKohima_Model_Price: Mapped[Optional[str]] = mapped_column("ExKohima_Model_Price", String(255), nullable=True)
    ExKohima_Chasis_Price: Mapped[Optional[str]] = mapped_column("ExKohima_Chasis_Price", String(255), nullable=True)
    ExPatna_Body_Price: Mapped[Optional[str]] = mapped_column("ExPatna_Body_Price", String(255), nullable=True)
    ExPatna_Model_Price: Mapped[Optional[str]] = mapped_column("ExPatna_Model_Price", String(255), nullable=True)
    ExPatna_Chasis_Price: Mapped[Optional[str]] = mapped_column("ExPatna_Chasis_Price", String(255), nullable=True)
    ExChennai_Body_Price: Mapped[Optional[str]] = mapped_column("ExChennai_Body_Price", String(255), nullable=True)
    ExChennai_Model_Price: Mapped[Optional[str]] = mapped_column("ExChennai_Model_Price", String(255), nullable=True)
    ExChennai_Chasis_Price: Mapped[Optional[str]] = mapped_column("ExChennai_Chasis_Price", String(255), nullable=True)
    ExThiruvananthapuram_Body_Price: Mapped[Optional[str]] = mapped_column("ExThiruvananthapuram_Body_Price", String(255), nullable=True)
    ExThiruvananthapuram_Model_Price: Mapped[Optional[str]] = mapped_column("ExThiruvananthapuram_Model_Price", String(255), nullable=True)
    ExThiruvananthapuram_Chasis_Price: Mapped[Optional[str]] = mapped_column("ExThiruvananthapuram_Chasis_Price", String(255), nullable=True)
    ExHyderabad_Body_Price: Mapped[Optional[str]] = mapped_column("ExHyderabad_Body_Price", String(255), nullable=True)
    ExHyderabad_Model_Price: Mapped[Optional[str]] = mapped_column("ExHyderabad_Model_Price", String(255), nullable=True)
    ExHyderabad_Chasis_Price: Mapped[Optional[str]] = mapped_column("ExHyderabad_Chasis_Price", String(255), nullable=True)
    ExBhopal_Body_Price: Mapped[Optional[str]] = mapped_column("ExBhopal_Body_Price", String(255), nullable=True)
    ExBhopal_Model_Price: Mapped[Optional[str]] = mapped_column("ExBhopal_Model_Price", String(255), nullable=True)
    ExBhopal_Chasis_Price: Mapped[Optional[str]] = mapped_column("ExBhopal_Chasis_Price", String(255), nullable=True)
    ExRaipur_Body_Price: Mapped[Optional[str]] = mapped_column("ExRaipur_Body_Price", String(255), nullable=True)
    ExRaipur_Model_Price: Mapped[Optional[str]] = mapped_column("ExRaipur_Model_Price", String(255), nullable=True)
    ExRaipur_Chasis_Price: Mapped[Optional[str]] = mapped_column("ExRaipur_Chasis_Price", String(255), nullable=True)
    ExJaipur_Body_Price: Mapped[Optional[str]] = mapped_column("ExJaipur_Body_Price", String(255), nullable=True)
    ExJaipur_Model_Price: Mapped[Optional[str]] = mapped_column("ExJaipur_Model_Price", String(255), nullable=True)
    ExJaipur_Chasis_Price: Mapped[Optional[str]] = mapped_column("ExJaipur_Chasis_Price", String(255), nullable=True)
    ExPanaji_Body_Price: Mapped[Optional[str]] = mapped_column("ExPanaji_Body_Price", String(255), nullable=True)
    ExPanaji_Model_Price: Mapped[Optional[str]] = mapped_column("ExPanaji_Model_Price", String(255), nullable=True)
    ExPanaji_Chasis_Price: Mapped[Optional[str]] = mapped_column("ExPanaji_Chasis_Price", String(255), nullable=True)

    # Metadata & Legacy Mapping References (86-91)
    Last_Updated_Date: Mapped[Optional[str]] = mapped_column("Last_Updated_Date", String(255), nullable=True)
    Mfg_BuildIn: Mapped[Optional[str]] = mapped_column("Mfg_BuildIn", String(255), nullable=True)
    ModelStatus: Mapped[Optional[str]] = mapped_column("ModelStatus", String(255), nullable=True)
    R_Make_ID: Mapped[Optional[int]] = mapped_column("R_Make_ID", Integer, nullable=True)
    R_Model_ID: Mapped[Optional[int]] = mapped_column("R_Model_ID", Integer, nullable=True)
    Make_Id: Mapped[int] = mapped_column("Make_Id", Integer, nullable=False, server_default=text("0"))


class RTOMaster(Base):
    """
    RTO Office and Registration District Master Model
    Physical Table: tbl_rto
    Physical PK: RTOId
    Verified Column Count: 10
    Physical Foreign Keys: 0
    """
    __tablename__ = "tbl_rto"
    __table_args__ = {
        "mysql_charset": "utf8",
        "mysql_collate": "utf8_general_ci",
        "mysql_row_format": "DYNAMIC",
    }

    RTOId: Mapped[int] = mapped_column("RTOId", Integer, primary_key=True, autoincrement=True)
    RTOLocation: Mapped[str] = mapped_column("RTOLocation", String(255), nullable=False)
    District: Mapped[str] = mapped_column("District", String(255), nullable=False)
    REG_code: Mapped[Optional[str]] = mapped_column("REG_code", String(255), nullable=True)
    State_ID_FK: Mapped[Optional[int]] = mapped_column("State_ID_FK", Integer, nullable=True)
    zone: Mapped[Optional[str]] = mapped_column("zone", String(255), nullable=True)
    ClusterId: Mapped[int] = mapped_column("ClusterId", Integer, nullable=False)
    isdeleted: Mapped[Optional[int]] = mapped_column("isdeleted", Integer, nullable=True)
    StateId: Mapped[Optional[int]] = mapped_column("StateId", Integer, nullable=True)
    RTOWithLocation: Mapped[Optional[str]] = mapped_column("RTOWithLocation", String(100), nullable=True, server_default=text("'0'"))


class InsuranceCompany(Base):
    """
    Underwriting Insurance Company Master Model
    Physical Table: tbl_insurancecompany
    Physical PK: InsuranceCompanyId
    Verified Column Count: 22
    Physical Foreign Keys: 0
    """
    __tablename__ = "tbl_insurancecompany"
    __table_args__ = {
        "mysql_charset": "utf8",
        "mysql_collate": "utf8_general_ci",
        "mysql_row_format": "DYNAMIC",
    }

    InsuranceCompanyId: Mapped[int] = mapped_column("InsuranceCompanyId", Integer, primary_key=True, autoincrement=True)
    InsuranceCompany: Mapped[Optional[str]] = mapped_column("InsuranceCompany", String(255), nullable=True)
    BranchName: Mapped[Optional[str]] = mapped_column("BranchName", String(255), nullable=True)
    BranchCode: Mapped[Optional[str]] = mapped_column("BranchCode", String(255), nullable=True)
    NCB: Mapped[str] = mapped_column("NCB", String(255), nullable=False)
    Cluster: Mapped[str] = mapped_column("Cluster", String(255), nullable=False)
    ZeroDeep: Mapped[str] = mapped_column("ZeroDeep", String(255), nullable=False)
    isdeleted: Mapped[Optional[str]] = mapped_column("isdeleted", String(255), nullable=True)
    IsAppQuotation: Mapped[str] = mapped_column("IsAppQuotation", String(255), nullable=False)
    MailId: Mapped[Optional[str]] = mapped_column("MailId", String(300), nullable=True)
    CompImgPath: Mapped[str] = mapped_column("CompImgPath", String(255), nullable=False)
    LedgerMId: Mapped[int] = mapped_column("LedgerMId", Integer, nullable=False)
    ShortName: Mapped[str] = mapped_column("ShortName", String(255), nullable=False)
    CreditDays: Mapped[int] = mapped_column("CreditDays", Integer, nullable=False, server_default=text("0"))
    PolicyNo: Mapped[str] = mapped_column("PolicyNo", String(500), nullable=False)
    len: Mapped[int] = mapped_column("len", Integer, nullable=False)
    InsurerSAIBA: Mapped[Optional[str]] = mapped_column("InsurerSAIBA", String(200), nullable=True, server_default=text("'0'"))
    InsurerBranchAutoCodeSAIBA: Mapped[Optional[str]] = mapped_column("InsurerBranchAutoCodeSAIBA", Text, nullable=True)
    PE_CompanyName: Mapped[Optional[str]] = mapped_column("PE_CompanyName", String(100), nullable=True, server_default=text("'-'"))
    VantageInsurance: Mapped[Optional[str]] = mapped_column("VantageInsurance", String(200), nullable=True, server_default=text("'0'"))
    VantageBranch: Mapped[Optional[str]] = mapped_column("VantageBranch", String(100), nullable=True, server_default=text("'0'"))
    VantageBranchAddress: Mapped[Optional[str]] = mapped_column("VantageBranchAddress", String(300), nullable=True, server_default=text("'0'"))


class Branch(Base):
    """
    Branch Office Organization Master Model
    Physical Table: tbl_branch
    Physical PK: BranchId
    Verified Column Count: 7
    Physical Foreign Keys: 0
    """
    __tablename__ = "tbl_branch"
    __table_args__ = (
        Index("tbl_branch_code_idx", "BranchCode"),
        {
            "mysql_charset": "utf8",
            "mysql_collate": "utf8_general_ci",
            "mysql_row_format": "DYNAMIC",
        },
    )

    BranchId: Mapped[int] = mapped_column("BranchId", Integer, primary_key=True, autoincrement=True)
    BranchCode: Mapped[Optional[str]] = mapped_column("BranchCode", String(50), nullable=True)
    BranchName: Mapped[Optional[str]] = mapped_column("BranchName", String(255), nullable=True)
    Address: Mapped[Optional[str]] = mapped_column("Address", String(500), nullable=True)
    ContactNo: Mapped[Optional[str]] = mapped_column("ContactNo", String(50), nullable=True)
    BranchTypeId: Mapped[Optional[int]] = mapped_column("BranchTypeId", Integer, nullable=True, server_default=text("1"))
    isdeleted: Mapped[int] = mapped_column("isdeleted", Integer, nullable=False, server_default=text("0"))


class StateMaster(Base):
    """
    State Geographic Reference Master Model
    Physical Table: tbl_state
    Physical PK: StateID
    Verified Column Count: 3
    Physical Foreign Keys: 0
    """
    __tablename__ = "tbl_state"
    __table_args__ = {
        "mysql_charset": "utf8",
        "mysql_collate": "utf8_general_ci",
        "mysql_row_format": "DYNAMIC",
    }

    StateID: Mapped[int] = mapped_column("StateID", Integer, primary_key=True, autoincrement=True)
    StateName: Mapped[str] = mapped_column("StateName", String(255), nullable=False)
    isdeleted: Mapped[int] = mapped_column("isdeleted", Integer, nullable=False, server_default=text("0"))


class DistrictMaster(Base):
    """
    District Geographic Reference Master Model
    Physical Table: tbl_district
    Physical PK: DistrictID
    Verified Column Count: 4
    Physical Foreign Keys: 0
    """
    __tablename__ = "tbl_district"
    __table_args__ = (
        Index("tbl_district_state_id_idx", "StateID"),
        {
            "mysql_charset": "utf8",
            "mysql_collate": "utf8_general_ci",
            "mysql_row_format": "DYNAMIC",
        },
    )

    DistrictID: Mapped[int] = mapped_column("DistrictID", Integer, primary_key=True, autoincrement=True)
    DistrictName: Mapped[str] = mapped_column("DistrictName", String(255), nullable=False)
    StateID: Mapped[int] = mapped_column("StateID", Integer, nullable=False)
    isdeleted: Mapped[int] = mapped_column("isdeleted", Integer, nullable=False, server_default=text("0"))


class BankMaster(Base):
    """
    Commercial Bank Reference Master Model
    Physical Table: tbl_bank
    Physical PK: BankId
    Verified Column Count: 3
    Physical Foreign Keys: 0
    """
    __tablename__ = "tbl_bank"
    __table_args__ = {
        "mysql_charset": "utf8",
        "mysql_collate": "utf8_general_ci",
        "mysql_row_format": "DYNAMIC",
    }

    BankId: Mapped[int] = mapped_column("BankId", Integer, primary_key=True, autoincrement=True)
    BankName: Mapped[str] = mapped_column("BankName", String(255), nullable=False)
    isdeleted: Mapped[int] = mapped_column("isdeleted", Integer, nullable=False, server_default=text("0"))

