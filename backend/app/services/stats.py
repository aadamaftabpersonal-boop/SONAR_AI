"""Per-shop call history (Bible 48.5). Pure: the database row is mapped to and from StatsData.

History only ever *orders* calls and feeds a labelled 'history' line. It never creates, changes
or hides an answer (D-033). Provider failures are not the shop's fault, so they are not counted.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime

from app.domain.enums import Availability, CallStatus
from app.services.selector import IST


@dataclass
class StatsData:
    attempts: int = 0  # calls that reached an outcome about the shop (answered, no-answer, busy)
    connected: int = 0  # a person answered and gave a recordable response
    completed: int = 0
    no_answer: int = 0
    reported_available: int = 0
    reported_unavailable: int = 0
    uncertain: int = 0
    declined: int = 0
    total_duration_seconds: int = 0
    hour_bucket_stats: dict[str, dict[str, int]] = field(default_factory=dict)
    last_attempt_at: datetime | None = None

    @property
    def answered(self) -> int:
        """Calls that produced a response row (the denominator for the history line)."""
        return self.reported_available + self.reported_unavailable + self.uncertain + self.declined


def apply_outcome(
    stats: StatsData,
    *,
    status: CallStatus,
    availability: Availability | None,
    duration_seconds: int | None,
    now: datetime,
) -> StatsData:
    """Return updated stats for one finished call. Failures and cancellations change nothing."""
    if status not in {CallStatus.COMPLETED, CallStatus.NO_ANSWER, CallStatus.BUSY}:
        return stats
    new = deepcopy(stats)
    new.attempts += 1
    new.last_attempt_at = now
    hour = str(now.astimezone(IST).hour)
    bucket = new.hour_bucket_stats.setdefault(hour, {"attempts": 0, "connected": 0})
    bucket["attempts"] += 1

    if status in {CallStatus.NO_ANSWER, CallStatus.BUSY}:
        new.no_answer += 1
        return new

    new.completed += 1
    new.total_duration_seconds += max(duration_seconds or 0, 0)
    if availability is not None:  # voicemail or IVR has no response row: not a connection
        new.connected += 1
        bucket["connected"] += 1
        match availability:
            case Availability.REPORTED_AVAILABLE:
                new.reported_available += 1
            case Availability.REPORTED_UNAVAILABLE:
                new.reported_unavailable += 1
            case Availability.DECLINED:
                new.declined += 1
            case _:
                new.uncertain += 1
    return new
