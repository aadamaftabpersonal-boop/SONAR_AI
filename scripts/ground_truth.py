"""Record whether a live answer matched reality, and review answers against their transcript.

    python scripts/ground_truth.py list
    python scripts/ground_truth.py check RESPONSE_ID --checker Asha --method IN_PERSON --outcome AGREE
    python scripts/ground_truth.py review RESPONSE_ID --reviewer Asha --agrees
    python scripts/ground_truth.py review RESPONSE_ID --reviewer Asha --disagrees

Run it with backend\\.venv\\Scripts\\python. Only live answers can be checked; the result feeds the
agreement figure in scripts/metrics_report.py (reported as agree of checked, never a bare percent).
"""

from __future__ import annotations

import argparse
import sys
import uuid
from collections.abc import Callable
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from sqlalchemy import select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.db.models import Business  # noqa: E402
from app.db.session import get_engine, make_session_factory  # noqa: E402
from app.domain.enums import GroundTruthOutcome  # noqa: E402
from app.services import review  # noqa: E402


def run(argv: list[str], session_factory: Callable[[], Session]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    check = sub.add_parser("check")
    check.add_argument("response_id", type=uuid.UUID)
    check.add_argument("--checker", required=True)
    check.add_argument("--method", required=True, choices=review.METHODS)
    check.add_argument("--outcome", required=True, choices=[o.value for o in GroundTruthOutcome])
    check.add_argument("--note")
    rev = sub.add_parser("review")
    rev.add_argument("response_id", type=uuid.UUID)
    rev.add_argument("--reviewer", required=True)
    group = rev.add_mutually_exclusive_group(required=True)
    group.add_argument("--agrees", action="store_true")
    group.add_argument("--disagrees", action="store_true")
    args = parser.parse_args(argv)

    with session_factory() as session:
        try:
            if args.cmd == "list":
                rows = review.list_unchecked(session)
                if not rows:
                    print("nothing to check")
                for r in rows:
                    name = session.execute(
                        select(Business.name).where(Business.id == r.business_id)
                    ).scalar_one()
                    print(f"{r.id}  {name}  {r.answer_timestamp:%Y-%m-%d %H:%M}  {r.availability}")
                    print(f"    {r.answer_summary}")
                    print(f"    quote: {r.evidence_excerpt or '(none)'}")
                return 0
            if args.cmd == "check":
                review.record_ground_truth(
                    session,
                    args.response_id,
                    checker=args.checker,
                    method=args.method,
                    outcome=GroundTruthOutcome(args.outcome),
                    note=args.note,
                )
            else:
                review.mark_review(
                    session, args.response_id, agrees=args.agrees, reviewer=args.reviewer
                )
            session.commit()
        except review.ReviewError as exc:
            print(f"refused: {exc}", file=sys.stderr)
            return 1
    print("recorded")
    return 0


if __name__ == "__main__":
    raise SystemExit(run(sys.argv[1:], make_session_factory(get_engine())))
