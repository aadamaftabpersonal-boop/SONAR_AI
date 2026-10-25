"""Search-job aggregation and deadlines (Bible 26, FR-22)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import CallAttempt, SearchJob
from app.db.repositories import AttemptRepo, SearchRepo
from app.domain.enums import CallStatus, SearchStatus
from app.domain.transitions import is_terminal, search_status_from_attempts
from app.services.stoprule import STOP_REASON

OPEN_STATUSES = (SearchStatus.CREATED, SearchStatus.RUNNING)


def latest_attempts(attempts: list[CallAttempt]) -> list[CallAttempt]:
    """One attempt per business: the highest attempt number decides the business's state."""
    best: dict[uuid.UUID, CallAttempt] = {}
    for a in attempts:
        if a.business_id not in best or a.attempt_number > best[a.business_id].attempt_number:
            best[a.business_id] = a
    return list(best.values())


def refresh_job(session: Session, job_id: uuid.UUID, now: datetime) -> SearchStatus | None:
    """Recompute a job's status from its attempts. Safe to call repeatedly."""
    jobs = SearchRepo(session)
    job = jobs.lock(job_id)
    if job is None:
        return None
    attempts = AttemptRepo(session).for_search(job_id)
    if not attempts:
        return SearchStatus(job.status)  # clarification / no-eligible jobs have no attempts

    latest = latest_attempts(attempts)
    if job.stopped_early:
        # shops deliberately not called (enough had confirmed) do not make the search "partial"
        latest = [a for a in latest if a.failure_reason != STOP_REASON]
    statuses = [CallStatus(a.status) for a in latest]
    cancelled = job.status == SearchStatus.CANCELLED
    deadline_passed = job.deadline_at is not None and now >= job.deadline_at

    if all(s == CallStatus.PENDING for s in statuses) and not (cancelled or deadline_passed):
        return SearchStatus(job.status)  # nothing dispatched yet: stay CREATED

    new_status = search_status_from_attempts(
        statuses, cancelled=cancelled, deadline_passed=deadline_passed
    )
    fields: dict = {}
    if job.started_at is None and any(s != CallStatus.PENDING for s in statuses):
        fields["started_at"] = now
    if new_status != SearchStatus.RUNNING and job.completed_at is None:
        fields["completed_at"] = now
    jobs.set_status(job_id, new_status, **fields)
    return new_status


def enforce_deadlines(session: Session, now: datetime) -> list[uuid.UUID]:
    """Unfinished calls on an expired job become TIMED_OUT; the job closes (FR-22)."""
    expired = (
        session.execute(
            select(SearchJob).where(
                SearchJob.status.in_(OPEN_STATUSES),
                SearchJob.deadline_at.is_not(None),
                SearchJob.deadline_at <= now,
            )
        )
        .scalars()
        .all()
    )
    attempts = AttemptRepo(session)
    closed = []
    for job in expired:
        for attempt in attempts.for_search(job.id):
            if not is_terminal(CallStatus(attempt.status)):
                attempts.update_status(attempt.id, CallStatus.TIMED_OUT, failure_reason="DEADLINE")
        refresh_job(session, job.id, now)
        closed.append(job.id)
    return closed
