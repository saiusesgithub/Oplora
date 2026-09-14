from __future__ import annotations

from typing import Any

import httpx
from strands import tool
from strands.vended_tools import make_web_fetch

from agent.discovery.activity import run_state
from agent.discovery.normalizer import canonical_url, normalize_opportunity
from agent.discovery.state import (
    MAX_CANDIDATES,
    MAX_FETCHES_PER_RUN,
    MAX_INSPECT_PER_CALL,
    MAX_SEARCH_QUERIES,
    MAX_SEARCH_RESULTS_PER_QUERY,
    Candidate,
    discovery_state,
)
from agent.discovery.web_search import get_search_provider


def _candidate_payload(candidate: Candidate) -> dict[str, str | None]:
    return {
        "candidate_id": candidate.candidate_id,
        "title": candidate.title,
        "url": candidate.url,
        "snippet": candidate.snippet,
        "domain": candidate.domain,
        "published_date": candidate.published_date,
    }


@tool
def search_opportunities(queries: list[str]) -> dict[str, Any]:
    """Find compact, ranked real-web opportunity candidates from up to four agent-chosen queries.

    The Python layer enforces four queries, four results per query, URL deduplication, and a total
    of ten candidates. Review the returned summaries before calling inspect_candidates.
    """
    provider = get_search_provider()
    if provider is None:
        return {"candidates": [], "error": "No search API configured."}

    ranked: list[tuple[float, int, Candidate]] = []
    seen_urls: set[str] = set()
    for query_index, query in enumerate(queries[:MAX_SEARCH_QUERIES]):
        query = query.strip()
        if not query:
            continue
        discovery_state.add_query(query)
        run_state.record("DISCOVERY_SEARCH", f"Searching for {query}")
        try:
            results = provider.search(query, MAX_SEARCH_RESULTS_PER_QUERY)
        except httpx.HTTPError:
            run_state.record("DISCOVERY_SEARCH_FAILED", f"Search failed for {query}")
            continue
        for result_index, result in enumerate(results[:MAX_SEARCH_RESULTS_PER_QUERY]):
            url = canonical_url(result.url)
            if url in seen_urls:
                continue
            seen_urls.add(url)
            candidate = Candidate(
                candidate_id=f"candidate-{len(ranked) + 1}",
                title=result.title,
                url=url,
                snippet=result.snippet,
                domain=result.source,
                published_date=result.published_date,
                relevance=result.relevance,
            )
            ranked.append((result.relevance, query_index * MAX_SEARCH_RESULTS_PER_QUERY + result_index, candidate))

    ranked.sort(key=lambda item: (-item[0], item[1]))
    candidates = [item[2] for item in ranked[:MAX_CANDIDATES]]
    candidates = [
        Candidate(candidate_id=f"candidate-{index}", title=item.title, url=item.url, snippet=item.snippet, domain=item.domain, published_date=item.published_date, relevance=item.relevance)
        for index, item in enumerate(candidates, start=1)
    ]
    discovery_state.store_candidates(candidates)
    run_state.record("DISCOVERY_FOUND", f"Found {len(candidates)} candidate pages")
    return {"candidates": [_candidate_payload(candidate) for candidate in candidates]}


async def _fetch_markdown(url: str) -> str:
    async with httpx.AsyncClient(timeout=httpx.Timeout(10.0), follow_redirects=True) as client:
        internal_fetch = make_web_fetch(
            mode="markdown",
            client=client,
            max_bytes=1_000_000,
            max_content_chars=6_000,
        )
        return await internal_fetch._tool_func(url)


def _compact_opportunity(candidate_id: str, opportunity: Any) -> dict[str, Any]:
    populated = sum(value is not None and value != [] for value in (opportunity.organizer, opportunity.date, opportunity.location, opportunity.price_inr, opportunity.description, opportunity.source_url))
    return {
        "candidate_id": candidate_id,
        "opportunity_id": opportunity.id,
        "title": opportunity.title,
        "organizer": opportunity.organizer,
        "date": opportunity.date.isoformat() if opportunity.date else None,
        "location": opportunity.location,
        "price": opportunity.price_inr,
        "description": (opportunity.description or "")[:800] or None,
        "source_url": str(opportunity.source_url or opportunity.url) if opportunity.source_url or opportunity.url else None,
        "extraction_confidence": round(populated / 6, 2),
    }


@tool
async def inspect_candidates(candidate_ids: list[str]) -> dict[str, Any]:
    """Inspect up to three stored candidates and return compact, source-grounded opportunities.

    A run has six fetches total. Each candidate is fetched at most once. Individual fetch failures
    are returned for that candidate and do not abort the remaining inspection work.
    """
    inspected: list[dict[str, Any]] = []
    for candidate_id in candidate_ids[:MAX_INSPECT_PER_CALL]:
        claim_error = discovery_state.claim_fetch(candidate_id)
        if claim_error:
            inspected.append({"candidate_id": candidate_id, "success": False, "error": claim_error})
            continue
        candidate = discovery_state.candidate(candidate_id)
        if candidate is None:
            inspected.append({"candidate_id": candidate_id, "success": False, "error": "Unknown candidate_id"})
            continue
        try:
            page_text = await _fetch_markdown(candidate.url)
            opportunity = normalize_opportunity(page_text, candidate.url, candidate.domain, candidate.title)
        except (httpx.HTTPError, TimeoutError, ValueError):
            inspected.append({"candidate_id": candidate_id, "success": False, "error": "Fetch failed"})
            run_state.record("PAGE_FETCH_FAILED", f"Could not read {candidate.title}")
            continue
        if opportunity is None:
            inspected.append({"candidate_id": candidate_id, "success": False, "error": "No opportunity details extracted"})
            continue
        discovery_state.add_extracted(opportunity)
        run_state.record("PAGE_FETCHED", f"Read {opportunity.title}")
        run_state.record("OPPORTUNITY_EXTRACTED", f"Extracted {opportunity.title}", discovered=1)
        inspected.append({"success": True, **_compact_opportunity(candidate_id, opportunity)})
    return {
        "inspected": inspected,
        "remaining_fetch_budget": discovery_state.remaining_fetch_budget(),
        "max_fetches_per_run": MAX_FETCHES_PER_RUN,
    }
