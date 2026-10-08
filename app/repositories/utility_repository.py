"""
Repository layer for Phase 15B — IDV Requests, Health Members, Bulk Policy MIS & Operational Batch Jobs.
"""
from typing import Optional, Sequence, List, Dict, Any
from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, update, extract, case
from app.models.utility import IDVRequest, HealthMember, ImportAgentPolicy
from app.models.payment import TransactionPayment
from app.models.transaction import Transaction
from app.models.user import User
from app.models.customer import Customer
from app.models.profile import Employee, Agent, Franchise


class UtilityRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ========================================================================
    # IDV REQUEST METHODS
    # ========================================================================

    async def get_idv_request_by_id(self, req_id: int) -> Optional[IDVRequest]:
        stmt = select(IDVRequest).where(
            IDVRequest.IDVRequestId == req_id,
            IDVRequest.isdeleted != "1"
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list_idv_requests(
        self,
        status: Optional[str] = None,
        sales_ex_id: Optional[int] = None,
        reg_no: Optional[str] = None,
        offset: int = 0,
        limit: int = 100
    ) -> Sequence[IDVRequest]:
        stmt = select(IDVRequest).where(IDVRequest.isdeleted != "1")
        if status:
            stmt = stmt.where(IDVRequest.Status == status.upper())
        if sales_ex_id is not None:
            stmt = stmt.where(IDVRequest.SalesExId == sales_ex_id)
        if reg_no:
            stmt = stmt.where(IDVRequest.RegistrationNo.ilike(f"%{reg_no.strip()}%"))
        stmt = stmt.order_by(IDVRequest.IDVRequestId.desc()).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def create_idv_request(self, req: IDVRequest) -> IDVRequest:
        self.session.add(req)
        await self.session.flush()
        return req

    # ========================================================================
    # HEALTH MEMBER METHODS
    # ========================================================================

    async def get_health_member_by_id(self, member_id: int) -> Optional[HealthMember]:
        stmt = select(HealthMember).where(
            HealthMember.MemberId == member_id,
            HealthMember.isdeleted != "1"
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list_health_members(
        self,
        transaction_id: Optional[int] = None,
        customer_id: Optional[int] = None,
        offset: int = 0,
        limit: int = 100
    ) -> Sequence[HealthMember]:
        stmt = select(HealthMember).where(HealthMember.isdeleted != "1")
        if transaction_id is not None:
            stmt = stmt.where(HealthMember.TransanctionId == transaction_id)
        if customer_id is not None:
            stmt = stmt.where(HealthMember.CustomerId == customer_id)
        stmt = stmt.order_by(HealthMember.MemberId.asc()).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def create_health_member(self, member: HealthMember) -> HealthMember:
        self.session.add(member)
        await self.session.flush()
        return member

    async def soft_delete_health_member(self, member_id: int, user: str = "SYSTEM") -> bool:
        member = await self.get_health_member_by_id(member_id)
        if not member:
            return False
        member.isdeleted = "1"
        member.UpdateUser = user
        await self.session.flush()
        return True

    # ========================================================================
    # BULK POLICY MIS STAGING METHODS
    # ========================================================================

    async def bulk_create_imported_policies(
        self, records: List[ImportAgentPolicy]
    ) -> List[ImportAgentPolicy]:
        self.session.add_all(records)
        await self.session.flush()
        return records

    async def list_imported_policies(
        self,
        batch_id: Optional[str] = None,
        is_process: Optional[int] = None,
        policy_no: Optional[str] = None,
        offset: int = 0,
        limit: int = 100
    ) -> Sequence[ImportAgentPolicy]:
        stmt = select(ImportAgentPolicy).where(ImportAgentPolicy.isdeleted != "1")
        if batch_id:
            stmt = stmt.where(ImportAgentPolicy.BatchId == batch_id)
        if is_process is not None:
            stmt = stmt.where(ImportAgentPolicy.IsProcess == is_process)
        if policy_no:
            stmt = stmt.where(ImportAgentPolicy.PolicyNumber.ilike(f"%{policy_no.strip()}%"))
        stmt = stmt.order_by(ImportAgentPolicy.Id.desc()).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def mark_batch_processed(
        self, batch_id: str, remark: Optional[str] = None
    ) -> int:
        stmt = (
            update(ImportAgentPolicy)
            .where(
                ImportAgentPolicy.BatchId == batch_id,
                ImportAgentPolicy.isdeleted != "1"
            )
            .values(
                IsProcess=1,
                Remark=remark or "Batch Processed Successfully"
            )
        )
        res = await self.session.execute(stmt)
        await self.session.flush()
        return res.rowcount

    async def get_batch_summary(self, batch_id: str) -> Optional[Dict[str, Any]]:
        stmt = select(
            func.count(ImportAgentPolicy.Id).label("total_records"),
            func.sum(
                case((ImportAgentPolicy.IsProcess == 1, 1), else_=0)
            ).label("processed_records"),
            func.sum(
                case((ImportAgentPolicy.IsProcess == 0, 1), else_=0)
            ).label("pending_records"),
            func.coalesce(func.sum(ImportAgentPolicy.GrossAmount), Decimal("0.00")).label("total_gross"),
            func.coalesce(func.sum(ImportAgentPolicy.NetAmount), Decimal("0.00")).label("total_net"),
            func.min(ImportAgentPolicy.CreatedDate).label("created_at"),
            func.min(ImportAgentPolicy.CreatedBy).label("created_by"),
        ).where(
            ImportAgentPolicy.BatchId == batch_id,
            ImportAgentPolicy.isdeleted != "1"
        )
        res = await self.session.execute(stmt)
        row = res.one_or_none()
        if not row or not row.total_records:
            return None
        return {
            "batch_id": batch_id,
            "total_records": row.total_records or 0,
            "processed_records": int(row.processed_records or 0),
            "pending_records": int(row.pending_records or 0),
            "total_gross_amount": Decimal(str(row.total_gross or 0)),
            "total_net_amount": Decimal(str(row.total_net or 0)),
            "created_at": row.created_at or datetime.utcnow(),
            "created_by": row.created_by or "SYSTEM",
        }

    # ========================================================================
    # OPERATIONAL BATCH JOB QUERIES
    # ========================================================================

    async def find_overdue_uncleared_cheques(self, threshold_days: int = 15) -> List[Dict[str, Any]]:
        """
        LBR-069: Scans tbl_transactionpayment for cheques pending clearance older than threshold_days.
        """
        cutoff_date = datetime.utcnow() - timedelta(days=threshold_days)
        stmt = (
            select(
                TransactionPayment.PaymentId,
                TransactionPayment.TransanctionId,
                TransactionPayment.docno,
                TransactionPayment.PaymentDate,
                TransactionPayment.PaidAmount,
                TransactionPayment.CreateDate,
                TransactionPayment.CashierApproval,
                Transaction.CreateUser,
                Transaction.AgentId,
                Transaction.PolicyNo,
            )
            .join(Transaction, TransactionPayment.TransanctionId == Transaction.TransanctionId)
            .where(
                TransactionPayment.PaymentType.ilike("%cheque%"),
                or_(
                    TransactionPayment.CashierApproval == 0,
                    TransactionPayment.CashierApproval.is_(None),
                ),
                TransactionPayment.CreateDate <= cutoff_date,
            )
        )
        result = await self.session.execute(stmt)
        rows = result.all()
        return [
            {
                "payment_id": r.PaymentId,
                "transaction_id": r.TransanctionId,
                "cheque_no": r.docno,
                "cheque_date": r.PaymentDate,
                "cheque_amount": r.PaidAmount or Decimal("0.00"),
                "created_date": r.CreateDate,
                "user_name": r.CreateUser,
                "agent_id": r.AgentId,
                "policy_number": r.PolicyNo,
            }
            for r in rows
        ]



    async def find_today_birthday_candidates(self, target_date: Optional[date] = None) -> List[Dict[str, Any]]:
        """
        Scans customers, employees, and agents whose birth month and day match target_date (default today).
        """
        if target_date is None:
            target_date = date.today()

        t_month = target_date.month
        t_day = target_date.day

        candidates: List[Dict[str, Any]] = []

        # 1. Customers
        c_stmt = select(Customer).where(
            Customer.DateOfBirth.is_not(None),
            extract("month", Customer.DateOfBirth) == t_month,
            extract("day", Customer.DateOfBirth) == t_day,
            Customer.isdeleted != "1"
        )
        c_res = await self.session.execute(c_stmt)
        for cust in c_res.scalars().all():
            candidates.append({
                "entity_type": "CUSTOMER",
                "entity_id": cust.CustomerId,
                "name": cust.full_name if hasattr(cust, "full_name") else f"{cust.CustFName or ''} {cust.CustLName or ''}".strip(),
                "mobile": cust.MoblieNo1 or cust.MoblieNo2,
                "email": cust.EMailId,
                "date_of_birth": cust.DateOfBirth,
            })

        # 2. Employees
        e_stmt = select(Employee).where(
            Employee.CreateDate.is_not(None),  # If DOB not present in tbl_employee, fallback or check
            Employee.isdeleted != "1"
        )
        # Note: Employee doesn't have DateOfBirth column in legacy tbl_employee; Franchise does!

        # 3. Franchise partners
        f_stmt = select(Franchise).where(
            Franchise.DateOfBirth.is_not(None),
            extract("month", Franchise.DateOfBirth) == t_month,
            extract("day", Franchise.DateOfBirth) == t_day,
            Franchise.isdeleted != "1"
        )
        f_res = await self.session.execute(f_stmt)
        for fran in f_res.scalars().all():
            candidates.append({
                "entity_type": "FRANCHISE",
                "entity_id": fran.FranchiseId,
                "name": fran.full_name,
                "mobile": fran.MoblieNo1 or fran.MoblieNo2,
                "email": fran.EmailId,
                "date_of_birth": fran.DateOfBirth,
            })

        return candidates
