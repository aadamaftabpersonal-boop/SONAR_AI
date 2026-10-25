"""Provider event intake (Bible 20.6, FR-11..13). Persist first, act second, trust nothing."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.db.repositories import AttemptRepo, EventRepo
from app.domain.enums import CallStatus
from app.domain.transitions import is_terminal, map_bolna_status
from app.services.redact import redact

log = logging.getLogger("sonar.events")

# Field locations are an ASSUMPTION (A-18) until real payloads are captured in the spike; these
# are the candidates, tried in order.
_ID_KEYS = ("execution_id", "id", "call_id")
_STATUS_KEYS = ("status", "smart_status")

ORPHAN = "ORPHAN"
DUPLICATE = "DUPLICATE"
PROGRESS = "PROGRESS"
FINALIZE = "FINALIZE"
IGNORED = "IGNORED"


@dataclass(frozen=True)
class EventOutcome:
    action: str
    attempt_id: uuid.UUID | None = None


def extract_ref(payload: dict[str, Any]) -> tuple[str | None, str | None]:
    call_id = next((str(payload[k]) for k in _ID_KEYS if payload.get(k)), None)
    status = next((str(payload[k]) for k in _STATUS_KEYS if payload.get(k)), None)
    return call_id, status


def record_event(session: Session, provider: str, payload: dict[str, Any]) -> EventOutcome:
    """Store the raw event and apply any safe, monotonic progress. Terminal statuses only ring
    the doorbell: the caller must then finalize by pulling the authoritative record."""
    call_id, raw_status = extract_ref(payload)
    attempts = AttemptRepo(session)
    attempt = attempts.by_provider_call_id(provider, call_id) if call_id else None

    # what is kept is redacted at write time: no phone numbers, no recording links (D-021)
    stored = EventRepo(session).insert_or_ignore(
        provider=provider,
        provider_call_id=call_id,
        provider_status=raw_status,
        payload=redact(payload),
        call_attempt_id=attempt.id if attempt else None,
    )
    if not stored:
        return EventOutcome(DUPLICATE, attempt.id if attempt else None)
    if attempt is None:
        return EventOutcome(ORPHAN)

    mapped = map_bolna_status(raw_status)
    if mapped is None:
        log.warning("unknown provider status %r for attempt %s", raw_status, attempt.id)
        # record the raw status for debugging; the attempt's state does not change
        attempts.update_status(attempt.id, CallStatus(attempt.status), provider_status=raw_status)
        return EventOutcome(IGNORED, attempt.id)
    if is_terminal(mapped):
        return EventOutcome(FINALIZE, attempt.id)
    attempts.update_status(attempt.id, mapped, provider_status=raw_status)
    return EventOutcome(PROGRESS, attempt.id)
