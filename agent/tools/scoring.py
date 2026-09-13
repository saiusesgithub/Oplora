from strands import tool


@tool
def score_opportunity(opportunity: dict) -> dict:
    """Prepare an opportunity for model-led scoring. Evaluate it against the profile yourself.

    Return a 0-100 score, HIGH/MEDIUM/LOW recommendation, concise reasons, and warnings.
    Consider interests, location/radius, event mode, price, and deadlines. This tool
    deliberately does not calculate a score: the agent makes the recommendation.
    """
    return {"opportunity": opportunity, "scoring_dimensions": ["interest overlap", "Hyderabad radius", "online allowance", "price limit", "deadline urgency"]}
