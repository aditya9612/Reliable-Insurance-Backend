"""
ReportService for Phase 14 — Orchestrates Dashboards, MIS, POSP Invoices,
Statutory Statements, Accounting Drilldowns, and Document Exports.
Enforces multi-tenant row scoping, strict export gating, decimal financial formulas,
and integration with Phase 11 StorageBackend.
"""
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional, Tuple, Dict, Any
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import PrincipalContext, is_global_read_role, is_global_admin_role
from app.repositories.report_repository import ReportRepository
from app.models.report import PospInvoice
from app.schemas.report import PospInvoiceCreateRequest
from app.services.export_service import (
    convert_number_to_words_inr,
    generate_excel_spreadsheet,
    generate_csv_stream,
    generate_posp_invoice_pdf,
    generate_voucher_pdf,
)
from app.services.storage_backend import get_storage_backend


class ReportService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = ReportRepository(session)
        self.storage = get_storage_backend()

    # =========================================================================
    # 1. Dashboards
    # =========================================================================

    async def get_admin_dashboard(
        self,
        financial_year: str,
        broker: Optional[str] = None,
        date_mode: str = "T_Date",
        branch_id: Optional[int] = None,
        principal: Optional[PrincipalContext] = None,
    ) -> Dict[str, Any]:
        # Branch scoping for non-global users
        if principal and not is_global_read_role(principal.role_name):
            branch_id = principal.branch_id
        return await self.repo.get_admin_dashboard(financial_year, broker, date_mode, branch_id)

    async def get_accounts_summary(
        self,
        from_date: date,
        to_date: date,
        branch_id: Optional[int] = None,
        principal: Optional[PrincipalContext] = None,
    ) -> Dict[str, Any]:
        if principal and not is_global_read_role(principal.role_name):
            branch_id = principal.branch_id
        return await self.repo.get_accounts_summary(from_date, to_date, branch_id)

    async def get_owner_dashboard(
        self,
        from_date: date,
        to_date: date,
        principal: Optional[PrincipalContext] = None,
    ) -> Dict[str, Any]:
        return await self.repo.get_owner_dashboard(from_date, to_date)

    async def get_cut_and_pay_summary(
        self,
        financial_year: str,
        month: Optional[str] = None,
        branch_id: Optional[int] = None,
        principal: Optional[PrincipalContext] = None,
    ) -> Dict[str, Any]:
        if principal and not is_global_read_role(principal.role_name):
            branch_id = principal.branch_id
        return await self.repo.get_cut_and_pay_summary(financial_year, month, branch_id)

    async def get_agent_outstanding(
        self,
        branch_id: Optional[int] = None,
        min_days_overdue: int = 0,
        principal: Optional[PrincipalContext] = None,
    ) -> Dict[str, Any]:
        if principal and not is_global_read_role(principal.role_name):
            branch_id = principal.branch_id
        return await self.repo.get_agent_outstanding(branch_id, min_days_overdue)

    # =========================================================================
    # 2. MIS Transactions & Scoped Querying / Exporting
    # =========================================================================

    def _resolve_mis_scope(
        self,
        principal: PrincipalContext,
        branch_id: Optional[int],
    ) -> Tuple[Optional[int], Optional[int], Optional[str], Optional[int]]:
        """
        Resolves (effective_branch_id, effective_agent_id, effective_created_by, effective_franchise_id)
        strictly from server-side PrincipalContext (GAP-5F-03).
        """
        role = (principal.role_name or "").upper()

        effective_branch_id = branch_id
        effective_agent_id = None
        effective_created_by = None
        effective_franchise_id = None

        if role in ("OWNER", "ADMIN", "IT SUPPORT", "ACCOUNT", "ACCOUNT HEAD"):
            # Global: can filter by requested branch_id
            effective_branch_id = branch_id
        elif role in ("LOCATION HEAD", "BRANCH MANAGER", "BRANCH_MANAGER", "MANAGER"):
            effective_branch_id = principal.branch_id
        elif role in ("OPERATOR", "BACK OFFICE"):
            effective_created_by = principal.username
        elif "FRANCHISE" in role:
            effective_franchise_id = principal.franchise_id
        elif role in ("AGENT", "POSP", "FRANCHISE AGENT"):
            effective_agent_id = principal.agent_id or principal.user_id

        return effective_branch_id, effective_agent_id, effective_created_by, effective_franchise_id

    async def get_mis_transactions(
        self,
        principal: PrincipalContext,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        policy_no: Optional[str] = None,
        vehicle_no: Optional[str] = None,
        payment_mode: Optional[str] = None,
        company_id: Optional[int] = None,
        broker: Optional[str] = None,
        branch_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Dict[str, Any]:
        eff_branch, eff_agent, eff_user, eff_franchise = self._resolve_mis_scope(principal, branch_id)

        items, total_count, tot_net, tot_gross = await self.repo.get_mis_transactions(
            from_date=from_date,
            to_date=to_date,
            policy_no=policy_no,
            vehicle_no=vehicle_no,
            payment_mode=payment_mode,
            company_id=company_id,
            broker=broker,
            branch_id=eff_branch,
            agent_id=eff_agent,
            created_by=eff_user,
            franchise_id=eff_franchise,
            skip=skip,
            limit=limit,
        )

        # Mask 12 sensitive internal columns for non-admin/finance roles
        is_admin_finance = (principal.role_name or "").upper() in ("OWNER", "ADMIN", "IT SUPPORT", "ACCOUNT", "ACCOUNT HEAD")
        if not is_admin_finance:
            for item in items:
                item["company_commission_rate"] = None
                item["total_company_commission"] = None
                item["company_profit"] = None
                item["franchise_commission_rate"] = None
                item["franchise_commission_amount"] = None
                item["tds_percentage"] = None
                item["internal_remarks"] = None

        return {
            "items": items,
            "total": total_count,
            "page": (skip // limit) + 1 if limit else 1,
            "page_size": limit,
            "total_net_premium": tot_net,
            "total_gross_premium": tot_gross,
        }

    async def export_mis_transactions(
        self,
        principal: PrincipalContext,
        export_format: str,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        broker: Optional[str] = None,
        branch_id: Optional[int] = None,
    ) -> Tuple[Any, str, str]:
        """
        Strictly gated export trigger.
        Allowed roles: OWNER, ADMIN, IT SUPPORT, ACCOUNT, ACCOUNT HEAD.
        Unauthorized roles: HTTP 403 Forbidden.
        """
        role = (principal.role_name or "").upper()
        if role not in ("OWNER", "ADMIN", "IT SUPPORT", "ACCOUNT", "ACCOUNT HEAD"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Transaction export is strictly gated to ADMIN, IT SUPPORT, and ACCOUNT roles.",
            )

        eff_branch, eff_agent, eff_user, eff_franchise = self._resolve_mis_scope(principal, branch_id)

        # Retrieve full dataset for export (up to 10,000 records)
        items, _, _, _ = await self.repo.get_mis_transactions(
            from_date=from_date,
            to_date=to_date,
            broker=broker,
            branch_id=eff_branch,
            agent_id=eff_agent,
            created_by=eff_user,
            franchise_id=eff_franchise,
            skip=0,
            limit=10000,
        )

        columns = [
            "Trans ID", "Policy No", "Policy Date", "Risk Start", "Risk End",
            "Insurance Company", "Broker", "Vehicle Reg No", "Make", "Model",
            "Customer Name", "Mobile No", "City",
            "OD Premium", "TP Premium", "Net Premium", "GST Amount", "Gross Premium",
            "Payment Mode", "Cheque No", "Agent Name", "Branch Name"
        ]

        rows = []
        for it in items:
            rows.append([
                it["trans_id"], it["policy_no"], it["policy_date"], it["start_date"], it["end_date"],
                it["insurance_company"], it["broker_name"], it["vehicle_no"], it["make"], it["model"],
                it["customer_name"], it["mobile_no"], it["city"],
                it["od_premium"], it["tp_premium"], it["net_premium"], it["gst_amount"], it["gross_premium"],
                it["payment_mode"], it["cheque_no"], it["agent_name"], it["branch_name"]
            ])

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if export_format.lower() == "csv":
            filename = f"TransactionReport_{timestamp}.csv"
            media_type = "text/csv; charset=utf-8"
            stream = generate_csv_stream(columns, rows)
            return stream, filename, media_type
        else:
            filename = f"TransactionReport_{timestamp}.xlsx"
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            file_bytes = generate_excel_spreadsheet(columns, rows, sheet_name="Transactions")
            return file_bytes, filename, media_type

    # =========================================================================
    # 3. POSP Invoicing & Payout Reconciliation
    # =========================================================================

    async def create_posp_invoice(
        self,
        request: PospInvoiceCreateRequest,
        principal: PrincipalContext,
    ) -> Dict[str, Any]:
        """
        Creates a new POSP Agent Payout Invoice.
        GST Parity:
        - If Agent is GST registered (checked via agent lookup): 18% IGST added.
        - If Unregistered: 0% GST.
        TDS Section 194H: 5% deducted on Base Payout.
        Net Disbursement: Base + GST - TDS.
        """
        amount = request.amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        # Lookup agent info
        from app.models.user import User
        u_res = await self.session.execute(select(User).where(User.UserId == request.agent_id))
        agent_user = u_res.scalar_one_or_none()
        agent_name = agent_user.UserName if agent_user else f"Agent #{request.agent_id}"

        # In legacy, agent GST status determines whether 18% GST applies
        has_gst = getattr(request, "is_gst_registered", False)
        if not has_gst and agent_user:
            p_id = str(getattr(agent_user, "partner_user_id", "") or "")
            if "GST" in p_id.upper():
                has_gst = True

        if has_gst:
            gst_amt = (amount * Decimal("0.18")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            grand_total = amount + gst_amt
        else:
            gst_amt = Decimal("0.00")
            grand_total = amount

        tds_amount = (amount * Decimal("0.05")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        net_payable = grand_total - tds_amount

        # Invoice numbering with concurrency protection
        if request.custom_invoice_no:
            inv_no = request.custom_invoice_no.strip()
            if await self.repo.check_invoice_no_exists(inv_no):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Invoice number '{inv_no}' already exists.",
                )
        else:
            inv_no = await self.repo.get_next_invoice_number(
                request.financial_year, request.month, request.agent_id
            )

        inv_date = request.invoice_date or date.today()
        amt_words = convert_number_to_words_inr(net_payable)

        # Generate PDF document
        pdf_payload = {
            "invoice_no": inv_no,
            "invoice_date": inv_date.strftime("%d/%m/%Y"),
            "agent_id": request.agent_id,
            "agent_name": agent_name,
            "posp_type": request.posp_type,
            "financial_year": request.financial_year,
            "month": request.month.upper(),
            "amount": amount,
            "gst_amt": gst_amt,
            "grand_total": grand_total,
            "tds_amount": tds_amount,
            "net_payable": net_payable,
            "amount_in_words": amt_words,
            "created_by": principal.username or "Admin",
            "status": "GENERATED",
        }
        pdf_bytes = generate_posp_invoice_pdf(pdf_payload)

        # Save to StorageBackend using canonical key
        canonical_key = f"invoices/{request.financial_year}/{request.agent_id}/{inv_no.replace('/', '_')}.pdf"
        self.storage.write_bytes(canonical_key, pdf_bytes)

        # Persist to database
        db_invoice = PospInvoice(
            InvoiceNo=inv_no,
            InvoiceDate=inv_date,
            AgentId=request.agent_id,
            AgentName=agent_name,
            POSPType=request.posp_type,
            FinancialYear=request.financial_year,
            Month=request.month.upper(),
            Amount=amount,
            GSTAmt=gst_amt,
            GrandTotal=grand_total,
            TDSAmount=tds_amount,
            NetPayable=net_payable,
            PdfPath=canonical_key,
            Status="GENERATED",
            CreatedDate=datetime.utcnow(),
            CreatedBy=principal.username or "Admin",
        )
        saved = await self.repo.create_posp_invoice(db_invoice)
        await self.session.commit()

        return {
            "invoice_id": saved.InvoiceId,
            "invoice_no": saved.InvoiceNo,
            "invoice_date": saved.InvoiceDate,
            "agent_id": saved.AgentId,
            "agent_name": saved.AgentName,
            "posp_type": saved.POSPType,
            "financial_year": saved.FinancialYear,
            "month": saved.Month,
            "amount": saved.Amount,
            "gst_amt": saved.GSTAmt,
            "grand_total": saved.GrandTotal,
            "tds_amount": saved.TDSAmount,
            "net_payable": saved.NetPayable,
            "pdf_path": saved.PdfPath,
            "status": saved.Status,
            "created_date": saved.CreatedDate,
            "created_by": saved.CreatedBy,
            "amount_in_words": amt_words,
        }

    async def get_posp_invoices(
        self,
        financial_year: Optional[str] = None,
        month: Optional[str] = None,
        agent_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 50,
        principal: Optional[PrincipalContext] = None,
    ) -> Dict[str, Any]:
        # If authenticated user is an agent, restrict strictly to self
        if principal and (principal.role_name or "").upper() in ("AGENT", "POSP", "FRANCHISE AGENT"):
            agent_id = principal.agent_id or principal.user_id

        invoices, total = await self.repo.get_posp_invoices(
            financial_year=financial_year,
            month=month,
            agent_id=agent_id,
            skip=skip,
            limit=limit,
        )

        items = []
        for inv in invoices:
            items.append({
                "invoice_id": inv.InvoiceId,
                "invoice_no": inv.InvoiceNo,
                "invoice_date": inv.InvoiceDate,
                "agent_id": inv.AgentId,
                "agent_name": inv.AgentName,
                "posp_type": inv.POSPType,
                "financial_year": inv.FinancialYear,
                "month": inv.Month,
                "amount": inv.Amount,
                "gst_amt": inv.GSTAmt,
                "grand_total": inv.GrandTotal,
                "tds_amount": inv.TDSAmount,
                "net_payable": inv.NetPayable,
                "pdf_path": inv.PdfPath,
                "status": inv.Status,
                "created_date": inv.CreatedDate,
                "created_by": inv.CreatedBy,
                "amount_in_words": convert_number_to_words_inr(inv.NetPayable),
            })

        return {
            "items": items,
            "total": total,
            "page": (skip // limit) + 1 if limit else 1,
            "page_size": limit,
        }

    async def get_posp_invoice_pdf(
        self,
        invoice_id: int,
        principal: Optional[PrincipalContext] = None,
    ) -> bytes:
        inv = await self.repo.get_posp_invoice_by_id(invoice_id)
        if not inv:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found.")

        # Access check
        if principal and (principal.role_name or "").upper() in ("AGENT", "POSP", "FRANCHISE AGENT"):
            eff_agent = principal.agent_id or principal.user_id
            if inv.AgentId != eff_agent:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access to other agent invoices denied.")

        if inv.PdfPath:
            try:
                return self.storage.read_bytes(inv.PdfPath)
            except Exception:
                pass

        # Regenerate on the fly if missing from storage
        pdf_payload = {
            "invoice_no": inv.InvoiceNo,
            "invoice_date": inv.InvoiceDate.strftime("%d/%m/%Y"),
            "agent_id": inv.AgentId,
            "agent_name": inv.AgentName,
            "posp_type": inv.POSPType,
            "financial_year": inv.FinancialYear,
            "month": inv.Month,
            "amount": inv.Amount,
            "gst_amt": inv.GSTAmt,
            "grand_total": inv.GrandTotal,
            "tds_amount": inv.TDSAmount,
            "net_payable": inv.NetPayable,
            "amount_in_words": convert_number_to_words_inr(inv.NetPayable),
            "created_by": inv.CreatedBy,
            "status": inv.Status,
        }
        return generate_posp_invoice_pdf(pdf_payload)

    async def get_agent_payout_reconciliation(
        self,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        agent_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        return await self.repo.get_agent_payout_reconciliation(from_date, to_date, agent_id)

    # =========================================================================
    # 4. Accounting & Statutory Reports
    # =========================================================================

    async def get_tds_register(
        self,
        from_date: date,
        to_date: date,
        agent_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        return await self.repo.get_tds_register(from_date, to_date, agent_id)

    async def export_tds_register(
        self,
        from_date: date,
        to_date: date,
        agent_id: Optional[int] = None,
    ) -> Tuple[bytes, str, str]:
        data = await self.repo.get_tds_register(from_date, to_date, agent_id)
        columns = ["Trans ID", "Voucher No", "Voucher Date", "Agent ID", "Agent Name", "Gross Commission", "TDS Rate %", "TDS Deducted", "Net Commission"]
        rows = [
            [
                it["trans_id"], it["voucher_no"], it["voucher_date"], it["agent_id"], it["agent_name"],
                it["gross_commission"], it["tds_rate"], it["tds_amount"], it["net_commission"]
            ]
            for it in data["items"]
        ]
        file_bytes = generate_excel_spreadsheet(columns, rows, sheet_name="TDS Register")
        filename = f"TdsRegister_{from_date}_{to_date}.xlsx"
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        return file_bytes, filename, media_type

    async def get_ledger_summary(self, from_date: date, to_date: date) -> List[Dict[str, Any]]:
        return await self.repo.get_ledger_type_summary(from_date, to_date)

    async def get_ledger_statement(self, ledger_m_id: int, from_date: date, to_date: date) -> Dict[str, Any]:
        return await self.repo.get_ledger_statement(ledger_m_id, from_date, to_date)

    async def get_voucher(self, voucher_id: int) -> Dict[str, Any]:
        v = await self.repo.get_voucher_by_id(voucher_id)
        if not v:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Voucher not found.")
        v["amount_in_words"] = convert_number_to_words_inr(v["amount"])
        return v

    async def get_voucher_pdf(self, voucher_id: int) -> bytes:
        v = await self.get_voucher(voucher_id)
        return generate_voucher_pdf(v)

    async def get_payment_advice(
        self,
        financial_year: str,
        month: str,
        agent_id: int,
        principal: Optional[PrincipalContext] = None,
    ) -> Dict[str, Any]:
        if principal and (principal.role_name or "").upper() in ("AGENT", "POSP", "FRANCHISE AGENT"):
            eff_agent = principal.agent_id or principal.user_id
            if agent_id != eff_agent:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
        return await self.repo.get_payment_advice(financial_year, month, agent_id)

    async def get_bank_commission_statement(
        self,
        financial_year: str,
        month: str,
        branch_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        return await self.repo.get_bank_commission_statement(financial_year, month, branch_id)

    async def get_daily_collection_audit(
        self,
        report_date: date,
        branch_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        return await self.repo.get_daily_collection_audit(report_date, branch_id)

    # =========================================================================
    # 5. Operations, Targets & Renewal Reports
    # =========================================================================

    async def get_commission_reconciliation(
        self,
        from_date: date,
        to_date: date,
        company_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        return await self.repo.get_commission_reconciliation(from_date, to_date, company_id)

    async def get_bank_reconciliation(
        self,
        from_date: date,
        to_date: date,
        bank_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        return await self.repo.get_bank_reconciliation(from_date, to_date, bank_id)

    async def get_endorsements(
        self,
        from_date: date,
        to_date: date,
        branch_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Dict[str, Any]:
        items, total = await self.repo.get_endorsement_report(from_date, to_date, branch_id, skip, limit)
        return {"items": items, "total": total}

    async def get_claims(
        self,
        from_date: date,
        to_date: date,
        status_filter: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Dict[str, Any]:
        items, total = await self.repo.get_claims_report(from_date, to_date, status_filter, skip, limit)
        return {"items": items, "total": total}

    async def get_telecaller_targets(
        self,
        financial_year: str,
        month: str,
        user_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        return await self.repo.get_telecaller_targets(financial_year, month, user_id)

    async def get_executive_targets(
        self,
        financial_year: str,
        month: str,
        user_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        return await self.repo.get_executive_targets(financial_year, month, user_id)

    async def get_expiring_policies(
        self,
        as_of_date: date,
        window_days: int = 30,
        branch_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        return await self.repo.get_expiring_policies(as_of_date, window_days, branch_id)
