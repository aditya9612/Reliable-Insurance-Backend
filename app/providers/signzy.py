"""
Signzy Vehicle RC & Detailed Search Integration Provider Adapter.
"""
from typing import Optional
from datetime import datetime
import httpx
from app.core.config import settings
from app.providers.base import VehicleRCProvider
from app.schemas.integrations import VehicleRCData


class SignzyRCProvider(VehicleRCProvider):
    """Production/UAT HTTP Adapter for Signzy v3 Vehicle Detailed Search API."""

    def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None):
        self.base_url = base_url or settings.SIGNZY_BASE_URL
        self.api_key = api_key or settings.SIGNZY_API_KEY

    async def lookup_rc(self, registration_number: str) -> Optional[VehicleRCData]:
        clean_reg = registration_number.strip().upper().replace(" ", "").replace("-", "")
        payload = {
            "vehicleNumber": clean_reg,
            "blacklistCheck": "true",
            "splitAddress": True,
        }
        headers = {
            "Authorization": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(self.base_url, json=payload, headers=headers)
            if response.status_code == 404:
                return None
            response.raise_for_status()
            data = response.json()

        result = data.get("result", data) if isinstance(data, dict) else {}
        if not result or not isinstance(result, dict):
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
            request_id=str(data.get("requestId", "")),
            license_plate_RegNo=clean_reg,
            owner_name=result.get("ownerName") or result.get("owner_name"),
            father_name=result.get("fatherName") or result.get("father_name"),
            is_financed="YES" if (result.get("financingAuthority") or result.get("is_financed") == "YES") else "NO",
            financer=result.get("financingAuthority") or result.get("financer"),
            present_address=result.get("presentAddress") or result.get("present_address"),
            permanent_address=result.get("permanentAddress") or result.get("permanent_address"),
            insurance_company=result.get("insuranceCompany") or result.get("vehicleInsuranceCompanyName"),
            insurance_policy=result.get("insurancePolicyNumber") or result.get("insurance_policy"),
            insurance_expiry=parse_dt(result.get("insuranceExpiryDate") or result.get("vehicleInsuranceUpto")),
            rc_class=result.get("vehicleClass") or result.get("vehicleClassDesc"),
            category=result.get("category") or result.get("vehicleCategory"),
            registration_date=parse_dt(result.get("registrationDate") or result.get("regDate")),
            vehicle_age=result.get("vehicleAge"),
            pucc_upto=parse_dt(result.get("puccUpto")),
            pucc_number=result.get("puccNumber"),
            chassis_number=result.get("chassisNumber") or result.get("chassis"),
            engine_number=result.get("engineNumber") or result.get("engine"),
            fuel_type=result.get("fuelType") or result.get("type"),
            brand_name=result.get("makerDescription") or result.get("brand_name"),
            brand_model=result.get("makerModel") or result.get("brand_model"),
            body_type=result.get("bodyTypeDescription"),
            cubic_capacity=str(result.get("cubicCapacity") or ""),
            gross_weight=str(result.get("grossVehicleWeight") or ""),
            cylinders=str(result.get("numberOfCylinders") or ""),
            color=result.get("color"),
            norms=result.get("normsDescription"),
            fit_up_to=result.get("fitnessUpto"),
            manufacturing_date=result.get("manufacturingDate"),
            manufacturing_date_formatted=result.get("manufacturingDateFormatted"),
            rto_name=result.get("registeredAt"),
            latest_by=result.get("statusAsOn"),
            sleeper_capacity=str(result.get("sleeperCapacity") or "0"),
            standing_capacity=str(result.get("standingCapacity") or "0"),
            wheelbase=str(result.get("wheelbase") or ""),
            unladen_weight=str(result.get("unladenWeight") or ""),
            noc_details=result.get("nocDetails"),
            seating_capacity=str(result.get("seatingCapacity") or ""),
            owner_count=str(result.get("ownerCount") or "1"),
            tax_upto=result.get("taxUpto"),
            tax_paid_upto=result.get("taxPaidUpto"),
            permit_number=result.get("permitNumber"),
            permit_issue_date=result.get("permitIssueDate"),
            permit_valid_from=result.get("permitValidFrom"),
            permit_valid_upto=result.get("permitValidUpto"),
            permit_type=result.get("permitType"),
            national_permit_number=result.get("nationalPermitNumber"),
            national_permit_upto=result.get("nationalPermitUpto"),
            national_permit_issued_by=result.get("nationalPermitIssuedBy"),
            rc_status=result.get("status", "ACTIVE"),
            CreatedDate=datetime.utcnow(),
            CreatedBy="SIGNZY_PROVIDER",
        )
