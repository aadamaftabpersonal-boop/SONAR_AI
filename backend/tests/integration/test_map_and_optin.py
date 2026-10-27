"""D-059..D-061: nearby shops for the map, OpenStreetMap discovery, shop self opt-in."""

import json
from datetime import timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.api.deps import get_clock
from app.config import Settings, get_settings
from app.db.models import AuditEvent, Business
from app.db.session import get_session
from app.main import create_app
from app.services import osm
from app.services.optin_store import InviteRefused, issue_invite
from app.services.selector import CALLABLE
from tests.factories import make_business
from tests.integration.test_api import CENTER, HEADERS, KEY, NOW

pytestmark = pytest.mark.integration
FIXTURE = Path(__file__).parents[1] / "fixtures" / "osm" / "overpass_pharmacies.json"
NEAR = {"category": "pharmacy", "lat": CENTER["lat"], "lng": CENTER["lng"], "radius_km": 3}


@pytest.fixture
def client(engine, session_factory):
    def build(**flags):
        app = create_app()

        def _session():
            with session_factory() as s:
                yield s

        app.dependency_overrides[get_session] = _session
        app.dependency_overrides[get_clock] = lambda: lambda: NOW
        app.dependency_overrides[get_settings] = lambda: Settings(
            _env_file=None, sonar_access_key=KEY, **flags
        )
        return TestClient(app)

    return build


def here(session, **over):
    return make_business(session, latitude=CENTER["lat"], longitude=CENTER["lng"], **over)


# --- nearby ----------------------------------------------------------------------------------


def test_nearby_lists_joined_and_not_joined_but_never_phones_or_refusals(client, session):
    here(session, name="Joined")
    here(
        session,
        name="Not joined",
        kind="REAL_BUSINESS",
        participation_status="INVITED",
        consent_recorded_at=None,
    )
    here(
        session,
        name="Said no",
        kind="REAL_BUSINESS",
        participation_status="DECLINED",
        consent_recorded_at=None,
    )
    here(
        session,
        name="Stopped",
        kind="REAL_BUSINESS",
        participation_status="OPTED_OUT",
        consent_recorded_at=None,
        opted_out_at=NOW,
    )
    r = client().get("/api/businesses/nearby", params=NEAR)
    assert r.status_code == 200
    by_name = {b["name"]: b for b in r.json()["businesses"]}
    assert set(by_name) == {"Joined", "Not joined"}
    assert by_name["Joined"]["contactable"] and not by_name["Not joined"]["contactable"]
    assert "phone" not in r.text and "+91" not in r.text


def test_nearby_respects_the_plan_radius(client):
    r = client().get("/api/businesses/nearby", params={**NEAR, "radius_km": 5, "plan": "FREE"})
    assert r.status_code == 422 and "Free plan" in r.json()["error"]["message"]


# --- discovery -------------------------------------------------------------------------------


def fake_overpass(monkeypatch):
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    monkeypatch.setattr(osm, "fetch", lambda url, query, timeout: payload)


def test_discover_is_off_by_default(client):
    r = client().post("/api/businesses/discover", json=NEAR, headers=HEADERS)
    assert r.status_code == 404


def test_discover_needs_the_access_key(client):
    r = client(feature_discovery=True).post("/api/businesses/discover", json=NEAR)
    assert r.status_code == 401


def test_discovered_shops_are_invited_and_never_callable(client, session, monkeypatch):
    fake_overpass(monkeypatch)
    r = client(feature_discovery=True).post("/api/businesses/discover", json=NEAR, headers=HEADERS)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["new"] == 2 and body["without_phone"] == 1
    assert "OpenStreetMap" in body["attribution"]
    found = session.execute(select(Business).where(Business.source == "osm")).scalars().all()
    assert {b.participation_status for b in found} == {"INVITED"}
    assert not any(b.participation_status in CALLABLE for b in found)


def test_discovery_never_touches_a_consent_decision(client, session, monkeypatch):
    fake_overpass(monkeypatch)
    stopped = here(
        session,
        name="Stopped",
        phone_e164="+910000900101",
        kind="REAL_BUSINESS",
        participation_status="OPTED_OUT",
        consent_recorded_at=None,
        opted_out_at=NOW,
    )
    client(feature_discovery=True).post("/api/businesses/discover", json=NEAR, headers=HEADERS)
    session.refresh(stopped)
    assert stopped.participation_status == "OPTED_OUT" and stopped.name == "Stopped"


def test_overpass_failure_is_reported_not_retried(client, monkeypatch):
    calls = []

    def boom(url, query, timeout):
        calls.append(1)
        raise ConnectionError("down")

    monkeypatch.setattr(osm, "fetch", boom)
    r = client(feature_discovery=True).post("/api/businesses/discover", json=NEAR, headers=HEADERS)
    assert r.status_code == 503 and len(calls) == 1


# --- self opt-in -----------------------------------------------------------------------------


def invited(session):
    return here(
        session,
        name="Fixture Medicals",
        kind="REAL_BUSINESS",
        participation_status="INVITED",
        consent_recorded_at=None,
    )


AGREE = {
    "authorised": True,
    "understands_ai_calls": True,
    "contact_name": "Ravi",
    "call_window": "10:00-13:00",
    "language": "en",
}


def test_invite_link_lets_the_shop_opt_in_itself(client, session):
    shop = invited(session)
    token = issue_invite(session, shop.id, "teammate-a", NOW, 14)
    session.commit()
    c = client(feature_opt_in=True)
    page = c.get(f"/join/{token}")
    assert page.status_code == 200 and "AI assistant" in page.text and "transcribed" in page.text
    r = c.post(f"/api/join/{token}", json=AGREE)
    assert r.status_code == 200 and r.json()["stop_path"].startswith("/stop/")
    session.refresh(shop)
    assert shop.participation_status == "CONSENTED" and shop.consent_source == "SELF_OPT_IN"
    assert shop.consent_recorded_at is not None and "Self opt-in" in shop.consent_note
    assert shop.best_call_window == "10:00-13:00 IST"
    # single use
    assert c.post(f"/api/join/{token}", json=AGREE).status_code == 404


def test_both_boxes_are_required(client, session):
    shop = invited(session)
    token = issue_invite(session, shop.id, "teammate-a", NOW, 14)
    session.commit()
    r = client(feature_opt_in=True).post(f"/api/join/{token}", json={**AGREE, "authorised": False})
    assert r.status_code == 422
    session.refresh(shop)
    assert shop.participation_status == "INVITED"


def test_expired_unknown_or_flag_off_links_are_404(client, session):
    shop = invited(session)
    token = issue_invite(session, shop.id, "teammate-a", NOW - timedelta(days=20), 14)
    session.commit()
    assert client(feature_opt_in=True).get(f"/join/{token}").status_code == 404
    assert client(feature_opt_in=True).get("/join/not-a-real-token").status_code == 404
    fresh = issue_invite(session, shop.id, "teammate-a", NOW, 14)
    session.commit()
    assert client().get(f"/join/{fresh}").status_code == 404


def test_opted_out_shops_are_never_invited(session):
    shop = here(
        session,
        kind="REAL_BUSINESS",
        participation_status="OPTED_OUT",
        consent_recorded_at=None,
        opted_out_at=NOW,
    )
    with pytest.raises(InviteRefused):
        issue_invite(session, shop.id, "teammate-a", NOW, 14)


def test_stop_link_works_even_with_the_feature_off(client, session):
    shop = invited(session)
    token = issue_invite(session, shop.id, "teammate-a", NOW, 14)
    session.commit()
    stop_path = (
        client(feature_opt_in=True).post(f"/api/join/{token}", json=AGREE).json()["stop_path"]
    )
    assert client().get(stop_path).status_code == 200
    assert client().post("/api" + stop_path).status_code == 200
    session.refresh(shop)
    assert shop.participation_status == "OPTED_OUT" and shop.opted_out_at is not None
    actions = session.execute(select(AuditEvent.action)).scalars().all()
    assert {"self_opt_in", "opt_out_via_stop_link"} <= set(actions)


def test_public_request_is_never_callable_and_reveals_nothing(client, session):
    c = client(feature_opt_in=True)
    body = {
        "shop_name": "New Chemist",
        "area": "Example Nagar",
        "category": "pharmacy",
        "phone": "98765 43210",
    }
    assert c.post("/api/join-request", json=body).json() == {"status": "received"}
    shop = session.execute(select(Business).where(Business.name == "New Chemist")).scalar_one()
    assert shop.participation_status == "INVITED" and shop.opt_in_requested_at is not None
    # an opted-out shop asking again is not revived, and the reply is identical
    stopped = here(
        session,
        name="Stopped",
        kind="REAL_BUSINESS",
        participation_status="OPTED_OUT",
        consent_recorded_at=None,
        opted_out_at=NOW,
        phone_e164="+910000900999",
    )
    again = {**body, "shop_name": "Stopped", "phone": "+91 00009 00999"}
    assert c.post("/api/join-request", json=again).json() == {"status": "received"}
    session.refresh(stopped)
    assert stopped.participation_status == "OPTED_OUT"


def test_honeypot_requests_are_dropped(client, session):
    c = client(feature_opt_in=True)
    body = {
        "shop_name": "Bot Shop",
        "area": "x",
        "category": "pharmacy",
        "phone": "98765 43210",
        "website": "http://spam.example",
    }
    assert c.post("/api/join-request", json=body).status_code == 200
    assert session.execute(select(Business).where(Business.name == "Bot Shop")).first() is None


def test_join_pages_escape_shop_names(client, session):
    shop = here(
        session,
        name="<script>x</script>",
        kind="REAL_BUSINESS",
        participation_status="INVITED",
        consent_recorded_at=None,
    )
    token = issue_invite(session, shop.id, "teammate-a", NOW, 14)
    session.commit()
    page = client(feature_opt_in=True).get(f"/join/{token}").text
    assert "<script>x</script>" not in page and "&lt;script&gt;" in page
