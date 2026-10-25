"""The real BolnaVoiceProvider driven through the real pipeline, with Bolna itself mocked at the
HTTP layer: orchestrator -> POST /call -> webhook doorbell -> GET /executions pull -> validator ->
stored result. If this passes, only Bolna's real field names remain unproven."""

from __future__ import annotations

import httpx
import pytest
from sqlalchemy import func, select

from app.db.models import AuditEvent, BusinessResponse, CallAttempt
from app.providers.bolna import BolnaVoiceProvider
from tests.integration.test_pipeline import (  # noqa: F401
    HOOK,
    H,
    clock,
    providers,
    results_by_name,
    search_body,
    settings,
    shop,
    world,
)

pytestmark = pytest.mark.integration

# ruff: noqa: F811

EXEC_ID = "aaaaaaaa-0000-4000-8000-000000000001"
TRANSCRIPT = "agent: Do you have it?\nshop: Yes, we have it in stock.\nshop: It is 42 rupees.\n"


class FakeBolna:
    """Just enough of Bolna's documented API to run a call end to end."""

    def __init__(self):
        self.posts: list[dict] = []
        self.gets: list[str] = []
        self.status = "completed"
        self.extracted: dict | None = {
            "availability": "available",
            "exact_match_confirmed": "yes",
            "price_amount": 42,
            "price_currency_stated": "rupees",
            "supporting_quote": "Yes, we have it in stock",
            "opt_out_requested": "no",
            "call_outcome": "human",
        }
        self.post_response: httpx.Response | None = None

    def handler(self, request: httpx.Request) -> httpx.Response:
        import json

        if request.method == "POST" and request.url.path == "/call":
            self.posts.append(json.loads(request.content))
            return self.post_response or httpx.Response(
                200, json={"message": "done", "status": "queued", "execution_id": EXEC_ID}
            )
        if request.method == "GET" and request.url.path.startswith("/executions/"):
            self.gets.append(request.url.path.rsplit("/", 1)[-1])
            body = {"status": self.status, "conversation_duration": 31, "total_cost": 0.4}
            if self.status == "completed":
                body |= {"transcript": TRANSCRIPT, "extracted_data": self.extracted}
            return httpx.Response(200, json=body)
        return httpx.Response(404, json={"message": "unexpected"})


@pytest.fixture
def bolna_world(world):
    fake = FakeBolna()
    client = httpx.AsyncClient(transport=httpx.MockTransport(fake.handler))
    live = BolnaVoiceProvider("sk-test", agent_ids={"pharmacy": "agent-uuid"}, client=client)
    world.providers.register("bolna", live)
    world.fake = fake
    world.settings.max_attempts_per_business = 1
    return world


def create_live(world, **over):
    r = world.client.post("/api/searches", json=search_body(demo_mode=False, **over), headers=H)
    assert r.status_code == 202, r.text
    return r.json()["search_id"]


def hook(world, status, call_id=EXEC_ID):
    return world.client.post(
        f"/api/webhooks/bolna/{HOOK}", json={"execution_id": call_id, "status": status}
    )


async def test_a_live_search_places_one_call_with_the_right_body(bolna_world):
    shop(bolna_world.session, "Real Shop", "+910000041001")
    create_live(bolna_world)
    await bolna_world.orch.tick()
    assert len(bolna_world.fake.posts) == 1
    sent = bolna_world.fake.posts[0]
    assert sent["agent_id"] == "agent-uuid" and sent["recipient_phone_number"] == "+910000041001"
    assert sent["user_data"]["item"] == "Paracetamol"
    assert set(sent["user_data"]) == {"category", "item", "attributes_text", "required_fields_text"}
    assert "retry_config" not in sent and "bypass_call_guardrails" not in sent


async def test_the_webhook_rings_the_doorbell_and_the_result_comes_from_the_pull(bolna_world):
    biz = shop(bolna_world.session, "Real Shop", "+910000041002")
    sid = create_live(bolna_world)
    await bolna_world.orch.tick()
    bolna_world.session.expire_all()
    attempt = bolna_world.session.execute(select(CallAttempt)).scalars().one()
    assert attempt.provider == "bolna" and attempt.provider_call_id == EXEC_ID
    assert attempt.status == "DIALING"

    assert hook(bolna_world, "completed").status_code == 200
    assert bolna_world.fake.gets == [EXEC_ID]  # the authoritative record was pulled

    bolna_world.session.expire_all()
    resp = bolna_world.session.execute(select(BusinessResponse)).scalars().one()
    assert resp.business_id == biz.id and resp.data_origin == "LIVE_CALL"
    assert resp.availability == "REPORTED_AVAILABLE" and float(resp.price_amount) == 42.0
    assert resp.price_currency == "INR" and resp.evidence_validated
    result = results_by_name(bolna_world, sid)["Real Shop"]
    assert result["data_origin"] == "LIVE_CALL" and result["result_state"] == "REPORTED_AVAILABLE"


async def test_a_forged_completed_webhook_is_ignored_when_bolna_says_in_progress(bolna_world):
    shop(bolna_world.session, "Real Shop", "+910000041003")
    create_live(bolna_world)
    await bolna_world.orch.tick()
    bolna_world.fake.status = "in-progress"
    hook(bolna_world, "completed")  # the body claims completed, the pull disagrees
    bolna_world.session.expire_all()
    assert (
        bolna_world.session.execute(select(func.count()).select_from(BusinessResponse)).scalar_one()
        == 0
    )
    assert bolna_world.session.execute(select(CallAttempt)).scalars().one().status == "IN_PROGRESS"


async def test_the_reconciler_finishes_a_call_whose_webhooks_never_arrived(bolna_world):
    from datetime import timedelta

    shop(bolna_world.session, "Real Shop", "+910000041004")
    create_live(bolna_world)
    await bolna_world.orch.tick()
    bolna_world.clock.offset = timedelta(seconds=bolna_world.settings.reconcile_after_seconds + 5)
    assert await bolna_world.orch.reconcile() == 1
    bolna_world.session.expire_all()
    assert (
        bolna_world.session.execute(select(func.count()).select_from(BusinessResponse)).scalar_one()
        == 1
    )


async def test_nested_extracted_data_is_understood_end_to_end(bolna_world):
    bolna_world.fake.extracted = {
        "stock": {
            "availability": {"objective": "available", "confidence": 0.9},
            "exact_match_confirmed": {"objective": "yes", "confidence": 0.9},
            "price_amount": {"value": 42},
            "price_currency_stated": {"subjective": "rupees"},
            "supporting_quote": {"subjective": "Yes, we have it in stock", "confidence": 0.8},
            "call_outcome": {"objective": "human"},
            "opt_out_requested": {"objective": "no"},
        }
    }
    shop(bolna_world.session, "Real Shop", "+910000041005")
    create_live(bolna_world)
    await bolna_world.orch.tick()
    hook(bolna_world, "completed")
    bolna_world.session.expire_all()
    resp = bolna_world.session.execute(select(BusinessResponse)).scalars().one()
    assert resp.availability == "REPORTED_AVAILABLE" and float(resp.provider_confidence) == 0.8


async def test_a_call_with_no_extraction_is_uncertain_not_available(bolna_world):
    bolna_world.fake.extracted = None
    sid = None
    shop(bolna_world.session, "Real Shop", "+910000041006")
    sid = create_live(bolna_world)
    await bolna_world.orch.tick()
    hook(bolna_world, "completed")
    assert results_by_name(bolna_world, sid)["Real Shop"]["result_state"] == "UNCERTAIN"


async def test_an_unanswered_call_is_no_answer_and_is_not_unavailable(bolna_world):
    bolna_world.fake.status = "no-answer"
    shop(bolna_world.session, "Real Shop", "+910000041007")
    sid = create_live(bolna_world)
    await bolna_world.orch.tick()
    hook(bolna_world, "no-answer")
    assert results_by_name(bolna_world, sid)["Real Shop"]["result_state"] in {
        "NO_ANSWER",
        "PENDING",
    }
    bolna_world.session.expire_all()
    assert (
        bolna_world.session.execute(select(func.count()).select_from(BusinessResponse)).scalar_one()
        == 0
    )


async def test_a_bolna_error_on_dispatch_is_recorded_without_a_redial(bolna_world):
    bolna_world.fake.post_response = httpx.Response(500, json={"message": "boom"})
    shop(bolna_world.session, "Real Shop", "+910000041008")
    create_live(bolna_world)
    for _ in range(3):
        await bolna_world.orch.tick()
    assert len(bolna_world.fake.posts) == 1  # a 5xx is an unknown outcome: never dialed twice
    bolna_world.session.expire_all()
    assert (
        bolna_world.session.execute(select(CallAttempt)).scalars().one().status
        == "DISPATCH_UNKNOWN"
    )


async def test_a_rejected_number_fails_cleanly_and_is_not_retried(bolna_world):
    bolna_world.fake.post_response = httpx.Response(
        400, json={"error": 400, "message": "number is not verified"}
    )
    shop(bolna_world.session, "Real Shop", "+910000041009")
    create_live(bolna_world)
    await bolna_world.orch.tick()
    bolna_world.session.expire_all()
    attempts = bolna_world.session.execute(select(CallAttempt)).scalars().all()
    assert len(attempts) == 1 and attempts[0].status == "FAILED"
    assert attempts[0].error_class == "PROVIDER_REJECTED"


async def test_a_low_balance_pauses_every_further_call(bolna_world):
    bolna_world.fake.post_response = httpx.Response(
        400, json={"error": 400, "message": "Insufficient balance"}
    )
    shop(bolna_world.session, "One", "+910000041010")
    shop(bolna_world.session, "Two", "+910000041011", dlat=0.001)
    create_live(bolna_world)
    await bolna_world.orch.tick()
    assert bolna_world.orch.paused and len(bolna_world.fake.posts) == 1
    bolna_world.session.expire_all()
    statuses = {a.status for a in bolna_world.session.execute(select(CallAttempt)).scalars()}
    assert "INSUFFICIENT_BALANCE" in statuses and "PENDING" in statuses


async def test_the_daily_budget_stops_real_calls_before_bolna_is_contacted(bolna_world):
    bolna_world.settings.global_daily_call_budget = 1
    shop(bolna_world.session, "One", "+910000041012")
    shop(bolna_world.session, "Two", "+910000041013", dlat=0.001)
    create_live(bolna_world)
    for _ in range(3):
        await bolna_world.orch.tick()
    assert len(bolna_world.fake.posts) == 1
    bolna_world.session.expire_all()
    classes = {a.error_class for a in bolna_world.session.execute(select(CallAttempt)).scalars()}
    assert "BUDGET_EXCEEDED" in classes


async def test_the_dispatch_is_audited_without_the_phone_number(bolna_world):
    shop(bolna_world.session, "Real Shop", "+910000041014")
    create_live(bolna_world)
    await bolna_world.orch.tick()
    bolna_world.session.expire_all()
    events = bolna_world.session.execute(select(AuditEvent)).scalars().all()
    assert any(e.action == "call_dispatched" for e in events)
    assert "+9100000410" not in str([e.detail for e in events])
