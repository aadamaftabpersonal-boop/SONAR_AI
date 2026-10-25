"""Target selection (Bible 24.2, FR-05..07). Pure: all state is passed in, so it is easy to test.

Eligibility is enforced here and again in the dispatcher (FR-06).
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.domain.enums import BusinessKind, ParticipationStatus
from app.domain.schemas import PlannedTarget
from app.services.geo import distance_km

IST = ZoneInfo("Asia/Kolkata")
DEFAULT_WINDOW = (time(9, 0), time(20, 0))
_WINDOW = re.compile(r"(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})")
CALLABLE = {ParticipationStatus.CONSENTED, ParticipationStatus.TEST_LINE}


@dataclass(frozen=True)
class Candidate:
    business_id: uuid.UUID
    name: str
    kind: BusinessKind
    participation_status: ParticipationStatus
    lat: float | None
    lng: float | None
    best_call_window: str | None = None
    opted_out: bool = False
    calls_today: int = 0
    last_call_at: datetime | None = None


@dataclass
class SelectionResult:
    targets: list[PlannedTarget]
    excluded: dict[str, int] = field(default_factory=dict)

    @property
    def considered(self) -> int:
        return len(self.targets) + sum(self.excluded.values())


def parse_window(text: str | None) -> tuple[time, time]:
    """'10:00-13:00 IST' -> (10:00, 13:00). Unparseable or missing text means the default."""
    if not text:
        return DEFAULT_WINDOW
    m = _WINDOW.search(text)
    if not m:
        return DEFAULT_WINDOW
    h1, m1, h2, m2 = (int(g) for g in m.groups())
    try:
        return time(h1, m1), time(h2, m2)
    except ValueError:
        return DEFAULT_WINDOW


def in_window(now: datetime, window_text: str | None) -> bool:
    start, end = parse_window(window_text)
    local = now.astimezone(IST).time()
    return start <= local < end


def select(
    candidates: list[Candidate],
    *,
    lat: float,
    lng: float,
    radius_km: float,
    now: datetime,
    max_targets: int,
    daily_cap: int,
    cooldown_minutes: int,
) -> SelectionResult:
    excluded: dict[str, int] = {}

    def skip(reason: str) -> None:
        excluded[reason] = excluded.get(reason, 0) + 1

    eligible: list[tuple[float, Candidate]] = []
    for c in candidates:
        # defence in depth: never trust the caller to have pre-filtered consent (FR-06)
        if c.opted_out or c.participation_status not in CALLABLE:
            skip("not_consented")
            continue
        if c.lat is None or c.lng is None:
            skip("no_location")
            continue
        d = distance_km(lat, lng, c.lat, c.lng)
        if d > radius_km:
            skip("outside_radius")
            continue
        if c.calls_today >= daily_cap:
            skip("daily_cap")
            continue
        if c.last_call_at and now - c.last_call_at < timedelta(minutes=cooldown_minutes):
            skip("cooldown")
            continue
        if not in_window(now, c.best_call_window):
            skip("outside_call_window")
            continue
        eligible.append((d, c))

    eligible.sort(key=lambda pair: (pair[0], str(pair[1].business_id)))
    targets = [
        PlannedTarget(business_id=c.business_id, name=c.name, kind=c.kind, distance_km=round(d, 2))
        for d, c in eligible[:max_targets]
    ]
    if len(eligible) > max_targets:
        excluded["over_target_cap"] = len(eligible) - max_targets
    return SelectionResult(targets=targets, excluded=excluded)
