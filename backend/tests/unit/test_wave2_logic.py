import random
from datetime import UTC, datetime

import pytest

from app.domain.enums import Availability as A
from app.domain.enums import CallStatus as C
from app.services.priors import Scored, order, score
from app.services.stats import StatsData, apply_outcome
from app.services.stoprule import Confirmation, counts_as_confirmation, satisfied

# 11:00 IST
NOW = datetime(2026, 11, 2, 5, 30, tzinfo=UTC)

# --- stats -----------------------------------------------------------------------------------


def test_answered_available_call():
    s = apply_outcome(
        StatsData(),
        status=C.COMPLETED,
        availability=A.REPORTED_AVAILABLE,
        duration_seconds=40,
        now=NOW,
    )
    assert (s.attempts, s.connected, s.completed, s.reported_available) == (1, 1, 1, 1)
    assert s.total_duration_seconds == 40 and s.last_attempt_at == NOW
    assert s.hour_bucket_stats == {"11": {"attempts": 1, "connected": 1}}


@pytest.mark.parametrize(
    ("availability", "field"),
    [
        (A.REPORTED_UNAVAILABLE, "reported_unavailable"),
        (A.UNCERTAIN, "uncertain"),
        (A.ALTERNATIVE_ONLY, "uncertain"),
        (A.DECLINED, "declined"),
    ],
)
def test_each_answer_kind_has_its_own_counter(availability, field):
    s = apply_outcome(
        StatsData(), status=C.COMPLETED, availability=availability, duration_seconds=10, now=NOW
    )
    assert getattr(s, field) == 1 and s.connected == 1


@pytest.mark.parametrize("status", [C.NO_ANSWER, C.BUSY])
def test_silence_counts_as_an_attempt_but_not_a_connection(status):
    s = apply_outcome(StatsData(), status=status, availability=None, duration_seconds=None, now=NOW)
    assert (s.attempts, s.no_answer, s.connected) == (1, 1, 0)
    assert s.hour_bucket_stats["11"] == {"attempts": 1, "connected": 0}


def test_voicemail_is_completed_but_not_a_connection():
    s = apply_outcome(
        StatsData(), status=C.COMPLETED, availability=None, duration_seconds=8, now=NOW
    )
    assert (s.attempts, s.completed, s.connected) == (1, 1, 0)


@pytest.mark.parametrize(
    "status",
    [C.FAILED, C.ERROR, C.CANCELLED, C.TIMED_OUT, C.INSUFFICIENT_BALANCE, C.STOPPED],
)
def test_provider_failures_are_not_the_shops_fault(status):
    original = StatsData()
    assert (
        apply_outcome(original, status=status, availability=None, duration_seconds=None, now=NOW)
        is original
    )


def test_apply_does_not_mutate_the_input():
    before = StatsData()
    apply_outcome(before, status=C.NO_ANSWER, availability=None, duration_seconds=None, now=NOW)
    assert before.attempts == 0 and before.hour_bucket_stats == {}


def test_answered_property_excludes_silence():
    s = StatsData(reported_available=3, uncertain=1, no_answer=9, attempts=13)
    assert s.answered == 4


# --- priors ----------------------------------------------------------------------------------


def sc(stats, hour=11, distance=1.0, radius=5.0, min_obs=5):
    return score(
        stats, hour_ist=hour, distance_km=distance, radius_km=radius, min_observations=min_obs
    )


def test_cold_start_orders_by_distance_only():
    near, _ = sc(None, distance=0.5)
    far, snap = sc(None, distance=4.0)
    assert near > far and snap["source"] == "cold_start"
    # a shop with too little history is also treated as cold
    few = StatsData(attempts=2, connected=2, reported_available=2)
    assert sc(few)[1]["source"] == "cold_start"


def test_a_reliable_shop_outranks_an_unreliable_one_at_equal_distance():
    good = StatsData(attempts=10, connected=9, completed=9, reported_available=8)
    bad = StatsData(attempts=10, connected=1, completed=1, reported_available=0)
    assert sc(good)[0] > sc(bad)[0]


def test_the_current_hour_is_used_when_there_is_enough_data():
    stats = StatsData(
        attempts=10,
        connected=8,
        hour_bucket_stats={
            "11": {"attempts": 4, "connected": 0},
            "15": {"attempts": 6, "connected": 6},
        },
    )
    morning, m = sc(stats, hour=11)
    afternoon, a = sc(stats, hour=15)
    assert m["source"] == "hour_bucket" and a["source"] == "hour_bucket"
    assert afternoon > morning


def test_a_sparse_hour_falls_back_to_the_overall_rate():
    stats = StatsData(
        attempts=10, connected=8, hour_bucket_stats={"11": {"attempts": 1, "connected": 0}}
    )
    assert sc(stats, hour=11)[1]["source"] == "overall"


def test_one_bad_call_cannot_bury_a_shop():
    one_miss = StatsData(attempts=5, connected=0, no_answer=5)
    value, _ = sc(one_miss)
    assert value > 0.15  # smoothing keeps the floor above zero


def test_score_is_bounded_and_records_its_inputs():
    perfect = StatsData(attempts=1000, connected=1000, reported_available=1000)
    value, snap = sc(perfect, distance=0.0)
    assert 0.0 <= value <= 1.0
    assert set(snap) == {
        "source",
        "connect_rate",
        "positive_rate",
        "proximity",
        "attempts",
        "hour_ist",
    }


def test_proximity_never_goes_negative():
    assert sc(None, distance=50, radius=5)[1]["proximity"] == 0.0


def test_scores_are_monotone_in_the_positive_rate():
    values = [
        sc(StatsData(attempts=20, connected=20, reported_available=k))[0] for k in (0, 5, 10, 20)
    ]
    assert values == sorted(values) and len(set(values)) == len(values)


def scored(n=8):
    return [Scored(f"s{i}", 0.9 - i * 0.05, float(i)) for i in range(n)]


def test_order_without_exploration_is_best_first_and_stable():
    items = scored()
    shuffled = random.Random(1).sample(items, len(items))
    assert [c.key for c in order(shuffled, 0.0, random.Random(0))] == [c.key for c in items]


def test_order_breaks_ties_by_distance_then_key():
    tied = [Scored("b", 0.5, 2.0), Scored("a", 0.5, 2.0), Scored("c", 0.5, 1.0)]
    assert [c.key for c in order(tied, 0.0, random.Random(0))] == ["c", "a", "b"]


def test_exploration_promotes_a_lower_ranked_shop_at_roughly_the_configured_rate():
    promoted = 0
    trials = 4000
    for seed in range(trials):
        first = order(scored(), 0.15, random.Random(seed))[0]
        promoted += first.key != "s0"
    assert 0.10 < promoted / trials < 0.20


def test_exploration_is_deterministic_for_a_seed_and_loses_nobody():
    a = order(scored(), 0.5, random.Random(7))
    b = order(scored(), 0.5, random.Random(7))
    assert a == b and {c.key for c in a} == {c.key for c in scored()}


def test_order_handles_empty_and_single():
    assert order([], 0.5, random.Random(0)) == []
    one = [Scored("x", 0.5, 1.0)]
    assert order(one, 1.0, random.Random(0)) == one


# --- stop rule -------------------------------------------------------------------------------


def conf(name="a", **over):
    fields = {
        "business_id": name,
        "data_origin": "LIVE_CALL",
        "availability": "REPORTED_AVAILABLE",
        "exact_match": "CONFIRMED",
        "evidence_validated": True,
        "price_present": True,
    }
    fields.update(over)
    return Confirmation(**fields)


def sat(items, k=2, require_price=True, allow_simulated=False):
    return satisfied(items, k=k, require_price=require_price, allow_simulated=allow_simulated)


def test_two_distinct_confirmations_satisfy_k2():
    assert sat([conf("a"), conf("b")])
    assert not sat([conf("a")])


def test_two_answers_from_the_same_shop_count_once():
    assert not sat([conf("a"), conf("a")])


@pytest.mark.parametrize(
    "over",
    [
        {"availability": "REPORTED_UNAVAILABLE"},
        {"availability": "UNCERTAIN"},
        {"availability": "ALTERNATIVE_ONLY"},
        {"availability": "DECLINED"},
        {"exact_match": "UNKNOWN"},
        {"exact_match": "NOT_CONFIRMED"},
        {"evidence_validated": False},
        {"price_present": False},
        {"data_origin": "CACHED_LIVE"},
        {"data_origin": "SHOP_SELF_REPORT"},
    ],
)
def test_only_a_fully_validated_positive_counts(over):
    assert not counts_as_confirmation(conf(**over), require_price=True, allow_simulated=False)


def test_price_is_only_required_when_the_search_asked_for_it():
    no_price = [conf("a", price_present=False), conf("b", price_present=False)]
    assert not sat(no_price, require_price=True)
    assert sat(no_price, require_price=False)


def test_simulated_answers_never_satisfy_a_live_job_but_can_satisfy_a_demo():
    sim = [conf("a", data_origin="SIMULATED"), conf("b", data_origin="SIMULATED")]
    assert not sat(sim, allow_simulated=False)
    assert sat(sim, allow_simulated=True)


def test_negatives_alone_never_satisfy_however_many_there_are():
    negatives = [conf(str(i), availability="REPORTED_UNAVAILABLE") for i in range(50)]
    assert not sat(negatives, k=1)


@pytest.mark.parametrize(("k", "have", "expected"), [(1, 1, True), (3, 2, False), (3, 3, True)])
def test_k_boundaries(k, have, expected):
    assert sat([conf(str(i)) for i in range(have)], k=k) is expected


def test_empty_never_satisfies():
    assert not sat([], k=1)
