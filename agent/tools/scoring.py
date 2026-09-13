from strands import tool

from agent.discovery.activity import run_state
from agent.models import Opportunity, OpportunityScore, Recommendation


@tool
def score_opportunity(
    opportunity: dict,
    match_score: int,
    recommendation: str,
    reasons: list[str],
    warnings: list[str] | None = None,
) -> dict:
    """Record the agent's source-grounded opportunity evaluation.

    Decide the score yourself from the user profile and opportunity facts, then pass a 0-100
    score, HIGH/MEDIUM/LOW recommendation, concise reasons, and warnings. This tool validates
    and records the model-led judgment; it does not use a hardcoded scoring formula.
    """
    parsed_opportunity = Opportunity(**opportunity)
    score = OpportunityScore(
        opportunity_id=parsed_opportunity.id,
        match_score=match_score,
        recommendation=Recommendation(recommendation),
        reasons=reasons,
        warnings=warnings or [],
    )
    run_state.record("OPPORTUNITY_SCORED", f"{score.match_score}% match for {parsed_opportunity.title}", evaluated=1)
    return score.model_dump(mode="json")
