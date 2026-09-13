from __future__ import annotations

import hashlib
import re
from datetime import date, datetime, timezone
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from agent.models import EventMode, Opportunity

TRACKING_PARAMETERS = {"fbclid", "gclid", "mc_cid", "mc_eid"}
DATE_PATTERNS = ("%Y-%m-%d", "%d %B %Y", "%B %d, %Y", "%d %b %Y", "%b %d, %Y")


def canonical_url(url: str) -> str:
    parsed = urlsplit(url)
    query = urlencode([(key, value) for key, value in parse_qsl(parsed.query) if not key.lower().startswith("utm_") and key.lower() not in TRACKING_PARAMETERS])
    return urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), parsed.path.rstrip("/"), query, ""))


def _clean(value: str | None) -> str | None:
    if not value:
        return None
    value = re.sub(r"\s+", " ", value).strip(" -|:\t")
    return value or None


def _line_value(text: str, labels: str) -> str | None:
    match = re.search(rf"(?:^|\n)\s*(?:{labels})\s*[:\-]\s*([^\n]{{2,200}})", text, re.IGNORECASE)
    return _clean(match.group(1)) if match else None


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    value = value.strip()
    for pattern in DATE_PATTERNS:
        try:
            return datetime.strptime(value, pattern).date()
        except ValueError:
            continue
    return None


def _labeled_date(text: str, labels: str) -> date | None:
    value = _line_value(text, labels)
    if value:
        match = re.search(r"\d{4}-\d{2}-\d{2}|\d{1,2}\s+[A-Za-z]+\s+\d{4}|[A-Za-z]+\s+\d{1,2},?\s+\d{4}", value)
        return _parse_date(match.group(0)) if match else None
    return None


def _first_heading(text: str) -> str | None:
    match = re.search(r"^\s*#\s+(.+)$", text, re.MULTILINE)
    return _clean(match.group(1)) if match else None


def _description(text: str) -> str | None:
    for line in text.splitlines():
        clean = _clean(line)
        if clean and not clean.startswith("#") and len(clean) >= 40:
            return clean[:700]
    return None


def _mode(text: str) -> EventMode | None:
    lower = text.lower()
    if re.search(r"\bhybrid\b", lower):
        return EventMode.HYBRID
    if re.search(r"\b(online|virtual|remote)\b", lower):
        return EventMode.ONLINE
    if re.search(r"\b(in[ -]?person|offline)\b", lower):
        return EventMode.OFFLINE
    return None


def _price(text: str) -> tuple[int | None, str | None]:
    if re.search(r"\b(free|no cost|complimentary)\b", text, re.IGNORECASE):
        return 0, None
    match = re.search(r"(?:₹|INR\s?)([\d,]+)|(?:\$|USD\s?)([\d,]+)", text, re.IGNORECASE)
    if not match:
        return None, None
    amount = int((match.group(1) or match.group(2)).replace(",", ""))
    return amount, "INR" if match.group(1) else "USD"


def _tags(text: str) -> list[str]:
    lower = text.lower()
    labels = {"hackathon": "hackathons", "meetup": "developer events", "workshop": "workshops", "competition": "competitions", "internship": "internships", "student": "student programs", "aws": "AWS", "cloud": "cloud", "generative ai": "AI", "artificial intelligence": "AI", "startup": "startups"}
    return list(dict.fromkeys(tag for token, tag in labels.items() if token in lower))


def normalize_opportunity(page_text: str, source_url: str, source: str, fallback_title: str | None = None) -> Opportunity | None:
    """Normalize only source-supported values; absent values intentionally remain null."""
    page_text = page_text[:25_000]
    title = _first_heading(page_text) or _clean(fallback_title)
    if not title:
        return None
    venue = _line_value(page_text, "venue")
    location = _line_value(page_text, "location|where") or venue
    price, currency = _price(page_text)
    canonical = canonical_url(source_url)
    stable_key = "|".join((title.lower(), (_line_value(page_text, "organizer|hosted by|organised by") or "").lower(), str(_labeled_date(page_text, "event date|date|when") or ""), (location or "").lower(), canonical))
    return Opportunity.model_validate({
        "id": f"web-{hashlib.sha256(stable_key.encode()).hexdigest()[:16]}",
        "title": title,
        "organizer": _line_value(page_text, "organizer|hosted by|organised by"),
        "description": _description(page_text),
        "location": location,
        "venue": venue,
        "mode": _mode(page_text),
        "price": price,
        "currency": currency,
        "date": _labeled_date(page_text, "event date|date|when"),
        "registration_deadline": _labeled_date(page_text, "registration deadline|registration closes|deadline|apply by"),
        "eligibility": _line_value(page_text, "eligibility|who can apply|who can attend"),
        "tags": _tags(page_text),
        "url": canonical,
        "source": source,
        "source_url": canonical,
        "discovered_at": datetime.now(timezone.utc),
    })
