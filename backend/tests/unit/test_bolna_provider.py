"""BolnaVoiceProvider against a mocked HTTP layer.

These payloads follow the DOCUMENTED contract (Bible 21.3), not captured responses. When the
Phase 1 spike captures real ones, re-base the field names in app/providers/bolna.py and replace
the payloads here with the redacted fixtures.
"""

import json
import logging
import uuid
from decimal import Decimal

import httpx
import pytest

from app.providers import bolna
from app.providers.base import (
    CallRequest,
    ProviderBalanceLow,
    ProviderRejected,
    ProviderTimeout,
    ProviderUnavailable,
)
from app.providers.bolna import (
    BolnaVoiceProvider,
    normalize_extracted,
    normalize_transcript,
)

KEY = "sk-test-key-do-not-leak-0123456789"
EXEC_ID = "11111111-2222-3333-4444-555555555555"
PHONE = "+910000000042"
USER_DATA = {
    "category": "pharmacy",
    "item": "Paracetamol",
    "attributes_text": "strength 500 mg",
    "required_fields_text": "availability, price",
}


def provider(handler, agent_ids=None, **kw):
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return BolnaVoiceProvider(
        KEY,
        agent_ids=agent_ids if agent_ids is not None else {"pharmacy": "agent-uuid"},
        client=client,
        **kw,
    )


def req(**over):
    fields = {
        "attempt_id": uuid.uuid4(),
        "agent_key": "pharmacy",
        "to_e164": PHONE,
        "user_data": USER_DATA,
    }
    fields.update(over)
    return CallRequest(**fields)


def respond(status=200, body=None, text=None):
    def handler(request):
        if text is not None:
            return httpx.Response(status, text=text)
        return httpx.Response(status, json=body if body is not None else {})

    return handler


OK_CALL = {"message": "done", "status": "queued", "execution_id": EXEC_ID}


# --- POST /call: the request ------------------------------------------------------------------


async def test_the_request_matches_the_documented_contract_exactly():
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(200, json=OK_CALL)

    await provider(handler).start_call(req())
    (r,) = seen
    assert r.method == "POST" and str(r.url) == "https://api.bolna.ai/call"
    assert r.headers["authorization"] == f"Bearer {KEY}"
    assert json.loads(r.content) == {
        "agent_id": "agent-uuid",
        "recipient_phone_number": PHONE,
        "user_data": USER_DATA,
    }


async def test_the_from_number_is_sent_only_when_given():
    bodies = []

    def handler(request):
        bodies.append(json.loads(request.content))
        return httpx.Response(200, json=OK_CALL)

    p = provider(handler)
    await p.start_call(req())
    await p.start_call(req(from_e164="+910000000099"))
    assert "from_phone_number" not in bodies[0]
    assert bodies[1]["from_phone_number"] == "+910000000099"


async def test_it_never_sets_retry_scheduling_or_guardrail_overrides():
    bodies = []

    def handler(request):
        bodies.append(json.loads(request.content))
        return httpx.Response(200, json=OK_CALL)

    await provider(handler).start_call(req(from_e164="+910000000099"))
    for forbidden in ("retry_config", "scheduled_at", "bypass_call_guardrails", "agent_data"):
        assert forbidden not in bodies[0]


async def test_the_agent_is_chosen_by_category():
    seen = []

    def handler(request):
        seen.append(json.loads(request.content)["agent_id"])
        return httpx.Response(200, json=OK_CALL)

    p = provider(handler, agent_ids={"pharmacy": "A", "computer_repair": "B"})
    await p.start_call(req(agent_key="computer_repair"))
    assert seen == ["B"]


async def test_a_missing_agent_fails_before_any_network_use():
    def handler(request):
        raise AssertionError("must not touch the network")

    with pytest.raises(ProviderRejected, match="no Bolna agent"):
        await provider(handler, agent_ids={}).start_call(req())
    assert not provider(handler, agent_ids={"x": ""}).has_agent("x")


def test_it_refuses_to_exist_without_a_key():
    with pytest.raises(ValueError):
        BolnaVoiceProvider("")


# --- POST /call: the response ------------------------------------------------------------------


async def test_a_200_becomes_a_call_reference():
    ref = await provider(respond(200, OK_CALL)).start_call(req())
    assert (ref.provider, ref.provider_call_id, ref.provider_status) == ("bolna", EXEC_ID, "queued")


@pytest.mark.parametrize("body", [{}, {"status": "queued"}, {"execution_id": ""}])
async def test_a_200_without_an_execution_id_is_an_unknown_outcome_not_a_failure(body):
    """The call may exist, so it must never be retried."""
    with pytest.raises(ProviderTimeout):
        await provider(respond(200, body)).start_call(req())


async def test_a_200_that_is_not_json_is_an_unknown_outcome():
    with pytest.raises(ProviderTimeout):
        await provider(respond(200, text="<html>ok</html>")).start_call(req())


async def test_a_400_is_a_rejection_carrying_the_message():
    body = {"error": 400, "message": "recipient_phone_number is not a verified number"}
    with pytest.raises(ProviderRejected, match="not a verified number"):
        await provider(respond(400, body)).start_call(req())


@pytest.mark.parametrize(
    "message", ["Insufficient balance", "wallet is empty", "Not enough credits"]
)
async def test_a_400_about_balance_pauses_dispatching(message):
    with pytest.raises(ProviderBalanceLow):
        await provider(respond(400, {"error": 400, "message": message})).start_call(req())


@pytest.mark.parametrize("status", [401, 403])
async def test_a_rejected_key_is_a_rejection_that_says_what_to_check(status):
    with pytest.raises(ProviderRejected, match="BOLNA_API_KEY"):
        await provider(respond(status, {"message": "nope"})).start_call(req())


@pytest.mark.parametrize("status", [404, 409, 422])
async def test_other_4xx_are_rejections(status):
    with pytest.raises(ProviderRejected):
        await provider(respond(status, {"message": "x"})).start_call(req())


async def test_a_rate_limit_is_retryable():
    with pytest.raises(ProviderUnavailable):
        await provider(respond(429, {"message": "slow down"})).start_call(req())


@pytest.mark.parametrize("status", [500, 502, 503, 504])
async def test_a_5xx_is_an_unknown_outcome_never_a_retry(status):
    """No idempotency key (A-11): a 5xx may have started the call, so we must not redial."""
    with pytest.raises(ProviderTimeout):
        await provider(respond(status, {"message": "boom"})).start_call(req())


def failing(exc):
    def handler(request):
        raise exc

    return handler


@pytest.mark.parametrize(
    "exc",
    [httpx.ConnectError("refused"), httpx.ConnectTimeout("slow"), httpx.PoolTimeout("busy")],
)
async def test_failures_before_the_request_left_are_safe_to_retry(exc):
    with pytest.raises(ProviderUnavailable):
        await provider(failing(exc)).start_call(req())


@pytest.mark.parametrize(
    "exc",
    [
        httpx.ReadTimeout("slow"),
        httpx.WriteTimeout("slow"),
        httpx.RemoteProtocolError("cut"),
        httpx.ReadError("reset"),
    ],
)
async def test_failures_after_the_request_may_have_left_are_unknown_never_retried(exc):
    with pytest.raises(ProviderTimeout):
        await provider(failing(exc)).start_call(req())


# --- secrets and privacy ----------------------------------------------------------------------


@pytest.mark.parametrize("status", [400, 401, 429, 500])
async def test_the_key_never_appears_in_an_error(status):
    with pytest.raises(
        (ProviderRejected, ProviderBalanceLow, ProviderUnavailable, ProviderTimeout)
    ) as exc:
        await provider(respond(status, {"message": "bad"})).start_call(req())
    assert KEY not in str(exc.value) and KEY not in repr(exc.value)


async def test_a_transport_error_does_not_echo_the_url_or_key():
    with pytest.raises(ProviderUnavailable) as exc:
        await provider(
            failing(httpx.ConnectError(f"cannot connect to https://x/{KEY}"))
        ).start_call(req())
    assert KEY not in str(exc.value)


async def test_logs_never_contain_the_key_or_the_full_number(caplog):
    caplog.set_level(logging.DEBUG)
    await provider(respond(200, OK_CALL)).start_call(req())
    text = caplog.text
    assert KEY not in text and PHONE not in text
    assert "queued to" in text  # it does log that a call went out, masked


# --- GET /executions/{id} ----------------------------------------------------------------------


COMPLETED = {
    "id": EXEC_ID,
    "status": "completed",
    "transcript": "agent: Do you have it?\nshop: Yes, we have it in stock.\n",
    "conversation_duration": 38.4,
    "total_cost": 0.42,
    "extracted_data": {
        "availability": "available",
        "exact_match_confirmed": "yes",
        "price_amount": 42,
        "supporting_quote": "Yes, we have it in stock",
    },
    "telephony_data": {"recording_url": "https://cdn.example.com/call.mp3", "to_number": PHONE},
}


async def test_the_execution_request_matches_the_contract():
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(200, json=COMPLETED)

    await provider(handler).get_call(EXEC_ID)
    (r,) = seen
    assert r.method == "GET" and str(r.url) == f"https://api.bolna.ai/executions/{EXEC_ID}"
    assert r.headers["authorization"] == f"Bearer {KEY}"


async def test_a_completed_execution_is_mapped_to_a_record():
    rec = await provider(respond(200, COMPLETED)).get_call(EXEC_ID)
    assert rec.provider_call_id == EXEC_ID and rec.provider_status == "completed"
    assert rec.transcript.startswith("agent: Do you have it?")
    assert rec.duration_seconds == 38 and rec.cost_amount == Decimal("0.42")
    assert rec.extracted["availability"] == "available" and rec.extracted["price_amount"] == 42
    assert rec.cost_currency is None  # unknown until the spike shows what the field means


async def test_the_raw_record_is_redacted():
    rec = await provider(respond(200, COMPLETED)).get_call(EXEC_ID)
    dumped = json.dumps(rec.raw)
    assert "cdn.example.com" not in dumped and PHONE not in dumped
    assert rec.raw["telephony_data"]["recording_url"] == "<redacted>"
    assert rec.raw["status"] == "completed"


async def test_the_provider_status_string_is_preserved_untouched():
    rec = await provider(respond(200, {"status": "some-new-status"})).get_call(EXEC_ID)
    assert rec.provider_status == "some-new-status"  # mapping is the state machine's job


async def test_a_call_that_never_connected_has_no_transcript_or_extraction():
    rec = await provider(respond(200, {"status": "no-answer"})).get_call(EXEC_ID)
    assert (rec.transcript, rec.extracted, rec.duration_seconds, rec.cost_amount) == (
        None,
        None,
        None,
        None,
    )


@pytest.mark.parametrize("bad", ["lots", "NaN", "Infinity", None, True, -5])
async def test_a_bad_cost_or_duration_becomes_none_not_a_crash(bad):
    body = {"status": "completed", "total_cost": bad, "conversation_duration": bad}
    rec = await provider(respond(200, body)).get_call(EXEC_ID)
    assert rec.cost_amount is None  # unknown, never a nonsense value
    assert rec.duration_seconds is None
    assert rec.duration_seconds is None


async def test_execution_errors_are_mapped_safely():
    with pytest.raises(ProviderRejected, match="no such execution"):
        await provider(respond(404, {"message": "nope"})).get_call(EXEC_ID)
    with pytest.raises(ProviderRejected, match="BOLNA_API_KEY"):
        await provider(respond(401, {})).get_call(EXEC_ID)
    for status in (429, 500, 503):
        with pytest.raises(ProviderUnavailable):
            await provider(respond(status, {})).get_call(EXEC_ID)


async def test_reads_that_fail_in_transit_are_retryable():
    for exc in (httpx.ReadTimeout("t"), httpx.ConnectError("c"), httpx.RemoteProtocolError("r")):
        with pytest.raises(ProviderUnavailable):
            await provider(failing(exc)).get_call(EXEC_ID)


async def test_a_non_json_execution_is_retryable():
    with pytest.raises(ProviderUnavailable):
        await provider(respond(200, text="<html>")).get_call(EXEC_ID)
    with pytest.raises(ProviderUnavailable):
        await provider(respond(200, text="[1, 2]")).get_call(EXEC_ID)


# --- the shapes the documentation disagrees about ---------------------------------------------


def test_transcript_as_a_string_or_a_list_of_turns():
    assert normalize_transcript("agent: hi") == "agent: hi"
    turns = [
        {"role": "assistant", "content": "Hello"},
        {"speaker": "user", "text": "Yes"},
        "raw line",
    ]
    assert normalize_transcript(turns) == "assistant: Hello\nuser: Yes\nraw line"
    for empty in (None, "", [], 7, {}):
        assert normalize_transcript(empty) is None


def test_flat_extracted_data():
    out = normalize_extracted({"availability": "available", "price_amount": 42, "ignored": "x"})
    assert out == {"availability": "available", "price_amount": 42}


def test_nested_extracted_data_by_category():
    nested = {
        "stock": {"availability": "not_available", "exact_match_confirmed": "no"},
        "other": {"price_amount": 10},
    }
    assert normalize_extracted(nested) == {
        "availability": "not_available",
        "exact_match_confirmed": "no",
        "price_amount": 10,
    }


def test_wrapped_answers_with_confidence_keep_the_lowest_confidence_raw():
    data = {
        "availability": {"objective": "available", "confidence": 0.9},
        "supporting_quote": {"subjective": "Yes we have it", "confidence": 0.4},
        "price_amount": {"value": 42},
    }
    out = normalize_extracted(data)
    assert out["availability"] == "available" and out["supporting_quote"] == "Yes we have it"
    assert out["price_amount"] == 42 and out["confidence"] == 0.4


def test_blank_answers_become_none_so_unknown_stays_unknown():
    out = normalize_extracted(
        {"availability": "available", "price_amount": "", "alternative_offered": {"subjective": ""}}
    )
    assert out["price_amount"] is None and out["alternative_offered"] is None


@pytest.mark.parametrize(
    "junk", [None, {}, [], "text", {"unrelated": 1}, {"group": {"nothing": 1}}]
)
def test_extracted_data_with_nothing_we_know_is_none(junk):
    assert normalize_extracted(junk) is None


# --- registration: live calling can never switch itself on --------------------------------------


def make_registry(**over):
    from app.config import Settings
    from app.main import default_providers

    return default_providers(Settings(_env_file=None, **over))


def test_without_a_key_only_the_simulator_exists():
    registry = make_registry()
    assert registry.has("simulated") and not registry.has("bolna")


def test_a_key_without_an_agent_does_not_enable_live_calling():
    assert not make_registry(bolna_api_key="sk-x").has("bolna")


def test_an_agent_without_a_key_does_not_enable_live_calling():
    assert not make_registry(bolna_agent_id_pharmacy="agent").has("bolna")


def test_a_key_and_an_agent_enable_it_for_exactly_that_category():
    registry = make_registry(bolna_api_key="sk-x", bolna_agent_id_pharmacy="agent")
    live = registry.get("bolna")
    assert live.has_agent("pharmacy") and not live.has_agent("computer_repair")


def test_field_names_live_in_one_block():
    """The single place to re-base when real payloads arrive."""
    for name in (
        "CALL_RESPONSE_ID",
        "EXEC_STATUS",
        "EXEC_TRANSCRIPT",
        "EXEC_DURATION",
        "EXEC_COST",
        "EXEC_EXTRACTED",
        "KNOWN_EXTRACTIONS",
    ):
        assert hasattr(bolna, name)


def test_every_extraction_the_validator_reads_is_known():
    from app.services import validator

    source = open(validator.__file__, encoding="utf-8").read()
    for name in bolna.KNOWN_EXTRACTIONS - {"call_outcome"}:
        assert name in source or name == "open_now", name
