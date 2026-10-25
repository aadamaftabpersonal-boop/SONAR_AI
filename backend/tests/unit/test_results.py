from datetime import UTC, datetime, timedelta

import pytest

from app.domain.enums import Availability as A
from app.domain.enums import BusinessKind, CallStatus, DataOrigin, Freshness, ResultState
from app.domain.schemas import BusinessRef, ReportedPrice
from app.domain.schemas import Reported as Rep
from app.services.freshness import field_freshness
from app.services.result_copy import LABELS, NOT_UNAVAILABLE, NOTES
from app.services.results import (
    TIER,
    derive_result_state,
    sort_results,
    view_without_response,
)

NOW = datetime(2026, 11, 2, 6, 0, tzinfo=UTC)
TTL = timedelta(minutes=60)


# --- freshness -----------------------------------------------------------------------------


def test_fresh_exactly_at_ttl_and_stale_just_after():
    assert field_freshness(True, NOW - TTL, NOW, TTL) is Freshness.FRESH
    assert field_freshness(True, NOW - TTL - timedelta(seconds=1), NOW, TTL) is Freshness.STALE


def test_missing_field_is_unknown_not_stale():
    assert field_freshness(False, NOW - timedelta(days=9), NOW, TTL) is Freshness.UNKNOWN


def test_future_timestamp_counts_as_fresh():
    assert field_freshness(True, NOW + timedelta(minutes=5), NOW, TTL) is Freshness.FRESH


# --- result state derivation ----------------------------------------------------------------

IN_FLIGHT = [
    CallStatus.PENDING,
    CallStatus.DISPATCHING,
    CallStatus.DISPATCH_UNKNOWN,
    CallStatus.DIALING,
    CallStatus.RINGING,
    CallStatus.IN_PROGRESS,
    CallStatus.PROCESSING,
]


@pytest.mark.parametrize("status", IN_FLIGHT)
def test_in_flight_calls_are_pending(status):
    assert derive_result_state(status, None) is ResultState.PENDING


@pytest.mark.parametrize("status", [CallStatus.NO_ANSWER, CallStatus.BUSY])
def test_unanswered_is_no_answer(status):
    assert derive_result_state(status, None) is ResultState.NO_ANSWER


@pytest.mark.parametrize(
    "status",
    [
        CallStatus.FAILED,
        CallStatus.ERROR,
        CallStatus.STOPPED,
        CallStatus.INSUFFICIENT_BALANCE,
        CallStatus.TIMED_OUT,
    ],
)
def test_failures_are_call_failed(status):
    assert derive_result_state(status, None) is ResultState.CALL_FAILED


def test_completed_without_a_response_is_no_answer_never_unavailable():
    assert derive_result_state(CallStatus.COMPLETED, None) is ResultState.NO_ANSWER


def test_cancelled_by_stop_rule_is_distinct_from_user_cancel():
    assert (
        derive_result_state(CallStatus.CANCELLED, None, "STOP_RULE_SATISFIED")
        is ResultState.NOT_CALLED_STOP_RULE
    )
    assert derive_result_state(CallStatus.CANCELLED, None, None) is ResultState.CANCELLED


@pytest.mark.parametrize("availability", list(A))
def test_response_availability_maps_one_to_one(availability):
    assert derive_result_state(CallStatus.COMPLETED, availability).value == availability.value


def test_only_an_explicit_response_can_yield_unavailable():
    """Exhaustive: no call status without a response may produce REPORTED_UNAVAILABLE."""
    for status in CallStatus:
        for reason in (None, "STOP_RULE_SATISFIED", "NO_HUMAN"):
            assert derive_result_state(status, None, reason) is not ResultState.REPORTED_UNAVAILABLE
    assert (
        derive_result_state(CallStatus.COMPLETED, A.REPORTED_UNAVAILABLE)
        is ResultState.REPORTED_UNAVAILABLE
    )


# --- copy (NFR-09) --------------------------------------------------------------------------

MUST_NOT_CLAIM_UNAVAILABLE = [
    ResultState.NO_ANSWER,
    ResultState.CALL_FAILED,
    ResultState.DECLINED,
    ResultState.PENDING,
    ResultState.CANCELLED,
    ResultState.UNCERTAIN,
    ResultState.NOT_CALLED_STOP_RULE,
    ResultState.ALTERNATIVE_ONLY,
]


@pytest.mark.parametrize("state", MUST_NOT_CLAIM_UNAVAILABLE)
def test_copy_never_claims_unavailability(state):
    text = f"{LABELS[state]} {NOTES.get(state, '')}".replace(NOT_UNAVAILABLE, "").lower()
    assert "unavailable" not in text
    assert "out of stock" not in text
    assert "not available" not in text


@pytest.mark.parametrize(
    "state",
    [
        ResultState.NO_ANSWER,
        ResultState.CALL_FAILED,
        ResultState.DECLINED,
        ResultState.CANCELLED,
        ResultState.UNCERTAIN,
        ResultState.NOT_CALLED_STOP_RULE,
    ],
)
def test_silent_or_skipped_states_say_they_are_not_unavailability(state):
    assert NOT_UNAVAILABLE in NOTES[state]


def test_every_state_has_a_label_and_a_tier():
    assert set(LABELS) == set(ResultState)
    assert set(TIER) == set(ResultState)


# --- ranking --------------------------------------------------------------------------------


def biz(name, distance):
    return BusinessRef(
        id=__import__("uuid").uuid4(),
        name=name,
        kind=BusinessKind.REAL_BUSINESS,
        distance_km=distance,
    )


def view(name, state, distance, price=None):
    v = view_without_response(state, biz(name, distance), DataOrigin.LIVE_CALL)
    if price is not None:
        v.reported = Rep(price=ReportedPrice(amount=price, currency="INR"))
    return v


def test_tier_order_is_available_then_uncertain_then_unavailable_then_unanswered():
    items = [
        view("noans", ResultState.NO_ANSWER, 0.1),
        view("unavail", ResultState.REPORTED_UNAVAILABLE, 0.2),
        view("uncertain", ResultState.UNCERTAIN, 0.3),
        view("alt", ResultState.ALTERNATIVE_ONLY, 0.4),
        view("avail", ResultState.REPORTED_AVAILABLE, 5.0),
    ]
    assert [v.business.name for v in sort_results(items)] == [
        "avail",
        "alt",
        "uncertain",
        "unavail",
        "noans",
    ]


def test_within_a_tier_nearer_first_then_priced_before_unpriced():
    items = [
        view("far", ResultState.REPORTED_AVAILABLE, 2.0, price=10),
        view("near-priced", ResultState.REPORTED_AVAILABLE, 1.0, price=50),
        view("near-cheaper", ResultState.REPORTED_AVAILABLE, 1.0, price=40),
        view("near-unpriced", ResultState.REPORTED_AVAILABLE, 1.0),
    ]
    assert [v.business.name for v in sort_results(items)] == [
        "near-cheaper",
        "near-priced",
        "near-unpriced",
        "far",
    ]


def test_uncertain_never_outranks_a_reported_available():
    items = [view("u", ResultState.UNCERTAIN, 0.01), view("a", ResultState.REPORTED_AVAILABLE, 20)]
    assert sort_results(items)[0].business.name == "a"
