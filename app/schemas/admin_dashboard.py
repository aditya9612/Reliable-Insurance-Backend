"""
Pydantic Schemas for Phase 16B — Admin Dashboard Overview Counters.
"""
from pydantic import BaseModel


class AdminCountersResponse(BaseModel):
    total_users: int
    active_users: int
    locked_users: int
    pending_kyc_agents: int
    total_agents: int
    total_employees: int
    total_franchises: int
