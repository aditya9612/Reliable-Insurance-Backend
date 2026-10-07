from typing import Optional, Dict, Any, List
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field


class AutocompleteItem(BaseModel):
    id: int
    label: str
    value: str
    category: str
    sub_text: Optional[str] = None
    extra: Optional[Dict[str, Any]] = None


class AutocompleteResponse(BaseModel):
    category: str
    query: str
    total: int
    items: List[AutocompleteItem]


class VehicleDuplicateCheckRequest(BaseModel):
    registration_no: str
    financial_year: Optional[str] = None


class VehicleDuplicateCheckResponse(BaseModel):
    registration_no: str
    financial_year: Optional[str] = None
    is_duplicate: bool
    is_allowed: bool
    existing_transaction_id: Optional[int] = None
    message: str


class PendingCountersResponse(BaseModel):
    new_app_entries: int = 0
    operator_pending_entries: int = 0
    operator_pending_inward: int = 0
    new_endorsement_entries: int = 0
    new_mis_entries: int = 0
    new_agent_entries: int = 0


class DashboardChartDataResponse(BaseModel):
    chart_name: str
    total_amount: Decimal = Decimal("0.00")
    total_count: int = 0
    labels: List[str] = Field(default_factory=list)
    values: List[Decimal] = Field(default_factory=list)
    summary_string: Optional[str] = None


class ServerStatusResponse(BaseModel):
    status: str = "ACTIVE"
    is_inactive: bool = False
    message: str = "Server is active and operational"
    server_time: str
