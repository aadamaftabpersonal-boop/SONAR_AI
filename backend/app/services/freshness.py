"""Per-field freshness (Bible 28). Pure."""

from __future__ import annotations

from datetime import datetime, timedelta

from app.domain.enums import Freshness


def field_freshness(
    value_present: bool, answer_timestamp: datetime, now: datetime, ttl: timedelta
) -> Freshness:
    """FRESH if within TTL, STALE if older, UNKNOWN if the field was never reported."""
    if not value_present:
        return Freshness.UNKNOWN
    age = max(now - answer_timestamp, timedelta(0))  # clock skew: a future timestamp is age 0
    return Freshness.FRESH if age <= ttl else Freshness.STALE
