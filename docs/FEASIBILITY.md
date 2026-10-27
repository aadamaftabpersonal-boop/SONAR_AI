# Bolna feasibility (Phase 1 spike)

**Status: PARTLY RUN (updated 2026-10-27).** Four calls to team phones on 2026-10-25, placed with the
spike scripts (`s4_make_call.py --watch`, which also pulled `GET /executions/{id}`). That passes
**G1a** (a real call was placed). Not run yet: S-3 and S-5 (webhooks), S-8 to S-10, and the G1
decision (S-11). This file records only what was observed, with evidence. "Not recorded" means we
did not write it down at the time; it is not a finding.

Evidence: raw captures stay on the machine that ran the spike, in
`D:\bolnabuildathon\spikes\bolna\captures\` (git-ignored). Named files below are from there. Copy a
redacted version into `backend/tests/fixtures/bolna/` with `scripts/redact_fixture.py` before relying
on it in a test.

How to run each step: `spikes/bolna/README.md`.

---

## S-1 Account, key, wallet, plan (resolves A-03, B-02)
| Item | Observed | Evidence |
|---|---|---|
| Key works for an authenticated request | Yes: `POST /call` and `GET /executions/{id}` both succeeded | 4 calls, 2026-10-25; `s4_call_20261025T110010313620Z.json` |
| Plan (trial or paid) | Trial | Agent Studio banner, 2026-10-25 |
| Wallet balance | Not recorded. Record it before and after the next call (that also settles the cost unit) | |
| Concurrency shown | Not recorded | |
| Calls only to verified numbers? How do we verify one? | Yes: a call to an unverified number was refused with HTTP 400 (exact message is in the local capture; paste it into S-10) | capture, 2026-10-25 |
| Free credits / buildathon credits | $10 Buildathon credit, as stated on the credits request form; extra Bolna and partner credits being requested | credits form, 2026-10-27 |
**B-02 status:** partly resolved. A key and a trial account work for team phones. Calling any real
shop needs a paid plan or per-number verification.

## S-2 Agent and prompt variables (resolves A-09)
*Observed in the Agent Studio UI (screenshot, 2026-10-25):* variables are written
`{{variable_name}}`; the studio showed a displayed cost of $0.060 per minute for the default
"Cascaded" voice engine, and a trial-plan banner saying outbound calls are limited to verified
phone numbers. The $0.060 is the studio's displayed estimate, **not** a measured call cost.

| Item | Observed | Evidence |
|---|---|---|
| Placeholder syntax that works in the prompt | `{{item}}` and `{{attributes_text}}` | spoken in a live call (next row) |
| First spoken question contains the substituted item | Yes: "Do you currently have Paracetamol strength 500 mg available?" | `s6_fd721701_006_completed.json`, transcript |
| Agent id recorded in `.env` (never here) | Yes | `.env` (local) |
| Prompt synced to `docs/agent/prompt_v1.md` | **Not confirmed.** The repo's v1 gained the repeat-once rule, the off-topic guard and units in full after these calls; check the dashboard matches before the next call | commit `d3843fd` |
**A-09:** resolved (double braces).

## S-3 Public webhook (resolves A-17, B-06)
| Item | Observed | Evidence |
|---|---|---|
| Tunnel used | Not run | |
| "Send test" payload arrived | Not run | |
| Payload keys (test) | Not run | |
| Source IP / X-Forwarded-For | Not run | |
**B-06 status:** open.

## S-4 First real call (resolves A-04, A-05, B-03)
| Item | Observed | Evidence |
|---|---|---|
| `POST /call` HTTP status, `execution_id` | Accepted, `execution_id` returned (one began `fd721701`) | `s4_call_20261025T110010313620Z.json` |
| Exact 400 message if it failed | Unverified number: HTTP 400 (see S-1) | local capture |
| Phone rang; conversation worked | Yes, on 4 calls. Two were cut at about 10 s by voicemail detection while a person was listening quietly; detection was then turned off for tests | 4 calls, 2026-10-25 |
| Caller number shown on the phone | Not recorded | |
| Marked as spam / blocked? | Not recorded | |
| Default `from` number works for India? | It reached the team's Indian phones. Pickup by real shops and spam labelling are untested | 4 calls |
**G1a (a real call was placed): PASSED, 2026-10-25.**  **B-03 status:** partly resolved (team phones
only; caller ID not recorded).

## S-5 Webhook behaviour (resolves A-06, A-07, A-18)
**Not run.** Paste the output of `s5_summarize_webhooks.py` here after three calls (answered,
unanswered, hung up).
| Question | Answer | Evidence |
|---|---|---|
| A-18: id and status top-level? Key names? | | |
| A-06: custom headers delivered? | | |
| A-07: redelivery after a 500? | | |
| Statuses delivered, in what order | | |
| Duplicates seen? | | |
| Fields present at `call-disconnected` vs `completed` | | |
| First webhook before our `/call` response? | | |
| Source IPs match the documented three? | | |

## S-6 Get Execution payload
| Item | Observed | Evidence |
|---|---|---|
| Field names and types | `status` (string, e.g. `completed`), `conversation_duration` (number, seconds, e.g. `72.0`), `total_cost` (number), `transcript` (string), `extracted_data` (object, see S-7), `telephony_data` (object, with `hangup_by` e.g. `Callee` and `hangup_reason` e.g. `Call recipient hungup`) | `s6_fd721701_006_completed.json` |
| `transcript`: string or structured? speaker labels? | One string; one line per turn, labelled `assistant:` and `user:` (the business is `user`) | same |
| `total_cost` and its currency | 3.0 for 10 s, 6.0 for 48 s, 9.0 for 72 s: looks like 3.0 per started 30 s. **Unit not confirmed** (no currency field seen; possibly US cents). Check against the wallet | 4 calls |
| `telephony_data.recording_url` present? | A recording was produced (`IMPROVEMENTS.md` §0); whether a URL is always present is not recorded | |
| Webhook body equals Get Execution body? | Not run (needs S-5) | |
| Error shape: unknown id | Not recorded (`s6_capture_execution.py --probe-errors`) | |
| Error shape: wrong key | Not recorded | |

## S-7 Extractions (resolves A-08)
| Item | Observed | Evidence |
|---|---|---|
| `extracted_data` nested or flat | Nested: `extracted_data.sonar.<field>`. Each field is an object with `objective` and `subjective` (one of them null), `confidence`, and `validation.is_valid`. The parser takes whichever value is not empty (fixed in `d3843fd`) | `s6_fd721701_006_completed.json`; `test_bolna_provider.py` |
| `confidence` per field present? | Yes | same |
| Which statuses populate it | Seen at `completed`; earlier statuses not recorded | |
| Field never discussed: null or absent? | Not recorded | |
| `supporting_quote` is a verbatim substring of the transcript (n of N calls) | Not counted yet | |
**A-08:** shape resolved; quote reliability still to count.

### Finding: a misheard unit (call `fd721701`, 72 s)
Speech-to-text heard "500 milligrams" as "millie gills". The agent treated it as a different
product, then talked about the word, and never asked again, so no price was captured. The shop's last
words were "yes we have it". Changes: units are now spoken in full, the prompt has a repeat-once rule
and an off-topic guard (`d3843fd`), and the validator now treats an exact-match "no" followed by the
shop reaffirming as `UNCERTAIN` with flag `CONTRADICTORY` (regression test in `test_validator.py`).
Next: transcriber keywords and an Indian-English transcriber and voice (`docs/agent/VOICE_AND_TRANSCRIBER.md`).

## S-8 Language and accent (resolves A-10)
| Case | Transcribed correctly / partly / wrongly | Evidence |
|---|---|---|
| | | |
**Decision:**

## S-9 Retention and recording (resolves A-14)
| Item | Observed | Evidence |
|---|---|---|
| Can recording be turned off? | | |
| Is `recording_url` always produced? | | |
| Required disclosure wording for callees | | |

## S-10 Limits and errors (resolves A-15)
| Case | HTTP status and exact message | Evidence |
|---|---|---|
| Invalid agent id | | |
| Invalid `from_phone_number` | | |
| Malformed number | | |
| Unverified number on trial | | |
| Two concurrent calls, then a third | | |

## S-13 Live transcript and recording playback (resolves A-20, A-21, A-22)
| Item | Observed | Evidence |
|---|---|---|
| Transcript grows during `in-progress`? How fresh? | | |
| `recording_url` plays in a browser tag? How long does it live? | | |
| Any live-monitoring feature | | |

---

## S-11 Gate G1 decision

Filled in as far as the evidence goes (2026-10-27). The decision waits for S-3 and S-5.

| Capability | VERIFIED / FAILED / WORKAROUND | Evidence |
|---|---|---|
| Agent with variables | VERIFIED | S-2 row 2 |
| Outbound call | VERIFIED for verified team phones only (trial) | S-4 |
| Status events | open (S-5) | |
| Webhook authentication options | open (S-3, S-5) | |
| Verify-by-pull | `GET /executions/{id}` returns the full record: VERIFIED. Pull triggered by a webhook: open (S-5) | S-6 |
| Extraction | VERIFIED shape; quote reliability open | S-7 |
| Language | English works for a clear speaker; a unit was misheard; Indian-English and Hindi open (S-8) | S-7 finding |
| Cost field | present; unit WORKAROUND until checked against the wallet | S-6 |
| Retention | open (S-9) | |

**Decision: not taken yet. GO / GO-WITH-CHANGES / NO-GO**

Changes required to the Bible and code (list each, with the file):

1.
