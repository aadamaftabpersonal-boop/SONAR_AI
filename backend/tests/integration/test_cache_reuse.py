"""T7.4: a fresh live answer to the same question is shown instead of calling the shop again."""

from datetime import timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.api.deps import get_clock
from app.config import Settings, get_settings
from app.db.models import BusinessResponse, CallAttempt
from app.db.session import get_session
from app.main import create_app
from app.providers.simulated import SimulatedVoiceProvider
from tests.factories import make_attempt, make_business, make_job
from tests.integration.test_api import CENTER, HEADERS, KEY, NOW, body

pytestmark = pytest.mark.integration

QUERY = {
    "category": "pharmacy",
    "item_name": "Paracetamol",
    "attributes": {"strength": "500 mg"},
    "required_fields": ["availability", "price"],
}


@pytest.fixture
def make_client(engine, session_factory):
    def build(**settings):
        app = create_app()
        app.state.providers.register("bolna", SimulatedVoiceProvider())

        def _session():
            with session_factory() as s:
                yield s

        app.dependency_overrides[get_session] = _session
        app.dependency_overrides[get_clock] = lambda: lambda: NOW
        app.dependency_overrides[get_settings] = lambda: Settings(
            _env_file=None,
            sonar_access_key=KEY,
            rate_limit_search_per_minute=1000,
            **settings,
        )
        return TestClient(app)

    return build


def earlier_answer(session, shop, minutes_ago=20, origin="LIVE_CALL", query=None, **over):
    job = make_job(session, status="COMPLETED", parsed_query=query or QUERY)
    attempt = make_attempt(
        session,
        job,
        shop,
        provider="bolna",
        status="COMPLETED",
        provider_call_id=f"exec-{job.id}",
        started_at=NOW - timedelta(minutes=minutes_ago, seconds=60),
    )
    fields = {
        "call_attempt_id": attempt.id,
        "search_job_id": job.id,
        "business_id": shop.id,
        "data_origin": origin,
        "availability": "REPORTED_AVAILABLE",
        "exact_match": "CONFIRMED",
        "price_amount": Decimal("42"),
        "price_currency": "INR",
        "answer_summary": "Reported by phone at 11:10 IST: available, price ₹42",
        "evidence_excerpt": "Yes, we have it in stock",
        "evidence_validated": True,
        "extraction_status": "VALID",
        "answer_timestamp": NOW - timedelta(minutes=minutes_ago),
    }
    fields.update(over)
    session.add(BusinessResponse(**fields))
    session.commit()
    return job


def shop(session, **over):
    return make_business(session, latitude=CENTER["lat"], longitude=CENTER["lng"], **over)


def search(client, **over):
    r = client.post("/api/searches", json=body(**over), headers=HEADERS)
    assert r.status_code in (200, 202), r.text
    return r.json()


def attempts_for(session, search_id):
    return (
        session.execute(select(CallAttempt).where(CallAttempt.search_job_id == search_id))
        .scalars()
        .all()
    )


def test_fresh_answer_is_reused_with_its_original_time(make_client, session):
    s = shop(session)
    earlier_answer(session, s)
    created = search(make_client(feature_cache_reuse=True))
    assert created["status"] == "COMPLETED"  # nothing left to call
    [attempt] = attempts_for(session, created["search_id"])
    assert attempt.provider == "cache" and attempt.started_at is None  # never dialed
    results = (
        make_client(feature_cache_reuse=True)
        .get(f"/api/searches/{created['search_id']}/results")
        .json()
    )
    [r] = results["results"]
    assert r["data_origin"] == "CACHED_LIVE"
    assert r["result_state"] == "REPORTED_AVAILABLE"
    assert r["answer_timestamp"].startswith((NOW - timedelta(minutes=20)).isoformat()[:16])


def test_flag_off_calls_again(make_client, session):
    s = shop(session)
    earlier_answer(session, s)
    created = search(make_client())
    [attempt] = attempts_for(session, created["search_id"])
    assert attempt.provider == "bolna" and attempt.status == "PENDING"


def test_force_fresh_calls_again(make_client, session):
    s = shop(session)
    earlier_answer(session, s)
    created = search(make_client(feature_cache_reuse=True), force_fresh=True)
    [attempt] = attempts_for(session, created["search_id"])
    assert attempt.provider == "bolna"


def test_demo_search_never_shows_live_data(make_client, session):
    s = shop(session)
    earlier_answer(session, s)
    created = search(make_client(feature_cache_reuse=True), demo_mode=True)
    [attempt] = attempts_for(session, created["search_id"])
    assert attempt.provider == "simulated"


def test_stale_simulated_or_different_answers_are_not_reused(make_client, session):
    stale, simulated, other = shop(session), shop(session), shop(session)
    earlier_answer(session, stale, minutes_ago=90)
    earlier_answer(session, simulated, origin="SIMULATED")
    earlier_answer(session, other, query={**QUERY, "attributes": {"strength": "650 mg"}})
    created = search(make_client(feature_cache_reuse=True))
    providers = {a.provider for a in attempts_for(session, created["search_id"])}
    assert providers == {"bolna"}


def test_an_opted_out_shop_is_never_shown_from_cache(make_client, session):
    s = shop(session, opted_out_at=NOW - timedelta(minutes=5))
    earlier_answer(session, s)
    created = search(make_client(feature_cache_reuse=True))
    assert created["status"] == "FAILED"  # nobody left to call or reuse
    assert attempts_for(session, created["search_id"]) == []


def test_a_newer_unclear_answer_blocks_an_older_clear_one(make_client, session):
    s = shop(session)
    earlier_answer(session, s, minutes_ago=40)
    earlier_answer(session, s, minutes_ago=10, availability="UNCERTAIN", exact_match="UNKNOWN")
    created = search(make_client(feature_cache_reuse=True))
    [attempt] = attempts_for(session, created["search_id"])
    assert attempt.provider == "bolna"


def test_mixed_search_reuses_one_and_calls_the_other(make_client, session):
    cached, fresh = shop(session), shop(session)
    earlier_answer(session, cached)
    created = search(make_client(feature_cache_reuse=True))
    by_shop = {a.business_id: a for a in attempts_for(session, created["search_id"])}
    assert by_shop[cached.id].provider == "cache"
    assert by_shop[fresh.id].provider == "bolna" and by_shop[fresh.id].status == "PENDING"
    assert created["status"] == "RUNNING"
    assert len(created["planned_targets"]) == 2
