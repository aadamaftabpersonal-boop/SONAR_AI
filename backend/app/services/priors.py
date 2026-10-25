"""Dispatch ordering from shop history (Bible 48.3, D-032, D-033). Pure and deterministic.

The score only decides *who to call first*. It cannot create, upgrade, hide or imply an answer.
A small exploration rate keeps a shop that had one bad day from being buried forever (R-15).
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any

from app.services.stats import StatsData

W_CONNECT, W_POSITIVE, W_NEAR = 0.50, 0.35, 0.15
MIN_BUCKET_ATTEMPTS = 2  # below this, the shop's overall pickup rate is used instead of this hour's


@dataclass(frozen=True)
class Scored:
    key: str
    score: float
    distance_km: float


def _smooth(successes: int, trials: int) -> float:
    """Laplace smoothing: no history means 0.5, and a single event cannot swing it to 0 or 1."""
    return (successes + 1) / (trials + 2)


def score(
    stats: StatsData | None,
    *,
    hour_ist: int,
    distance_km: float,
    radius_km: float,
    min_observations: int,
) -> tuple[float, dict[str, Any]]:
    """Return (priority in [0,1], the inputs used, kept on the attempt for audit)."""
    proximity = max(0.0, 1.0 - distance_km / radius_km) if radius_km > 0 else 0.0
    cold = stats is None or stats.attempts < min_observations
    if cold:
        connect = positive = 0.5
        source = "cold_start"
    else:
        assert stats is not None
        bucket = stats.hour_bucket_stats.get(str(hour_ist), {})
        if bucket.get("attempts", 0) >= MIN_BUCKET_ATTEMPTS:
            connect, source = _smooth(bucket["connected"], bucket["attempts"]), "hour_bucket"
        else:
            connect, source = _smooth(stats.connected, stats.attempts), "overall"
        positive = _smooth(stats.reported_available, stats.connected)
    value = W_CONNECT * connect + W_POSITIVE * positive + W_NEAR * proximity
    snapshot = {
        "source": source,
        "connect_rate": round(connect, 4),
        "positive_rate": round(positive, 4),
        "proximity": round(proximity, 4),
        "attempts": 0 if stats is None else stats.attempts,
        "hour_ist": hour_ist,
    }
    return round(min(max(value, 0.0), 1.0), 4), snapshot


def order(candidates: list[Scored], epsilon: float, rng: random.Random) -> list[Scored]:
    """Best first, except that with probability `epsilon` per slot a lower-ranked shop is tried
    instead. Ties break by distance, then key, so the result is stable."""
    remaining = sorted(candidates, key=lambda c: (-c.score, c.distance_km, c.key))
    result: list[Scored] = []
    while remaining:
        if len(remaining) > 1 and rng.random() < epsilon:
            pick = rng.choice(remaining[1:])
            remaining.remove(pick)
        else:
            pick = remaining.pop(0)
        result.append(pick)
    return result
