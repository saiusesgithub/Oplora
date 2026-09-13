from __future__ import annotations

import re

from strands import tool

from agent.discovery.activity import run_state
from agent.discovery.normalizer import canonical_url
from agent.models import Opportunity


def _text(value: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (value or "").lower()).strip()


def _identity(opportunity: Opportunity) -> tuple[str, ...]:
    url = canonical_url(str(opportunity.source_url or opportunity.url)) if opportunity.source_url or opportunity.url else ""
    return (
        _text(opportunity.title),
        _text(opportunity.organizer),
        str(opportunity.date or ""),
        _text(opportunity.location),
        url,
    )


def deduplicate(items: list[Opportunity]) -> list[Opportunity]:
    seen: set[tuple[str, ...]] = set()
    unique: list[Opportunity] = []
    for item in items:
        identity = _identity(item)
        # A canonical URL is authoritative; otherwise title + organizer + date + location form the key.
        key = ("url", identity[-1]) if identity[-1] else ("event", *identity[:-1])
        if key in seen:
            run_state.record("DUPLICATE_REMOVED", f"Removed duplicate opportunity: {item.title}", deduplicated=1)
            continue
        seen.add(key)
        unique.append(item)
    return unique


@tool
def deduplicate_opportunities(opportunities: list[dict]) -> dict:
    """Remove obvious duplicate real opportunities before scoring.

    Pass extracted candidates once, after no more than 20 plausible pages have been read.
    """
    bounded = opportunities[:20]
    if len(opportunities) > len(bounded):
        run_state.record("DISCOVERY_LIMIT", "Limited candidates to 20 before scoring", deduplicated=len(opportunities) - len(bounded))
    unique = deduplicate([Opportunity(**item) for item in bounded])
    return {"opportunities": [item.model_dump(mode="json", by_alias=True) for item in unique]}
