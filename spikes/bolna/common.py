"""Shared helpers for the Phase 1 spike scripts. Plain stdlib; no app code (Build Map Phase 1).

Safety rules baked in here:
- the API key is read from the environment and is never printed or saved
- phone numbers are masked in everything printed or written to captures
- captures live in spikes/bolna/captures/, which is git-ignored (raw data stays local)
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CAPTURES = HERE / "captures"
DEFAULT_BASE_URL = "https://api.bolna.ai"

# VERIFIED final statuses (Bible 21.3, call-flow page). Real payloads override this in the spike.
TERMINAL_STATUSES = {
    "completed",
    "no-answer",
    "busy",
    "failed",
    "canceled",
    "stopped",
    "error",
    "balance-low",
}

_E164 = re.compile(r"^\+[1-9][0-9]{7,14}$")
# '+' numbers, Indian mobiles (6-9 then nine digits, optional 91/0 prefix) and the common
# "98765 43210" grouping. Dates (2026-11-02), costs (0.12) and the digit run at the end of a UUID
# must NOT match, so a number may not be glued to a word character, '.' or '-'.
_PHONE_IN_TEXT = re.compile(
    r"\+\d[\d\s\-]{8,}\d"
    r"|(?<![\w.\-])(?:91|0)?[6-9]\d{9}(?![\w\-])"
    r"|(?<![\w.\-])[6-9]\d{4}[\s\-]\d{5}(?![\w\-])"
)


def load_env(path: Path = ROOT / ".env") -> None:
    """Load KEY=VALUE lines from .env into os.environ (existing variables win)."""
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip("'\""))


def env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def require(name: str, hint: str = "") -> str:
    value = env(name)
    if not value:
        sys.exit(f"missing {name}. Put it in .env (git-ignored). {hint}".strip())
    return value


def is_e164(value: str) -> bool:
    return bool(_E164.match(value or ""))


def mask_phone(value: str) -> str:
    """'+919876543210' -> '+91*******210' (keeps the country code and last three digits)."""
    digits = re.sub(r"\D", "", value)
    if len(digits) < 8:
        return "***"
    return f"+{digits[:2]}{'*' * (len(digits) - 5)}{digits[-3:]}"


def mask_in_text(text: str) -> str:
    return _PHONE_IN_TEXT.sub(lambda m: mask_phone(m.group(0)), text)


def auth_headers(api_key: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}


def utcnow() -> datetime:
    return datetime.now(UTC)


def stamp() -> str:
    return utcnow().strftime("%Y%m%dT%H%M%S%fZ")


def is_terminal(status: str | None) -> bool:
    return (status or "").strip().lower() in TERMINAL_STATUSES


def save_capture(name: str, data: Any, directory: Path | None = None) -> Path:
    directory = directory or CAPTURES  # resolved at call time so tests can redirect CAPTURES
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / name
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    return path


def type_table(obj: Any, prefix: str = "", depth: int = 3) -> list[tuple[str, str]]:
    """Flatten a JSON value into (path, type) rows for the FEASIBILITY field table (S-6, S-7)."""
    rows: list[tuple[str, str]] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            rows.append((path, type(value).__name__))
            if depth > 0 and isinstance(value, dict):
                rows += type_table(value, path, depth - 1)
    return rows


def markdown_table(rows: list[tuple[str, str]]) -> str:
    lines = ["| field | type |", "|---|---|"] + [f"| `{p}` | {t} |" for p, t in rows]
    return "\n".join(lines)


def short(value: str | None, n: int = 8) -> str:
    return (value or "none")[:n]
