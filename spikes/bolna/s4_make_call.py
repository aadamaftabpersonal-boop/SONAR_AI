"""S-4: place ONE real call to a team test phone, then (optionally) watch it.

This is the first time Sonar touches Bolna. It is deliberately hard to misuse:
  - it will not run without --yes-test-line (you confirm the number is a verified team phone)
  - the number must be E.164 and is masked everywhere it is printed or saved
  - it never sets retry_config, scheduled_at or bypass_call_guardrails (Bible D-010)
  - --dry-run shows the exact request and needs no key, so you can check it today

    python spikes/bolna/s4_make_call.py --dry-run
    python spikes/bolna/s4_make_call.py --to +91XXXXXXXXXX --yes-test-line --watch

Answer the phone as a shopkeeper. Try: available + price, then not available, then a hesitant
"maybe". Record what the phone showed as the caller number (and any spam label) in FEASIBILITY.md.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import s6_capture_execution as s6  # noqa: E402


def build_user_data(item: str, attributes: dict[str, str]) -> dict[str, str]:
    """Same keys the Sonar backend sends (app.services.query.build_user_data)."""
    return {
        "category": "pharmacy",
        "item": item,
        "attributes_text": ", ".join(f"{k.replace('_', ' ')} {v}" for k, v in attributes.items()),
        "required_fields_text": "availability, price",
    }


def build_request(agent_id: str, to: str, user_data: dict[str, str], from_number: str = "") -> dict:
    body = {"agent_id": agent_id, "recipient_phone_number": to, "user_data": user_data}
    if from_number:
        body["from_phone_number"] = from_number
    return body


def parse_attributes(pairs: list[str]) -> dict[str, str]:
    out = {}
    for pair in pairs:
        if "=" not in pair:
            sys.exit(f"--attr must look like key=value, got {pair!r}")
        key, _, value = pair.partition("=")
        out[key.strip()] = value.strip()
    return out


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument("--to", default="", help="E.164; defaults to SPIKE_TEST_PHONE in .env")
    p.add_argument("--agent-id", default="", help="defaults to BOLNA_AGENT_ID_PHARMACY")
    p.add_argument("--from", dest="from_number", default="", help="omit to use the account default")
    p.add_argument("--item", default="Paracetamol")
    p.add_argument(
        "--attr", action="append", help="key=value (repeatable; default strength=500 mg)"
    )
    p.add_argument("--yes-test-line", action="store_true", help="confirm --to is a team test phone")
    p.add_argument("--watch", action="store_true", help="poll the execution after dialing (S-6)")
    p.add_argument(
        "--dry-run", action="store_true", help="print the request and exit; no key needed"
    )
    args = p.parse_args()

    common.load_env()
    to = args.to or common.env("SPIKE_TEST_PHONE")
    agent_id = args.agent_id or common.env("BOLNA_AGENT_ID_PHARMACY")
    from_number = args.from_number or common.env("BOLNA_FROM_PHONE_NUMBER")
    base = common.env("BOLNA_API_BASE_URL", common.DEFAULT_BASE_URL)
    attrs = parse_attributes(args.attr or ["strength=500 mg"])
    user_data = build_user_data(args.item, attrs)

    shown = build_request(
        agent_id or "<agent-id>",
        common.mask_phone(to) if to else "<to>",
        user_data,
        common.mask_phone(from_number) if from_number else "",
    )
    print("request (number masked):")
    print(json.dumps({"POST": f"{base}/call", "body": shown}, indent=2))
    if args.dry_run:
        print("\ndry run: nothing was sent.")
        return

    if not common.is_e164(to):
        sys.exit("--to (or SPIKE_TEST_PHONE) must be E.164, e.g. +91XXXXXXXXXX")
    if from_number and not common.is_e164(from_number):
        sys.exit("--from must be E.164")
    if not args.yes_test_line:
        sys.exit("refusing to dial: add --yes-test-line to confirm this is a verified team phone")
    key = common.require("BOLNA_API_KEY", "Get it from the organisers (spike S-1).")
    if not agent_id:
        sys.exit("missing agent id: set BOLNA_AGENT_ID_PHARMACY in .env or pass --agent-id")

    body = build_request(agent_id, to, user_data, from_number)
    t_sent = common.utcnow()
    with httpx.Client(timeout=30) as client:
        resp = client.post(f"{base}/call", headers=common.auth_headers(key), json=body)
        t_received = common.utcnow()
        try:
            data = resp.json()
        except ValueError:
            data = {"_non_json_body": resp.text[:500]}
        capture = {
            "t_sent": t_sent.isoformat(),
            "t_response": t_received.isoformat(),
            "http_status": resp.status_code,
            "request": {**body, "recipient_phone_number": common.mask_phone(to)},
            "response": data,
        }
        path = common.save_capture(f"s4_call_{common.stamp()}.json", capture)
        print(f"\nHTTP {resp.status_code}: {json.dumps(data)}")
        print(f"saved -> {path.name}")
        if resp.status_code != 200:
            print("\nNot a 200. Record the exact message in FEASIBILITY.md (B-02 / B-03 evidence).")
            sys.exit(1)

        execution_id = data.get("execution_id")
        print(f"\nexecution_id = {execution_id}   (answer the phone as a shopkeeper now)")
        if args.watch and execution_id:
            s6.poll_execution(execution_id, base=base, key=key, client=client)
        elif execution_id:
            print(
                f"watch it later with: python spikes/bolna/s6_capture_execution.py {execution_id}"
            )


if __name__ == "__main__":
    main()
