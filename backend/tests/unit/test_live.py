"""T15.1: the live ticker shows only what was transcribed, labelled, masked and capped."""

import uuid

from app.providers.base import CallRequest
from app.providers.simulated import SimulatedVoiceProvider
from app.services.live import LiveCache, may_show, ticker_lines

BOLNA_STYLE = (
    "assistant: Hello, this is an automated assistant calling for Sonar.\n"
    "user:  yes yes\n"
    "assistant:  Do you currently have Paracetamol 500 milligrams available?\n"
    "user:  yes we do, call me on 98765 43210\n"
)


def test_labels_are_ours_and_whitespace_is_tidied():
    lines = ticker_lines(BOLNA_STYLE)
    assert [line["speaker"] for line in lines] == ["Sonar assistant", "Shop"] * 2
    assert lines[1]["text"] == "yes yes"


def test_phone_numbers_are_masked():
    text = ticker_lines(BOLNA_STYLE)[-1]["text"]
    assert "98765" not in text and "43210" not in text


def test_only_the_last_lines_are_kept():
    assert len(ticker_lines(BOLNA_STYLE, max_lines=2)) == 2
    assert ticker_lines(BOLNA_STYLE, max_lines=2)[-1]["speaker"] == "Shop"
    assert ticker_lines(BOLNA_STYLE, max_lines=0) == []


def test_long_lines_are_capped():
    line = ticker_lines("user: " + "a" * 500, max_chars=200)[0]["text"]
    assert len(line) == 200 and line.endswith("…")


def test_nothing_is_invented_for_missing_or_unlabelled_text():
    assert ticker_lines(None) == []
    assert ticker_lines("") == []
    assert ticker_lines("recording: please leave a message\nno label here") == []


def test_markup_is_passed_as_plain_text_for_the_ui_to_escape():
    [line] = ticker_lines("user: <script>alert(1)</script>")
    assert line["text"] == "<script>alert(1)</script>"  # rendered as text, never as HTML


def test_only_test_lines_and_simulated_calls_are_shown():
    assert may_show("TEAM_TEST_LINE", "bolna")
    assert may_show("REAL_BUSINESS", "simulated")
    assert not may_show("REAL_BUSINESS", "bolna")


def test_cache_limits_pulls_per_call():
    now = [100.0]
    cache = LiveCache(min_interval=2.0, clock=lambda: now[0])
    assert cache.lookup("c1") == (False, None)
    cache.store("c1", "user: hi")
    assert cache.lookup("c1") == (True, "user: hi")
    now[0] += 2.5
    assert cache.lookup("c1") == (False, None)


async def test_simulator_reveals_its_script_line_by_line():
    now = [0.0]
    provider = SimulatedVoiceProvider(
        {"+910000000005": "available"}, clock=lambda: now[0], live_line_seconds=1.0
    )
    ref = await provider.start_call(
        CallRequest(
            attempt_id=uuid.uuid4(),
            agent_key="pharmacy",
            to_e164="+910000000005",
            user_data={"item": "Paracetamol", "attributes_text": "strength 500 mg"},
        )
    )
    first = await provider.live_transcript(ref.provider_call_id)
    assert first is not None and len(first.splitlines()) == 1
    now[0] = 2.5
    later = await provider.live_transcript(ref.provider_call_id)
    assert len(later.splitlines()) == 3
    now[0] = 1000
    full = (await provider.get_call(ref.provider_call_id)).transcript
    assert await provider.live_transcript(ref.provider_call_id) == full.rstrip("\n")


async def test_unanswered_simulated_calls_have_no_live_text():
    provider = SimulatedVoiceProvider({"+910000000006": "no_answer"})
    ref = await provider.start_call(
        CallRequest(attempt_id=uuid.uuid4(), agent_key="pharmacy", to_e164="+910000000006")
    )
    assert await provider.live_transcript(ref.provider_call_id) is None
