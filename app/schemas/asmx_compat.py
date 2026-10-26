"""
Pydantic schemas for Legacy Mobile ASMX Compatibility Router (GAP-P1-001 & GAP-P1-002).
Exact contract mirror of legacy DTOs in API/AllMaster.cs & Service.asmx.cs:
- API_Agent
- API_AgentNew
- API_CustomerApp
- API_EwalletBalanceResponse
"""
from typing import Optional, Union
from pydantic import BaseModel, Field


class API_AgentResponse(BaseModel):
    """
    Legacy DTO contract mirror for Service.asmx/AppLogin.
    Physical C# class: API.API_Agent (API/AllMaster.cs L1263-L1276).
    """
    UserId: Union[int, float] = Field(default=0, description="User ID from tbl_user.UserId")
    SalesExecutiveId: Union[int, float] = Field(default=0, description="Sales Executive Employee ID")
    CoordinatorId: Union[int, float] = Field(default=0, description="Coordinator Employee ID")
    AgentId: Union[int, float] = Field(default=0, description="Agent ID from tbl_agent.AgentId")
    UserName: str = Field(default="", description="Login username")
    Password: str = Field(default="", description="Always empty string; NEVER return password or hash")
    Coordinator: str = Field(default="", description="Coordinator name or General")
    UserRoleId: str = Field(default="", description="User Role ID as string")
    OldVersion: Optional[str] = Field(default=None, description="App version info")
    NewVersion: Optional[str] = Field(default=None, description="App version info")

    model_config = {
        "populate_by_name": True,
        "json_schema_extra": {
            "example": {
                "UserId": 243,
                "SalesExecutiveId": 108,
                "CoordinatorId": 0,
                "AgentId": 243,
                "UserName": "agent_posp",
                "Password": "",
                "Coordinator": "General",
                "UserRoleId": "4",
                "OldVersion": None,
                "NewVersion": None,
            }
        }
    }


class API_AgentNewResponse(BaseModel):
    """
    Legacy DTO contract mirror for Service.asmx/AgentAppLoginNew.
    Physical C# class: API.API_AgentNew (API/AllMaster.cs L1279-L1297).
    Note exact legacy spelling of FranchaiseId.
    """
    UserId: Union[int, float] = Field(default=0, description="User ID from tbl_user.UserId")
    SalesExecutiveId: Union[int, float] = Field(default=0, description="Sales Executive Employee ID")
    CoordinatorId: Union[int, float] = Field(default=0, description="Coordinator Employee ID")
    AgentId: Union[int, float] = Field(default=0, description="Agent ID from tbl_agent.AgentId")
    UserName: str = Field(default="", description="Login username")
    Password: str = Field(default="", description="Always empty string; NEVER return password or hash")
    Coordinator: str = Field(default="", description="Coordinator name or General")
    UserRoleId: str = Field(default="", description="User Role ID as string")
    OldVersion: Optional[str] = Field(default=None, description="App version info")
    NewVersion: Optional[str] = Field(default=None, description="App version info")
    FranchaiseId: Union[int, float] = Field(default=0, description="Franchise ID (legacy spelling)")
    BranchId: Union[int, float] = Field(default=0, description="Branch ID")
    FullName: str = Field(default="", description="Agent full name")
    MobileNo: str = Field(default="", description="Agent mobile number")
    MailId: str = Field(default="", description="Agent email address")

    model_config = {
        "populate_by_name": True,
        "json_schema_extra": {
            "example": {
                "UserId": 243,
                "SalesExecutiveId": 108,
                "CoordinatorId": 0,
                "AgentId": 243,
                "UserName": "agent_posp",
                "Password": "",
                "Coordinator": "General",
                "UserRoleId": "4",
                "OldVersion": "1.0",
                "NewVersion": "1.0",
                "FranchaiseId": 1015,
                "BranchId": 1,
                "FullName": "Rajesh Kumar",
                "MobileNo": "9876543210",
                "MailId": "rajesh@example.com",
            }
        }
    }


class API_CustomerAppResponse(BaseModel):
    """
    Legacy DTO contract mirror for Service.asmx/CheckLoginCustomer.
    Physical C# class: API.API_CustomerApp (API/AllMaster.cs L1145-L1154).
    Note exact legacy spelling of MoblieNo1, MoblieNo2, EMailId.
    """
    CustomerId: Union[int, float] = Field(default=0, description="Customer ID from tbl_customer.CustomerId")
    Name: str = Field(default="", description="Customer full name")
    MoblieNo1: str = Field(default="", description="Primary mobile number (legacy spelling)")
    MoblieNo2: Optional[str] = Field(default="", description="Secondary mobile number (legacy spelling)")
    EMailId: Optional[str] = Field(default="", description="Email address (legacy spelling)")
    Address: Optional[str] = Field(default="", description="Communication/permanent address")

    model_config = {
        "populate_by_name": True,
        "json_schema_extra": {
            "example": {
                "CustomerId": 501,
                "Name": "Amit Sharma",
                "MoblieNo1": "9876543210",
                "MoblieNo2": "9123456780",
                "EMailId": "amit@example.com",
                "Address": "Flat 101, Reliable Heights, Pune",
            }
        }
    }


class API_EwalletBalanceResponse(BaseModel):
    """
    Legacy DTO contract mirror for Service.asmx/SelectEwalletBalanceByAgent (GAP-P1-002).
    Legacy returns a JSON array of records from sp_SelectEwalletBalance.
    Matches column lookups dt.Rows[0]["Balance"], dt.Rows[0]["EwalletBalance"],
    and positional dt.Rows[0][0].
    """
    Balance: float = Field(default=0.0, description="Current wallet balance")
    EwalletBalance: float = Field(default=0.0, description="Legacy alias for wallet balance")
    AgentId: int = Field(default=0, description="POSP Agent ID from tbl_agent.AgentId")

    model_config = {
        "populate_by_name": True,
        "json_schema_extra": {
            "example": {
                "Balance": 5000.0,
                "EwalletBalance": 5000.0,
                "AgentId": 243,
            }
        }
    }


class API_VehicleTypeResponse(BaseModel):
    """
    Legacy DTO contract mirror for Service.asmx/SelectVehicleType (GAP-P1-003).
    C# source: Service.asmx.cs L12221, API/AllMaster.cs L69.
    """
    Veh_Type_ID: int = Field(default=0, description="Vehicle Type ID from tbl_vehicle_type.Veh_Type_ID")
    Veh_Type_Name: str = Field(default="", description="Vehicle Type Name")
    VehicleTypeId: int = Field(default=0, description="Legacy alias for Veh_Type_ID")
    VehicleType: str = Field(default="", description="Legacy alias for Veh_Type_Name")
    IsAppQuotation: Optional[int] = Field(default=None, description="Quotation availability flag")

    model_config = {
        "populate_by_name": True,
        "json_schema_extra": {
            "example": {
                "Veh_Type_ID": 1,
                "Veh_Type_Name": "Two Wheeler",
                "VehicleTypeId": 1,
                "VehicleType": "Two Wheeler",
                "IsAppQuotation": 1,
            }
        }
    }


class API_VehicleMakeResponse(BaseModel):
    """
    Legacy DTO contract mirror for Service.asmx/SelectVehicleMake (GAP-P1-003).
    C# source: Service.asmx.cs L12284 & L3325, API/AllMaster.cs L74.
    """
    Make_ID: int = Field(default=0, description="Make ID from tbl_vehicle_make.Make_ID")
    Make_Name: str = Field(default="", description="Make Name (e.g. MARUTI, HONDA)")
    VehicleMakeId: int = Field(default=0, description="Legacy alias for Make_ID")
    CompanyName: str = Field(default="", description="Legacy alias for Make_Name")
    R_Make_ID: Optional[int] = Field(default=None, description="Regional Make ID")
    GCV: Optional[str] = Field(default=None, description="GCV classification flag")
    Misc_D: Optional[str] = Field(default=None, description="Misc-D classification flag")
    PCV: Optional[str] = Field(default=None, description="PCV classification flag")
    PvtCar: Optional[str] = Field(default=None, description="Private Car classification flag")
    Two_Wheeler: Optional[str] = Field(default=None, description="Two Wheeler classification flag")
    Bus: Optional[str] = Field(default=None, description="Bus classification flag")

    model_config = {
        "populate_by_name": True,
        "json_schema_extra": {
            "example": {
                "Make_ID": 1,
                "Make_Name": "MARUTI",
                "VehicleMakeId": 1,
                "CompanyName": "MARUTI",
                "Two_Wheeler": "0",
                "PvtCar": "1",
            }
        }
    }


class API_VehicleModelResponse(BaseModel):
    """
    Legacy DTO contract mirror for Service.asmx/SelectVehicleModel (GAP-P1-003).
    C# source: Service.asmx.cs L3208 & L3408, API/AllMaster.cs L1379.
    """
    Model_ID: int = Field(default=0, description="Model ID from tbl_vehicle_model.Model_ID")
    Model_Name: str = Field(default="", description="Model Name (e.g. SWIFT, ACTIVA)")
    Make_ID: int = Field(default=0, description="Make ID from tbl_vehicle_model.Make_ID")
    ModelId: int = Field(default=0, description="Legacy alias for Model_ID")
    ModelName: str = Field(default="", description="Legacy alias for Model_Name")
    MakeId: int = Field(default=0, description="Legacy alias for Make_ID")
    VehicleModelId: int = Field(default=0, description="Legacy alias for Model_ID")
    VehicleModelName: str = Field(default="", description="Legacy alias for Model_Name")
    Type: Optional[int] = Field(default=None, description="Vehicle Type classification")
    SegmentId: Optional[int] = Field(default=None, description="Segment classification")

    model_config = {
        "populate_by_name": True,
        "json_schema_extra": {
            "example": {
                "Model_ID": 10,
                "Model_Name": "SWIFT",
                "Make_ID": 1,
                "ModelId": 10,
                "ModelName": "SWIFT",
                "MakeId": 1,
                "VehicleModelId": 10,
                "VehicleModelName": "SWIFT",
            }
        }
    }


class API_VehicleVariantResponse(BaseModel):
    """
    Legacy DTO contract mirror for Service.asmx/SelectVehicleVariance (GAP-P1-003).
    C# source: Service.asmx.cs L3442 & L3381, API/AllMaster.cs L91.
    """
    Variant_ID: int = Field(default=0, description="Variant ID from tbl_vehicle_variants.Variant_ID")
    Variance: str = Field(default="", description="Variant Name (e.g. VXI, ZXI)")
    Model_ID: int = Field(default=0, description="Model ID")
    Veh_Type_ID: int = Field(default=0, description="Vehicle Type ID")
    Veh_Sub_Type_ID: Optional[int] = Field(default=None, description="Vehicle Sub-Type ID")
    VariantId: int = Field(default=0, description="Legacy alias for Variant_ID")
    VarianceName: str = Field(default="", description="Legacy alias for Variance")
    CC: Optional[str] = Field(default="", description="Engine Displacement CC")
    Seating_Capacity: Optional[str] = Field(default="", description="Seating capacity")
    Carrying_Capacity: Optional[str] = Field(default="", description="Carrying capacity")
    Body_Type: Optional[str] = Field(default="", description="Body type")
    FuelType: Optional[str] = Field(default="", description="Fuel type / segment")

    model_config = {
        "populate_by_name": True,
        "json_schema_extra": {
            "example": {
                "Variant_ID": 101,
                "Variance": "1.2 VXI BS6",
                "Model_ID": 10,
                "Veh_Type_ID": 2,
                "VariantId": 101,
                "VarianceName": "1.2 VXI BS6",
                "CC": "1197",
                "Seating_Capacity": "5",
            }
        }
    }


class API_RTOResponse(BaseModel):
    """
    Legacy DTO contract mirror for Service.asmx/SelectRTO (GAP-P1-003).
    C# source: Service.asmx.cs L13057 & L13087, API/AllMaster.cs L61.
    """
    RTOId: int = Field(default=0, description="RTO ID from tbl_rto.RTOId")
    RTOLocation: str = Field(default="", description="RTO Location Name")
    REG_code: str = Field(default="", description="RTO Registration Code (e.g. MH12, DL01)")
    District: Optional[str] = Field(default="", description="District Name")
    StateId: Optional[int] = Field(default=None, description="State ID")
    zone: Optional[str] = Field(default="", description="Zone classification")
    ClusterId: Optional[int] = Field(default=None, description="Cluster ID")
    RTOWithLocation: Optional[str] = Field(default="", description="RTO Code with Location")
    RTO_ID: int = Field(default=0, description="Legacy alias for RTOId")
    RTO_Location: str = Field(default="", description="Legacy alias for RTOLocation")

    model_config = {
        "populate_by_name": True,
        "json_schema_extra": {
            "example": {
                "RTOId": 27,
                "RTOLocation": "PUNE",
                "REG_code": "MH-12",
                "District": "Pune",
                "StateId": 1,
                "RTO_ID": 27,
                "RTO_Location": "PUNE",
            }
        }
    }


class API_InsuranceCompanyResponse(BaseModel):
    """
    Legacy DTO contract mirror for Service.asmx/SelectInsuranceCompany (GAP-P1-003).
    C# source: Service.asmx.cs L124 & L149, API/AllMaster.cs L390.
    """
    InsuranceCompanyId: int = Field(default=0, description="Insurance Company ID from tbl_insurancecompany.InsuranceCompanyId")
    InsuranceCompany: str = Field(default="", description="Company Name (e.g. ICICI LOMBARD, HDFC ERGO)")
    BranchName: Optional[str] = Field(default="", description="Branch Name")
    BranchCode: Optional[str] = Field(default="", description="Branch Code")
    MailId: Optional[str] = Field(default="", description="Email address")
    CompImgPath: Optional[str] = Field(default="", description="Company logo path")
    ShortName: Optional[str] = Field(default="", description="Short code / acronym")
    IsAppQuotation: Optional[str] = Field(default=None, description="Quotation availability flag")

    model_config = {
        "populate_by_name": True,
        "json_schema_extra": {
            "example": {
                "InsuranceCompanyId": 1,
                "InsuranceCompany": "ICICI LOMBARD GENERAL INSURANCE CO. LTD.",
                "BranchName": "PUNE",
                "BranchCode": "4001",
                "MailId": "support@icicilombard.com",
                "ShortName": "ICICI",
            }
        }
    }
