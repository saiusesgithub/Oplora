from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock

from agent.models import Opportunity

MAX_SEARCH_QUERIES = 4
MAX_SEARCH_RESULTS_PER_QUERY = 4
MAX_CANDIDATES = 10
MAX_INSPECT_PER_CALL = 3
MAX_FETCHES_PER_RUN = 6


@dataclass(frozen=True)
class Candidate:
    candidate_id: str
    title: str
    url: str
    snippet: str | None
    domain: str
    published_date: str | None
    relevance: float


@dataclass
class DiscoveryState:
    search_queries_used: list[str] = field(default_factory=list)
    candidate_urls: dict[str, Candidate] = field(default_factory=dict)
    inspected_candidate_ids: set[str] = field(default_factory=set)
    fetch_count: int = 0
    extracted_opportunities: dict[str, Opportunity] = field(default_factory=dict)


class DiscoveryStateStore:
    """Thread-safe process-local state for one bounded discovery run."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._state = DiscoveryState()

    def reset(self) -> None:
        with self._lock:
            self._state = DiscoveryState()

    def add_query(self, query: str) -> None:
        with self._lock:
            self._state.search_queries_used.append(query)

    def store_candidates(self, candidates: list[Candidate]) -> None:
        with self._lock:
            self._state.candidate_urls = {candidate.candidate_id: candidate for candidate in candidates}

    def candidate(self, candidate_id: str) -> Candidate | None:
        with self._lock:
            return self._state.candidate_urls.get(candidate_id)

    def claim_fetch(self, candidate_id: str) -> str | None:
        """Claim a fetch slot, returning a structured error string if it cannot run."""
        with self._lock:
            if candidate_id not in self._state.candidate_urls:
                return "Unknown candidate_id"
            if candidate_id in self._state.inspected_candidate_ids:
                return "Candidate already inspected"
            if self._state.fetch_count >= MAX_FETCHES_PER_RUN:
                return "Fetch budget exhausted"
            self._state.inspected_candidate_ids.add(candidate_id)
            self._state.fetch_count += 1
            return None

    def add_extracted(self, opportunity: Opportunity) -> None:
        with self._lock:
            self._state.extracted_opportunities[opportunity.id] = opportunity

    def remaining_fetch_budget(self) -> int:
        with self._lock:
            return MAX_FETCHES_PER_RUN - self._state.fetch_count

    def snapshot(self) -> DiscoveryState:
        with self._lock:
            return DiscoveryState(
                search_queries_used=list(self._state.search_queries_used),
                candidate_urls=dict(self._state.candidate_urls),
                inspected_candidate_ids=set(self._state.inspected_candidate_ids),
                fetch_count=self._state.fetch_count,
                extracted_opportunities=dict(self._state.extracted_opportunities),
            )


discovery_state = DiscoveryStateStore()
