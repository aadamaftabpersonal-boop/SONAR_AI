"""Shop self opt-in (D-061): the shop's own act is the only route to being called.

Pure helpers (tokens, form validation, consent wording) live here; database work is in
`optin_store.py`. A teammate hands a single-use invite link to the shop (in person, on paper, or by
WhatsApp to the shop's own number). The public form only *requests* an invite: anyone can type any
number, so it never makes a shop callable by itself.
"""

from __future__ import annotations

import hashlib
import re
import secrets
from datetime import datetime
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field, field_validator

from app.services.osm import normalize_in_phone

IST = ZoneInfo("Asia/Kolkata")
CONSENT_SCRIPT = "consent_script_v2 self opt-in"
LANGUAGES = {"en": "English", "hi": "Hindi", "kn": "Kannada", "ta": "Tamil", "te": "Telugu"}
_WINDOW = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)-([01]\d|2[0-3]):([0-5]\d)$")
_NAME = re.compile(r"^[\w .,'&()\-]{1,60}$", re.UNICODE)


def new_token() -> tuple[str, str]:
    """(token for the link, hash to store). The token itself is never stored."""
    token = secrets.token_urlsafe(24)
    return token, hash_token(token)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class JoinForm(BaseModel):
    """What the shop submits on its invite page."""

    authorised: bool  # "I am allowed to agree for this shop"
    understands_ai_calls: bool  # "calls are from an AI assistant and are transcribed"
    contact_name: str | None = Field(default=None, max_length=60)
    call_window: str | None = None  # "10:00-13:00"
    language: str = "en"

    @field_validator("contact_name")
    @classmethod
    def _name(cls, v: str | None) -> str | None:
        v = (v or "").strip()
        if not v:
            return None
        if not _NAME.match(v):
            raise ValueError("use letters, numbers and simple punctuation only")
        return v

    @field_validator("call_window")
    @classmethod
    def _window(cls, v: str | None) -> str | None:
        v = (v or "").replace(" ", "")
        if not v:
            return None
        m = _WINDOW.match(v)
        if not m or (int(m[1]), int(m[2])) >= (int(m[3]), int(m[4])):
            raise ValueError("use a window like 10:00-13:00")
        return v

    @field_validator("language")
    @classmethod
    def _language(cls, v: str) -> str:
        if v not in LANGUAGES:
            raise ValueError("unsupported language")
        return v

    def agreed(self) -> bool:
        return self.authorised and self.understands_ai_calls


class JoinRequest(BaseModel):
    """The public 'I'd like my shop to join' form. Never makes a shop callable."""

    shop_name: str = Field(min_length=1, max_length=80)
    area: str = Field(min_length=1, max_length=80)
    category: str = Field(min_length=1, max_length=40)
    phone: str = Field(min_length=6, max_length=30)
    website: str = ""  # honeypot: people never see it, simple bots fill it

    @field_validator("shop_name", "area")
    @classmethod
    def _text(cls, v: str) -> str:
        v = " ".join(v.split())
        if not _NAME.match(v[:60]):
            raise ValueError("use letters, numbers and simple punctuation only")
        return v

    def phone_e164(self) -> str | None:
        return normalize_in_phone(self.phone)

    def is_bot(self) -> bool:
        return bool(self.website.strip())


def consent_note(when: datetime, form: JoinForm) -> str:
    stamp = when.astimezone(IST).strftime("%Y-%m-%d %H:%M IST")
    who = f"by {form.contact_name}" if form.contact_name else "name not given"
    return (
        f"Self opt-in via invite link, {stamp}, {who}, language {LANGUAGES[form.language]}, "
        f"{CONSENT_SCRIPT}. Confirmed authority to agree and that calls are AI and transcribed."
    )


def window_for_selector(call_window: str | None) -> str | None:
    """The selector's format ('10:00-13:00 IST')."""
    return f"{call_window} IST" if call_window else None
