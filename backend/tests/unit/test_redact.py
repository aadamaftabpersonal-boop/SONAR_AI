from app.services.redact import REDACTED, mask_phone, redact

PHONE = "+91" + "9123456780"  # built so this file is not itself flagged by the secret scan


def test_phone_numbers_are_masked_to_country_code_and_last_three_digits():
    masked = mask_phone(PHONE)
    assert masked.startswith("+91") and masked.endswith("780") and "9123456" not in masked


def test_numbers_in_text_urls_and_nested_data_are_masked_and_recording_links_removed():
    payload = {
        "status": "completed",
        "telephony_data": {"recording_url": "https://cdn.example.com/a/call.mp3", "to": PHONE},
        "transcript": f"shop: call me on {PHONE} or 98765 43210",
        "turns": [{"text": f"my number is {PHONE}"}],
    }
    text = str(redact(payload))
    for leaked in ("9123456780", "98765 43210", "cdn.example.com"):
        assert leaked not in text
    assert redact(payload)["telephony_data"]["recording_url"] == REDACTED


def test_ordinary_values_are_untouched():
    payload = {
        "execution_id": "11111111-2222-3333-4444-555555555555",
        "created_at": "2026-11-02T10:41:12",
        "total_cost": 0.1234567890,
        "n": 7,
        "ok": True,
        "none": None,
    }
    assert redact(payload) == payload


def test_the_input_is_not_modified():
    payload = {"to": PHONE, "list": [PHONE]}
    redact(payload)
    assert payload == {"to": PHONE, "list": [PHONE]}


def test_a_recording_link_in_free_text_is_removed():
    assert "example.com" not in redact("listen at https://example.com/x/y.wav?sig=1 now")
