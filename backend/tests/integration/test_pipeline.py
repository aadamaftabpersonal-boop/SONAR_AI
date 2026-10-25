"""End-to-end behaviour of search -> dispatch -> webhook/pull -> validate -> results, on the
simulator and on stub providers. These tests are the safety rules, executed."""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.api.deps import get_clock, get_session_factory
from app.config import Settings, get_settings
from app.db.models import Business, BusinessResponse, CallAttempt, ProviderEvent
from app.db.repositories import AttemptRepo
from app.db.session import get_session
from app.main import create_app
from app.providers.base import (
    CallRequest,
    ProviderBalanceLow,
    ProviderCallRecord,
    ProviderCallRef,
    ProviderRejected,
    ProviderTimeout,
    ProviderUnavailable,
)
from app.providers.registry import ProviderRegistry
from app.providers.simulated import SimulatedVoiceProvider
from app.services.finalizer import FINALIZED, NOT_READY, UNKNOWN_STATUS, finalize_attempt
from app.services.orchestrator import Orchestrator
from tests.factories import make_attempt, make_business, make_job

pytestmark = pytest.mark.integration

KEY, HOOK = "test-key", "hook-token"
H = {"X-Sonar-Key": KEY}
# Real time, because the database stamps created_at/updated_at with its own clock. Shops get an
# all-day call window so these tests pass at any hour (the window logic has its own unit tests).
NOW = datetime.now(UTC)
LAT, LNG = 12.9716, 77.5946


class Clock:
    """Real time plus an adjustable offset, so DB-stamped times and the app's clock agree."""

    def __init__(self):
        self.offset = timedelta(0)

    def __call__(self) -> datetime:
        return datetime.now(UTC) + self.offset


class StubProvider:
    """Hand-controlled provider for failure and race scenarios."""

    name = "stub"

    def __init__(self):
        self.calls = 0
        self.start_error: Exception | None = None
        self.record: ProviderCallRecord | None = None
        self.pull_error: Exception | None = None

    async def start_call(self, req: CallRequest) -> ProviderCallRef:
        self.calls += 1
        if self.start_error:
            raise self.start_error
        return ProviderCallRef(
            provider="bolna", provider_call_id=f"stub-{self.calls}", provider_status="queued"
        )

    async def get_call(self, provider_call_id: str) -> ProviderCallRecord:
        if self.pull_error:
            raise self.pull_error
        assert self.record is not None
        return self.record.model_copy(update={"provider_call_id": provider_call_id})


def completed_record(**ex_over) -> ProviderCallRecord:
    transcript = "shop: Yes, we have it in stock.\nshop: It is 42 rupees.\n"
    extracted = {
        "availability": "available",
        "exact_match_confirmed": "yes",
        "price_amount": 42,
        "price_currency_stated": "rupees",
        "opt_out_requested": "no",
        "call_outcome": "human",
        "supporting_quote": "Yes, we have it in stock",
    }
    extracted.update(ex_over)
    return ProviderCallRecord(
        provider_call_id="x",
        provider_status="completed",
        transcript=transcript,
        extracted=extracted,
        duration_seconds=30,
    )


@pytest.fixture
def settings():
    return Settings(
        _env_file=None,
        sonar_access_key=KEY,
        webhook_secret_token=HOOK,
        sim_step_seconds=0,
        rate_limit_search_per_minute=1000,
        max_concurrent_calls=2,
    )


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
def providers():
    return ProviderRegistry({"simulated": SimulatedVoiceProvider(), "bolna": StubProvider()})


@pytest.fixture
def world(engine, session, session_factory, settings, clock, providers):
    app = create_app()
    app.state.providers = providers

    def _session():
        with session_factory() as s:
            yield s

    app.dependency_overrides[get_session] = _session
    app.dependency_overrides[get_session_factory] = lambda: session_factory
    app.dependency_overrides[get_clock] = lambda: clock
    app.dependency_overrides[get_settings] = lambda: settings
    orch = Orchestrator(session_factory, providers, settings, clock)
    return type(
        "World",
        (),
        {
            "client": TestClient(app),
            "orch": orch,
            "sf": session_factory,
            "session": session,
            "providers": providers,
            "clock": clock,
            "settings": settings,
            "app": app,
        },
    )


def shop(session, name, phone, dlat=0.0, **over):
    over.setdefault("best_call_window", "00:00-23:59 IST")
    return make_business(
        session, name=name, phone_e164=phone, latitude=LAT + dlat, longitude=LNG, **over
    )


def search_body(**over):
    body = {
        "query_text": "Does anyone have it?",
        "category": "pharmacy",
        "item": {"name": "Paracetamol", "attributes": {"strength": "500 mg"}},
        "location": {"lat": LAT, "lng": LNG},
        "radius_km": 3,
        "demo_mode": True,
    }
    body.update(over)
    return body


async def run_to_completion(world, search_id, max_ticks=60):
    for _ in range(max_ticks):
        await world.orch.tick()
        await world.orch.drain()
        status = world.client.get(f"/api/searches/{search_id}").json()["status"]
        if status not in {"CREATED", "RUNNING"}:
            return status
    raise AssertionError("search did not finish")


def results_by_name(world, search_id):
    data = world.client.get(f"/api/searches/{search_id}/results").json()
    return {r["business"]["name"]: r for r in data["results"]}


# --- the full simulated flow -----------------------------------------------------------------


async def test_full_flow_mixed_outcomes_are_honest(world):
    sim: SimulatedVoiceProvider = world.providers.get("simulated")
    for name, phone, scenario, d in [
        ("Yes Shop", "+910000020001", "available", 0.001),
        ("No Shop", "+910000020002", "unavailable", 0.002),
        ("Silent Shop", "+910000020003", "no_answer", 0.003),
        ("Unsure Shop", "+910000020004", "ambiguous", 0.004),
    ]:
        shop(world.session, name, phone, dlat=d)
        sim._by_phone[phone] = scenario
    world.settings.max_attempts_per_business = 1  # no retries in this test
    sid = world.client.post("/api/searches", json=search_body(), headers=H).json()["search_id"]

    final = await run_to_completion(world, sid)
    assert final == "COMPLETED_PARTIAL"

    r = results_by_name(world, sid)
    assert r["Yes Shop"]["result_state"] == "REPORTED_AVAILABLE"
    assert r["Yes Shop"]["data_origin"] == "SIMULATED"
    assert r["Yes Shop"]["evidence"]["validated"] is True
    assert r["Yes Shop"]["reported"]["price"]["amount"] == 42.0
    assert r["No Shop"]["result_state"] == "REPORTED_UNAVAILABLE"
    assert r["Unsure Shop"]["result_state"] == "UNCERTAIN"
    assert r["Silent Shop"]["result_state"] == "NO_ANSWER"
    assert "does not mean" in r["Silent Shop"]["note"]
    # the silent shop produced no response row at all
    count = world.session.execute(select(func.count()).select_from(BusinessResponse)).scalar_one()
    assert count == 3
    # ranking: available first, silence last
    order = [
        x["business"]["name"]
        for x in world.client.get(f"/api/searches/{sid}/results").json()["results"]
    ]
    assert order[0] == "Yes Shop" and order[-1] == "Silent Shop"


async def test_simulated_results_never_look_live(world):
    shop(world.session, "S", "+910000020010")
    sid = world.client.post("/api/searches", json=search_body(), headers=H).json()["search_id"]
    await run_to_completion(world, sid)
    data = world.client.get(f"/api/searches/{sid}/results").json()
    assert {r["data_origin"] for r in data["results"]} == {"SIMULATED"}
    assert world.client.get(f"/api/searches/{sid}").json()["demo_mode"] is True


async def test_hostile_transcript_does_not_change_the_outcome(world):
    sim = world.providers.get("simulated")
    shop(world.session, "Evil", "+910000020011")
    sim._by_phone["+910000020011"] = "injection"
    sid = world.client.post("/api/searches", json=search_body(), headers=H).json()["search_id"]
    await run_to_completion(world, sid)
    r = results_by_name(world, sid)["Evil"]
    assert r["result_state"] == "REPORTED_AVAILABLE"
    assert "SYSTEM" not in json.dumps(r) and "<script>" not in json.dumps(r)


async def test_a_second_search_does_not_double_dial_within_the_cooldown(world):
    shop(world.session, "Once", "+910000020012")
    sid1 = world.client.post("/api/searches", json=search_body(), headers=H).json()["search_id"]
    await run_to_completion(world, sid1)
    again = world.client.post("/api/searches", json=search_body(), headers=H).json()
    assert again["status"] == "FAILED" and again["error_code"] == "NO_ELIGIBLE_BUSINESSES"
    assert world.providers.get("simulated").calls_started == 1


# --- retries ---------------------------------------------------------------------------------


async def test_no_answer_is_retried_once_then_stops(world):
    sim = world.providers.get("simulated")
    shop(world.session, "Flaky", "+910000020020")
    sim._by_phone["+910000020020"] = "no_answer"
    world.settings.business_cooldown_minutes = 0
    sid = world.client.post("/api/searches", json=search_body(), headers=H).json()["search_id"]

    await world.orch.tick()
    await world.orch.drain()
    attempts = AttemptRepo(world.session).for_search(sid)
    world.session.expire_all()
    attempts = (
        world.session.execute(select(CallAttempt).order_by(CallAttempt.attempt_number))
        .scalars()
        .all()
    )
    assert [a.attempt_number for a in attempts] == [1, 2]
    assert attempts[0].status == "NO_ANSWER" and attempts[1].status == "PENDING"
    assert attempts[1].not_before >= NOW + timedelta(seconds=world.settings.retry_backoff_seconds)

    # while the retry is queued, the first silence stays visible and is never called unavailable
    shown = results_by_name(world, sid)["Flaky"]
    assert shown["result_state"] == "PENDING"
    assert "Not answered on the first try" in shown["note"]
    assert "does not mean the item is unavailable" in shown["note"]

    # not due yet: nothing dials
    await world.orch.tick()
    assert sim.calls_started == 1
    # advance past the backoff: the retry is dialed, and no third attempt is created
    world.clock.offset = timedelta(seconds=world.settings.retry_backoff_seconds + 1)
    await world.orch.tick()
    await world.orch.drain()
    world.session.expire_all()
    attempts = world.session.execute(select(CallAttempt)).scalars().all()
    assert len(attempts) == 2 and sim.calls_started == 2
    assert {a.status for a in attempts} == {"NO_ANSWER"}
    status = world.client.get(f"/api/searches/{sid}").json()["status"]
    assert status == "COMPLETED_PARTIAL"


async def test_answered_calls_are_never_retried(world):
    shop(world.session, "Answered", "+910000020021")
    sid = world.client.post("/api/searches", json=search_body(), headers=H).json()["search_id"]
    await run_to_completion(world, sid)
    assert world.session.execute(select(func.count()).select_from(CallAttempt)).scalar_one() == 1


# --- consent, opt-out, cancel, deadline ------------------------------------------------------


async def test_opted_out_between_planning_and_dialing_is_never_called(world):
    sim = world.providers.get("simulated")
    biz = shop(world.session, "Changed Mind", "+910000020030")
    sid = world.client.post("/api/searches", json=search_body(), headers=H).json()["search_id"]
    from app.db.repositories import BusinessRepo

    BusinessRepo(world.session).mark_opt_out(biz.id)
    world.session.commit()
    await world.orch.tick()
    await world.orch.drain()
    assert sim.calls_started == 0
    attempt = world.session.execute(select(CallAttempt)).scalars().one()
    world.session.refresh(attempt)
    assert attempt.status == "CANCELLED" and attempt.failure_reason == "NOT_CONSENTED"
    assert world.client.get(f"/api/searches/{sid}").json()["status"] == "COMPLETED_PARTIAL"


async def test_opt_out_on_a_call_is_recorded_and_cancels_queued_attempts(world):
    sim = world.providers.get("simulated")
    biz = shop(world.session, "Stop Calling", "+910000020031")
    sim._by_phone["+910000020031"] = "opt_out"
    # another search already has a call queued for the same shop, scheduled for later
    job2 = make_job(
        world.session,
        parsed_query=search_body()
        | {
            "item_name": "Paracetamol",
            "attributes": {},
            "lat": LAT,
            "lng": LNG,
            "required_fields": ["availability"],
        },
    )
    queued = make_attempt(
        world.session, job2, biz, provider="simulated", not_before=NOW + timedelta(hours=1)
    )
    sid = world.client.post("/api/searches", json=search_body(), headers=H).json()["search_id"]
    await run_to_completion(world, sid)
    world.session.expire_all()
    biz = world.session.get(Business, biz.id)
    assert biz.participation_status == "OPTED_OUT" and biz.opted_out_at is not None
    assert world.session.get(CallAttempt, queued.id).status == "CANCELLED"
    r = results_by_name(world, sid)["Stop Calling"]
    assert r["result_state"] == "DECLINED"
    # and the shop is excluded from every future search
    again = world.client.post("/api/searches", json=search_body(), headers=H).json()
    assert again["error_code"] == "NO_ELIGIBLE_BUSINESSES"


async def test_cancelled_job_dials_nobody(world):
    sim = world.providers.get("simulated")
    shop(world.session, "A", "+910000020032")
    sid = world.client.post("/api/searches", json=search_body(), headers=H).json()["search_id"]
    world.client.post(f"/api/searches/{sid}/cancel", headers=H)
    await world.orch.tick()
    assert sim.calls_started == 0


async def test_deadline_times_out_stragglers_and_closes_the_job(world):
    sim = world.providers.get("simulated")
    shop(world.session, "Slow", "+910000020033")
    sid = world.client.post("/api/searches", json=search_body(), headers=H).json()["search_id"]
    world.clock.offset = timedelta(seconds=world.settings.search_deadline_seconds + 1)
    await world.orch.tick()
    data = world.client.get(f"/api/searches/{sid}").json()
    assert data["status"] == "COMPLETED_PARTIAL"
    assert data["attempts"][0]["status"] == "TIMED_OUT"
    assert data["attempts"][0]["result_state"] == "CALL_FAILED"
    assert sim.calls_started == 0


async def test_concurrency_cap_is_never_exceeded(world):
    world.settings.sim_step_seconds = 0.02
    for i in range(5):
        shop(world.session, f"S{i}", f"+91000002004{i}", dlat=0.001 * (i + 1))
    sid = world.client.post("/api/searches", json=search_body(), headers=H).json()["search_id"]
    peak = 0
    for _ in range(200):
        await world.orch.tick()
        world.session.expire_all()
        peak = max(peak, AttemptRepo(world.session).count_active())
        if world.client.get(f"/api/searches/{sid}").json()["status"] not in {"CREATED", "RUNNING"}:
            break
        await asyncio.sleep(0.01)
    await world.orch.drain()
    assert 1 <= peak <= world.settings.max_concurrent_calls
    assert world.providers.get("simulated").calls_started == 5


# --- dispatch safety (stub provider) ---------------------------------------------------------


def bolna_attempt(world, name="B", phone="+910000020050", **over):
    biz = shop(world.session, name, phone)
    job = make_job(
        world.session,
        parsed_query={
            "query_text": "q",
            "category": "pharmacy",
            "item_name": "Paracetamol",
            "attributes": {"strength": "500 mg"},
            "lat": LAT,
            "lng": LNG,
            "radius_km": 3,
            "required_fields": ["availability", "price"],
        },
        center_lat=LAT,
        center_lng=LNG,
        radius_km=3,
        status="CREATED",
        deadline_at=NOW + timedelta(minutes=5),
    )
    att = make_attempt(world.session, job, biz, provider="bolna", **over)
    return job, biz, att


async def test_timeout_during_dispatch_becomes_dispatch_unknown_and_is_never_redialed(world):
    stub: StubProvider = world.providers.get("bolna")
    stub.start_error = ProviderTimeout("slow")
    _, _, att = bolna_attempt(world)
    await world.orch.tick()
    world.session.expire_all()
    assert world.session.get(CallAttempt, att.id).status == "DISPATCH_UNKNOWN"
    stub.start_error = None
    for _ in range(3):
        await world.orch.tick()
    assert stub.calls == 1  # never dialed a second time


async def test_restart_mid_dispatch_never_redials(world):
    stub: StubProvider = world.providers.get("bolna")
    _, _, att = bolna_attempt(world, status="DISPATCHING")  # crashed after claiming
    assert world.orch.recover_on_start() == 1
    for _ in range(3):
        await world.orch.tick()
    world.session.expire_all()
    assert world.session.get(CallAttempt, att.id).status == "DISPATCH_UNKNOWN"
    assert stub.calls == 0


async def test_provider_rejection_is_not_retried(world):
    stub: StubProvider = world.providers.get("bolna")
    stub.start_error = ProviderRejected("bad number")
    _, _, att = bolna_attempt(world)
    await world.orch.tick()
    world.session.expire_all()
    a = world.session.get(CallAttempt, att.id)
    assert a.status == "FAILED" and a.error_class == "PROVIDER_REJECTED"
    assert world.session.execute(select(func.count()).select_from(CallAttempt)).scalar_one() == 1


async def test_provider_outage_is_retried_within_the_cap(world):
    stub: StubProvider = world.providers.get("bolna")
    stub.start_error = ProviderUnavailable("503")
    bolna_attempt(world)
    await world.orch.tick()
    world.session.expire_all()
    attempts = (
        world.session.execute(select(CallAttempt).order_by(CallAttempt.attempt_number))
        .scalars()
        .all()
    )
    assert [(a.attempt_number, a.status) for a in attempts] == [(1, "FAILED"), (2, "PENDING")]


async def test_low_balance_pauses_dispatching(world):
    stub: StubProvider = world.providers.get("bolna")
    stub.start_error = ProviderBalanceLow("empty")
    _, _, first = bolna_attempt(world, "One", "+910000020051")
    bolna_attempt(world, "Two", "+910000020052")
    await world.orch.tick()
    assert world.orch.paused and stub.calls == 1
    world.session.expire_all()
    assert world.session.get(CallAttempt, first.id).status == "INSUFFICIENT_BALANCE"


async def test_daily_budget_stops_dialing_without_calling(world):
    world.settings.global_daily_call_budget = 1
    stub: StubProvider = world.providers.get("bolna")
    stub.record = completed_record()
    _, _, a1 = bolna_attempt(world, "One", "+910000020053")
    _, _, a2 = bolna_attempt(world, "Two", "+910000020054")
    await world.orch.tick()
    await world.orch.tick()
    world.session.expire_all()
    statuses = {world.session.get(CallAttempt, a.id).status for a in (a1, a2)}
    assert "FAILED" in statuses and stub.calls == 1
    failed = [a for a in (a1, a2) if world.session.get(CallAttempt, a.id).status == "FAILED"][0]
    assert world.session.get(CallAttempt, failed.id).error_class == "BUDGET_EXCEEDED"


# --- webhook + pull (D-005) ------------------------------------------------------------------


def hook(world, payload, token=HOOK, raw=None):
    url = f"/api/webhooks/bolna/{token}"
    if raw is not None:
        return world.client.post(url, content=raw, headers={"content-type": "application/json"})
    return world.client.post(url, json=payload)


def dialing_attempt(world, call_id="stub-1"):
    _, _, att = bolna_attempt(world, status="DIALING", provider_call_id=call_id)
    return att


def test_forged_completed_webhook_cannot_write_a_result(world):
    """D-005: the pulled record says in-progress, so the 'completed' body is ignored."""
    stub: StubProvider = world.providers.get("bolna")
    stub.record = ProviderCallRecord(provider_call_id="x", provider_status="in-progress")
    att = dialing_attempt(world)
    assert (
        hook(
            world,
            {
                "execution_id": "stub-1",
                "status": "completed",
                "transcript": "shop: yes",
                "extracted_data": {"availability": "available"},
            },
        ).status_code
        == 200
    )
    world.session.expire_all()
    assert world.session.get(CallAttempt, att.id).status == "IN_PROGRESS"
    assert (
        world.session.execute(select(func.count()).select_from(BusinessResponse)).scalar_one() == 0
    )


def test_completed_webhook_triggers_a_pull_and_stores_the_validated_result(world):
    stub: StubProvider = world.providers.get("bolna")
    stub.record = completed_record()
    att = dialing_attempt(world)
    hook(world, {"execution_id": "stub-1", "status": "completed"})
    world.session.expire_all()
    assert world.session.get(CallAttempt, att.id).status == "COMPLETED"
    resp = world.session.execute(select(BusinessResponse)).scalars().one()
    assert resp.availability == "REPORTED_AVAILABLE" and resp.data_origin == "LIVE_CALL"
    assert resp.evidence_validated and float(resp.price_amount) == 42.0


def test_fifty_duplicate_deliveries_store_one_event_and_one_response(world):
    stub: StubProvider = world.providers.get("bolna")
    stub.record = completed_record()
    dialing_attempt(world)
    for _ in range(50):
        assert hook(world, {"execution_id": "stub-1", "status": "completed"}).status_code == 200
    world.session.expire_all()
    assert world.session.execute(select(func.count()).select_from(ProviderEvent)).scalar_one() == 1
    assert (
        world.session.execute(select(func.count()).select_from(BusinessResponse)).scalar_one() == 1
    )


def test_out_of_order_events_end_in_the_right_state(world):
    stub: StubProvider = world.providers.get("bolna")
    stub.record = completed_record()
    att = dialing_attempt(world)
    for status in ("completed", "in-progress", "ringing", "queued", "call-disconnected"):
        hook(world, {"execution_id": "stub-1", "status": status})
    world.session.expire_all()
    a = world.session.get(CallAttempt, att.id)
    assert a.status == "COMPLETED"  # a late 'ringing' never moves it backwards
    assert (
        world.session.execute(select(func.count()).select_from(BusinessResponse)).scalar_one() == 1
    )


def test_event_for_an_unknown_call_is_stored_as_an_orphan(world):
    assert hook(world, {"execution_id": "nobody", "status": "ringing"}).status_code == 200
    ev = world.session.execute(select(ProviderEvent)).scalars().one()
    assert ev.call_attempt_id is None and ev.provider_call_id == "nobody"


def test_wrong_or_unset_token_is_rejected_and_nothing_is_stored(world):
    assert hook(world, {"execution_id": "x", "status": "ringing"}, token="wrong").status_code == 401
    world.app.dependency_overrides[get_settings] = lambda: Settings(_env_file=None)
    assert hook(world, {"execution_id": "x", "status": "ringing"}, token="").status_code in (
        401,
        404,
    )
    assert (
        hook(world, {"execution_id": "x", "status": "ringing"}, token="anything").status_code == 401
    )
    assert world.session.execute(select(func.count()).select_from(ProviderEvent)).scalar_one() == 0


@pytest.mark.parametrize("raw", [b"not json", b"[1, 2]", b'"str"'])
def test_malformed_bodies_are_400(world, raw):
    r = hook(world, None, raw=raw)
    assert r.status_code == 400 and r.json()["error"]["code"] == "WEBHOOK_MALFORMED"


def test_oversized_body_is_413(world):
    world.settings.webhook_max_body_bytes = 100
    r = hook(world, None, raw=json.dumps({"x": "y" * 500}).encode())
    assert r.status_code == 413


def test_source_ip_allowlist(world):
    world.settings.webhook_allowed_ips = "13.203.39.153"
    assert hook(world, {"execution_id": "x", "status": "ringing"}).status_code == 401


def test_unknown_status_is_recorded_without_changing_state(world):
    att = dialing_attempt(world)
    hook(world, {"execution_id": "stub-1", "status": "brand-new-status"})
    world.session.expire_all()
    a = world.session.get(CallAttempt, att.id)
    assert a.status == "DIALING" and a.provider_status == "brand-new-status"


# --- finalize edge cases and the reconciler ---------------------------------------------------


async def run_finalize(world, attempt_id):
    return await finalize_attempt(
        world.sf, attempt_id, world.providers, world.settings, world.clock
    )


async def test_finalize_twice_is_idempotent(world):
    stub: StubProvider = world.providers.get("bolna")
    stub.record = completed_record()
    att = dialing_attempt(world)
    assert await run_finalize(world, att.id) == FINALIZED
    assert await run_finalize(world, att.id) == FINALIZED
    assert (
        world.session.execute(select(func.count()).select_from(BusinessResponse)).scalar_one() == 1
    )


async def test_finalize_not_ready_leaves_the_attempt_open(world):
    stub: StubProvider = world.providers.get("bolna")
    stub.record = ProviderCallRecord(provider_call_id="x", provider_status="ringing")
    att = dialing_attempt(world)
    assert await run_finalize(world, att.id) == NOT_READY
    world.session.expire_all()
    assert world.session.get(CallAttempt, att.id).status == "RINGING"


async def test_unknown_pulled_status_is_not_terminal(world):
    stub: StubProvider = world.providers.get("bolna")
    stub.record = ProviderCallRecord(provider_call_id="x", provider_status="warp-speed")
    att = dialing_attempt(world)
    assert await run_finalize(world, att.id) == UNKNOWN_STATUS
    world.session.expire_all()
    assert world.session.get(CallAttempt, att.id).status == "DIALING"


async def test_failed_pull_leaves_it_for_the_reconciler(world):
    stub: StubProvider = world.providers.get("bolna")
    stub.pull_error = ProviderUnavailable("down")
    att = dialing_attempt(world)
    assert await run_finalize(world, att.id) == "PULL_FAILED"
    stub.pull_error = None
    stub.record = completed_record()
    assert await run_finalize(world, att.id) == FINALIZED


async def test_reconciler_recovers_a_call_whose_webhooks_never_arrived(world):
    stub: StubProvider = world.providers.get("bolna")
    stub.record = completed_record()
    _, _, att = bolna_attempt(world, status="RINGING", provider_call_id="stub-9")
    # quiet for longer than RECONCILE_AFTER_SECONDS
    world.clock.offset = timedelta(seconds=world.settings.reconcile_after_seconds + 5)
    from sqlalchemy import update

    world.session.execute(
        update(CallAttempt).where(CallAttempt.id == att.id).values(updated_at=NOW)
    )
    world.session.commit()
    assert await world.orch.reconcile() == 1
    world.session.expire_all()
    assert world.session.get(CallAttempt, att.id).status == "COMPLETED"
    assert (
        world.session.execute(select(func.count()).select_from(BusinessResponse)).scalar_one() == 1
    )


async def test_reconciler_ignores_recent_attempts(world):
    stub: StubProvider = world.providers.get("bolna")
    stub.record = completed_record()
    bolna_attempt(world, status="RINGING", provider_call_id="stub-8")
    assert await world.orch.reconcile() == 0


async def test_voicemail_creates_no_response_and_is_not_unavailable(world):
    stub: StubProvider = world.providers.get("bolna")
    stub.record = completed_record(call_outcome="voicemail")
    _, _, att = bolna_attempt(world, status="DIALING", provider_call_id="stub-7")
    await run_finalize(world, att.id)
    world.session.expire_all()
    a = world.session.get(CallAttempt, att.id)
    assert a.status == "COMPLETED" and a.failure_reason == "NO_HUMAN"
    assert (
        world.session.execute(select(func.count()).select_from(BusinessResponse)).scalar_one() == 0
    )
    data = world.client.get(f"/api/searches/{a.search_job_id}/results").json()
    assert data["results"][0]["result_state"] == "NO_ANSWER"
