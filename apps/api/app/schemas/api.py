from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

LeadStatus = Literal["new", "qualified", "unqualified", "contacted", "converted", "rejected"]
DraftStatus = Literal["draft", "approved", "rejected", "sent"]


class CompanyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    country: str | None = Field(default=None, max_length=100)
    industry: str | None = Field(default=None, max_length=100)
    website: str | None = Field(default=None, max_length=500)
    description: str | None = None
    employee_range: str | None = Field(default=None, max_length=50)
    source: str | None = Field(default=None, max_length=100)


class CompanyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    country: str | None
    industry: str | None
    website: str | None
    description: str | None
    employee_range: str | None
    source: str | None
    created_at: datetime
    updated_at: datetime


class LeadCreate(BaseModel):
    company_id: str | None = None
    company_name: str | None = None
    company_country: str | None = None
    company_industry: str | None = None
    full_name: str = Field(min_length=1, max_length=255)
    job_title: str | None = Field(default=None, max_length=255)
    email: EmailStr
    source: str | None = Field(default=None, max_length=100)


class LeadUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    job_title: str | None = None
    email: EmailStr | None = None
    status: LeadStatus | None = None
    source: str | None = None


class LeadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    company_id: str
    full_name: str
    job_title: str | None
    email: str
    status: str
    source: str | None
    fit_score: int | None
    fit_explanation: str | None
    created_at: datetime
    updated_at: datetime


class LeadListItem(LeadOut):
    company_name: str | None = None
    company_country: str | None = None
    company_industry: str | None = None


class CriterionScore(BaseModel):
    criterion: str
    points: float
    max_points: float
    outcome: Literal["matched", "mismatched", "unknown"]
    evidence: list[str] = []
    note: str = ""


class QualificationResult(BaseModel):
    score: int = Field(ge=0, le=100)
    breakdown: list[CriterionScore]
    evidence: list[str] = []
    missing_info: list[str] = []
    explanation: str


class ICPCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    target_industries: list[str] = []
    target_countries: list[str] = []
    company_size_preferences: list[str] = []
    qualification_criteria: dict[str, Any] = {}


class ICPOut(ICPCreate):
    model_config = ConfigDict(from_attributes=True)
    id: str
    created_at: datetime


class AgentRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    lead_id: str
    workflow_type: str
    status: str
    input_snapshot: dict[str, Any] | None = None
    output: dict[str, Any] | None = None
    error_message: str | None = None
    started_at: datetime
    completed_at: datetime | None = None


class AgentStepOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    agent_run_id: str
    step_name: str
    status: str
    input_summary: str | None = None
    output_summary: str | None = None
    duration_ms: int | None = None
    created_at: datetime


class OutreachDraftOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    lead_id: str
    agent_run_id: str | None
    subject: str
    body: str
    evidence: list[str] = []
    status: str
    approved_by: str | None = None
    approved_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class DraftUpdate(BaseModel):
    subject: str | None = Field(default=None, min_length=1, max_length=500)
    body: str | None = Field(default=None, min_length=1)


class SimulateSendIn(BaseModel):
    confirm: bool = False
    idempotency_key: str | None = None


class ActivityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    lead_id: str
    activity_type: str
    description: str
    meta: dict[str, Any] = {}
    created_at: datetime


class Paginated(BaseModel):
    items: list[Any]
    total: int
    page: int
    page_size: int
