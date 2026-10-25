"""S-5: turn a folder of webhook captures into the answers FEASIBILITY.md needs.

    python spikes/bolna/s5_summarize_webhooks.py

Answers (each printed with the evidence, never a guess):
  A-18  do payloads carry the execution id and status as top-level fields?
  A-06  which header names arrive (are custom headers delivered)?
  A-07  does Bolna redeliver after we answered 500?
  order and duplicates: are statuses out of order or repeated?
  fields present at each status (call-disconnected vs completed)
  source IPs vs the three documented Bolna IPs
  did the first webhook arrive BEFORE our POST /call response? (matters for orphan handling)
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402

DOCUMENTED_IPS = {"13.203.39.153", "13.126.9.249", "13.202.133.53"}
DOCUMENTED_ORDER = [
    "queued",
    "initiated",
    "ringing",
    "in-progress",
    "call-disconnected",
    "completed",
]
INTERESTING_FIELDS = (
    "transcript",
    "extracted_data",
    "telephony_data",
    "total_cost",
    "conversation_duration",
)
STANDARD_HEADERS = {
    "host",
    "user-agent",
    "accept",
    "accept-encoding",
    "content-type",
    "content-length",
    "connection",
    "x-forwarded-for",
    "x-forwarded-proto",
    "x-forwarded-host",
    "x-real-ip",
    "cf-connecting-ip",
    "cf-ipcountry",
    "cf-ray",
    "cf-visitor",
    "cdn-loop",
    "ngrok-trace-id",
}


def load_webhooks(directory: Path) -> list[dict]:
    items = []
    for path in sorted(directory.glob("webhook_*.json")):
        try:
            items.append(json.loads(path.read_text(encoding="utf-8")))
        except ValueError:
            continue
    return sorted(items, key=lambda r: r.get("seq", 0))


def _exec_id(body: dict) -> str | None:
    return body.get("execution_id") or body.get("id")


def _present(value) -> bool:
    return value not in (None, "", 0, {}, [])


def latest_call_capture(directory: Path) -> dict | None:
    calls = sorted(directory.glob("s4_call_*.json"))
    if not calls:
        return None
    try:
        return json.loads(calls[-1].read_text(encoding="utf-8"))
    except ValueError:
        return None


def summarize(directory: Path) -> str:
    hooks = load_webhooks(directory)
    if not hooks:
        return "No webhook captures found. Run webhook_capture.py and place a call first."

    json_hooks = [h for h in hooks if isinstance(h.get("body_json"), dict)]
    out = [
        f"# S-5 webhook summary ({len(hooks)} deliveries, {len(json_hooks)} with a JSON object)",
        "",
    ]

    # A-18: top-level execution id and status
    id_keys = Counter(k for h in json_hooks for k in ("execution_id", "id") if k in h["body_json"])
    status_keys = Counter(k for h in json_hooks for k in ("status",) if k in h["body_json"])
    out += [
        "## A-18: are the execution id and status top-level fields?",
        f"- id key counts: `{dict(id_keys)}`; status key counts: `{dict(status_keys)}`",
        f"- verdict: {'YES' if id_keys and status_keys else 'NO or UNKNOWN'} "
        "(if NO, `app/services/events.py` _ID_KEYS/_STATUS_KEYS must change)",
        "",
    ]

    # per-execution timeline, duplicates, ordering
    by_exec: dict[str, list[dict]] = defaultdict(list)
    for h in json_hooks:
        by_exec[str(_exec_id(h["body_json"]))].append(h)
    out.append("## Timeline per execution")
    for exec_id, items in by_exec.items():
        statuses = [i["body_json"].get("status") for i in items]
        out.append(f"- `{common.short(exec_id)}`: " + " -> ".join(str(s) for s in statuses))
        counts = Counter(statuses)
        dups = {s: n for s, n in counts.items() if n > 1}
        if dups:
            out.append(f"  - duplicates: {dups}")
        ranks = [DOCUMENTED_ORDER.index(s) for s in statuses if s in DOCUMENTED_ORDER]
        if ranks != sorted(ranks):
            out.append("  - OUT OF ORDER relative to the documented sequence")
    out.append("")

    # fields present per status
    out.append("## Fields present at each status (non-empty)")
    out.append("| status | " + " | ".join(INTERESTING_FIELDS) + " |")
    out.append("|---|" + "---|" * len(INTERESTING_FIELDS))
    seen_status: dict[str, dict[str, bool]] = {}
    for h in json_hooks:
        b = h["body_json"]
        s = str(b.get("status"))
        row = seen_status.setdefault(s, dict.fromkeys(INTERESTING_FIELDS, False))
        for f in INTERESTING_FIELDS:
            row[f] = row[f] or _present(b.get(f))
    for s, row in seen_status.items():
        out.append(
            f"| {s} | " + " | ".join("yes" if row[f] else "no" for f in INTERESTING_FIELDS) + " |"
        )
    out.append("")

    # headers and IPs
    names = sorted({k.lower() for h in hooks for k in h.get("headers", {})})
    custom = [n for n in names if n not in STANDARD_HEADERS]
    ips = sorted({h.get("client_ip") for h in hooks if h.get("client_ip")})
    fwd = sorted({h.get("x_forwarded_for") for h in hooks if h.get("x_forwarded_for")})
    out += [
        "## A-06: headers observed",
        f"- all: `{names}`",
        f"- not in the usual proxy/HTTP set (custom headers would show here): `{custom}`",
        "",
        "## Source IPs",
        f"- socket peers: `{ips}`; X-Forwarded-For: `{fwd}`",
        f"- documented Bolna IPs: `{sorted(DOCUMENTED_IPS)}`",
        f"- any forwarded IP in the documented set: {bool(DOCUMENTED_IPS & set(','.join(fwd).replace(' ', '').split(',')))}"
        " (behind a tunnel the socket peer is the tunnel, so check X-Forwarded-For)",
        "",
    ]

    # A-07: redelivery after a failure
    failed = [h for h in json_hooks if (h.get("responded_with") or 200) >= 400]
    out.append("## A-07: does Bolna redeliver after a failure?")
    if not failed:
        out.append("- no failing responses were recorded (run webhook_capture.py --fail-once)")
    for f in failed:
        key = (_exec_id(f["body_json"]), f["body_json"].get("status"))
        later = [
            h
            for h in json_hooks
            if h["seq"] > f["seq"]
            and (_exec_id(h["body_json"]), h["body_json"].get("status")) == key
        ]
        out.append(
            f"- delivery #{f['seq']} (status {key[1]}) got HTTP {f['responded_with']}; "
            f"later deliveries of the same status: {len(later)} -> "
            f"{'REDELIVERED' if later else 'NOT redelivered (in the window observed)'}"
        )
    out.append("")

    # webhook before our /call response?
    call = latest_call_capture(directory)
    out.append("## Did a webhook arrive before our POST /call response?")
    if call and json_hooks:
        exec_id = (call.get("response") or {}).get("execution_id")
        mine = [h for h in json_hooks if _exec_id(h["body_json"]) == exec_id]
        if mine:
            first = min(h["received_at"] for h in mine)
            before = first < call["t_response"]
            out.append(
                f"- first webhook {first[11:23]} vs /call response {call['t_response'][11:23]} -> "
                f"{'BEFORE (orphan handling is required)' if before else 'after'}"
            )
        else:
            out.append("- no webhooks for the latest s4 call's execution id")
    else:
        out.append("- needs an s4_call capture and webhook captures from the same call")
    return common.mask_in_text("\n".join(out))


def main() -> None:
    directory = common.CAPTURES
    text = summarize(directory)
    print(text)
    if directory.is_dir():
        path = directory / "webhook_summary.md"
        path.write_text(text, encoding="utf-8")
        print(f"\nsaved -> {path}")


if __name__ == "__main__":
    main()
