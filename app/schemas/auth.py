from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    """
    User login request payload.
    Supports standard username and password credentials.
    """
    username: str = Field(..., min_length=1, max_length=255, description="Unique username identifier")
    password: str = Field(..., min_length=1, description="Account password (plaintext from client)")


class UserRead(BaseModel):
    """
    Public safe user profile representation.
    CRITICAL SECURITY RULE: NEVER exposes password, password hash, or security secrets.
    """
    model_config = ConfigDict(from_attributes=True)

    user_id: int = Field(..., description="Unique user identifier (UserId)")
    username: str = Field(..., description="Username")
    role: Optional[str] = Field(None, description="Assigned role name (e.g., ADMIN, AGENT, OWNER)")
    role_id: Optional[int] = Field(None, description="Assigned role identifier (UserRoleId)")
    branch_id: Optional[int] = Field(None, description="Assigned operational branch identifier (BranchId)")
    agent_id: Optional[int] = Field(None, description="Resolved AgentId when principal is an Agent")
    emp_id: Optional[int] = Field(None, description="Resolved EmpId when principal is an Employee/Executive")
    employee_id: Optional[int] = Field(None, description="Resolved EmployeeId alias for EmpId")
    franchise_id: Optional[int] = Field(None, description="Resolved FranchiseId when principal is a Franchise")
    mobile_no: Optional[str] = Field(None, description="Registered mobile number")
    is_active: bool = Field(True, description="Account active status")


class LoginResponse(BaseModel):
    """
    Authentication response with JWT Bearer token and optional safe user context.
    """
    access_token: str = Field(..., description="Signed JWT Bearer access token")
    token_type: str = Field("bearer", description="Token type specification")
    expires_in: int = Field(..., description="Token lifespan in seconds")
    user: Optional[UserRead] = Field(None, description="Authenticated safe user context")
