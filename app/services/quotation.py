"""
Service Layer for Phase 6 Quotation & Rating Engine.
Orchestrates:
- Deterministic motor rating calculation & multi-insurer comparison
- Self-Quotation persistence, code generation, and ownership-scoped retrieval
- Assisted Quotation Request lifecycle (Create, Update/Resubmit, Attend, Revert, Generate Quotes, Cancel/Soft-Delete)
- Phase 7 Policy Proposal prefill data contract
"""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import (
    AGENT_PRINCIPAL_ROLES,
    EMPLOYEE_PRINCIPAL_ROLES,
    FRANCHISE_PRINCIPAL_ROLES,
    PrincipalContext,
    _normalize,
    is_global_admin_role,
    is_global_read_role,
    is_quotation_coordinator_role,
)
from app.models.quotation import AppQuatationEntry, AppQuotationRequest
from app.models.user import User
from app.repositories.quotation import QuotationRepository, _to_decimal
from app.schemas.quotation import (
    AssistedQuotationListResponse,
    AssistedQuotationRequestCreate,
    AssistedQuotationRequestResponse,
    AssistedQuotationRequestUpdate,
    GenerateInsurerQuotesRequest,
    InsurerQuoteOptionResponse,
    MultiInsurerCompareRequest,
    MultiInsurerCompareResponse,
    PolicyPrefillResponse,
    PremiumBreakdownResponse,
    PremiumCalculationRequest,
    QuotationAttendRequest,
    QuotationRemarkResponse,
    QuotationStatusTransitionRequest,
    SelfQuotationCreateRequest,
    SelfQuotationListResponse,
    SelfQuotationResponse,
)
from app.services.rating import RatingEngineService


_AGENT_ROLES_NORM = frozenset(_normalize(r) for r in AGENT_PRINCIPAL_ROLES)
_EMPLOYEE_ROLES_NORM = frozenset(_normalize(r) for r in EMPLOYEE_PRINCIPAL_ROLES)
_FRANCHISE_ROLES_NORM = frozenset(_normalize(r) for r in FRANCHISE_PRINCIPAL_ROLES)


class QuotationService:
    """Business logic service for Quotation & Rating Engine."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = QuotationRepository(session)
        self.rating_service = RatingEngineService(self.repo)

    # -----------------------------------------------------------------------
    # Helper: Principal Context & Ownership Scope Resolution
    # -----------------------------------------------------------------------

    @staticmethod
    def _get_principal(user: User) -> PrincipalContext:
        ctx = getattr(user, "principal_context", None)
        if isinstance(ctx, PrincipalContext):
            return ctx
        return PrincipalContext(
            user_id=user.UserId,
            username=getattr(user, "UserName", None),
            role_id=getattr(user, "UserRoleId", None),
            role_name=getattr(user, "role_name", None),
            branch_id=getattr(user, "BranchId", None),
            agent_id=getattr(user, "agent_id", None),
            emp_id=getattr(user, "emp_id", None),
            employee_id=getattr(user, "employee_id", None),
            franchise_id=getattr(user, "franchise_id", None),
        )

    def _resolve_actor_ownership_for_write(
        self,
        user: User,
        requested_agent_id: Optional[int] = None,
        requested_sale_ex_id: Optional[int] = None,
        requested_franchise_id: int = 0,
    ) -> tuple[int, int, int, int, int]:
        """
        Returns (effective_agent_id, effective_sale_ex_id, effective_franchise_id, user_role_id, actor_id_for_code)
        enforcing strict server-side principal isolation so Agents/RMs/Franchises cannot spoof ownership.
        """
        ctx = self._get_principal(user)
        norm_role = _normalize(ctx.role_name)
        role_id = ctx.role_id or 4

        if norm_role in _AGENT_ROLES_NORM:
            effective_agent_id = ctx.agent_id or ctx.user_id
            effective_sale_ex_id = requested_sale_ex_id or 0
            effective_franchise_id = ctx.franchise_id or requested_franchise_id or 0
            actor_id = effective_agent_id
        elif norm_role in _EMPLOYEE_ROLES_NORM:
            effective_sale_ex_id = ctx.emp_id or ctx.user_id
            effective_agent_id = requested_agent_id or 0
            effective_franchise_id = ctx.franchise_id or requested_franchise_id or 0
            actor_id = effective_sale_ex_id
        elif norm_role in _FRANCHISE_ROLES_NORM:
            effective_franchise_id = ctx.franchise_id or ctx.user_id
            effective_agent_id = requested_agent_id or 0
            effective_sale_ex_id = requested_sale_ex_id or 0
            actor_id = effective_franchise_id
        else:
            # Global Admin / Coordinator / Operator
            effective_agent_id = requested_agent_id or 0
            effective_sale_ex_id = requested_sale_ex_id or (ctx.emp_id or ctx.user_id)
            effective_franchise_id = requested_franchise_id or 0
            actor_id = effective_agent_id if effective_agent_id > 0 else effective_sale_ex_id

        return (
            effective_agent_id,
            effective_sale_ex_id,
            effective_franchise_id,
            role_id,
            actor_id,
        )

    def _assert_can_access_self_quotation(
        self,
        entry: AppQuatationEntry,
        user: User,
    ) -> None:
        """Enforces row-level ownership scoping for Self-Quotation records."""
        ctx = self._get_principal(user)
        if is_global_read_role(ctx.role_name) or is_quotation_coordinator_role(ctx.role_name):
            return

        norm_role = _normalize(ctx.role_name)
        if norm_role in _AGENT_ROLES_NORM:
            expected_agent = ctx.agent_id or ctx.user_id
            if entry.AgentId != expected_agent:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: You can only access your own self-quotations.",
                )
            return

        if norm_role in _EMPLOYEE_ROLES_NORM:
            expected_emp = ctx.emp_id or ctx.user_id
            if entry.SaleExId != expected_emp and entry.AgentId != expected_emp:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: Self-quotation is outside your Sales Executive scope.",
                )
            return

    def _assert_can_access_quotation_request(
        self,
        req_row: AppQuotationRequest,
        user: User,
    ) -> None:
        """Enforces row-level ownership scoping for Assisted Quotation Requests."""
        ctx = self._get_principal(user)
        if is_global_read_role(ctx.role_name) or is_quotation_coordinator_role(ctx.role_name):
            return

        norm_role = _normalize(ctx.role_name)
        if norm_role in _AGENT_ROLES_NORM:
            expected_agent = ctx.agent_id or ctx.user_id
            if req_row.AgentId != expected_agent:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: You can only access your own quotation requests.",
                )
            return

        if norm_role in _EMPLOYEE_ROLES_NORM:
            expected_emp = ctx.emp_id or ctx.user_id
            if req_row.SalesEx_Id != expected_emp and req_row.LocationHeadId != expected_emp:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: Quotation request is outside your Sales Executive scope.",
                )
            return

        if norm_role in _FRANCHISE_ROLES_NORM:
            expected_frn = ctx.franchise_id or ctx.user_id
            if req_row.FranchiseId != expected_frn:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: Quotation request is outside your Franchise scope.",
                )
            return

    # -----------------------------------------------------------------------
    # 1. Stateless Rating Calculation & Multi-Insurer Comparison
    # -----------------------------------------------------------------------

    async def calculate_premium(
        self,
        payload: PremiumCalculationRequest,
    ) -> PremiumBreakdownResponse:
        return await self.rating_service.calculate_premium(payload)

    async def compare_insurers(
        self,
        payload: MultiInsurerCompareRequest,
    ) -> MultiInsurerCompareResponse:
        return await self.rating_service.compare_insurers(payload)

    # -----------------------------------------------------------------------
    # 2. Self-Quotation Persistence & Retrieval (tbl_app_quatationentry)
    # -----------------------------------------------------------------------

    @staticmethod
    def _map_self_quotation_response(
        entry: AppQuatationEntry,
        breakdown: Optional[PremiumBreakdownResponse] = None,
    ) -> SelfQuotationResponse:
        return SelfQuotationResponse(
            quatation_id=entry.QuatationId,
            quatation_code=entry.QuatationCode or "",
            quatation_date=entry.QuatationDate,
            title=entry.Title,
            product_name=entry.ProductName,
            product_type=entry.ProductType,
            registration_no=entry.RegistrationNo,
            mgf_year=entry.MgfYear,
            rto_id=entry.RTOId,
            zone=entry.Zone,
            insurance_company_id=entry.InsuranceCompanyId,
            veh_type_id=entry.Veh_Type_ID,
            veh_sub_type_id=entry.Veh_Sub_Type_ID,
            make_id=entry.Make_ID,
            model_id=entry.Model_ID,
            variant_id=entry.Variant_ID,
            fuel_type_id=entry.FuelTypeId,
            seats_capacity=entry.SeatsCapacity,
            cubic_capacity=entry.CubicCapacity,
            vehicle_weight=entry.VehicleWeight,
            idv=_to_decimal(entry.IDV),
            own_damage_premium=_to_decimal(entry.OwnDamagePremium),
            od_discount_amount=_to_decimal(entry.OD),
            imt23_amount=_to_decimal(entry.AddExtra15IMTno23),
            zero_depreciation=_to_decimal(entry.ZeroDepreciation),
            no_claim_bonus=_to_decimal(entry.NoClaimBonus),
            ncb_percent=_to_decimal(entry.NCBPre),
            total_od_premium=_to_decimal(entry.AtotalOwnDamPremium),
            total_liability_premium=_to_decimal(entry.BtotalLiabilityPremium),
            total_net_premium=_to_decimal(entry.TotalPremium),
            gst_amount=_to_decimal(entry.GST18),
            final_premium=_to_decimal(entry.finalPrmium),
            body_price=_to_decimal(entry.BodyPrice),
            chassis_price=_to_decimal(entry.ChassisPrice),
            agent_id=entry.AgentId,
            sale_ex_id=entry.SaleExId,
            user_role_id=entry.UserRoleId,
            breakdown=breakdown,
        )

    async def create_self_quotation(
        self,
        payload: SelfQuotationCreateRequest,
        current_user: User,
    ) -> SelfQuotationResponse:
        """
        Calculates deterministic rating breakdown and persists a Self-Quotation record
        in tbl_app_quatationentry (Sp_InsertAppQuotationEntry parity).
        """
        calc_in = payload.calculation_input
        breakdown = await self.rating_service.calculate_premium(calc_in)

        (
            eff_agent_id,
            eff_sale_ex_id,
            _,
            role_id,
            actor_id,
        ) = self._resolve_actor_ownership_for_write(
            user=current_user,
            requested_agent_id=payload.agent_id,
            requested_sale_ex_id=payload.sale_ex_id,
        )

        veh_type_id = calc_in.veh_type_id or 1
        srq_code, _ = await self.repo.generate_self_quotation_code(
            user_role_id=role_id,
            actor_id=actor_id,
            veh_type_id=veh_type_id,
            insurance_company_id=calc_in.insurance_company_id,
        )

        title = payload.title.strip() if payload.title else srq_code
        if await self.repo.check_self_quotation_title_exists(title):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Quotation Title '{title}' already exists.",
            )

        now = datetime.utcnow()
        entry = AppQuatationEntry(
            QuatationCode=srq_code,
            QuatationDate=now,
            Title=title,
            ProductName=payload.product_name,
            ProductType=payload.product_type,
            RegistrationNo=payload.registration_no.strip().upper(),
            MgfYear=payload.mgf_year,
            RTOId=calc_in.rto_id or 1,
            Zone=calc_in.zone,
            InsuranceCompanyId=calc_in.insurance_company_id,
            Veh_Type_ID=veh_type_id,
            Veh_Sub_Type_ID=calc_in.veh_sub_type_id or 0,
            Make_ID=calc_in.make_id or 1,
            Model_ID=calc_in.model_id or 1,
            Variant_ID=calc_in.variant_id or 1,
            SeatsCapacity=str(calc_in.seating_capacity),
            CubicCapacity=str(calc_in.cubic_capacity),
            VehicleWeight=str(calc_in.gross_vehicle_weight),
            IDV=str(breakdown.selected_idv),
            OwnDamagePremium=str(breakdown.gross_od_premium),
            OD=str(breakdown.od_discount_amount),
            AddExtra15IMTno23=str(breakdown.imt23_loading_amount),
            ZeroDepreciation=str(breakdown.zero_dep_premium),
            NoClaimBonus=str(breakdown.ncb_amount),
            AddLoading="0",
            AddPremiumAbove12000kg=str(breakdown.gvw_above_12000_loading),
            EletricAccessories=str(breakdown.electrical_accessories_od),
            CNGFulekits=str(breakdown.lpg_cng_kit_od + breakdown.inbuilt_lpg_cng_od),
            VehicleBasicRate=str(breakdown.od_basic_rate_percent),
            BasicPremium=str(breakdown.basic_od_premium),
            LiabilityPremium=str(breakdown.basic_tp_premium),
            TPRisk=str(breakdown.passenger_ll_premium),
            CNGfuleKitLiabilityPremium=str(breakdown.lpg_cng_tp_premium),
            PAforOwnerDriver=str(breakdown.pa_owner_driver_premium),
            PAtoUnnamedocc=str(breakdown.pa_unnamed_passenger_premium),
            LegallibtoEmp=str(breakdown.ll_employee_premium),
            legallibtoPaidDriver=str(breakdown.ll_paid_driver_premium),
            TPPDLimtoRS6000=str(breakdown.tppd_discount),
            PAToPaidDriver=str(breakdown.pa_paid_driver_premium),
            Antitheftacc=str(breakdown.anti_theft_discount),
            Automobaccmemdis=str(breakdown.automobile_association_discount),
            LLtoDrCleanerandCoolies=str(breakdown.ll_cleaner_coolie_premium),
            LLtoNonfarepayingpass=str(breakdown.nfpp_premium),
            PABenefits="0",
            PAtoPillionRider=str(breakdown.pa_pillion_rider_premium),
            AtotalOwnDamPremium=str(breakdown.total_od_with_addons),
            BtotalLiabilityPremium=str(breakdown.total_tp_premium),
            TotalPremium=str(breakdown.net_premium),
            GST18=str(breakdown.total_gst_amount),
            finalPrmium=str(breakdown.final_payable_premium),
            AgentId=eff_agent_id,
            SaleExId=eff_sale_ex_id,
            isdeleted="0",
            FuelTypeId=calc_in.fuel_type_id,
            NCBPre=str(breakdown.ncb_percent),
            Mfg_Year=payload.mfg_date or now,
            UserRoleId=role_id,
            BodyPrice=float(breakdown.body_price),
            ChassisPrice=float(breakdown.chassis_price),
        )

        saved = await self.repo.create_self_quotation(entry)
        await self.session.commit()
        return self._map_self_quotation_response(saved, breakdown=breakdown)

    async def get_self_quotation(
        self,
        quotation_id: int,
        current_user: User,
    ) -> SelfQuotationResponse:
        entry = await self.repo.get_self_quotation_by_id(quotation_id)
        if entry is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Self-Quotation #{quotation_id} not found.",
            )
        self._assert_can_access_self_quotation(entry, current_user)
        return self._map_self_quotation_response(entry)

    async def list_self_quotations(
        self,
        current_user: User,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        registration_no: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> SelfQuotationListResponse:
        ctx = self._get_principal(current_user)
        agent_filter: Optional[int] = None
        sale_ex_filter: Optional[int] = None

        if not (is_global_read_role(ctx.role_name) or is_quotation_coordinator_role(ctx.role_name)):
            norm_role = _normalize(ctx.role_name)
            if norm_role in _AGENT_ROLES_NORM:
                agent_filter = ctx.agent_id or ctx.user_id
            elif norm_role in _EMPLOYEE_ROLES_NORM:
                sale_ex_filter = ctx.emp_id or ctx.user_id

        total, rows = await self.repo.list_self_quotations(
            agent_id_filter=agent_filter,
            sale_ex_id_filter=sale_ex_filter,
            from_date=from_date,
            to_date=to_date,
            registration_no=registration_no,
            limit=limit,
            offset=offset,
        )
        return SelfQuotationListResponse(
            total=total,
            items=[self._map_self_quotation_response(r) for r in rows],
        )

    # -----------------------------------------------------------------------
    # 3. Assisted Quotation Request Lifecycle (tbl_app_quotationrequest)
    # -----------------------------------------------------------------------

    async def _build_assisted_request_response(
        self,
        req_row: AppQuotationRequest,
    ) -> AssistedQuotationRequestResponse:
        quotes = await self.repo.get_insurer_quote_options(req_row.QuatationId)
        remarks = await self.repo.get_quotation_remarks(req_row.QuatationId)

        return AssistedQuotationRequestResponse(
            quatation_id=req_row.QuatationId,
            quatation_code=req_row.QuatationCode,
            quatation_date=req_row.QuatationDate,
            insurance_company_id=req_row.InsuranceCompanyId,
            vehicle_id=req_row.VehicleId,
            agent_id=req_row.AgentId,
            sales_ex_id=req_row.SalesEx_Id,
            user_role_id=req_row.UserRoleId,
            other_agent_name=req_row.OtherAgentName,
            location_head_id=req_row.LocationHeadId,
            franchise_id=req_row.FranchiseId,
            product_type=req_row.ProductType,
            zerodepth=req_row.Zerodepth,
            policy_mode=req_row.PolicyMode,
            mobile_no=req_row.MobileNo,
            ncb=req_row.NCB,
            vehicle_no=req_row.VehicleNo,
            vehicle_type=req_row.VehicleType,
            vehicle_make=req_row.VehicleMake,
            vehicle_model=req_row.VehicleModel,
            vehicle_variance=req_row.VehicleVariance,
            policytype=req_row.policytype,
            note=req_row.Note or "",
            remark=req_row.Remark,
            is_quotation_generate=req_row.IsQuotationGenerate or 0,
            is_pending_revert=req_row.isPendingRevert or 0,
            read_status=req_row.ReadStatus or 0,
            attended_by=req_row.AttendedBy,
            attended_user_id=req_row.AttendedUserId,
            attended_date=req_row.AttendedDate,
            quot_send_date=req_row.QuotSendDate,
            cancel_remark=req_row.CancelRemark,
            cancel_date=req_row.CancelDate,
            cancel_by=req_row.CancelBy,
            insurer_quotes=[
                InsurerQuoteOptionResponse(
                    quotation_id=q.QuotationId,
                    transction_id=q.TransctionId,
                    insurance_company_id=q.InsuranceCompanyId,
                    agent_id=q.agentId,
                    emp_id=q.EmpId,
                    quotation_file=q.QuotationFile,
                    quotation_file_name=q.Quotationfile_Name,
                    product_id=q.ProductId or 1,
                    remark=q.Remark,
                    insert_date=q.InsertDate,
                )
                for q in quotes
            ],
            remarks_history=[
                QuotationRemarkResponse(
                    quat_remark_id=rm.QuatRemarkId,
                    quatation_id=rm.QuatationId,
                    quatation_date=rm.QuatationDate,
                    user_id=rm.UserId,
                    remark=rm.Remark,
                    update_by=rm.UpdateBy,
                    update_date=rm.UpdateDate,
                    remark_from=rm.RemarkFrom,
                )
                for rm in remarks
            ],
        )

    async def create_quotation_request(
        self,
        payload: AssistedQuotationRequestCreate,
        current_user: User,
    ) -> AssistedQuotationRequestResponse:
        """
        Creates an Assisted Quotation Request in tbl_app_quotationrequest
        (InsertAppQuotationRequest parity).
        """
        (
            eff_agent_id,
            eff_sale_ex_id,
            eff_franchise_id,
            role_id,
            actor_id,
        ) = self._resolve_actor_ownership_for_write(
            user=current_user,
            requested_agent_id=payload.agent_id,
            requested_sale_ex_id=payload.sales_ex_id,
            requested_franchise_id=payload.franchise_id,
        )

        q_code = await self.repo.generate_assisted_quotation_code(
            user_role_id=role_id,
            actor_id=actor_id,
        )

        now = datetime.utcnow()
        req_row = AppQuotationRequest(
            QuatationCode=q_code,
            InsuranceCompanyId=payload.insurance_company_id.strip(),
            VehicleId=payload.vehicle_id or 0,
            QuatationDate=now,
            QuotationFile=payload.quotation_file,
            PolicyImage=payload.policy_image,
            AgentId=eff_agent_id,
            SalesEx_Id=eff_sale_ex_id,
            IsQuotationGenerate=0,
            isdeleted=0,
            ProductType=payload.product_type,
            Zerodepth=payload.zerodepth,
            PolicyMode=payload.policy_mode,
            MobileNo=payload.mobile_no.strip(),
            Camera=payload.camera,
            NCB=payload.ncb,
            VehicleNo=payload.vehicle_no.strip().upper(),
            VehicleType=payload.vehicle_type.strip(),
            VehicleMake=payload.vehicle_make.strip(),
            VehicleModel=payload.vehicle_model.strip(),
            VehicleVariance=payload.vehicle_variance.strip(),
            policytype=payload.policytype.strip(),
            Note=payload.note,
            ReadStatus=0,
            isPendingRevert=0,
            Remark=payload.remark,
            UserRoleId=role_id,
            OtherAgentName=payload.other_agent_name,
            LocationHeadId=payload.location_head_id,
            FranchiseId=eff_franchise_id,
        )

        saved = await self.repo.create_quotation_request(req_row)

        if payload.remark:
            await self.repo.add_quotation_remark(
                quatation_id=saved.QuatationId,
                user_id=current_user.UserId,
                remark=payload.remark,
                update_by=getattr(current_user, "UserName", None) or str(current_user.UserId),
                remark_from="Sales",
            )

        await self.session.commit()
        return await self._build_assisted_request_response(saved)

    async def get_quotation_request(
        self,
        quotation_id: int,
        current_user: User,
    ) -> AssistedQuotationRequestResponse:
        req_row = await self.repo.get_quotation_request_by_id(quotation_id)
        if req_row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Assisted Quotation Request #{quotation_id} not found.",
            )
        self._assert_can_access_quotation_request(req_row, current_user)
        return await self._build_assisted_request_response(req_row)

    async def list_quotation_requests(
        self,
        current_user: User,
        is_generated: Optional[int] = None,
        is_pending_revert: Optional[int] = None,
        vehicle_no: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> AssistedQuotationListResponse:
        ctx = self._get_principal(current_user)
        agent_filter: Optional[int] = None
        sales_ex_filter: Optional[int] = None
        franchise_filter: Optional[int] = None

        if not (is_global_read_role(ctx.role_name) or is_quotation_coordinator_role(ctx.role_name)):
            norm_role = _normalize(ctx.role_name)
            if norm_role in _AGENT_ROLES_NORM:
                agent_filter = ctx.agent_id or ctx.user_id
            elif norm_role in _EMPLOYEE_ROLES_NORM:
                sales_ex_filter = ctx.emp_id or ctx.user_id
            elif norm_role in _FRANCHISE_ROLES_NORM:
                franchise_filter = ctx.franchise_id or ctx.user_id

        total, rows = await self.repo.list_quotation_requests(
            agent_id_filter=agent_filter,
            sales_ex_id_filter=sales_ex_filter,
            franchise_id_filter=franchise_filter,
            is_generated=is_generated,
            is_pending_revert=is_pending_revert,
            vehicle_no=vehicle_no,
            limit=limit,
            offset=offset,
        )
        items = [await self._build_assisted_request_response(r) for r in rows]
        return AssistedQuotationListResponse(total=total, items=items)

    async def update_quotation_request(
        self,
        quotation_id: int,
        payload: AssistedQuotationRequestUpdate,
        current_user: User,
    ) -> AssistedQuotationRequestResponse:
        """
        Updates an Assisted Quotation Request and marks isPendingRevert = 2
        when resubmitted by Agent/Sales (Sp_UpdateAppQuotReqNew parity).
        """
        req_row = await self.repo.get_quotation_request_by_id(quotation_id)
        if req_row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Assisted Quotation Request #{quotation_id} not found.",
            )
        self._assert_can_access_quotation_request(req_row, current_user)

        if payload.insurance_company_id is not None:
            req_row.InsuranceCompanyId = payload.insurance_company_id.strip()
        if payload.vehicle_id is not None:
            req_row.VehicleId = payload.vehicle_id
        if payload.product_type is not None:
            req_row.ProductType = payload.product_type
        if payload.zerodepth is not None:
            req_row.Zerodepth = payload.zerodepth
        if payload.policy_mode is not None:
            req_row.PolicyMode = payload.policy_mode
        if payload.mobile_no is not None:
            req_row.MobileNo = payload.mobile_no.strip()
        if payload.ncb is not None:
            req_row.NCB = payload.ncb
        if payload.vehicle_no is not None:
            req_row.VehicleNo = payload.vehicle_no.strip().upper()
        if payload.vehicle_type is not None:
            req_row.VehicleType = payload.vehicle_type.strip()
        if payload.vehicle_make is not None:
            req_row.VehicleMake = payload.vehicle_make.strip()
        if payload.vehicle_model is not None:
            req_row.VehicleModel = payload.vehicle_model.strip()
        if payload.vehicle_variance is not None:
            req_row.VehicleVariance = payload.vehicle_variance.strip()
        if payload.policytype is not None:
            req_row.policytype = payload.policytype.strip()
        if payload.note is not None:
            req_row.Note = payload.note
        if payload.policy_image is not None:
            req_row.PolicyImage = payload.policy_image
        if payload.remark is not None:
            req_row.Remark = payload.remark

        # Legacy Sp_UpdateAppQuotReqNew sets isPendingRevert = 2 (Re-opened / Resubmitted)
        req_row.isPendingRevert = 2
        req_row.IsQuotationGenerate = 0
        req_row.updatedDate = datetime.utcnow()

        if payload.remark:
            await self.repo.add_quotation_remark(
                quatation_id=req_row.QuatationId,
                user_id=current_user.UserId,
                remark=payload.remark,
                update_by=getattr(current_user, "UserName", None) or str(current_user.UserId),
                remark_from="Sales",
            )

        await self.session.commit()
        await self.session.refresh(req_row)
        return await self._build_assisted_request_response(req_row)

    async def attend_quotation_request(
        self,
        quotation_id: int,
        payload: QuotationAttendRequest,
        current_user: User,
    ) -> AssistedQuotationRequestResponse:
        """
        Coordinator claims or releases an Assisted Quotation Request
        (sp_UpdateAppAttendQuotation1 parity).
        """
        req_row = await self.repo.get_quotation_request_by_id(quotation_id)
        if req_row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Assisted Quotation Request #{quotation_id} not found.",
            )

        ctx = self._get_principal(current_user)
        can_override = is_global_admin_role(ctx.role_name) or _normalize(ctx.role_name) == "OPERATOR HEAD"

        if payload.attend:
            if (
                req_row.AttendedUserId
                and req_row.AttendedUserId != current_user.UserId
                and not can_override
            ):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Quotation Request #{quotation_id} is already attended by '{req_row.AttendedBy}'.",
                )
            req_row.AttendedBy = getattr(current_user, "UserName", None) or f"User#{current_user.UserId}"
            req_row.AttendedUserId = current_user.UserId
            req_row.AttendedDate = datetime.utcnow()
        else:
            if (
                req_row.AttendedUserId
                and req_row.AttendedUserId != current_user.UserId
                and not can_override
            ):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Cannot release a Quotation Request attended by another coordinator.",
                )
            req_row.AttendedBy = None
            req_row.AttendedUserId = 0
            req_row.AttendedDate = None

        await self.session.commit()
        await self.session.refresh(req_row)
        return await self._build_assisted_request_response(req_row)

    async def transition_quotation_request_status(
        self,
        quotation_id: int,
        payload: QuotationStatusTransitionRequest,
        current_user: User,
    ) -> AssistedQuotationRequestResponse:
        """
        Executes state machine transitions on Assisted Quotation Requests:
        - 'revert' (sp_UpdateAppQuotationReopen): isPendingRevert = 1, IsQuotationGenerate = 0
        - 'resubmit' (Sp_UpdateAppQuotReqNew): isPendingRevert = 2, IsQuotationGenerate = 0
        - 'mark_read' (sp_UpdateAppQuotationReadStatus): ReadStatus = 1
        - 'cancel': CancelRemark, CancelDate, CancelBy, isdeleted = 1
        """
        req_row = await self.repo.get_quotation_request_by_id(quotation_id)
        if req_row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Assisted Quotation Request #{quotation_id} not found.",
            )

        now = datetime.utcnow()
        actor_name = getattr(current_user, "UserName", None) or str(current_user.UserId)

        if payload.action == "revert":
            req_row.isPendingRevert = 1
            req_row.IsQuotationGenerate = 0
            req_row.Remark = payload.remark
            req_row.updatedDate = now
            remark_source = "Operator"
        elif payload.action == "resubmit":
            req_row.isPendingRevert = 2
            req_row.IsQuotationGenerate = 0
            req_row.Remark = payload.remark
            req_row.updatedDate = now
            remark_source = "Sales"
        elif payload.action == "mark_read":
            req_row.ReadStatus = 1
            req_row.updatedDate = now
            remark_source = "Operator"
        else:  # cancel
            req_row.CancelRemark = payload.remark
            req_row.CancelDate = now
            req_row.CancelBy = actor_name
            req_row.isdeleted = 1
            remark_source = "Operator"

        await self.repo.add_quotation_remark(
            quatation_id=req_row.QuatationId,
            user_id=current_user.UserId,
            remark=payload.remark,
            update_by=actor_name,
            remark_from=remark_source,
        )

        await self.session.commit()
        await self.session.refresh(req_row)
        return await self._build_assisted_request_response(req_row)

    async def generate_insurer_quotes(
        self,
        quotation_id: int,
        payload: GenerateInsurerQuotesRequest,
        current_user: User,
    ) -> AssistedQuotationRequestResponse:
        """
        Attaches one or more insurer quotation options in tbl_insurancecompanyquotation
        (sp_insertInsuranceComponyQuotation) and marks tbl_app_quotationrequest as Generated
        (sp_UpdateAppQuotationRequest: IsQuotationGenerate = 1, QuotSendDate = now).
        """
        req_row = await self.repo.get_quotation_request_by_id(quotation_id)
        if req_row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Assisted Quotation Request #{quotation_id} not found.",
            )

        if payload.replace_existing:
            await self.repo.soft_delete_insurer_quotes(quotation_id)

        ctx = self._get_principal(current_user)
        emp_id = ctx.emp_id or current_user.UserId
        first_opt = payload.options[0]

        for opt in payload.options:
            await self.repo.add_insurer_quote_option(
                quatation_id=quotation_id,
                insurance_company_id=opt.insurance_company_id,
                agent_id=req_row.AgentId or 0,
                emp_id=emp_id,
                quotation_file=opt.quotation_file,
                quotation_file_name=opt.quotation_file_name,
                product_id=opt.product_id,
                remark=opt.remark,
            )

        now = datetime.utcnow()
        req_row.QuotationFile = first_opt.quotation_file
        req_row.IsQuotationGenerate = 1
        req_row.isPendingRevert = 0
        req_row.QuotSendDate = now
        req_row.updatedDate = now
        if payload.coordinator_remark:
            req_row.Remark = payload.coordinator_remark
            await self.repo.add_quotation_remark(
                quatation_id=quotation_id,
                user_id=current_user.UserId,
                remark=payload.coordinator_remark,
                update_by=getattr(current_user, "UserName", None) or str(current_user.UserId),
                remark_from="Operator",
            )

        await self.session.commit()
        await self.session.refresh(req_row)
        return await self._build_assisted_request_response(req_row)

    async def delete_quotation_request(
        self,
        quotation_id: int,
        current_user: User,
    ) -> dict:
        """
        Soft-deletes an Assisted Quotation Request (sp_UpdateClearSelfQutation('GETData')).
        """
        req_row = await self.repo.get_quotation_request_by_id(quotation_id)
        if req_row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Assisted Quotation Request #{quotation_id} not found.",
            )
        self._assert_can_access_quotation_request(req_row, current_user)

        ctx = self._get_principal(current_user)
        if (
            req_row.IsQuotationGenerate == 1
            and not is_global_admin_role(ctx.role_name)
            and not is_quotation_coordinator_role(ctx.role_name)
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot delete an Assisted Quotation Request after quotes have been generated.",
            )

        req_row.isdeleted = 1
        req_row.CancelDate = datetime.utcnow()
        req_row.CancelBy = getattr(current_user, "UserName", None) or str(current_user.UserId)
        await self.session.commit()
        return {"quatation_id": quotation_id, "deleted": True}

    # -----------------------------------------------------------------------
    # 4. Phase 7 Policy Proposal Conversion Prefill Contract
    # -----------------------------------------------------------------------

    async def get_policy_prefill(
        self,
        quotation_id: int,
        source_type: str,
        current_user: User,
        insurance_company_id: Optional[int] = None,
    ) -> PolicyPrefillResponse:
        """
        Builds Phase 7 Policy Proposal prefill payload from either:
        - Self-Quotation (tbl_app_quatationentry -> SELFQUO branch)
        - Assisted Quotation Request (tbl_app_quotationrequest + tbl_insurancecompanyquotation)
        """
        if source_type == "SELF_QUOTATION":
            entry = await self.repo.get_self_quotation_by_id(quotation_id)
            if entry is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Self-Quotation #{quotation_id} not found.",
                )
            self._assert_can_access_self_quotation(entry, current_user)
            gross_od = _to_decimal(entry.OwnDamagePremium)
            od_disc_amt = _to_decimal(entry.OD)
            od_disc_pct = (
                ((od_disc_amt * Decimal("100")) / gross_od).quantize(Decimal("0.01"))
                if gross_od > Decimal("0")
                else Decimal("0.00")
            )
            return PolicyPrefillResponse(
                source_type="SELF_QUOTATION",
                quotation_id=entry.QuatationId,
                quotation_code=entry.QuatationCode or "",
                insurance_company_id=entry.InsuranceCompanyId or 1,
                product_type=entry.ProductType,
                registration_no=entry.RegistrationNo,
                veh_type_id=entry.Veh_Type_ID,
                veh_sub_type_id=entry.Veh_Sub_Type_ID,
                make_id=entry.Make_ID,
                model_id=entry.Model_ID,
                variant_id=entry.Variant_ID,
                fuel_type_id=entry.FuelTypeId,
                rto_id=entry.RTOId,
                idv_amount=_to_decimal(entry.IDV),
                od_discount_percent=od_disc_pct,
                ncb_percent=_to_decimal(entry.NCBPre),
                od_premium=_to_decimal(entry.AtotalOwnDamPremium),
                tp_premium=_to_decimal(entry.BtotalLiabilityPremium),
                net_premium=_to_decimal(entry.TotalPremium),
                gst_amount=_to_decimal(entry.GST18),
                final_premium=_to_decimal(entry.finalPrmium),
                agent_id=entry.AgentId,
                sales_ex_id=entry.SaleExId,
                user_role_id=entry.UserRoleId,
                quotation_file=None,
            )

        req_row = await self.repo.get_quotation_request_by_id(quotation_id)
        if req_row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Assisted Quotation Request #{quotation_id} not found.",
            )
        self._assert_can_access_quotation_request(req_row, current_user)

        quotes = await self.repo.get_insurer_quote_options(quotation_id)
        selected_quote = None
        if insurance_company_id is not None:
            for q in quotes:
                if q.InsuranceCompanyId == insurance_company_id:
                    selected_quote = q
                    break
        elif quotes:
            selected_quote = quotes[0]

        comp_id = (
            selected_quote.InsuranceCompanyId
            if selected_quote
            else int(str(req_row.InsuranceCompanyId or "1").split(",")[0].strip() or "1")
        )
        q_file = selected_quote.QuotationFile if selected_quote else req_row.QuotationFile

        return PolicyPrefillResponse(
            source_type="ASSISTED_REQUEST",
            quotation_id=req_row.QuatationId,
            quotation_code=req_row.QuatationCode or "",
            insurance_company_id=comp_id,
            product_type=req_row.ProductType,
            registration_no=req_row.VehicleNo,
            ncb_percent=_to_decimal(req_row.NCB),
            agent_id=req_row.AgentId,
            sales_ex_id=req_row.SalesEx_Id,
            user_role_id=req_row.UserRoleId,
            quotation_file=q_file,
        )
