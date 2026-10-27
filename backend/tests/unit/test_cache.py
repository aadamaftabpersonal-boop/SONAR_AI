"""T7.4: which earlier live answers may be shown instead of a new call."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from app.services.cache import PastAnswer, reusable, same_question

NOW = datetime(2026, 11, 2, 6, 0, tzinfo=UTC)
TTL_AVAIL = timedelta(minutes=60)
TTL_PRICE = timedelta(minutes=1440)
QUERY = {
    "category": "pharmacy",
    "item_name": "Paracetamol",
    "attributes": {"strength": "500 mg"},
    "required_fields": ["availability", "price"],
}


def past(**over):
    base = {
        "data_origin": "LIVE_CALL",
        "extraction_status": "VALID",
        "availability": "REPORTED_AVAILABLE",
        "exact_match": "CONFIRMED",
        "evidence_validated": True,
        "price_amount": Decimal("42"),
        "answer_timestamp": NOW - timedelta(minutes=20),
        "query": dict(QUERY),
    }
    base.update(over)
    return PastAnswer(**base)


def ok(p, query=QUERY, now=NOW):
    return reusable(p, query, now, ttl_availability=TTL_AVAIL, ttl_price=TTL_PRICE)


def test_a_fresh_validated_live_answer_is_reused():
    assert ok(past())


def test_a_definite_no_is_reused_without_a_price():
    assert ok(past(availability="REPORTED_UNAVAILABLE", exact_match="UNKNOWN", price_amount=None))


@pytest.mark.parametrize("minutes, expected", [(59, True), (60, True), (61, False)])
def test_ttl_boundary(minutes, expected):
    assert ok(past(answer_timestamp=NOW - timedelta(minutes=minutes))) is expected


def test_a_future_timestamp_is_never_reused():
    assert not ok(past(answer_timestamp=NOW + timedelta(minutes=5)))


@pytest.mark.parametrize("origin", ["SIMULATED", "CACHED_LIVE", "SHOP_SELF_REPORT"])
def test_only_live_calls_are_reused(origin):
    assert not ok(past(data_origin=origin))


@pytest.mark.parametrize("availability", ["UNCERTAIN", "DECLINED", "ALTERNATIVE_ONLY", "NO_ANSWER"])
def test_unclear_answers_are_called_again(availability):
    assert not ok(past(availability=availability))


def test_partial_or_unvalidated_answers_are_not_reused():
    assert not ok(past(extraction_status="PARTIAL"))
    assert not ok(past(evidence_validated=False))


def test_available_needs_a_confirmed_exact_match():
    assert not ok(past(exact_match="NOT_CONFIRMED"))


def test_missing_price_is_a_miss_when_price_is_required():
    assert not ok(past(price_amount=None))
    no_price_needed = {**QUERY, "required_fields": ["availability"]}
    assert ok(past(price_amount=None), query=no_price_needed)


@pytest.mark.parametrize(
    "change",
    [
        {"attributes": {"strength": "650 mg"}},
        {"attributes": {}},
        {"item_name": "Crocin"},
        {"category": "computer_repair"},
    ],
)
def test_a_different_question_is_a_miss(change):
    assert not ok(past(), query={**QUERY, **change})


def test_case_and_spacing_do_not_matter():
    other = {**QUERY, "item_name": "  paracetamol ", "attributes": {"Strength": "500  MG"}}
    assert same_question(QUERY, other)
    assert ok(past(), query=other)
