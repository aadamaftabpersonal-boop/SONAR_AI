"""Shop self opt-in pages (D-061). Behind FEATURE_OPT_IN, except the stop link, which always works.

/join/{token}  the invite page a teammate hands to one shop; the shop agrees itself
/join          a public "my shop would like to join" form; it only records a request
/stop/{token}  the shop's private "stop calling me" page, shown once after opting in

The wording follows docs/CONSENT_SCRIPT.md. English only until a native speaker has reviewed a
translation (the consent script forbids machine translation).
"""

from __future__ import annotations

import html
from collections.abc import Callable
from datetime import datetime

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.api.deps import _client_key, get_clock
from app.api.errors import ApiError
from app.config import Settings, get_settings
from app.db.session import get_session
from app.domain.enums import ErrorClass
from app.services.categories import get_categories
from app.services.optin import LANGUAGES, JoinForm, JoinRequest
from app.services.optin_store import invite_for, redeem, request_to_join, stop_calls

router = APIRouter()
NO_STORE = {"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"}


def _not_found() -> ApiError:
    # one deliberately uninformative 404 for "feature off", "unknown", "used" and "expired"
    return ApiError(
        404, ErrorClass.NOT_FOUND, "This link is not valid. Ask the Sonar team for a new one."
    )


def _page(title: str, body: str) -> HTMLResponse:
    return HTMLResponse(
        f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex"><meta name="referrer" content="no-referrer">
<title>{html.escape(title)}</title>
<style>
body{{font-family:system-ui,sans-serif;max-width:40rem;margin:2rem auto;padding:0 1rem;line-height:1.55}}
label{{display:block;margin:.8rem 0}}input,select{{font-size:1rem;padding:.4rem}}
button{{padding:.7rem 1.1rem;font-size:1rem}}.note{{color:#555;font-size:.92rem}}
.box{{background:#f4f6f5;border-radius:12px;padding:1rem}}.hp{{position:absolute;left:-9999px}}
</style></head><body>{body}</body></html>""",
        headers=NO_STORE,
    )


_FACTS = """
<div class="box">
<p><b>What Sonar is.</b> A small student project that helps people find out which nearby shops
have an item right now.</p>
<ul>
<li>An <b>AI assistant</b> would phone you now and then and ask one short question, for example
"Do you have Paracetamol 500 mg in stock right now?". It says it is an AI at the start of every
call.</li>
<li>Calls are <b>transcribed</b> to record your exact answer, and the voice provider may keep a
recording. People searching see what you said and when, labelled as what you reported.</li>
<li>It never buys, reserves or promises anything, and gives no advice.</li>
<li>At most 4 calls a day, only in the hours you choose. It is free.</li>
<li>You can <b>stop at any time</b>: say "don't call again" on a call, or use the stop link you get
after joining. It takes effect straight away.</li>
</ul></div>"""


@router.get("/join/{token}", response_class=HTMLResponse)
def invite_page(
    token: str,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
    clock: Callable[[], datetime] = Depends(get_clock),
) -> HTMLResponse:
    found = invite_for(session, token, clock()) if settings.feature_opt_in else None
    if found is None:
        raise _not_found()
    _, business = found
    langs = "".join(f'<option value="{k}">{v}</option>' for k, v in LANGUAGES.items())
    return _page(
        "Sonar: may we call your shop?",
        f"""<h1>{html.escape(business.name)}</h1>
<p>You were invited by the Sonar team. Please read this, then decide. Saying no is fine: just close
this page and we will not call.</p>
{_FACTS}
<form id="f">
<label><input type="checkbox" name="authorised" required> I am allowed to agree for this shop.</label>
<label><input type="checkbox" name="understands_ai_calls" required> I understand the calls come from
an AI assistant and are transcribed.</label>
<label>Your name (optional) <input name="contact_name" maxlength="60" autocomplete="name"></label>
<label>Hours we may call (optional) <input name="call_window" placeholder="10:00-13:00"
 pattern="[0-2][0-9]:[0-5][0-9]-[0-2][0-9]:[0-5][0-9]"></label>
<label>Language for calls <select name="language">{langs}</select></label>
<button type="submit">Yes, Sonar may call my shop</button>
</form>
<p id="msg" role="status"></p>
<script>
document.getElementById('f').addEventListener('submit', async (e) => {{
  e.preventDefault();
  const f = new FormData(e.target);
  const body = {{
    authorised: f.get('authorised') === 'on',
    understands_ai_calls: f.get('understands_ai_calls') === 'on',
    contact_name: f.get('contact_name') || null,
    call_window: f.get('call_window') || null,
    language: f.get('language'),
  }};
  const r = await fetch('/api' + location.pathname, {{
    method: 'POST', headers: {{'Content-Type': 'application/json'}}, body: JSON.stringify(body)}});
  const msg = document.getElementById('msg');
  if (r.ok) {{
    const d = await r.json();
    e.target.remove();
    msg.innerHTML = '';
    const p = document.createElement('p');
    p.textContent = 'Thank you. Sonar may now call your shop. Save this link: it stops the calls '
      + 'at any time.';
    const a = document.createElement('a');
    a.href = d.stop_path; a.textContent = location.origin + d.stop_path;
    msg.append(p, a);
  }} else {{
    msg.textContent = 'This did not work. The link may have expired; ask the Sonar team.';
  }}
}});
</script>""",
    )


@router.post("/api/join/{token}")
def accept_invite(
    token: str,
    form: JoinForm,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
    clock: Callable[[], datetime] = Depends(get_clock),
) -> dict[str, str]:
    if not settings.feature_opt_in:
        raise _not_found()
    if not form.agreed():
        raise ApiError(
            422, ErrorClass.VALIDATION, "Both boxes must be ticked to agree", "authorised"
        )
    done = redeem(session, token, form, clock())
    if done is None:
        raise _not_found()
    session.commit()
    return {"status": "CONSENTED", "stop_path": f"/stop/{done.stop_token}"}


@router.get("/stop/{token}", response_class=HTMLResponse)
def stop_page(token: str) -> HTMLResponse:
    # Always available, whatever the flags: stopping must never depend on a feature switch.
    return _page(
        "Sonar: stop calls",
        """<h1>Stop Sonar calling your shop</h1>
<p>Press the button and Sonar will not call this shop again. It takes effect straight away.</p>
<button id="stop">Stop Sonar calling me</button> <p id="msg" role="status"></p>
<script>
document.getElementById('stop').addEventListener('click', async () => {
  const r = await fetch('/api' + location.pathname, {method: 'POST'});
  document.getElementById('msg').textContent = r.ok
    ? 'Done. Sonar will not call you again.'
    : 'This link is not valid. Please tell the Sonar team directly and we will stop.';
});
</script>""",
    )


@router.post("/api/stop/{token}")
def stop(
    token: str,
    session: Session = Depends(get_session),
    clock: Callable[[], datetime] = Depends(get_clock),
) -> dict[str, str]:
    if not stop_calls(session, token, clock()):
        raise _not_found()
    session.commit()
    return {"status": "OPTED_OUT"}


@router.get("/join", response_class=HTMLResponse)
def public_form(settings: Settings = Depends(get_settings)) -> HTMLResponse:
    if not settings.feature_opt_in:
        raise _not_found()
    cats = "".join(
        f'<option value="{html.escape(k)}">{html.escape(v.display_name)}</option>'
        for k, v in get_categories().items()
    )
    return _page(
        "Sonar: ask to join",
        f"""<h1>Would your shop like to join Sonar?</h1>
{_FACTS}
<p>Leave your details and someone from the Sonar team will contact you to check, then send you a
personal link to agree. Nothing happens until you agree on that link.</p>
<form id="f">
<label>Shop name <input name="shop_name" required maxlength="80"></label>
<label>Area <input name="area" required maxlength="80"></label>
<label>Type of shop <select name="category">{cats}</select></label>
<label>Shop phone number <input name="phone" required maxlength="30" inputmode="tel"></label>
<label class="hp" aria-hidden="true">Website <input name="website" tabindex="-1" autocomplete="off"></label>
<button type="submit">Send</button>
</form>
<p id="msg" role="status"></p>
<script>
document.getElementById('f').addEventListener('submit', async (e) => {{
  e.preventDefault();
  const body = Object.fromEntries(new FormData(e.target));
  const r = await fetch('/api/join-request', {{
    method: 'POST', headers: {{'Content-Type': 'application/json'}}, body: JSON.stringify(body)}});
  document.getElementById('msg').textContent = r.ok
    ? 'Thank you. The Sonar team will be in touch. Nobody will call until you agree.'
    : 'Please check the details and try again.';
  if (r.ok) e.target.remove();
}});
</script>""",
    )


@router.post("/api/join-request")
def join_request(
    form: JoinRequest,
    request: Request,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
    clock: Callable[[], datetime] = Depends(get_clock),
) -> dict[str, str]:
    if not settings.feature_opt_in:
        raise _not_found()
    if not request.app.state.join_limiter.allow(_client_key(request)):
        raise ApiError(429, ErrorClass.RATE_LIMITED, "Too many requests, try again in a minute")
    if form.category not in get_categories():
        raise ApiError(422, ErrorClass.VALIDATION, "Unknown type of shop", "category")
    request_to_join(session, form, clock())
    session.commit()
    return {"status": "received"}  # the same reply whether or not the number was known
