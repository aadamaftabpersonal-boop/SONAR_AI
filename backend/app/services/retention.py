"""Data minimisation (Bible NFR-13, 30): nothing sensitive is kept longer than it is useful.

Raw provider events can contain transcripts, so they are deleted after a short window. Old call
excerpts are cleared, but the row stays so the numbers (counts, costs, outcomes) remain true.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from sqlalchemy import delete, null, select
from sqlalchemy.orm import Session

from app.db.models import (
    BusinessResponse,
    BusinessStats,
    CallAttempt,
    ProviderEvent,
)
from app.db.repositories import AuditRepo

PURGED_FLAG = "RETENTION_PURGED"


def purge_old(
    session: Session, now: datetime, *, event_days: int, response_days: int
) -> dict[str, int]:
    events = session.execute(
        delete(ProviderEvent).where(ProviderEvent.received_at < now - timedelta(days=event_days))
    ).rowcount

    cleared = 0
    old = session.execute(
        select(BusinessResponse).where(
            BusinessResponse.created_at < now - timedelta(days=response_days),
            (BusinessResponse.evidence_excerpt.is_not(None))
            | (BusinessResponse.provider_extracted.is_not(None)),
        )
    ).scalars()
    for response in old:
        response.evidence_excerpt = None
        # a JSONB column given Python None stores the JSON value null, which is not SQL NULL and
        # would make this row match again on every run; null() writes a real NULL
        response.provider_extracted = null()
        flags = list(response.validation_flags or [])
        if PURGED_FLAG not in flags:
            response.validation_flags = [*flags, PURGED_FLAG]
        cleared += 1
    session.flush()
    return {"events_deleted": events, "responses_cleared": cleared}


def delete_business_data(session: Session, business_id: uuid.UUID) -> dict[str, int]:
    """Remove what we hold about a shop's calls (its answers, raw events, history) on request.

    The business row and its opt-out stay, so a shop that asked to be forgotten is never called
    again, and the audit trail records that the deletion happened (without the content)."""
    attempt_rows = session.execute(
        select(CallAttempt.id, CallAttempt.provider, CallAttempt.provider_call_id).where(
            CallAttempt.business_id == business_id
        )
    ).all()
    attempt_ids = [r.id for r in attempt_rows]
    call_ids = [r.provider_call_id for r in attempt_rows if r.provider_call_id]

    events = 0
    if attempt_ids:
        events += session.execute(
            delete(ProviderEvent).where(ProviderEvent.call_attempt_id.in_(attempt_ids))
        ).rowcount
    if call_ids:  # events that arrived before the call id was stored
        events += session.execute(
            delete(ProviderEvent).where(ProviderEvent.provider_call_id.in_(call_ids))
        ).rowcount
    responses = session.execute(
        delete(BusinessResponse).where(BusinessResponse.business_id == business_id)
    ).rowcount  # ground-truth checks go with them (ON DELETE CASCADE)
    stats = session.execute(
        delete(BusinessStats).where(BusinessStats.business_id == business_id)
    ).rowcount
    AuditRepo(session).add(
        "cli:delete_business_data",
        "business_data_deleted",
        business_id=business_id,
        detail={"responses": responses, "events": events, "stats": stats},
    )
    session.flush()
    return {"responses": responses, "events": events, "stats": stats}
