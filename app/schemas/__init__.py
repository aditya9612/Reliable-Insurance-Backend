from app.schemas.auth import LoginRequest, LoginResponse, UserRead
from app.schemas.customer import (
    CustomerBase,
    CustomerCreate,
    CustomerUpdate,
    CustomerResponse,
)
from app.schemas.vehicle import (
    VehicleBase,
    VehicleCreate,
    VehicleUpdate,
    VehicleResponse,
)

__all__ = [
    "LoginRequest",
    "LoginResponse",
    "UserRead",
    "CustomerBase",
    "CustomerCreate",
    "CustomerUpdate",
    "CustomerResponse",
    "VehicleBase",
    "VehicleCreate",
    "VehicleUpdate",
    "VehicleResponse",
]
