"""Data access. Sync SQLAlchemy sessions; the caller owns commit/rollback unless noted.

Postgres is the job queue (D-006): `claim_next` uses FOR UPDATE SKIP LOCKED so two workers can
never take the same attempt.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.db.models import (
    AuditEvent,
    Business,
    BusinessResponse,
    BusinessStats,
    CallAttempt,
    ProviderEvent,
    SearchJob,
)
from app.domain.enums import CallStatus, ParticipationStatus
from app.domain.transitions import can_transition, is_terminal
from app.services.stats import StatsData


def utcnow() -> datetime:
    return datetime.now(UTC)


def payload_hash(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class SearchRepo:
    def __init__(self, session: Session):
        self.s = session

    def create(self, **fields: Any) -> SearchJob:
        job = SearchJob(**fields)
        self.s.add(job)
        self.s.flush()
        return job

    def get(self, job_id: uuid.UUID) -> SearchJob | None:
        return self.s.get(SearchJob, job_id)

    def lock(self, job_id: uuid.UUID) -> SearchJob | None:
        return self.s.execute(
            select(SearchJob).where(SearchJob.id == job_id).with_for_update()
        ).scalar_one_or_none()

    def set_status(self, job_id: uuid.UUID, status: str, **fields: Any) -> None:
        self.s.execute(
            update(SearchJob).where(SearchJob.id == job_id).values(status=status, **fields)
        )


class AttemptRepo:
    def __init__(self, session: Session):
        self.s = session

    def insert(self, **fields: Any) -> CallAttempt:
        attempt = CallAttempt(**fields)
        self.s.add(attempt)
        self.s.flush()
        return attempt

    def get(self, attempt_id: uuid.UUID) -> CallAttempt | None:
        return self.s.get(CallAttempt, attempt_id)

    def for_search(self, job_id: uuid.UUID) -> list[CallAttempt]:
        return list(
            self.s.execute(
                select(CallAttempt)
                .where(CallAttempt.search_job_id == job_id)
                .order_by(CallAttempt.created_at, CallAttempt.attempt_number)
            ).scalars()
        )

    def claim_next(self, now: datetime | None = None) -> CallAttempt | None:
        """Claim one due PENDING attempt and mark it DISPATCHING, atomically.

        Rows locked by another transaction are skipped, so concurrent workers never share one.
        The caller must commit to release the lock and persist the claim.
        """
        now = now or utcnow()
        attempt = self.s.execute(
            select(CallAttempt)
            .where(CallAttempt.status == CallStatus.PENDING, CallAttempt.not_before <= now)
            # attempts planned together share not_before; Wave 2 priority decides who goes first
            .order_by(
                CallAttempt.not_before,
                CallAttempt.priority_score.desc().nulls_last(),
                CallAttempt.created_at,
            )
            .limit(1)
            .with_for_update(skip_locked=True)
        ).scalar_one_or_none()
        if attempt is None:
            return None
        attempt.status = CallStatus.DISPATCHING
        attempt.started_at = attempt.started_at or now
        attempt.updated_at = now
        self.s.flush()
        return attempt

    def update_status(
        self,
        attempt_id: uuid.UUID,
        new: CallStatus,
        *,
        provider_status: str | None = None,
        **fields: Any,
    ) -> bool:
        """Apply a status change only if it moves forward. Returns whether it was applied.

        The raw provider status is always recorded for debugging, even when the change is ignored.
        """
        attempt = self.s.execute(
            select(CallAttempt).where(CallAttempt.id == attempt_id).with_for_update()
        ).scalar_one()
        if provider_status is not None:
            attempt.provider_status = provider_status
        current = CallStatus(attempt.status)
        if not can_transition(current, new):
            self.s.flush()
            return False
        attempt.status = new
        attempt.updated_at = utcnow()
        if is_terminal(new) and attempt.completed_at is None:
            attempt.completed_at = attempt.updated_at
        for key, value in fields.items():
            setattr(attempt, key, value)
        self.s.flush()
        return True

    def mark_dispatch_unknown(self, attempt_id: uuid.UUID, reason: str) -> None:
        """The call may or may not have started. Never auto-retried (a duplicate call to a
        shopkeeper is worse than a missed one, Bible 27.2.1). Same rank as DISPATCHING, so it
        bypasses the forward-only rule on purpose."""
        self.s.execute(
            update(CallAttempt)
            .where(CallAttempt.id == attempt_id, CallAttempt.status == CallStatus.DISPATCHING)
            .values(status=CallStatus.DISPATCH_UNKNOWN, failure_reason=reason, updated_at=utcnow())
        )

    def dispatch_unknown_on_start(self) -> int:
        """After a restart, DISPATCHING attempts with no call id become DISPATCH_UNKNOWN."""
        result = self.s.execute(
            update(CallAttempt)
            .where(
                CallAttempt.status == CallStatus.DISPATCHING, CallAttempt.provider_call_id.is_(None)
            )
            .values(
                status=CallStatus.DISPATCH_UNKNOWN,
                failure_reason="RESTART_DURING_DISPATCH",
                updated_at=utcnow(),
            )
        )
        return result.rowcount

    def stale_in_flight(self, older_than: datetime) -> list[CallAttempt]:
        """Non-terminal attempts that have a provider call id and have gone quiet."""
        live = [
            CallStatus.DIALING,
            CallStatus.RINGING,
            CallStatus.IN_PROGRESS,
            CallStatus.PROCESSING,
        ]
        return list(
            self.s.execute(
                select(CallAttempt).where(
                    CallAttempt.status.in_(live),
                    CallAttempt.provider_call_id.is_not(None),
                    CallAttempt.updated_at < older_than,
                )
            ).scalars()
        )

    def dispatched_since(self, since: datetime, provider: str) -> int:
        """Calls that actually left the building today, for the global budget (NFR-06)."""
        return self.s.execute(
            select(func.count())
            .select_from(CallAttempt)
            .where(
                CallAttempt.provider == provider,
                CallAttempt.started_at >= since,
                (CallAttempt.provider_call_id.is_not(None))
                | (CallAttempt.status == CallStatus.DISPATCH_UNKNOWN),
            )
        ).scalar_one()

    def cancel_pending_for_business(self, business_id: uuid.UUID, reason: str) -> int:
        result = self.s.execute(
            update(CallAttempt)
            .where(CallAttempt.business_id == business_id, CallAttempt.status == CallStatus.PENDING)
            .values(
                status=CallStatus.CANCELLED,
                failure_reason=reason,
                completed_at=utcnow(),
                updated_at=utcnow(),
            )
        )
        return result.rowcount

    def attach_execution_id(self, attempt_id: uuid.UUID, provider_call_id: str) -> None:
        self.s.execute(
            update(CallAttempt)
            .where(CallAttempt.id == attempt_id)
            .values(provider_call_id=provider_call_id)
        )

    def by_provider_call_id(self, provider: str, provider_call_id: str) -> CallAttempt | None:
        return self.s.execute(
            select(CallAttempt).where(
                CallAttempt.provider == provider, CallAttempt.provider_call_id == provider_call_id
            )
        ).scalar_one_or_none()

    def count_active(self) -> int:
        """Attempts that occupy a call slot: from DISPATCHING until terminal (Bible 27.2.6)."""
        active = [
            CallStatus.DISPATCHING,
            CallStatus.DIALING,
            CallStatus.RINGING,
            CallStatus.IN_PROGRESS,
            CallStatus.PROCESSING,
        ]
        return self.s.execute(
            select(func.count()).select_from(CallAttempt).where(CallAttempt.status.in_(active))
        ).scalar_one()

    def calls_today(self, business_id: uuid.UUID, since: datetime) -> int:
        """Dispatched attempts (any outcome) for a business since a boundary (daily cap, FR-05)."""
        return self.s.execute(
            select(func.count())
            .select_from(CallAttempt)
            .where(
                CallAttempt.business_id == business_id,
                CallAttempt.started_at.is_not(None),
                CallAttempt.started_at >= since,
            )
        ).scalar_one()

    def last_call_at(self, business_id: uuid.UUID) -> datetime | None:
        return self.s.execute(
            select(func.max(CallAttempt.started_at)).where(CallAttempt.business_id == business_id)
        ).scalar_one()


class EventRepo:
    def __init__(self, session: Session):
        self.s = session

    def insert_or_ignore(
        self,
        *,
        provider: str,
        provider_call_id: str | None,
        provider_status: str | None,
        payload: dict[str, Any],
        call_attempt_id: uuid.UUID | None = None,
    ) -> bool:
        """Store a raw provider event. Returns False if an identical one already exists."""
        stmt = (
            pg_insert(ProviderEvent)
            .values(
                provider=provider,
                provider_call_id=provider_call_id,
                provider_status=provider_status,
                payload_sha256=payload_hash(payload),
                payload=payload,
                call_attempt_id=call_attempt_id,
            )
            .on_conflict_do_nothing(constraint="uq_provider_event")
            .returning(ProviderEvent.id)
        )
        return self.s.execute(stmt).scalar_one_or_none() is not None

    def attach_orphans(self, provider: str, provider_call_id: str, attempt_id: uuid.UUID) -> int:
        result = self.s.execute(
            update(ProviderEvent)
            .where(
                ProviderEvent.provider == provider,
                ProviderEvent.provider_call_id == provider_call_id,
                ProviderEvent.call_attempt_id.is_(None),
            )
            .values(call_attempt_id=attempt_id)
        )
        return result.rowcount

    def orphans(self, provider: str) -> list[ProviderEvent]:
        return list(
            self.s.execute(
                select(ProviderEvent).where(
                    ProviderEvent.provider == provider, ProviderEvent.call_attempt_id.is_(None)
                )
            ).scalars()
        )


class ResponseRepo:
    def __init__(self, session: Session):
        self.s = session

    def insert_once(self, **fields: Any) -> bool:
        """Write the result for an attempt exactly once. Returns False if it already existed."""
        stmt = (
            pg_insert(BusinessResponse)
            .values(**fields)
            .on_conflict_do_nothing(index_elements=["call_attempt_id"])
            .returning(BusinessResponse.id)
        )
        return self.s.execute(stmt).scalar_one_or_none() is not None

    def for_search(self, job_id: uuid.UUID) -> list[BusinessResponse]:
        return list(
            self.s.execute(
                select(BusinessResponse)
                .where(BusinessResponse.search_job_id == job_id)
                .order_by(BusinessResponse.answer_timestamp)
            ).scalars()
        )

    def latest_for_business(self, business_id: uuid.UUID) -> BusinessResponse | None:
        return self.s.execute(
            select(BusinessResponse)
            .where(BusinessResponse.business_id == business_id)
            .order_by(BusinessResponse.answer_timestamp.desc())
            .limit(1)
        ).scalar_one_or_none()


class BusinessRepo:
    def __init__(self, session: Session):
        self.s = session

    def get(self, business_id: uuid.UUID) -> Business | None:
        return self.s.get(Business, business_id)

    def callable_in_category(self, category: str) -> list[Business]:
        """Consented or test-line businesses that have not opted out (FR-06, first defence)."""
        return list(
            self.s.execute(
                select(Business).where(
                    Business.category == category,
                    Business.participation_status.in_(
                        [ParticipationStatus.CONSENTED, ParticipationStatus.TEST_LINE]
                    ),
                    Business.opted_out_at.is_(None),
                )
            ).scalars()
        )

    def mark_opt_out(self, business_id: uuid.UUID) -> None:
        now = utcnow()
        self.s.execute(
            update(Business)
            .where(Business.id == business_id)
            .values(
                participation_status=ParticipationStatus.OPTED_OUT, opted_out_at=now, updated_at=now
            )
        )


class StatsRepo:
    """Reads and writes a shop's history. Rows are locked while updated, so two jobs finishing
    calls to the same shop cannot lose each other's counts."""

    def __init__(self, session: Session):
        self.s = session

    def _row(self, business_id: uuid.UUID, lock: bool) -> BusinessStats | None:
        stmt = select(BusinessStats).where(BusinessStats.business_id == business_id)
        return self.s.execute(stmt.with_for_update() if lock else stmt).scalar_one_or_none()

    def get(self, business_id: uuid.UUID) -> StatsData | None:
        row = self._row(business_id, lock=False)
        return None if row is None else _to_data(row)

    def update(self, business_id: uuid.UUID, change: Callable[[StatsData], StatsData]) -> None:
        """Apply `change` to the shop's history. A change that returns its input unchanged (for
        example a provider failure) is a no-op and creates no row."""
        row = self._row(business_id, lock=True)
        if row is None:
            blank = StatsData()
            if change(blank) is blank:
                return
            self.s.execute(
                pg_insert(BusinessStats)
                .values(business_id=business_id)
                .on_conflict_do_nothing(index_elements=["business_id"])
            )
            row = self._row(business_id, lock=True)  # recompute from the locked row, so a
            assert row is not None  # concurrent first update is never lost
        new = change(_to_data(row))
        for name in _STATS_FIELDS:
            setattr(row, name, getattr(new, name))
        row.updated_at = utcnow()
        self.s.flush()


_STATS_FIELDS = (
    "attempts",
    "connected",
    "completed",
    "no_answer",
    "reported_available",
    "reported_unavailable",
    "uncertain",
    "declined",
    "total_duration_seconds",
    "hour_bucket_stats",
    "last_attempt_at",
)


def _to_data(row: BusinessStats) -> StatsData:
    return StatsData(**{name: getattr(row, name) for name in _STATS_FIELDS})


class AuditRepo:
    def __init__(self, session: Session):
        self.s = session

    def add(
        self,
        actor: str,
        action: str,
        *,
        search_job_id: uuid.UUID | None = None,
        business_id: uuid.UUID | None = None,
        detail: dict[str, Any] | None = None,
    ) -> None:
        self.s.add(
            AuditEvent(
                actor=actor,
                action=action,
                search_job_id=search_job_id,
                business_id=business_id,
                detail=detail or {},
            )
        )
        self.s.flush()
