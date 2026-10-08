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


class LoginHistory(Base):
    """
    User Login and Session Tracking History Model
    Physical Table: tbl_loginhistory
    Physical PK: LoginHistoryId
    Verified Column Count: 8
    Physical Foreign Keys: 0
    """
    __tablename__ = "tbl_loginhistory"
    __table_args__ = (
        Index("ix_tbl_loginhistory_UserId", "UserId"),
        Index("ix_tbl_loginhistory_CreateDate", "CreateDate"),
        {
            "mysql_charset": "utf8",
            "mysql_collate": "utf8_general_ci",
            "mysql_row_format": "DYNAMIC",
        },
    )

    LoginHistoryId: Mapped[int] = mapped_column("LoginHistoryId", Integer, primary_key=True, autoincrement=True)
    UserId: Mapped[Optional[int]] = mapped_column("UserId", Integer, nullable=True)
    UserName: Mapped[Optional[str]] = mapped_column("UserName", String(255), nullable=True)
    LogInOrLogOut: Mapped[Optional[str]] = mapped_column("LogInOrLogOut", String(50), nullable=True)
    funPerform: Mapped[Optional[str]] = mapped_column("funPerform", String(255), nullable=True)
    IPAddress: Mapped[Optional[str]] = mapped_column("IPAddress", String(100), nullable=True)
    CreateDate: Mapped[Optional[datetime]] = mapped_column("CreateDate", DateTime, nullable=True, default=datetime.utcnow)
    Remark: Mapped[Optional[str]] = mapped_column("Remark", String(255), nullable=True)


class RolePrivilege(Base):
    """
    Role Screen & Dynamic Menu Privilege Mapping Model
    Physical Table: tbl_role_privilege
    Physical PK: Id
    Verified Column Count: 6
    Physical Foreign Keys: 0
    """
    __tablename__ = "tbl_role_privilege"
    __table_args__ = (
        Index("ix_tbl_role_privilege_BranchId", "BranchId"),
        Index("ix_tbl_role_privilege_RoleId", "RoleId"),
        Index("ix_tbl_role_privilege_ScreenId", "ScreenId"),
        {
            "mysql_charset": "utf8",
            "mysql_collate": "utf8_general_ci",
            "mysql_row_format": "DYNAMIC",
        },
    )

    Id: Mapped[int] = mapped_column("Id", Integer, primary_key=True, autoincrement=True)
    BranchId: Mapped[Optional[int]] = mapped_column("BranchId", Integer, nullable=True)
    RoleId: Mapped[Optional[int]] = mapped_column("RoleId", Integer, nullable=True)
    ScreenId: Mapped[Optional[int]] = mapped_column("ScreenId", Integer, nullable=True)
    CreateDate: Mapped[Optional[datetime]] = mapped_column("CreateDate", DateTime, nullable=True, default=datetime.utcnow)
    isdeleted: Mapped[str] = mapped_column("isdeleted", String(10), nullable=False, default="0")

    @property
    def is_active(self) -> bool:
        return str(self.isdeleted).strip() != "1"


class MenuMaster(Base):
    """
    System Navigation & Presentation Menu Model
    Physical Table: tbl_menu
    Physical PK: MenuId
    Verified Column Count: 7
    Physical Foreign Keys: 0
    """
    __tablename__ = "tbl_menu"
    __table_args__ = (
        Index("ix_tbl_menu_ParentMenuId", "ParentMenuId"),
        {
            "mysql_charset": "utf8",
            "mysql_collate": "utf8_general_ci",
            "mysql_row_format": "DYNAMIC",
        },
    )

    MenuId: Mapped[int] = mapped_column("MenuId", Integer, primary_key=True, autoincrement=True)
    MenuName: Mapped[Optional[str]] = mapped_column("MenuName", String(100), nullable=True)
    MenuUrl: Mapped[Optional[str]] = mapped_column("MenuUrl", String(255), nullable=True)
    ParentMenuId: Mapped[int] = mapped_column("ParentMenuId", Integer, nullable=False, default=0)
    OrderNo: Mapped[int] = mapped_column("OrderNo", Integer, nullable=False, default=0)
    IconClass: Mapped[Optional[str]] = mapped_column("IconClass", String(50), nullable=True)
    isdeleted: Mapped[str] = mapped_column("isdeleted", String(10), nullable=False, default="0")

    @property
    def is_active(self) -> bool:
        return str(self.isdeleted).strip() != "1"
