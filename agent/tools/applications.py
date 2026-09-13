from __future__ import annotations

import logging
from threading import Lock

from strands import tool

from agent.discovery.activity import run_state
from agent.models import ApplicationApprovalRequest, Opportunity, OpportunityScore, SavedOpportunity

logger = logging.getLogger(__name__)
_saved: dict[str, SavedOpportunity] = {}
_lock = Lock()


def saved_opportunities() -> list[SavedOpportunity]:
    with _lock:
        return list(_saved.values())


@tool
def save_opportunity(opportunity: dict, score: dict | None = None) -> dict:
    """Save a strong opportunity in memory. Call only for HIGH recommendations."""
    parsed_opportunity = Opportunity(**opportunity)
    parsed_score = OpportunityScore(**score) if score else None
    if parsed_score is None or parsed_score.recommendation.value != "HIGH":
        raise ValueError("Only opportunities with a HIGH recommendation may be saved.")
    saved = SavedOpportunity(opportunity=parsed_opportunity, score=parsed_score)
    with _lock:
        _saved[parsed_opportunity.id] = saved
    logger.info("Saved opportunity %s", parsed_opportunity.id)
    run_state.record("OPPORTUNITY_SAVED", f"Saved {parsed_opportunity.title}", saved=1)
    return {"saved": True, "opportunity_id": parsed_opportunity.id}


@tool
def request_application_approval(opportunity: dict) -> dict:
    """Create an approval request. Never submit an application."""
    parsed = Opportunity(**opportunity)
    request = ApplicationApprovalRequest(
        opportunity_id=parsed.id,
        opportunity_title=parsed.title,
        message=f"Approval required before starting an application for {parsed.title or 'this opportunity'}.",
        application_url=parsed.source_url or parsed.url,
    )
    logger.info("Created application approval request for %s", parsed.id)
    return request.model_dump(mode="json")
