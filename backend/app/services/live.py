"""Live transcript ticker (Bible 51 tier T-1, FR-46, NFR-19, T15.1). Pure helpers.

Only text the provider has already transcribed is shown; nothing is invented. Lines are short,
phone numbers are masked, and the speaker labels are ours, never the provider's free text.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field

from app.services.redact import _PHONE, mask_phone

_SPEAKERS = {
    "assistant": "Sonar assistant",
    "agent": "Sonar assistant",
    "bot": "Sonar assistant",
    "user": "Shop",
    "shop": "Shop",
    "human": "Shop",
}


def ticker_lines(transcript: str | None, max_lines: int = 6, max_chars: int = 200) -> list[dict]:
    """The last `max_lines` labelled turns, each at most `max_chars` characters."""
    if not transcript:
        return []
    lines: list[dict] = []
    for raw in transcript.splitlines():
        head, sep, text = raw.partition(":")
        speaker = _SPEAKERS.get(head.strip().lower()) if sep else None
        if speaker is None:
            continue  # unlabelled lines (system notes, recordings) are not shown
        text = " ".join(text.split())
        if not text:
            continue
        text = _PHONE.sub(lambda m: mask_phone(m.group(0)), text)
        if len(text) > max_chars:
            text = text[: max_chars - 1].rstrip() + "…"
        lines.append({"speaker": speaker, "text": text})
    return lines[-max_lines:] if max_lines > 0 else []


def may_show(kind: str, provider: str) -> bool:
    """Test lines (role-play, consented to being shown) and simulated calls only. A real shop's
    words are never streamed to a screen without a separate audience consent (Bible 51)."""
    return kind == "TEAM_TEST_LINE" or provider == "simulated"


@dataclass
class _Entry:
    fetched_at: float
    transcript: str | None


@dataclass
class LiveCache:
    """At most one provider pull per call every `min_interval` seconds, however many viewers."""

    min_interval: float = 2.0
    clock: Callable[[], float] = time.monotonic
    _entries: dict[str, _Entry] = field(default_factory=dict)

    def lookup(self, key: str) -> tuple[bool, str | None]:
        """(True, transcript) if a recent pull is cached, else (False, None)."""
        entry = self._entries.get(key)
        if entry and self.clock() - entry.fetched_at < self.min_interval:
            return True, entry.transcript
        return False, None

    def store(self, key: str, transcript: str | None) -> None:
        self._entries[key] = _Entry(self.clock(), transcript)
        if len(self._entries) > 500:  # bounded: drop the oldest half
            for k in sorted(self._entries, key=lambda k: self._entries[k].fetched_at)[:250]:
                del self._entries[k]
