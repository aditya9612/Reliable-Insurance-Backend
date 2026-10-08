from app.repositories.base import BaseRepository
from app.repositories.customer import CustomerRepository
from app.repositories.vehicle import VehicleRepository
from app.repositories.transaction import TransactionRepository
from app.repositories.transaction_app import TransactionAppRepository
from app.repositories.payment import PaymentRepository
from app.repositories.account import AccountRepository
from app.repositories.ledger import LedgerRepository
from app.repositories.commission import (
    FranchiseCommissionRepository,
    AgentCommissionRepository,
    CutNPayCommissionRepository,
)
from app.repositories.user import UserRepository
from app.repositories.role import RoleRepository
from app.repositories.master import (
    VehicleTypeRepository,
    VehicleSubTypeRepository,
    VehicleMakeRepository,
    VehicleModelRepository,
    VehicleVariantRepository,
    RTORepository,
    InsuranceCompanyRepository,
)

from app.repositories.profile_repository import ProfileRepository
from app.repositories.utility_repository import UtilityRepository

__all__ = [
    "BaseRepository",
    "CustomerRepository",
    "VehicleRepository",
    "TransactionRepository",
    "TransactionAppRepository",
    "PaymentRepository",
    "AccountRepository",
    "LedgerRepository",
    "FranchiseCommissionRepository",
    "AgentCommissionRepository",
    "CutNPayCommissionRepository",
    "UserRepository",
    "RoleRepository",
    "VehicleTypeRepository",
    "VehicleSubTypeRepository",
    "VehicleMakeRepository",
    "VehicleModelRepository",
    "VehicleVariantRepository",
    "RTORepository",
    "InsuranceCompanyRepository",
    "ProfileRepository",
    "UtilityRepository",
]
