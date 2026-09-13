from __future__ import annotations

import logging
from threading import Lock

from strands import tool

from agent.discovery.activity import run_state
from agent.models import ApplicationApprovalRequest, Opportunity, OpportunityScore, SavedOpportunity

logger = logging.getLogger(__name__)
_saved: dict[str, SavedOpportunity] = {}
_evaluated: dict[str, tuple[Opportunity, OpportunityScore]] = {}
_lock = Lock()


def saved_opportunities() -> list[SavedOpportunity]:
    with _lock:
        return list(_saved.values())


def clear_evaluated_opportunities() -> None:
    """Reset only the current-run registry; saved demo results remain available."""
    with _lock:
        _evaluated.clear()


def register_evaluated_opportunity(opportunity: Opportunity, score: OpportunityScore) -> None:
    with _lock:
        _evaluated[opportunity.id] = (opportunity, score)


@tool
def save_opportunity(opportunity_id: str) -> dict:
    """Save one previously evaluated HIGH opportunity by its ID.

    Pass only the opportunity_id returned by score_opportunity. Unknown IDs and non-HIGH
    opportunities return an error result rather than raising. Do not retry an error more than once.
    """
    with _lock:
        evaluated = _evaluated.get(opportunity_id)
        if evaluated is None:
            return {"success": False, "error": "Unknown opportunity_id"}
        opportunity, score = evaluated
        if score.recommendation.value != "HIGH":
            return {"success": False, "error": "Only HIGH opportunities may be saved"}
        if opportunity_id in _saved:
            return {"success": True, "opportunity_id": opportunity_id, "message": "Opportunity already saved"}
        _saved[opportunity_id] = SavedOpportunity(opportunity=opportunity, score=score)
    logger.info("Saved opportunity %s", opportunity_id)
    run_state.record("OPPORTUNITY_SAVED", f"Saved {opportunity.title}", saved=1)
    return {"success": True, "opportunity_id": opportunity_id, "message": "Opportunity saved"}


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
