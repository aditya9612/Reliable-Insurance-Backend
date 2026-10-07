"""
APIClub Vehicle RC & KYC Integration Provider Adapter.
"""
from typing import Optional
from datetime import datetime
import httpx
from app.core.config import settings
from app.providers.base import VehicleRCProvider
from app.schemas.integrations import VehicleRCData


class APIClubRCProvider(VehicleRCProvider):
    """Production/UAT HTTP Adapter for APIClub v1 RC Info API."""

    def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None):
        self.base_url = base_url or settings.RC_BASE_URL
        self.api_key = api_key or settings.RC_API_KEY

    async def lookup_rc(self, registration_number: str) -> Optional[VehicleRCData]:
        clean_reg = registration_number.strip().upper().replace(" ", "").replace("-", "")
        payload = {"vehicleId": clean_reg}
        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Referer": "docs.apiclub.in",
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(self.base_url, json=payload, headers=headers)
            if response.status_code == 404:
                return None
            response.raise_for_status()
            data = response.json()

        # Extract nested vehicle info if present
        veh_data = data.get("response", data) if isinstance(data, dict) else {}
        if not veh_data or not isinstance(veh_data, dict):
            return None

        def parse_dt(val: Optional[str]) -> Optional[datetime]:
            if not val:
                return None
            for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
                try:
                    return datetime.strptime(val.strip(), fmt)
                except ValueError:
                    continue
            return None

        return VehicleRCData(
            request_id=str(veh_data.get("request_id") or data.get("request_id", "")),
            license_plate_RegNo=clean_reg,
            owner_name=veh_data.get("owner_name") or veh_data.get("owner"),
            father_name=veh_data.get("father_name") or veh_data.get("fatherName"),
            is_financed=str(veh_data.get("is_financed", "NO")),
            financer=veh_data.get("financer"),
            present_address=veh_data.get("present_address"),
            permanent_address=veh_data.get("permanent_address"),
            insurance_company=veh_data.get("insurance_company") or (veh_data.get("insurance") or {}).get("company"),
            insurance_policy=veh_data.get("insurance_policy") or (veh_data.get("insurance") or {}).get("policy"),
            insurance_expiry=parse_dt(veh_data.get("insurance_expiry") or (veh_data.get("insurance") or {}).get("expiry")),
            rc_class=veh_data.get("class") or veh_data.get("rc_class"),
            category=veh_data.get("category"),
            registration_date=parse_dt(veh_data.get("registration_date")),
            vehicle_age=veh_data.get("vehicle_age"),
            pucc_upto=parse_dt(veh_data.get("pucc_upto")),
            pucc_number=veh_data.get("pucc_number"),
            chassis_number=veh_data.get("chassis_number") or veh_data.get("chassis"),
            engine_number=veh_data.get("engine_number") or veh_data.get("engine"),
            fuel_type=veh_data.get("fuel_type") or veh_data.get("fuelType"),
            brand_name=veh_data.get("brand_name") or veh_data.get("maker"),
            brand_model=veh_data.get("brand_model") or veh_data.get("model"),
            body_type=veh_data.get("body_type"),
            cubic_capacity=str(veh_data.get("cubic_capacity") or ""),
            gross_weight=str(veh_data.get("gross_weight") or ""),
            cylinders=str(veh_data.get("cylinders") or ""),
            color=veh_data.get("color"),
            norms=veh_data.get("norms"),
            fit_up_to=veh_data.get("fit_up_to"),
            manufacturing_date=veh_data.get("manufacturing_date"),
            manufacturing_date_formatted=veh_data.get("manufacturing_date_formatted"),
            rto_name=veh_data.get("rto_name"),
            latest_by=veh_data.get("latest_by"),
            sleeper_capacity=str(veh_data.get("sleeper_capacity") or "0"),
            standing_capacity=str(veh_data.get("standing_capacity") or "0"),
            wheelbase=str(veh_data.get("wheelbase") or ""),
            unladen_weight=str(veh_data.get("unladen_weight") or ""),
            noc_details=veh_data.get("noc_details"),
            seating_capacity=str(veh_data.get("seating_capacity") or ""),
            owner_count=str(veh_data.get("owner_count") or "1"),
            tax_upto=veh_data.get("tax_upto"),
            tax_paid_upto=veh_data.get("tax_paid_upto"),
            permit_number=veh_data.get("permit_number"),
            permit_issue_date=veh_data.get("permit_issue_date"),
            permit_valid_from=veh_data.get("permit_valid_from"),
            permit_valid_upto=veh_data.get("permit_valid_upto"),
            permit_type=veh_data.get("permit_type"),
            national_permit_number=veh_data.get("national_permit_number"),
            national_permit_upto=veh_data.get("national_permit_upto"),
            national_permit_issued_by=veh_data.get("national_permit_issued_by"),
            rc_status=veh_data.get("rc_status", "ACTIVE"),
            CreatedDate=datetime.utcnow(),
            CreatedBy="APICLUB_PROVIDER",
        )
