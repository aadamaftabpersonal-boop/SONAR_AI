# Improvements and scaling plan

What we would do next, in what order, and what has to be true first. Written 2026-10-25 after the
first live calls (spike S-4/S-6). Nothing here is a promise: every item says what it depends on and
what would prove it worked. "Unknown" means we have not measured it yet.

Legend: **Built** (in the repo), **Partly**, **Not built**. Effort: S (hours), M (days), L (weeks).

---

## 0. What the first live calls taught us

| Finding | Evidence | What it changes |
|---|---|---|
| The call path works: `POST /call`, ring, talk, extractions, recording | 4 calls, 2026-10-25 | The core bet is feasible |
| Voicemail detection hung up on a person who was listening quietly | 2 calls, `voicemail_detected` at ~10 s | Detection is off for tests; retest on its own |
| Speech-to-text turned "milligrams" into "millie gills"; the agent read it as a different product | 1 call, 72 s | Units spelled out (done), transcriber keywords, one repeat-question rule |
| A small model asked questions the list did not allow | 1 call | Prompt rule added |
| Extractions arrive nested as `extracted_data.sonar.<name>` with `objective` or `subjective` | captured payloads | Parser fixed and tested (done) |
| Cost looks like 3.0 per 30-second block | 4 calls: 10 s 3.0, 48 s 6.0, 72 s 9.0 | Hypothesis only: likely US cents. Confirm against the wallet |
| Trial plan only calls verified numbers | HTTP 400, exact message captured | Real shops need a paid plan |

---

## 1. Agent quality (the biggest lever on result quality)

| # | Improvement | Status | Effort | Proof it worked |
|---|---|---|---|---|
| A1 | Transcriber **keywords and context** per call (item name, units, "rupees") | Not built | S | Fewer wrong transcripts on the 12-call script |
| A2 | Units spoken in full (`500 milligrams`) | **Built** | S | Test in `test_query.py` |
| A3 | Repeat-once rule for unclear answers; "different" only on a clear no | **Built** (prompt v1, paste into Bolna) | S | Script case 4 |
| A4 | Off-topic guard: "I can only ask whether you have it" | **Built** (prompt v1) | S | Script cases 7 and 8 |
| A5 | Compare a stronger model on the same script | Not built | S | Fewer misread answers per 12 calls, and the cost difference |
| A6 | Re-test voicemail detection with a longer wait; keep `call_outcome` as the backstop | Not built | S | No false hang-ups across 10 calls |
| A7 | Yes/no phrasing for every question, one question per turn | Partly | S | Shorter calls, fewer chats |
| A8 | **12-call acceptance script** with fixed answers (yes, no, different brand, noisy, Hindi, mumbled, opt-out, advice question, silence, voicemail) | Script written (`docs/agent/ACCEPTANCE_CALLS.md`), not run | S | Counts of correct / Uncertain / wrong recorded in `METRICS.md` |
| A9 | Prompt versioning: `prompt_v2.md` for any change, tests keep it honest | Partly | S | `test_agent_prompt.py` passes |
| A10 | Indian-English voice (lower pitch, slower) and a transcriber comparison: Sarvam vs Deepgram, both with keywords (D-056) | Not run; steps in `docs/agent/VOICE_AND_TRANSCRIBER.md` | S | Fewer misheard words on the acceptance calls, as x of N |
| A11 | Validator: an exact-match "no" followed by the shop reaffirming is Uncertain; alternatives must be in the shop's own words (D-055) | **Built**, regression test from the 2026-10-25 call | S | `test_validator.py` |

Rule: the agent is an unreliable witness. We never make it smarter by letting it guess; we make it
fail safe (Uncertain) and show the evidence.

---

## 2. Multilingual

| # | Improvement | Status | Effort | Depends on |
|---|---|---|---|---|
| L1 | Hindi agent (prompt, voice, transcriber `hi`) | Partly: Hindi prompt exists in Bolna, untested | S | A test call with a Hindi speaker (S-8) |
| L2 | Language per shop in the directory (`language` field) so the call starts in the shop's language | Not built | M | L1 result |
| L3 | Auto-switch only after S-8 shows it is safe; today it is "requested or auto-detected" | Not built | S | S-8 |
| L4 | Kannada, Tamil, Telugu, Marathi: add one language at a time, each with its own 5-call test | Not built | M per language | Provider support for voice and transcriber (check, unknown) |
| L5 | UI in Hindi and one regional language; result copy translated, not machine-guessed | Not built | M | Review by a native speaker |
| L6 | Read-aloud result in the user's language | Partly (browser speech, English) | S | Browser voices available |
| L7 | Numbers and units in local speech ("bees rupaye", "paanch sau milligram") normalised before validation | Not built | M | Real Hindi transcripts |

Never ship a language without a native-speaker check of the disclosure and the opt-out line.

---

## 3. Map and location (OpenStreetMap)

Built: Leaflet with OSM tiles, click to choose a place, search radius, result pins, an offline
radar tab, visible attribution, referer, no prefetching.

| # | Improvement | Status | Effort | Note |
|---|---|---|---|---|
| M1 | Place search (geocoding) in the search box | Not built | M | OSM's Nominatim policy forbids autocomplete and heavy use; use a geocoder with a proper plan or search on Enter only |
| M2 | **Own tile source before any real traffic.** The public OSM tile server is for light use only | Not built | M | `VITE_TILE_URL` is already configurable; pick a hosted provider or self-host |
| M3 | Marker clustering and "call status" colours on pins | Not built | S | |
| M4 | "Directions" link per shop (opens the user's maps app; no routing in our code) | Not built | S | |
| M5 | Walking/driving distance instead of straight-line | Not built | M | Needs a routing service |
| M6 | Shop opening hours on the card from the directory, labelled with a source and a date | Not built | S | |
| M7 | Privacy: round the user's location sent to the server (about 100 m) unless they choose precision | Not built | S | |

---

## 4. UI and product experience

| # | Improvement | Status | Effort |
|---|---|---|---|
| U1 | Live call ticker: show "calling shop 2 of 5" with elapsed time | Not built (flag exists) | M |
| U2 | Audio replay of the recording, only with consent, expiring | Not built (flag exists) | M |
| U3 | Voice input for the question | Not built (flag exists) | M |
| U4 | "Why this answer?" panel: quote, time, confidence, the check that passed | Partly (evidence shown) | S |
| U5 | Result freshness chips ("confirmed 4 min ago") and an auto "re-check" | Partly | S |
| U6 | Empty, error and slow states for every screen; skeletons everywhere | Partly | S |
| U7 | Mobile layout pass and thumb-reachable controls | Partly | S |
| U8 | Accessibility: keyboard order, contrast, screen-reader labels on the map | Partly | M |
| U9 | Share a result as a link with an expiry | Not built | M |
| U10 | Browser end-to-end test (Playwright) for the main flow | Not built | M |
| U11 | Visually re-check map, radar, ledger and picker in a real browser (never verified visually, only unit-tested) | Not done | S |

---

## 5. Reliability and scale

Assumptions (unknown until measured): Bolna's concurrency cap on a paid plan, rate limits, and
whether the caller number is trusted by Indian carriers.

| # | Improvement | Status | Effort | Why |
|---|---|---|---|---|
| R1 | **Public webhook** through a stable host (not a laptop tunnel) | Not built | M | Needed for any live use |
| R2 | Cache reuse: a fresh answer for the same shop and item is shown instead of calling again | Not built (T7.4) | M | Cuts cost and shop annoyance the most |
| R3 | Stop rule on by default after a trial (it is behind a flag today) | Built, flag off | S | Fewer calls per search |
| R4 | Several workers on the same Postgres queue (`SKIP LOCKED`) | Design allows it | M | One worker is fine for hundreds of searches a day |
| R5 | Per-shop call windows (business hours, lunch, closing day) | Partly | M | Fewer wasted calls and complaints |
| R6 | Provider fallback: a second voice provider behind the same interface | Interface exists | L | Only if Bolna limits bind |
| R7 | Alerts: stuck calls, balance low, webhook silent, error rate | Not built | M | Operate without watching |
| R8 | Backups and a restore test for the database | Not built | S | |
| R9 | Load test with the simulated provider (1,000 searches) | Not built | S | Finds our bottlenecks, not Bolna's |
| R10 | Hosting choice and a deploy script (image, compose and env checker exist) | Partly | M | Needs an owner decision |

---

## 6. Trust, consent and law (blocks any real shop outside the team)

| # | Item | Status |
|---|---|---|
| T1 | Written consent per shop, recorded before any call (script A) | Built in code, not exercised with real shops |
| T2 | Opt-out in one sentence, honoured at once, tested | Built; run the refusal call (script case 5) |
| T3 | **Legal review** of automated calls to businesses in India (telecom and spam-call rules, recording and AI disclosure). We have not done this and cannot confirm the position | Not done |
| T4 | Retention: events 30 days, excerpts 90 days, delete on request | Built |
| T5 | Pharmacy safety: blocked-terms list reviewed by a pharmacist | Not done (starter list only) |
| T6 | Caller ID and spam labelling check on 3 phones from different carriers | Not done |
| T7 | Privacy notice and terms page | Not built |

---

## 7. Data and supply (the real scale limit)

| # | Item | Status | Effort |
|---|---|---|---|
| D1 | Shop onboarding flow: consent, language, hours, category | Not built | M |
| D2 | Inbound shop line: shops call in to update stock themselves | Not built (flag exists) | L |
| D3 | Shop digest ("5 people asked for X near you this week"), the reason a shop says yes | Built behind a flag | M to test |
| D4 | Directory import and de-duplication | Partly (seed file) | M |
| D5 | Watches: "tell me when X is back in stock" | Not built | L |
| D6 | Question compiler: free text to category, item, fields, with a human-checkable preview | Not built | L |
| D7 | Public API `/api/v1/ask` for other apps, keyed and rate-limited | Not built | M |
| D8 | More categories beyond pharmacy and computer repair, each with its own prompt and extractions | Partly | M each |

---

## 8. Measurement (so we know it works)

| # | Item | Status |
|---|---|---|
| E1 | Live-only metrics with denominators: answer rate, correct rate, Uncertain rate, cost per answered search | Built |
| E2 | Ground-truth checks: someone walks in and confirms | Built, not run |
| E3 | Human review of a sample of transcripts per week | Built, not run |
| E4 | The 12-call acceptance script (A8) as a gate before each prompt change | Not built |
| E5 | Cost per call recorded and the unit confirmed | Unknown |
| E6 | Three buyer or shopkeeper interviews (`DISCOVERY_LOG.md`) | Not done |
| E7 | Business-case hypotheses H-1 to H-5 | All "not run" |

---

## 9. Suggested order

1. **Now (days):** paste prompt v1 changes into Bolna; set `price_currency_stated` to Text; add transcriber keywords (A1); run the 12-call script (A8); confirm cost units (E5); run the refusal call (T2).
2. **Next (a week):** webhook through a stable host (R1); full search through Sonar with your own phone as the shop; Hindi test (L1); re-check the UI visually (U11).
3. **Before any outside shop:** legal review (T3); caller-ID check (T6); pharmacist review (T5); consent flow tested (T1); paid Bolna plan.
4. **Pilot (3 to 5 consenting shops):** cache reuse (R2), stop rule on (R3), digest (D3), live ticker (U1), own tile source (M2), alerts (R7).
5. **Then, only if the pilot shows value:** more languages (L4), inbound line (D2), watches (D5), API (D7).

Do not start step 4 until step 3 is done, and do not call it a product until E1 shows real numbers
from real shops.
