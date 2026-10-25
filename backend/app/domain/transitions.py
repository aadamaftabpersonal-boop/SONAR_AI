"""Call-state rules (Bible 19.3, 27.2). Pure functions; no I/O."""

from __future__ import annotations

from collections.abc import Iterable

from app.domain.enums import CallStatus, SearchStatus

_TERMINAL_RANK = 6

RANK: dict[CallStatus, int] = {
    CallStatus.PENDING: 0,
    CallStatus.DISPATCHING: 1,
    CallStatus.DISPATCH_UNKNOWN: 1,
    CallStatus.DIALING: 2,
    CallStatus.RINGING: 3,
    CallStatus.IN_PROGRESS: 4,
    CallStatus.PROCESSING: 5,
    CallStatus.COMPLETED: _TERMINAL_RANK,
    CallStatus.NO_ANSWER: _TERMINAL_RANK,
    CallStatus.BUSY: _TERMINAL_RANK,
    CallStatus.FAILED: _TERMINAL_RANK,
    CallStatus.ERROR: _TERMINAL_RANK,
    CallStatus.CANCELLED: _TERMINAL_RANK,
    CallStatus.STOPPED: _TERMINAL_RANK,
    CallStatus.INSUFFICIENT_BALANCE: _TERMINAL_RANK,
    CallStatus.TIMED_OUT: _TERMINAL_RANK,
}

TERMINAL: frozenset[CallStatus] = frozenset(s for s, r in RANK.items() if r == _TERMINAL_RANK)

# Bolna status strings (VERIFIED from the call-flow page 2026-10-24; real payloads in the spike
# override this table). An unknown value maps to None: the caller logs it and leaves the attempt
# non-terminal for the reconciler.
_BOLNA_STATUS: dict[str, CallStatus] = {
    "queued": CallStatus.DIALING,
    "initiated": CallStatus.DIALING,
    "ringing": CallStatus.RINGING,
    "in-progress": CallStatus.IN_PROGRESS,
    "call-disconnected": CallStatus.PROCESSING,
    "completed": CallStatus.COMPLETED,
    "no-answer": CallStatus.NO_ANSWER,
    "busy": CallStatus.BUSY,
    "failed": CallStatus.FAILED,
    "canceled": CallStatus.CANCELLED,
    "stopped": CallStatus.STOPPED,
    "error": CallStatus.ERROR,
    "balance-low": CallStatus.INSUFFICIENT_BALANCE,
}


def map_bolna_status(raw: str | None) -> CallStatus | None:
    if not raw:
        return None
    return _BOLNA_STATUS.get(raw.strip().lower())


def is_terminal(status: CallStatus) -> bool:
    return status in TERMINAL


def can_transition(current: CallStatus, new: CallStatus) -> bool:
    """Monotonic: only forward in rank, and a terminal status is never overwritten."""
    if is_terminal(current):
        return False
    return RANK[new] > RANK[current]


def retry_eligible(status: CallStatus, attempt_number: int, max_attempts: int) -> bool:
    """Retry only unanswered or transiently failed calls, never after an answer (FR-21)."""
    if attempt_number >= max_attempts:
        return False
    return status in {CallStatus.NO_ANSWER, CallStatus.BUSY, CallStatus.FAILED}


def search_status_from_attempts(
    statuses: Iterable[CallStatus], *, cancelled: bool = False, deadline_passed: bool = False
) -> SearchStatus:
    """Aggregate a job's status from its attempts' latest statuses."""
    if cancelled:
        return SearchStatus.CANCELLED
    effective = list(statuses)
    if not effective:
        return SearchStatus.FAILED
    if deadline_passed:
        effective = [s if is_terminal(s) else CallStatus.TIMED_OUT for s in effective]
    if any(not is_terminal(s) for s in effective):
        return SearchStatus.RUNNING
    if all(s == CallStatus.COMPLETED for s in effective):
        return SearchStatus.COMPLETED
    if any(s == CallStatus.COMPLETED for s in effective):
        return SearchStatus.COMPLETED_PARTIAL
    hard_failures = {CallStatus.FAILED, CallStatus.ERROR, CallStatus.INSUFFICIENT_BALANCE}
    if all(s in hard_failures for s in effective):
        return SearchStatus.FAILED
    return SearchStatus.COMPLETED_PARTIAL
