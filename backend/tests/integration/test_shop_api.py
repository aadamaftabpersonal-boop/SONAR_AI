# ruff: noqa: F811, F401  (pytest fixtures are imported from test_pipeline and used by name)
"""Shop digest page, opt-out, radar data, static serving and the retention job."""

from __future__ import annotations

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.api.deps import get_clock, get_session_factory
from app.config import get_settings
from app.db.models import AuditEvent, Business, CallAttempt
from app.db.session import get_session
from app.main import create_app
from app.services import digest as digest_mod
from tests.factories import make_attempt, make_business, make_job
from tests.integration.test_pipeline import (
    LAT,
    LNG,
    NOW,
    H,
    clock,
    providers,
    search_body,
    settings,
    shop,
    world,
)

pytestmark = pytest.mark.integration


def real_shop(world, name="Corner Pharmacy", phone="+910000051001", **over):
    return shop(
        world.session, name, phone, kind="REAL_BUSINESS", participation_status="CONSENTED", **over
    )


def searches_for(world, biz, n=3, item="Paracetamol"):
    for _ in range(n):
        job = make_job(world.session, parsed_query={"item_name": item, "category": "pharmacy"})
        make_attempt(world.session, job, biz, provider="bolna")
    world.session.commit()


def enable(world, biz):
    token = digest_mod.enable_digest(world.session, biz.id)
    world.session.commit()
    return token


# --- the digest API --------------------------------------------------------------------------


def test_the_digest_is_hidden_entirely_while_the_feature_is_off(world):
    biz = real_shop(world)
    token = enable(world, biz)
    assert world.settings.feature_digest is False
    assert world.client.get(f"/api/shop/{token}/digest").status_code == 404
    assert world.client.get(f"/shop/{token}").status_code == 404
    assert world.client.post(f"/api/shop/{token}/opt-out").status_code == 404


def test_a_wrong_token_and_a_disabled_feature_look_identical(world):
    biz = real_shop(world)
    token = enable(world, biz)
    off = world.client.get(f"/api/shop/{token}/digest")
    world.settings.feature_digest = True
    wrong = world.client.get("/api/shop/not-a-real-token/digest")
    assert off.status_code == wrong.status_code == 404
    assert off.json()["error"]["message"] == wrong.json()["error"]["message"]


def test_the_digest_json_shows_demand_without_identities_or_phone_numbers(world):
    world.settings.feature_digest = True
    biz = real_shop(world)
    searches_for(world, biz, 3)
    token = enable(world, biz)
    r = world.client.get(f"/api/shop/{token}/digest")
    assert r.status_code == 200
    data = r.json()
    assert data["business_name"] == "Corner Pharmacy" and data["window_days"] == 7
    assert data["lines"][0]["item"] == "paracetamol" and data["lines"][0]["searches"] == 3
    assert "+9100000" not in r.text and "searches, not people" in data["note"]


def test_counts_below_the_minimum_are_suppressed(world):
    world.settings.feature_digest = True
    biz = real_shop(world)
    searches_for(world, biz, 2)
    data = world.client.get(f"/api/shop/{enable(world, biz)}/digest").json()
    assert data["lines"] == [] and data["suppressed_lines"] == 1


def test_the_page_escapes_everything_it_prints(world):
    world.settings.feature_digest = True
    biz = real_shop(world, name="<script>alert(1)</script> Chemist")
    searches_for(world, biz, 3, item="<img src=x onerror=alert(2)>")
    token = enable(world, biz)
    page = world.client.get(f"/shop/{token}")
    assert page.status_code == 200 and "text/html" in page.headers["content-type"]
    assert "<script>alert(1)" not in page.text and "<img src=x" not in page.text
    assert "&lt;script&gt;" in page.text
    assert page.headers["cache-control"] == "no-store"
    assert 'name="robots" content="noindex"' in page.text
    assert "+9100000" not in page.text


def test_the_page_offers_a_way_to_stop_calls(world):
    world.settings.feature_digest = True
    biz = real_shop(world)
    page = world.client.get(f"/shop/{enable(world, biz)}")
    assert "Stop Sonar calling me" in page.text and "/opt-out" in page.text


def test_opting_out_stops_calls_immediately_and_everywhere(world):
    world.settings.feature_digest = True
    biz = real_shop(world, phone="+910000051002")
    token = enable(world, biz)
    queued = make_attempt(world.session, make_job(world.session), biz, provider="bolna")

    r = world.client.post(f"/api/shop/{token}/opt-out")
    assert r.status_code == 200 and r.json() == {"status": "OPTED_OUT"}

    world.session.expire_all()
    b = world.session.get(Business, biz.id)
    assert b.participation_status == "OPTED_OUT" and b.opted_out_at is not None
    assert not b.digest_opt_in
    assert world.session.get(CallAttempt, queued.id).status == "CANCELLED"
    assert (
        world.session.execute(
            select(func.count())
            .select_from(AuditEvent)
            .where(AuditEvent.action == "opt_out_via_digest")
        ).scalar_one()
        == 1
    )
    # the link now finds nothing, and the shop can no longer be planned into a search
    assert world.client.get(f"/api/shop/{token}/digest").status_code == 404
    again = world.client.post("/api/searches", json=search_body(demo_mode=True), headers=H).json()
    assert again["error_code"] == "NO_ELIGIBLE_BUSINESSES"


def test_opting_out_twice_is_harmless(world):
    world.settings.feature_digest = True
    biz = real_shop(world, phone="+910000051003")
    token = enable(world, biz)
    assert world.client.post(f"/api/shop/{token}/opt-out").status_code == 200
    assert world.client.post(f"/api/shop/{token}/opt-out").status_code == 404


# --- radar data ------------------------------------------------------------------------------


def test_searches_report_the_radius_and_each_shops_bearing(world):
    shop(world.session, "North", "+910000052001", dlat=0.01)
    r = world.client.post("/api/searches", json=search_body(demo_mode=True), headers=H).json()
    view = world.client.get(f"/api/searches/{r['search_id']}").json()
    assert view["radius_km"] == 3.0
    assert view["center_lat"] == pytest.approx(LAT) and view["center_lng"] == pytest.approx(LNG)
    ref = view["attempts"][0]["business"]
    assert ref["distance_km"] > 0 and (ref["bearing_deg"] < 1 or ref["bearing_deg"] > 359)


# --- serving the built frontend --------------------------------------------------------------


@pytest.fixture
def static_client(tmp_path, monkeypatch):
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<html>SONAR APP</html>", encoding="utf-8")
    (dist / "assets" / "app.js").write_text("console.log('hi')", encoding="utf-8")
    (tmp_path / "secret.txt").write_text("TOP SECRET", encoding="utf-8")
    monkeypatch.setenv("FRONTEND_DIST", str(dist))
    get_settings.cache_clear()
    yield TestClient(create_app())
    get_settings.cache_clear()


def test_the_api_serves_the_built_app_and_falls_back_to_it_for_routes(static_client):
    assert "SONAR APP" in static_client.get("/").text
    assert "SONAR APP" in static_client.get("/some/client/route").text
    assert static_client.get("/assets/app.js").text == "console.log('hi')"


def test_api_and_health_routes_are_never_shadowed(static_client):
    assert static_client.get("/health").json() == {"status": "ok"}
    r = static_client.get("/api/nope")
    assert r.status_code == 404 and r.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.parametrize(
    "path", ["/../secret.txt", "/%2e%2e/secret.txt", "/assets/../../secret.txt"]
)
def test_files_outside_the_build_folder_are_never_served(static_client, path):
    assert "TOP SECRET" not in static_client.get(path).text


def test_without_a_frontend_folder_nothing_extra_is_served(monkeypatch):
    monkeypatch.setenv("FRONTEND_DIST", "")
    get_settings.cache_clear()
    try:
        assert TestClient(create_app()).get("/").status_code == 404
    finally:
        get_settings.cache_clear()


# --- the retention job -----------------------------------------------------------------------


def test_maintenance_runs_the_purge_with_the_configured_windows(world):
    from app.db.models import ProviderEvent
    from app.db.repositories import EventRepo

    repo = EventRepo(world.session)
    repo.insert_or_ignore(
        provider="bolna", provider_call_id="a", provider_status="x", payload={"k": 1}
    )
    world.session.execute(
        ProviderEvent.__table__.update().values(received_at=NOW - timedelta(days=60))
    )
    world.session.commit()
    counts = world.orch.maintenance()
    assert counts["events_deleted"] == 1
    assert world.orch.maintenance() == {"events_deleted": 0, "responses_cleared": 0}
