from strands import tool

from agent.discovery.activity import run_state
from agent.discovery.normalizer import normalize_opportunity


@tool
def extract_opportunity(page_text: str, source_url: str, source: str, fallback_title: str | None = None) -> dict:
    """Extract a source-grounded Opportunity from text returned by web_fetch.

    Call only after selectively reading a promising URL. Never add facts absent from page_text.
    """
    opportunity = normalize_opportunity(page_text, source_url, source, fallback_title)
    if opportunity is None:
        return {"extracted": False, "reason": "The page did not provide a usable title."}
    run_state.record("PAGE_FETCHED", f"Read {opportunity.title}")
    run_state.record("OPPORTUNITY_EXTRACTED", f"Extracted {opportunity.title}", discovered=1)
    return {"extracted": True, "opportunity": opportunity.model_dump(mode="json", by_alias=True)}
