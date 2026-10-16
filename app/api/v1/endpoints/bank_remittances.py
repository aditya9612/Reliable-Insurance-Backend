"""
FastAPI Route Handlers for Phase 27:
Company Outstanding Premium Remittance & Cash-to-Bank Deposit Settlement Engine.
Physical Tables: tbl_debitfrombankaccount, tbl_account, tbl_transaction, tbl_ledgermaster.
"""
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.dependencies import get_current_principal
from app.core.rbac import PrincipalContext
from app.services.bank_remittance_service import BankDebitRemittanceService
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

bank_remittance_router = APIRouter(prefix="/bank-remittance", tags=["Bank Remittance & Cash Settlement"])


@bank_remittance_router.get(
    "/pending-company",
    response_model=List[PendingCompanyRemittanceItemResponse],
    summary="List Pending Policy Premiums for Company Remittance",
    description="Lists issued proposals and policies awaiting batch remittance payment to the underwriting insurance company.",
)
async def list_pending_company_remittances(
    company_id: int = Query(..., ge=1, description="Underwriting Insurance Company ID"),
    branch_id: Optional[int] = Query(None, ge=1, description="Optional Branch ID filter"),
    from_date: Optional[datetime] = Query(None, description="Optional start creation date filter"),
    to_date: Optional[datetime] = Query(None, description="Optional end creation date filter"),
    skip: int = Query(0, ge=0, description="Pagination skip offset"),
    limit: int = Query(50, ge=1, le=500, description="Pagination page limit"),
    db: AsyncSession = Depends(get_db),
    principal: PrincipalContext = Depends(get_current_principal),
) -> List[PendingCompanyRemittanceItemResponse]:
    service = BankDebitRemittanceService(db)
    return await service.list_pending_company_remittances(
        company_id=company_id,
        branch_id=branch_id,
        from_date=from_date,
        to_date=to_date,
        skip=skip,
        limit=limit,
        principal=principal,
    )


@bank_remittance_router.post(
    "/company-batch",
    response_model=CompanyRemittanceBatchResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Execute Batch Premium Remittance to Insurance Company",
    description="Atomically settles a batch of policies to an insurance company, records double-entry vouchers (debit company, credit bank), and writes to tbl_debitfrombankaccount.",
)
async def execute_company_remittance_batch(
    payload: CompanyRemittanceBatchRequest,
    db: AsyncSession = Depends(get_db),
    principal: PrincipalContext = Depends(get_current_principal),
) -> CompanyRemittanceBatchResponse:
    service = BankDebitRemittanceService(db)
    return await service.execute_company_remittance_batch(payload, principal=principal)


@bank_remittance_router.post(
    "/cash-to-bank",
    response_model=CashToBankDepositResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Execute Branch Cash-to-Bank Deposit Settlement",
    description="Records deposit of collected branch cash into the company bank account with double-entry ledger vouchers and tbl_debitfrombankaccount journal.",
)
async def execute_cash_to_bank_deposit(
    payload: CashToBankDepositRequest,
    db: AsyncSession = Depends(get_db),
    principal: PrincipalContext = Depends(get_current_principal),
) -> CashToBankDepositResponse:
    service = BankDebitRemittanceService(db)
    return await service.execute_cash_to_bank_deposit(payload, principal=principal)


@bank_remittance_router.get(
    "/cash-balance",
    response_model=CashBalanceSummaryResponse,
    summary="Get Branch Cash Balance & Settlement Summary",
    description="Calculates authoritative branch cash collections, bank deposits, net remaining cash, and pending un-deposited proposal counts.",
)
async def get_cash_balance_summary(
    branch_id: int = Query(..., ge=1, description="Branch ID to summarize"),
    db: AsyncSession = Depends(get_db),
    principal: PrincipalContext = Depends(get_current_principal),
) -> CashBalanceSummaryResponse:
    service = BankDebitRemittanceService(db)
    return await service.get_cash_balance_summary(branch_id=branch_id, principal=principal)


@bank_remittance_router.get(
    "/history",
    response_model=DebitRemittanceHistoryListResponse,
    summary="List Bank Debit Remittance and Cash Settlement History",
    description="Retrieves paginated audit log of company remittances and cash-to-bank deposits from tbl_debitfrombankaccount.",
)
async def list_debit_remittance_history(
    flag: Optional[str] = Query(None, description="Filter by Flag: 'Company' or 'Cash'"),
    branch_id: Optional[int] = Query(None, ge=1, description="Optional Branch ID filter"),
    from_date: Optional[datetime] = Query(None, description="Optional start account date filter"),
    to_date: Optional[datetime] = Query(None, description="Optional end account date filter"),
    skip: int = Query(0, ge=0, description="Pagination skip offset"),
    limit: int = Query(50, ge=1, le=500, description="Pagination page limit"),
    db: AsyncSession = Depends(get_db),
    principal: PrincipalContext = Depends(get_current_principal),
) -> DebitRemittanceHistoryListResponse:
    service = BankDebitRemittanceService(db)
    return await service.list_debit_remittance_history(
        flag=flag,
        branch_id=branch_id,
        from_date=from_date,
        to_date=to_date,
        skip=skip,
        limit=limit,
        principal=principal,
    )


@bank_remittance_router.get(
    "/{debit_id}",
    response_model=DebitRemittanceResponse,
    summary="Get Bank Debit Remittance Record by ID",
    description="Retrieves a single bank debit remittance journal record by its primary key.",
)
async def get_debit_remittance_by_id(
    debit_id: int = Path(..., ge=1, description="Debit Account Entry ID (Account_Id)"),
    db: AsyncSession = Depends(get_db),
    principal: PrincipalContext = Depends(get_current_principal),
) -> DebitRemittanceResponse:
    service = BankDebitRemittanceService(db)
    return await service.get_debit_remittance_by_id(debit_id=debit_id, principal=principal)
