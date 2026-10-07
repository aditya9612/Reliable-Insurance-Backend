from typing import Optional, Dict, Any, List, Sequence
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import select, and_, or_, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole
from app.models.customer import Customer
from app.models.vehicle import VehicleDetails
from app.models.transaction import Transaction
from app.models.transaction_app import TransactionAppNew
from app.models.payment import TransactionPayment
from app.models.claims_endorsement import PolicyEndorsement
from app.models.master import (
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
from app.models.quotation import AppQuatationEntry
from app.core.rbac import (
    GLOBAL_ADMIN_ROLES,
    GLOBAL_READ_ROLES,
    CUSTOMER_VEHICLE_READ_ROLES,
)
from app.schemas.search import (
    AutocompleteItem,
    AutocompleteResponse,
    VehicleDuplicateCheckResponse,
    PendingCountersResponse,
    DashboardChartDataResponse,
    ServerStatusResponse,
)


class SearchService:
    """
    Search and Autocomplete Service implementing legacy SearchMethods.aspx.cs (41 methods)
    and AppSearchMethod.aspx.cs (16 methods) with strict RBAC and branch isolation.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # -----------------------------------------------------------------------
    # Autocomplete / Typeahead (Maps 22 search WebMethods)
    # -----------------------------------------------------------------------

    async def autocomplete(
        self,
        current_user: User,
        query: str,
        category: str = "customer",
        limit: int = 20,
    ) -> AutocompleteResponse:
        """
        Generic typeahead search across domain entities strictly scoped by caller role and branch.
        """
        clean_query = query.strip()
        safe_limit = max(1, min(limit, 100))
        cat = category.strip().lower()

        # Determine caller's branch scope
        caller_role = getattr(current_user, "role_name", "") or ""
        caller_branch_id = getattr(current_user, "branch_id", None) or getattr(current_user, "BranchId", None)
        is_global = caller_role.upper() in GLOBAL_READ_ROLES or caller_role.upper() in GLOBAL_ADMIN_ROLES

        items: List[AutocompleteItem] = []

        if cat in ("customer", "cust"):
            # Maps GetCustName, GetCustByVehicleNo
            conditions = [or_(Customer.isdeleted == "0", Customer.isdeleted == 0, Customer.isdeleted.is_(None))]
            if not is_global and caller_branch_id is not None:
                conditions.append(Customer.BranchId == caller_branch_id)
            if clean_query:
                q_term = f"{clean_query}%"
                conditions.append(
                    or_(
                        Customer.CustFName.like(q_term),
                        Customer.CustLName.like(q_term),
                        Customer.MoblieNo1.like(q_term),
                        Customer.CustomerCode.like(q_term),
                    )
                )

            stmt = (
                select(Customer)
                .where(and_(*conditions))
                .order_by(Customer.CustFName, Customer.CustLName)
                .limit(safe_limit)
            )
            res = await self.session.execute(stmt)
            for c in res.scalars().all():
                full_name = f"{c.CustFName or ''} {c.CustLName or ''}".strip()
                items.append(
                    AutocompleteItem(
                        id=c.CustomerId,
                        label=f"{full_name} ({c.MoblieNo1 or 'No Mobile'})",
                        value=full_name,
                        category="customer",
                        sub_text=f"Code: {c.CustomerCode or '-'} | Mobile: {c.MoblieNo1 or '-'}",
                        extra={"customer_id": c.CustomerId, "mobile": c.MoblieNo1, "pan": c.PAN_No},
                    )
                )

        elif cat in ("vehicle", "veh", "regno"):
            # Maps GetCustVehicleNo
            conditions = [or_(VehicleDetails.isdeleted == "0", VehicleDetails.isdeleted == 0, VehicleDetails.isdeleted.is_(None))]
            if clean_query:
                q_term = f"{clean_query}%"
                conditions.append(
                    or_(
                        VehicleDetails.RegistrationNo.like(q_term),
                        VehicleDetails.ChaiseNo.like(q_term),
                        VehicleDetails.EngineNo.like(q_term),
                    )
                )

            stmt = (
                select(VehicleDetails)
                .where(and_(*conditions))
                .order_by(VehicleDetails.RegistrationNo)
                .limit(safe_limit)
            )
            res = await self.session.execute(stmt)
            for v in res.scalars().all():
                items.append(
                    AutocompleteItem(
                        id=v.CustVehId,
                        label=f"{v.RegistrationNo or 'UNREGISTERED'} (Chassis: {v.ChaiseNo or '-'})",
                        value=v.RegistrationNo or "",
                        category="vehicle",
                        sub_text=f"Engine: {v.EngineNo or '-'} | Chassis: {v.ChaiseNo or '-'}",
                        extra={"cust_veh_id": v.CustVehId, "reg_no": v.RegistrationNo, "chassis_no": v.ChaiseNo},
                    )
                )

        elif cat in ("policy", "policy_no"):
            # Maps GetPolicyNo
            conditions = [or_(Transaction.isdeleted == "0", Transaction.isdeleted == 0, Transaction.isdeleted.is_(None))]
            if not is_global and caller_branch_id is not None:
                conditions.append(Transaction.BranchId == caller_branch_id)
            if clean_query:
                q_term = f"{clean_query}%"
                conditions.append(
                    or_(
                        Transaction.PolicyNo.like(q_term),
                        Transaction.InwardNo.like(q_term),
                    )
                )

            stmt = (
                select(Transaction)
                .where(and_(*conditions))
                .order_by(Transaction.TransanctionId.desc())
                .limit(safe_limit)
            )
            res = await self.session.execute(stmt)
            for t in res.scalars().all():
                items.append(
                    AutocompleteItem(
                        id=t.TransanctionId,
                        label=f"{t.PolicyNo or 'PENDING'} (Inward: {t.InwardNo or '-'})",
                        value=t.PolicyNo or "",
                        category="policy",
                        sub_text=f"Inward: {t.InwardNo or '-'} | Gross: {t.Amount or 0}",
                        extra={"transaction_id": t.TransanctionId, "policy_no": t.PolicyNo, "inward_no": t.InwardNo},
                    )
                )

        elif cat in ("policy_by_cheque", "cheque_policy"):
            # Maps GetPolicyNoByCheqe
            conditions = [
                or_(Transaction.isdeleted == "0", Transaction.isdeleted == 0, Transaction.isdeleted.is_(None)),
                or_(TransactionPayment.isdeleted == "0", TransactionPayment.isdeleted == 0, TransactionPayment.isdeleted.is_(None)),
                TransactionPayment.PaymentType == "Cheque",
            ]
            if not is_global and caller_branch_id is not None:
                conditions.append(Transaction.BranchId == caller_branch_id)
            if clean_query:
                conditions.append(Transaction.PolicyNo.like(f"{clean_query}%"))

            stmt = (
                select(Transaction)
                .join(TransactionPayment, Transaction.TransanctionId == TransactionPayment.TransanctionId)
                .where(and_(*conditions))
                .order_by(Transaction.TransanctionId.desc())
                .limit(safe_limit)
            )
            res = await self.session.execute(stmt)
            for t in res.scalars().all():
                items.append(
                    AutocompleteItem(
                        id=t.TransanctionId,
                        label=f"{t.PolicyNo} (Cheque Payment)",
                        value=t.PolicyNo or "",
                        category="policy_by_cheque",
                        sub_text=f"Inward: {t.InwardNo or '-'}",
                        extra={"transaction_id": t.TransanctionId, "policy_no": t.PolicyNo},
                    )
                )

        elif cat in ("quotation", "quote"):
            # Maps GetQuatationNo
            conditions = [or_(AppQuatationEntry.isdeleted == "0", AppQuatationEntry.isdeleted == 0, AppQuatationEntry.isdeleted.is_(None))]
            if clean_query:
                conditions.append(AppQuatationEntry.QuatationCode.like(f"{clean_query}%"))

            stmt = (
                select(AppQuatationEntry)
                .where(and_(*conditions))
                .order_by(AppQuatationEntry.QuatationId.desc())
                .limit(safe_limit)
            )
            res = await self.session.execute(stmt)
            for q in res.scalars().all():
                items.append(
                    AutocompleteItem(
                        id=q.QuatationId,
                        label=f"{q.QuatationCode or '-'} ({q.Title or 'Quotation'})",
                        value=q.QuatationCode or "",
                        category="quotation",
                        sub_text=f"Title: {q.Title or '-'}",
                        extra={"quotation_id": q.QuatationId, "code": q.QuatationCode},
                    )
                )

        elif cat in ("agent", "posp", "sales_ex", "employee", "franchise"):
            # Maps GetAgentName, GetPOSPName, GetFranchiseName, GetFranchiseAgentName,
            # GetSalesExName, SearchtextAgentName, SearchtextEmpName, SearchtextEmpCode
            conditions = [or_(User.isdeleted == "0", User.isdeleted == 0, User.isdeleted.is_(None))]
            if not is_global and caller_branch_id is not None:
                conditions.append(User.BranchId == caller_branch_id)

            if cat == "agent":
                conditions.append(User.UserRoleId == 4)
            elif cat == "posp":
                conditions.append(or_(User.UserRoleId == 4, User.UserRoleId == 35))
            elif cat == "franchise":
                conditions.append(User.UserRoleId == 9)
            elif cat == "sales_ex":
                conditions.append(User.UserRoleId == 10)
            elif cat == "employee":
                conditions.append(User.UserRoleId.in_([5, 6, 8, 10, 11, 24]))

            if clean_query:
                conditions.append(User.UserName.like(f"{clean_query}%"))

            stmt = select(User).where(and_(*conditions)).order_by(User.UserName).limit(safe_limit)
            res = await self.session.execute(stmt)
            for u in res.scalars().all():
                items.append(
                    AutocompleteItem(
                        id=u.UserId,
                        label=f"{u.UserName} (Role: {u.UserRoleId})",
                        value=u.UserName,
                        category=cat,
                        sub_text=f"Branch: {u.BranchId or '-'} | Active",
                        extra={"user_id": u.UserId, "username": u.UserName, "role_id": u.UserRoleId},
                    )
                )

        elif cat == "rto":
            conditions = [or_(RTOMaster.isdeleted == 0, RTOMaster.isdeleted.is_(None))]
            if clean_query:
                s = f"{clean_query}%"
                conditions.append(or_(RTOMaster.REG_code.like(s), RTOMaster.RTOLocation.like(s)))
            stmt = select(RTOMaster).where(and_(*conditions)).order_by(RTOMaster.REG_code).limit(safe_limit)
            res = await self.session.execute(stmt)
            for r in res.scalars().all():
                items.append(
                    AutocompleteItem(
                        id=r.RTOId,
                        label=f"{r.REG_code} - {r.RTOLocation} ({r.District})",
                        value=r.REG_code or "",
                        category="rto",
                        sub_text=f"District: {r.District} | Zone: {r.zone or 'A'}",
                        extra={"rto_id": r.RTOId, "reg_code": r.REG_code, "zone": r.zone},
                    )
                )

        elif cat == "make":
            conditions = [VehicleMake.isdeleted == 0]
            if clean_query:
                conditions.append(VehicleMake.Make_Name.like(f"{clean_query}%"))
            stmt = select(VehicleMake).where(and_(*conditions)).order_by(VehicleMake.Make_Name).limit(safe_limit)
            res = await self.session.execute(stmt)
            for m in res.scalars().all():
                items.append(
                    AutocompleteItem(
                        id=m.Make_ID,
                        label=m.Make_Name or "",
                        value=m.Make_Name or "",
                        category="make",
                        sub_text=None,
                        extra={"make_id": m.Make_ID},
                    )
                )

        elif cat == "bank":
            conditions = [BankMaster.isdeleted == 0]
            if clean_query:
                conditions.append(BankMaster.BankName.like(f"{clean_query}%"))
            stmt = select(BankMaster).where(and_(*conditions)).order_by(BankMaster.BankName).limit(safe_limit)
            res = await self.session.execute(stmt)
            for b in res.scalars().all():
                items.append(
                    AutocompleteItem(
                        id=b.BankId,
                        label=b.BankName,
                        value=b.BankName,
                        category="bank",
                        sub_text=None,
                        extra={"bank_id": b.BankId},
                    )
                )

        elif cat == "branch":
            conditions = [Branch.isdeleted == 0]
            if clean_query:
                conditions.append(
                    or_(
                        Branch.BranchName.like(f"{clean_query}%"),
                        Branch.BranchCode.like(f"{clean_query}%"),
                    )
                )
            stmt = select(Branch).where(and_(*conditions)).order_by(Branch.BranchName).limit(safe_limit)
            res = await self.session.execute(stmt)
            for br in res.scalars().all():
                items.append(
                    AutocompleteItem(
                        id=br.BranchId,
                        label=f"{br.BranchName} ({br.BranchCode or '-'})",
                        value=br.BranchName or "",
                        category="branch",
                        sub_text=br.Address,
                        extra={"branch_id": br.BranchId, "code": br.BranchCode},
                    )
                )

        return AutocompleteResponse(
            category=category,
            query=clean_query,
            total=len(items),
            items=items,
        )

    # -----------------------------------------------------------------------
    # Duplicate Registration Check (Maps checkVehicleNo)
    # -----------------------------------------------------------------------

    async def check_vehicle_no(
        self,
        registration_no: str,
        financial_year: Optional[str] = None,
    ) -> VehicleDuplicateCheckResponse:
        """
        Validates vehicle registration number duplicate status.
        Maps SearchMethods.aspx.cs::checkVehicleNo and AppSearchMethod.aspx.cs::checkVehicleNo.
        """
        reg_clean = registration_no.strip().upper().replace(" ", "").replace("-", "")

        # Query vehicle record
        v_stmt = select(VehicleDetails).where(
            func.replace(func.replace(VehicleDetails.RegistrationNo, " ", ""), "-", "") == reg_clean,
            or_(VehicleDetails.isdeleted == "0", VehicleDetails.isdeleted == 0, VehicleDetails.isdeleted.is_(None)),
        )
        v_res = await self.session.execute(v_stmt)
        vehicle = v_res.scalars().first()

        if not vehicle:
            return VehicleDuplicateCheckResponse(
                registration_no=registration_no,
                financial_year=financial_year,
                is_duplicate=False,
                is_allowed=True,
                existing_transaction_id=None,
                message="Vehicle registration number is available for new policy booking",
            )

        # Check existing transaction for this vehicle
        t_conditions = [
            Transaction.CustVehId == vehicle.CustVehId,
            or_(Transaction.isdeleted == "0", Transaction.isdeleted == 0, Transaction.isdeleted.is_(None)),
        ]
        if financial_year:
            t_conditions.append(Transaction.FinancialYear == financial_year.strip())

        t_stmt = (
            select(Transaction)
            .where(and_(*t_conditions))
            .order_by(Transaction.TransanctionId.desc())
        )
        t_res = await self.session.execute(t_stmt)
        existing_tx = t_res.scalars().first()

        if existing_tx:
            return VehicleDuplicateCheckResponse(
                registration_no=registration_no,
                financial_year=financial_year,
                is_duplicate=True,
                is_allowed=False,
                existing_transaction_id=existing_tx.TransanctionId,
                message=f"Duplicate policy exists for vehicle {registration_no} in FY {financial_year or 'active'} (Inward: {existing_tx.InwardNo})",
            )

        return VehicleDuplicateCheckResponse(
            registration_no=registration_no,
            financial_year=financial_year,
            is_duplicate=False,
            is_allowed=True,
            existing_transaction_id=None,
            message="Vehicle exists in database with no overlapping active policy in specified financial year",
        )

    # -----------------------------------------------------------------------
    # Pending Operational Counters (Maps getNewAppEntry, getPendingEntryOp, etc.)
    # -----------------------------------------------------------------------

    async def get_pending_counters(
        self,
        current_user: User,
    ) -> PendingCountersResponse:
        """
        Aggregates operational inbox counters for UI badges and polling.
        Maps getNewAppEntry, getNewAppEntryOp, getPendingEntryOp, getPendingInwardOp,
        getNewAppEndorsementEntry, getNewMISAppEntry, getNewAgentAppEntry.
        """
        caller_role = getattr(current_user, "role_name", "") or ""
        caller_branch_id = getattr(current_user, "branch_id", None) or getattr(current_user, "BranchId", None)
        is_global = caller_role.upper() in GLOBAL_READ_ROLES or caller_role.upper() in GLOBAL_ADMIN_ROLES

        # 1. New app entries
        app_stmt = select(func.count(TransactionAppNew.TransId)).where(
            TransactionAppNew.IsSubmit == 1,
        )
        new_apps = (await self.session.execute(app_stmt)).scalar() or 0

        # 2. Operator pending entries
        op_stmt = select(func.count(Transaction.TransanctionId)).where(
            or_(Transaction.isdeleted == "0", Transaction.isdeleted == 0, Transaction.isdeleted.is_(None)),
            Transaction.TStatus == "Pending",
        )
        if not is_global and caller_branch_id is not None:
            op_stmt = op_stmt.where(Transaction.BranchId == caller_branch_id)
        pending_op = (await self.session.execute(op_stmt)).scalar() or 0

        # 3. Pending inward locking
        inward_stmt = select(func.count(Transaction.TransanctionId)).where(
            or_(Transaction.isdeleted == "0", Transaction.isdeleted == 0, Transaction.isdeleted.is_(None)),
            Transaction.pendingStatus == 1,
        )
        if not is_global and caller_branch_id is not None:
            inward_stmt = inward_stmt.where(Transaction.BranchId == caller_branch_id)
        pending_inward = (await self.session.execute(inward_stmt)).scalar() or 0

        # 4. Pending endorsements
        end_stmt = select(func.count(PolicyEndorsement.EndorsementId)).where(
            or_(PolicyEndorsement.isdeleted == "0", PolicyEndorsement.isdeleted == 0, PolicyEndorsement.isdeleted.is_(None)),
            PolicyEndorsement.EndorsementStatus.in_(["SUBMITTED", "PENDING", "Pending"]),
        )
        pending_end = (await self.session.execute(end_stmt)).scalar() or 0

        # 5. Pending MIS entries
        mis_stmt = select(func.count(Transaction.TransanctionId)).where(
            or_(Transaction.isdeleted == "0", Transaction.isdeleted == 0, Transaction.isdeleted.is_(None)),
            Transaction.MISId > 0,
            Transaction.TStatus == "Pending",
        )
        if not is_global and caller_branch_id is not None:
            mis_stmt = mis_stmt.where(Transaction.BranchId == caller_branch_id)
        pending_mis = (await self.session.execute(mis_stmt)).scalar() or 0

        # 6. Pending agent entries
        agent_stmt = select(func.count(Transaction.TransanctionId)).where(
            or_(Transaction.isdeleted == "0", Transaction.isdeleted == 0, Transaction.isdeleted.is_(None)),
            Transaction.AgentId > 0,
            Transaction.TStatus == "Pending",
        )
        if not is_global and caller_branch_id is not None:
            agent_stmt = agent_stmt.where(Transaction.BranchId == caller_branch_id)
        pending_agent = (await self.session.execute(agent_stmt)).scalar() or 0

        return PendingCountersResponse(
            new_app_entries=new_apps,
            operator_pending_entries=pending_op,
            operator_pending_inward=pending_inward,
            new_endorsement_entries=pending_end,
            new_mis_entries=pending_mis,
            new_agent_entries=pending_agent,
        )

    # -----------------------------------------------------------------------
    # Dashboard Chart & Summary Data (Maps chart_Premium_Summary, pie_*, etc.)
    # -----------------------------------------------------------------------

    async def get_dashboard_summary(
        self,
        current_user: User,
        chart_type: str = "premium_summary",
    ) -> DashboardChartDataResponse:
        """
        Computes dashboard chart data and summary strings.
        Maps chart_Premium_Summary, pie_Premium_Summary, pie_ODPremium_Summary,
        PolicyMode_Premium_Summary, businesstype_Premium_Summary, ProductType_Premium_Summary,
        pie_ODNetPremium_Summary, pie_ODNetMonthlyPremium, pie_ODNetDailyPremium,
        DashBoardInsuranceCompany, pie_Premium_Summary_Vehicle.
        """
        caller_role = getattr(current_user, "role_name", "") or ""
        caller_branch_id = getattr(current_user, "branch_id", None) or getattr(current_user, "BranchId", None)
        is_global = caller_role.upper() in GLOBAL_READ_ROLES or caller_role.upper() in GLOBAL_ADMIN_ROLES

        ctype = chart_type.strip().lower()

        base_conds = [or_(Transaction.isdeleted == "0", Transaction.isdeleted == 0, Transaction.isdeleted.is_(None))]
        if not is_global and caller_branch_id is not None:
            base_conds.append(Transaction.BranchId == caller_branch_id)

        # 1. Total business aggregate
        agg_stmt = select(
            func.count(Transaction.TransanctionId),
            func.coalesce(func.sum(Transaction.Amount), 0),
        ).where(and_(*base_conds))
        agg_res = await self.session.execute(agg_stmt)
        total_cnt, total_amt = agg_res.first() or (0, 0)
        total_dec = Decimal(str(total_amt or 0))

        labels: List[str] = []
        values: List[Decimal] = []

        if ctype in ("od_net", "pie_odnetpremium_summary", "pie_odpremium_summary"):
            stmt = select(
                func.coalesce(func.sum(Transaction.ODPermium), 0),
                func.coalesce(func.sum(Transaction.NetPermium), 0),
            ).where(and_(*base_conds))
            r = (await self.session.execute(stmt)).first()
            labels = ["Own Damage Premium", "Net Premium"]
            values = [Decimal(str(r[0] or 0)), Decimal(str(r[1] or 0))]

        elif ctype in ("insurer", "dashboardinsurancecompany"):
            stmt = (
                select(
                    Transaction.InsuranceCompanyId,
                    func.coalesce(func.sum(Transaction.Amount), 0),
                )
                .where(and_(*base_conds))
                .group_by(Transaction.InsuranceCompanyId)
                .order_by(func.sum(Transaction.Amount).desc())
                .limit(10)
            )
            for r in (await self.session.execute(stmt)).all():
                labels.append(f"Insurer {r[0]}")
                values.append(Decimal(str(r[1] or 0)))

        elif ctype in ("vehicle", "vehicle_type", "pie_premium_summary_vehicle"):
            stmt = (
                select(
                    func.coalesce(VehicleDetails.Veh_Type_ID, 0),
                    func.coalesce(func.sum(Transaction.Amount), 0),
                )
                .join(VehicleDetails, Transaction.CustVehId == VehicleDetails.CustVehId, isouter=True)
                .where(and_(*base_conds))
                .group_by(VehicleDetails.Veh_Type_ID)
                .limit(10)
            )
            for r in (await self.session.execute(stmt)).all():
                labels.append(f"Vehicle Type {r[0]}")
                values.append(Decimal(str(r[1] or 0)))

        else:
            # Default premium summary breakdown
            labels = ["Gross Premium"]
            values = [total_dec]

        summary_str = f"Total Policies: {total_cnt} | Total Premium: ₹{total_dec:,.2f}"

        return DashboardChartDataResponse(
            chart_name=chart_type,
            total_amount=total_dec,
            total_count=total_cnt,
            labels=labels,
            values=values,
            summary_string=summary_str,
        )

    # -----------------------------------------------------------------------
    # Server Heartbeat (Maps getserverInactive)
    # -----------------------------------------------------------------------

    async def get_server_status(self) -> ServerStatusResponse:
        """
        Returns active server status.
        Maps SearchMethods.aspx.cs::getserverInactive.
        """
        return ServerStatusResponse(
            status="ACTIVE",
            is_inactive=False,
            message="Server is active and operational",
            server_time=datetime.now(timezone.utc).isoformat(),
        )
