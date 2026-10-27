"""D-061: shop self opt-in helpers."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.services.optin import (
    JoinForm,
    JoinRequest,
    consent_note,
    hash_token,
    new_token,
    window_for_selector,
)


def test_tokens_are_random_and_only_the_hash_is_kept():
    t1, h1 = new_token()
    t2, _ = new_token()
    assert t1 != t2 and len(t1) >= 32
    assert h1 == hash_token(t1) and t1 not in h1 and len(h1) == 64


def test_agreement_needs_both_boxes():
    assert JoinForm(authorised=True, understands_ai_calls=True).agreed()
    assert not JoinForm(authorised=True, understands_ai_calls=False).agreed()
    assert not JoinForm(authorised=False, understands_ai_calls=True).agreed()


@pytest.mark.parametrize("window", ["10:00-13:00", " 09:30 - 20:00 "])
def test_valid_call_windows(window):
    form = JoinForm(authorised=True, understands_ai_calls=True, call_window=window)
    assert window_for_selector(form.call_window).endswith(" IST")


@pytest.mark.parametrize("window", ["13:00-10:00", "25:00-26:00", "morning", "10-13"])
def test_invalid_call_windows(window):
    with pytest.raises(ValidationError):
        JoinForm(authorised=True, understands_ai_calls=True, call_window=window)


def test_name_and_language_are_checked():
    with pytest.raises(ValidationError):
        JoinForm(authorised=True, understands_ai_calls=True, contact_name="<script>")
    with pytest.raises(ValidationError):
        JoinForm(authorised=True, understands_ai_calls=True, language="xx")
    assert (
        JoinForm(authorised=True, understands_ai_calls=True, contact_name="  ").contact_name is None
    )


def test_consent_note_records_how_when_and_who():
    form = JoinForm(authorised=True, understands_ai_calls=True, contact_name="Ravi", language="hi")
    note = consent_note(datetime(2026, 10, 28, 6, 0, tzinfo=UTC), form)
    assert "Self opt-in via invite link" in note and "2026-10-28 11:30 IST" in note
    assert "Ravi" in note and "Hindi" in note and "AI and transcribed" in note


def request(**over):
    base = {
        "shop_name": "Fixture Medicals",
        "area": "Example Nagar",
        "category": "pharmacy",
        "phone": "98765 43210",
    }
    base.update(over)
    return JoinRequest(**base)


def test_public_request_normalises_the_phone():
    assert request().phone_e164() == "+919876543210"
    assert request(phone="12345 678").phone_e164() is None


def test_honeypot_marks_bots():
    assert not request().is_bot()
    assert request(website="http://spam.example").is_bot()


def test_public_request_rejects_markup():
    with pytest.raises(ValidationError):
        request(shop_name="<b>shop</b>")
