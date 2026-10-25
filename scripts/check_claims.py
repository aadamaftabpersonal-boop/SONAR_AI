"""Flag unsourced numbers and market claims in the business documents (Build Map T13.1, WP-20).

    python scripts/check_claims.py            # checks the default business documents
    python scripts/check_claims.py FILE...

A pitch may only say what we measured or can source. This catches the usual slips: percentages,
market-size words and revenue-style figures. A line can opt out only by carrying the marker
`<!-- claim-ok -->`, which must sit next to a source or a clear "we do not claim this" statement.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FILES = [
    ROOT / "docs" / "BUSINESS_CASE.md",
    ROOT / "docs" / "CONSENT_SCRIPT.md",
    ROOT / "docs" / "DISCOVERY_LOG.md",
]
MARKER = "<!-- claim-ok -->"

RULES: list[tuple[str, re.Pattern[str]]] = [
    ("percentage", re.compile(r"\d\s*%")),
    ("market-size word", re.compile(r"\b(crore|lakh|billion|million|trillion|TAM|SAM|SOM|CAGR)\b")),
    ("market-size phrase", re.compile(r"market size|growing market|multi-?billion", re.IGNORECASE)),
    ("revenue figure", re.compile(r"(?:revenue|ARR|MRR)\D{0,15}\d", re.IGNORECASE)),
]


def check_text(text: str, name: str = "<text>") -> list[str]:
    findings = []
    for number, line in enumerate(text.splitlines(), start=1):
        if MARKER in line:
            continue
        for label, pattern in RULES:
            if pattern.search(line):
                findings.append(f"{name}:{number}: {label}: {line.strip()[:90]}")
    return findings


def main(argv: list[str]) -> int:
    files = [Path(a) for a in argv] if argv else DEFAULT_FILES
    findings: list[str] = []
    for path in files:
        if path.is_file():
            findings += check_text(path.read_text(encoding="utf-8"), path.name)
    for f in findings:
        print(f)
    if findings:
        print(f"\n{len(findings)} unsourced claim(s). Remove them, measure them, or source them.")
        return 1
    print("claims check: clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
