"""Create a single-use invite link for one shop to opt in itself (D-061). Run from the repo root:

    backend\\.venv\\Scripts\\python scripts/invite_shop.py --phone "+91 98765 43210" --by "Teammate A"
    backend\\.venv\\Scripts\\python scripts/invite_shop.py --business-id <uuid> --by "Teammate A"

Hand the printed link to the shop yourself: in person, on paper, or by WhatsApp to the shop's own
number. Never send it to anyone else. The shop must open it and agree; nothing is called before.
"""

from __future__ import annotations

import argparse
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from sqlalchemy import select  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.db.models import Business  # noqa: E402
from app.db.session import get_engine, make_session_factory  # noqa: E402
from app.services.optin_store import InviteRefused, issue_invite  # noqa: E402
from app.services.osm import normalize_in_phone  # noqa: E402


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--phone")
    target.add_argument("--business-id")
    parser.add_argument("--by", required=True, help="who is handing the link over")
    args = parser.parse_args(argv)

    settings = get_settings()
    if not settings.feature_opt_in:
        print("FEATURE_OPT_IN is off: the link would not open. Turn it on first.", file=sys.stderr)
        return 1
    with make_session_factory(get_engine())() as session:
        if args.phone:
            phone = normalize_in_phone(args.phone)
            if phone is None:
                print("not a usable phone number", file=sys.stderr)
                return 1
            business = session.execute(
                select(Business).where(Business.phone_e164 == phone)
            ).scalar_one_or_none()
        else:
            business = session.get(Business, uuid.UUID(args.business_id))
        if business is None:
            print("no such shop; add it (seed file or discovery) first", file=sys.stderr)
            return 1
        try:
            token = issue_invite(
                session, business.id, args.by, datetime.now(UTC), settings.opt_in_token_days
            )
        except InviteRefused as exc:
            print(f"refused: {exc}", file=sys.stderr)
            return 1
        session.commit()
    base = settings.public_base_url.rstrip("/")
    print(f"Invite for {business.name} (valid {settings.opt_in_token_days} days, single use):")
    print(f"  {base}/join/{token}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
