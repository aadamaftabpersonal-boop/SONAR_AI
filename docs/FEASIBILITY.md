# Bolna feasibility (Phase 1 spike)

**Status: NOT RUN.** No Bolna key yet (waiting on the organisers). Every row below is blank on
purpose: this file records what we *observed*, with a capture file path or a documentation URL and
date as evidence. A claim without evidence does not go here.

How to run each step: `spikes/bolna/README.md`. Raw captures stay local; commit only redacted
fixtures (`scripts/redact_fixture.py`).

---

## S-1 Account, key, wallet, plan (resolves A-03, B-02)
| Item | Observed | Evidence |
|---|---|---|
| Key works for an authenticated request | | |
| Plan (trial or paid) | | |
| Wallet balance | | |
| Concurrency shown | | |
| Calls only to verified numbers? How do we verify one? | | |
| Free credits / buildathon credits | | |
**B-02 status:**

## S-2 Agent and prompt variables (resolves A-09)
| Item | Observed | Evidence |
|---|---|---|
| Placeholder syntax that works in the prompt | | |
| First spoken question contains the substituted item | | |
| Agent id recorded in `.env` (never here) | | |
| Prompt synced to `docs/agent/prompt_v1.md` | | |

## S-3 Public webhook (resolves A-17, B-06)
| Item | Observed | Evidence |
|---|---|---|
| Tunnel used | | |
| "Send test" payload arrived | | |
| Payload keys (test) | | |
| Source IP / X-Forwarded-For | | |
**B-06 status:**

## S-4 First real call (resolves A-04, A-05, B-03)
| Item | Observed | Evidence |
|---|---|---|
| `POST /call` HTTP status, `execution_id` | | |
| Exact 400 message if it failed | | |
| Phone rang; conversation worked | | |
| Caller number shown on the phone | | |
| Marked as spam / blocked? | | |
| Default `from` number works for India? | | |
**G1a (a real call was placed):**  **B-03 status:**

## S-5 Webhook behaviour (resolves A-06, A-07, A-18)
Paste the output of `s5_summarize_webhooks.py` here after three calls (answered, unanswered, hung up).
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
Paste the field table from `s6_*_REPORT.md`.
| Item | Observed | Evidence |
|---|---|---|
| Field names and types | | |
| `transcript`: string or structured? speaker labels? | | |
| `total_cost` and its currency | | |
| `telephony_data.recording_url` present? | | |
| Webhook body equals Get Execution body? | | |
| Error shape: unknown id | | |
| Error shape: wrong key | | |

## S-7 Extractions (resolves A-08)
| Item | Observed | Evidence |
|---|---|---|
| `extracted_data` nested or flat | | |
| `confidence` per field present? | | |
| Which statuses populate it | | |
| Field never discussed: null or absent? | | |
| `supporting_quote` is a verbatim substring of the transcript (n of N calls) | | |

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

| Capability | VERIFIED / FAILED / WORKAROUND | Evidence |
|---|---|---|
| Agent with variables | | |
| Outbound call | | |
| Status events | | |
| Webhook authentication options | | |
| Verify-by-pull | | |
| Extraction | | |
| Language | | |
| Cost field | | |
| Retention | | |

**Decision: GO / GO-WITH-CHANGES / NO-GO**

Changes required to the Bible and code (list each, with the file):

1.
