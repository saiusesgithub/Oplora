from __future__ import annotations

from datetime import date as Date, datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl


class EventMode(str, Enum):
    IN_PERSON = "IN_PERSON"
    OFFLINE = "OFFLINE"
    ONLINE = "ONLINE"
    HYBRID = "HYBRID"


class Recommendation(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class UserProfile(BaseModel):
    city: str
    radius_km: int = Field(ge=0)
    max_price_inr: int = Field(ge=0)
    interests: list[str]
    online_events_allowed: bool


class Opportunity(BaseModel):
    id: str
    title: str | None = None
    organizer: str | None = None
    description: str | None = None
    location: str | None = None
    venue: str | None = None
    mode: EventMode | None = None
    price_inr: int | None = Field(default=None, ge=0, alias="price")
    currency: str | None = None
    date: Date | None = None
    registration_deadline: Date | None = None
    eligibility: str | None = None
    tags: list[str] = Field(default_factory=list)
    url: HttpUrl | None = None
    source: str = "mock"
    source_url: HttpUrl | None = None
    discovered_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"populate_by_name": True}


class OpportunityScore(BaseModel):
    opportunity_id: str
    match_score: int = Field(ge=0, le=100)
    recommendation: Recommendation
    reasons: list[str]
    warnings: list[str] = Field(default_factory=list)


class SavedOpportunity(BaseModel):
    opportunity: Opportunity
    score: OpportunityScore | None = None
    saved_at: datetime = Field(default_factory=datetime.utcnow)


class ApplicationApprovalRequest(BaseModel):
    opportunity_id: str
    opportunity_title: str | None = None
    status: str = "PENDING_APPROVAL"
    message: str
    application_url: HttpUrl | None = None
    submitted: bool = False


class AgentRunResponse(BaseModel):
    response: str
    discovered: int
    deduplicated: int
    evaluated: int
    saved: int
    saved_opportunities: list[SavedOpportunity]


class AgentRunRequest(BaseModel):
    mode: Literal["mock", "web"] = "mock"
