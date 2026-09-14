from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from typing import Any
from urllib.parse import urlsplit

import httpx
from strands import tool

from agent.discovery.activity import run_state

logger = logging.getLogger(__name__)
MAX_RESULTS_PER_QUERY = 6
MAX_SNIPPET_CHARS = 500


@dataclass(frozen=True)
class SearchResult:
    title: str
    url: str
    snippet: str | None
    source: str
    published_date: str | None = None


def _compact_result(title: str, url: str, snippet: str | None, published_date: str | None = None) -> SearchResult:
    """Expose only compact, fetch-decision metadata to the model."""
    compact_snippet = " ".join((snippet or "").split())[:MAX_SNIPPET_CHARS] or None
    return SearchResult(
        title=" ".join(title.split())[:300],
        url=url,
        snippet=compact_snippet,
        source=urlsplit(url).netloc.lower(),
        published_date=published_date,
    )


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
        return [
            _compact_result(item.get("title", ""), item["url"], item.get("content"), item.get("published_date"))
            for item in response.json().get("results", [])
            if item.get("url")
        ]


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
        return [
            _compact_result(item.get("title", ""), item["url"], item.get("description"), item.get("age"))
            for item in items
            if item.get("url")
        ]


def get_search_provider() -> SearchProvider | None:
    if key := os.getenv("TAVILY_API_KEY"):
        return TavilySearchProvider(key)
    if key := os.getenv("BRAVE_SEARCH_API_KEY"):
        return BraveSearchProvider(key)
    return None


def search_provider_name() -> str:
    """Return a safe display name without exposing configured credential values."""
    if os.getenv("TAVILY_API_KEY"):
        return "Tavily"
    if os.getenv("BRAVE_SEARCH_API_KEY"):
        return "Brave"
    return "none"


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
        message = "No search API configured. Set TAVILY_API_KEY or BRAVE_SEARCH_API_KEY."
        logger.warning(message)
        return {"results": [], "error": message}
    try:
        results = provider.search(query, max_results)
    except httpx.HTTPError as exc:
        logger.warning("Search failed for %r: %s", query, exc)
        return {"results": [], "error": "Search provider request failed; continue with other queries or mock mode."}
    run_state.record("DISCOVERY_FOUND", f"Found {len(results)} candidate pages", discovered=0)
    return {"results": [asdict(result) for result in results]}
