"""Remove phone numbers and recording links from provider data before it is stored or logged.

A number may not be glued to a word character, '.' or '-', so dates, costs and the digit run at the
end of a UUID are left alone (the same rule as scripts/redact_fixture.py).
"""

from __future__ import annotations

import re
from typing import Any

_PHONE = re.compile(
    r"\+\d[\d\s\-]{8,}\d"
    r"|(?<![\w.\-])(?:91|0)?[6-9]\d{9}(?![\w\-])"
    r"|(?<![\w.\-])[6-9]\d{4}[\s\-]\d{5}(?![\w\-])"
)
_AUDIO_URL = re.compile(r"https?://\S+\.(?:mp3|wav|ogg|m4a|webm)(?:\?\S*)?", re.IGNORECASE)
RECORDING_KEY = "recording_url"
REDACTED = "<redacted>"


def mask_phone(value: str) -> str:
    """'+919876543210' -> '+91*******210': country code and last three digits only."""
    digits = re.sub(r"\D", "", value)
    return "***" if len(digits) < 8 else f"+{digits[:2]}{'*' * (len(digits) - 5)}{digits[-3:]}"


def redact(value: Any, key: str = "") -> Any:
    """A redacted deep copy: recording URLs removed, phone numbers masked in every string."""
    if "recording" in key.lower() and isinstance(value, str) and value.startswith("http"):
        return REDACTED
    if isinstance(value, dict):
        return {k: redact(v, k) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v, key) for v in value]
    if isinstance(value, str):
        value = _AUDIO_URL.sub(REDACTED, value)
        return _PHONE.sub(lambda m: mask_phone(m.group(0)), value)
    return value
