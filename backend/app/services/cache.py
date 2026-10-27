"""Fresh-cache reuse (Bible FR-30, Build Map T7.4). The rule is pure; the lookup is one query.

A shop that answered the *same* question on a live call a short while ago is not called again: its
earlier answer is shown as `CACHED_LIVE`, with the **original** time, so nobody mistakes it for a
new call. Only definite, fully validated live answers qualify. Simulated answers never do, and a
demo search never shows live data. `force_fresh` always calls.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

REUSABLE_AVAILABILITY = {"REPORTED_AVAILABLE", "REPORTED_UNAVAILABLE"}


@dataclass(frozen=True)
class PastAnswer:
    data_origin: str
    extraction_status: str
    availability: str
    exact_match: str
    evidence_validated: bool
    price_amount: Decimal | None
    answer_timestamp: datetime
    query: dict[str, Any]  # the ParsedQuery of the search that produced the answer


def _key(query: dict[str, Any]) -> tuple[str, str, tuple[tuple[str, str], ...]]:
    attrs = query.get("attributes") or {}
    return (
        str(query.get("category", "")).strip().casefold(),
        " ".join(str(query.get("item_name", "")).split()).casefold(),
        tuple(
            sorted(
                (str(k).strip().casefold(), " ".join(str(v).split()).casefold())
                for k, v in attrs.items()
            )
        ),
    )


def same_question(a: dict[str, Any], b: dict[str, Any]) -> bool:
    """Same category, item and attributes (case and spacing ignored). Anything else is a miss."""
    return _key(a) == _key(b)


def reusable(
    past: PastAnswer,
    query: dict[str, Any],
    now: datetime,
    *,
    ttl_availability: timedelta,
    ttl_price: timedelta,
) -> bool:
    if past.data_origin != "LIVE_CALL":
        return False  # simulated or already-cached answers are never reused
    if past.extraction_status != "VALID" or not past.evidence_validated:
        return False
    if past.availability not in REUSABLE_AVAILABILITY:
        return False  # uncertain, declined, alternatives: call again
    if not same_question(past.query, query):
        return False
    age = now - past.answer_timestamp
    if age < timedelta(0) or age > ttl_availability:
        return False  # a future timestamp is suspicious; an old one is stale
    if past.availability == "REPORTED_AVAILABLE":
        if past.exact_match != "CONFIRMED":
            return False
        if "price" in (query.get("required_fields") or []):
            if past.price_amount is None or age > ttl_price:
                return False
    return True
