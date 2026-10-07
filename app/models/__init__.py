"""
SQLAlchemy 2.0 Declarative Models for Reliable Assurance Backend.
All models strictly preserve verified physical MySQL database table and column names.
"""
from app.db.base import Base
from app.models.transaction import Transaction
from app.models.transaction_app import TransactionAppNew
from app.models.payment import TransactionPayment
from app.models.customer import Customer
from app.models.vehicle import VehicleDetails
from app.models.account import Account
from app.models.ledger import LedgerMaster
from app.models.commission import (
    FranchiseCommission,
    AgentCommissionPayment,
    CutNPayCommPayable,
)
from app.models.user import User, UserRole
from app.models.master import (
    VehicleType,
    VehicleSubType,
    VehicleMake,
    VehicleModel,
    VehicleVariant,
    RTOMaster,
    InsuranceCompany,
    Branch,
    StateMaster,
    DistrictMaster,
    BankMaster,
)
from app.models.quotation import (
    AppQuatationEntry,
    AppQuotationRequest,
    InsuranceCompanyQuotation,
    AppQuotationRemark,
    AppRequestedQuotationFile,
    QuotDamagePremium,
    QuotLiabilityPremium,
    AppODDiscountNew,
    AppODDiscountNewGCV,
    AppODDiscount,
    InsuranceCompanyByVehicleType,
    PAToOwnerDriver,
    InsuranceCompanyWiseTowingChanges,
    ZeroDep,
    ZeroDepForSegmentWise,
    ZeroDepNewAddonRate,
    AddonExtraAmt,
    AppTwoWheelerCCRate,
    AppPCVCCRate,
    AppBusCCRate,
    AppThreeWheelerCCRate,
    QuotationPrefix,
    SelfDiscount,
)
from app.models.claims_endorsement import (
    Claim,
    ClaimDocument,
    PolicyEndorsement,
)
from app.models.document import (
    DocumentRecord,
    PolicyParserWebhookRecord,
)
from app.models.integration import VehicleRCDetails
from app.models.renewal import PolicyRenewalStatus, RenewalFollowupHistory
from app.models.notification import (
    SMSLog,
    PushNotificationLog,
    MessageMaster,
    MessageDetail,
    OTPLog,
)

__all__ = [
    "Base",
    "Transaction",
    "TransactionAppNew",
    "TransactionPayment",
    "Customer",
    "VehicleDetails",
    "Account",
    "LedgerMaster",
    "FranchiseCommission",
    "AgentCommissionPayment",
    "CutNPayCommPayable",
    "User",
    "UserRole",
    "VehicleType",
    "VehicleSubType",
    "VehicleMake",
    "VehicleModel",
    "VehicleVariant",
    "RTOMaster",
    "InsuranceCompany",
    "Branch",
    "StateMaster",
    "DistrictMaster",
    "BankMaster",
    "AppQuatationEntry",
    "AppQuotationRequest",
    "InsuranceCompanyQuotation",
    "AppQuotationRemark",
    "AppRequestedQuotationFile",
    "QuotDamagePremium",
    "QuotLiabilityPremium",
    "AppODDiscountNew",
    "AppODDiscountNewGCV",
    "AppODDiscount",
    "InsuranceCompanyByVehicleType",
    "PAToOwnerDriver",
    "InsuranceCompanyWiseTowingChanges",
    "ZeroDep",
    "ZeroDepForSegmentWise",
    "ZeroDepNewAddonRate",
    "AddonExtraAmt",
    "AppTwoWheelerCCRate",
    "AppPCVCCRate",
    "AppBusCCRate",
    "AppThreeWheelerCCRate",
    "QuotationPrefix",
    "SelfDiscount",
    "Claim",
    "ClaimDocument",
    "PolicyEndorsement",
    "DocumentRecord",
    "PolicyParserWebhookRecord",
    "VehicleRCDetails",
    "PolicyRenewalStatus",
    "RenewalFollowupHistory",
    "SMSLog",
    "PushNotificationLog",
    "MessageMaster",
    "MessageDetail",
    "OTPLog",
]
