"""Seed the business directory. Run from the repo root:

    backend\\.venv\\Scripts\\python scripts/seed_businesses.py [path]

Defaults to BUSINESS_SEED_PATH (data/businesses.local.yaml). Pass data/businesses.example.yaml
to load the fictional examples.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.config import get_settings  # noqa: E402
from app.db.session import get_engine, make_session_factory  # noqa: E402
from app.services.seed import SeedError, load_seed  # noqa: E402


def main(argv: list[str]) -> int:
    path = Path(argv[0]) if argv else ROOT / get_settings().business_seed_path
    try:
        with make_session_factory(get_engine())() as session:
            summary = load_seed(session, path)
    except SeedError as exc:
        print(f"seed failed: {exc}", file=sys.stderr)
        return 1
    print(f"seeded from {path.name}: {summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
