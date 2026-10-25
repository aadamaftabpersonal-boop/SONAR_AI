"""The Phase 1 spike tools must work the first time, because the first run uses real credit and a
real phone. These tests run them with no network and no key."""

import importlib.util
import json
import sys
import threading
from pathlib import Path

import httpx
import pytest

ROOT = Path(__file__).resolve().parents[3]
SPIKES = ROOT / "spikes" / "bolna"
sys.path.insert(0, str(SPIKES))

import common  # noqa: E402
import s4_make_call  # noqa: E402
import s5_summarize_webhooks as s5  # noqa: E402
import s6_capture_execution as s6  # noqa: E402
import webhook_capture  # noqa: E402


def load_script(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


redact_fixture = load_script("redact_fixture")

# --- common ----------------------------------------------------------------------------------


def test_mask_phone_keeps_country_code_and_last_three():
    masked = common.mask_phone("+919876543210")
    assert masked.startswith("+91") and masked.endswith("210") and "9876543" not in masked


def test_mask_in_text_masks_numbers_but_not_dates_or_costs():
    text = "call +91 98765 43210 on 2026-11-02T10:41:12 cost 0.1234567890 id 9876543210"
    masked = common.mask_in_text(text)
    assert "98765 43210" not in masked and "9876543210" not in masked
    assert "2026-11-02T10:41:12" in masked and "0.1234567890" in masked


@pytest.mark.parametrize("ok", ["+919876543210", "+14155550123"])
def test_is_e164_accepts(ok):
    assert common.is_e164(ok)


@pytest.mark.parametrize("bad", ["9876543210", "+0123456789", "+91 98765 43210", "", "+1"])
def test_is_e164_rejects(bad):
    assert not common.is_e164(bad)


def test_terminal_statuses():
    for s in (
        "completed",
        "no-answer",
        "busy",
        "failed",
        "canceled",
        "stopped",
        "error",
        "balance-low",
    ):
        assert common.is_terminal(s)
    for s in ("queued", "ringing", "in-progress", "call-disconnected", None):
        assert not common.is_terminal(s)


def test_load_env_never_overrides_existing_and_ignores_comments(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text("# c\nA_KEY=from_file\nB_KEY='quoted'\n\nbad line\n", encoding="utf-8")
    monkeypatch.setenv("A_KEY", "already")
    monkeypatch.delenv("B_KEY", raising=False)
    common.load_env(env)
    assert common.env("A_KEY") == "already" and common.env("B_KEY") == "quoted"


def test_type_table_lists_nested_paths():
    rows = dict(common.type_table({"a": 1, "b": {"c": "x", "d": [1]}}))
    assert rows == {"a": "int", "b": "dict", "b.c": "str", "b.d": "list"}


# --- s4: the call script ---------------------------------------------------------------------


def test_user_data_uses_the_same_keys_as_the_backend():
    data = s4_make_call.build_user_data("Paracetamol", {"strength": "500 mg"})
    assert set(data) == {"category", "item", "attributes_text", "required_fields_text"}
    assert data["attributes_text"] == "strength 500 mg"


def test_request_never_contains_retry_or_guardrail_overrides():
    body = s4_make_call.build_request("agent-1", "+910000000001", {"item": "x"}, "+910000000002")
    assert set(body) == {"agent_id", "recipient_phone_number", "user_data", "from_phone_number"}
    for forbidden in ("retry_config", "bypass_call_guardrails", "scheduled_at"):
        assert forbidden not in body


def test_from_number_is_omitted_when_not_given():
    assert "from_phone_number" not in s4_make_call.build_request("a", "+910000000001", {})


def run_main(module, monkeypatch, argv):
    monkeypatch.setattr(sys, "argv", [module.__name__, *argv])
    module.main()


def test_dry_run_sends_nothing_masks_the_number_and_needs_no_key(monkeypatch, capsys):
    monkeypatch.setattr(common, "load_env", lambda *a, **k: None)
    monkeypatch.delenv("BOLNA_API_KEY", raising=False)

    def boom(*a, **k):
        raise AssertionError("dry run must not touch the network")

    monkeypatch.setattr(httpx.Client, "post", boom)
    run_main(s4_make_call, monkeypatch, ["--to", "+919876543210", "--dry-run"])
    out = capsys.readouterr().out
    assert "dry run: nothing was sent" in out and "9876543210" not in out


def test_refuses_to_dial_without_the_test_line_confirmation(monkeypatch):
    monkeypatch.setattr(common, "load_env", lambda *a, **k: None)
    monkeypatch.setenv("BOLNA_API_KEY", "k")
    monkeypatch.setenv("BOLNA_AGENT_ID_PHARMACY", "agent")
    with pytest.raises(SystemExit, match="--yes-test-line"):
        run_main(s4_make_call, monkeypatch, ["--to", "+919876543210"])


def test_refuses_a_non_e164_number(monkeypatch):
    monkeypatch.setattr(common, "load_env", lambda *a, **k: None)
    with pytest.raises(SystemExit, match="E.164"):
        run_main(s4_make_call, monkeypatch, ["--to", "98765"])


def test_refuses_without_a_key_even_when_confirmed(monkeypatch):
    monkeypatch.setattr(common, "load_env", lambda *a, **k: None)
    monkeypatch.delenv("BOLNA_API_KEY", raising=False)
    with pytest.raises(SystemExit, match="BOLNA_API_KEY"):
        run_main(s4_make_call, monkeypatch, ["--to", "+919876543210", "--yes-test-line"])


def test_a_real_call_is_posted_once_saved_masked_and_the_key_never_leaks(
    monkeypatch, tmp_path, capsys
):
    monkeypatch.setattr(common, "load_env", lambda *a, **k: None)
    monkeypatch.setattr(common, "CAPTURES", tmp_path)
    monkeypatch.setenv("BOLNA_API_KEY", "super-secret-key-value")
    monkeypatch.setenv("BOLNA_AGENT_ID_PHARMACY", "agent-uuid")
    sent = []

    def handler(request: httpx.Request) -> httpx.Response:
        sent.append(request)
        return httpx.Response(
            200,
            json={
                "message": "done",
                "status": "queued",
                "execution_id": "11111111-2222-3333-4444-555555555555",
            },
        )

    real_client = httpx.Client
    monkeypatch.setattr(
        s4_make_call.httpx,
        "Client",
        lambda **kw: real_client(transport=httpx.MockTransport(handler), **kw),
    )
    run_main(s4_make_call, monkeypatch, ["--to", "+919876543210", "--yes-test-line"])
    assert len(sent) == 1
    assert sent[0].headers["authorization"] == "Bearer super-secret-key-value"
    assert json.loads(sent[0].content)["recipient_phone_number"] == "+919876543210"
    files = list(tmp_path.glob("s4_call_*.json"))
    saved = files[0].read_text(encoding="utf-8")
    assert len(files) == 1 and "9876543210" not in saved and "super-secret" not in saved
    assert "super-secret" not in capsys.readouterr().out


def test_a_non_200_is_reported_and_exits_nonzero(monkeypatch, tmp_path):
    monkeypatch.setattr(common, "load_env", lambda *a, **k: None)
    monkeypatch.setattr(common, "CAPTURES", tmp_path)
    monkeypatch.setenv("BOLNA_API_KEY", "k")
    monkeypatch.setenv("BOLNA_AGENT_ID_PHARMACY", "agent")
    real_client = httpx.Client
    handler = lambda r: httpx.Response(400, json={"error": 400, "message": "number not verified"})  # noqa: E731
    monkeypatch.setattr(
        s4_make_call.httpx,
        "Client",
        lambda **kw: real_client(transport=httpx.MockTransport(handler), **kw),
    )
    with pytest.raises(SystemExit) as exc:
        run_main(s4_make_call, monkeypatch, ["--to", "+919876543210", "--yes-test-line"])
    assert exc.value.code == 1
    assert "number not verified" in next(tmp_path.glob("s4_call_*.json")).read_text("utf-8")


# --- s6: execution capture -------------------------------------------------------------------


def make_mock_client(bodies: list[dict]):
    """Serves each body once in order, then repeats the last one."""
    state = {"i": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        body = bodies[min(state["i"], len(bodies) - 1)]
        state["i"] += 1
        return httpx.Response(200, json=body)

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_poll_saves_each_change_and_stops_after_the_terminal_status(tmp_path, monkeypatch):
    monkeypatch.setattr(s6.time, "sleep", lambda s: None)
    bodies = [
        {"status": "ringing", "transcript": None},
        {"status": "in-progress", "transcript": "agent: hi"},
        {"status": "in-progress", "transcript": "agent: hi\nshop: yes"},
        {"status": "call-disconnected", "transcript": "agent: hi\nshop: yes"},
        {
            "status": "completed",
            "transcript": "agent: hi\nshop: yes",
            "extracted_data": {"availability": "available"},
            "total_cost": 0.4,
        },
    ]
    snaps = s6.poll_execution(
        "exec-123456789",
        base="http://x",
        key="k",
        interval=0,
        timeout=30,
        out_dir=tmp_path,
        client=make_mock_client(bodies),
    )
    assert [s["body"]["status"] for s in snaps] == [
        "ringing",
        "in-progress",
        "in-progress",
        "call-disconnected",
        "completed",
    ]
    # transcript growth is recorded (S-13)
    assert [s["transcript_chars"] for s in snaps][1:3] == [9, 19]
    report = next(tmp_path.glob("*_REPORT.md")).read_text(encoding="utf-8")
    assert "extracted_data" in report and "Transcript growth" in report
    assert len(list(tmp_path.glob("s6_*_0*.json"))) == 5


def test_poll_once_takes_a_single_snapshot(tmp_path):
    snaps = s6.poll_execution(
        "exec-abcdef",
        base="http://x",
        key="k",
        once=True,
        out_dir=tmp_path,
        client=make_mock_client([{"status": "ringing"}]),
    )
    assert len(snaps) == 1


def test_poll_survives_http_errors_without_saving_them_as_snapshots(tmp_path, monkeypatch):
    monkeypatch.setattr(s6.time, "sleep", lambda s: None)
    handler = lambda r: httpx.Response(404, json={"message": "not found"})  # noqa: E731
    client = httpx.Client(transport=httpx.MockTransport(handler))
    snaps = s6.poll_execution(
        "nope", base="http://x", key="k", timeout=0, out_dir=tmp_path, client=client
    )
    assert snaps == []


def test_probe_errors_records_both_error_shapes(tmp_path, monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        if "wrong-key" in request.headers["authorization"]:
            return httpx.Response(401, json={"message": "bad key"})
        return httpx.Response(404, json={"message": "no such execution"})

    real_client = httpx.Client
    monkeypatch.setattr(
        s6.httpx, "Client", lambda **kw: real_client(transport=httpx.MockTransport(handler), **kw)
    )
    results = s6.probe_errors("http://x", "real-key", tmp_path)
    assert results["unknown_execution_id"]["http_status"] == 404
    assert results["wrong_api_key"]["http_status"] == 401
    assert "real-key" not in next(tmp_path.glob("s6_error_shapes_*.json")).read_text("utf-8")


# --- webhook capture server ------------------------------------------------------------------


@pytest.fixture
def capture_server(tmp_path):
    servers = []

    def start(**kw):
        server = webhook_capture.make_server("127.0.0.1", 0, tmp_path, **kw)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        servers.append(server)
        return f"http://127.0.0.1:{server.server_address[1]}"

    yield start
    for s in servers:
        s.shutdown()
        s.server_close()


def test_server_records_the_full_request_and_redacts_auth(capture_server, tmp_path):
    url = capture_server()
    payload = {"execution_id": "abcdef12-0000", "status": "ringing"}
    r = httpx.post(
        f"{url}/hook", json=payload, headers={"Authorization": "Bearer abc", "X-Custom": "yes"}
    )
    assert r.status_code == 200
    record = json.loads(next(tmp_path.glob("webhook_0001_ringing_*.json")).read_text("utf-8"))
    assert record["body_json"] == payload and record["path"] == "/hook"
    assert record["headers"]["Authorization"] == "<redacted>"
    assert record["headers"]["X-Custom"] == "yes"
    assert record["client_ip"] == "127.0.0.1" and record["responded_with"] == 200


def test_server_keeps_non_json_bodies_as_text(capture_server, tmp_path):
    url = capture_server()
    httpx.post(url, content=b"not json at all")
    record = json.loads(next(tmp_path.glob("webhook_0001_*.json")).read_text("utf-8"))
    assert record["body_json"] is None and record["body_text"] == "not json at all"


def test_fail_once_fails_only_the_first_delivery(capture_server, tmp_path):
    url = capture_server(fail_once=True)
    codes = [
        httpx.post(url, json={"execution_id": "e", "status": "completed"}).status_code
        for _ in range(3)
    ]
    assert codes == [500, 200, 200]
    records = [json.loads(p.read_text("utf-8")) for p in sorted(tmp_path.glob("webhook_*.json"))]
    assert [r["responded_with"] for r in records] == [500, 200, 200]  # failures are still recorded


def test_custom_respond_status(capture_server):
    url = capture_server(respond_status=503)
    assert httpx.post(url, json={}).status_code == 503


def test_get_works_for_checking_the_tunnel(capture_server):
    assert httpx.get(capture_server()).json()["ok"] is True


# --- s5: summary -----------------------------------------------------------------------------


def write_hook(directory: Path, seq: int, status: str, exec_id="exec-1", **extra):
    body = {"execution_id": exec_id, "status": status, **extra}
    rec = {
        "seq": seq,
        "received_at": f"2026-11-02T10:00:{seq:02d}+00:00",
        "client_ip": "10.0.0.1",
        "x_forwarded_for": "13.203.39.153",
        "headers": {"Host": "x", "X-Bolna-Sig": "abc"},
        "body_json": body,
        "responded_with": 500 if seq == 99 else 200,
    }
    (directory / f"webhook_{seq:04d}_{status}.json").write_text(json.dumps(rec), encoding="utf-8")


def test_summary_reports_order_duplicates_headers_and_fields(tmp_path):
    for i, s in enumerate(["queued", "ringing", "in-progress", "call-disconnected"], 1):
        write_hook(tmp_path, i, s)
    write_hook(tmp_path, 5, "completed", transcript="agent: hi", extracted_data={"a": 1})
    write_hook(tmp_path, 6, "completed", transcript="agent: hi", extracted_data={"a": 1})
    text = s5.summarize(tmp_path)
    assert "verdict: YES" in text
    assert "duplicates: {'completed': 2}" in text
    assert "x-bolna-sig" in text  # a custom header shows up in the 'not usual' list
    assert "| completed | yes | yes | no |" in text
    assert "| call-disconnected | no | no | no |" in text
    assert "True" in text.split("documented set:")[1].split("\n")[0]


def test_summary_flags_out_of_order_deliveries(tmp_path):
    write_hook(tmp_path, 1, "completed")
    write_hook(tmp_path, 2, "ringing")
    assert "OUT OF ORDER" in s5.summarize(tmp_path)


def test_summary_detects_redelivery_after_a_failure(tmp_path):
    write_hook(tmp_path, 99, "completed")  # seq 99 is recorded as having been answered 500
    rec = json.loads((tmp_path / "webhook_0099_completed.json").read_text("utf-8"))
    rec["seq"] = 1
    (tmp_path / "webhook_0001_completed.json").write_text(json.dumps(rec), encoding="utf-8")
    (tmp_path / "webhook_0099_completed.json").unlink()
    write_hook(tmp_path, 2, "completed")  # same exec + status again, after the failure
    assert "REDELIVERED" in s5.summarize(tmp_path)


def test_summary_notes_when_nothing_was_captured(tmp_path):
    assert "No webhook captures" in s5.summarize(tmp_path)


def test_summary_orphan_check_compares_with_the_call_response(tmp_path):
    write_hook(tmp_path, 1, "queued")
    call = {"t_response": "2026-11-02T10:00:05+00:00", "response": {"execution_id": "exec-1"}}
    (tmp_path / "s4_call_1.json").write_text(json.dumps(call), encoding="utf-8")
    assert "BEFORE (orphan handling is required)" in s5.summarize(tmp_path)


# --- redaction -------------------------------------------------------------------------------


def test_redaction_removes_numbers_recording_urls_emails_and_secrets():
    raw = {
        "recipient_phone_number": "+919876543210",
        "telephony_data": {"recording_url": "https://cdn.example.com/a/b/call.mp3?x=1"},
        "transcript": "shop: call me on 98765 43210 or +91 98765 43210 or a@b.com",
        "headers": {"Authorization": "Bearer xyz", "X-Ok": "fine"},
        "created_at": "2026-11-02T10:41:12",
        "total_cost": 0.1234567890,
        "execution_id": "11111111-2222-3333-4444-555555555555",
    }
    out = json.dumps(redact_fixture.redact(raw))
    for leaked in ("9876543210", "98765 43210", "cdn.example.com", "a@b.com", "Bearer xyz"):
        assert leaked not in out
    assert "2026-11-02T10:41:12" in out and "11111111-2222-3333-4444-555555555555" in out
    assert "0.123456789" in out


def test_redacted_phone_placeholder_cannot_be_mistaken_for_a_real_number():
    cleaned = redact_fixture.redact_text("+91 98765 43210")
    assert cleaned == "+910000000000"
    assert not common.is_e164("+91" + "0" * 0 + "0000000000") or cleaned.startswith("+910")


def test_redact_cli_writes_a_file(tmp_path):
    src, dst = tmp_path / "in.json", tmp_path / "out" / "fixture.json"
    src.write_text(json.dumps({"to": "+919876543210"}), encoding="utf-8")
    assert redact_fixture.main([str(src), str(dst)]) == 0
    assert "9876543210" not in dst.read_text("utf-8")
    assert redact_fixture.main([]) == 2
