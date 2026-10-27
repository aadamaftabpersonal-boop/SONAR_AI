"""List shops that asked to join through the public form, and issue an invite after checking.

    backend\\.venv\\Scripts\\python scripts/approve_opt_in.py                 # list pending requests
    backend\\.venv\\Scripts\\python scripts/approve_opt_in.py <business-id> --by "Teammate A"

Before approving, a teammate must confirm the number belongs to that shop (call it yourself, or
visit). Approving only creates an invite link; the shop still has to open it and agree (D-061).
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "scripts"))

from app.db.session import get_engine, make_session_factory  # noqa: E402
from app.services.optin_store import pending_requests  # noqa: E402
from app.services.redact import mask_phone  # noqa: E402


def main(argv: list[str]) -> int:
    if not argv:
        with make_session_factory(get_engine())() as session:
            pending = pending_requests(session)
        if not pending:
            print("No pending requests.")
        for b in pending:
            when = b.opt_in_requested_at.strftime("%Y-%m-%d %H:%M UTC")
            print(f"{b.id}  {b.name}  ({b.address or 'no area'})  {mask_phone(b.phone_e164)}  {when}")
        return 0
    if "--by" not in argv:
        print("say who checked the number: --by \"Teammate A\"", file=sys.stderr)
        return 1
    answer = input("Did you confirm this number belongs to the shop (call or visit)? [y/N] ")
    if answer.strip().lower() != "y":
        print("Not approved.")
        return 1
    import invite_shop

    by = argv[argv.index("--by") + 1]
    return invite_shop.main(["--business-id", argv[0], "--by", by])


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
