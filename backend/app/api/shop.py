"""The shop-facing digest page and its opt-out (Bible 49, FR-41).

A shop reaches this only through its private token. The page shows no phone number and no searcher
identity. Opting out here has the same effect as asking on a call: Sonar never calls it again.
"""

from __future__ import annotations

import html
from collections.abc import Callable
from dataclasses import asdict
from datetime import datetime

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.api.deps import get_clock
from app.api.errors import ApiError
from app.config import Settings, get_settings
from app.db.models import Business
from app.db.repositories import AttemptRepo, AuditRepo, BusinessRepo
from app.db.session import get_session
from app.domain.enums import ErrorClass
from app.services.digest import Digest, business_for_token, generate

router = APIRouter()


def _lookup(session: Session, settings: Settings, token: str) -> Business:
    # one deliberately uninformative 404 for "feature off", "no such token" and "opted out"
    business = business_for_token(session, token) if settings.feature_digest else None
    if business is None:
        raise ApiError(404, ErrorClass.NOT_FOUND, "Not found")
    return business


@router.get("/api/shop/{token}/digest")
def digest_json(
    token: str,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
    clock: Callable[[], datetime] = Depends(get_clock),
) -> dict:
    business = _lookup(session, settings, token)
    return asdict(generate(session, business, clock(), settings.digest_min_k))


@router.post("/api/shop/{token}/opt-out")
def opt_out(
    token: str,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> dict[str, str]:
    business = _lookup(session, settings, token)
    BusinessRepo(session).mark_opt_out(business.id)
    cancelled = AttemptRepo(session).cancel_pending_for_business(business.id, "OPTED_OUT")
    business.digest_opt_in = False
    AuditRepo(session).add(
        "shop", "opt_out_via_digest", business_id=business.id, detail={"cancelled": cancelled}
    )
    session.commit()
    return {"status": "OPTED_OUT"}


def render_page(token: str, digest: Digest) -> str:
    esc = html.escape
    if digest.lines:
        rows = "".join(
            f"<tr><td>{esc(line.item)}</td><td>{line.searches}</td>"
            f"<td>{line.you_reported_available}</td></tr>"
            for line in digest.lines
        )
        table = (
            "<table><thead><tr><th>Item</th><th>Searches near you</th>"
            f"<th>Times you reported having it</th></tr></thead><tbody>{rows}</tbody></table>"
        )
    else:
        table = "<p>Nothing to show yet: no item reached the minimum number of searches.</p>"
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex"><meta name="referrer" content="no-referrer">
<title>Sonar: your weekly digest</title>
<style>
body{{font-family:system-ui,sans-serif;max-width:40rem;margin:2rem auto;padding:0 1rem;line-height:1.5}}
table{{border-collapse:collapse;width:100%}}th,td{{border-bottom:1px solid #ccc;padding:.5rem;text-align:left}}
button{{padding:.6rem 1rem;font-size:1rem}}.note{{color:#555;font-size:.9rem}}
</style></head><body>
<h1>{esc(digest.business_name)}</h1>
<p>What people near you searched for in the last {digest.window_days} days.</p>
{table}
<p class="note">{esc(digest.note)}</p>
<h2>Stop calls</h2>
<p>If you do not want Sonar to phone you again, press the button. It takes effect straight away.</p>
<button id="stop">Stop Sonar calling me</button> <span id="msg" role="status"></span>
<script>
document.getElementById('stop').addEventListener('click', async () => {{
  const r = await fetch('/api/shop/{esc(token)}/opt-out', {{method: 'POST'}});
  document.getElementById('msg').textContent =
    r.ok ? 'Done. Sonar will not call you again.' : 'Something went wrong. Please tell us directly.';
}});
</script></body></html>"""


@router.get("/shop/{token}", response_class=HTMLResponse)
def digest_page(
    token: str,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
    clock: Callable[[], datetime] = Depends(get_clock),
) -> HTMLResponse:
    business = _lookup(session, settings, token)
    page = render_page(token, generate(session, business, clock(), settings.digest_min_k))
    return HTMLResponse(page, headers={"Cache-Control": "no-store"})
