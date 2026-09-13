from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from threading import Lock

logger = logging.getLogger("oplora.discovery")


@dataclass(frozen=True)
class DiscoveryActivity:
    event: str
    message: str
    occurred_at: datetime


class DiscoveryRunState:
    """Small process-local activity and counter store for the current demo run."""

    def __init__(self) -> None:
        self._lock = Lock()
        self.reset()

    def reset(self) -> None:
        with self._lock:
            self._events: list[DiscoveryActivity] = []
            self._counts = {"discovered": 0, "deduplicated": 0, "evaluated": 0, "saved": 0}

    def record(self, event: str, message: str, **increments: int) -> None:
        activity = DiscoveryActivity(event, message, datetime.now(timezone.utc))
        with self._lock:
            self._events.append(activity)
            for name, amount in increments.items():
                self._counts[name] = self._counts.get(name, 0) + amount
        logger.info("%s %s", event, message)

    def snapshot(self) -> dict:
        with self._lock:
            return {**self._counts, "events": [asdict(event) for event in self._events]}


run_state = DiscoveryRunState()
