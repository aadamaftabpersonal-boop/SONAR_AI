import pytest

from app.domain.enums import CallStatus as C
from app.domain.enums import SearchStatus as S
from app.domain.transitions import (
    RANK,
    TERMINAL,
    can_transition,
    is_terminal,
    map_bolna_status,
    retry_eligible,
    search_status_from_attempts,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("queued", C.DIALING),
        ("initiated", C.DIALING),
        ("ringing", C.RINGING),
        ("in-progress", C.IN_PROGRESS),
        ("call-disconnected", C.PROCESSING),
        ("completed", C.COMPLETED),
        ("no-answer", C.NO_ANSWER),
        ("busy", C.BUSY),
        ("failed", C.FAILED),
        ("canceled", C.CANCELLED),
        ("stopped", C.STOPPED),
        ("error", C.ERROR),
        ("balance-low", C.INSUFFICIENT_BALANCE),
        ("  COMPLETED ", C.COMPLETED),
    ],
)
def test_bolna_status_mapping(raw, expected):
    assert map_bolna_status(raw) is expected


@pytest.mark.parametrize("raw", [None, "", "weird-new-status"])
def test_unknown_status_maps_to_none(raw):
    assert map_bolna_status(raw) is None


def test_every_status_has_a_rank():
    assert set(RANK) == set(C)


def test_terminal_set():
    assert {C.COMPLETED, C.NO_ANSWER, C.BUSY, C.FAILED, C.ERROR, C.CANCELLED} <= TERMINAL
    assert C.PROCESSING not in TERMINAL
    assert not is_terminal(C.RINGING)


def test_forward_transitions_allowed_and_backward_ignored():
    assert can_transition(C.PENDING, C.DISPATCHING)
    assert can_transition(C.DIALING, C.IN_PROGRESS)
    assert can_transition(C.PROCESSING, C.COMPLETED)
    assert not can_transition(C.IN_PROGRESS, C.RINGING)
    assert not can_transition(C.RINGING, C.RINGING)


@pytest.mark.parametrize("terminal", sorted(TERMINAL))
def test_terminal_is_never_overwritten(terminal):
    for other in C:
        assert not can_transition(terminal, other)


def test_pending_can_be_cancelled():
    assert can_transition(C.PENDING, C.CANCELLED)


@pytest.mark.parametrize(
    ("status", "n", "cap", "expected"),
    [
        (C.NO_ANSWER, 1, 2, True),
        (C.BUSY, 1, 2, True),
        (C.FAILED, 1, 2, True),
        (C.NO_ANSWER, 2, 2, False),
        (C.COMPLETED, 1, 2, False),
        (C.CANCELLED, 1, 2, False),
        (C.INSUFFICIENT_BALANCE, 1, 2, False),
        (C.ERROR, 1, 2, False),
    ],
)
def test_retry_eligibility(status, n, cap, expected):
    assert retry_eligible(status, n, cap) is expected


def test_search_status_aggregation():
    assert search_status_from_attempts([C.COMPLETED, C.COMPLETED]) is S.COMPLETED
    assert search_status_from_attempts([C.COMPLETED, C.NO_ANSWER]) is S.COMPLETED_PARTIAL
    assert search_status_from_attempts([C.COMPLETED, C.RINGING]) is S.RUNNING
    assert search_status_from_attempts([C.FAILED, C.ERROR]) is S.FAILED
    assert search_status_from_attempts([C.NO_ANSWER, C.BUSY]) is S.COMPLETED_PARTIAL
    assert search_status_from_attempts([]) is S.FAILED


def test_cancel_and_deadline():
    assert search_status_from_attempts([C.RINGING], cancelled=True) is S.CANCELLED
    assert (
        search_status_from_attempts([C.COMPLETED, C.RINGING], deadline_passed=True)
        is S.COMPLETED_PARTIAL
    )
    assert search_status_from_attempts([C.PENDING], deadline_passed=True) is S.COMPLETED_PARTIAL
