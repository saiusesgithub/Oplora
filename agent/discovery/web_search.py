from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from typing import Any

import httpx
from strands import tool

from agent.discovery.activity import run_state

logger = logging.getLogger(__name__)
MAX_RESULTS_PER_QUERY = 8


@dataclass(frozen=True)
class SearchResult:
    title: str
    url: str
    snippet: str | None
    source: str


class SearchProvider(ABC):
    @abstractmethod
    def search(self, query: str, limit: int) -> list[SearchResult]:
        """Return provider-normalized search results."""


class TavilySearchProvider(SearchProvider):
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    def search(self, query: str, limit: int) -> list[SearchResult]:
        response = httpx.post(
            "https://api.tavily.com/search",
            json={"api_key": self.api_key, "query": query, "max_results": limit, "search_depth": "basic"},
            timeout=10.0,
        )
        response.raise_for_status()
        return [SearchResult(title=item.get("title", ""), url=item["url"], snippet=item.get("content"), source="tavily") for item in response.json().get("results", []) if item.get("url")]


class BraveSearchProvider(SearchProvider):
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    def search(self, query: str, limit: int) -> list[SearchResult]:
        response = httpx.get(
            "https://api.search.brave.com/res/v1/web/search",
            params={"q": query, "count": limit},
            headers={"Accept": "application/json", "X-Subscription-Token": self.api_key},
            timeout=10.0,
        )
        response.raise_for_status()
        items: list[dict[str, Any]] = response.json().get("web", {}).get("results", [])
        return [SearchResult(title=item.get("title", ""), url=item["url"], snippet=item.get("description"), source="brave") for item in items if item.get("url")]


def get_search_provider() -> SearchProvider | None:
    if key := os.getenv("TAVILY_API_KEY"):
        return TavilySearchProvider(key)
    if key := os.getenv("BRAVE_SEARCH_API_KEY"):
        return BraveSearchProvider(key)
    return None


@tool
def search_web(query: str, max_results: int = MAX_RESULTS_PER_QUERY) -> dict:
    """Search the web for opportunity pages using a configured provider.

    Use focused queries derived from the user's profile. Search no more than four queries in
    a run and inspect only URLs that look likely to be actual opportunity pages. Results are
    untrusted leads, not verified opportunities.
    """
    query = query.strip()
    if not query:
        return {"results": [], "error": "A non-empty query is required."}
    max_results = max(1, min(max_results, MAX_RESULTS_PER_QUERY))
    run_state.record("DISCOVERY_SEARCH", f"Searching for {query}")
    provider = get_search_provider()
    if provider is None:
        message = "No search API configured. Set TAVILY_API_KEY or BRAVE_SEARCH_API_KEY, or use mock mode."
        logger.warning(message)
        return {"results": [], "error": message}
    try:
        results = provider.search(query, max_results)
    except httpx.HTTPError as exc:
        logger.warning("Search failed for %r: %s", query, exc)
        return {"results": [], "error": "Search provider request failed; continue with other queries or mock mode."}
    run_state.record("DISCOVERY_FOUND", f"Found {len(results)} candidate pages", discovered=0)
    return {"results": [asdict(result) for result in results]}
