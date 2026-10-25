"""Fail if files contain what looks like a secret or a real phone number (WP-6, T0.4).

Usage:
  python scripts/check_no_secrets.py            # scan git-tracked + untracked, not-ignored files
  python scripts/check_no_secrets.py PATH...    # scan given files or directories

Files named *.example.* and .env.example are exempt: they hold placeholders by design.
Heuristic, not a guarantee. Review `git diff --cached` as well.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "assigned secret value",
        re.compile(
            r"(?im)^\s*[A-Z0-9_]*(?:API_KEY|SECRET|TOKEN|ACCESS_KEY)[A-Z0-9_]*\s*[=:]\s*"
            r"['\"]?(?!changeme|placeholder|xxxx|<)[A-Za-z0-9_\-]{16,}"
        ),
    ),
    ("long hex string", re.compile(r"\b[0-9a-f]{32,}\b")),
    ("indian mobile number", re.compile(r"(?<!\d)\+91[\s-]?[6-9]\d{9}(?!\d)")),
]

SKIP_DIRS = {".git", ".venv", "node_modules", "__pycache__", ".pytest_cache", ".ruff_cache"}
SKIP_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".pdf", ".zip", ".ico", ".lock"}
SELF = Path(__file__).resolve()


def is_exempt(path: Path) -> bool:
    name = path.name
    return ".example." in name or name.endswith(".example") or path.resolve() == SELF


# Obviously fake numbers that tests use as stand-ins (a descending run of digits). Allowlisting
# exact values keeps the rule strict for everything else.
KNOWN_FAKE_MOBILES = {"9876543210"}


def scan_text(text: str, filename: str = "<text>") -> list[str]:
    findings = []
    for label, pattern in PATTERNS:
        for match in pattern.finditer(text):
            if label == "indian mobile number":
                if re.sub(r"\D", "", match.group(0))[-10:] in KNOWN_FAKE_MOBILES:
                    continue
            line = text.count("\n", 0, match.start()) + 1
            findings.append(f"{filename}:{line}: {label}")
    return findings


def iter_files(paths: list[str]) -> list[Path]:
    if paths:
        out: list[Path] = []
        for p in map(Path, paths):
            if p.is_dir():
                out += [f for f in p.rglob("*") if f.is_file()]
            elif p.is_file():
                out.append(p)
        return out
    try:
        listed = subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.splitlines()
    except (subprocess.CalledProcessError, FileNotFoundError):
        listed = [str(f.relative_to(ROOT)) for f in ROOT.rglob("*") if f.is_file()]
    return [ROOT / f for f in listed]


def main(argv: list[str]) -> int:
    findings: list[str] = []
    for path in iter_files(argv):
        if set(path.parts) & SKIP_DIRS or path.suffix.lower() in SKIP_SUFFIXES:
            continue
        if is_exempt(path):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        findings += scan_text(text, str(path))
    for f in findings:
        print(f)
    if findings:
        print(f"\n{len(findings)} possible secret(s) found.", file=sys.stderr)
        return 1
    print("secret check: clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
