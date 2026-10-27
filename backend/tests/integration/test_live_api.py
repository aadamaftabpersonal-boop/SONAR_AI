"""T15.1: GET /api/searches/{id}/live."""

import asyncio
import uuid

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_clock, get_session_factory
from app.config import Settings, get_settings
from app.db.session import get_session
from app.main import create_app
from app.providers.base import CallRequest
from app.providers.simulated import SimulatedVoiceProvider
from tests.factories import make_attempt, make_business, make_job
from tests.integration.test_api import KEY, NOW

pytestmark = pytest.mark.integration


@pytest.fixture
def setup(engine, session_factory):
    def build(flag=True):
        app = create_app()
        sim = SimulatedVoiceProvider({"+910000000077": "available"})
        app.state.providers.register("simulated", sim)

        def _session():
            with session_factory() as s:
                yield s

        app.dependency_overrides[get_session] = _session
        app.dependency_overrides[get_session_factory] = lambda: session_factory
        app.dependency_overrides[get_clock] = lambda: lambda: NOW
        app.dependency_overrides[get_settings] = lambda: Settings(
            _env_file=None, sonar_access_key=KEY, feature_live_ticker=flag
        )
        return TestClient(app), sim

    return build


def started_call(sim):
    req = CallRequest(attempt_id=uuid.uuid4(), agent_key="pharmacy", to_e164="+910000000077")
    return asyncio.run(sim.start_call(req)).provider_call_id


def test_flag_off_is_404(setup, session):
    client, _ = setup(flag=False)
    job = make_job(session)
    assert client.get(f"/api/searches/{job.id}/live").status_code == 404


def test_unknown_search_is_404(setup):
    client, _ = setup()
    assert client.get(f"/api/searches/{uuid.uuid4()}/live").status_code == 404
    assert client.get("/api/searches/not-a-uuid/live").status_code == 404


def test_simulated_call_in_progress_shows_lines(setup, session):
    client, sim = setup()
    job = make_job(session, demo_mode=True)
    shop = make_business(session, kind="REAL_BUSINESS", participation_status="CONSENTED")
    make_attempt(session, job, shop, status="IN_PROGRESS", provider_call_id=started_call(sim))
    [call] = client.get(f"/api/searches/{job.id}/live").json()["calls"]
    assert call["lines"] and call["lines"][0]["speaker"] == "Sonar assistant"
    assert call["reason"] is None


def test_real_business_on_a_live_call_is_never_shown(setup, session):
    client, _ = setup()
    job = make_job(session)
    shop = make_business(session, kind="REAL_BUSINESS", participation_status="CONSENTED")
    make_attempt(session, job, shop, provider="bolna", status="IN_PROGRESS", provider_call_id="x1")
    [call] = client.get(f"/api/searches/{job.id}/live").json()["calls"]
    assert call["lines"] == [] and call["reason"] == "not_shown"


def test_finished_and_pending_calls_are_not_listed(setup, session):
    client, _ = setup()
    job = make_job(session)
    make_attempt(session, job, make_business(session), status="PENDING")
    make_attempt(session, job, make_business(session), status="COMPLETED")
    assert client.get(f"/api/searches/{job.id}/live").json()["calls"] == []
