# Phase 1: Bolna spike runbook

Goal: replace our assumptions about Bolna with captured, real responses (Gate G1). Everything here
is a throwaway, standalone script: plain `httpx` and the standard library, no app code.

**Safety rules (they are enforced in the code, but read them anyway)**
- Calls go only to a **verified team phone**. `s4_make_call.py` refuses without `--yes-test-line`.
- Never call a shop here. Shop calls need recorded consent first (Bible D-004).
- Your API key lives in `.env` (git-ignored). The scripts never print or save it.
- Phone numbers are masked in everything printed or saved. Raw captures stay in
  `spikes/bolna/captures/` (git-ignored). Redact before committing anything (see step 7).
- Keep each test call under about 2 minutes, and stop after the first failure to record it.

## Before you have a key (do these today)

```powershell
backend\.venv\Scripts\python spikes\bolna\s4_make_call.py --dry-run
backend\.venv\Scripts\python spikes\bolna\webhook_capture.py --port 9000
```
The dry run prints the exact request with no key and sends nothing. The capture server starts and
saves anything POSTed to it; test it with `curl -X POST localhost:9000 -d "{}"`.

## Setup once the key arrives

Put these in `.env` (never commit it):
```
BOLNA_API_KEY=...
BOLNA_AGENT_ID_PHARMACY=...        # created in the Bolna dashboard (step S-2)
SPIKE_TEST_PHONE=+91XXXXXXXXXX     # a verified team phone, E.164
BOLNA_FROM_PHONE_NUMBER=           # leave empty to use the account default
```

## Order of work (matches the Build Map)

| Step | Task | Command / action | What to record in `docs/FEASIBILITY.md` |
|---|---|---|---|
| 1 | S-1 | Check the dashboard: plan, wallet, concurrency, whether numbers must be verified | plan, balance, limits, how to verify a number |
| 2 | S-2 | Create the agent in the dashboard using `docs/agent/prompt_v1.md` (to be written) with the placeholders `item`, `attributes_text`, `required_fields_text`; set call end ~120 s and hang up after ~10 s silence | exact placeholder syntax that worked |
| 3 | S-3 | Run `webhook_capture.py`, start an HTTPS tunnel to port 9000, paste the URL into the agent's Webhook Configuration, press **Send test** | which tunnel; did the test payload arrive; payload keys |
| 4 | S-4 | `s4_make_call.py --yes-test-line --watch` and answer the phone as a shopkeeper | HTTP status; `execution_id`; did the phone ring; the caller number it showed; any spam label |
| 5 | S-5 | Place 3 calls: (a) answered and finished, (b) let it ring out, (c) answered then hang up mid-sentence. Then `s5_summarize_webhooks.py`. Once more with `webhook_capture.py --fail-once` | the printed summary: A-18, A-06, A-07, order, duplicates, IPs, orphan timing |
| 6 | S-6, S-7 | The `--watch` run already saved snapshots and `*_REPORT.md`. Run `s6_capture_execution.py --probe-errors` once | field table, `extracted_data` shape (nested vs flat), error shapes |
| 7 | fixtures | `python scripts\redact_fixture.py <capture> backend\tests\fixtures\bolna\<name>.json`, then **read the result** | which fixtures were committed |

A tunnel is any tool that gives your localhost a public HTTPS URL, for example `cloudflared tunnel
--url http://localhost:9000` or `ngrok http 9000`. I have not checked that either is installed on
this machine. Behind a tunnel the socket peer is the tunnel, so the summary also reports
`X-Forwarded-For` for the source-IP check.

## What each script does

| Script | Spike | Notes |
|---|---|---|
| `webhook_capture.py` | S-3, S-5 | Tape recorder. `--fail-once` answers the first POST with 500 to see if Bolna retries. `--respond-status N` for other codes. |
| `s4_make_call.py` | S-4 | One call. Never sets `retry_config`, `scheduled_at` or `bypass_call_guardrails`. `--dry-run` needs no key. |
| `s6_capture_execution.py` | S-6, S-7, S-13 | Polls `GET /executions/{id}` and saves every change, a field report, transcript growth, and error shapes. |
| `s5_summarize_webhooks.py` | S-5 | Reads the webhook captures and answers A-18, A-06, A-07 with evidence. |
| `../../scripts/redact_fixture.py` | S-5, S-6 | Strips numbers, recording URLs, emails and auth values from a capture so it can become a fixture. |

## After the spike

1. Fill in `docs/FEASIBILITY.md`, including the GO / GO-WITH-CHANGES / NO-GO decision (S-11).
2. If a real payload differs from our assumptions, fix `app/services/events.py` (field names) and
   `app/domain/transitions.py` (status strings) and re-base the pipeline tests on the redacted
   fixtures. The simulator's payload shapes are assumptions until then.
3. Then implement `BolnaVoiceProvider` (T5.3) against those fixtures.
