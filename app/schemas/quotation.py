"""
Pydantic v2 Request & Response Schemas for Phase 6 Quotation & Rating Engine.
All monetary, rate, IDV, discount, and tax fields strictly use Decimal (never float).
"""
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


ALLOWED_NCB_SLABS = {
    Decimal("0"),
    Decimal("20"),
    Decimal("25"),
    Decimal("35"),
    Decimal("45"),
    Decimal("50"),
}

CANONICAL_VEHICLE_CATEGORIES = {
    "PVT": "PVT",
    "PRIVATE CAR": "PVT",
    "TWOWHEELER": "TwoWheeler",
    "TWO WHEELER": "TwoWheeler",
    "2W": "TwoWheeler",
    "PUBLIC_GCV": "Public_GCV",
    "PUBLIC GCV": "Public_GCV",
    "GCV": "Public_GCV",
    "PRIVATE_GCV": "Private_GCV",
    "PRIVATE GCV": "Private_GCV",
    "PUBLICGCV3W": "PublicGCV3W",
    "3W GCV": "PublicGCV3W",
    "PUBLICPCV3W": "PublicPCV3W",
    "3W PCV": "PublicPCV3W",
    "MISC-D": "Misc-D",
    "MISC_D": "Misc-D",
    "MISCD": "Misc-D",
    "PASSENGERTAXI(PCV)": "PassengerTaxi(PCV)",
    "PASSENGERTAXI": "PassengerTaxi(PCV)",
    "PCV": "PassengerTaxi(PCV)",
    "TAXI": "PassengerTaxi(PCV)",
    "SCHOOL_BUS": "School_Bus",
    "SCHOOL BUS": "School_Bus",
    "STAFF BUS": "School_Bus",
    "OTHER BUS": "School_Bus",
    "BUS": "School_Bus",
}


class PremiumCalculationRequest(BaseModel):
    """
    Input payload for deterministic motor insurance premium calculation
    (POST /api/v1/quotations/calculate and POST /api/v1/quotations/compare).
    """
    model_config = ConfigDict(extra="forbid")

    vehicle_category: str = Field(
        ...,
        description="Canonical vehicle category: PVT, TwoWheeler, Public_GCV, Private_GCV, PublicGCV3W, PublicPCV3W, Misc-D, PassengerTaxi(PCV), School_Bus",
    )
    product_type_id: int = Field(
        default=1,
        ge=1,
        le=3,
        description="1=Comprehensive/Package, 2=Liability Only (STP), 3=Standalone OD (SAOD)",
    )
    business_type_id: int = Field(
        default=3,
        ge=1,
        le=8,
        description="1=New, 2=Renewal, 3=Roll Over",
    )
    insurance_company_id: int = Field(
        default=1,
        ge=1,
        description="Underwriting InsuranceCompanyId from tbl_insurancecompany",
    )
    veh_type_id: Optional[int] = Field(default=None, ge=1)
    veh_sub_type_id: Optional[int] = Field(default=None, ge=0)
    make_id: Optional[int] = Field(default=None, ge=1)
    model_id: Optional[int] = Field(default=None, ge=1)
    variant_id: Optional[int] = Field(default=None, ge=1)
    fuel_type_id: int = Field(default=1, ge=1)
    rto_id: Optional[int] = Field(default=None, ge=1)
    cluster_id: int = Field(default=1, ge=0)
    zone: str = Field(default="A", description="Tariff Zone: A, B, or C")

    # Registration & Manufacturing Dates for Age Calculation (sp_SelectMgfyearOfyearmonth)
    registration_date: Optional[date] = Field(default=None)
    calculation_date: Optional[date] = Field(default=None)
    vehicle_age_override: Optional[Decimal] = Field(default=None, ge=Decimal("0"))

    # Capacity / Weight / Seating
    cubic_capacity: int = Field(default=1200, ge=0, description="Engine CC or GVW depending on category")
    gross_vehicle_weight: int = Field(default=0, ge=0, description="GVW in kg for GCV / Bus")
    seating_capacity: int = Field(default=5, ge=0, description="Passenger / seating capacity")
    bus_type: Optional[str] = Field(default="SCHOOL BUS", description="SCHOOL BUS, STAFF BUS, or OTHER BUS")

    # IDV & Sum Insured Inputs
    with_body: bool = Field(default=True, description="For GCV: True='Yes' (Model price), False='No' (Body+Chassis)")
    base_idv_override: Optional[Decimal] = Field(default=None, ge=Decimal("0"))
    selected_idv: Optional[Decimal] = Field(default=None, ge=Decimal("0"))
    validate_idv_band: bool = Field(
        default=True,
        description="Enforce legacy +/-15% IDV band around base variant IDV",
    )
    electrical_accessories: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    non_electrical_accessories: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    lpg_cng_kit_value: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    inbuilt_lpg_cng: bool = Field(default=False)
    trailer_idv: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    no_of_trailers: int = Field(default=0, ge=0)

    # OD Loadings & Discounts
    imt23: bool = Field(default=False, description="IMT-23 15% OD loading for GCV/Commercial/Misc-D")
    fiber_glass_tank: bool = Field(default=False)
    geographical_extension: bool = Field(default=False)
    own_premises: bool = Field(default=False, description="33% Own Premises OD discount")
    anti_theft: bool = Field(default=False, description="2.5% Anti-Theft OD discount (max Rs 500)")
    automobile_association_discount: bool = Field(default=False)
    voluntary_deductible_slab: int = Field(default=0, ge=0)

    # Previous Policy & NCB
    prev_policy_available: bool = Field(default=True)
    claim_in_previous_policy: bool = Field(default=False)
    ncb_percent: Decimal = Field(default=Decimal("0"))
    od_discount_override: Optional[Decimal] = Field(default=None, ge=Decimal("0"), le=Decimal("100"))

    # Add-On Covers
    zero_dep: bool = Field(default=False, description="Zero Depreciation / Nil-Dep cover")
    addon_plan: str = Field(
        default="NillDep",
        description="NillDep, SecurePlus, or SPremium column selector for Zero-Dep tables",
    )
    zero_dep_rate_override: Optional[Decimal] = Field(default=None, ge=Decimal("0"))
    towing_selection: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    towing_override: Optional[Decimal] = Field(default=None, ge=Decimal("0"))

    # Third-Party Liability Add-Ons
    pa_to_owner_driver: bool = Field(default=True)
    pa_owner_driver_override: Optional[Decimal] = Field(default=None, ge=Decimal("0"))
    lpg_cng_tp_liability: bool = Field(default=False)
    ll_paid_driver_count: int = Field(default=0, ge=0)
    ll_cleaner_count: int = Field(default=0, ge=0)
    ll_coolie_count: int = Field(default=0, ge=0)
    ll_employee_count: int = Field(default=0, ge=0)
    nfpp_count: int = Field(default=0, ge=0, description="Non-Fare Paying Passengers count (Rs 75 each)")
    pa_paid_driver_amount: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    pa_unnamed_passenger_amount: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    pa_pillion_rider_amount: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    tppd_restriction: bool = Field(default=False, description="TPPD restricted to Rs 6000 (-Rs 200/150/50)")

    # GCV GST mode: split (18% OD/Add-on + 12% or 5% Basic TP) or uniform 18%
    gcv_split_tp_gst: bool = Field(
        default=True,
        description="Apply legacy GCV split GST on Basic TP (12% before 2025-09-23 or SelfQuotation mode; 5% on/after 2025-09-23 in adm_PolicyDetails mode) and 18% on OD + other TP",
    )
    risk_start_date: Optional[date] = Field(
        default=None,
        description="Policy risk start date; when provided, applies adm_PolicyDetails.aspx.cs:L636-644 GCV Basic TP GST cutover (5% on/after 2025-09-23, 12% before 2025-09-23)",
    )
    apply_gcv_2025_09_23_tp_gst_cutover: bool = Field(
        default=False,
        description="Explicitly apply adm_PolicyDetails.aspx.cs:L636-644 2025-09-23 GCV Basic TP GST cutover (5% vs 12%) using risk_start_date or calculation_date",
    )
    gcv_basic_tp_gst_rate_override: Optional[Decimal] = Field(
        default=None,
        ge=Decimal("0"),
        le=Decimal("100"),
        description="Optional explicit override for GCV Basic TP GST rate (e.g., 5 or 12)",
    )

    @field_validator("vehicle_category")
    @classmethod
    def validate_vehicle_category(cls, v: str) -> str:
        key = v.strip().upper()
        if key not in CANONICAL_VEHICLE_CATEGORIES:
            raise ValueError(
                f"Unsupported vehicle_category '{v}'. Allowed: {sorted(set(CANONICAL_VEHICLE_CATEGORIES.values()))}"
            )
        return CANONICAL_VEHICLE_CATEGORIES[key]

    @field_validator("zone")
    @classmethod
    def validate_zone(cls, v: str) -> str:
        z = v.strip().upper()
        if z not in {"A", "B", "C"}:
            raise ValueError("zone must be 'A', 'B', or 'C'")
        return z

    @field_validator("ncb_percent")
    @classmethod
    def validate_ncb_slab(cls, v: Decimal) -> Decimal:
        if v not in ALLOWED_NCB_SLABS:
            raise ValueError(f"Invalid NCB slab {v}%. Allowed slabs: 0, 20, 25, 35, 45, 50")
        return v


class MultiInsurerCompareRequest(BaseModel):
    """
    Request payload for comparing premiums across multiple eligible insurers
    (POST /api/v1/quotations/compare).
    """
    model_config = ConfigDict(extra="forbid")

    calculation_input: PremiumCalculationRequest
    insurance_company_ids: Optional[List[int]] = Field(
        default=None,
        description="Optional explicit list of InsuranceCompanyIds; if omitted, uses sp_SelectInsuranceCompanyByVehicleType",
    )


class PremiumBreakdownResponse(BaseModel):
    """
    Complete deterministic motor rating breakdown with every intermediate line item
    using Decimal exclusively.
    """
    insurance_company_id: int
    insurance_company_name: Optional[str] = None
    vehicle_category: str
    product_type_id: int
    business_type_id: int
    zone: str

    # Age & IDV Band
    vehicle_age: Decimal
    lookup_age: Decimal
    base_idv: Decimal
    min_idv: Decimal
    max_idv: Decimal
    selected_idv: Decimal
    body_price: Decimal = Decimal("0.00")
    chassis_price: Decimal = Decimal("0.00")
    total_idv: Decimal

    # Own Damage (OD) Breakdown
    od_basic_rate_percent: Decimal
    basic_od_premium: Decimal
    gvw_above_12000_loading: Decimal
    electrical_accessories_od: Decimal
    non_electrical_accessories_od: Decimal
    lpg_cng_kit_od: Decimal
    inbuilt_lpg_cng_od: Decimal
    fiber_glass_tank_od: Decimal
    geographical_extension_od: Decimal
    subtotal_od_before_imt23: Decimal
    imt23_loading_amount: Decimal
    gross_od_premium: Decimal

    # Tariff & Statutory OD Discounts
    own_premises_discount: Decimal
    anti_theft_discount: Decimal
    automobile_association_discount: Decimal
    voluntary_deductible_discount: Decimal
    od_after_tariff_discounts: Decimal

    # Company OD Discount & NCB
    od_discount_percent: Decimal
    od_discount_amount: Decimal
    od_after_company_discount: Decimal
    ncb_percent: Decimal
    ncb_amount: Decimal
    net_od_premium: Decimal

    # Add-On Covers
    zero_dep_rate_percent: Decimal
    zero_dep_extra_amount: Decimal
    zero_dep_premium: Decimal
    towing_charges_amount: Decimal
    total_od_with_addons: Decimal

    # Third-Party (TP) Liability Breakdown
    basic_tp_premium: Decimal
    passenger_ll_premium: Decimal
    lpg_cng_tp_premium: Decimal
    geographical_extension_tp: Decimal
    pa_owner_driver_premium: Decimal
    ll_paid_driver_premium: Decimal
    ll_cleaner_coolie_premium: Decimal
    ll_employee_premium: Decimal
    nfpp_premium: Decimal
    pa_paid_driver_premium: Decimal
    pa_unnamed_passenger_premium: Decimal
    pa_pillion_rider_premium: Decimal
    trailer_tp_premium: Decimal
    tppd_discount: Decimal
    total_tp_premium: Decimal

    # Net Premium, GST & Final Payable
    net_premium: Decimal
    gst_on_od_and_other_tp: Decimal
    gst_on_basic_tp: Decimal
    gcv_basic_tp_gst_rate_percent: Decimal = Decimal("0.00")
    total_gst_amount: Decimal
    final_payable_premium: Decimal

    # Underwriting Flags
    is_declined: bool = False


class MultiInsurerCompareResponse(BaseModel):
    """Response containing side-by-side insurer quotation breakdowns."""
    vehicle_category: str
    product_type_id: int
    comparisons: List[PremiumBreakdownResponse]


class SelfQuotationCreateRequest(BaseModel):
    """
    Request payload for creating and persisting a Self-Quotation record
    in tbl_app_quatationentry (POST /api/v1/quotations/self).
    """
    model_config = ConfigDict(extra="forbid")

    title: Optional[str] = Field(default=None, max_length=200)
    product_name: str = Field(default="Package Policy", max_length=255)
    product_type: str = Field(default="COMPREHENSIVE", max_length=255)
    registration_no: str = Field(default="NEW", max_length=255)
    mgf_year: str = Field(default="2024", max_length=255)
    mfg_date: Optional[datetime] = None
    agent_id: Optional[int] = Field(default=None, ge=0)
    sale_ex_id: Optional[int] = Field(default=None, ge=0)
    calculation_input: PremiumCalculationRequest


class SelfQuotationResponse(BaseModel):
    """Persisted Self-Quotation record response from tbl_app_quatationentry."""
    quatation_id: int
    quatation_code: str
    quatation_date: Optional[datetime] = None
    title: Optional[str] = None
    product_name: Optional[str] = None
    product_type: Optional[str] = None
    registration_no: Optional[str] = None
    mgf_year: Optional[str] = None
    rto_id: Optional[int] = None
    zone: Optional[str] = None
    insurance_company_id: Optional[int] = None
    veh_type_id: Optional[int] = None
    veh_sub_type_id: Optional[int] = None
    make_id: Optional[int] = None
    model_id: Optional[int] = None
    variant_id: Optional[int] = None
    fuel_type_id: Optional[int] = None
    seats_capacity: Optional[str] = None
    cubic_capacity: Optional[str] = None
    vehicle_weight: Optional[str] = None
    idv: Decimal
    own_damage_premium: Decimal
    od_discount_amount: Decimal
    imt23_amount: Decimal
    zero_depreciation: Decimal
    no_claim_bonus: Decimal
    ncb_percent: Decimal
    total_od_premium: Decimal
    total_liability_premium: Decimal
    total_net_premium: Decimal
    gst_amount: Decimal
    final_premium: Decimal
    body_price: Decimal
    chassis_price: Decimal
    agent_id: Optional[int] = None
    sale_ex_id: Optional[int] = None
    user_role_id: Optional[int] = None
    breakdown: Optional[PremiumBreakdownResponse] = None


class SelfQuotationListResponse(BaseModel):
    """Paginated list of Self-Quotations."""
    total: int
    items: List[SelfQuotationResponse]


class AssistedQuotationRequestCreate(BaseModel):
    """
    Request payload for creating an Assisted Quotation Request in tbl_app_quotationrequest
    (POST /api/v1/quotations/requests).
    """
    model_config = ConfigDict(extra="forbid")

    insurance_company_id: str = Field(..., min_length=1, max_length=255, description="Comma-separated or single InsuranceCompanyId")
    vehicle_id: Optional[int] = Field(default=None, ge=0)
    product_type: str = Field(default="1", max_length=255)
    zerodepth: str = Field(default="No", max_length=255)
    policy_mode: str = Field(default="Online", max_length=255)
    mobile_no: str = Field(..., min_length=10, max_length=20)
    ncb: str = Field(default="0", max_length=50)
    vehicle_no: str = Field(..., min_length=4, max_length=50)
    vehicle_type: str = Field(..., min_length=1, max_length=255)
    vehicle_make: str = Field(..., min_length=1, max_length=255)
    vehicle_model: str = Field(..., min_length=1, max_length=255)
    vehicle_variance: str = Field(..., min_length=1, max_length=255)
    policytype: str = Field(default="Package", max_length=255)
    note: str = Field(default="", max_length=255)
    remark: Optional[str] = Field(default=None, max_length=500)
    quotation_file: Optional[str] = Field(default=None, max_length=1000)
    policy_image: Optional[str] = Field(default=None, max_length=1000)
    camera: str = Field(default="", max_length=1000)
    agent_id: Optional[int] = Field(default=None, ge=0)
    sales_ex_id: Optional[int] = Field(default=None, ge=0)
    location_head_id: int = Field(default=0, ge=0)
    franchise_id: int = Field(default=0, ge=0)
    other_agent_name: Optional[str] = Field(default=None, max_length=255)

    @field_validator("ncb")
    @classmethod
    def validate_ncb_str(cls, v: str) -> str:
        cleaned = v.strip().replace("%", "")
        try:
            dec = Decimal(cleaned)
        except Exception as exc:
            raise ValueError(f"Invalid NCB value '{v}'") from exc
        if dec not in ALLOWED_NCB_SLABS:
            raise ValueError(f"NCB must be one of {sorted(ALLOWED_NCB_SLABS)}")
        return str(int(dec))


class AssistedQuotationRequestUpdate(BaseModel):
    """
    Request payload for updating or resubmitting an Assisted Quotation Request
    (PUT /api/v1/quotations/requests/{quotation_id}).
    """
    model_config = ConfigDict(extra="forbid")

    insurance_company_id: Optional[str] = Field(default=None, max_length=255)
    vehicle_id: Optional[int] = Field(default=None, ge=0)
    product_type: Optional[str] = Field(default=None, max_length=255)
    zerodepth: Optional[str] = Field(default=None, max_length=255)
    policy_mode: Optional[str] = Field(default=None, max_length=255)
    mobile_no: Optional[str] = Field(default=None, min_length=10, max_length=20)
    ncb: Optional[str] = Field(default=None, max_length=50)
    vehicle_no: Optional[str] = Field(default=None, min_length=4, max_length=50)
    vehicle_type: Optional[str] = Field(default=None, max_length=255)
    vehicle_make: Optional[str] = Field(default=None, max_length=255)
    vehicle_model: Optional[str] = Field(default=None, max_length=255)
    vehicle_variance: Optional[str] = Field(default=None, max_length=255)
    policytype: Optional[str] = Field(default=None, max_length=255)
    note: Optional[str] = Field(default=None, max_length=255)
    remark: Optional[str] = Field(default=None, max_length=500)
    policy_image: Optional[str] = Field(default=None, max_length=1000)


class QuotationAttendRequest(BaseModel):
    """Payload for coordinator claiming/releasing an Assisted Quotation Request."""
    model_config = ConfigDict(extra="forbid")

    attend: bool = Field(default=True, description="True to claim/attend, False to release")


class QuotationStatusTransitionRequest(BaseModel):
    """
    Payload for transitioning an Assisted Quotation Request status
    (Revert / Reopen / Generate / Cancel).
    """
    model_config = ConfigDict(extra="forbid")

    action: str = Field(
        ...,
        description="Transition action: 'revert', 'resubmit', 'mark_read', 'cancel'",
    )
    remark: str = Field(..., min_length=1, max_length=500)

    @field_validator("action")
    @classmethod
    def validate_action(cls, v: str) -> str:
        act = v.strip().lower()
        if act not in {"revert", "resubmit", "mark_read", "cancel"}:
            raise ValueError("action must be one of: 'revert', 'resubmit', 'mark_read', 'cancel'")
        return act


class InsurerQuoteOptionCreate(BaseModel):
    """Single insurer quotation option uploaded/generated by Coordinator."""
    model_config = ConfigDict(extra="forbid")

    insurance_company_id: int = Field(..., ge=1)
    quotation_file: str = Field(..., min_length=1, max_length=255)
    quotation_file_name: str = Field(default="Company Quotation File", max_length=255)
    product_id: int = Field(default=1, ge=1, le=3)
    remark: Optional[str] = Field(default=None, max_length=255)


class GenerateInsurerQuotesRequest(BaseModel):
    """Payload for attaching insurer quotation options and marking request Generated."""
    model_config = ConfigDict(extra="forbid")

    options: List[InsurerQuoteOptionCreate] = Field(..., min_length=1)
    replace_existing: bool = Field(default=True)
    coordinator_remark: Optional[str] = Field(default=None, max_length=500)


class InsurerQuoteOptionResponse(BaseModel):
    """Response model for a row in tbl_insurancecompanyquotation."""
    quotation_id: int
    transction_id: int
    insurance_company_id: int
    agent_id: int
    emp_id: int
    quotation_file: str
    quotation_file_name: Optional[str] = None
    product_id: int
    remark: Optional[str] = None
    insert_date: Optional[datetime] = None


class QuotationRemarkResponse(BaseModel):
    """Response model for a row in tbl_app_quotationremark."""
    quat_remark_id: int
    quatation_id: int
    quatation_date: Optional[datetime] = None
    user_id: Optional[int] = None
    remark: Optional[str] = None
    update_by: Optional[str] = None
    update_date: Optional[datetime] = None
    remark_from: Optional[str] = None


class AssistedQuotationRequestResponse(BaseModel):
    """Detailed response for an Assisted Quotation Request (tbl_app_quotationrequest)."""
    quatation_id: int
    quatation_code: Optional[str] = None
    quatation_date: Optional[datetime] = None
    insurance_company_id: Optional[str] = None
    vehicle_id: Optional[int] = None
    agent_id: Optional[int] = None
    sales_ex_id: Optional[int] = None
    user_role_id: Optional[int] = None
    other_agent_name: Optional[str] = None
    location_head_id: int
    franchise_id: int
    product_type: Optional[str] = None
    zerodepth: Optional[str] = None
    policy_mode: Optional[str] = None
    mobile_no: Optional[str] = None
    ncb: Optional[str] = None
    vehicle_no: Optional[str] = None
    vehicle_type: Optional[str] = None
    vehicle_make: Optional[str] = None
    vehicle_model: Optional[str] = None
    vehicle_variance: Optional[str] = None
    policytype: Optional[str] = None
    note: str
    remark: Optional[str] = None
    is_quotation_generate: int
    is_pending_revert: int
    read_status: int
    attended_by: Optional[str] = None
    attended_user_id: Optional[int] = None
    attended_date: Optional[datetime] = None
    quot_send_date: Optional[datetime] = None
    cancel_remark: Optional[str] = None
    cancel_date: Optional[datetime] = None
    cancel_by: Optional[str] = None
    insurer_quotes: List[InsurerQuoteOptionResponse] = Field(default_factory=list)
    remarks_history: List[QuotationRemarkResponse] = Field(default_factory=list)


class AssistedQuotationListResponse(BaseModel):
    """Paginated list of Assisted Quotation Requests."""
    total: int
    items: List[AssistedQuotationRequestResponse]


class PolicyPrefillResponse(BaseModel):
    """
    Phase 7 Policy Proposal Conversion Prefill Payload
    (Sp_GetQuotationDetailByQuotationCode / sp_getDataForPolicyEntry /SELFQUO parity).
    """
    source_type: str = Field(description="'SELF_QUOTATION' or 'ASSISTED_REQUEST'")
    quotation_id: int
    quotation_code: str
    insurance_company_id: int
    product_type: Optional[str] = None
    registration_no: Optional[str] = None
    veh_type_id: Optional[int] = None
    veh_sub_type_id: Optional[int] = None
    make_id: Optional[int] = None
    model_id: Optional[int] = None
    variant_id: Optional[int] = None
    fuel_type_id: Optional[int] = None
    rto_id: Optional[int] = None
    idv_amount: Decimal = Decimal("0.00")
    od_discount_percent: Decimal = Decimal("0.00")
    ncb_percent: Decimal = Decimal("0.00")
    od_premium: Decimal = Decimal("0.00")
    tp_premium: Decimal = Decimal("0.00")
    net_premium: Decimal = Decimal("0.00")
    gst_amount: Decimal = Decimal("0.00")
    final_premium: Decimal = Decimal("0.00")
    agent_id: Optional[int] = None
    sales_ex_id: Optional[int] = None
    user_role_id: Optional[int] = None
    quotation_file: Optional[str] = None
