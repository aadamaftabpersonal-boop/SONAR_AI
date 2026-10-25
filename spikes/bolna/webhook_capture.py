"""S-3: a tiny webhook receiver that records exactly what Bolna sends.

It answers every POST with 200 (or what you configure) and writes the full request to
spikes/bolna/captures/. It decides nothing and trusts nothing; it is a tape recorder.

    python spikes/bolna/webhook_capture.py --port 9000
    python spikes/bolna/webhook_capture.py --port 9000 --fail-once     # S-5: does Bolna retry on 500?
    python spikes/bolna/webhook_capture.py --port 9000 --respond-status 503

Expose it with any HTTPS tunnel (cloudflared, ngrok, ...) and paste the tunnel URL into the agent's
Webhook Configuration. Note which tunnel you used in docs/FEASIBILITY.md.
"""

from __future__ import annotations

import argparse
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402

SENSITIVE_HEADERS = {"authorization", "cookie", "x-api-key", "proxy-authorization"}


def redact_headers(headers: dict[str, str]) -> dict[str, str]:
    return {k: ("<redacted>" if k.lower() in SENSITIVE_HEADERS else v) for k, v in headers.items()}


class CaptureState:
    def __init__(self, out_dir: Path, fail_once: bool, respond_status: int) -> None:
        self.out_dir = out_dir
        self.fail_once = fail_once
        self.respond_status = respond_status
        self.seq = 0
        self.lock = threading.Lock()
        self.failed_already = False

    def next_seq(self) -> int:
        with self.lock:
            self.seq += 1
            return self.seq

    def status_for_next(self) -> int:
        with self.lock:
            if self.fail_once and not self.failed_already:
                self.failed_already = True
                return 500
            return self.respond_status


def make_handler(state: CaptureState) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args) -> None:  # we print our own concise line
            pass

        def _reply(self, status: int, body: dict) -> None:
            payload = json.dumps(body).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self) -> None:  # lets you check the tunnel from a browser
            self._reply(200, {"ok": True, "service": "sonar-webhook-capture"})

        def do_POST(self) -> None:
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length else b""
            text = raw.decode("utf-8", errors="replace")
            try:
                parsed = json.loads(text)
            except ValueError:
                parsed = None
            status = state.status_for_next()
            seq = state.next_seq()
            record = {
                "seq": seq,
                "received_at": common.utcnow().isoformat(),
                "method": "POST",
                "path": self.path,
                "client_ip": self.client_address[0],
                "x_forwarded_for": self.headers.get("X-Forwarded-For"),
                "headers": redact_headers({k: v for k, v in self.headers.items()}),
                "body_text": text,
                "body_json": parsed,
                "responded_with": status,
            }
            body_status = parsed.get("status") if isinstance(parsed, dict) else None
            exec_id = None
            if isinstance(parsed, dict):
                exec_id = parsed.get("execution_id") or parsed.get("id")
            name = f"webhook_{seq:04d}_{body_status or 'nostatus'}_{common.short(exec_id)}.json"
            common.save_capture(name, record, state.out_dir)
            print(
                f"[{seq:04d}] {record['received_at'][11:23]} ip={record['client_ip']} "
                f"status={body_status} exec={common.short(exec_id)} -> {status}  ({name})",
                flush=True,
            )
            self._reply(status, {"ok": status < 400})

    return Handler


def make_server(
    host: str, port: int, out_dir: Path, fail_once: bool = False, respond_status: int = 200
) -> ThreadingHTTPServer:
    state = CaptureState(out_dir, fail_once, respond_status)
    server = ThreadingHTTPServer((host, port), make_handler(state))
    server.capture_state = state  # type: ignore[attr-defined]
    return server


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=9000)
    p.add_argument("--out", type=Path, default=common.CAPTURES)
    p.add_argument("--fail-once", action="store_true", help="answer the first POST with 500")
    p.add_argument("--respond-status", type=int, default=200)
    args = p.parse_args()

    server = make_server(args.host, args.port, args.out, args.fail_once, args.respond_status)
    print(f"listening on http://{args.host}:{args.port}  -> captures in {args.out}")
    print("expose with an HTTPS tunnel, then set it as the agent's webhook URL. Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")


if __name__ == "__main__":
    main()
