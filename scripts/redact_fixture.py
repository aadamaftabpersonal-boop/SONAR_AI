"""Turn a raw spike capture into a committable test fixture (Build Map S-5, S-6).

    python scripts/redact_fixture.py spikes/bolna/captures/webhook_0003_completed_ab12cd34.json \
        backend/tests/fixtures/bolna/webhook_completed.json

Removes: phone numbers, recording URLs, emails, auth headers and tokens. Execution ids are kept
(they identify nothing outside Bolna). Transcripts are NOT sanitised beyond phone numbers: read the
result yourself before committing, and never commit a real shopkeeper's speech without consent.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

# Same rules as spikes/bolna/common.py: a number may not be glued to a word character, '.' or '-',
# so dates, costs and the digit run at the end of a UUID are left alone.
PHONE = re.compile(
    r"\+\d[\d\s\-]{8,}\d"
    r"|(?<![\w.\-])(?:91|0)?[6-9]\d{9}(?![\w\-])"
    r"|(?<![\w.\-])[6-9]\d{4}[\s\-]\d{5}(?![\w\-])"
)
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
AUDIO_URL = re.compile(r"https?://\S+\.(?:mp3|wav|ogg|m4a|webm)(?:\?\S*)?", re.IGNORECASE)
SECRET_KEYS = {
    "authorization",
    "cookie",
    "x-api-key",
    "api_key",
    "apikey",
    "token",
    "secret",
    "password",
    "proxy-authorization",
}

FAKE_PHONE = "+910000000000"  # starts with 0, so it can never be a real Indian mobile number
FAKE_URL = "https://example.invalid/recording-redacted"
FAKE_EMAIL = "redacted@example.invalid"


def redact_text(text: str) -> str:
    text = AUDIO_URL.sub(FAKE_URL, text)
    text = EMAIL.sub(FAKE_EMAIL, text)
    return PHONE.sub(FAKE_PHONE, text)


def redact(value: Any, key: str = "") -> Any:
    if key.lower() in SECRET_KEYS:
        return "<redacted>"
    if isinstance(value, dict):
        return {k: redact(v, k) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v, key) for v in value]
    if isinstance(value, str):
        if "recording" in key.lower() and value.startswith("http"):
            return FAKE_URL
        return redact_text(value)
    return value


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    src, dst = Path(argv[0]), Path(argv[1])
    data = json.loads(src.read_text(encoding="utf-8"))
    cleaned = redact(data)
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(json.dumps(cleaned, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {dst}. Read it before you commit: transcripts may contain names or addresses.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
