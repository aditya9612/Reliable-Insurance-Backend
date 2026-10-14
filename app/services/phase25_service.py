"""
Phase 25 Service Layer:
Corporate Group Clients, Commercial Sales Invoicing & Sister Concern Advances.
"""
from datetime import datetime, date
from decimal import Decimal, ROUND_HALF_EVEN
from typing import List, Optional, Tuple, Dict, Any
from fastapi import HTTPException, status
from sqlalchemy import select, update, func, delete, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.phase25_features import (
    SalesType,
    ReliableCompany,
    ClientMaster,
    SalesRegDetails,
    CompanyAdvanceMaster,
    CompanyAdvDetail,
    InvoiceSequence,
)
from app.models.phase18a_features import SalesRegistration
from app.models.account import Account
from app.models.user import User
from app.schemas.phase25 import (
    SalesTypeCreate,
    SalesTypeUpdate,
    SalesTypeResponse,
    ReliableCompanyCreate,
    ReliableCompanyUpdate,
    ReliableCompanyResponse,
    ClientMasterCreate,
    ClientMasterUpdate,
    ClientMasterResponse,
    CommercialInvoiceCreateRequest,
    CommercialInvoiceResponse,
    CommercialInvoiceLineItemResponse,
    CommercialSalesRegisterReportItem,
    CommercialSalesRegisterReportResponse,
    CompanyAdvanceCreateRequest,
    CompanyAdvanceResponse,
    CompanyAdvanceRecoveryRequest,
    CompanyAdvanceRecoveryResponse,
    CompanyAdvanceDetailItem,
    CompanyAdvanceReportResponse,
)

# Precision Constants
ZERO = Decimal("0.00")
ONE_RUPEE = Decimal("1")
CENTS = Decimal("0.01")


def round_bankers_rupee(val: Decimal) -> Decimal:
    """Exact parity with C# Math.Round(double) -> MidpointRounding.ToEven to 0 decimals."""
    return val.quantize(ONE_RUPEE, rounding=ROUND_HALF_EVEN)


def _q2(val: Any) -> Decimal:
    """Formats numeric value to 2 decimal places."""
    if val is None:
        return ZERO
    if isinstance(val, Decimal):
        return val.quantize(CENTS)
    return Decimal(str(val)).quantize(CENTS)


class Phase25Service:
    def __init__(self, db: AsyncSession):
        self.db = db

    # =========================================================================
    # 1. COMMERCIAL SALES TYPES (tbl_salestype)
    # =========================================================================

    async def create_sales_type(self, payload: SalesTypeCreate) -> SalesTypeResponse:
        # Check duplicate description
        clean_desc = payload.Description.strip()
        stmt = select(SalesType).where(func.lower(SalesType.Description) == clean_desc.lower())
        existing = (await self.db.execute(stmt)).scalar_one_or_none()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"SalesType with description '{clean_desc}' already exists.",
            )

        st = SalesType(
            Description=clean_desc,
            IsActive=payload.IsActive,
            CreatedDate=datetime.utcnow(),
        )
        self.db.add(st)
        await self.db.commit()
        await self.db.refresh(st)
        return SalesTypeResponse.model_validate(st)

    async def get_sales_type(self, sales_type_id: int) -> SalesTypeResponse:
        st = await self.db.get(SalesType, sales_type_id)
        if not st:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"SalesType {sales_type_id} not found.",
            )
        return SalesTypeResponse.model_validate(st)

    async def list_sales_types(self, is_active: Optional[bool] = None) -> List[SalesTypeResponse]:
        stmt = select(SalesType)
        if is_active is not None:
            stmt = stmt.where(SalesType.IsActive == is_active)
        stmt = stmt.order_by(SalesType.SalesTypeId.asc())
        rows = (await self.db.execute(stmt)).scalars().all()
        return [SalesTypeResponse.model_validate(r) for r in rows]

    async def update_sales_type(self, sales_type_id: int, payload: SalesTypeUpdate) -> SalesTypeResponse:
        st = await self.db.get(SalesType, sales_type_id)
        if not st:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"SalesType {sales_type_id} not found.",
            )
        if payload.Description is not None:
            clean_desc = payload.Description.strip()
            # check duplicate with other IDs
            stmt = select(SalesType).where(
                func.lower(SalesType.Description) == clean_desc.lower(),
                SalesType.SalesTypeId != sales_type_id,
            )
            existing = (await self.db.execute(stmt)).scalar_one_or_none()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"SalesType with description '{clean_desc}' already exists.",
                )
            st.Description = clean_desc
        if payload.IsActive is not None:
            st.IsActive = payload.IsActive

        await self.db.commit()
        await self.db.refresh(st)
        return SalesTypeResponse.model_validate(st)

    async def delete_sales_type(self, sales_type_id: int, hard_delete: bool = False) -> Dict[str, Any]:
        st = await self.db.get(SalesType, sales_type_id)
        if not st:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"SalesType {sales_type_id} not found.",
            )

        # Check references in SalesRegistration or SalesRegDetails
        ref_reg = await self.db.execute(
            select(func.count(SalesRegistration.salesRegId)).where(SalesRegistration.SalesTypeId == sales_type_id)
        )
        ref_det = await self.db.execute(
            select(func.count(SalesRegDetails.SalesRegDetailId)).where(SalesRegDetails.SalesTypeId == sales_type_id)
        )
        total_refs = (ref_reg.scalar() or 0) + (ref_det.scalar() or 0)

        if total_refs > 0 and hard_delete:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot permanently delete SalesType {sales_type_id}: referenced by {total_refs} commercial invoices.",
            )

        if hard_delete:
            await self.db.delete(st)
            await self.db.commit()
            return {"deleted": True, "sales_type_id": sales_type_id, "mode": "hard"}
        else:
            st.IsActive = False
            await self.db.commit()
            return {"deleted": True, "sales_type_id": sales_type_id, "mode": "soft"}

    # =========================================================================
    # 2. RELIABLE GROUP COMPANIES (tbl_reliablecompanymst)
    # =========================================================================

    async def create_reliable_company(self, payload: ReliableCompanyCreate) -> ReliableCompanyResponse:
        clean_company = payload.RCompany.strip()
        clean_prefix = payload.Prefix.strip().upper()

        stmt = select(ReliableCompany).where(
            or_(
                func.lower(ReliableCompany.RCompany) == clean_company.lower(),
                func.upper(ReliableCompany.Prefix) == clean_prefix,
            )
        )
        existing = (await self.db.execute(stmt)).scalar_one_or_none()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"ReliableCompany '{clean_company}' or prefix '{clean_prefix}' already exists.",
            )

        rc = ReliableCompany(
            RCompany=clean_company,
            Prefix=clean_prefix,
            LedgerMId=payload.LedgerMId,
            IsActive=payload.IsActive,
            CreatedDate=datetime.utcnow(),
        )
        self.db.add(rc)
        await self.db.commit()
        await self.db.refresh(rc)
        return ReliableCompanyResponse.model_validate(rc)

    async def get_reliable_company(self, r_company_id: int) -> ReliableCompanyResponse:
        rc = await self.db.get(ReliableCompany, r_company_id)
        if not rc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"ReliableCompany {r_company_id} not found.",
            )
        return ReliableCompanyResponse.model_validate(rc)

    async def list_reliable_companies(self, is_active: Optional[bool] = None) -> List[ReliableCompanyResponse]:
        stmt = select(ReliableCompany)
        if is_active is not None:
            stmt = stmt.where(ReliableCompany.IsActive == is_active)
        stmt = stmt.order_by(ReliableCompany.RCompanyId.asc())
        rows = (await self.db.execute(stmt)).scalars().all()
        return [ReliableCompanyResponse.model_validate(r) for r in rows]

    async def update_reliable_company(self, r_company_id: int, payload: ReliableCompanyUpdate) -> ReliableCompanyResponse:
        rc = await self.db.get(ReliableCompany, r_company_id)
        if not rc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"ReliableCompany {r_company_id} not found.",
            )
        if payload.RCompany is not None:
            rc.RCompany = payload.RCompany.strip()
        if payload.Prefix is not None:
            clean_prefix = payload.Prefix.strip().upper()
            stmt = select(ReliableCompany).where(
                func.upper(ReliableCompany.Prefix) == clean_prefix,
                ReliableCompany.RCompanyId != r_company_id,
            )
            existing = (await self.db.execute(stmt)).scalar_one_or_none()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Prefix '{clean_prefix}' is already used by another ReliableCompany.",
                )
            rc.Prefix = clean_prefix
        if payload.LedgerMId is not None:
            rc.LedgerMId = payload.LedgerMId
        if payload.IsActive is not None:
            rc.IsActive = payload.IsActive

        await self.db.commit()
        await self.db.refresh(rc)
        return ReliableCompanyResponse.model_validate(rc)

    async def delete_reliable_company(self, r_company_id: int, hard_delete: bool = False) -> Dict[str, Any]:
        rc = await self.db.get(ReliableCompany, r_company_id)
        if not rc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"ReliableCompany {r_company_id} not found.",
            )

        ref_reg = await self.db.execute(
            select(func.count(SalesRegistration.salesRegId)).where(SalesRegistration.RCompanyId == r_company_id)
        )
        total_refs = ref_reg.scalar() or 0
        if total_refs > 0 and hard_delete:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot permanently delete ReliableCompany {r_company_id}: referenced by {total_refs} commercial invoices.",
            )

        if hard_delete:
            await self.db.delete(rc)
            await self.db.commit()
            return {"deleted": True, "r_company_id": r_company_id, "mode": "hard"}
        else:
            rc.IsActive = False
            await self.db.commit()
            return {"deleted": True, "r_company_id": r_company_id, "mode": "soft"}

    # =========================================================================
    # 3. CORPORATE GROUP CLIENTS (tbl_clientmaster)
    # =========================================================================

    async def create_client_master(self, payload: ClientMasterCreate, user_name: Optional[str] = None) -> ClientMasterResponse:
        clean_desc = payload.Description.strip()
        cm = ClientMaster(
            Description=clean_desc,
            InsuranceCompanyId=payload.InsuranceCompanyId,
            Address=payload.Address.strip() if payload.Address else None,
            PanNo=payload.PanNo,
            GST=payload.GST,
            CGST=_q2(payload.CGST),
            SGST=_q2(payload.SGST),
            IGST=_q2(payload.IGST),
            IsActive=payload.IsActive,
            CreatedUser=user_name or "SYSTEM",
            Createdate=datetime.utcnow(),
        )
        self.db.add(cm)
        await self.db.commit()
        await self.db.refresh(cm)
        return ClientMasterResponse.model_validate(cm)

    async def get_client_master(self, client_master_id: int) -> ClientMasterResponse:
        cm = await self.db.get(ClientMaster, client_master_id)
        if not cm:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"ClientMaster {client_master_id} not found.",
            )
        return ClientMasterResponse.model_validate(cm)

    async def list_client_masters(
        self,
        search: Optional[str] = None,
        insurance_company_id: Optional[int] = None,
        is_active: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[ClientMasterResponse]:
        stmt = select(ClientMaster)
        if is_active is not None:
            stmt = stmt.where(ClientMaster.IsActive == is_active)
        if insurance_company_id is not None:
            stmt = stmt.where(ClientMaster.InsuranceCompanyId == insurance_company_id)
        if search:
            kw = f"%{search.strip().lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(ClientMaster.Description).like(kw),
                    func.lower(ClientMaster.GST).like(kw),
                    func.lower(ClientMaster.PanNo).like(kw),
                )
            )
        stmt = stmt.order_by(ClientMaster.ClientMasterId.desc()).offset(skip).limit(limit)
        rows = (await self.db.execute(stmt)).scalars().all()
        return [ClientMasterResponse.model_validate(r) for r in rows]

    async def update_client_master(self, client_master_id: int, payload: ClientMasterUpdate) -> ClientMasterResponse:
        cm = await self.db.get(ClientMaster, client_master_id)
        if not cm:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"ClientMaster {client_master_id} not found.",
            )
        if payload.Description is not None:
            cm.Description = payload.Description.strip()
        if payload.InsuranceCompanyId is not None:
            cm.InsuranceCompanyId = payload.InsuranceCompanyId
        if payload.Address is not None:
            cm.Address = payload.Address.strip() if payload.Address else None
        if payload.PanNo is not None:
            cm.PanNo = payload.PanNo
        if payload.GST is not None:
            cm.GST = payload.GST
        if payload.CGST is not None:
            cm.CGST = _q2(payload.CGST)
        if payload.SGST is not None:
            cm.SGST = _q2(payload.SGST)
        if payload.IGST is not None:
            cm.IGST = _q2(payload.IGST)
        if payload.IsActive is not None:
            cm.IsActive = payload.IsActive

        await self.db.commit()
        await self.db.refresh(cm)
        return ClientMasterResponse.model_validate(cm)

    async def delete_client_master(self, client_master_id: int, hard_delete: bool = False) -> Dict[str, Any]:
        cm = await self.db.get(ClientMaster, client_master_id)
        if not cm:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"ClientMaster {client_master_id} not found.",
            )
        ref_reg = await self.db.execute(
            select(func.count(SalesRegistration.salesRegId)).where(SalesRegistration.ClientMasterId == client_master_id)
        )
        total_refs = ref_reg.scalar() or 0
        if total_refs > 0 and hard_delete:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot permanently delete ClientMaster {client_master_id}: referenced by {total_refs} commercial invoices.",
            )

        if hard_delete:
            await self.db.delete(cm)
            await self.db.commit()
            return {"deleted": True, "client_master_id": client_master_id, "mode": "hard"}
        else:
            cm.IsActive = False
            await self.db.commit()
            return {"deleted": True, "client_master_id": client_master_id, "mode": "soft"}

    # =========================================================================
    # 4. INVOICE SEQUENCING & CONCURRENCY-SAFE NUMBER ALLOCATION
    # =========================================================================

    async def preview_next_invoice_number(self, r_company_id: int) -> Dict[str, Any]:
        rc = await self.db.get(ReliableCompany, r_company_id)
        if not rc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"ReliableCompany {r_company_id} not found.",
            )
        seq_stmt = select(InvoiceSequence.CurrentValue).where(InvoiceSequence.SequenceName == "COMMERCIAL_SALES")
        cur_val = (await self.db.execute(seq_stmt)).scalar() or 1000
        preview_no = f"{rc.Prefix}/{cur_val + 1}"
        return {
            "r_company_id": r_company_id,
            "prefix": rc.Prefix,
            "next_sequence": cur_val + 1,
            "preview_invoice_no": preview_no,
        }

    async def _allocate_invoice_number(self, prefix: str) -> str:
        """
        Atomically allocates the next sequential invoice number with collision avoidance.
        Must be executed within an active database transaction.
        Uses native database upsert to safely initialize the counter row under concurrency.

        BUSINESS DECISION (Approved):
        - Counter initialized to 1000 by default (producing 1001 as first number). This is an explicit
          synthetic default, not verified legacy behavior (legacy sp_generatesalesregistrationInvoice
          was parameterless, but its SQL body was stored in production DB and unavailable in repo dumps).
        - Before production deployment, the 'COMMERCIAL_SALES' counter in `tbl_invoicesequence` must be
          reconciled against actual legacy numbering and historical production invoices.
        """
        dialect_name = self.db.bind.dialect.name if self.db.bind else "mysql"
        now_dt = datetime.utcnow()

        # Concurrency-safe initialization of COMMERCIAL_SALES counter row
        if dialect_name == "sqlite":
            from sqlalchemy.dialects.sqlite import insert as sqlite_insert
            init_stmt = (
                sqlite_insert(InvoiceSequence)
                .values(SequenceName="COMMERCIAL_SALES", CurrentValue=1000, UpdatedDate=now_dt)
                .on_conflict_do_nothing()
            )
        else:
            from sqlalchemy.dialects.mysql import insert as mysql_insert
            init_stmt = (
                mysql_insert(InvoiceSequence)
                .values(SequenceName="COMMERCIAL_SALES", CurrentValue=1000, UpdatedDate=now_dt)
                .on_duplicate_key_update(SequenceName=InvoiceSequence.SequenceName)
            )
        await self.db.execute(init_stmt)

        # Row-level lock on sequence counter
        seq_stmt = (
            select(InvoiceSequence)
            .where(InvoiceSequence.SequenceName == "COMMERCIAL_SALES")
            .with_for_update()
        )
        seq = (await self.db.execute(seq_stmt)).scalar_one()

        while True:
            seq.CurrentValue += 1
            candidate_no = f"{prefix}/{seq.CurrentValue}"
            # Check collision with out-of-band existing records
            dup_stmt = select(SalesRegistration.salesRegId).where(SalesRegistration.InvoiceNo == candidate_no)
            if (await self.db.execute(dup_stmt)).scalar_one_or_none() is None:
                seq.UpdatedDate = datetime.utcnow()
                return candidate_no

    async def _allocate_doc_no(self) -> int:
        """
        Allocates next monotonic Doc_No for tbl_account matching repository convention.
        Coordinated across all accounting writers via CommissionAccountingRepository.
        """
        from app.repositories.commission_accounting import CommissionAccountingRepository
        repo = CommissionAccountingRepository(self.db)
        return await repo.allocate_next_doc_no()

    # =========================================================================
    # 5. COMMERCIAL INVOICE GENERATION & ATOMIC REVENUE BOOKING
    # =========================================================================

    async def create_commercial_invoice(
        self, payload: CommercialInvoiceCreateRequest, current_user: User
    ) -> CommercialInvoiceResponse:
        # Validate foreign entities
        rc = await self.db.get(ReliableCompany, payload.r_company_id)
        if not rc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"ReliableCompany {payload.r_company_id} not found.",
            )
        cm = await self.db.get(ClientMaster, payload.client_master_id)
        if not cm:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"ClientMaster {payload.client_master_id} not found.",
            )

        # 1. Calculate each line item with Banker's Rounding parity
        # BUSINESS DECISION (Approved):
        # In legacy WebForms (adm_SalesRegistrationNew.aspx.cs lines 238-239), the UI computed
        # header Total as Math.Round(totBT + totGST), while detail rows computed Math.Round(line.Taxable + line.Taxes).
        # On multi-line invoices with fractional cents, this legacy behavior produced an internal ₹1 discrepancy
        # between header total and sum of detail rows.
        # Under this approved business decision, Phase 25 enforces strict Sum-of-Line-Totals aggregation:
        # Header Total = sum(line.Total) = abs(Account.amount).
        # This is an intentional accounting safety improvement over legacy multi-line rounding behavior.
        calculated_items = []
        tot_taxable = Decimal("0.00")
        tot_cgst = Decimal("0.00")
        tot_sgst = Decimal("0.00")
        tot_igst = Decimal("0.00")
        tot_grand = Decimal("0.00")

        for item in payload.items:
            # Preserves unrounded base taxable amount cents
            t_amt = _q2(item.taxable_amt)
            c_per = _q2(item.cgst_per)
            s_per = _q2(item.sgst_per)
            i_per = _q2(item.igst_per)

            # Round tax components to whole rupee using Banker's Rounding (MidpointRounding.ToEven)
            cgst_amt = round_bankers_rupee((t_amt * c_per) / Decimal("100.00"))
            sgst_amt = round_bankers_rupee((t_amt * s_per) / Decimal("100.00"))
            igst_amt = round_bankers_rupee((t_amt * i_per) / Decimal("100.00"))

            # Line total: taxable + integer tax components, rounded to nearest rupee
            line_total = round_bankers_rupee(t_amt + cgst_amt + sgst_amt + igst_amt)

            tot_taxable += t_amt
            tot_cgst += cgst_amt
            tot_sgst += sgst_amt
            tot_igst += igst_amt
            tot_grand += line_total

            calculated_items.append({
                "sales_type": item.sales_type,
                "sales_type_id": item.sales_type_id,
                "taxable_amt": t_amt,
                "cgst_per": c_per,
                "cgst_amt": cgst_amt.quantize(CENTS),
                "sgst_per": s_per,
                "sgst_amt": sgst_amt.quantize(CENTS),
                "igst_per": i_per,
                "igst_amt": igst_amt.quantize(CENTS),
                "total": line_total.quantize(CENTS),
            })

        # Ensure single atomic transaction
        # If payload provides a custom invoice_no, validate uniqueness
        if payload.invoice_no:
            cand_no = payload.invoice_no.strip()
            dup = await self.db.execute(
                select(SalesRegistration.salesRegId).where(SalesRegistration.InvoiceNo == cand_no)
            )
            if dup.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Invoice number '{cand_no}' already exists in database.",
                )
            final_invoice_no = cand_no
        else:
            final_invoice_no = await self._allocate_invoice_number(rc.Prefix)

        doc_no = await self._allocate_doc_no()

        # 2. Persist SalesRegistration Header
        header = SalesRegistration(
            InvoiceNo=final_invoice_no,
            RegistrationType=payload.registration_type,
            SalesDate=payload.sales_date,
            RCompanyId=payload.r_company_id,
            SalesTypeId=payload.sales_type_id or 1,
            SalesType=calculated_items[0]["sales_type"] or "COMMERCIAL_INVOICE",
            ClientMasterId=payload.client_master_id,
            LedgerMId=payload.ledger_m_id or rc.LedgerMId,
            Description=payload.description,
            amount=tot_taxable.quantize(CENTS),
            CGSTPer=calculated_items[0]["cgst_per"],
            CGSTAmt=tot_cgst.quantize(CENTS),
            SGSTPer=calculated_items[0]["sgst_per"],
            SGSTAmt=tot_sgst.quantize(CENTS),
            IGSTPer=calculated_items[0]["igst_per"],
            IGSTAmt=tot_igst.quantize(CENTS),
            Total=tot_grand.quantize(CENTS),
            ReceivedAmt=Decimal("0.00"),
            BalanceAmt=tot_grand.quantize(CENTS),
            AccDocNo=str(doc_no),
            CreatedUser=current_user.UserId,
            Createdate=datetime.utcnow(),
        )
        self.db.add(header)
        await self.db.flush()

        # 3. Persist SalesRegDetails Line Items
        line_records = []
        for c in calculated_items:
            det = SalesRegDetails(
                InvoiceId=header.salesRegId,
                InvoiceNo=final_invoice_no,
                SalesType=c["sales_type"],
                SalesTypeId=c["sales_type_id"],
                TaxableAmt=c["taxable_amt"],
                CGSTPre=c["cgst_per"],
                CGSTAmt=c["cgst_amt"],
                SGSTPre=c["sgst_per"],
                SGSTAmt=c["sgst_amt"],
                IGSTPre=c["igst_per"],
                IGSTAmt=c["igst_amt"],
                Total=c["total"],
            )
            self.db.add(det)
            line_records.append(det)

        # 4. Post Balanced Double-Entry Revenue Entry in tbl_account
        account_entry = Account(
            AccTransId=1,                                    # Verified legacy constant
            AccountDate=datetime.combine(payload.sales_date, datetime.min.time()),
            LedgerMId=2756,                                  # Verified legacy sales revenue ledger
            amount=-tot_grand.quantize(CENTS),               # Verified negative credit polarity
            Narration="sales Registration Amount",           # Verified exact legacy literal
            ReferenceCustId=payload.client_master_id,
            ReferenceAgentId=0,
            BranchId=current_user.BranchId or 1,
            Extra1=final_invoice_no,
            Extra2=str(payload.r_company_id),
            Doc_No=doc_no,
            CreatedUser=str(current_user.UserId),
            CreatedDate=datetime.utcnow(),
            PaymentType="",
            isdeleted=0,
            IsNill=0,
            TransactionId=0,
            CustVehId=0,
            MonthId=payload.sales_date.month,
            EndorsementId=0,
            TransId=0,
        )
        self.db.add(account_entry)

        await self.db.commit()
        await self.db.refresh(header)
        for det in line_records:
            await self.db.refresh(det)

        resp = CommercialInvoiceResponse.model_validate(header)
        resp.items = [CommercialInvoiceLineItemResponse.model_validate(det) for det in line_records]
        return resp

    async def list_commercial_invoices(
        self,
        client_master_id: Optional[int] = None,
        r_company_id: Optional[int] = None,
        invoice_no: Optional[str] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[CommercialInvoiceResponse]:
        stmt = select(SalesRegistration)
        if client_master_id is not None:
            stmt = stmt.where(SalesRegistration.ClientMasterId == client_master_id)
        if r_company_id is not None:
            stmt = stmt.where(SalesRegistration.RCompanyId == r_company_id)
        if invoice_no:
            stmt = stmt.where(SalesRegistration.InvoiceNo.like(f"%{invoice_no.strip()}%"))
        if from_date:
            stmt = stmt.where(SalesRegistration.SalesDate >= from_date)
        if to_date:
            stmt = stmt.where(SalesRegistration.SalesDate <= to_date)

        stmt = stmt.order_by(SalesRegistration.salesRegId.desc()).offset(skip).limit(limit)
        headers = (await self.db.execute(stmt)).scalars().all()

        results = []
        for h in headers:
            det_stmt = select(SalesRegDetails).where(SalesRegDetails.InvoiceId == h.salesRegId)
            details = (await self.db.execute(det_stmt)).scalars().all()
            resp = CommercialInvoiceResponse.model_validate(h)
            resp.items = [CommercialInvoiceLineItemResponse.model_validate(d) for d in details]
            results.append(resp)
        return results

    async def get_commercial_invoice(self, sales_reg_id: int) -> CommercialInvoiceResponse:
        header = await self.db.get(SalesRegistration, sales_reg_id)
        if not header:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Commercial Invoice {sales_reg_id} not found.",
            )
        det_stmt = select(SalesRegDetails).where(SalesRegDetails.InvoiceId == header.salesRegId)
        details = (await self.db.execute(det_stmt)).scalars().all()
        resp = CommercialInvoiceResponse.model_validate(header)
        resp.items = [CommercialInvoiceLineItemResponse.model_validate(d) for d in details]
        return resp

    # =========================================================================
    # 6. SISTER CONCERN ADVANCES & RECOVERY ENGINE (tbl_companyadvancemaster)
    # =========================================================================

    async def create_advance(
        self, payload: CompanyAdvanceCreateRequest, current_user: User
    ) -> CompanyAdvanceResponse:
        amt = _q2(payload.amount)
        adv = CompanyAdvanceMaster(
            LedgerMID=payload.ledger_m_id,
            compAdvDate=payload.advance_date,
            Amount=amt,
            RecivingAmount=Decimal("0.00"),
            BalanceAmt=amt,
            Description=payload.description,
            CreatedUser=str(current_user.UserId),
            CreatedDate=datetime.utcnow(),
        )
        self.db.add(adv)
        await self.db.commit()
        await self.db.refresh(adv)
        return CompanyAdvanceResponse.model_validate(adv)

    async def recover_advance(
        self, advance_id: int, payload: CompanyAdvanceRecoveryRequest, current_user: User
    ) -> CompanyAdvanceRecoveryResponse:
        # Validate positive recovery amount
        recd_amt = _q2(payload.recovery_amount)
        if recd_amt <= Decimal("0.00"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Recovery amount ({recd_amt}) must be greater than zero.",
            )

        # Lock advance row with FOR UPDATE
        stmt = (
            select(CompanyAdvanceMaster)
            .where(CompanyAdvanceMaster.CompanyAdvId == advance_id)
            .with_for_update()
        )
        adv = (await self.db.execute(stmt)).scalar_one_or_none()
        if not adv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"CompanyAdvance {advance_id} not found.",
            )

        current_bal = _q2(adv.BalanceAmt)
        if recd_amt > current_bal:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Recovery amount ({recd_amt}) cannot exceed available advance balance ({current_bal}).",
            )

        # Duplicate voucher protection
        if payload.acc_doc_no:
            clean_doc = payload.acc_doc_no.strip()
            dup_stmt = (
                select(CompanyAdvDetail)
                .where(
                    CompanyAdvDetail.CompanyAdvId == advance_id,
                    CompanyAdvDetail.AccDocNo == clean_doc,
                )
                .with_for_update()
            )
            dup = (await self.db.execute(dup_stmt)).scalar_one_or_none()
            if dup:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Voucher AccDocNo '{clean_doc}' has already been processed against this advance.",
                )

        # Update advance balances
        adv.RecivingAmount = _q2(adv.RecivingAmount + recd_amt)
        adv.BalanceAmt = _q2(current_bal - recd_amt)

        # Record history detail log
        detail = CompanyAdvDetail(
            CompanyAdvId=advance_id,
            LedgerMID=adv.LedgerMID,
            HistoryDate=payload.recovery_date,
            SalesInvoiceId=payload.sales_invoice_id,
            AccDocNo=payload.acc_doc_no,
            Amount=recd_amt,
            CreatedDate=datetime.utcnow(),
        )
        self.db.add(detail)

        # If linked to a sales invoice, adjust invoice balance synchronously
        if payload.sales_invoice_id:
            inv_stmt = select(SalesRegistration).where(
                SalesRegistration.InvoiceNo == payload.sales_invoice_id.strip()
            )
            inv = (await self.db.execute(inv_stmt)).scalar_one_or_none()
            if inv:
                inv.ReceivedAmt = _q2(inv.ReceivedAmt + recd_amt)
                inv.BalanceAmt = _q2(max(Decimal("0.00"), inv.Total - inv.ReceivedAmt))

        await self.db.commit()
        await self.db.refresh(adv)
        await self.db.refresh(detail)

        return CompanyAdvanceRecoveryResponse(
            advance=CompanyAdvanceResponse.model_validate(adv),
            detail_id=detail.DetailId,
            recovered_amount=recd_amt,
            acc_doc_no=detail.AccDocNo,
            sales_invoice_id=detail.SalesInvoiceId,
        )

    async def list_advances(self, ledger_m_id: Optional[int] = None) -> List[CompanyAdvanceResponse]:
        stmt = select(CompanyAdvanceMaster)
        if ledger_m_id is not None:
            stmt = stmt.where(CompanyAdvanceMaster.LedgerMID == ledger_m_id)
        stmt = stmt.order_by(CompanyAdvanceMaster.CompanyAdvId.desc())
        rows = (await self.db.execute(stmt)).scalars().all()
        return [CompanyAdvanceResponse.model_validate(r) for r in rows]

    # =========================================================================
    # 7. REPORTING (SALES REGISTER & ADVANCE RECOVERY HISTORY)
    # =========================================================================

    async def get_sales_register_report(
        self,
        r_company_id: Optional[int] = None,
        client_master_id: Optional[int] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        invoice_no: Optional[str] = None,
    ) -> CommercialSalesRegisterReportResponse:
        stmt = select(SalesRegistration)
        if r_company_id is not None:
            stmt = stmt.where(SalesRegistration.RCompanyId == r_company_id)
        if client_master_id is not None:
            stmt = stmt.where(SalesRegistration.ClientMasterId == client_master_id)
        if invoice_no:
            stmt = stmt.where(SalesRegistration.InvoiceNo.like(f"%{invoice_no.strip()}%"))
        if from_date:
            stmt = stmt.where(SalesRegistration.SalesDate >= from_date)
        if to_date:
            stmt = stmt.where(SalesRegistration.SalesDate <= to_date)

        stmt = stmt.order_by(SalesRegistration.SalesDate.asc(), SalesRegistration.salesRegId.asc())
        rows = (await self.db.execute(stmt)).scalars().all()

        report_items = []
        tot_taxable = Decimal("0.00")
        tot_cgst = Decimal("0.00")
        tot_sgst = Decimal("0.00")
        tot_igst = Decimal("0.00")
        tot_grand = Decimal("0.00")
        tot_recd = Decimal("0.00")
        tot_bal = Decimal("0.00")

        # Prefetch company and client maps
        c_map = {}
        r_map = {}
        for r in rows:
            if r.ClientMasterId and r.ClientMasterId not in c_map:
                c = await self.db.get(ClientMaster, r.ClientMasterId)
                c_map[r.ClientMasterId] = c.Description if c else "Unknown"
            if r.RCompanyId and r.RCompanyId not in r_map:
                rc = await self.db.get(ReliableCompany, r.RCompanyId)
                r_map[r.RCompanyId] = rc.RCompany if rc else "Unknown"

            item = CommercialSalesRegisterReportItem(
                sales_reg_id=r.salesRegId,
                sales_date=r.SalesDate,
                r_company=r_map.get(r.RCompanyId),
                invoice_no=r.InvoiceNo,
                sales_type=r.SalesType,
                client_name=c_map.get(r.ClientMasterId),
                description=r.Description,
                amount=_q2(r.amount),
                cgst_per=_q2(r.CGSTPer),
                cgst_amt=_q2(r.CGSTAmt),
                sgst_per=_q2(r.SGSTPer),
                sgst_amt=_q2(r.SGSTAmt),
                igst_per=_q2(r.IGSTPer),
                igst_amt=_q2(r.IGSTAmt),
                total=_q2(r.Total),
                received_amt=_q2(r.ReceivedAmt),
                balance_amt=_q2(r.BalanceAmt),
            )
            report_items.append(item)
            tot_taxable += _q2(r.amount)
            tot_cgst += _q2(r.CGSTAmt)
            tot_sgst += _q2(r.SGSTAmt)
            tot_igst += _q2(r.IGSTAmt)
            tot_grand += _q2(r.Total)
            tot_recd += _q2(r.ReceivedAmt)
            tot_bal += _q2(r.BalanceAmt)

        return CommercialSalesRegisterReportResponse(
            items=report_items,
            total_taxable=tot_taxable.quantize(CENTS),
            total_cgst=tot_cgst.quantize(CENTS),
            total_sgst=tot_sgst.quantize(CENTS),
            total_igst=tot_igst.quantize(CENTS),
            total_grand=tot_grand.quantize(CENTS),
            total_received=tot_recd.quantize(CENTS),
            total_balance=tot_bal.quantize(CENTS),
            count=len(report_items),
        )

    async def get_advance_report(
        self, advance_id: Optional[int] = None, ledger_m_id: Optional[int] = None
    ) -> CompanyAdvanceReportResponse:
        stmt = select(CompanyAdvanceMaster)
        if advance_id is not None:
            stmt = stmt.where(CompanyAdvanceMaster.CompanyAdvId == advance_id)
        if ledger_m_id is not None:
            stmt = stmt.where(CompanyAdvanceMaster.LedgerMID == ledger_m_id)
        stmt = stmt.order_by(CompanyAdvanceMaster.CompanyAdvId.asc())
        adv_rows = (await self.db.execute(stmt)).scalars().all()

        det_stmt = select(CompanyAdvDetail)
        if advance_id is not None:
            det_stmt = det_stmt.where(CompanyAdvDetail.CompanyAdvId == advance_id)
        if ledger_m_id is not None:
            det_stmt = det_stmt.where(CompanyAdvDetail.LedgerMID == ledger_m_id)
        det_stmt = det_stmt.order_by(CompanyAdvDetail.DetailId.asc())
        det_rows = (await self.db.execute(det_stmt)).scalars().all()

        tot_adv = sum([_q2(a.Amount) for a in adv_rows], ZERO)
        tot_recd = sum([_q2(a.RecivingAmount) for a in adv_rows], ZERO)
        tot_bal = sum([_q2(a.BalanceAmt) for a in adv_rows], ZERO)

        return CompanyAdvanceReportResponse(
            advances=[CompanyAdvanceResponse.model_validate(a) for a in adv_rows],
            details=[CompanyAdvanceDetailItem.model_validate(d) for d in det_rows],
            total_advance_amount=tot_adv.quantize(CENTS),
            total_recovered_amount=tot_recd.quantize(CENTS),
            total_balance_amount=tot_bal.quantize(CENTS),
        )
