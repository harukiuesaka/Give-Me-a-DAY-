"""
Pydantic models for API request/response.

These are the API boundary types, separate from internal domain models.
"""

from typing import Optional

from pydantic import BaseModel, Field


# ---- Request schemas ----

class CreateRunRequest(BaseModel):
    goal: str = Field(min_length=10)
    success_criteria: Optional[str] = None
    risk: Optional[str] = None  # very_low | low | medium | high
    time_horizon: Optional[str] = None  # fast | one_day | one_week | one_month | quality_over_speed
    exclusions: list[str] = Field(default_factory=list)


class ApproveRequest(BaseModel):
    candidate_id: str
    user_confirmations: dict[str, bool]  # risks_reviewed, stop_conditions_reviewed, paper_run_understood
    virtual_capital: Optional[float] = None


class ReApproveRequest(BaseModel):
    candidate_id: str
    user_confirmations: dict[str, bool]


# ---- Response schemas ----

class CreateRunResponse(BaseModel):
    run_id: str
    status_url: str


class RunStatusResponse(BaseModel):
    run_id: str
    status: str  # pending | executing | completed | failed
    current_step: str = ""
    steps_completed: int = 0
    steps_total: int = 7
    estimated_remaining_seconds: Optional[int] = None
    error: Optional[str] = None


class ApproveResponse(BaseModel):
    approval_id: str
    paper_run_id: str
    status_url: str


class PaperRunStatusResponse(BaseModel):
    status: str
    day_count: int = 0
    current_value: float = 0.0
    total_return_pct: float = 0.0
    safety_status: str = "all_clear"
    next_report: Optional[str] = None
    next_re_eval: Optional[str] = None


class StopResponse(BaseModel):
    status: str = "halted"


class ReApproveResponse(BaseModel):
    new_approval_id: str
    status: str
