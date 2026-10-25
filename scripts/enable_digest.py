"""Give a consenting shop its private digest link (only after it agreed; see CONSENT_SCRIPT.md).

    backend\\.venv\\Scripts\\python scripts/enable_digest.py BUSINESS_ID [--base-url https://your.app]

Also set FEATURE_DIGEST=true on the server, or the link will show nothing. Do not offer the digest
to a shop until this works (consent script variant B).
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

from app.db.session import get_engine, make_session_factory  # noqa: E402
from app.services.digest import enable_digest  # noqa: E402


def run(argv: list[str], session_factory: Callable[[], Session]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("business_id", type=uuid.UUID)
    parser.add_argument("--base-url", default="http://localhost:8000")
    args = parser.parse_args(argv)
    with session_factory() as session:
        try:
            token = enable_digest(session, args.business_id)
        except ValueError as exc:
            print(f"refused: {exc}", file=sys.stderr)
            return 1
        session.commit()
    print(f"digest link: {args.base_url.rstrip('/')}/shop/{token}")
    print("Treat it like a password: anyone with the link can see this shop's digest.")
    return 0


if __name__ == "__main__":
    raise SystemExit(run(sys.argv[1:], make_session_factory(get_engine())))
