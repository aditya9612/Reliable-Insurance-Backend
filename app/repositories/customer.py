from typing import Optional, Sequence
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.customer import Customer
from app.repositories.base import BaseRepository


class CustomerRepository(BaseRepository[Customer]):
    """
    Data-access repository for Customer entity (tbl_customer).
    No business logic, pure database access.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Customer, session)

    async def get_by_code(self, customer_code: str) -> Optional[Customer]:
        """Lookup customer by unique CustomerCode."""
        query = select(Customer).where(Customer.CustomerCode == customer_code)
        result = await self.session.execute(query)
        return result.scalars().first()

    async def search_by_name(
        self,
        search_text: str,
        branch_id: int = 0,
        offset: int = 0,
        limit: int = 50,
    ) -> Sequence[Customer]:
        """
        Search customers by full or partial name (matching CustFName, CustMName, CustLName).
        Scoped by branch_id if branch_id > 0 (0 returns all branches).
        Excludes soft-deleted records (isdeleted == '1').
        """
        name_concat = func.concat(
            func.coalesce(Customer.CustFName, ""),
            " ",
            func.coalesce(Customer.CustMName, ""),
            " ",
            func.coalesce(Customer.CustLName, ""),
        )
        conditions = [
            name_concat.ilike(f"%{search_text}%"),
            or_(Customer.isdeleted != "1", Customer.isdeleted.is_(None)),
        ]
        if branch_id > 0:
            conditions.append(Customer.BranchId == branch_id)

        query = select(Customer).where(*conditions).offset(offset).limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def list_by_branch(
        self,
        branch_id: int,
        offset: int = 0,
        limit: int = 50,
    ) -> Sequence[Customer]:
        """List customers scoped to a specific branch."""
        query = (
            select(Customer)
            .where(Customer.BranchId == branch_id)
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_by_branch(self, branch_id: int) -> Sequence[Customer]:
        """Backward-compatible lookup for customers by BranchId without explicit pagination."""
        return await self.list_by_branch(branch_id=branch_id, offset=0, limit=100)

    async def get_by_mobile(
        self,
        mobile_no: str,
        offset: int = 0,
        limit: int = 50,
    ) -> Sequence[Customer]:
        """
        Lookup customer(s) by MoblieNo1 or MoblieNo2.
        Returns a collection because MoblieNo1 is NOT globally unique in legacy data.
        """
        query = (
            select(Customer)
            .where((Customer.MoblieNo1 == mobile_no) | (Customer.MoblieNo2 == mobile_no))
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_by_pan(
        self,
        pan_no: str,
        offset: int = 0,
        limit: int = 50,
    ) -> Sequence[Customer]:
        """Lookup customer(s) by PAN_No."""
        query = (
            select(Customer)
            .where(Customer.PAN_No == pan_no)
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def search_customers(
        self,
        *,
        name: Optional[str] = None,
        mobile: Optional[str] = None,
        pan: Optional[str] = None,
        customer_code: Optional[str] = None,
        branch_id: Optional[int] = None,
        offset: int = 0,
        limit: int = 50,
    ) -> Sequence[Customer]:
        """
        Composite customer search/list query supporting name, mobile, PAN, customer_code,
        and branch scoping while strictly excluding soft-deleted rows (isdeleted == '1').
        """
        conditions = [
            or_(Customer.isdeleted != "1", Customer.isdeleted.is_(None)),
        ]
        if branch_id is not None and branch_id > 0:
            conditions.append(Customer.BranchId == branch_id)

        if name and name.strip():
            name_concat = func.concat(
                func.coalesce(Customer.CustFName, ""),
                " ",
                func.coalesce(Customer.CustMName, ""),
                " ",
                func.coalesce(Customer.CustLName, ""),
            )
            conditions.append(name_concat.ilike(f"%{name.strip()}%"))

        if mobile and mobile.strip():
            mob = mobile.strip()
            conditions.append(
                or_(Customer.MoblieNo1 == mob, Customer.MoblieNo2 == mob)
            )

        if pan and pan.strip():
            conditions.append(Customer.PAN_No == pan.strip().upper())

        if customer_code and customer_code.strip():
            conditions.append(Customer.CustomerCode == customer_code.strip())

        query = (
            select(Customer)
            .where(*conditions)
            .order_by(Customer.CustomerId.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return result.scalars().all()
