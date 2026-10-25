import uuid

import pytest
from pydantic import ValidationError

from app.providers.base import CallRequest, ProviderRejected
from app.providers.simulated import HOSTILE, SCENARIOS, SimulatedVoiceProvider

USER_DATA = {
    "category": "pharmacy",
    "item": "Paracetamol",
    "attributes_text": "strength 500 mg",
    "required_fields_text": "availability, price",
}
PHONE = "+910000000005"


def request(attempt_id=None, phone=PHONE, **over) -> CallRequest:
    fields = {
        "attempt_id": attempt_id or uuid.uuid4(),
        "agent_key": "pharmacy",
        "to_e164": phone,
        "user_data": USER_DATA,
    }
    fields.update(over)
    return CallRequest(**fields)


async def run(scenario: str):
    provider = SimulatedVoiceProvider({PHONE: scenario})
    ref = await provider.start_call(request())
    record = await provider.get_call(ref.provider_call_id)
    return provider, ref, record


@pytest.mark.parametrize("scenario", SCENARIOS)
async def test_every_scenario_reaches_a_terminal_provider_status(scenario):
    _, ref, record = await run(scenario)
    assert ref.provider == "simulated"
    assert ref.provider_status == "queued"
    assert record.provider_status in {"completed", "no-answer", "busy", "failed"}


@pytest.mark.parametrize("scenario", ["no_answer", "busy", "failed"])
async def test_unanswered_calls_have_no_transcript_or_extraction(scenario):
    _, _, record = await run(scenario)
    assert record.transcript is None and record.extracted is None


@pytest.mark.parametrize(
    "scenario",
    [
        "available",
        "available_no_price",
        "unavailable",
        "ambiguous",
        "alternative_only",
        "opt_out",
        "injection",
        "contradictory",
    ],
)
async def test_supporting_quote_appears_in_the_transcript(scenario):
    _, _, record = await run(scenario)
    assert record.extracted["supporting_quote"].lower() in record.transcript.lower()


async def test_evidence_missing_scenario_quote_is_not_in_transcript():
    _, _, record = await run("evidence_missing")
    assert record.extracted["supporting_quote"].lower() not in record.transcript.lower()


async def test_item_from_user_data_is_spoken():
    _, _, record = await run("available")
    assert "Paracetamol strength 500 mg" in record.transcript


async def test_available_scenario_has_a_price():
    _, _, record = await run("available")
    assert record.extracted["price_amount"] == 42
    assert "forty two rupees" in record.transcript


async def test_injection_scenario_carries_hostile_text():
    _, _, record = await run("injection")
    assert HOSTILE in record.transcript


async def test_opt_out_is_flagged():
    _, _, record = await run("opt_out")
    assert record.extracted["opt_out_requested"] == "yes"


async def test_voicemail_is_not_a_human():
    _, _, record = await run("voicemail")
    assert record.extracted["call_outcome"] == "voicemail"


async def test_deterministic_for_same_attempt():
    attempt = uuid.uuid4()
    p1, p2 = (
        SimulatedVoiceProvider({PHONE: "available"}),
        SimulatedVoiceProvider({PHONE: "available"}),
    )
    r1 = await p1.start_call(request(attempt))
    r2 = await p2.start_call(request(attempt))
    assert r1.provider_call_id == r2.provider_call_id
    assert (await p1.get_call(r1.provider_call_id)) == (await p2.get_call(r2.provider_call_id))


async def test_different_attempts_get_different_ids():
    provider = SimulatedVoiceProvider({PHONE: "available"})
    a = await provider.start_call(request())
    b = await provider.start_call(request())
    assert a.provider_call_id != b.provider_call_id
    assert provider.calls_started == 2


async def test_scenario_is_chosen_per_phone_number():
    provider = SimulatedVoiceProvider({PHONE: "unavailable"}, default="available")
    other = await provider.start_call(request(phone="+910000000006"))
    mine = await provider.start_call(request())
    assert "finished" in (await provider.get_call(mine.provider_call_id)).transcript
    assert "in stock" in (await provider.get_call(other.provider_call_id)).transcript


async def test_event_sequences():
    provider, ref, _ = await run("available")
    statuses = [e["status"] for e in provider.events_for(ref.provider_call_id)]
    assert statuses[0] == "queued" and statuses[-1] == "completed"
    assert (
        "call-disconnected" in statuses and statuses.index("call-disconnected") < len(statuses) - 1
    )


async def test_unanswered_event_sequence_ends_in_its_status():
    provider, ref, _ = await run("no_answer")
    assert provider.events_for(ref.provider_call_id)[-1]["status"] == "no-answer"


async def test_duplicate_and_reversed_events():
    provider, ref, _ = await run("available")
    base = provider.events_for(ref.provider_call_id)
    dup = provider.events_for(ref.provider_call_id, duplicate=True)
    rev = provider.events_for(ref.provider_call_id, reverse=True)
    assert len(dup) == 2 * len(base)
    assert [e["status"] for e in rev] == [e["status"] for e in reversed(base)]


async def test_unknown_call_id_is_rejected():
    with pytest.raises(ProviderRejected):
        await SimulatedVoiceProvider().get_call("sim-nope")


async def test_unknown_scenario_is_rejected():
    provider = SimulatedVoiceProvider({PHONE: "teleport"})
    with pytest.raises(ProviderRejected):
        await provider.start_call(request())


def test_unknown_default_scenario_is_rejected():
    with pytest.raises(ValueError):
        SimulatedVoiceProvider(default="teleport")


def test_call_request_rejects_non_e164_numbers():
    with pytest.raises(ValidationError):
        request(phone="9876543210")


def test_call_request_rejects_oversized_user_data():
    with pytest.raises(ValidationError):
        request(user_data={"item": "x" * 201})
