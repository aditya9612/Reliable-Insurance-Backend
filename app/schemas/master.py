from typing import Optional, Dict, Any, List
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# BLOCK 1: Core 7 Master Schemas
# ---------------------------------------------------------------------------

class VehicleTypeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    Veh_Type_ID: int
    Veh_Type_Name: Optional[str] = None
    IsAppQuotation: Optional[int] = 0
    PolicyTypeSAIBA: Optional[str] = None
    VantagePolicyType: Optional[str] = None
    Comprehensive: Optional[str] = None
    TP: Optional[str] = None
    Saod: Optional[str] = None
    VehicleType: Optional[str] = None
    NatureOfUse: Optional[str] = None


class VehicleSubTypeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    Veh_Sub_Type_ID: int
    Veh_Sub_Type_Name: Optional[str] = None
    Veh_Type_ID: Optional[int] = None


class VehicleMakeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    Make_ID: int
    Make_Name: Optional[str] = None
    R_Make_ID: Optional[int] = None
    GCV: Optional[str] = None
    Misc_D: Optional[str] = None
    PCV: Optional[str] = None
    PvtCar: Optional[str] = None
    Two_Wheeler: Optional[str] = None
    Bus: Optional[str] = None
    Three_Wheeler: Optional[str] = None
    Three_Wheeler_Pcv: Optional[str] = None
    isdeleted: int = 0


class VehicleModelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    Model_ID: int
    Make_ID: Optional[int] = None
    Model_Name: Optional[str] = None
    R_Make_ID: Optional[int] = None
    Type: Optional[int] = None
    SegmentId: int
    isdeleted: int = 0


class VehicleVariantSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    Variant_ID: int
    Veh_Type_ID: Optional[int] = None
    Veh_Sub_Type_ID: Optional[int] = None
    Model_ID: Optional[int] = None
    Make_Tac_Code: Optional[str] = None
    Model_Tac_Code: Optional[str] = None
    Variance: Optional[str] = None
    Tac_Code: Optional[str] = None
    Wheels: Optional[str] = None
    Manufacturing_Year: Optional[str] = None
    Operated_By: Optional[str] = None
    CC: Optional[str] = None
    Seating_Capacity: Optional[str] = None
    Carrying_Capacity: Optional[str] = None
    Body_Type: Optional[str] = None
    Vehicle_Segment_Name: Optional[str] = None
    COM_Segment: Optional[str] = None
    Is_In_Black_Listed: Optional[str] = None
    IsObsolete: Optional[str] = None
    IsImported: Optional[str] = None


class VehicleVariantDetailResponse(BaseModel):
    """Full 91-column variant specification including regional price fields."""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    Variant_ID: int
    Veh_Type_ID: Optional[int] = None
    Veh_Sub_Type_ID: Optional[int] = None
    Model_ID: Optional[int] = None
    Make_Tac_Code: Optional[str] = None
    Model_Tac_Code: Optional[str] = None
    Variance: Optional[str] = None
    Tac_Code: Optional[str] = None
    Wheels: Optional[str] = None
    Manufacturing_Year: Optional[str] = None
    Operated_By: Optional[str] = None
    Amp: Optional[str] = None
    CC: Optional[str] = None
    Unit_Name: Optional[str] = None
    Battery_Manufacturer: Optional[str] = None
    Gross_Weight: Optional[str] = None
    Seating_Capacity: Optional[str] = None
    Carrying_Capacity: Optional[str] = None
    Body_Type: Optional[str] = None
    Min_Seating_Capacity: Optional[str] = None
    Max_Seating_Capacity: Optional[str] = None
    Min_carrying_Capacity: Optional[str] = None
    Max_carrying_Capacity: Optional[str] = None
    Is_In_Black_Listed: Optional[str] = None
    IsObsolete: Optional[str] = None
    IsImported: Optional[str] = None
    Vehicle_Segment_Name: Optional[str] = None
    COM_Segment: Optional[str] = None

    # Regional Ex-Showroom Prices (19 regional markets)
    ExMumbai_Body_Price: Optional[str] = None
    ExMumbai_Model_Price: Optional[str] = None
    ExMumbai_Chasis_Price: Optional[str] = None
    ExNewDelhi_Body_Price: Optional[str] = None
    ExNewDelhi_Model_Price: Optional[str] = None
    ExNewDelhi_Chasis_Price: Optional[str] = None
    ExBangalore_Body_Price: Optional[str] = None
    ExBangalore_Model_Price: Optional[str] = None
    ExBangalore_Chasis_Price: Optional[str] = None
    ExKolkatta_Body_Price: Optional[str] = None
    ExKolkatta_Model_Price: Optional[str] = None
    ExKolkatta_Chasis_Price: Optional[str] = None
    ExAhmedabad_Body_Price: Optional[str] = None
    ExAhmedabad_Model_Price: Optional[str] = None
    ExAhmedabad_Chasis_Price: Optional[str] = None
    ExChandigarh_Body_Price: Optional[str] = None
    ExChandigarh_Model_Price: Optional[str] = None
    ExChandigarh_Chasis_Price: Optional[str] = None
    ExShimla_Body_Price: Optional[str] = None
    ExShimla_Model_Price: Optional[str] = None
    ExShimla_Chasis_Price: Optional[str] = None
    ExFaridabad_Body_Price: Optional[str] = None
    ExFaridabad_Model_Price: Optional[str] = None
    ExFaridabad_Chasis_Price: Optional[str] = None
    ExLucknow_Body_Price: Optional[str] = None
    ExLucknow_Model_Price: Optional[str] = None
    ExLucknow_Chasis_Price: Optional[str] = None
    ExDehradun_Body_Price: Optional[str] = None
    ExDehradun_Model_Price: Optional[str] = None
    ExDehradun_Chasis_Price: Optional[str] = None
    ExKohima_Body_Price: Optional[str] = None
    ExKohima_Model_Price: Optional[str] = None
    ExKohima_Chasis_Price: Optional[str] = None
    ExPatna_Body_Price: Optional[str] = None
    ExPatna_Model_Price: Optional[str] = None
    ExPatna_Chasis_Price: Optional[str] = None
    ExChennai_Body_Price: Optional[str] = None
    ExChennai_Model_Price: Optional[str] = None
    ExChennai_Chasis_Price: Optional[str] = None
    ExThiruvananthapuram_Body_Price: Optional[str] = None
    ExThiruvananthapuram_Model_Price: Optional[str] = None
    ExThiruvananthapuram_Chasis_Price: Optional[str] = None
    ExHyderabad_Body_Price: Optional[str] = None
    ExHyderabad_Model_Price: Optional[str] = None
    ExHyderabad_Chasis_Price: Optional[str] = None
    ExBhopal_Body_Price: Optional[str] = None
    ExBhopal_Model_Price: Optional[str] = None
    ExBhopal_Chasis_Price: Optional[str] = None
    ExRaipur_Body_Price: Optional[str] = None
    ExRaipur_Model_Price: Optional[str] = None
    ExRaipur_Chasis_Price: Optional[str] = None
    ExJaipur_Body_Price: Optional[str] = None
    ExJaipur_Model_Price: Optional[str] = None
    ExJaipur_Chasis_Price: Optional[str] = None
    ExPanaji_Body_Price: Optional[str] = None
    ExPanaji_Model_Price: Optional[str] = None
    ExPanaji_Chasis_Price: Optional[str] = None

    Last_Updated_Date: Optional[str] = None
    Mfg_BuildIn: Optional[str] = None
    ModelStatus: Optional[str] = None
    R_Make_ID: Optional[int] = None
    R_Model_ID: Optional[int] = None
    Make_Id: int = 0


class VariantRegionalPriceResponse(BaseModel):
    variant_id: int
    variance: Optional[str] = None
    market_region: str
    ex_showroom_body_price: Optional[Decimal] = None
    ex_showroom_model_price: Optional[Decimal] = None
    ex_showroom_chasis_price: Optional[Decimal] = None
    effective_ex_showroom_price: Decimal = Decimal("0.00")


class RTOResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    RTOId: int
    RTOLocation: str
    District: str
    REG_code: Optional[str] = None
    State_ID_FK: Optional[int] = None
    zone: Optional[str] = None
    ClusterId: int
    isdeleted: Optional[int] = 0
    StateId: Optional[int] = None
    RTOWithLocation: Optional[str] = None


class InsuranceCompanyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    InsuranceCompanyId: int
    InsuranceCompany: Optional[str] = None
    BranchName: Optional[str] = None
    BranchCode: Optional[str] = None
    NCB: str
    Cluster: str
    ZeroDeep: str
    isdeleted: Optional[str] = "0"
    IsAppQuotation: str
    MailId: Optional[str] = None
    CompImgPath: str
    LedgerMId: int
    ShortName: str
    CreditDays: int = 0
    PolicyNo: str
    len: int
    InsurerSAIBA: Optional[str] = None
    InsurerBranchAutoCodeSAIBA: Optional[str] = None
    PE_CompanyName: Optional[str] = None
    VantageInsurance: Optional[str] = None
    VantageBranch: Optional[str] = None
    VantageBranchAddress: Optional[str] = None


# ---------------------------------------------------------------------------
# BLOCK 2: Underwriting / Rating Lookup Masters
# ---------------------------------------------------------------------------

class AddonExtraAmtResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    ExtraAddonId: int
    InsuranceCompanyId: Optional[int] = None
    VehiceTypeId: Optional[int] = None
    makeId: Optional[int] = 0
    ModelId: Optional[int] = 0
    Age: Optional[int] = 0
    NillDep: Optional[float] = None
    SecurePlus: Optional[float] = None
    SPremium: Optional[float] = None
    No: Optional[float] = None
    IsDeleted: Optional[int] = 0


class ZeroDepResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    ZerodepId: int
    InsuranceCompanyId: Optional[int] = None
    Make_ID: Optional[int] = None
    Model_Id: Optional[int] = None
    FuelTypeId: int = 1
    Age: Optional[str] = None
    NillDep: Optional[float] = None
    SecurePlus: Optional[float] = None
    SPremium: Optional[float] = None
    NO: Optional[int] = None
    Isdelete: int = 0


class PAToOwnerDriverResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    PAToOwnerDriverId: int
    InsuranceCompanyId: Optional[int] = None
    Rate: Optional[float] = None
    TowingCharges: float = 0.0
    IsDeleted: Optional[int] = 0


class TowingRateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    Id: int
    InsuranceCompanyId: Optional[int] = None
    Selection: Optional[float] = None
    Rate: Optional[float] = None
    GST18: Optional[float] = None
    Total: Optional[float] = None
    IsDelete: Optional[int] = 0
    Flag: Optional[str] = None


class NCBSlabResponse(BaseModel):
    slab_code: str
    ncb_percentage: Decimal
    step_order: int
    description: str


# ---------------------------------------------------------------------------
# BLOCK 3: Organizational / Reference Masters
# ---------------------------------------------------------------------------

class BranchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    BranchId: int
    BranchCode: Optional[str] = None
    BranchName: Optional[str] = None
    Address: Optional[str] = None
    ContactNo: Optional[str] = None
    BranchTypeId: Optional[int] = 1
    isdeleted: int = 0


class StateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    StateID: int
    StateName: str
    isdeleted: int = 0


class DistrictResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    DistrictID: int
    DistrictName: str
    StateID: int
    isdeleted: int = 0


class BankResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    BankId: int
    BankName: str
    isdeleted: int = 0
