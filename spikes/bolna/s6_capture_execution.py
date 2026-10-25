"""S-6 / S-7 / S-13: capture what GET /executions/{id} really returns.

Polls an execution while it runs and saves a snapshot every time the body changes, so you get:
  - the exact JSON field names and types (S-6, S-7: extracted_data shape, nesting vs flat keys)
  - whether the transcript grows during the call (S-13: live ticker feasibility)
  - what the record looks like at `call-disconnected` versus `completed`
  - the error shapes for an unknown id and a wrong key (--probe-errors)

    python spikes/bolna/s6_capture_execution.py EXECUTION_ID
    python spikes/bolna/s6_capture_execution.py EXECUTION_ID --once
    python spikes/bolna/s6_capture_execution.py --probe-errors

The API key comes from BOLNA_API_KEY in .env and is never printed or saved.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import uuid
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402


def fetch(client: httpx.Client, base: str, key: str, execution_id: str) -> tuple[int, object]:
    resp = client.get(f"{base}/executions/{execution_id}", headers=common.auth_headers(key))
    try:
        body = resp.json()
    except ValueError:
        body = {"_non_json_body": resp.text[:500]}
    return resp.status_code, body


def poll_execution(
    execution_id: str,
    *,
    base: str,
    key: str,
    interval: float = 2.0,
    timeout: float = 240.0,
    once: bool = False,
    out_dir: Path | None = None,
    client: httpx.Client | None = None,
) -> list[dict]:
    """Poll until a terminal status (plus one extra poll to catch late-filled fields)."""
    out_dir = out_dir or common.CAPTURES
    own_client = client is None
    client = client or httpx.Client(timeout=20)
    snapshots: list[dict] = []
    seen: set[str] = set()
    started = time.monotonic()
    terminal_polls = 0
    try:
        while True:
            t = common.utcnow()
            code, body = fetch(client, base, key, execution_id)
            digest = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
            status = body.get("status") if isinstance(body, dict) else None
            transcript = body.get("transcript") if isinstance(body, dict) else None
            tlen = len(transcript) if isinstance(transcript, str) else None
            if code != 200:
                print(f"{t:%H:%M:%S} http {code}: {str(body)[:200]}")
            elif digest not in seen:
                seen.add(digest)
                n = len(snapshots) + 1
                name = f"s6_{common.short(execution_id)}_{n:03d}_{status or 'nostatus'}.json"
                snap = {
                    "polled_at": t.isoformat(),
                    "http_status": code,
                    "transcript_chars": tlen,
                    "body": body,
                }
                common.save_capture(name, snap, out_dir)
                snapshots.append(snap)
                print(
                    f"{t:%H:%M:%S} change #{n}: status={status} transcript_chars={tlen} -> {name}"
                )
            if once:
                break
            if common.is_terminal(status):
                terminal_polls += 1
                if (
                    terminal_polls >= 2
                ):  # one extra poll: some fields fill in after the status flips
                    break
            if time.monotonic() - started > timeout:
                print(f"timeout after {timeout:.0f}s")
                break
            time.sleep(interval)
    finally:
        if own_client:
            client.close()

    if snapshots:
        write_field_report(execution_id, snapshots, out_dir)
    return snapshots


def write_field_report(execution_id: str, snapshots: list[dict], out_dir: Path) -> Path:
    final = snapshots[-1]["body"]
    lines = [
        f"# S-6 field report for {common.short(execution_id)}",
        "",
        f"snapshots: {len(snapshots)}; final status: `{final.get('status')}`",
        "",
        "## Fields in the final snapshot",
        common.markdown_table(common.type_table(final)),
        "",
        "## Transcript growth (S-13: is there live text during the call?)",
        "| # | polled_at | status | transcript chars |",
        "|---|---|---|---|",
    ]
    for i, s in enumerate(snapshots, 1):
        lines.append(
            f"| {i} | {s['polled_at'][11:23]} | {s['body'].get('status')} | {s['transcript_chars']} |"
        )
    extracted = final.get("extracted_data")
    lines += [
        "",
        "## extracted_data shape (S-7)",
        f"type: `{type(extracted).__name__}`",
        "```json",
        json.dumps(extracted, indent=2, ensure_ascii=False)[:2000],
        "```",
        "",
        "Compare with the webhook body for the same status (s5_summarize_webhooks.py): "
        "the docs say they match.",
    ]
    path = out_dir / f"s6_{common.short(execution_id)}_REPORT.md"
    path.write_text(common.mask_in_text("\n".join(lines)), encoding="utf-8")
    print(f"field report -> {path.name}")
    return path


def probe_errors(base: str, key: str, out_dir: Path | None = None) -> dict:
    """Record the error shape for an unknown execution id and for a wrong key."""
    results = {}
    with httpx.Client(timeout=20) as client:
        unknown = str(uuid.uuid4())
        code, body = fetch(client, base, key, unknown)
        results["unknown_execution_id"] = {"http_status": code, "body": body}
        code, body = fetch(client, base, "wrong-key-for-probe", unknown)
        results["wrong_api_key"] = {"http_status": code, "body": body}
    for name, r in results.items():
        print(f"{name}: http {r['http_status']} {str(r['body'])[:150]}")
    path = common.save_capture(f"s6_error_shapes_{common.stamp()}.json", results, out_dir)
    print(f"saved -> {path.name}")
    return results


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument("execution_id", nargs="?")
    p.add_argument("--interval", type=float, default=2.0)
    p.add_argument("--timeout", type=float, default=240.0)
    p.add_argument("--once", action="store_true", help="fetch a single snapshot and stop")
    p.add_argument("--probe-errors", action="store_true")
    args = p.parse_args()

    common.load_env()
    key = common.require("BOLNA_API_KEY", "Get it from the organisers (spike S-1).")
    base = common.env("BOLNA_API_BASE_URL", common.DEFAULT_BASE_URL)

    if args.probe_errors:
        probe_errors(base, key)
        return
    if not args.execution_id:
        sys.exit("give an EXECUTION_ID, or use --probe-errors")
    poll_execution(
        args.execution_id,
        base=base,
        key=key,
        interval=args.interval,
        timeout=args.timeout,
        once=args.once,
    )


if __name__ == "__main__":
    main()
