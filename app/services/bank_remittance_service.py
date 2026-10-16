"""
Phase 27 Service Layer:
Company Outstanding Premium Remittance & Cash-to-Bank Deposit Settlement Engine.
Physical Tables:
1. tbl_debitfrombankaccount (BankDebitRemittance)
2. tbl_account (Double-entry financial ledger)
3. tbl_transaction (Policy proposals and settlements)
4. tbl_ledgermaster (Chart of accounts)
"""
from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Dict, Any, Tuple
import logging
from fastapi import HTTPException, status
from sqlalchemy import select, update, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bank_remittance import BankDebitRemittance
from app.models.account import Account
from app.models.ledger import LedgerMaster
from app.models.transaction import Transaction
from app.models.customer import Customer
from app.models.master import InsuranceCompany, Branch
from app.core.rbac import PrincipalContext, is_global_admin_role, is_global_read_role
from app.repositories.commission_accounting import CommissionAccountingRepository
from app.schemas.bank_remittance import (
    CompanyRemittanceBatchRequest,
    CashToBankDepositRequest,
    DebitRemittanceResponse,
    CompanyRemittanceBatchResponse,
    CashToBankDepositResponse,
    PendingCompanyRemittanceItemResponse,
    CashBalanceSummaryResponse,
    DebitRemittanceHistoryListResponse,
)

logger = logging.getLogger(__name__)


class BankDebitRemittanceService:
    """Service orchestrating company remittance clearance and cash-to-bank settlement."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def _allocate_doc_no(self) -> int:
        """Concurrency-safe allocation of monotonic sequential Doc_No in tbl_account."""
        repo = CommissionAccountingRepository(self.db)
        return await repo.allocate_next_doc_no()

    # =========================================================================
    # 1. PENDING COMPANY PREMIUM REMITTANCE DISCOVERY
    # =========================================================================

    async def list_pending_company_remittances(
        self,
        company_id: int,
        branch_id: Optional[int] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 50,
        principal: Optional[PrincipalContext] = None,
    ) -> List[PendingCompanyRemittanceItemResponse]:
        """
        Lists issued policy proposals pending remittance/clearance to the underwriting insurance company.
        Legacy Parity: adm_DebitFromBankAccount.aspx.cs -> fillGrid() & sp_CashOnlinePaymentPendingEntry.
        """
        # Multi-tenant branch scoping
        effective_branch_id = branch_id
        if principal and not (is_global_admin_role(principal.role_name) or is_global_read_role(principal.role_name)):
            if principal.branch_id:
                effective_branch_id = principal.branch_id

        # Subquery to exclude transactions already remitted in tbl_debitfrombankaccount
        remitted_subquery = (
            select(BankDebitRemittance.TransactionId)
            .where(
                BankDebitRemittance.Flag == "Company",
                BankDebitRemittance.isdeleted == 0,
                BankDebitRemittance.TransactionId.isnot(None),
            )
            .scalar_subquery()
        )

        query = (
            select(Transaction)
            .where(
                Transaction.InsuranceCompanyId == company_id,
                or_(Transaction.isdeleted == "0", Transaction.isdeleted.is_(None)),
                Transaction.OnlinePaymentToCompany == 0,
                Transaction.TransanctionId.not_in(remitted_subquery),
            )
        )

        if effective_branch_id:
            query = query.where(Transaction.BranchId == effective_branch_id)
        if from_date:
            query = query.where(Transaction.CreateDate >= from_date)
        if to_date:
            query = query.where(Transaction.CreateDate <= to_date)

        query = query.order_by(Transaction.TransanctionId.desc()).offset(skip).limit(limit)
        results = (await self.db.execute(query)).scalars().all()

        if not results:
            return []

        # Bulk fetch Customer Names and Insurance Company Name
        cust_ids = [t.CustomerId for t in results if t.CustomerId]
        cust_name_map: Dict[int, str] = {}
        if cust_ids:
            cust_stmt = select(Customer.CustomerId, Customer.CustomerName).where(
                Customer.CustomerId.in_(cust_ids)
            )
            for c_id, c_name in (await self.db.execute(cust_stmt)).all():
                cust_name_map[c_id] = c_name or ""

        comp_stmt = select(InsuranceCompany.InsuranceCompany).where(
            InsuranceCompany.InsuranceCompanyId == company_id
        )
        company_name = (await self.db.execute(comp_stmt)).scalars().first() or ""

        items: List[PendingCompanyRemittanceItemResponse] = []
        for t in results:
            gross = t.Amount or Decimal("0.00")
            net = t.NetPermium or Decimal("0.00")
            proposal = t.ProPosalAmt or net or gross
            items.append(
                PendingCompanyRemittanceItemResponse(
                    TransactionId=t.TransanctionId,
                    ProposalNo=t.InwardNo,
                    PolicyNo=t.PolicyNo,
                    CustomerId=t.CustomerId,
                    customer_name=cust_name_map.get(t.CustomerId or 0, ""),
                    InsuranceCompanyId=company_id,
                    insurance_company_name=company_name,
                    GrossPremium=gross,
                    NetPremium=net,
                    ProposalAmt=proposal,
                    BranchId=t.BranchId or 101,
                    CreatedDate=t.CreateDate,
                )
            )

        return items

    # =========================================================================
    # 2. BATCH COMPANY REMITTANCE CLEARANCE
    # =========================================================================

    async def execute_company_remittance_batch(
        self,
        payload: CompanyRemittanceBatchRequest,
        principal: PrincipalContext,
    ) -> CompanyRemittanceBatchResponse:
        """
        Executes atomic batch premium remittance to an underwriting insurance company.
        Creates balanced double-entry accounting entries in tbl_account and audit journal records
        in tbl_debitfrombankaccount (Flag = 'Company'), updating policy records.
        
        Legacy Parity:
        adm_Outstandingclearentry.aspx.cs / adm_DebitFromBankAccount.aspx.cs
        -> OnlinePaymentToCompany() + BLL_InsertDebitFromBankAccount + BLL_UpdateDocNoAfterPayment.
        """
        is_admin = is_global_admin_role(principal.role_name) or is_global_read_role(principal.role_name) or (
            principal.role_name in {"ACCOUNT", "ACCOUNT HEAD"}
        )
        target_branch_id = payload.branch_id or principal.branch_id or 101
        if not is_admin and principal.branch_id and target_branch_id != principal.branch_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Branch scoping violation: not authorized to remit for branch {target_branch_id}.",
            )

        # Validate Ledgers
        comp_ledger = await self.db.get(LedgerMaster, payload.company_ledger_id)
        if not comp_ledger or str(comp_ledger.isdeleted).strip() == "1":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Insurance Company Ledger ID {payload.company_ledger_id} not found or inactive.",
            )

        bank_ledger = await self.db.get(LedgerMaster, payload.bank_ledger_id)
        if not bank_ledger or str(bank_ledger.isdeleted).strip() == "1":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Bank Ledger ID {payload.bank_ledger_id} not found or inactive.",
            )

        # Fetch and validate all transactions
        stmt = select(Transaction).where(
            Transaction.TransanctionId.in_(payload.transaction_ids),
            or_(Transaction.isdeleted == "0", Transaction.isdeleted.is_(None)),
        )
        trans_list = (await self.db.execute(stmt)).scalars().all()
        if len(trans_list) != len(payload.transaction_ids):
            found_ids = {t.TransanctionId for t in trans_list}
            missing = set(payload.transaction_ids) - found_ids
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Transaction IDs {missing} not found or deleted.",
            )

        now_dt = datetime.utcnow()
        remit_date = payload.payment_date or now_dt
        total_amount = Decimal("0.00")

        for t in trans_list:
            if t.OnlinePaymentToCompany == 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Transaction {t.TransanctionId} has already been remitted to company (Doc: {t.CompSubmitionDocNo}).",
                )
            if t.InsuranceCompanyId != payload.company_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Transaction {t.TransanctionId} belongs to company {t.InsuranceCompanyId}, not {payload.company_id}.",
                )
            if not is_admin and principal.branch_id and t.BranchId != principal.branch_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Transaction {t.TransanctionId} belongs to branch {t.BranchId}, not permitted.",
                )
            amt = t.ProPosalAmt or t.NetPermium or t.Amount or Decimal("0.00")
            total_amount += amt

        # Allocate monotonic sequential Doc_No
        doc_no_int = await self._allocate_doc_no()
        doc_no_str = str(doc_no_int)

        remittance_records: List[BankDebitRemittance] = []
        comp_ledger_name = comp_ledger.LedgerName or f"Company Ledger {payload.company_ledger_id}"

        # 1. Double-Entry: Debit Company Ledger for each individual policy
        for t in trans_list:
            amt = t.ProPosalAmt or t.NetPermium or t.Amount or Decimal("0.00")
            narr = payload.narration or f"Pay To {comp_ledger_name} With Cheque No-{payload.cheque_no or 'N/A'}"

            # tbl_account Entry 1 (Debit Company)
            comp_entry = Account(
                AccTransId=1,
                AccountDate=remit_date,
                LedgerMId=payload.company_ledger_id,
                amount=amt,  # Positive DEBIT
                Narration=narr,
                ReferenceAgentId=t.AgentId or 0,
                ReferenceCustId=t.CustomerId or 0,
                BranchId=t.BranchId or target_branch_id,
                Doc_No=doc_no_int,
                CreatedUser=principal.username,
                CreatedDate=now_dt,
                UpdatedUser="",
                PaymentType=payload.payment_mode,
                TransactionId=t.TransanctionId,
                CustVehId=t.CustVehId or 0,
                IsNill=0,
                MonthId=remit_date.month,
                EndorsementId=0,
                TransId=0,
                isdeleted=0,
            )
            self.db.add(comp_entry)

            # tbl_debitfrombankaccount Audit record
            debit_rec = BankDebitRemittance(
                TransactionId=t.TransanctionId,
                LedgerMId=payload.company_ledger_id,
                BranchId=t.BranchId or target_branch_id,
                Doc_No=doc_no_str,
                Amount=amt,
                AccountDate=remit_date,
                Narration=f"Pay To {comp_ledger_name}",
                Flag="Company",
                CompanyChequeNo=payload.cheque_no,
                CreatedUser=principal.username,
                CreatedDate=now_dt,
                isdeleted=0,
            )
            self.db.add(debit_rec)
            remittance_records.append(debit_rec)

            # Update Transaction settlement state
            t.OnlinePaymentToCompany = 1
            t.CompSubmitionDocNo = doc_no_str
            t.OnlineToCompanyDate = remit_date
            t.CompanyChequeNo = payload.cheque_no
            t.UpdateDate = now_dt
            t.UpdateUser = principal.username

        # 2. Double-Entry: Credit Bank Ledger once for the total batch
        bank_narr = payload.narration or f"Pay To {comp_ledger_name} With Cheque No-{payload.cheque_no or 'N/A'}"
        bank_entry = Account(
            AccTransId=1,
            AccountDate=remit_date,
            LedgerMId=payload.bank_ledger_id,
            amount=-total_amount,  # Negative CREDIT
            Narration=bank_narr,
            ReferenceAgentId=0,
            ReferenceCustId=0,
            BranchId=target_branch_id,
            Doc_No=doc_no_int,
            CreatedUser=principal.username,
            CreatedDate=now_dt,
            UpdatedUser="",
            PaymentType=payload.payment_mode,
            TransactionId=0,
            CustVehId=0,
            IsNill=0,
            MonthId=remit_date.month,
            EndorsementId=0,
            TransId=0,
            isdeleted=0,
        )
        self.db.add(bank_entry)

        # Atomic commit
        await self.db.commit()

        # Refresh created remittance records
        for r in remittance_records:
            await self.db.refresh(r)

        return CompanyRemittanceBatchResponse(
            success=True,
            message="Batch remittance to company executed successfully.",
            doc_no=doc_no_str,
            company_id=payload.company_id,
            company_ledger_id=payload.company_ledger_id,
            bank_ledger_id=payload.bank_ledger_id,
            total_remitted_amount=total_amount,
            transaction_count=len(trans_list),
            remittance_records=[
                DebitRemittanceResponse.model_validate(r) for r in remittance_records
            ],
        )

    # =========================================================================
    # 3. CASH-TO-BANK DEPOSIT SETTLEMENT
    # =========================================================================

    async def execute_cash_to_bank_deposit(
        self,
        payload: CashToBankDepositRequest,
        principal: PrincipalContext,
    ) -> CashToBankDepositResponse:
        """
        Deposits collected branch cash into the company bank account.
        Generates balanced double-entry accounting records (AccTransId 1 Bank, AccTransId 3 Cash)
        and logs the settlement in tbl_debitfrombankaccount (Flag = 'Cash').
        
        Legacy Parity:
        adm_PremiumCashtoBank.aspx.cs -> btnsave_Click() + OnlinePaymentToCompany()
        + BLL_InsertDebitFromBankAccount + BLL_UpdateCashBalanceData.
        """
        is_admin = is_global_admin_role(principal.role_name) or is_global_read_role(principal.role_name) or (
            principal.role_name in {"ACCOUNT", "ACCOUNT HEAD", "CASHIER"}
        )
        target_branch_id = payload.branch_id or principal.branch_id or 101
        if not is_admin and principal.branch_id and target_branch_id != principal.branch_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Branch scoping violation: not authorized to deposit cash for branch {target_branch_id}.",
            )

        # Validate Ledgers
        from_cash_ledger = await self.db.get(LedgerMaster, payload.from_cash_ledger_id)
        if not from_cash_ledger or str(from_cash_ledger.isdeleted).strip() == "1":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Cash Ledger ID {payload.from_cash_ledger_id} not found or inactive.",
            )

        to_bank_ledger = await self.db.get(LedgerMaster, payload.to_bank_ledger_id)
        if not to_bank_ledger or str(to_bank_ledger.isdeleted).strip() == "1":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Bank Ledger ID {payload.to_bank_ledger_id} not found or inactive.",
            )

        now_dt = datetime.utcnow()
        deposit_date = payload.deposit_date or now_dt
        doc_no_int = await self._allocate_doc_no()
        doc_no_str = str(doc_no_int)
        narr = payload.narration or "Premium cash deposite in Bank"

        # Double Entry 1: Bank Leg (AccTransId 1, Credit Bank)
        bank_entry = Account(
            AccTransId=1,
            AccountDate=deposit_date,
            LedgerMId=payload.to_bank_ledger_id,
            amount=-payload.deposit_amount,  # Per legacy convention: -deposit_amount
            Narration=narr,
            ReferenceAgentId=0,
            ReferenceCustId=0,
            BranchId=target_branch_id,
            Doc_No=doc_no_int,
            CreatedUser=principal.username,
            CreatedDate=now_dt,
            UpdatedUser="",
            PaymentType=payload.payment_mode,
            TransactionId=0,
            CustVehId=0,
            IsNill=0,
            MonthId=deposit_date.month,
            EndorsementId=0,
            TransId=0,
            isdeleted=0,
        )
        self.db.add(bank_entry)

        # Double Entry 2: Cash Leg (AccTransId 3, Debit Cash)
        cash_entry = Account(
            AccTransId=3,
            AccountDate=deposit_date,
            LedgerMId=payload.from_cash_ledger_id,
            amount=payload.deposit_amount,  # Per legacy convention: +deposit_amount
            Narration=narr,
            ReferenceAgentId=0,
            ReferenceCustId=0,
            BranchId=target_branch_id,
            Doc_No=doc_no_int,
            CreatedUser=principal.username,
            CreatedDate=now_dt,
            UpdatedUser="",
            PaymentType=payload.payment_mode,
            TransactionId=0,
            CustVehId=0,
            IsNill=0,
            MonthId=deposit_date.month,
            EndorsementId=0,
            TransId=0,
            isdeleted=0,
        )
        self.db.add(cash_entry)

        # Audit Journal in tbl_debitfrombankaccount
        debit_rec = BankDebitRemittance(
            TransactionId=payload.transaction_ids[0] if payload.transaction_ids else None,
            LedgerMId=payload.to_bank_ledger_id,
            BranchId=target_branch_id,
            Doc_No=doc_no_str,
            Amount=payload.deposit_amount,
            AccountDate=deposit_date,
            Narration=narr,
            Flag="Cash",
            CompanyChequeNo=None,
            isdeleted=0,
            CreatedUser=principal.username,
            CreatedDate=now_dt,
        )
        self.db.add(debit_rec)

        # If specific transaction IDs were attached to this deposit batch, mark them settled
        if payload.transaction_ids:
            stmt = select(Transaction).where(
                Transaction.TransanctionId.in_(payload.transaction_ids),
                or_(Transaction.isdeleted == "0", Transaction.isdeleted.is_(None)),
            )
            attached_trans = (await self.db.execute(stmt)).scalars().all()
            for t in attached_trans:
                t.PremiumCashToBank = 1
                t.PremiumCashDocNo = doc_no_str
                t.UpdateDate = now_dt
                t.UpdateUser = principal.username

        await self.db.commit()
        await self.db.refresh(debit_rec)

        return CashToBankDepositResponse(
            success=True,
            message="Premium cash deposited to bank successfully.",
            doc_no=doc_no_str,
            from_cash_ledger_id=payload.from_cash_ledger_id,
            to_bank_ledger_id=payload.to_bank_ledger_id,
            deposit_amount=payload.deposit_amount,
            remittance_record=DebitRemittanceResponse.model_validate(debit_rec),
        )

    # =========================================================================
    # 4. BRANCH CASH BALANCE & SETTLEMENT SUMMARY
    # =========================================================================

    async def get_cash_balance_summary(
        self,
        branch_id: int,
        principal: Optional[PrincipalContext] = None,
    ) -> CashBalanceSummaryResponse:
        """
        Calculates authoritative real-time cash balance and pending cash settlement metrics for a branch.
        Legacy Parity: adm_PremiumCashtoBank.aspx.cs -> BLL_CashBalanceData & BLL_CashBalanceDataTotalPremium.
        """
        if principal and not (is_global_admin_role(principal.role_name) or is_global_read_role(principal.role_name)):
            if principal.branch_id and principal.branch_id != branch_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Branch scoping violation: cannot access cash summary for branch {branch_id}.",
                )

        # Get branch name
        branch = await self.db.get(Branch, branch_id)
        branch_name = branch.BranchName if branch else f"Branch {branch_id}"

        # Total Cash collected in branch
        collected_stmt = select(
            func.coalesce(func.sum(Account.amount), Decimal("0.00"))
        ).where(
            Account.BranchId == branch_id,
            Account.AccTransId == 3,
            Account.isdeleted == 0,
        )
        total_collected = (await self.db.execute(collected_stmt)).scalar_one()

        # Total Cash deposited into bank
        deposited_stmt = select(
            func.coalesce(func.sum(BankDebitRemittance.Amount), Decimal("0.00"))
        ).where(
            BankDebitRemittance.BranchId == branch_id,
            BankDebitRemittance.Flag == "Cash",
            BankDebitRemittance.isdeleted == 0,
        )
        total_deposited = (await self.db.execute(deposited_stmt)).scalar_one()

        # Net remaining cash balance in branch
        current_balance = total_collected - total_deposited
        if current_balance < Decimal("0.00"):
            current_balance = Decimal("0.00")

        # Pending un-deposited cash transactions count
        pending_count_stmt = select(func.count(Transaction.TransanctionId)).where(
            Transaction.BranchId == branch_id,
            Transaction.PremiumCashToBank == 0,
            or_(Transaction.isdeleted == "0", Transaction.isdeleted.is_(None)),
        )
        pending_count = (await self.db.execute(pending_count_stmt)).scalar_one()

        return CashBalanceSummaryResponse(
            branch_id=branch_id,
            branch_name=branch_name,
            total_cash_collected=total_collected,
            total_cash_deposited_to_bank=total_deposited,
            current_cash_balance=current_balance,
            pending_cash_transactions_count=pending_count,
        )

    # =========================================================================
    # 5. AUDIT JOURNAL HISTORY & DETAIL RETRIEVAL
    # =========================================================================

    async def list_debit_remittance_history(
        self,
        flag: Optional[str] = None,
        branch_id: Optional[int] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 50,
        principal: Optional[PrincipalContext] = None,
    ) -> DebitRemittanceHistoryListResponse:
        """
        Lists historical bank debit remittances and cash-to-bank deposit audit records.
        """
        effective_branch_id = branch_id
        if principal and not (is_global_admin_role(principal.role_name) or is_global_read_role(principal.role_name)):
            if principal.branch_id:
                effective_branch_id = principal.branch_id

        query = select(BankDebitRemittance).where(BankDebitRemittance.isdeleted == 0)

        if flag:
            query = query.where(BankDebitRemittance.Flag == flag)
        if effective_branch_id:
            query = query.where(BankDebitRemittance.BranchId == effective_branch_id)
        if from_date:
            query = query.where(BankDebitRemittance.AccountDate >= from_date)
        if to_date:
            query = query.where(BankDebitRemittance.AccountDate <= to_date)

        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar_one()

        query = query.order_by(BankDebitRemittance.DebitAccountId.desc()).offset(skip).limit(limit)
        items = (await self.db.execute(query)).scalars().all()

        return DebitRemittanceHistoryListResponse(
            total=total,
            items=[DebitRemittanceResponse.model_validate(it) for it in items],
        )

    async def get_debit_remittance_by_id(
        self,
        debit_id: int,
        principal: Optional[PrincipalContext] = None,
    ) -> DebitRemittanceResponse:
        """Retrieves a single bank debit remittance entry by its primary key."""
        entry = await self.db.get(BankDebitRemittance, debit_id)
        if not entry or entry.isdeleted != 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Bank debit remittance entry {debit_id} not found.",
            )

        if principal and not (is_global_admin_role(principal.role_name) or is_global_read_role(principal.role_name)):
            if principal.branch_id and entry.BranchId != principal.branch_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Branch scoping violation: not authorized to access record for branch {entry.BranchId}.",
                )

        return DebitRemittanceResponse.model_validate(entry)
