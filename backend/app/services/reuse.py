"""Database side of fresh-cache reuse (T7.4): find reusable answers and copy them into a search.

The copy is a new attempt (provider `cache`, already COMPLETED, never dialed) plus a response row
with `data_origin = CACHED_LIVE` and the original answer time. Every existing view keeps working,
live-only metrics and shop history ignore it (they filter on LIVE_CALL), and the stop rule never
counts it.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import BusinessResponse, SearchJob
from app.db.repositories import AttemptRepo, ResponseRepo
from app.domain.enums import CallStatus
from app.services.cache import PastAnswer, reusable, same_question

_COPIED = (
    "availability",
    "exact_match",
    "matched_attributes",
    "alternative_note",
    "price_amount",
    "price_currency",
    "price_note",
    "quantity_reported",
    "wait_time_minutes",
    "open_status",
    "answer_summary",
    "evidence_excerpt",
    "evidence_validated",
    "extraction_status",
    "validation_flags",
    "verification_status",
    "answer_timestamp",
    "availability_expires_at",
    "price_expires_at",
)


def find_reusable(
    session: Session,
    business_ids: list[uuid.UUID],
    query: dict,
    now: datetime,
    *,
    ttl_availability: timedelta,
    ttl_price: timedelta,
) -> dict[uuid.UUID, BusinessResponse]:
    """The newest reusable live answer per business, if any."""
    if not business_ids:
        return {}
    rows = session.execute(
        select(BusinessResponse, SearchJob.parsed_query)
        .join(SearchJob, SearchJob.id == BusinessResponse.search_job_id)
        .where(
            BusinessResponse.business_id.in_(business_ids),
            BusinessResponse.data_origin == "LIVE_CALL",
            BusinessResponse.answer_timestamp >= now - ttl_availability,
        )
        .order_by(BusinessResponse.answer_timestamp.desc())
    ).all()
    found: dict[uuid.UUID, BusinessResponse] = {}
    decided: set[uuid.UUID] = set()
    for response, past_query in rows:
        if response.business_id in decided or not same_question(past_query or {}, query):
            continue  # only a shop's newest answer to this question counts; never an older one
        decided.add(response.business_id)
        past = PastAnswer(
            data_origin=response.data_origin,
            extraction_status=response.extraction_status,
            availability=response.availability,
            exact_match=response.exact_match,
            evidence_validated=response.evidence_validated,
            price_amount=response.price_amount,
            answer_timestamp=response.answer_timestamp,
            query=past_query or {},
        )
        if reusable(past, query, now, ttl_availability=ttl_availability, ttl_price=ttl_price):
            found[response.business_id] = response
    return found


def copy_into_search(
    session: Session, job_id: uuid.UUID, source: BusinessResponse, now: datetime
) -> None:
    attempt = AttemptRepo(session).insert(
        search_job_id=job_id,
        business_id=source.business_id,
        attempt_number=1,
        provider="cache",
        provider_call_id=f"cache-{source.id}-{job_id}",
        status=CallStatus.COMPLETED,
        completed_at=now,
    )
    ResponseRepo(session).insert_once(
        call_attempt_id=attempt.id,
        search_job_id=job_id,
        business_id=source.business_id,
        data_origin="CACHED_LIVE",
        **{f: getattr(source, f) for f in _COPIED},
    )
