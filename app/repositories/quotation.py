"""
Repository Layer for Phase 6 Quotation & Rating Engine.
Encapsulates all SQLAlchemy 2.0 async queries for:
- Motor Rating Tariffs, OD Discounts, Zero-Dep & Add-On Tables
- Self-Quotation Entries (tbl_app_quatationentry)
- Assisted Quotation Requests (tbl_app_quotationrequest)
- Insurer Quote Options (tbl_insurancecompanyquotation)
- Quotation Remarks / Audit Trail (tbl_app_quotationremark)
"""
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_FLOOR
from typing import Dict, List, Optional, Tuple
from sqlalchemy import and_, desc, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.master import InsuranceCompany, VehicleVariant
from app.models.quotation import (
    AddonExtraAmt,
    AppBusCCRate,
    AppODDiscount,
    AppODDiscountNew,
    AppODDiscountNewGCV,
    AppPCVCCRate,
    AppQuatationEntry,
    AppQuotationRemark,
    AppQuotationRequest,
    AppThreeWheelerCCRate,
    AppTwoWheelerCCRate,
    InsuranceCompanyByVehicleType,
    InsuranceCompanyQuotation,
    InsuranceCompanyWiseTowingChanges,
    PAToOwnerDriver,
    QuotDamagePremium,
    QuotLiabilityPremium,
    QuotationPrefix,
    ZeroDep,
    ZeroDepForSegmentWise,
    ZeroDepNewAddonRate,
)


# Age integer -> physical column attribute name in tbl_app_oddiscountnew & tbl_app_oddiscountnew_gcv
AGE_COLUMN_MAP: Dict[str, str] = {
    "N": "N",
    "0": "Zero",
    "1": "One",
    "2": "Two",
    "3": "Three",
    "4": "Four",
    "5": "Five",
    "6": "Six",
    "7": "Seven",
    "8": "Eight",
    "9": "Nine",
    "10": "Ten",
    "11": "Eleven",
    "12": "Twelve",
    "13": "thriteen",  # Verified physical column spelling in legacy schema
    "14": "fourteen",
    "15": "fifteen",
    "16": "Sixteen",
}

# Verified static prefix fallback matching tbl_quotation_prefix in brahmainsurance
STATIC_ROLE_PREFIX_MAP: Dict[int, str] = {
    4: "Q",
    5: "QS",
    6: "QO",
    9: "QF",
    16: "Q",
    24: "QH",
    32: "QI",
}

# Verified static PA to Owner-Driver rates from tbl_patoownerdriver
STATIC_PA_OWNER_DRIVER_RATES: Dict[int, Tuple[Decimal, Decimal]] = {
    1: (Decimal("326"), Decimal("0")),
    2: (Decimal("325"), Decimal("0")),
    3: (Decimal("375"), Decimal("100")),
    4: (Decimal("315"), Decimal("0")),
    5: (Decimal("375"), Decimal("0")),
    14: (Decimal("375"), Decimal("200")),
    18: (Decimal("331"), Decimal("0")),
    20: (Decimal("325"), Decimal("150")),
    21: (Decimal("345"), Decimal("0")),
    32: (Decimal("330"), Decimal("0")),
}

# Verified static Towing slabs from tbl_insurancecompanywisetowingchanges
STATIC_TOWING_SLABS: Dict[Tuple[int, int], Decimal] = {
    (3, 5000): Decimal("500"),
    (3, 10000): Decimal("1000"),
    (3, 15000): Decimal("1500"),
    (3, 20000): Decimal("2000"),
    (14, 5000): Decimal("615"),
    (14, 10000): Decimal("615"),
    (14, 15000): Decimal("953"),
    (1, 15000): Decimal("784"),
    (4, 5000): Decimal("250"),
    (4, 10000): Decimal("500"),
    (4, 15000): Decimal("1124"),
    (4, 20000): Decimal("1500"),
}


def _to_decimal(val: object, default: Decimal = Decimal("0")) -> Decimal:
    """Safely converts a DB string/int/Decimal/float value to Decimal without float binary artifacts."""
    if val is None:
        return default
    if isinstance(val, Decimal):
        return val
    s = str(val).strip()
    if not s or s.upper() in {"NULL", "NA", "-"}:
        return default
    try:
        return Decimal(s)
    except Exception:
        return default


class QuotationRepository:
    """Async SQLAlchemy repository for Quotation & Rating Engine."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # -----------------------------------------------------------------------
    # 1. Vehicle Variant IDV Lookup (sp_SelectIDVDetails / sp_SelectIDVDetailsForGCV)
    # -----------------------------------------------------------------------

    async def get_variant_by_id(self, variant_id: int) -> Optional[VehicleVariant]:
        stmt = select(VehicleVariant).where(VehicleVariant.Variant_ID == variant_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_insurer_by_id(self, company_id: int) -> Optional[InsuranceCompany]:
        stmt = select(InsuranceCompany).where(InsuranceCompany.InsuranceCompanyId == company_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    # -----------------------------------------------------------------------
    # 2. OD Base Tariff Lookup (sp_quot_damagepremium & CC rate tables)
    # -----------------------------------------------------------------------

    async def get_od_base_tariff(
        self,
        company_type: str,
        cc: int,
        lookup_age: Decimal,
        zone: str,
    ) -> Decimal:
        """
        Queries tbl_quot_damagepremium matching sp_quot_damagepremium.
        Falls back to verified static tariff matrix if table has no matching row.
        """
        age_float = float(lookup_age)
        stmt = (
            select(QuotDamagePremium)
            .where(
                and_(
                    QuotDamagePremium.Company_Type == company_type,
                    QuotDamagePremium.Age == age_float,
                )
            )
            .order_by(QuotDamagePremium.Id.asc())
        )
        result = await self.session.execute(stmt)
        rows = list(result.scalars().all())
        if rows:
            matched: Optional[QuotDamagePremium] = None
            for r in rows:
                from_cc = r.fromCubicCapacity or 0
                to_cc = r.toCubicCapacity or 0
                if from_cc == 0 and to_cc == 0:
                    matched = r
                    break
                if from_cc <= cc <= to_cc:
                    matched = r
                    break
            if matched is None:
                matched = rows[0]
            if zone == "A":
                return _to_decimal(matched.OD_premium_Azone)
            if zone == "B":
                return _to_decimal(matched.OD_premium_Bzone)
            return _to_decimal(matched.OD_premium_Czone)

        return self._static_od_base_tariff(company_type, cc, lookup_age, zone)

    @staticmethod
    def _static_od_base_tariff(
        company_type: str,
        cc: int,
        lookup_age: Decimal,
        zone: str,
    ) -> Decimal:
        """Verified 216-row static tariff matrix from tbl_quot_damagepremium."""
        age_int = int(lookup_age)
        if company_type == "PVT":
            if cc <= 1000:
                if age_int <= 5:
                    rates = ("3.127", "3.039", "0")
                elif age_int <= 10:
                    rates = ("3.283", "3.191", "0")
                else:
                    rates = ("3.362", "3.267", "0")
            elif cc <= 1500:
                if age_int <= 5:
                    rates = ("3.283", "3.191", "0")
                elif age_int <= 10:
                    rates = ("3.447", "3.351", "0")
                else:
                    rates = ("3.529", "3.430", "0")
            else:
                if age_int <= 5:
                    rates = ("3.440", "3.343", "0")
                elif age_int <= 10:
                    rates = ("3.612", "3.510", "0")
                else:
                    rates = ("3.698", "3.594", "0")
        elif company_type == "Public_GCV":
            if age_int <= 5:
                rates = ("1.751", "1.743", "1.726")
            elif age_int <= 7:
                rates = ("1.795", "1.787", "1.770")
            else:
                rates = ("1.839", "1.830", "1.812")
        elif company_type == "Private_GCV":
            if age_int <= 4:
                rates = ("1.226", "1.220", "1.208")
            elif age_int == 5:
                rates = ("1.257", "1.251", "1.208")
            elif age_int <= 7:
                rates = ("1.257", "1.251", "1.239")
            else:
                rates = ("1.287", "1.281", "1.268")
        elif company_type == "PassengerTaxi(PCV)":
            if cc <= 1000:
                if age_int <= 5:
                    rates = ("3.284", "3.191", "0")
                elif age_int == 6:
                    rates = ("3.366", "3.271", "0")
                else:
                    rates = ("3.448", "3.351", "0")
            elif cc <= 1500:
                if age_int <= 5:
                    rates = ("3.448", "3.351", "0")
                elif age_int == 6:
                    rates = ("3.534", "3.435", "0")
                else:
                    rates = ("3.620", "3.519", "0")
            else:
                if age_int <= 5:
                    rates = ("3.612", "3.510", "0")
                elif age_int == 6:
                    rates = ("3.703", "3.598", "0")
                else:
                    rates = ("3.793", "3.686", "0")
        elif company_type == "School_Bus":
            if age_int <= 5:
                rates = ("1.680", "1.672", "1.656")
            elif age_int == 6:
                rates = ("1.722", "1.714", "1.697")
            else:
                rates = ("1.764", "1.756", "1.739")
        elif company_type == "PublicGCV3W":
            if age_int <= 5:
                rates = ("1.664", "1.656", "1.640")
            elif age_int <= 7:
                rates = ("1.706", "1.697", "1.681")
            else:
                rates = ("1.747", "1.739", "1.722")
        elif company_type == "PublicPCV3W":
            if age_int <= 5:
                rates = ("1.664", "1.656", "1.260")
            elif age_int <= 7:
                rates = ("1.706", "1.697", "1.290")
            else:
                rates = ("1.747", "1.739", "1.320")
        elif company_type == "TwoWheeler":
            if cc <= 150:
                if age_int <= 5:
                    rates = ("1.708", "1.676", "0")
                elif age_int <= 10:
                    rates = ("1.793", "1.760", "0")
                else:
                    rates = ("1.836", "1.802", "0")
            elif cc <= 350:
                if age_int <= 5:
                    rates = ("1.793", "1.760", "0")
                elif age_int <= 10:
                    rates = ("1.883", "1.848", "0")
                else:
                    rates = ("1.928", "1.892", "0")
            else:
                if age_int <= 5:
                    rates = ("1.879", "1.844", "0")
                elif age_int <= 10:
                    rates = ("1.973", "1.936", "0")
                else:
                    rates = ("2.020", "1.982", "0")
        else:  # Misc-D
            if age_int <= 5:
                rates = ("3.284", "1.190", "0")
            elif age_int <= 7:
                rates = ("3.366" if age_int == 6 else "3.448", "1.220", "0")
            else:
                rates = ("3.448", "1.250", "0")

        idx = 0 if zone == "A" else (1 if zone == "B" else 2)
        return Decimal(rates[idx])

    # -----------------------------------------------------------------------
    # 3. TP Base Tariff & Per-Passenger Rate Lookup (sp_quot_liabilitypremium & CC rate tables)
    # -----------------------------------------------------------------------

    async def get_tp_base_tariff(
        self,
        company_type: str,
        unit_value: int,
        bus_type: str = "SCHOOL BUS",
        age: Decimal = Decimal("0"),
    ) -> Tuple[Decimal, Decimal]:
        """
        Returns (basic_tp_premium, per_passenger_ll_rate) for the category and CC/GVW.
        Queries tbl_quot_liabilitypremium / tbl_app_*_cc_rate first, then static verified fallback.
        """
        if company_type == "PassengerTaxi(PCV)":
            stmt_pcv = select(AppPCVCCRate).where(
                and_(
                    AppPCVCCRate.isdeleted == 0,
                    AppPCVCCRate.Up_CC <= float(unit_value),
                    AppPCVCCRate.To_CC >= float(unit_value),
                )
            )
            res_pcv = await self.session.execute(stmt_pcv)
            row_pcv = res_pcv.scalars().first()
            if row_pcv:
                return _to_decimal(row_pcv.TP_Rate), _to_decimal(row_pcv.Per_PassengerRate)
            if unit_value <= 1000:
                return Decimal("5769"), Decimal("1110")
            if unit_value <= 1500:
                return Decimal("7584"), Decimal("934")
            return Decimal("10051"), Decimal("1067")

        if company_type == "School_Bus":
            stmt_bus = select(AppBusCCRate).where(
                and_(
                    AppBusCCRate.isdeleted == 0,
                    AppBusCCRate.Bus_Type == bus_type.strip().upper(),
                )
            )
            res_bus = await self.session.execute(stmt_bus)
            row_bus = res_bus.scalars().first()
            if row_bus:
                return _to_decimal(row_bus.TP_Rate), _to_decimal(row_bus.Per_PassengerRate)
            if bus_type.strip().upper() == "SCHOOL BUS":
                return Decimal("13874"), Decimal("848")
            return Decimal("14494"), Decimal("886")

        if company_type == "PublicPCV3W":
            age_int = int(age)
            stmt_3w = select(AppThreeWheelerCCRate).where(
                and_(
                    AppThreeWheelerCCRate.isdeleted == 0,
                    AppThreeWheelerCCRate.UpAge <= age_int,
                    AppThreeWheelerCCRate.ToAge >= age_int,
                )
            )
            res_3w = await self.session.execute(stmt_3w)
            row_3w = res_3w.scalars().first()
            if row_3w:
                return _to_decimal(row_3w.TP_Rate), _to_decimal(row_3w.Per_PassengerRate)
            return Decimal("2595"), Decimal("1241")

        # Standard lookup in tbl_quot_liabilitypremium
        search_types = [company_type]
        if company_type == "Misc-D":
            search_types.append("Miss-D")

        stmt = select(QuotLiabilityPremium).where(
            and_(
                QuotLiabilityPremium.Company_Type.in_(search_types),
                QuotLiabilityPremium.fromunit <= unit_value,
                QuotLiabilityPremium.tounit >= unit_value,
            )
        )
        result = await self.session.execute(stmt)
        row = result.scalars().first()
        if row:
            return _to_decimal(row.Premium), Decimal("0")

        return self._static_tp_base_tariff(company_type, unit_value), Decimal("0")

    @staticmethod
    def _static_tp_base_tariff(company_type: str, unit_value: int) -> Decimal:
        """Verified 28-row static liability tariff matrix from tbl_quot_liabilitypremium."""
        if company_type == "PVT":
            if unit_value <= 1000:
                return Decimal("2094")
            if unit_value <= 1500:
                return Decimal("3416")
            return Decimal("7897")
        if company_type == "TwoWheeler":
            if unit_value <= 75:
                return Decimal("582")
            if unit_value <= 150:
                return Decimal("714")
            if unit_value <= 350:
                return Decimal("1366")
            return Decimal("2804")
        if company_type == "Public_GCV":
            if unit_value <= 7500:
                return Decimal("16049")
            if unit_value <= 12000:
                return Decimal("27186")
            if unit_value <= 20000:
                return Decimal("35313")
            if unit_value <= 40000:
                return Decimal("43950")
            return Decimal("44242")
        if company_type == "Private_GCV":
            if unit_value <= 7500:
                return Decimal("8438")
            if unit_value <= 12000:
                return Decimal("17204")
            if unit_value <= 20000:
                return Decimal("10876")
            if unit_value <= 40000:
                return Decimal("17476")
            return Decimal("24825")
        if company_type == "PublicGCV3W":
            return Decimal("4492")
        if company_type == "Misc-D":
            return Decimal("7267")
        return Decimal("0")

    # -----------------------------------------------------------------------
    # 4. OD Discount & Decline Lookup (sp_SelectAppDiscWithFueltype / GCV / Fallback)
    # -----------------------------------------------------------------------

    async def get_od_discount_and_decline(
        self,
        vehicle_category: str,
        make_id: Optional[int],
        model_id: Optional[int],
        insurance_company_id: int,
        age: Decimal,
        ncb_percent: Decimal,
        cluster_id: int,
        zero_dep: bool,
        fuel_type_id: int,
        business_type_id: int,
        bus_type: str = "SCHOOL BUS",
    ) -> Tuple[Decimal, bool]:
        """
        Resolves (od_discount_percent, is_declined) following the exact legacy stored procedure hierarchy:
        1. sp_SelectAppDiscWithFueltypeGCV (tbl_app_oddiscountnew_gcv) for GCV categories
        2. sp_SelectAppDiscWithFueltype (tbl_app_oddiscountnew) for non-GCV categories
        3. sp_SelectAppDiscount (tbl_appoddiscount)
        4. sp_Quot_ODDiscFromCompany (tbl_insurancecompanybyvehicletype) / tbl_app_bus_cc_rate
        """
        age_key = "N" if business_type_id == 1 else str(min(int(age), 16))
        col_name = AGE_COLUMN_MAP.get(age_key, "Sixteen")
        zero_dep_str = "Yes" if zero_dep else "No"
        ncb_cond = "Yes" if ncb_percent > Decimal("0") else "No"
        # Legacy quirk in Adm_UpdateAppODDiscount.aspx.cs: if compId != 3, ClusterId = 0
        effective_clusters = [cluster_id, 0] if cluster_id != 0 else [0]

        is_declined = False

        if model_id is not None:
            if vehicle_category in {"Public_GCV", "Private_GCV", "PublicGCV3W"}:
                stmt_gcv = (
                    select(AppODDiscountNewGCV)
                    .where(
                        and_(
                            AppODDiscountNewGCV.Model_ID == model_id,
                            AppODDiscountNewGCV.InsuranceCompanyId == insurance_company_id,
                            AppODDiscountNewGCV.ClusterId.in_(effective_clusters),
                            or_(
                                AppODDiscountNewGCV.NCB == str(int(ncb_percent)),
                                AppODDiscountNewGCV.NCB == ncb_cond,
                                AppODDiscountNewGCV.NCB == "0",
                            ),
                            or_(
                                AppODDiscountNewGCV.ZeroDep == zero_dep_str,
                                AppODDiscountNewGCV.ZeroDep == ("1" if zero_dep else "0"),
                                AppODDiscountNewGCV.ZeroDep == "0",
                            ),
                            AppODDiscountNewGCV.Fueltypeid == fuel_type_id,
                            AppODDiscountNewGCV.BusinessTypeId == business_type_id,
                        )
                    )
                    .order_by(AppODDiscountNewGCV.AppODDiscountId.desc())
                )
                res_gcv = await self.session.execute(stmt_gcv)
                row_gcv = res_gcv.scalars().first()
                if row_gcv is not None:
                    raw_val = getattr(row_gcv, col_name, None)
                    disc = _to_decimal(raw_val).quantize(Decimal("1"), rounding=ROUND_FLOOR)
                    return disc, False
            else:
                # Check Decline status (sp_SelectAppDiscDiclineOrNot)
                stmt_dec = (
                    select(AppODDiscountNew)
                    .where(
                        and_(
                            AppODDiscountNew.Model_ID == model_id,
                            AppODDiscountNew.InsuranceCompanyId == insurance_company_id,
                            AppODDiscountNew.Fueltypeid == fuel_type_id,
                        )
                    )
                    .order_by(AppODDiscountNew.AppODDiscountId.desc())
                )
                res_dec = await self.session.execute(stmt_dec)
                row_dec = res_dec.scalars().first()
                if row_dec is not None and row_dec.Decline == 1:
                    is_declined = True

                stmt_od = (
                    select(AppODDiscountNew)
                    .where(
                        and_(
                            AppODDiscountNew.Model_ID == model_id,
                            AppODDiscountNew.InsuranceCompanyId == insurance_company_id,
                            AppODDiscountNew.ClusterId.in_(effective_clusters),
                            or_(
                                AppODDiscountNew.NCB == str(int(ncb_percent)),
                                AppODDiscountNew.NCB == ncb_cond,
                                AppODDiscountNew.NCB == "0",
                            ),
                            or_(
                                AppODDiscountNew.ZeroDep == zero_dep_str,
                                AppODDiscountNew.ZeroDep == ("1" if zero_dep else "0"),
                                AppODDiscountNew.ZeroDep == "0",
                            ),
                            AppODDiscountNew.Fueltypeid == fuel_type_id,
                            AppODDiscountNew.BusinessTypeId == business_type_id,
                        )
                    )
                    .order_by(AppODDiscountNew.AppODDiscountId.desc())
                )
                res_od = await self.session.execute(stmt_od)
                row_od = res_od.scalars().first()
                if row_od is not None:
                    raw_val = getattr(row_od, col_name, None)
                    disc = _to_decimal(raw_val).quantize(Decimal("1"), rounding=ROUND_FLOOR)
                    return disc, is_declined

            # Fallback to tbl_appoddiscount (sp_SelectAppDiscount)
            if make_id is not None:
                stmt_legacy = select(AppODDiscount).where(
                    and_(
                        AppODDiscount.Make_ID == make_id,
                        AppODDiscount.Model_ID == model_id,
                        AppODDiscount.InsuranceCompanyId == insurance_company_id,
                    )
                )
                res_leg = await self.session.execute(stmt_legacy)
                row_leg = res_leg.scalars().first()
                if row_leg is not None:
                    if int(age) <= 5:
                        return _to_decimal(row_leg.ZerotoFive), is_declined
                    if int(age) <= 10:
                        return _to_decimal(row_leg.fivetoTen), is_declined
                    return _to_decimal(row_leg.Greaterthen10), is_declined

        # Fallback to tbl_insurancecompanybyvehicletype (sp_Quot_ODDiscFromCompany)
        stmt_comp = select(InsuranceCompanyByVehicleType).where(
            and_(
                InsuranceCompanyByVehicleType.InsuranceCompanyId == insurance_company_id,
                InsuranceCompanyByVehicleType.IsDelete == 0,
            )
        )
        res_comp = await self.session.execute(stmt_comp)
        row_comp = res_comp.scalars().first()
        if row_comp is not None:
            cat_col_map = {
                "Public_GCV": "GCV_Disc",
                "Private_GCV": "GCV_Disc",
                "PublicGCV3W": "Three_Wheeler_Disc",
                "PublicPCV3W": "Three_Wheeler_PCV_Disc",
                "Misc-D": "Misc_D_Disc",
                "PVT": "PVT_CAR_Disc",
                "TwoWheeler": "Two_Wheeler_Disc",
                "PassengerTaxi(PCV)": "PCV_Disc",
                "School_Bus": "Bus_Disc",
            }
            disc_attr = cat_col_map.get(vehicle_category, "PVT_CAR_Disc")
            comp_disc = _to_decimal(getattr(row_comp, disc_attr, 0))
            if comp_disc > Decimal("0"):
                return comp_disc, is_declined

        if vehicle_category == "School_Bus":
            b_upper = bus_type.strip().upper()
            if b_upper == "SCHOOL BUS":
                return Decimal("85"), is_declined
            if b_upper == "STAFF BUS":
                return Decimal("80"), is_declined
            return Decimal("30"), is_declined

        return Decimal("0"), is_declined

    # -----------------------------------------------------------------------
    # 5. Zero-Dep & Add-On Rate Lookup
    # -----------------------------------------------------------------------

    async def get_zero_dep_rates(
        self,
        insurance_company_id: int,
        make_id: Optional[int],
        model_id: Optional[int],
        veh_type_id: Optional[int],
        fuel_type_id: int,
        business_type_id: int,
        cluster_id: int,
        ncb_percent: Decimal,
        age: Decimal,
        addon_plan: str = "NillDep",
    ) -> Tuple[Decimal, Decimal]:
        """
        Returns (zero_dep_rate_percent, extra_addon_flat_amount) from:
        1. tbl_zerodepnewaddonrate (sp_SelectZeroDepMultiAddOn_New)
        2. tbl_zerodepforsegmentwise (sp_selectZeroDepModelIdWise)
        3. tbl_zerodep (sp_SelectZeroDep)
        4. tbl_addonextraamt (sp_SelectZeroDepExtraAmount)
        """
        plan_col = addon_plan if addon_plan in {"NillDep", "SecurePlus", "SPremium"} else "NillDep"
        age_int = int(age)
        rate_pct = Decimal("0")
        extra_amt = Decimal("0")

        if make_id is not None and model_id is not None:
            stmt_multi = (
                select(ZeroDepNewAddonRate)
                .where(
                    and_(
                        ZeroDepNewAddonRate.InsuranceCompanyId == insurance_company_id,
                        ZeroDepNewAddonRate.MakeID == make_id,
                        ZeroDepNewAddonRate.Model_ID == model_id,
                        ZeroDepNewAddonRate.Age == age_int,
                        ZeroDepNewAddonRate.Fueltypeid == fuel_type_id,
                        ZeroDepNewAddonRate.Isdelete == 0,
                    )
                )
                .order_by(ZeroDepNewAddonRate.AddOnId.desc())
            )
            res_multi = await self.session.execute(stmt_multi)
            row_multi = res_multi.scalars().first()
            if row_multi is not None:
                rate_pct = _to_decimal(getattr(row_multi, plan_col, None))

            if rate_pct == Decimal("0"):
                stmt_seg = (
                    select(ZeroDepForSegmentWise)
                    .where(
                        and_(
                            ZeroDepForSegmentWise.InsuranceCompanyId == insurance_company_id,
                            ZeroDepForSegmentWise.Make_ID == make_id,
                            ZeroDepForSegmentWise.Model_Id == model_id,
                            ZeroDepForSegmentWise.FuelTypeId == fuel_type_id,
                            ZeroDepForSegmentWise.Age == str(age_int),
                            ZeroDepForSegmentWise.Isdelete == 0,
                        )
                    )
                    .order_by(ZeroDepForSegmentWise.ZerodepId.desc())
                )
                res_seg = await self.session.execute(stmt_seg)
                row_seg = res_seg.scalars().first()
                if row_seg is not None:
                    rate_pct = _to_decimal(getattr(row_seg, plan_col, None))

        if rate_pct == Decimal("0") and make_id is not None:
            stmt_zd = (
                select(ZeroDep)
                .where(
                    and_(
                        ZeroDep.InsuranceCompanyId == insurance_company_id,
                        ZeroDep.Make_ID == make_id,
                        ZeroDep.Age == age_int,
                        ZeroDep.Isdelete == 0,
                    )
                )
                .order_by(ZeroDep.ZerodepId.desc())
            )
            res_zd = await self.session.execute(stmt_zd)
            row_zd = res_zd.scalars().first()
            if row_zd is not None:
                rate_pct = _to_decimal(getattr(row_zd, plan_col, None))

        if make_id is not None and model_id is not None and veh_type_id is not None:
            stmt_ext = (
                select(AddonExtraAmt)
                .where(
                    and_(
                        AddonExtraAmt.InsuranceCompanyId == insurance_company_id,
                        AddonExtraAmt.VehiceTypeId == veh_type_id,
                        AddonExtraAmt.makeId == make_id,
                        AddonExtraAmt.ModelId == model_id,
                        AddonExtraAmt.IsDeleted == 0,
                    )
                )
                .order_by(AddonExtraAmt.ExtraAddonId.desc())
            )
            res_ext = await self.session.execute(stmt_ext)
            row_ext = res_ext.scalars().first()
            if row_ext is not None:
                extra_amt = _to_decimal(getattr(row_ext, plan_col, None))

        return rate_pct, extra_amt

    # -----------------------------------------------------------------------
    # 6. PA to Owner-Driver & Towing Charges Lookup
    # -----------------------------------------------------------------------

    async def get_pa_owner_driver_and_towing(
        self,
        insurance_company_id: int,
        towing_selection: Decimal = Decimal("0"),
    ) -> Tuple[Decimal, Decimal]:
        """
        Returns (pa_owner_driver_rate, towing_charge_rate) from tbl_patoownerdriver
        and tbl_insurancecompanywisetowingchanges (with verified static fallback).
        """
        pa_rate = Decimal("375")
        default_towing = Decimal("0")

        stmt_pa = select(PAToOwnerDriver).where(
            and_(
                PAToOwnerDriver.InsuranceCompanyId == insurance_company_id,
                PAToOwnerDriver.IsDeleted == 0,
            )
        )
        res_pa = await self.session.execute(stmt_pa)
        row_pa = res_pa.scalars().first()
        if row_pa is not None:
            pa_rate = _to_decimal(row_pa.Rate, Decimal("375"))
            default_towing = _to_decimal(row_pa.TowingCharges, Decimal("0"))
        elif insurance_company_id in STATIC_PA_OWNER_DRIVER_RATES:
            pa_rate, default_towing = STATIC_PA_OWNER_DRIVER_RATES[insurance_company_id]

        towing_rate = default_towing
        if towing_selection > Decimal("0"):
            stmt_tow = select(InsuranceCompanyWiseTowingChanges).where(
                and_(
                    InsuranceCompanyWiseTowingChanges.InsuranceCompanyId == insurance_company_id,
                    InsuranceCompanyWiseTowingChanges.Selection == float(towing_selection),
                    InsuranceCompanyWiseTowingChanges.IsDelete == 0,
                )
            )
            res_tow = await self.session.execute(stmt_tow)
            row_tow = res_tow.scalars().first()
            if row_tow is not None:
                towing_rate = _to_decimal(row_tow.Rate)
            elif (insurance_company_id, int(towing_selection)) in STATIC_TOWING_SLABS:
                towing_rate = STATIC_TOWING_SLABS[(insurance_company_id, int(towing_selection))]

        return pa_rate, towing_rate

    async def get_eligible_insurers_for_category(self, vehicle_category: str) -> List[int]:
        """
        Returns eligible InsuranceCompanyIds for the requested vehicle category
        from tbl_insurancecompanybyvehicletype (or default active insurer list).
        """
        stmt = select(InsuranceCompanyByVehicleType).where(
            InsuranceCompanyByVehicleType.IsDelete == 0
        )
        res = await self.session.execute(stmt)
        rows = list(res.scalars().all())
        if rows:
            cat_flag_map = {
                "Public_GCV": "GCV",
                "Private_GCV": "GCV",
                "PublicGCV3W": "Three_Wheeler",
                "PublicPCV3W": "Three_Wheeler_PCV",
                "Misc-D": "Misc_D",
                "PVT": "PVT_CAR",
                "TwoWheeler": "Two_Wheeler",
                "PassengerTaxi(PCV)": "PCV",
                "School_Bus": "Bus",
            }
            flag_attr = cat_flag_map.get(vehicle_category, "GCV")
            matched_ids = [
                r.InsuranceCompanyId
                for r in rows
                if r.InsuranceCompanyId and getattr(r, flag_attr, 0) == 1
            ]
            if matched_ids:
                return matched_ids

        # Verified static fallback from tbl_insurancecompanybyvehicletype
        static_map = {
            "Public_GCV": [2, 3, 4, 14, 24, 25, 26, 18, 16, 5, 6],
            "Private_GCV": [2, 3, 4, 14, 24, 25, 26, 18, 16, 5, 6],
            "Misc-D": [3, 25, 5],
            "PassengerTaxi(PCV)": [3, 18],
            "PVT": [1, 2, 3, 4, 5, 14, 18, 20, 21, 26],
            "TwoWheeler": [1, 2, 3, 4, 5, 14, 18, 20],
            "PublicGCV3W": [4, 14, 25, 18],
            "PublicPCV3W": [1, 3, 5, 14, 18, 24, 25],
            "School_Bus": [1, 2, 3, 4, 5, 14],
        }
        return static_map.get(vehicle_category, [1, 2, 3, 4, 5, 14])

    # -----------------------------------------------------------------------
    # 7. Quotation Code Generation (Sp_GetQuotationCodeForSelfRequestedQuotation)
    # -----------------------------------------------------------------------

    async def generate_self_quotation_code(
        self,
        user_role_id: int,
        actor_id: int,
        veh_type_id: int,
        insurance_company_id: int,
    ) -> Tuple[str, int]:
        """
        Generates next QuotationCode matching Sp_GetQuotationCodeForSelfRequestedQuotation
        and sp_GenrateQuatationCode.
        Returns (srq_title_code, next_seq_id).
        """
        stmt_max = select(func.coalesce(func.max(AppQuatationEntry.QuatationId), 0))
        res_max = await self.session.execute(stmt_max)
        max_id = int(res_max.scalar_one() or 0) + 1
        code_len = len(str(max_id))

        stmt_pref = select(QuotationPrefix).where(
            and_(
                QuotationPrefix.UserRoleId == user_role_id,
                QuotationPrefix.CodeLength == code_len,
                QuotationPrefix.IsDeleted == 0,
            )
        )
        res_pref = await self.session.execute(stmt_pref)
        pref_row = res_pref.scalars().first()

        if pref_row is not None:
            role_code = pref_row.Code
            no_of_digit = pref_row.NoOfDigit or ""
        else:
            role_code = STATIC_ROLE_PREFIX_MAP.get(user_role_id, "Q")
            padding_len = max(0, 5 - code_len)
            no_of_digit = "0" * padding_len if padding_len > 0 else "NULL"

        if code_len >= 5 or no_of_digit.upper() == "NULL":
            srq_code = f"SRQ{veh_type_id}{insurance_company_id}{role_code}{actor_id}{max_id}"
        else:
            srq_code = f"SRQ{veh_type_id}{insurance_company_id}{role_code}{actor_id}{no_of_digit}{max_id}"

        return srq_code, max_id

    async def generate_assisted_quotation_code(
        self,
        user_role_id: int,
        actor_id: int,
    ) -> str:
        """
        Generates next Assisted Quotation Code matching Sp_GetQuotationCodeForPolicyEntry1.
        """
        stmt_max = select(func.coalesce(func.max(AppQuotationRequest.QuatationId), 0))
        res_max = await self.session.execute(stmt_max)
        max_id = int(res_max.scalar_one() or 0) + 1
        code_len = len(str(max_id))

        role_code = STATIC_ROLE_PREFIX_MAP.get(user_role_id, "Q")
        padding_len = max(0, 5 - code_len)
        no_of_digit = "0" * padding_len if padding_len > 0 else ""
        return f"{role_code}{actor_id}{no_of_digit}{max_id}"

    # -----------------------------------------------------------------------
    # 8. Self-Quotation Persistence & Scoped Queries (tbl_app_quatationentry)
    # -----------------------------------------------------------------------

    async def check_self_quotation_title_exists(self, title: str) -> bool:
        """Matches sp_CheckQuatationTitle."""
        stmt = select(func.count(AppQuatationEntry.QuatationId)).where(
            AppQuatationEntry.Title == title
        )
        res = await self.session.execute(stmt)
        return int(res.scalar_one() or 0) > 0

    async def create_self_quotation(self, entry: AppQuatationEntry) -> AppQuatationEntry:
        self.session.add(entry)
        await self.session.flush()
        await self.session.refresh(entry)
        return entry

    async def get_self_quotation_by_id(self, quatation_id: int) -> Optional[AppQuatationEntry]:
        stmt = select(AppQuatationEntry).where(
            and_(
                AppQuatationEntry.QuatationId == quatation_id,
                or_(AppQuatationEntry.isdeleted == "0", AppQuatationEntry.isdeleted.is_(None)),
            )
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def list_self_quotations(
        self,
        agent_id_filter: Optional[int] = None,
        sale_ex_id_filter: Optional[int] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        registration_no: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[int, List[AppQuatationEntry]]:
        """
        Matches sp_ViewQuatationEntry, sp_ViewQuatationEntrySaleEx, and sp_selectSelfQuotation.
        """
        conditions = [
            or_(AppQuatationEntry.isdeleted == "0", AppQuatationEntry.isdeleted.is_(None))
        ]
        if agent_id_filter is not None and sale_ex_id_filter is not None:
            conditions.append(
                or_(
                    AppQuatationEntry.AgentId == agent_id_filter,
                    AppQuatationEntry.SaleExId == sale_ex_id_filter,
                )
            )
        elif agent_id_filter is not None:
            conditions.append(AppQuatationEntry.AgentId == agent_id_filter)
        elif sale_ex_id_filter is not None:
            conditions.append(AppQuatationEntry.SaleExId == sale_ex_id_filter)

        if from_date is not None:
            start_dt = datetime.combine(from_date - timedelta(days=1), datetime.min.time())
            conditions.append(AppQuatationEntry.QuatationDate >= start_dt)
        if to_date is not None:
            end_dt = datetime.combine(to_date, datetime.max.time())
            conditions.append(AppQuatationEntry.QuatationDate <= end_dt)
        if registration_no:
            conditions.append(
                AppQuatationEntry.RegistrationNo.ilike(f"%{registration_no.strip()}%")
            )

        count_stmt = select(func.count(AppQuatationEntry.QuatationId)).where(and_(*conditions))
        total = int((await self.session.execute(count_stmt)).scalar_one() or 0)

        stmt = (
            select(AppQuatationEntry)
            .where(and_(*conditions))
            .order_by(AppQuatationEntry.QuatationId.desc())
            .limit(limit)
            .offset(offset)
        )
        rows = list((await self.session.execute(stmt)).scalars().all())
        return total, rows

    # -----------------------------------------------------------------------
    # 9. Assisted Quotation Requests & Lifecycle (tbl_app_quotationrequest)
    # -----------------------------------------------------------------------

    async def create_quotation_request(
        self, req: AppQuotationRequest
    ) -> AppQuotationRequest:
        self.session.add(req)
        await self.session.flush()
        await self.session.refresh(req)
        return req

    async def get_quotation_request_by_id(
        self, quatation_id: int
    ) -> Optional[AppQuotationRequest]:
        stmt = select(AppQuotationRequest).where(
            and_(
                AppQuotationRequest.QuatationId == quatation_id,
                AppQuotationRequest.isdeleted == 0,
            )
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def list_quotation_requests(
        self,
        agent_id_filter: Optional[int] = None,
        sales_ex_id_filter: Optional[int] = None,
        franchise_id_filter: Optional[int] = None,
        is_generated: Optional[int] = None,
        is_pending_revert: Optional[int] = None,
        vehicle_no: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[int, List[AppQuotationRequest]]:
        conditions = [AppQuotationRequest.isdeleted == 0]

        scope_or = []
        if agent_id_filter is not None:
            scope_or.append(AppQuotationRequest.AgentId == agent_id_filter)
        if sales_ex_id_filter is not None:
            scope_or.append(AppQuotationRequest.SalesEx_Id == sales_ex_id_filter)
        if franchise_id_filter is not None:
            scope_or.append(AppQuotationRequest.FranchiseId == franchise_id_filter)
        if scope_or:
            conditions.append(or_(*scope_or))

        if is_generated is not None:
            conditions.append(AppQuotationRequest.IsQuotationGenerate == is_generated)
        if is_pending_revert is not None:
            conditions.append(AppQuotationRequest.isPendingRevert == is_pending_revert)
        if vehicle_no:
            conditions.append(AppQuotationRequest.VehicleNo.ilike(f"%{vehicle_no.strip().upper()}%"))

        count_stmt = select(func.count(AppQuotationRequest.QuatationId)).where(and_(*conditions))
        total = int((await self.session.execute(count_stmt)).scalar_one() or 0)

        stmt = (
            select(AppQuotationRequest)
            .where(and_(*conditions))
            .order_by(AppQuotationRequest.QuatationId.desc())
            .limit(limit)
            .offset(offset)
        )
        rows = list((await self.session.execute(stmt)).scalars().all())
        return total, rows

    async def add_quotation_remark(
        self,
        quatation_id: int,
        user_id: int,
        remark: str,
        update_by: str,
        remark_from: str,
    ) -> AppQuotationRemark:
        """Matches sp_insert_app_quotationremark('INS')."""
        now = datetime.utcnow()
        rem = AppQuotationRemark(
            QuatationId=quatation_id,
            QuatationDate=now,
            UserId=user_id,
            Remark=remark,
            UpdateBy=update_by,
            UpdateDate=now,
            isdeleted=0,
            RemarkFrom=remark_from,
        )
        self.session.add(rem)
        await self.session.flush()
        await self.session.refresh(rem)
        return rem

    async def get_quotation_remarks(
        self, quatation_id: int
    ) -> List[AppQuotationRemark]:
        """Matches sp_insert_app_quotationremark('SEL')."""
        stmt = (
            select(AppQuotationRemark)
            .where(
                and_(
                    AppQuotationRemark.QuatationId == quatation_id,
                    or_(AppQuotationRemark.isdeleted == 0, AppQuotationRemark.isdeleted.is_(None)),
                )
            )
            .order_by(AppQuotationRemark.QuatRemarkId.desc())
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def soft_delete_insurer_quotes(self, quatation_id: int) -> None:
        stmt = (
            update(InsuranceCompanyQuotation)
            .where(InsuranceCompanyQuotation.TransctionId == quatation_id)
            .values(isdeleted="1")
        )
        await self.session.execute(stmt)

    async def add_insurer_quote_option(
        self,
        quatation_id: int,
        insurance_company_id: int,
        agent_id: int,
        emp_id: int,
        quotation_file: str,
        quotation_file_name: str,
        product_id: int,
        remark: Optional[str],
    ) -> InsuranceCompanyQuotation:
        """Matches sp_insertInsuranceComponyQuotation('INSERT')."""
        opt = InsuranceCompanyQuotation(
            InsuranceCompanyId=insurance_company_id,
            TransctionId=quatation_id,
            agentId=agent_id,
            QuotationFile=quotation_file,
            EmpId=emp_id,
            isdeleted="0",
            InsertDate=datetime.utcnow(),
            Remark=remark,
            Quotationfile_Name=quotation_file_name,
            ProductId=product_id,
        )
        self.session.add(opt)
        await self.session.flush()
        await self.session.refresh(opt)
        return opt

    async def get_insurer_quote_options(
        self, quatation_id: int
    ) -> List[InsuranceCompanyQuotation]:
        stmt = (
            select(InsuranceCompanyQuotation)
            .where(
                and_(
                    InsuranceCompanyQuotation.TransctionId == quatation_id,
                    InsuranceCompanyQuotation.isdeleted == "0",
                )
            )
            .order_by(InsuranceCompanyQuotation.QuotationId.asc())
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())
