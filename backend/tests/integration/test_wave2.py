# ruff: noqa: F811, F401  (pytest fixtures are imported from test_pipeline and used by name)
"""Wave 2 Phase 14: stop rule, shop history and prior ordering, on the simulator and stubs."""

from __future__ import annotations

import asyncio

import pytest
from sqlalchemy import func, select

from app.db.models import AuditEvent, BusinessResponse, BusinessStats, CallAttempt, SearchJob
from app.db.repositories import StatsRepo
from app.domain.enums import Availability
from app.services.finalizer import finalize_attempt
from app.services.stats import StatsData
from tests.factories import make_attempt
from tests.integration.test_pipeline import (  # noqa: F401  (fixtures and helpers)
    LAT,
    LNG,
    NOW,
    H,
    StubProvider,
    bolna_attempt,
    clock,
    completed_record,
    providers,
    results_by_name,
    run_to_completion,
    search_body,
    settings,
    shop,
    world,
)

pytestmark = pytest.mark.integration


def make_shops(world, n, scenario="available", start=30000, **over):
    sim = world.providers.get("simulated")
    shops = []
    for i in range(n):
        phone = f"+91000{start + i}"
        shops.append(shop(world.session, f"Shop{i}", phone, dlat=0.001 * (i + 1), **over))
        sim._by_phone[phone] = scenario
    return shops


def create(world, **body):
    r = world.client.post("/api/searches", json=search_body(**body), headers=H)
    assert r.status_code in (200, 202), r.text
    return r.json()


def job_row(world, sid):
    world.session.expire_all()
    return world.session.get(SearchJob, sid)


def attempts_of(world, sid):
    world.session.expire_all()
    return (
        world.session.execute(select(CallAttempt).where(CallAttempt.search_job_id == sid))
        .scalars()
        .all()
    )


# --- the stop rule ---------------------------------------------------------------------------


async def test_search_stops_once_two_shops_confirm_and_skips_the_rest(world):
    world.settings.feature_stop_rule = True
    world.settings.max_attempts_per_business = 1
    make_shops(world, 6)  # a search plans at most MAX_TARGETS_PER_SEARCH (5) shops
    sid = create(world)["search_id"]

    status = await run_to_completion(world, sid)

    assert status == "COMPLETED"  # skipping shops on purpose is not "partial"
    assert world.providers.get("simulated").calls_started == 2
    job = job_row(world, sid)
    assert job.stopped_early and job.calls_avoided == 3 and job.mode == "FAST"
    data = world.client.get(f"/api/searches/{sid}").json()
    assert data["stopped_early"] is True and data["calls_avoided"] == 3
    states = [
        r["result_state"]
        for r in world.client.get(f"/api/searches/{sid}/results").json()["results"]
    ]
    assert states.count("REPORTED_AVAILABLE") == 2 and states.count("NOT_CALLED_STOP_RULE") == 3


async def test_skipped_shops_are_never_called_unavailable(world):
    world.settings.feature_stop_rule = True
    world.settings.max_attempts_per_business = 1
    make_shops(world, 5)
    sid = create(world)["search_id"]
    await run_to_completion(world, sid)
    results = world.client.get(f"/api/searches/{sid}/results").json()["results"]
    skipped = [r for r in results if r["result_state"] == "NOT_CALLED_STOP_RULE"]
    assert skipped
    for r in skipped:
        assert "does not mean the item is unavailable" in r["note"]
        assert r["reported"] is None and r["evidence"] is None
    assert "REPORTED_UNAVAILABLE" not in {r["result_state"] for r in results}


async def test_negative_answers_never_stop_a_search(world):
    world.settings.feature_stop_rule = True
    world.settings.max_attempts_per_business = 1
    make_shops(world, 5, scenario="unavailable")
    sid = create(world)["search_id"]
    assert await run_to_completion(world, sid) == "COMPLETED"
    assert world.providers.get("simulated").calls_started == 5
    assert not job_row(world, sid).stopped_early


async def test_hedged_and_silent_shops_never_stop_a_search(world):
    world.settings.feature_stop_rule = True
    world.settings.max_attempts_per_business = 1
    sim = world.providers.get("simulated")
    for i, scenario in enumerate(["ambiguous", "no_answer", "alternative_only", "ambiguous"]):
        phone = f"+91000{31000 + i}"
        shop(world.session, f"S{i}", phone, dlat=0.001 * (i + 1))
        sim._by_phone[phone] = scenario
    sid = create(world)["search_id"]
    await run_to_completion(world, sid)
    assert world.providers.get("simulated").calls_started == 4
    assert not job_row(world, sid).stopped_early


async def test_mixed_answers_stop_only_on_the_second_positive(world):
    world.settings.feature_stop_rule = True
    world.settings.max_attempts_per_business = 1
    world.settings.max_concurrent_calls = 1  # strictly one at a time, so order is observable
    world.settings.prior_exploration_epsilon = 0.0
    sim = world.providers.get("simulated")
    plan = ["unavailable", "available", "no_answer", "available", "available", "available"]
    for i, scenario in enumerate(plan):
        phone = f"+91000{32000 + i}"
        shop(world.session, f"S{i}", phone, dlat=0.001 * (i + 1))
        sim._by_phone[phone] = scenario
    sid = create(world)["search_id"]
    await run_to_completion(world, sid)
    # nearest first: S0 no, S1 yes, S2 silent, S3 yes -> stop; S4 and S5 skipped
    assert sim.calls_started == 4
    assert job_row(world, sid).calls_avoided == 1  # only 5 shops are planned; S4 is skipped


async def test_thorough_mode_calls_everyone_even_when_enough_confirmed(world):
    world.settings.feature_stop_rule = True
    world.settings.max_attempts_per_business = 1
    make_shops(world, 5)
    sid = create(world, mode="THOROUGH")["search_id"]
    await run_to_completion(world, sid)
    assert world.providers.get("simulated").calls_started == 5
    job = job_row(world, sid)
    assert job.mode == "THOROUGH" and not job.stopped_early and job.stop_rule is None


async def test_with_the_feature_off_every_shop_is_called_as_before(world):
    assert world.settings.feature_stop_rule is False
    world.settings.max_attempts_per_business = 1
    make_shops(world, 5)
    sid = create(world)["search_id"]
    await run_to_completion(world, sid)
    assert world.providers.get("simulated").calls_started == 5
    assert not job_row(world, sid).stopped_early
    assert all(a.priority_score is None for a in attempts_of(world, sid))


async def test_simulated_answers_cannot_stop_a_live_job(world):
    """A non-demo job whose answers are simulated must not satisfy the rule (D-022)."""
    world.settings.feature_stop_rule = True
    world.settings.max_attempts_per_business = 1
    stub: StubProvider = world.providers.get("bolna")
    stub.record = completed_record()
    job, biz, att = bolna_attempt(
        world, "A", "+910000033001", status="DIALING", provider_call_id="stub-1"
    )
    job.stop_rule = {"k": 1}
    world.session.commit()
    pending = make_attempt(
        world.session, job, shop(world.session, "B", "+910000033002"), provider="bolna"
    )
    # a SIMULATED response in a non-demo job
    world.session.add(
        BusinessResponse(
            call_attempt_id=make_attempt(
                world.session,
                job,
                shop(world.session, "C", "+910000033003"),
                status="COMPLETED",
                provider="simulated",
            ).id,
            search_job_id=job.id,
            business_id=biz.id,
            data_origin="SIMULATED",
            availability="REPORTED_AVAILABLE",
            exact_match="CONFIRMED",
            answer_summary="x",
            evidence_validated=True,
            extraction_status="VALID",
            price_amount=42,
            answer_timestamp=NOW,
        )
    )
    world.session.commit()
    await finalize_attempt(world.sf, att.id, world.providers, world.settings, world.clock)
    world.session.expire_all()
    # K=1 and a live positive now exists, so the rule fires; the simulated row alone must not
    assert job_row(world, job.id).stopped_early
    assert world.session.get(CallAttempt, pending.id).status == "CANCELLED"


async def test_two_confirmations_finishing_together_stop_the_search_exactly_once(world):
    world.settings.feature_stop_rule = True
    stub: StubProvider = world.providers.get("bolna")
    stub.record = completed_record()
    job, _, a1 = bolna_attempt(
        world, "A", "+910000034001", status="DIALING", provider_call_id="stub-1"
    )
    job.stop_rule = {"k": 2}
    world.session.commit()
    a2 = make_attempt(
        world.session,
        job,
        shop(world.session, "B", "+910000034002"),
        provider="bolna",
        status="DIALING",
        provider_call_id="stub-2",
    )
    for i in range(3):
        make_attempt(
            world.session, job, shop(world.session, f"P{i}", f"+91000003500{i}"), provider="bolna"
        )
    await asyncio.gather(
        *(
            finalize_attempt(world.sf, a.id, world.providers, world.settings, world.clock)
            for a in (a1, a2)
        )
    )
    world.session.expire_all()
    j = job_row(world, job.id)
    assert j.stopped_early and j.calls_avoided == 3
    audits = world.session.execute(
        select(func.count())
        .select_from(AuditEvent)
        .where(AuditEvent.action == "stop_rule_satisfied")
    ).scalar_one()
    assert audits == 1


async def test_nothing_left_to_skip_is_not_an_early_stop(world):
    world.settings.feature_stop_rule = True
    stub: StubProvider = world.providers.get("bolna")
    stub.record = completed_record()
    job, _, a1 = bolna_attempt(
        world, "A", "+910000036001", status="DIALING", provider_call_id="stub-1"
    )
    job.stop_rule = {"k": 1}
    world.session.commit()
    await finalize_attempt(world.sf, a1.id, world.providers, world.settings, world.clock)
    assert not job_row(world, job.id).stopped_early


async def test_a_price_is_required_only_when_the_search_asked_for_it(world):
    world.settings.feature_stop_rule = True
    world.settings.max_attempts_per_business = 1
    make_shops(world, 5, scenario="available_no_price")
    sid = create(world)["search_id"]  # required fields default to availability + price
    await run_to_completion(world, sid)
    assert world.providers.get("simulated").calls_started == 5  # no price, so nobody counted
    assert not job_row(world, sid).stopped_early


# --- ordering from history -------------------------------------------------------------------


def seed_history(world, business, **fields):
    StatsRepo(world.session).update(business.id, lambda _: StatsData(**fields))
    world.session.commit()


async def test_the_shop_most_likely_to_help_is_called_first(world):
    world.settings.feature_stop_rule = True
    world.settings.prior_exploration_epsilon = 0.0
    far_reliable = shop(world.session, "Reliable", "+910000037001", dlat=0.02)
    near_flaky = shop(world.session, "Flaky", "+910000037002", dlat=0.001)
    seed_history(
        world,
        far_reliable,
        attempts=12,
        connected=11,
        completed=11,
        reported_available=10,
        uncertain=1,
    )
    seed_history(
        world,
        near_flaky,
        attempts=12,
        connected=1,
        completed=1,
        no_answer=11,
        reported_unavailable=1,
    )
    data = create(world)
    assert [t["name"] for t in data["planned_targets"]] == ["Reliable", "Flaky"]
    atts = {a.business_id: a for a in attempts_of(world, data["search_id"])}
    assert atts[far_reliable.id].priority_score > atts[near_flaky.id].priority_score
    snap = atts[far_reliable.id].prior_snapshot
    assert snap["source"] in {"overall", "hour_bucket"} and snap["attempts"] == 12


async def test_dispatch_follows_priority_not_insertion_order(world):
    world.settings.feature_stop_rule = True
    world.settings.prior_exploration_epsilon = 0.0
    world.settings.max_concurrent_calls = 1
    sim = world.providers.get("simulated")
    good = shop(world.session, "Good", "+910000038001", dlat=0.02)
    bad = shop(world.session, "Bad", "+910000038002", dlat=0.001)
    seed_history(world, good, attempts=10, connected=10, reported_available=10)
    seed_history(world, bad, attempts=10, connected=0, no_answer=10)
    create(world)
    await world.orch.dispatch_one()
    first = (
        world.session.execute(select(CallAttempt).where(CallAttempt.status != "PENDING"))
        .scalars()
        .one()
    )
    world.session.refresh(first)
    assert first.business_id == good.id and sim.calls_started == 1
    await world.orch.drain()


async def test_cold_start_shops_are_ordered_nearest_first(world):
    world.settings.feature_stop_rule = True
    world.settings.prior_exploration_epsilon = 0.0
    make_shops(world, 4)
    names = [t["name"] for t in create(world)["planned_targets"]]
    assert names == ["Shop0", "Shop1", "Shop2", "Shop3"]


async def test_exploration_sometimes_tries_a_lower_ranked_shop_first(world):
    world.settings.feature_stop_rule = True
    world.settings.prior_exploration_epsilon = 1.0  # always explore, so the top is never first
    make_shops(world, 5)
    data = create(world)
    atts = attempts_of(world, data["search_id"])
    assert any(a.prior_snapshot["explored"] for a in atts)
    assert data["planned_targets"][0]["name"] != "Shop0"


# --- shop history is recorded correctly ------------------------------------------------------


async def test_calls_update_the_shops_history_when_enabled(world):
    world.settings.feature_stop_rule = True
    world.settings.stats_include_simulated = True
    world.settings.max_attempts_per_business = 1
    sim = world.providers.get("simulated")
    yes = shop(world.session, "Yes", "+910000039001", dlat=0.001)
    silent = shop(world.session, "Silent", "+910000039002", dlat=0.002)
    sim._by_phone.update({"+910000039001": "available", "+910000039002": "no_answer"})
    sid = create(world, mode="THOROUGH")["search_id"]
    await run_to_completion(world, sid)
    world.session.expire_all()
    y = world.session.get(BusinessStats, yes.id)
    s = world.session.get(BusinessStats, silent.id)
    assert (y.attempts, y.connected, y.reported_available) == (1, 1, 1)
    assert (s.attempts, s.connected, s.no_answer) == (1, 0, 1)


async def test_simulated_runs_do_not_touch_history_by_default(world):
    world.settings.feature_stop_rule = True
    assert world.settings.stats_include_simulated is False
    world.settings.max_attempts_per_business = 1
    make_shops(world, 2)
    sid = create(world, mode="THOROUGH")["search_id"]
    await run_to_completion(world, sid)
    assert world.session.execute(select(func.count()).select_from(BusinessStats)).scalar_one() == 0


async def test_repeating_a_finalize_does_not_double_count(world):
    world.settings.feature_stop_rule = True
    stub: StubProvider = world.providers.get("bolna")
    stub.record = completed_record()
    _, biz, att = bolna_attempt(
        world, "A", "+910000039101", status="DIALING", provider_call_id="stub-1"
    )
    for _ in range(3):
        await finalize_attempt(world.sf, att.id, world.providers, world.settings, world.clock)
    world.session.expire_all()
    assert world.session.get(BusinessStats, biz.id).attempts == 1


async def test_provider_failures_are_not_held_against_the_shop(world):
    world.settings.feature_stop_rule = True
    stub: StubProvider = world.providers.get("bolna")
    from app.providers.base import ProviderCallRecord

    stub.record = ProviderCallRecord(provider_call_id="x", provider_status="failed")
    _, biz, att = bolna_attempt(
        world, "A", "+910000039201", status="DIALING", provider_call_id="stub-1"
    )
    await finalize_attempt(world.sf, att.id, world.providers, world.settings, world.clock)
    world.session.expire_all()
    assert world.session.get(BusinessStats, biz.id) is None


async def test_with_both_flags_off_no_history_is_kept(world):
    stub: StubProvider = world.providers.get("bolna")
    stub.record = completed_record()
    _, biz, att = bolna_attempt(
        world, "A", "+910000039301", status="DIALING", provider_call_id="stub-1"
    )
    await finalize_attempt(world.sf, att.id, world.providers, world.settings, world.clock)
    world.session.expire_all()
    assert world.session.get(BusinessStats, biz.id) is None


# --- the history line ------------------------------------------------------------------------


def live_result_with_history(world, answered):
    stub: StubProvider = world.providers.get("bolna")
    stub.record = completed_record()
    job, biz, att = bolna_attempt(
        world, "A", "+910000039401", status="DIALING", provider_call_id="stub-1"
    )
    seed_history(
        world,
        biz,
        attempts=answered,
        connected=answered,
        completed=answered,
        reported_available=answered - 1,
        uncertain=1,
    )
    return job, att


async def test_history_is_shown_beside_a_live_answer_and_labelled(world):
    world.settings.feature_history = True
    job, att = live_result_with_history(world, answered=9)
    await finalize_attempt(world.sf, att.id, world.providers, world.settings, world.clock)
    result = world.client.get(f"/api/searches/{job.id}/results").json()["results"][0]
    assert result["result_state"] == "REPORTED_AVAILABLE"  # history never changes the state
    assert result["history"]["label"] == "HISTORY"
    assert result["history"]["answered"] == 10 and result["history"]["reported_available"] == 9


async def test_history_is_hidden_until_there_is_enough_of_it(world):
    world.settings.feature_history = True
    job, att = live_result_with_history(world, answered=2)
    await finalize_attempt(world.sf, att.id, world.providers, world.settings, world.clock)
    assert (
        world.client.get(f"/api/searches/{job.id}/results").json()["results"][0]["history"] is None
    )


async def test_history_is_off_by_default(world):
    job, att = live_result_with_history(world, answered=9)
    await finalize_attempt(world.sf, att.id, world.providers, world.settings, world.clock)
    assert (
        world.client.get(f"/api/searches/{job.id}/results").json()["results"][0]["history"] is None
    )


async def test_simulated_answers_never_carry_a_history_line(world):
    world.settings.feature_history = True
    sim = world.providers.get("simulated")
    biz = shop(world.session, "S", "+910000039501")
    sim._by_phone["+910000039501"] = "available"
    seed_history(world, biz, attempts=20, connected=20, reported_available=20)
    sid = create(world)["search_id"]
    await run_to_completion(world, sid)
    result = world.client.get(f"/api/searches/{sid}/results").json()["results"][0]
    assert result["history"] is None


async def test_a_card_without_a_live_answer_has_no_history_line(world):
    world.settings.feature_history = True
    sim = world.providers.get("simulated")
    biz = shop(world.session, "Quiet", "+910000039601")
    sim._by_phone["+910000039601"] = "no_answer"
    world.settings.max_attempts_per_business = 1
    seed_history(world, biz, attempts=20, connected=20, reported_available=20)
    sid = create(world)["search_id"]
    await run_to_completion(world, sid)
    result = world.client.get(f"/api/searches/{sid}/results").json()["results"][0]
    assert result["result_state"] == "NO_ANSWER" and result["history"] is None


def test_enum_for_a_confirmed_available_answer():
    assert Availability.REPORTED_AVAILABLE == "REPORTED_AVAILABLE"
