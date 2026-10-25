"""Curated business directory (Bible 24.1, D-014): load candidates for the selector."""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.db.repositories import AttemptRepo, BusinessRepo
from app.domain.enums import BusinessKind, ParticipationStatus
from app.services.selector import IST, Candidate


def ist_day_start(now: datetime) -> datetime:
    """Start of the current IST day; 'daily' caps reset at IST midnight (documented, Bible 27)."""
    local = now.astimezone(IST)
    return local.replace(hour=0, minute=0, second=0, microsecond=0)


def load_candidates(session: Session, category: str, now: datetime) -> list[Candidate]:
    businesses = BusinessRepo(session).callable_in_category(category)
    attempts = AttemptRepo(session)
    since = ist_day_start(now) if now.tzinfo else now - timedelta(hours=24)
    return [
        Candidate(
            business_id=b.id,
            name=b.name,
            kind=BusinessKind(b.kind),
            participation_status=ParticipationStatus(b.participation_status),
            lat=b.latitude,
            lng=b.longitude,
            best_call_window=b.best_call_window,
            opted_out=b.opted_out_at is not None,
            calls_today=attempts.calls_today(b.id, since),
            last_call_at=attempts.last_call_at(b.id),
        )
        for b in businesses
    ]
