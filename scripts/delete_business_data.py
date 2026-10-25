"""Delete what Sonar holds about one shop's calls, because it asked (Consent script, section 7).

    backend\\.venv\\Scripts\\python scripts/delete_business_data.py BUSINESS_ID           # dry run
    backend\\.venv\\Scripts\\python scripts/delete_business_data.py BUSINESS_ID --yes     # really

Removes its answers, raw provider events, ground-truth checks and call history. The business row
and its opt-out stay, so a shop that asked to be forgotten is never called again.
"""

from __future__ import annotations

import argparse
import sys
import uuid
from collections.abc import Callable
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from sqlalchemy.orm import Session  # noqa: E402

from app.db.models import Business  # noqa: E402
from app.db.session import get_engine, make_session_factory  # noqa: E402
from app.services.retention import delete_business_data  # noqa: E402


def run(argv: list[str], session_factory: Callable[[], Session]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("business_id", type=uuid.UUID)
    parser.add_argument("--yes", action="store_true", help="actually delete (default: dry run)")
    args = parser.parse_args(argv)
    with session_factory() as session:
        business = session.get(Business, args.business_id)
        if business is None:
            print("no such business", file=sys.stderr)
            return 1
        counts = delete_business_data(session, args.business_id)
        if args.yes:
            session.commit()
            print(f"deleted for {business.name}: {counts}")
        else:
            session.rollback()
            print(f"dry run for {business.name}: would delete {counts}. Add --yes to do it.")
    return 0


if __name__ == "__main__":
    raise SystemExit(run(sys.argv[1:], make_session_factory(get_engine())))
