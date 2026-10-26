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
