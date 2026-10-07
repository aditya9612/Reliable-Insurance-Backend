from decimal import Decimal
from datetime import datetime
from typing import Optional
from sqlalchemy import Integer, String, DateTime, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class UserRole(Base):
    """
    User Role Master Model
    Physical Table: tbl_userrole
    Physical PK: UserRoleId
    Verified Column Count: 4
    Physical Foreign Keys: 0 (Enforced at application layer)
    """
    __tablename__ = "tbl_userrole"
    __table_args__ = {
        "mysql_charset": "utf8",
        "mysql_collate": "utf8_general_ci",
        "mysql_row_format": "DYNAMIC",
    }

    UserRoleId: Mapped[int] = mapped_column("UserRoleId", Integer, primary_key=True, autoincrement=True)
    UserRole: Mapped[Optional[str]] = mapped_column("UserRole", String(255), nullable=True)
    code: Mapped[Optional[str]] = mapped_column("code", String(255), nullable=True)
    isdeleted: Mapped[Optional[str]] = mapped_column("isdeleted", String(255), nullable=True)

    @property
    def is_active(self) -> bool:
        """Determines if the role is active (isdeleted != '1')."""
        return str(self.isdeleted).strip() != "1"


class User(Base):
    """
    System User & Employee Account Model
    Physical Table: tbl_user
    Physical PK: UserId
    Verified Column Count: 13
    Physical Foreign Keys: 0 (Enforced at application layer)
    """
    __tablename__ = "tbl_user"
    __table_args__ = (
        Index("fk_UserRoleId", "UserRoleId"),
        Index("fk_BranchId", "BranchId"),
        {
            "mysql_charset": "utf8",
            "mysql_collate": "utf8_general_ci",
            "mysql_row_format": "DYNAMIC",
        },
    )

    UserId: Mapped[int] = mapped_column("UserId", Integer, primary_key=True, autoincrement=True)
    UserName: Mapped[Optional[str]] = mapped_column("UserName", String(255), unique=True, nullable=True)
    UserPassword: Mapped[Optional[str]] = mapped_column("UserPassword", String(255), nullable=True)
    UserRoleId: Mapped[Optional[int]] = mapped_column("UserRoleId", Integer, nullable=True)
    BranchId: Mapped[Optional[int]] = mapped_column("BranchId", Integer, nullable=True)
    isappuser: Mapped[Optional[str]] = mapped_column("isappuser", String(255), nullable=True)
    isdeleted: Mapped[Optional[str]] = mapped_column("isdeleted", String(255), nullable=True)
    CreateDate: Mapped[Optional[datetime]] = mapped_column("CreateDate", DateTime, nullable=True)
    CreateUser: Mapped[Optional[str]] = mapped_column("CreateUser", String(255), nullable=True)
    UpdateDate: Mapped[Optional[datetime]] = mapped_column("UpdateDate", DateTime, nullable=True)
    UpdateUser: Mapped[Optional[str]] = mapped_column("UpdateUser", String(255), nullable=True)
    partner_user_id: Mapped[Optional[str]] = mapped_column("partner_user_id", String(250), nullable=True)
    mobile_no: Mapped[Optional[str]] = mapped_column("mobile_no", String(100), nullable=True)

    @property
    def is_active(self) -> bool:
        """Determines if the user account is active (isdeleted != '1')."""
        return str(self.isdeleted).strip() != "1"
