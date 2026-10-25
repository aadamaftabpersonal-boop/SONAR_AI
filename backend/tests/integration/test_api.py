from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.api.deps import get_clock
from app.config import Settings, get_settings
from app.db.models import BusinessResponse, CallAttempt
from app.db.session import get_session
from app.main import create_app
from tests.factories import make_attempt, make_business, make_job

pytestmark = pytest.mark.integration

KEY = "test-access-key"
# 11:00 IST on a Monday: inside every default call window
NOW = datetime(2026, 11, 2, 5, 30, tzinfo=UTC)
CENTER = {"lat": 12.9716, "lng": 77.5946, "label": "Demo locality"}
HEADERS = {"X-Sonar-Key": KEY}


def body(**over):
    base = {
        "query_text": "Does anyone nearby have it in stock?",
        "category": "pharmacy",
        "item": {"name": "Paracetamol", "attributes": {"strength": "500 mg"}},
        "location": CENTER,
        "radius_km": 3,
    }
    base.update(over)
    return base


@pytest.fixture
def client(engine, session, session_factory):
    app = create_app()

    def _session():
        with session_factory() as s:
            yield s

    app.dependency_overrides[get_session] = _session
    app.dependency_overrides[get_clock] = lambda: lambda: NOW
    app.dependency_overrides[get_settings] = lambda: Settings(
        _env_file=None, sonar_access_key=KEY, rate_limit_search_per_minute=1000
    )
    return TestClient(app)


def shop(session, name="Shop", dlat=0.0, **over):
    return make_business(
        session,
        name=name,
        latitude=CENTER["lat"] + dlat,
        longitude=CENTER["lng"],
        **over,
    )


# --- health and config -----------------------------------------------------------------------


def test_health_and_ready(client):
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/health/ready").json() == {"status": "ready"}


def test_public_config_lists_categories_and_no_secrets(client):
    data = client.get("/api/config/public").json()
    assert "pharmacy" in data["categories"]
    assert data["max_radius_km"] == 25
    assert KEY not in client.get("/api/config/public").text


def test_business_list_never_contains_phone_numbers(client, session):
    shop(session, "Visible")
    r = client.get("/api/businesses", params={"category": "pharmacy", **CENTER})
    assert r.status_code == 200
    assert r.json()[0]["name"] == "Visible"
    assert "phone" not in r.text and "+91" not in r.text


# --- auth, limits, validation ----------------------------------------------------------------


def test_missing_key_is_unauthorized(client):
    r = client.post("/api/searches", json=body())
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "UNAUTHORIZED"


def test_wrong_key_is_unauthorized(client):
    r = client.post("/api/searches", json=body(), headers={"X-Sonar-Key": "nope"})
    assert r.status_code == 401


def test_unconfigured_key_fails_closed(client):
    client.app.dependency_overrides[get_settings] = lambda: Settings(_env_file=None)
    r = client.post("/api/searches", json=body(), headers={"X-Sonar-Key": ""})
    assert r.status_code == 401


def test_rate_limit_returns_429(engine, session, session_factory):
    app = create_app()

    def _session():
        with session_factory() as s:
            yield s

    app.dependency_overrides[get_session] = _session
    app.dependency_overrides[get_clock] = lambda: lambda: NOW
    app.dependency_overrides[get_settings] = lambda: Settings(
        _env_file=None, sonar_access_key=KEY, rate_limit_search_per_minute=2
    )
    c = TestClient(app)
    app.state.search_limiter.limit = 2
    codes = [c.post("/api/searches", json=body(), headers=HEADERS).status_code for _ in range(4)]
    assert 429 in codes[2:]
    assert codes[0] != 429


def test_validation_error_uses_the_envelope_with_field(client):
    r = client.post("/api/searches", json=body(radius_km=99), headers=HEADERS)
    assert r.status_code == 422
    err = r.json()["error"]
    assert err["code"] == "VALIDATION" and err["field"] == "radius_km"
    assert err["request_id"]


def test_oversized_query_is_rejected(client):
    r = client.post("/api/searches", json=body(query_text="x" * 501), headers=HEADERS)
    assert r.status_code == 422


def test_hostile_item_name_is_rejected(client):
    r = client.post(
        "/api/searches",
        json=body(item={"name": "'; DROP TABLE businesses;--", "attributes": {"strength": "5"}}),
        headers=HEADERS,
    )
    assert r.status_code == 422
    assert r.json()["error"]["field"] == "item.name"


def test_prescription_query_is_refused_and_creates_no_job(client, session):
    r = client.post("/api/searches", json=body(query_text="what dosage?"), headers=HEADERS)
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "UNSUPPORTED_QUERY"
    assert session.execute(select(CallAttempt)).first() is None


def test_unknown_search_id_is_a_404_envelope(client):
    for sid in ("00000000-0000-0000-0000-000000000000", "not-a-uuid"):
        r = client.get(f"/api/searches/{sid}")
        assert r.status_code == 404
        assert r.json()["error"]["code"] == "NOT_FOUND"


# --- create flows ----------------------------------------------------------------------------


def test_clarification_returns_questions_and_no_attempts(client, session):
    shop(session)
    r = client.post(
        "/api/searches",
        json=body(item={"name": "Paracetamol", "attributes": {}}),
        headers=HEADERS,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "NEEDS_CLARIFICATION"
    assert data["clarification"]["questions"][0]["field"] == "item.attributes.strength"
    assert session.execute(select(CallAttempt)).first() is None


def test_no_eligible_businesses_explains_why(client, session):
    shop(session, participation_status="INVITED", consent_recorded_at=None)
    r = client.post("/api/searches", json=body(), headers=HEADERS)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "FAILED"
    assert data["error_code"] == "NO_ELIGIBLE_BUSINESSES"
    assert "No consenting businesses" in data["message"]


def test_create_plans_nearest_targets_and_returns_immediately(client, session):
    near = shop(session, "Near", dlat=0.002)
    far = shop(session, "Far", dlat=0.02)
    shop(session, "Out of range", dlat=0.5)
    r = client.post("/api/searches", json=body(), headers=HEADERS)
    assert r.status_code == 202
    data = r.json()
    assert data["status"] == "CREATED"
    assert [t["name"] for t in data["planned_targets"]] == ["Near", "Far"]
    assert data["planned_targets"][0]["business_id"] == str(near.id)
    assert far.id is not None
    attempts = session.execute(select(CallAttempt)).scalars().all()
    assert {a.status for a in attempts} == {"PENDING"}
    assert {a.provider for a in attempts} == {"bolna"}


def test_demo_mode_uses_the_simulated_provider(client, session):
    shop(session)
    r = client.post("/api/searches", json=body(demo_mode=True), headers=HEADERS)
    assert r.status_code == 202
    attempt = session.execute(select(CallAttempt)).scalars().one()
    assert attempt.provider == "simulated"
    assert client.get(f"/api/searches/{r.json()['search_id']}").json()["demo_mode"] is True


def test_target_cap_is_enforced(client, session):
    for i in range(8):
        shop(session, f"S{i}", dlat=0.001 * (i + 1))
    data = client.post("/api/searches", json=body(), headers=HEADERS).json()
    assert len(data["planned_targets"]) == 5


def test_opted_out_business_is_never_planned(client, session):
    gone = shop(session, "Gone")
    shop(session, "Here", dlat=0.001)
    from app.db.repositories import BusinessRepo

    BusinessRepo(session).mark_opt_out(gone.id)
    session.commit()
    data = client.post("/api/searches", json=body(), headers=HEADERS).json()
    assert [t["name"] for t in data["planned_targets"]] == ["Here"]


def test_same_request_twice_creates_two_jobs(client, session):
    shop(session)
    a = client.post("/api/searches", json=body(), headers=HEADERS).json()
    b = client.post("/api/searches", json=body(), headers=HEADERS).json()
    assert a["search_id"] != b["search_id"]


# --- read endpoints --------------------------------------------------------------------------


def test_get_search_shows_counts_and_pending_attempts(client, session):
    shop(session, "A")
    shop(session, "B", dlat=0.001)
    sid = client.post("/api/searches", json=body(), headers=HEADERS).json()["search_id"]
    data = client.get(f"/api/searches/{sid}").json()
    assert data["counts"]["planned"] == 2 and data["counts"]["pending"] == 2
    assert {a["result_state"] for a in data["attempts"]} == {"PENDING"}
    assert data["deadline_at"] is not None


def test_results_before_any_call_are_pending_not_unavailable(client, session):
    shop(session)
    sid = client.post("/api/searches", json=body(), headers=HEADERS).json()["search_id"]
    data = client.get(f"/api/searches/{sid}/results").json()
    assert data["complete"] is False
    assert [r["result_state"] for r in data["results"]] == ["PENDING"]
    assert "unavailable" not in str(data["results"]).lower().replace("does not mean", "")


def test_no_answer_and_failed_calls_are_never_shown_as_unavailable(client, session):
    job = make_job(session, center_lat=CENTER["lat"], center_lng=CENTER["lng"], radius_km=3)
    for status in ("NO_ANSWER", "BUSY", "FAILED", "TIMED_OUT", "CANCELLED"):
        make_attempt(session, job, shop(session, status), status=status)
    data = client.get(f"/api/searches/{job.id}/results").json()
    states = {r["business"]["name"]: r["result_state"] for r in data["results"]}
    assert states == {
        "NO_ANSWER": "NO_ANSWER",
        "BUSY": "NO_ANSWER",
        "FAILED": "CALL_FAILED",
        "TIMED_OUT": "CALL_FAILED",
        "CANCELLED": "CANCELLED",
    }
    assert "REPORTED_UNAVAILABLE" not in states.values()
    for r in data["results"]:
        assert r["note"]


def _add_response(session, job, biz, attempt, availability="REPORTED_AVAILABLE", **over):
    fields = {
        "call_attempt_id": attempt.id,
        "search_job_id": job.id,
        "business_id": biz.id,
        "data_origin": "SIMULATED",
        "availability": availability,
        "exact_match": "CONFIRMED",
        "answer_summary": "Reported by phone: exact item available; price 42.",
        "evidence_excerpt": "Yes, we have it in stock",
        "evidence_validated": True,
        "extraction_status": "VALID",
        "price_amount": 42,
        "price_currency": "INR",
        "answer_timestamp": NOW - timedelta(minutes=10),
    }
    fields.update(over)
    session.add(BusinessResponse(**fields))
    session.commit()


def test_results_rank_available_first_and_include_evidence_and_freshness(client, session):
    job = make_job(session, center_lat=CENTER["lat"], center_lng=CENTER["lng"], radius_km=3)
    far_yes, near_no, near_unsure = (
        shop(session, "FarYes", dlat=0.02),
        shop(session, "NearNo", dlat=0.001),
        shop(session, "NearUnsure", dlat=0.002),
    )
    for biz, avail in (
        (far_yes, "REPORTED_AVAILABLE"),
        (near_no, "REPORTED_UNAVAILABLE"),
        (near_unsure, "UNCERTAIN"),
    ):
        att = make_attempt(session, job, biz, status="COMPLETED", provider="simulated")
        _add_response(session, job, biz, att, avail)
    data = client.get(f"/api/searches/{job.id}/results").json()
    assert [r["business"]["name"] for r in data["results"]] == ["FarYes", "NearUnsure", "NearNo"]
    first = data["results"][0]
    assert first["evidence"]["validated"] is True
    assert first["freshness"]["availability"] == "FRESH"
    assert first["reported"]["price"]["amount"] == 42.0
    assert first["data_origin"] == "SIMULATED"
    assert first["verification_status"] == "REPORTED_BY_PHONE"


def test_stale_answer_is_marked_stale(client, session):
    job = make_job(session, center_lat=CENTER["lat"], center_lng=CENTER["lng"], radius_km=3)
    biz = shop(session)
    att = make_attempt(session, job, biz, status="COMPLETED")
    _add_response(session, job, biz, att, answer_timestamp=NOW - timedelta(hours=3))
    data = client.get(f"/api/searches/{job.id}/results").json()
    assert data["results"][0]["freshness"]["availability"] == "STALE"


def test_latest_attempt_per_business_is_shown(client, session):
    job = make_job(session, center_lat=CENTER["lat"], center_lng=CENTER["lng"], radius_km=3)
    biz = shop(session)
    make_attempt(session, job, biz, attempt_number=1, status="NO_ANSWER")
    att2 = make_attempt(session, job, biz, attempt_number=2, status="COMPLETED")
    _add_response(session, job, biz, att2)
    data = client.get(f"/api/searches/{job.id}/results").json()
    assert len(data["results"]) == 1
    assert data["results"][0]["result_state"] == "REPORTED_AVAILABLE"


# --- cancel ----------------------------------------------------------------------------------


def test_cancel_marks_pending_attempts_and_is_idempotent(client, session):
    shop(session, "A")
    shop(session, "B", dlat=0.001)
    sid = client.post("/api/searches", json=body(), headers=HEADERS).json()["search_id"]
    assert client.post(f"/api/searches/{sid}/cancel", headers=HEADERS).json() == {
        "status": "CANCELLED"
    }
    assert client.post(f"/api/searches/{sid}/cancel", headers=HEADERS).json() == {
        "status": "CANCELLED"
    }
    data = client.get(f"/api/searches/{sid}").json()
    assert data["status"] == "CANCELLED"
    assert {a["status"] for a in data["attempts"]} == {"CANCELLED"}
    assert {a["result_state"] for a in data["attempts"]} == {"CANCELLED"}


def test_cancel_requires_the_key(client, session):
    shop(session)
    sid = client.post("/api/searches", json=body(), headers=HEADERS).json()["search_id"]
    assert client.post(f"/api/searches/{sid}/cancel").status_code == 401


def test_cancel_after_completion_is_a_noop(client, session):
    job = make_job(session, status="COMPLETED")
    r = client.post(f"/api/searches/{job.id}/cancel", headers=HEADERS)
    assert r.json() == {"status": "COMPLETED"}
