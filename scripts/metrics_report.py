"""Print the measured numbers (Bible 39, 54.2). Every figure shows its denominator.

    backend\\.venv\\Scripts\\python scripts/metrics_report.py
    backend\\.venv\\Scripts\\python scripts/metrics_report.py --since-days 7 --write docs/METRICS.md
    backend\\.venv\\Scripts\\python scripts/metrics_report.py --include-simulated   # rehearsal only

Live calls only by default: simulated runs prove nothing about reality.
"""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.db.session import get_engine, make_session_factory  # noqa: E402
from app.services.metrics import compute, render  # noqa: E402


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--since-days", type=int)
    parser.add_argument("--include-simulated", action="store_true")
    parser.add_argument("--write", type=Path, help="also write the report to this file")
    args = parser.parse_args(argv)

    since = datetime.now(UTC) - timedelta(days=args.since_days) if args.since_days else None
    with make_session_factory(get_engine())() as session:
        metrics = compute(session, since=since, include_simulated=args.include_simulated)
    title = "Sonar metrics" + (" (INCLUDES SIMULATED RUNS)" if args.include_simulated else "")
    report = render(metrics, title)
    stamp = f"\nGenerated {datetime.now(UTC):%Y-%m-%d %H:%M} UTC. "
    stamp += f"Window: last {args.since_days} days.\n" if args.since_days else "Window: all time.\n"
    print(report + stamp)
    if args.write:
        args.write.write_text(report + stamp, encoding="utf-8")
        print(f"written to {args.write}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
