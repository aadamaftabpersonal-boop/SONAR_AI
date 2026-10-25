"""Make sure the built web app contains no secret (Build Map T9.4, NFR-07, AC-7).

    npm --prefix frontend run build
    python scripts/check_bundle.py

Everything in the bundle is public. This fails if it contains any configured secret value, a
key-shaped string, a phone number, or a direct reference to the voice provider (the browser must
only ever talk to Sonar's own API).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SECRET_NAMES = ("SONAR_ACCESS_KEY", "WEBHOOK_SECRET_TOKEN", "BOLNA_API_KEY", "DATABASE_URL")
MIN_SECRET_LENGTH = 8  # shorter values would match innocent text

PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("API-key-shaped string", re.compile(r"\bsk-[A-Za-z0-9_\-]{16,}")),
    ("bearer token", re.compile(r"Bearer\s+[A-Za-z0-9._\-]{20,}")),
    ("long hex string", re.compile(r"\b[0-9a-f]{32,}\b")),
    ("phone number", re.compile(r"\+\d[\d\s\-]{9,}\d")),
    ("direct provider URL", re.compile(r"api\.bolna\.ai", re.IGNORECASE)),
    ("database URL", re.compile(r"postgres(?:ql)?(?:\+\w+)?://")),
    (
        "secret variable name",
        re.compile(r"\b(?:BOLNA_API_KEY|WEBHOOK_SECRET_TOKEN|SONAR_ACCESS_KEY)\b"),
    ),
]
TEXT_SUFFIXES = {".js", ".mjs", ".css", ".html", ".json", ".map", ".txt", ".svg"}


def scan_bundle(dist: Path, secrets: dict[str, str]) -> list[str]:
    findings: list[str] = []
    values = {k: v for k, v in secrets.items() if len(v) >= MIN_SECRET_LENGTH}
    for path in sorted(p for p in dist.rglob("*") if p.is_file()):
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        rel = path.relative_to(dist)
        for name, value in values.items():
            if value in text:
                findings.append(f"{rel}: contains the value of {name}")
        for label, pattern in PATTERNS:
            if pattern.search(text):
                findings.append(f"{rel}: {label}")
    return findings


def configured_secrets() -> dict[str, str]:
    import os

    found = {n: os.environ[n] for n in SECRET_NAMES if os.environ.get(n)}
    env = ROOT / ".env"
    if env.is_file():
        for raw in env.read_text(encoding="utf-8").splitlines():
            key, _, value = raw.strip().partition("=")
            if key in SECRET_NAMES and value.strip():
                found.setdefault(key, value.strip().strip("'\""))
    return found


def main(argv: list[str]) -> int:
    dist = Path(argv[0]) if argv else ROOT / "frontend" / "dist"
    if not (dist / "index.html").is_file():
        print(
            f"no build found at {dist}. Run `npm --prefix frontend run build` first.",
            file=sys.stderr,
        )
        return 2
    findings = scan_bundle(dist, configured_secrets())
    for f in findings:
        print(f)
    if findings:
        print(f"\n{len(findings)} problem(s): the web bundle is public, remove them.")
        return 1
    print(f"bundle check: clean ({dist})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
