"""Milestone M1 (Build Map T6.7): one real call, end to end, readable through the API.

Places a REAL call. Never runs by default: it needs RUN_LIVE=1 and `-m live`. Run it once per M1
run, against a running server, with the phone of a verified TEAM_TEST_LINE in range:

    RUN_LIVE=1 M1_EXPECT=REPORTED_AVAILABLE pytest -m live tests/live -s

Environment:
    SONAR_BASE_URL      default http://localhost:8000
    SONAR_ACCESS_KEY    the server's access key (X-Sonar-Key)
    M1_LAT, M1_LNG      the search point (near the test line in data/businesses.local.yaml)
    M1_RADIUS_KM        default 3
    M1_ITEM, M1_STRENGTH  default Paracetamol / 500 mg
    M1_EXPECT           the state you will play on the phone: REPORTED_AVAILABLE,
                        REPORTED_UNAVAILABLE, UNCERTAIN or NO_ANSWER (let it ring out)
    M1_EXPECT_CALLS     how many shops should be called, default 1
    M1_TIMEOUT_S        default 420
    DATABASE_URL        optional; enables the row-level checks (one response row, timestamps)

Paste the printed summary into docs/M1_EVIDENCE.md. It masks nothing because it prints no phone
numbers; still read it before committing.
"""

from __future__ import annotations

import json
import os
import time

import httpx
import pytest

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(os.environ.get("RUN_LIVE") != "1", reason="places a real call"),
]

ANSWERED = {"REPORTED_AVAILABLE", "REPORTED_UNAVAILABLE", "UNCERTAIN", "ALTERNATIVE_ONLY"}
TERMINAL = {"COMPLETED", "COMPLETED_PARTIAL", "FAILED", "CANCELLED"}


def _env(name: str, default: str | None = None) -> str:
    value = os.environ.get(name, default)
    if value is None or value == "":
        pytest.fail(f"set {name} (see the module docstring)")
    return value


def test_m1_one_real_call_end_to_end():
    base = _env("SONAR_BASE_URL", "http://localhost:8000").rstrip("/")
    headers = {"X-Sonar-Key": _env("SONAR_ACCESS_KEY")}
    expect = _env("M1_EXPECT")
    expect_calls = int(_env("M1_EXPECT_CALLS", "1"))
    timeout = float(_env("M1_TIMEOUT_S", "420"))
    body = {
        "query_text": "M1 live run",
        "category": "pharmacy",
        "item": {
            "name": _env("M1_ITEM", "Paracetamol"),
            "attributes": {"strength": _env("M1_STRENGTH", "500 mg")},
        },
        "location": {"lat": float(_env("M1_LAT")), "lng": float(_env("M1_LNG"))},
        "radius_km": float(_env("M1_RADIUS_KM", "3")),
        "demo_mode": False,
        "mode": "THOROUGH",  # M1 checks one call; never let the stop rule skip it
    }

    with httpx.Client(base_url=base, timeout=20) as client:
        created = client.post("/api/searches", json=body, headers=headers)
        assert created.status_code in (200, 201, 202), created.text
        search_id = created.json()["search_id"]
        print(f"\nsearch_id {search_id}")

        started = time.monotonic()
        search = {}
        while time.monotonic() - started < timeout:
            search = client.get(f"/api/searches/{search_id}").json()
            states = [a["status"] for a in search.get("attempts", [])]
            print(f"  {int(time.monotonic() - started):>4}s  {search['status']}  {states}")
            if search["status"] in TERMINAL:
                break
            time.sleep(5)
        assert search.get("status") in TERMINAL, "search did not finish in time"

        results = client.get(f"/api/searches/{search_id}/results").json()

    summary = {
        "search_id": search_id,
        "search_status": search["status"],
        "seconds": round(time.monotonic() - started),
        "results": [
            {
                "kind": r["business"].get("kind"),
                "result_state": r["result_state"],
                "data_origin": r["data_origin"],
                "summary": r.get("answer_summary"),
                "evidence": (r.get("evidence") or {}).get("excerpt"),
                "evidence_validated": (r.get("evidence") or {}).get("validated"),
                "flags": r.get("flags"),
            }
            for r in results["results"]
        ],
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))

    assert len(search["attempts"]) == expect_calls
    assert all(r["data_origin"] == "LIVE_CALL" for r in results["results"]), "not a live call"
    states = [r["result_state"] for r in results["results"]]
    assert expect in states, f"played {expect}, Sonar recorded {states}"
    for r in results["results"]:
        if r["result_state"] in {"REPORTED_AVAILABLE", "REPORTED_UNAVAILABLE"}:
            assert r["evidence"]["validated"] and r["evidence"]["excerpt"]
        if r["result_state"] == "NO_ANSWER":
            assert not r.get("reported"), "an unanswered call must have no response row"

    if os.environ.get("DATABASE_URL"):
        _check_rows(search_id, expect)


def _check_rows(search_id: str, expect: str) -> None:
    from sqlalchemy import create_engine, text

    url = os.environ["DATABASE_URL"]
    with create_engine(url).connect() as db:
        attempts = db.execute(
            text(
                "SELECT id, started_at, answered_at, completed_at, cost_amount, cost_currency "
                "FROM call_attempts WHERE search_job_id = :s"
            ),
            {"s": search_id},
        ).all()
        responses = db.execute(
            text("SELECT data_origin FROM business_responses WHERE search_job_id = :s"),
            {"s": search_id},
        ).all()
    print(f"  attempts {len(attempts)}, response rows {len(responses)}")
    for a in attempts:
        print(f"  started {a.started_at} answered {a.answered_at} completed {a.completed_at}")
        print(f"  cost {a.cost_amount} {a.cost_currency or '(unit not confirmed)'}")
        stamps = [t for t in (a.started_at, a.answered_at, a.completed_at) if t is not None]
        assert stamps == sorted(stamps), "timestamps out of order"
    if expect == "NO_ANSWER":
        assert responses == []
    elif expect in ANSWERED:
        assert len(responses) == 1 and responses[0].data_origin == "LIVE_CALL"
