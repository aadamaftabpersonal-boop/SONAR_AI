"""Finalizer (Bible D-005, FR-12): turn a finished call into a stored, validated result.

The webhook body is a doorbell. We never write a result from it. We pull the authoritative record
from the provider ourselves, validate it, and write once. Safe to call any number of times.
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Callable
from datetime import datetime, timedelta

from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings
from app.db.models import Business, CallAttempt, SearchJob
from app.db.repositories import (
    AttemptRepo,
    AuditRepo,
    BusinessRepo,
    ResponseRepo,
    SearchRepo,
)
from app.domain.enums import (
    CallStatus,
    ParticipationStatus,
    SearchStatus,
)
from app.domain.schemas import ParsedQuery
from app.domain.transitions import is_terminal, map_bolna_status, retry_eligible
from app.providers.base import ProviderError
from app.providers.registry import ProviderRegistry
from app.services.categories import get_categories
from app.services.jobs import refresh_job
from app.services.validator import validate

log = logging.getLogger("sonar.finalizer")

# Outcomes (returned for tests and logs)
NO_CALL_ID = "NO_CALL_ID"
PULL_FAILED = "PULL_FAILED"
UNKNOWN_STATUS = "UNKNOWN_STATUS"
NOT_READY = "NOT_READY"
FINALIZED = "FINALIZED"


def business_is_callable(business: Business) -> bool:
    return business.opted_out_at is None and business.participation_status in {
        ParticipationStatus.CONSENTED,
        ParticipationStatus.TEST_LINE,
    }


def plan_retry(
    session: Session, attempt: CallAttempt, job: SearchJob, now: datetime, settings: Settings
) -> bool:
    """Create the next attempt for an unanswered call (FR-21). Never after an answer or opt-out."""
    status = CallStatus(attempt.status)
    if not retry_eligible(status, attempt.attempt_number, settings.max_attempts_per_business):
        return False
    if job.status in {SearchStatus.CANCELLED, SearchStatus.COMPLETED, SearchStatus.FAILED}:
        return False
    if job.deadline_at is not None and now >= job.deadline_at:
        return False
    business = session.get(Business, attempt.business_id)
    if business is None or not business_is_callable(business):
        return False
    delay = timedelta(seconds=settings.retry_backoff_seconds)
    if job.deadline_at is not None and now + delay >= job.deadline_at:
        return False  # the retry could not finish before the deadline
    AttemptRepo(session).insert(
        search_job_id=job.id,
        business_id=attempt.business_id,
        attempt_number=attempt.attempt_number + 1,
        provider=attempt.provider,
        status=CallStatus.PENDING,
        not_before=now + delay,
    )
    return True


async def finalize_attempt(
    session_factory: sessionmaker[Session],
    attempt_id: uuid.UUID,
    providers: ProviderRegistry,
    settings: Settings,
    clock: Callable[[], datetime],
) -> str:
    # 1. read what we need, then release the connection before the network call
    with session_factory() as s:
        attempt = AttemptRepo(s).get(attempt_id)
        if attempt is None:
            return NO_CALL_ID
        call_id, provider_name = attempt.provider_call_id, attempt.provider
    if not call_id:
        return NO_CALL_ID

    # 2. pull the authoritative record (never trust a webhook body)
    try:
        record = await providers.get(provider_name).get_call(call_id)
    except ProviderError:
        log.warning("pull failed for attempt %s; the reconciler will retry", attempt_id)
        return PULL_FAILED

    mapped = map_bolna_status(record.provider_status)
    now = clock()
    if mapped is None:
        with session_factory() as s:
            AttemptRepo(s).update_status(
                attempt_id, CallStatus.PENDING, provider_status=record.provider_status
            )
            s.commit()
        log.warning("unknown provider status %r; left for the reconciler", record.provider_status)
        return UNKNOWN_STATUS

    # 3. write the outcome in one transaction
    with session_factory() as s:
        attempts = AttemptRepo(s)
        job = SearchRepo(s).lock(attempt_job_id(s, attempt_id))
        assert job is not None
        if not is_terminal(mapped):
            attempts.update_status(attempt_id, mapped, provider_status=record.provider_status)
            s.commit()
            return NOT_READY

        applied = attempts.update_status(
            attempt_id,
            mapped,
            provider_status=record.provider_status,
            duration_seconds=record.duration_seconds,
            cost_amount=record.cost_amount,
            cost_currency=record.cost_currency,
        )
        attempt = attempts.get(attempt_id)
        assert attempt is not None

        if mapped == CallStatus.COMPLETED:
            _store_result(s, attempt, job, record, now)
        elif applied:
            plan_retry(s, attempt, job, now, settings)

        refresh_job(s, job.id, now)
        s.commit()
    return FINALIZED


def attempt_job_id(session: Session, attempt_id: uuid.UUID) -> uuid.UUID:
    attempt = AttemptRepo(session).get(attempt_id)
    assert attempt is not None
    return attempt.search_job_id


def _store_result(
    session: Session, attempt: CallAttempt, job: SearchJob, record, now: datetime
) -> None:
    parsed = ParsedQuery.model_validate(job.parsed_query)
    price_max = get_categories()[parsed.category].price_max_plausible_inr
    answer = validate(
        provider_status=record.provider_status,
        transcript=record.transcript,
        extracted=record.extracted,
        query=parsed,
        answer_time=now,
        price_max=price_max,
    )
    attempts = AttemptRepo(session)

    if not answer.create_response:
        # voicemail / IVR / not completed: no response row, so it can never read as unavailable
        attempt.failure_reason = answer.failure_reason
        return

    written = ResponseRepo(session).insert_once(
        call_attempt_id=attempt.id,
        search_job_id=job.id,
        business_id=attempt.business_id,
        data_origin="SIMULATED" if attempt.provider == "simulated" else "LIVE_CALL",
        availability=answer.availability.value,
        exact_match=answer.exact_match.value,
        matched_attributes=answer.matched_attributes,
        alternative_note=answer.alternative_note,
        price_amount=answer.price_amount,
        price_currency=answer.price_currency,
        price_note=answer.price_note,
        quantity_reported=answer.quantity_reported,
        wait_time_minutes=answer.wait_time_minutes,
        open_status=answer.open_status,
        answer_summary=answer.answer_summary,
        evidence_excerpt=answer.evidence_excerpt,
        evidence_validated=answer.evidence_validated,
        provider_extracted=record.extracted,
        provider_confidence=answer.provider_confidence,
        extraction_status=answer.extraction_status.value,
        validation_flags=answer.validation_flags,
        answer_timestamp=now,
    )

    if answer.opt_out and written:  # only on the first write, so a repeat finalize is a no-op
        # an explicit "stop calling me" takes effect immediately and permanently (FR-24)
        BusinessRepo(session).mark_opt_out(attempt.business_id)
        cancelled = attempts.cancel_pending_for_business(attempt.business_id, "OPTED_OUT")
        AuditRepo(session).add(
            "system",
            "opt_out_recorded",
            search_job_id=job.id,
            business_id=attempt.business_id,
            detail={"cancelled_pending": cancelled},
        )
