"""
Attestr Vehicle RC & CheckX Integration Provider Adapter (Phase 18A — F-17B-089).
Legacy Reference: Insurance/VehicleNoDetails.cs & Web.config (Attestr / CheckX RC endpoint).
"""
from typing import Optional
from datetime import datetime
import httpx
from app.core.config import settings
from app.providers.base import VehicleRCProvider
from app.schemas.integrations import VehicleRCData


class AttestrRCProvider(VehicleRCProvider):
    """Production/UAT HTTP Adapter for Attestr CheckX v1 Public RC API."""

    def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None):
        self.base_url = base_url or getattr(
            settings, "ATTESTR_BASE_URL", "https://api.attestr.com/api/v1/public/checkx/rc"
        )
        self.api_key = api_key or getattr(settings, "ATTESTR_API_KEY", "mock-attestr-api-key")

    async def lookup_rc(self, registration_number: str) -> Optional[VehicleRCData]:
        clean_reg = registration_number.strip().upper().replace(" ", "").replace("-", "")
        payload = {"reg": clean_reg}
        headers = {
            "Authorization": f"Basic {self.api_key}"
            if not self.api_key.lower().startswith(("basic ", "bearer "))
            else self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(self.base_url, json=payload, headers=headers)
            if response.status_code == 404:
                return None
            response.raise_for_status()
            data = response.json()

        veh_data = data.get("data", data.get("result", data)) if isinstance(data, dict) else {}
        if not veh_data or not isinstance(veh_data, dict):
            return None

        if veh_data.get("valid") is False:
            return None

        def parse_dt(val: Optional[str]) -> Optional[datetime]:
            if not val:
                return None
            for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
                try:
                    return datetime.strptime(str(val).strip(), fmt)
                except ValueError:
                    continue
            return None

        return VehicleRCData(
            request_id=str(veh_data.get("uuid") or data.get("uuid") or data.get("request_id") or ""),
            license_plate_RegNo=clean_reg,
            owner_name=veh_data.get("owner") or veh_data.get("owner_name"),
            father_name=veh_data.get("father") or veh_data.get("father_name"),
            is_financed="YES" if (veh_data.get("financed") or veh_data.get("financier")) else "NO",
            financer=veh_data.get("financier") or veh_data.get("financer"),
            present_address=veh_data.get("currentAddress") or veh_data.get("present_address"),
            permanent_address=veh_data.get("permanentAddress") or veh_data.get("permanent_address"),
            insurance_company=veh_data.get("insurer") or veh_data.get("insurance_company"),
            insurance_policy=veh_data.get("policyNumber") or veh_data.get("insurance_policy"),
            insurance_expiry=parse_dt(veh_data.get("insuranceUpto") or veh_data.get("insurance_expiry")),
            rc_class=veh_data.get("class") or veh_data.get("rc_class"),
            category=veh_data.get("category"),
            registration_date=parse_dt(veh_data.get("registered") or veh_data.get("registration_date")),
            vehicle_age=str(veh_data.get("vehicleAge") or veh_data.get("vehicle_age") or ""),
            pucc_upto=parse_dt(veh_data.get("puccUpto") or veh_data.get("pucc_upto")),
            pucc_number=veh_data.get("puccNumber") or veh_data.get("pucc_number"),
            chassis_number=veh_data.get("chassis") or veh_data.get("chassis_number"),
            engine_number=veh_data.get("engine") or veh_data.get("engine_number"),
            fuel_type=veh_data.get("fuelType") or veh_data.get("fuel_type"),
            brand_name=veh_data.get("makerDescription") or veh_data.get("brand_name"),
            brand_model=veh_data.get("makerModel") or veh_data.get("brand_model"),
            body_type=veh_data.get("bodyType") or veh_data.get("body_type"),
            cubic_capacity=str(veh_data.get("cubicCapacity") or veh_data.get("cubic_capacity") or ""),
            gross_weight=str(veh_data.get("grossWeight") or veh_data.get("gross_weight") or ""),
            cylinders=str(veh_data.get("cylinders") or ""),
            color=veh_data.get("color"),
            norms=veh_data.get("normsType") or veh_data.get("norms"),
            fit_up_to=veh_data.get("fitnessUpto") or veh_data.get("fit_up_to"),
            manufacturing_date=veh_data.get("manufactured") or veh_data.get("manufacturing_date"),
            manufacturing_date_formatted=veh_data.get("manufactured") or veh_data.get("manufacturing_date_formatted"),
            rto_name=veh_data.get("rto") or veh_data.get("rto_name"),
            latest_by=veh_data.get("statusAsOn") or veh_data.get("latest_by"),
            sleeper_capacity=str(veh_data.get("sleeperCapacity") or "0"),
            standing_capacity=str(veh_data.get("standingCapacity") or "0"),
            wheelbase=str(veh_data.get("wheelbase") or ""),
            unladen_weight=str(veh_data.get("unladenWeight") or ""),
            noc_details=veh_data.get("nocDetails"),
            seating_capacity=str(veh_data.get("seatingCapacity") or ""),
            owner_count=str(veh_data.get("ownerCount") or "1"),
            tax_upto=veh_data.get("taxUpto"),
            tax_paid_upto=veh_data.get("taxPaidUpto"),
            permit_number=veh_data.get("permitNumber"),
            permit_issue_date=veh_data.get("permitIssueDate"),
            permit_valid_from=veh_data.get("permitValidFrom"),
            permit_valid_upto=veh_data.get("permitValidUpto"),
            permit_type=veh_data.get("permitType"),
            national_permit_number=veh_data.get("nationalPermitNumber"),
            national_permit_upto=veh_data.get("nationalPermitUpto"),
            national_permit_issued_by=veh_data.get("nationalPermitIssuedBy"),
            rc_status=veh_data.get("status", "ACTIVE"),
            CreatedDate=datetime.utcnow(),
            CreatedBy="ATTESTR_PROVIDER",
        )
