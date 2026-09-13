from __future__ import annotations

from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, Field, HttpUrl


class EventMode(str, Enum):
    IN_PERSON = "IN_PERSON"
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
    title: str
    organizer: str
    description: str
    location: str
    mode: EventMode
    price_inr: int = Field(ge=0, alias="price")
    date: date
    registration_deadline: date
    tags: list[str]
    url: HttpUrl

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
    opportunity_title: str
    status: str = "PENDING_APPROVAL"
    message: str
    application_url: HttpUrl
    submitted: bool = False


class AgentRunResponse(BaseModel):
    response: str
    saved_opportunities: list[SavedOpportunity]
