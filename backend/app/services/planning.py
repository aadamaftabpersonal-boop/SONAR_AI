"""Decide the order in which a FAST search calls its targets (Bible 48.3, D-032)."""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.config import Settings
from app.db.repositories import StatsRepo
from app.domain.schemas import ParsedQuery, PlannedTarget
from app.services.priors import Scored, order, score
from app.services.selector import IST


@dataclass(frozen=True)
class PlannedCall:
    target: PlannedTarget
    priority: float | None  # None when calls go in the planned order (Wave 2 off or THOROUGH)
    snapshot: dict[str, Any] | None


def plan_order(
    session: Session,
    targets: list[PlannedTarget],
    parsed: ParsedQuery,
    settings: Settings,
    now: datetime,
    rng: random.Random | None = None,
) -> list[PlannedCall]:
    """Score every target from its history, order best-first with a little exploration, and give
    each call a priority that reproduces that order when attempts are claimed.

    The scores only decide who is called first. They never alter or imply an answer (D-033)."""
    rng = rng or random.Random()
    stats = StatsRepo(session)
    hour = now.astimezone(IST).hour
    scored: dict[str, tuple[float, dict[str, Any]]] = {}
    for t in targets:
        scored[str(t.business_id)] = score(
            stats.get(t.business_id),
            hour_ist=hour,
            distance_km=t.distance_km,
            radius_km=parsed.radius_km,
            min_observations=settings.prior_min_observations,
        )
    by_key = {str(t.business_id): t for t in targets}
    natural = order([Scored(k, s, by_key[k].distance_km) for k, (s, _) in scored.items()], 0.0, rng)
    final = order(
        [Scored(k, s, by_key[k].distance_km) for k, (s, _) in scored.items()],
        settings.prior_exploration_epsilon,
        rng,
    )
    natural_rank = {c.key: i for i, c in enumerate(natural)}
    # Hand the best scores out in final order, so ordering by priority gives exactly `final`.
    ranked_scores = sorted((c.score for c in natural), reverse=True)
    plan: list[PlannedCall] = []
    for i, c in enumerate(final):
        own_score, snapshot = scored[c.key]
        plan.append(
            PlannedCall(
                target=by_key[c.key],
                priority=ranked_scores[i],
                snapshot={**snapshot, "own_score": own_score, "explored": natural_rank[c.key] != i},
            )
        )
    return plan
