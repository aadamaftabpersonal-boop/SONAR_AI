# SONAR BIBLE

**Project:** Sonar — "Google for the offline world."
**Event:** Bolna Buildathon 2026 (Symphony × Y Combinator Buildathon)
**Document status:** **v2.1** (v2.0 + sponsor-reference fix) — v1.0 written 2026-10-24; v1.1 revised the same day for a sponsor strategy (now defined in compact form in §22.1, v2.1); **v2.0 adds Part II (Wave 2 differentiators, §46–§56)** and amends the decision log. Source of truth for product, architecture, contracts and decisions. Superseded or amended decisions are kept in the decision log (§43) and marked, never deleted.
**Companion:** `SONAR_BUILD_MAP_v2.md` (execution plan).

> **v2.0 change log**
> 1. **Part II added (§46–§56):** product ladder, business-model hypotheses, stop rule and shop learning loop, demand digest, inbound shop line, live ticker / listen-live tiers, voice front door, radar view, race clock, trust ledger, question compiler, watches, phone-as-API, ground-truth study, Wave 2 acceptance criteria, env vars, schema and API additions.
> 2. **New IDs, no renumbering:** FR-37…FR-57, NFR-15…NFR-19, US-13…US-18, AC-11…AC-16, D-031…D-043, A-19…A-27, B-09, R-14…R-20, spikes S-12…S-14, hypotheses H-1…H-5. All Part I IDs and contracts are unchanged.
> 3. **Amended (not deleted):** D-012, D-013, D-021 (see D-037, D-039). FR-36 "map" is superseded for the MVP by the SVG radar (D-038).
> 4. **Dangling sponsor references: found in v2.0, resolved in v2.1.** The v1.1 header, §0 and §2 pointed to an all-sponsor strategy (§22.1–§22.11), decisions D-023…D-030, a "Sponsor Lab" and task SP-1 that did not exist in the file body or the Build Map. v2.1 **reconstructs them in compact form from what the v1.1 text itself said** and nothing more: one section (§22.1, replacing the eleven sub-sections that were never present), eight decisions (D-023…D-030, marked *reconstructed*), the Sponsor Lab as a **P2 offline harness**, and SP-1 / T19.1 in the Build Map (Phase 19). Every reference now resolves. The baseline is unchanged and Bolna-only (D-001, D-002, D-011, D-023); the sponsor annex is DEFERRED and cannot block M1, M2 or M3. Anything beyond the v1.1 text (for example D-028, D-029) is marked as a v2.1 proposal, not recovered history.
> 5. **Not changed on purpose:** the schedule and deadline logic (B-04, R-12) and all Part I requirement text. The two documents share requirement IDs (`FR-*`, `NFR-*`), decision IDs (`D-*`), assumption IDs (`A-*`), blocker IDs (`B-*`), enum names and API paths. If they ever disagree, this Bible wins for *what* and *why*; the Build Map wins for *order*. Fix the disagreement in the same commit.

---

## 0. How to read this document

### 0.1 Status tags (used throughout both documents)

| Tag | Meaning | Rule |
|---|---|---|
| **VERIFIED** | Supported by official documentation we read, or by a successful test we ran. Carries a date and a source. | Safe to build against. Still re-check payload details during the spike (§21.3). |
| **ASSUMPTION** | Plausible, not confirmed. Has an ID (`A-nn`). | Never build irreversible work on it. Each has a "how to confirm" in §45. |
| **BLOCKER** | Prevents implementation or demo until resolved. Has an ID (`B-nn`). | Listed in §0.2 and §40. Build Map gates reference them. |
| **DECISION** | An explicitly chosen option with rationale. Has an ID (`D-nn`). | Change only by adding a new decision-log entry (§43). |
| **DEFERRED** | Deliberately postponed. | Must not block submission. |
| **UNVERIFIED** | A claim we could not confirm from an authoritative source, with the way to resolve it. | Never stated as fact in the pitch, UI or README. Optional-path UNVERIFIED items never block the baseline. |

**Integration-status vocabulary (sponsors and optional providers; used in §22.1 and Build Map Phase 19).** A sponsor is never "integrated" because an SDK was installed, a key was added or a logo was shown.

| Status | Meaning |
|---|---|
| `VERIFIED_IMPLEMENTED` | Documented capability confirmed **and** code exists **and** an automated test or recorded live capture passes. *(Nothing is at this level yet: no application code exists.)* |
| `VERIFIED_NOT_IMPLEMENTED` | Capability confirmed from official documentation we read; no code or test yet. |
| `PROPOSED` | Planned role; capability not yet confirmed. |
| `BLOCKED` | Cannot proceed until credentials, credits, KYC or account access exist. |
| `UNVERIFIED` | Could not be confirmed from an authoritative source. |

**Demonstration depth (D-levels), the minimum bar for calling a sponsor "demonstrated":** D0 documented · D1 feasibility proven with a captured, sanitised real response · D2 automated test passes against that fixture · D3 measured in the Sponsor Lab with honest provenance labels · D4 used in a live call path (agent variant) with a passing test call. See §22.1.

Documentation was read on **2026-10-24**. Where a documentation page was summarised from a fetch tool rather than read in a browser, the tag is still VERIFIED for the facts quoted, but the spike (Phase 1) re-confirms them against real responses. Raw provider payloads captured in the spike **override** anything written here.

### 0.2 Blockers at a glance (full list in §40 and §45)

| ID | Blocker | Why it matters | Owner action |
|---|---|---|---|
| B-01 | No confirmed consenting businesses | No real call may be placed to a business that has not agreed. There is no live-demo without them. | Start outreach on day one, in parallel with everything else. |
| B-02 | Bolna account state unknown: API key, wallet balance, plan | The trial plan is documented as limited to verified phone numbers. Calls to arbitrary consenting shops may need a paid plan or per-number verification. | Spike task S-1. |
| B-03 | Outbound caller-ID/number route for India unconfirmed | `from_phone_number` is optional and defaults to the account's number, but whether the default works for Indian recipients (and pickup rate) is untested. | Spike tasks S-1, S-4. |
| B-04 | Buildathon submission rules, judging criteria and deadline are not published on the page we read | We cannot plan the final week without a submission deadline. The only published date is the 2026-11-20 finale. | Find/ask organisers; confirm you have completed the "Apply now" application. |
| B-05 | Compliance position for automated information-gathering calls to businesses in India is unresolved | We have only secondary commentary, not the regulation text, and no legal advice. | Consent-only pilot (D-004) + questions in §31. |
| B-06 | Public HTTPS webhook endpoint reachable from Bolna during development | Bolna documents that the endpoint must be publicly accessible. | Tunnel for dev (S-3); hosted endpoint for demo. |
| B-07 | **Optional path only.** Plivo/Exotel Indian numbers need an India-registered business and KYC (Plivo docs: "business registration must be in India"; Exotel signup lists KYC documents). We do not know whether the team has such an entity. | Blocks any Plivo/Exotel feasibility call using Indian numbers. **Does not block the baseline.** | SP-1; fall back to documentation-backed matrix + Bolna's own route (D-025). |
| B-08 | **Optional path only.** Sponsor credits/API access for Sarvam, Deepgram, Cartesia, Plivo, Exotel are not confirmed for buildathon participants (the event page lists only Bolna and Sarvam credits as *registration perks*). | Blocks Sponsor Lab runs that need paid keys. **Does not block the baseline.** | SP-1; use each vendor's own signup terms, ask organisers; mark NOT_MEASURED if no access. |
| B-09 | **Optional path only (Wave 2).** The inbound shop line (§50) needs a Bolna inbound-capable agent and a number to receive calls; availability and any KYC are unknown. | Blocks §50 only. **Does not block the baseline or any other Wave 2 item.** | Spike S-12; if it fails, §50 stays DEFERRED. |

Today is 2026-10-24. The buildathon window closes **2026-11-20** (VERIFIED). That is the latest possible date, not necessarily the submission deadline (B-04). The plan is therefore ordered by dependency and shaped so that an end-to-end real call exists as early as possible; see Build Map milestone **M1**.

---

## 1. Project overview

Sonar is a voice-powered search engine for facts that exist only in the heads of people at real businesses: "Do you have this in stock right now?", "Can you take this job today?", "What would it cost?" A user submits a query and a location. Sonar selects a small, bounded set of **consenting** businesses, phones them with an automated voice agent that identifies itself truthfully, extracts structured answers, validates them deterministically, and shows a time-stamped, evidence-backed comparison of **what each business reported**.

Sonar reports; it does not guarantee. Every label is phrased as "reported by phone", never as objective truth.

## 2. Executive summary

- **Product thesis:** Sonar searches the real world by calling it.
- **MVP:** one locality, one category, a handful of consenting businesses, one query type. A dependable vertical slice: search → select businesses → call → extract → validate → display evidence.
- **Architecture (D-001, D-006):** React/TS frontend; FastAPI backend; PostgreSQL as both datastore and job queue; Bolna as voice-agent orchestration; one telephony route via Bolna; no Redis, Celery, Kafka, vector DB or second LLM provider.
- **Trust model:** results distinguish *reported available*, *reported unavailable*, *uncertain*, *declined*, *no answer*, *call failed*, *pending*, and *cached (older call)*. Silence is never "unavailable".
- **Honesty model:** every result carries a `data_origin` (`LIVE_CALL`, `CACHED_LIVE`, `SIMULATED`) and every business carries a `kind` (`REAL_BUSINESS` or `TEAM_TEST_LINE`). A role-played test line is labelled as such in the UI.
- **Biggest risks:** B-01 (no willing businesses), B-02/B-03 (account and number route), B-04 (unknown rules/deadline), webhook authenticity (Bolna documents no signature scheme).
- **Sponsor strategy (D-023…D-030):** one reliable Bolna-first production path that works with every optional provider disabled; the other voice-stack sponsors (Plivo, Exotel, Sarvam, Deepgram, Cartesia) each get a defined role, demonstrated through verified agent variants on test lines or controlled **Sponsor Lab** benchmarks on identical consented inputs — never by routing one real call through several providers. Nothing is called integrated without a test (§22.1). The whole annex is DEFERRED (P2) and never blocks the baseline.
- **Wave 2 (v2.0, Part II; D-031…D-043):** after M1, add the differentiators: call the fewest shops that suffice (stop rule + learned priors, §48), give shops a reason to consent (demand digest, §49) and a way to update stock by phone (inbound line, §50), make the call visible and audible in the room (§51–§52), and publish the numbers a sceptic would ask for (ground-truth agreement n/N, stop-rule saving, §54). Every Wave 2 feature is behind a flag; with all flags off the system is the v1.1 MVP (NFR-15).
- **Biggest design answer to that last risk (D-005):** never trust a webhook body. Treat it as a *doorbell*, then **pull** the authoritative execution record from Bolna with our API key before writing any result.

## 3. Problem statement

Search engines and directories say a business exists, where it is, and sometimes its hours. They cannot answer volatile, specific questions (stock, capacity today, price for this exact item, wait time). People call shops one by one, repeat themselves, and compare answers by hand. Sonar automates exactly that loop for a bounded set of consenting businesses and presents the comparison with evidence.

## 4. Target users and personas

| Persona | Situation | What Sonar must give them |
|---|---|---|
| **Asha, caregiver** (illustrative) | Needs a specific over-the-counter product tonight; ringing five shops is exhausting. | A short list of shops that *reported* having the exact item, with times. |
| **Ravi, laptop owner** (illustrative) | Needs a screen replaced today; websites list no prices or capacity. | Which shops reported they can take it today, with estimated cost. |
| **Meena, hobbyist/engineer** (illustrative) | Needs a specific component; local suppliers are unlisted online. | Which suppliers reported stock and price for the exact part number. |
| **Judge/viewer** (hackathon) | Has minutes. | One clear query, live progress, visible evidence, honest handling of failure. |

Personas are illustrative design aids, not research findings.

## 5. User pain points

1. Listings are stale or silent on stock, price and capacity.
2. Repeated calls with the same questions.
3. Ambiguity ("we have something similar") is lost when relayed informally.
4. No record of *when* someone was told something.
5. No way to compare responses side by side.

## 6. Product thesis

**Sonar searches the real world by calling it.** A text model can reason over known information; it cannot establish what a shopkeeper is saying *now*. The value is (a) reaching independent businesses, (b) conducting real conversations, (c) coordinating asynchronous calls, (d) comparing independent answers, (e) keeping the evidence.

### 6.1 Trust labels (normative)

| UI label | Meaning | Never used when |
|---|---|---|
| Reported available by phone | Business said the exact item/service is available; evidence quote validated | Business hedged, or alternative only |
| Reported unavailable by phone | Business explicitly said not available | Call unanswered/failed/declined |
| Uncertain | Business unsure, hedged, contradictory, or extraction failed validation | — |
| Alternative only | Business offered something other than the exact request | Exact match confirmed |
| Declined to answer | Business refused or asked not to be called | — |
| No answer | Call not picked up / busy | Never rendered as "unavailable" |
| Call failed | Telephony/provider/internal error | — |
| Pending | Call not yet finished | — |
| Earlier call (cached) | Fresh-enough answer from a previous live call, shown with its original time | Presented as "just confirmed" |
| Simulated | Produced by the simulator | Ever shown without the banner |
| Not called (enough answers) *(Wave 2)* | Stop rule satisfied before this shop was dialled | Ever worded as unavailable; always followed by "This does not mean it is unavailable." |
| Self-reported by the shop *(Wave 2)* | The shop told Sonar's inbound line (caller matched, validated, within TTL) | Presented as "confirmed by Sonar's call" |
| History *(Wave 2)* | Past answered-call record, shown beside (never instead of) a live answer, with n | Used to promote, replace or imply today's availability |

### 6.2 Product ladder and 6.3 business hypotheses
Defined in Part II: product ladder §46, business-model hypotheses §47. They are positioning and hypotheses, not MVP requirements.

## 7. Goals, non-goals, working principles

### 7.1 Goals
G1. A real, consenting-business call flows through the whole pipeline and appears with evidence in the UI.
G2. Answers are structured, validated, time-stamped, and honestly labelled.
G3. Calls are bounded (count, concurrency, duration, budget) and auditable.
G4. A demo that survives a failed call and provider outage (labelled simulation fallback).
G5. A reproducible repository with tests.

### 7.2 Non-goals (MVP)
Universal search; nationwide coverage; calling arbitrary numbers; unbounded campaigns; multiple telephony integrations; vector DB/RAG; purchasing/booking/commitments; medical advice or substitutions; payments; merchant inventory system; mobile app; recommendation algorithms; large analytics.

### 7.3 Working principles (referenced by the Build Map as **WP-1…WP-20**)
1. Ship a working vertical slice before expanding scope.
2. Voice and real-world information acquisition stay central.
3. Prefer reliable, simple architecture over infrastructure.
4. Verify external API contracts before implementation.
5. Treat transcripts and provider outputs as untrusted input.
6. Keep all secrets server-side.
7. Validate structured output before storing or displaying it.
8. Make every asynchronous state transition explicit.
9. Never fabricate availability or claim a call succeeded when it did not.
10. Clearly distinguish live and simulated data.
11. Make external calls bounded, consent-based, auditable.
12. Preserve useful evidence and timestamps.
13. Keep unresolved questions visible.
14. Write tests alongside implementation.
15. Use reproducible commands and acceptance criteria.
16. Document important decisions and why.
17. Optimise for a reliable live demo and measurable value.
18. No new dependency without clear benefit.
19. Cost, latency and failure handling are first-class.
20. Keep the pitch consistent with what the code demonstrates.

## 8. The MVP vertical

### 8.1 Decision (D-003): the vertical is chosen at Gate G0 by *who consents*, not by what demos best

**Why:** B-01 is a hard dependency. A pharmacy demo with zero consenting pharmacies is a simulation. Choosing the category first and hoping for consent inverts the dependency.

**Rule:**
1. Start outreach for **both** pharmacies and computer-repair/electronics shops immediately.
2. The vertical is the first category with **≥ 3 consenting, reachable businesses** (see §8.3).
3. If none reaches 3 in time, run the live demo with `TEAM_TEST_LINE` businesses (team members' phones playing shopkeepers), labelled as role-play, and say so in the pitch.
4. The code is category-agnostic: category, required fields and the prompt template are configuration (§23.4).

### 8.2 Category comparison

| | Pharmacy (non-prescription items only) | Computer repair / electronics |
|---|---|---|
| Demo clarity | High | High |
| Regulatory/optics risk | Higher: health context, substitution temptation | Lower |
| Volatility of answer (good for freshness story) | High (stock) | Medium (capacity, quote) |
| Clinical-advice risk | Must be hard-blocked | None |
| Likelihood shopkeeper is happy to answer an unknown automated caller | Unknown | Unknown |

**Pharmacy guardrails if chosen:** only non-prescription, named products; refuse prescription-only/controlled items and any dosing or substitution question; the agent never recommends alternatives, never advises; UI repeats "Sonar reports what the business said. It does not give medical advice."

### 8.3 Minimum viable pilot set
≥ 3 businesses of the chosen category, each with: recorded consent (date, how obtained, by whom), a verified phone number, a named contact if possible, a known best time to call, and an opt-out route. Plus ≥ 2 `TEAM_TEST_LINE` numbers for development and for scripted failure/ambiguity scenarios.

## 9. User stories

| ID | Story |
|---|---|
| US-1 | As a user I enter what I need and where, and get a job I can watch. |
| US-2 | As a user I see which businesses will be contacted before calls start. |
| US-3 | As a user I see each call progress through meaningful states. |
| US-4 | As a user I see answers appear as calls finish, not only at the end. |
| US-5 | As a user I see what each business said, when, and the transcript excerpt behind it. |
| US-6 | As a user I can tell *unavailable* from *no answer* from *unsure*. |
| US-7 | As a user I can cancel a search that has not finished. |
| US-8 | As a user I am never shown simulated data as live. |
| US-9 | As a business owner I can say "stop calling me" and it sticks. |
| US-10 | As the team I can run a labelled simulation when telephony fails. |
| US-11 | As the team I can see cost and outcome per call. |
| US-12 | As a user, an earlier answer is reused only if still fresh, and is labelled with its original time. |
| US-13 | *(Wave 2)* As a user, I get a good answer from the fewest calls, and I can choose "ask everyone". |
| US-14 | *(Wave 2)* As a shopkeeper, I see what nearby people are looking for, so saying yes helps me. |
| US-15 | *(Wave 2)* As a shopkeeper, I can phone Sonar and say what I have in stock. |
| US-16 | *(Wave 2)* As a viewer, I can watch (or, for consenting lines, hear) a call as it happens. |
| US-17 | *(Wave 2)* As a user, I can speak my question and hear a summary read back. |
| US-18 | *(Wave 2, P2)* As a user, I can ask to be told when a shop reports an item in stock. |

## 10. Functional requirements

Priority: P0 = indispensable for end-to-end MVP, P1 = strengthens demo, P2 = future.

| ID | Pri | Requirement |
|---|---|---|
| FR-01 | P0 | Accept a search (query text, structured item/service fields, location, radius) via `POST /api/searches`; return a job id immediately without waiting for calls. |
| FR-02 | P0 | Validate input: required fields, radius range, location bounds, query length, category supported. Return typed errors. |
| FR-03 | P0 | If an essential field is missing or ambiguous, respond `NEEDS_CLARIFICATION` with the specific questions; do not guess. |
| FR-04 | P0 | Refuse unsupported or high-risk queries (prescription-only/controlled, dosing, clinical advice, legal advice) with a clear reason. |
| FR-05 | P0 | Select targets from the curated directory by category, distance and eligibility, capped at `MAX_TARGETS_PER_SEARCH`. |
| FR-06 | P0 | Only businesses with `participation_status ∈ {CONSENTED, TEST_LINE}` and not opted out are ever eligible. Enforced in the selector **and** again in the dispatcher. |
| FR-07 | P0 | Show the planned target list to the user and in the job record before/at call start. |
| FR-08 | P0 | Create one `CallAttempt` per (search, business) with a unique constraint to prevent duplicates. |
| FR-09 | P0 | Dispatch calls through the `VoiceProvider` interface with a concurrency cap and per-call, per-business and global budgets. |
| FR-10 | P0 | Persist the provider call id (`execution_id` for Bolna) immediately after dispatch. |
| FR-11 | P0 | Receive provider status events at a webhook endpoint; authenticate (§30); persist raw event; respond fast. |
| FR-12 | P0 | Treat webhook bodies as untrusted: on a terminal/finalising event, pull the authoritative execution record from the provider before writing any result. |
| FR-13 | P0 | Process events idempotently; ignore duplicates; tolerate out-of-order events (monotonic status ranks). |
| FR-14 | P0 | Reconcile non-terminal attempts by polling the provider after a timeout and on process start (covers lost webhooks and restarts). |
| FR-15 | P0 | Normalise provider output into a typed `BusinessResponse` through the deterministic validator (§23.3). |
| FR-16 | P0 | Never mark a business unavailable unless it explicitly said so with validated evidence. |
| FR-17 | P0 | Preserve unknown fields as unknown (null), never inferred. Prices keep currency. |
| FR-18 | P0 | Store a bounded transcript evidence excerpt per response; do not store audio or fetch recordings by default. |
| FR-19 | P0 | Each response carries `answer_timestamp`, `data_origin`, per-field freshness. |
| FR-20 | P0 | `GET /api/searches/{id}` and `/results` return progress and partial results while the job runs. |
| FR-21 | P0 | Retry only for `NO_ANSWER`/`BUSY` (and optionally transient provider failures) within `MAX_ATTEMPTS_PER_BUSINESS` with backoff; never retry after a business answered, declined or opted out. |
| FR-22 | P0 | Enforce `SEARCH_DEADLINE_SECONDS`; unfinished calls become `TIMED_OUT` and the search completes as `COMPLETED_PARTIAL`. |
| FR-23 | P0 | `POST /api/searches/{id}/cancel`: stop dispatching new calls, mark pending attempts `CANCELLED`, let in-flight calls finish and be recorded. |
| FR-24 | P0 | If a business asks not to be called (agent-detected or recorded), set `OPTED_OUT` and exclude it from all future searches. |
| FR-25 | P0 | Simulated provider (`SimulatedVoiceProvider`) with scripted scenarios; results flagged `SIMULATED`; UI banner mandatory. |
| FR-26 | P0 | Frontend: search form, planned targets, live progress, results list with evidence, error/empty/cancel states, "new search". |
| FR-27 | P0 | `GET /health` (liveness) and `GET /health/ready` (DB reachable). |
| FR-28 | P0 | Structured logs with correlation ids; phone numbers masked. |
| FR-29 | P0 | Rate limiting and an access key on search creation; no provider secret ever reaches the browser. |
| FR-30 | P1 | Fresh cached answers reused when they exactly match and are within TTL; labelled "earlier call". `force_fresh` flag bypasses. |
| FR-31 | P1 | Ranking explanation text rendered in the UI ("why this order"). |
| FR-32 | P1 | Metrics endpoint/CLI report for §39 definitions. |
| FR-33 | P1 | Provider cost recorded per call from the execution record. |
| FR-34 | P1 | Human review flag (`HUMAN_REVIEWED`) settable via a CLI/admin script to measure extraction accuracy. |
| FR-35 | P1 | SSE for live updates (polling is the P0 mechanism). |
| FR-36 | P2 | Map view *(superseded for the MVP by the SVG radar, FR-50, D-038)*; LLM-based query parser *(see FR-55)*; multi-category directory; follow-up call on user request. |
| FR-37 | P1 | **Stop rule.** In `FAST` mode, stop dispatching once `K` distinct exact, validated, fresh `REPORTED_AVAILABLE` answers exist; cancel remaining `PENDING` attempts with reason `STOP_RULE_SATISFIED`; negatives never stop a search (§48.2). |
| FR-38 | P1 | **Prior scoring and ordering.** Pure `PriorScorer` orders dispatch from `business_stats`, with cold-start handling and an exploration rate (§48.3, §48.5). |
| FR-39 | P1 | **History display.** Past-record line labelled `HISTORY`, only when enough answered calls exist, never replacing or implying a live answer (§48.5). |
| FR-40 | P1 | **Not-called state.** `NOT_CALLED_STOP_RULE` result state with mandatory non-misleading copy (§48.4). |
| FR-41 | P1 | **Demand digest.** k-anonymous, live-traffic-only weekly digest per consenting shop via a capability page, with opt-out (§49). |
| FR-42 | P1 | **Consent script v2** leads with the digest and records `digest_opt_in` separately from call consent (§49.1). |
| FR-43 | P1 | **Inbound shop line.** Inbound agent plus authenticated, verify-by-pull webhook writing `shop_updates` (§50). Conditional on S-12. |
| FR-44 | P1 | **Self-report validation.** Evidence and numeric checks as §23.3; caller match is soft; unmatched callers quarantined; per-day cap; shorter TTL (§50.1). |
| FR-45 | P1 | **Result merge.** Results show `source`; self-reports labelled and ranked after equally fresh live calls; contradictions shown, not resolved (§50.1). |
| FR-46 | P1 | **Live transcript ticker** for in-call attempts, flagged businesses and test lines only (§51). Conditional on S-13. |
| FR-47 | P2 | **Audio replay** for `TEAM_TEST_LINE` and `demo_audio_consent` businesses; never stored (§51). Conditional on S-13. |
| FR-48 | P1 | **Voice input.** Client-side speech recognition fills the form; user confirms; never auto-submits (§52.1). |
| FR-49 | P1 | **Voice output.** Browser speech reads only the templated summary and ranking explanation (§52.1). |
| FR-50 | P1 | **Radar view.** SVG radial view of the search with status shown by text, no map tiles (§52.2). |
| FR-51 | P1 | **Race clock** with a comparison shown only when a measured manual baseline exists (§52.3). |
| FR-52 | P1 | **Evidence replay.** Bounded context window with the validated quote highlighted (§51). |
| FR-53 | P1 | **Trust ledger** panel listing every claim Sonar declined to make and why (§52.4). |
| FR-54 | P1 | **Ground-truth checks.** CLI to record independent verification; metrics report agreement as n/N (§54.1). |
| FR-55 | P2 | **Question compiler.** Free text to a `ParsedQuery` candidate through the same validators; one LLM call; user confirms (§53.1). |
| FR-56 | P2 | **Standing watches** with floor cadence, poll cap and expiry; share the per-business daily cap (§53.2). |
| FR-57 | P2 | **`POST /api/v1/ask`** thin wrapper over search with identical guardrails (§53.3). |

## 11. Non-functional requirements

| ID | Requirement | Target / measure | Status |
|---|---|---|---|
| NFR-01 | `POST /api/searches` latency (excluding dispatch) | p95 < 500 ms locally | target, measure in Phase 9 |
| NFR-02 | Webhook handler response time | p95 < 300 ms (persist then return) | target |
| NFR-03 | UI reflects a status change | ≤ 3 s via 2 s polling | target |
| NFR-04 | No duplicate result rows on duplicate delivery | 0 duplicates over a test of N≥50 repeated deliveries | test |
| NFR-05 | Restart safety | After kill -9 mid-search, no call is dispatched twice; non-terminal attempts reconcile | test |
| NFR-06 | Call bounds | Never exceed `MAX_CONCURRENT_CALLS`, per-search target cap, daily budget | test |
| NFR-07 | Secrets | Zero provider secrets in frontend bundle, logs, or API responses | automated scan |
| NFR-08 | Evidence | 100 % of displayed positive/negative answers have a validated evidence excerpt | test |
| NFR-09 | Misleading labels | 0 occurrences of "unavailable" for no-answer/failed/declined states | test over all state fixtures |
| NFR-10 | Reproducibility | Fresh clone → running local stack with documented commands | checklist |
| NFR-11 | Test coverage | Pure logic modules (validator, freshness, ranking, transitions, retry) ≥ 90 % line coverage | measured |
| NFR-12 | Accessibility basics | Status not conveyed by colour alone; keyboard-operable | checklist |
| NFR-13 | Data minimisation | No audio retained; transcripts excerpt-limited; retention job enforced | test |
| NFR-14 | Observability | Every state transition logged with job/attempt ids | test |
| NFR-15 | Wave 2 isolation | With every `FEATURE_*` flag off, the Part I suite (AC-1…AC-10) passes unchanged and no Wave 2 table is read or written on the request path | test |
| NFR-16 | Digest privacy | No user identifiers, no demo/simulated traffic, counts suppressed below `DIGEST_MIN_K` | test |
| NFR-17 | Inbound abuse bounds | Unmatched callers never displayed; accepted updates ≤ `SHOP_UPDATE_MAX_PER_DAY`; opted-out businesses rejected | test |
| NFR-18 | Spoken = displayed | The string passed to speech synthesis equals the rendered templated text for every `ResultState` fixture | test |
| NFR-19 | Ticker freshness | When the provider supplies a partial transcript, the ticker reflects it within 5 s on 2 s polling; absent data shows "no live text yet", never invented text | test |

Latency targets are engineering targets, not claims about the live system. End-to-end search time depends on telephony and humans; we measure it, we do not promise it (§39).

## 12. Acceptance criteria (MVP)

The MVP is accepted when **all** hold:

- AC-1: With the simulator, the full E2E scenario matrix (§33.3) passes in CI.
- AC-2: With the live provider, at least one search against consenting/test-line numbers produces ≥ 1 `REPORTED_AVAILABLE` or `REPORTED_UNAVAILABLE` result with a validated evidence excerpt and timestamp (**milestone M1**).
- AC-3: A deliberately unanswered call renders as "No answer", never as unavailable.
- AC-4: A duplicate webhook delivery changes nothing.
- AC-5: Killing and restarting the backend mid-search results in correct final state and no double dials.
- AC-6: The simulation banner appears on every simulated result and cannot be hidden.
- AC-7: No secret in the built frontend (automated scan passes).
- AC-8: The demo script (§37) runs from a clean browser session at least 3 times.
- AC-9: README reproduces the setup from a clean clone.
- AC-10: Every pitch claim maps to a demonstrated behaviour (§37.4 checklist).
- AC-11…AC-16: Wave 2 criteria, defined in §55. They apply only to Wave 2 features that are enabled for the demo.

## 13. Core user journeys

**J1 happy path.** Enter query + location → (optional clarification) → see planned targets → start → watch calls ring/answer → first result appears → expand evidence → all complete → "new search".
**J2 partial.** One business never answers; one fails; two respond → job ends `COMPLETED_PARTIAL`, UI explains each state.
**J3 clarification.** "pain relief tablets" with no strength → Sonar asks for the missing attribute.
**J4 refusal.** Prescription-only query → clear refusal, no job.
**J5 cancel.** User cancels → pending attempts cancelled, in-flight recorded.
**J6 fallback.** Provider down → operator enables demo mode → entire flow with a permanent "SIMULATED" banner.
**J7 opt-out.** Business says "don't call again" → recorded, excluded forever.

## 14. Architecture overview

Single FastAPI service (API + in-process orchestrator + webhook receiver + reconciler) in front of PostgreSQL. Provider access sits behind a `VoiceProvider` protocol with two implementations: `BolnaVoiceProvider` and `SimulatedVoiceProvider`.

**D-006 — Postgres is the queue.** `call_attempts` rows are the work items. The orchestrator claims work with `SELECT … FOR UPDATE SKIP LOCKED` inside one process (single uvicorn worker for MVP). This avoids Redis/Celery, survives restarts (state is in the DB), and scales to multiple workers later without redesign. Trade-off: polling the DB, and a single process holding the concurrency semaphore (fine at ≤ 2–10 concurrent calls; Bolna's trial cap is 2 concurrent outbound calls, VERIFIED).

**D-007 — Polling for the UI.** 2 s polling of `GET /api/searches/{id}` + `/results`. SSE is P1 (FR-35) because polling is stateless, proxy-friendly and trivially testable.

## 15. Component responsibilities

| Component | Responsibility | Input | Output | Failure modes | Depends on | Tests |
|---|---|---|---|---|---|---|
| **API layer** (`app/api`) | HTTP, auth key, rate limit, error envelope | HTTP | JSON | 4xx validation, 429, 500 | services | contract tests |
| **QueryService** | Validate + parse to `ParsedQuery`; clarification/refusal | `SearchRequest` | `ParsedQuery` \| `Clarification` \| `Refusal` | ambiguous input | rules/config | unit |
| **DirectoryService** | Serve curated businesses; eligibility; geo filter | category, point, radius | `list[Business]` | empty set | DB, seed file | unit/integration |
| **Selector** | Apply eligibility, caps, cooldowns, cache reuse | candidates, policy | `list[Target]` | none eligible → `NO_ELIGIBLE_BUSINESSES` | Directory, ResultCache | unit |
| **Orchestrator** | Create attempts, enforce concurrency/deadline/budget, retries, cancel | job | attempt state changes | crash mid-dispatch, provider outage | DB, VoiceProvider | integration |
| **VoiceProvider** (protocol) | `start_call`, `get_call` | `CallRequest` | `ProviderCallRef` / `ProviderCallRecord` | HTTP errors, timeouts | httpx | mock tests |
| **BolnaVoiceProvider** | Bolna HTTP specifics | — | — | 400 errors, 5xx, rate limits | Bolna API | mock + live |
| **SimulatedVoiceProvider** | Scripted scenarios | scenario id | synthetic `ProviderCallRecord` with `SIMULATED` | — | none | unit |
| **WebhookHandler** | Authenticate, persist raw event, enqueue finalize | POST body | 200 | bad auth, malformed | DB | integration |
| **EventProcessor** | Map status, enforce monotonic transitions, dedupe | event | attempt update | unknown status | DB | unit |
| **Finalizer** | Pull authoritative record, validate, persist response, update job | attempt | `BusinessResponse` | pull fails → retry; invalid → UNCERTAIN | provider, Validator | integration |
| **AnswerValidator** | Deterministic rules (§23.3) | provider record, `ParsedQuery`, transcript | `ValidatedAnswer` | any rule failure → UNCERTAIN/INVALID | none (pure) | unit (many fixtures) |
| **FreshnessService** | Per-field expiry, cache eligibility | response, now | `Freshness` | clock skew | none (pure) | unit |
| **RankingService** | Deterministic ordering + explanation | responses | ordered list | — | none (pure) | unit |
| **Reconciler** | Poll stale non-terminal attempts; match orphan events | timer/startup | state repairs | provider down | provider, DB | integration |
| **RetentionJob** | Purge transcripts/events past retention | timer | deletions | — | DB | integration |
| **Frontend** | Form, progress, results, evidence, labels | API | UI | network errors | API | component + E2E |

## 16. Architecture diagram

```mermaid
flowchart LR
  subgraph Browser
    UI["React + TS UI"]
  end
  subgraph Backend["FastAPI service (single process, MVP)"]
    API["API layer<br/>auth key · rate limit"]
    QS["QueryService"]
    DIR["DirectoryService + Selector"]
    ORCH["Orchestrator<br/>concurrency · deadline · retries"]
    VP{{"VoiceProvider interface"}}
    BOLNA["BolnaVoiceProvider"]
    SIM["SimulatedVoiceProvider"]
    WH["Webhook handler"]
    FIN["Finalizer<br/>pull · validate · persist"]
    VAL["AnswerValidator"]
    REC["Reconciler"]
  end
  DB[("PostgreSQL<br/>jobs · attempts · responses · events")]
  EXT["Bolna API<br/>POST /call · GET /executions/id"]
  PH(("Business phone"))

  UI -- "HTTPS JSON (poll)" --> API
  API --> QS --> DIR --> DB
  API --> ORCH
  ORCH <--> DB
  ORCH --> VP
  VP --> BOLNA --> EXT
  VP --> SIM
  EXT -. "voice call" .-> PH
  EXT -- "status webhooks (POST)" --> WH
  WH --> DB
  WH --> FIN
  FIN -- "authoritative pull" --> EXT
  FIN --> VAL
  FIN --> DB
  REC --> EXT
  REC --> DB
```

## 17. Data-flow diagram

```mermaid
flowchart TD
  A["SearchRequest<br/>query, location, radius"] --> B{"Validate and parse"}
  B -- "missing essential field" --> C["NEEDS_CLARIFICATION"]
  B -- "unsupported / high-risk" --> D["Refusal"]
  B -- ok --> E["ParsedQuery"]
  E --> F["Directory: eligible, in radius"]
  F --> G["Selector: caps, cooldown, cache reuse"]
  G -- "fresh exact cache hit" --> H["Result: CACHED_LIVE"]
  G -- "needs call" --> I["CallAttempt rows (DB queue)"]
  I --> J["Dispatch via VoiceProvider"]
  J --> K["provider_call_id stored"]
  K --> L["Webhook doorbell / reconciler poll"]
  L --> M["Pull authoritative execution record"]
  M --> N["Raw record: transcript, extracted_data, cost"]
  N --> O{"AnswerValidator"}
  O -- "rules pass" --> P["BusinessResponse VALID"]
  O -- "rules fail / hedged" --> Q["BusinessResponse UNCERTAIN"]
  P --> R["Freshness + ranking"]
  Q --> R
  H --> R
  R --> S["GET /results → UI"]
```

## 18. Sequence diagram — one search, one call

```mermaid
sequenceDiagram
  autonumber
  participant U as User/UI
  participant API as Sonar API
  participant DB as PostgreSQL
  participant OR as Orchestrator
  participant B as Bolna
  participant S as Shop phone

  U->>API: POST /api/searches
  API->>DB: insert SearchJob(CREATED), targets
  API-->>U: 202 {search_id}
  loop every 2s
    U->>API: GET /api/searches/{id}
    API-->>U: status + attempts + partial results
  end
  OR->>DB: claim attempt (SKIP LOCKED), state=DISPATCHING
  OR->>B: POST /call {agent_id, recipient_phone_number, user_data}
  B-->>OR: 200 {status: queued, execution_id}
  OR->>DB: store execution_id, state=DIALING
  B->>S: dial
  B-->>API: POST /api/webhooks/bolna/{token} (initiated/ringing/in-progress)
  API->>DB: persist raw event, advance status (monotonic)
  S-->>B: shop answers, conversation
  B-->>API: webhook (call-disconnected), then (completed)
  API->>DB: persist event; mark attempt PROCESSING/finalising
  API->>B: GET /executions/{execution_id} (authoritative pull)
  B-->>API: transcript, extracted_data, cost, status
  API->>API: AnswerValidator (deterministic)
  API->>DB: upsert BusinessResponse (unique per attempt), update job counters
  Note over OR,DB: Reconciler polls any attempt with no terminal event after timeout
  U->>API: GET results
  API-->>U: ranked results with evidence and timestamps
```

## 19. Database schema

PostgreSQL 15+, SQLAlchemy 2.x, Alembic migrations (D-008). UUID primary keys (`gen_random_uuid()`), `timestamptz` everywhere, UTC.

### 19.1 Entities and relationships

```mermaid
erDiagram
  BUSINESS ||--o{ CALL_ATTEMPT : "is called in"
  SEARCH_JOB ||--o{ CALL_ATTEMPT : "has"
  CALL_ATTEMPT ||--o| BUSINESS_RESPONSE : "yields at most one"
  CALL_ATTEMPT ||--o{ PROVIDER_EVENT : "receives"
  SEARCH_JOB ||--o{ AUDIT_EVENT : "logs"
  BUSINESS ||--o{ AUDIT_EVENT : "logs"
  BUSINESS ||--o{ BUSINESS_RESPONSE : "reported by"
```

### 19.2 DDL (authoritative shape; refine in migrations)

```sql
-- enums created as PostgreSQL enums or CHECK-constrained text (D-008: use text + CHECK for easy migration)

CREATE TABLE businesses (
  id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name                text NOT NULL,
  phone_e164          text NOT NULL UNIQUE CHECK (phone_e164 ~ '^\+[1-9][0-9]{7,14}$'),
  address             text,
  latitude            double precision CHECK (latitude BETWEEN -90 AND 90),
  longitude           double precision CHECK (longitude BETWEEN -180 AND 180),
  category            text NOT NULL,
  kind                text NOT NULL CHECK (kind IN ('REAL_BUSINESS','TEAM_TEST_LINE')),
  source              text NOT NULL,                 -- 'curated_seed' for MVP
  participation_status text NOT NULL CHECK (participation_status IN
                      ('INVITED','CONSENTED','TEST_LINE','DECLINED','OPTED_OUT')),
  consent_recorded_at timestamptz,
  consent_note        text,                          -- how/when/who; no sensitive content
  opted_out_at        timestamptz,
  best_call_window    text,                          -- free text, e.g. '10:00-13:00 IST'
  created_at          timestamptz NOT NULL DEFAULT now(),
  updated_at          timestamptz NOT NULL DEFAULT now(),
  CHECK (participation_status NOT IN ('CONSENTED','TEST_LINE') OR consent_recorded_at IS NOT NULL)
);

CREATE TABLE search_jobs (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  query_text      text NOT NULL CHECK (char_length(query_text) <= 500),
  parsed_query    jsonb,                              -- ParsedQuery
  category        text,
  center_lat      double precision,
  center_lng      double precision,
  radius_km       numeric(5,2) CHECK (radius_km > 0 AND radius_km <= 25),
  status          text NOT NULL CHECK (status IN
                  ('CREATED','NEEDS_CLARIFICATION','RUNNING','COMPLETED','COMPLETED_PARTIAL',
                   'FAILED','CANCELLED')),
  demo_mode       boolean NOT NULL DEFAULT false,
  force_fresh     boolean NOT NULL DEFAULT false,
  planned_targets int NOT NULL DEFAULT 0,
  clarification   jsonb,
  error_code      text,
  error_summary   text,
  created_at      timestamptz NOT NULL DEFAULT now(),
  started_at      timestamptz,
  completed_at    timestamptz,
  deadline_at     timestamptz
);

CREATE TABLE call_attempts (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  search_job_id    uuid NOT NULL REFERENCES search_jobs(id) ON DELETE CASCADE,
  business_id      uuid NOT NULL REFERENCES businesses(id),
  attempt_number   int  NOT NULL CHECK (attempt_number BETWEEN 1 AND 5),
  provider         text NOT NULL CHECK (provider IN ('bolna','simulated')),
  provider_call_id text,                              -- Bolna execution_id
  status           text NOT NULL CHECK (status IN
                   ('PENDING','DISPATCHING','DISPATCH_UNKNOWN','DIALING','RINGING','IN_PROGRESS',
                    'PROCESSING','COMPLETED','NO_ANSWER','BUSY','FAILED','ERROR','CANCELLED',
                    'STOPPED','INSUFFICIENT_BALANCE','TIMED_OUT')),
  provider_status  text,                              -- last raw provider status, for debugging
  not_before       timestamptz NOT NULL DEFAULT now(),-- backoff scheduling
  started_at       timestamptz,
  answered_at      timestamptz,
  completed_at     timestamptz,
  duration_seconds int,
  cost_amount      numeric(10,4),
  cost_currency    text,
  failure_reason   text,
  error_class      text,
  retry_eligible   boolean NOT NULL DEFAULT false,
  created_at       timestamptz NOT NULL DEFAULT now(),
  updated_at       timestamptz NOT NULL DEFAULT now(),
  UNIQUE (search_job_id, business_id, attempt_number),
  UNIQUE (provider, provider_call_id)
);
CREATE INDEX ON call_attempts (status, not_before);

CREATE TABLE provider_events (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  call_attempt_id  uuid REFERENCES call_attempts(id) ON DELETE SET NULL,  -- null = orphan
  provider         text NOT NULL,
  provider_call_id text,
  provider_status  text,
  payload_sha256   text NOT NULL,
  payload          jsonb NOT NULL,                    -- size-limited, PII-redacted at write
  received_at      timestamptz NOT NULL DEFAULT now(),
  processed_at     timestamptz,
  UNIQUE (provider, provider_call_id, provider_status, payload_sha256)
);

CREATE TABLE business_responses (
  id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  call_attempt_id    uuid NOT NULL UNIQUE REFERENCES call_attempts(id) ON DELETE CASCADE, -- idempotency
  search_job_id      uuid NOT NULL REFERENCES search_jobs(id) ON DELETE CASCADE,
  business_id        uuid NOT NULL REFERENCES businesses(id),
  data_origin        text NOT NULL CHECK (data_origin IN ('LIVE_CALL','SIMULATED')),
  availability       text NOT NULL CHECK (availability IN
                     ('REPORTED_AVAILABLE','REPORTED_UNAVAILABLE','ALTERNATIVE_ONLY',
                      'UNCERTAIN','DECLINED')),
  exact_match        text NOT NULL CHECK (exact_match IN ('CONFIRMED','NOT_CONFIRMED','UNKNOWN')),
  matched_attributes jsonb NOT NULL DEFAULT '{}',     -- {attr: 'CONFIRMED'|'DIFFERENT'|'UNKNOWN'}
  alternative_note   text,                            -- what the business offered, verbatim-ish; never auto-accepted
  price_amount       numeric(12,2),
  price_currency     text,
  price_note         text,
  quantity_reported  int,
  wait_time_minutes  int,
  open_status        text CHECK (open_status IN ('OPEN','CLOSED','UNKNOWN')),
  answer_summary     text NOT NULL,                   -- templated from validated fields, not free LLM prose
  evidence_excerpt   text,                            -- bounded (<= 600 chars)
  evidence_validated boolean NOT NULL DEFAULT false,  -- excerpt found in transcript
  provider_extracted jsonb,                           -- raw provider extraction (debug; untrusted)
  provider_confidence numeric(4,3),                   -- raw vendor number; NOT shown as a probability
  extraction_status  text NOT NULL CHECK (extraction_status IN
                     ('VALID','PARTIAL','INVALID','MISSING')),
  validation_flags   text[] NOT NULL DEFAULT '{}',    -- which rules fired
  verification_status text NOT NULL DEFAULT 'REPORTED_BY_PHONE' CHECK (verification_status IN
                     ('REPORTED_BY_PHONE','HUMAN_REVIEWED','CONTRADICTED')),
  answer_timestamp   timestamptz NOT NULL,
  availability_expires_at timestamptz,
  price_expires_at   timestamptz,
  created_at         timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ON business_responses (business_id, answer_timestamp DESC);

CREATE TABLE audit_events (
  id         bigserial PRIMARY KEY,
  at         timestamptz NOT NULL DEFAULT now(),
  actor      text NOT NULL,         -- 'system','api','webhook','cli:<name>'
  action     text NOT NULL,         -- 'call_dispatched','opt_out_recorded','search_cancelled',...
  search_job_id uuid,
  business_id   uuid,
  detail     jsonb NOT NULL DEFAULT '{}'
);
```

Notes:
- `business_responses.call_attempt_id UNIQUE` is the idempotency anchor for results.
- A "no answer / failed" attempt has **no** `business_responses` row; the UI derives its state from `call_attempts.status`. This makes "unavailable" impossible to produce from silence.
- Cached results are not copied: a cached hit is a reference to an older `business_responses` row, rendered with its original timestamp and `CACHED_LIVE` origin at read time.
- Phone numbers are PII: the seed file with real numbers is git-ignored (§35); logs mask all but the last 3 digits.

### 19.3 Enumerations (canonical names; identical in code, DB, API, UI)

| Enum | Values |
|---|---|
| `SearchStatus` | `CREATED`, `NEEDS_CLARIFICATION`, `RUNNING`, `COMPLETED`, `COMPLETED_PARTIAL`, `FAILED`, `CANCELLED` |
| `CallStatus` | `PENDING`, `DISPATCHING`, `DISPATCH_UNKNOWN`, `DIALING`, `RINGING`, `IN_PROGRESS`, `PROCESSING`, `COMPLETED`, `NO_ANSWER`, `BUSY`, `FAILED`, `ERROR`, `CANCELLED`, `STOPPED`, `INSUFFICIENT_BALANCE`, `TIMED_OUT` |
| `ParticipationStatus` | `INVITED`, `CONSENTED`, `TEST_LINE`, `DECLINED`, `OPTED_OUT` |
| `BusinessKind` | `REAL_BUSINESS`, `TEAM_TEST_LINE` |
| `Availability` | `REPORTED_AVAILABLE`, `REPORTED_UNAVAILABLE`, `ALTERNATIVE_ONLY`, `UNCERTAIN`, `DECLINED` |
| `ExactMatch` | `CONFIRMED`, `NOT_CONFIRMED`, `UNKNOWN` |
| `ExtractionStatus` | `VALID`, `PARTIAL`, `INVALID`, `MISSING` |
| `VerificationStatus` | `REPORTED_BY_PHONE`, `HUMAN_REVIEWED`, `CONTRADICTED` |
| `Freshness` | `FRESH`, `STALE`, `UNKNOWN` |
| `DataOrigin` | `LIVE_CALL`, `CACHED_LIVE`, `SIMULATED` |
| `ResultState` (UI-derived) | `REPORTED_AVAILABLE`, `REPORTED_UNAVAILABLE`, `ALTERNATIVE_ONLY`, `UNCERTAIN`, `DECLINED`, `NO_ANSWER`, `CALL_FAILED`, `PENDING`, `CANCELLED` |
| `ErrorClass` | `VALIDATION`, `NO_ELIGIBLE_BUSINESSES`, `UNSUPPORTED_QUERY`, `PROVIDER_REJECTED`, `PROVIDER_UNAVAILABLE`, `PROVIDER_TIMEOUT`, `INSUFFICIENT_BALANCE`, `TELEPHONY_FAILED`, `BUDGET_EXCEEDED`, `WEBHOOK_UNAUTHENTICATED`, `WEBHOOK_MALFORMED`, `EXTRACTION_INVALID`, `INTERNAL` |

**Provider-status mapping** (Bolna status list VERIFIED 2026-10-24 from the call-flow page; the page says the full enum lives on an "Errors & Status Codes" page we did not read, so an unknown value must map to `ERROR`-safe handling: log + store `provider_status` + leave attempt non-terminal for the reconciler):

| Bolna `status` | Sonar `CallStatus` | Terminal? | Note |
|---|---|---|---|
| `queued` | `DIALING` | no | accepted by provider |
| `initiated` | `DIALING` | no | dialing |
| `ringing` | `RINGING` | no | |
| `in-progress` | `IN_PROGRESS` | no | answered |
| `call-disconnected` | `PROCESSING` | no | **fields still null/0 here** (VERIFIED); wait for `completed` |
| `completed` | `COMPLETED` | yes | finalise: pull + validate |
| `no-answer` | `NO_ANSWER` | yes | retry-eligible |
| `busy` | `BUSY` | yes | retry-eligible |
| `failed` | `FAILED` | yes | telephony error; retry-eligible once |
| `canceled` | `CANCELLED` | yes | |
| `stopped` | `STOPPED` | yes | |
| `error` | `ERROR` | yes | internal provider error |
| `balance-low` | `INSUFFICIENT_BALANCE` | yes | stop dispatching, alert operator |
| *(ours)* | `TIMED_OUT` | yes | we stopped waiting |

Monotonic rank: `PENDING 0 < DISPATCHING 1 < DIALING 2 < RINGING 3 < IN_PROGRESS 4 < PROCESSING 5 < {terminal} 6`. An event with a rank lower than the current one is stored but ignored. A terminal status is never overwritten (exception: `PROCESSING → COMPLETED` is the normal path).

## 20. Internal API contracts

Base path `/api`. JSON. UTC ISO-8601 timestamps. These are **Sonar** endpoints (not provider endpoints). **DECISION D-009:** MVP has no end-user accounts. `POST /api/searches` and `POST /cancel` require header `X-Sonar-Key: <shared demo key>`; read endpoints are protected by the unguessable job UUID (capability URL) plus rate limiting. Documented as a limitation.

### 20.1 Error envelope (all non-2xx)
```json
{ "error": { "code": "VALIDATION", "message": "radius_km must be between 0.5 and 25", "field": "radius_km", "request_id": "01J..." } }
```
`code` ∈ `ErrorClass` plus `RATE_LIMITED`, `UNAUTHORIZED`, `NOT_FOUND`.

### 20.2 `POST /api/searches`
Request (`SearchRequest`):
```json
{
  "query_text": "Does anyone nearby have <item> in stock?",
  "category": "pharmacy",
  "item": { "name": "<product>", "attributes": { "strength": "500 mg", "pack": "strip of 10" } },
  "location": { "lat": 12.9716, "lng": 77.5946, "label": "Demo locality" },
  "radius_km": 3,
  "required_fields": ["availability", "price"],
  "force_fresh": false,
  "demo_mode": false
}
```
Responses:
- `202` `{ "search_id": "uuid", "status": "CREATED" | "RUNNING", "planned_targets": [ {business_id, name, kind, distance_km} ] }`
- `200` `{ "search_id": "uuid", "status": "NEEDS_CLARIFICATION", "clarification": { "questions": [ {field, question} ] } }`
- `422` refusal/validation (`UNSUPPORTED_QUERY`, `VALIDATION`), `429` rate limited, `401` missing/invalid access key. Searches are never de-duplicated: the same request twice creates two jobs.
- If no eligible businesses: `200` with `status: FAILED`, `error_code: NO_ELIGIBLE_BUSINESSES` and a helpful message.

`demo_mode: true` selects the `SimulatedVoiceProvider` and sets `search_jobs.demo_mode = true`; every response/result is flagged simulated.

### 20.3 `GET /api/searches/{search_id}`
```json
{
  "search_id": "uuid",
  "status": "RUNNING",
  "demo_mode": false,
  "created_at": "...", "started_at": "...", "completed_at": null, "deadline_at": "...",
  "counts": { "planned": 4, "pending": 1, "in_call": 1, "answered": 1, "no_answer": 0, "failed": 0, "cancelled": 0 },
  "attempts": [
    { "attempt_id": "uuid", "business": {"id":"uuid","name":"...","kind":"REAL_BUSINESS","distance_km":1.2},
      "status": "RINGING", "attempt_number": 1, "updated_at": "...", "result_state": "PENDING" }
  ],
  "error": null
}
```

### 20.4 `GET /api/searches/{search_id}/results`
Returns ranked results (partial while running).
```json
{
  "search_id": "uuid",
  "complete": false,
  "ranking_explanation": "Ordered by: exact reported matches first, then by freshness, distance, and price.",
  "results": [
    {
      "business": { "id":"uuid", "name":"...", "kind":"REAL_BUSINESS", "address":"...", "distance_km": 1.2 },
      "result_state": "REPORTED_AVAILABLE",
      "data_origin": "LIVE_CALL",
      "answer_timestamp": "2026-11-02T10:41:12Z",
      "freshness": { "availability": "FRESH", "price": "FRESH" },
      "reported": { "exact_match": "CONFIRMED", "price": {"amount": 42.0, "currency": "INR", "note": null},
                    "quantity": null, "wait_time_minutes": null, "open_status": "UNKNOWN" },
      "answer_summary": "Reported by phone at 10:41: exact item available; price ₹42.",
      "evidence": { "excerpt": "…", "validated": true, "question_asked": "Do you have … in stock right now?" },
      "verification_status": "REPORTED_BY_PHONE",
      "flags": []
    },
    {
      "business": { "id":"uuid", "name":"..." },
      "result_state": "NO_ANSWER", "data_origin": "LIVE_CALL",
      "reported": null, "evidence": null,
      "note": "Call was not answered. This does not mean the item is unavailable."
    }
  ]
}
```

### 20.5 `POST /api/searches/{search_id}/cancel`
`200 {status: "CANCELLED" | current terminal}`. Idempotent.

### 20.6 `POST /api/webhooks/bolna/{secret_token}`
Receives Bolna status webhooks. Contract with **Bolna** is documented in §21; this section is *our* behaviour:
1. Constant-time compare `secret_token` (path) — and the optional custom header if the spike confirms Bolna sends configured headers (A-06).
2. Optional source-IP allowlist (`WEBHOOK_ALLOWED_IPS`, default the three documented IPs; honour `X-Forwarded-For` only from configured trusted proxies).
3. Body-size cap (e.g. 256 KB) and JSON parse. Missing `execution_id`/`status` equivalents → `400 WEBHOOK_MALFORMED`.
4. Persist the raw event (dedupe on unique key) then return `200` immediately; do finalisation in a background task.
5. Unknown `execution_id` → store as orphan event, return `200`.

Response is always small JSON `{ "ok": true }`. We do **not** assume Bolna retries on non-2xx (undocumented).

### 20.7 Other endpoints
- `GET /api/businesses?category=…&lat=…&lng=…&radius_km=…` — eligible businesses (name, kind, distance; **no phone numbers**).
- `GET /health` → `{"status":"ok"}`; `GET /health/ready` → checks DB.
- `GET /api/config/public` → non-secret UI config (demo banner text, max radius, supported categories).
- (P1) `GET /api/searches/{id}/events` SSE.
- (P1) `GET /api/metrics/summary` — §39 definitions.

## 21. External integrations

### 21.1 Documentation checked 2026-10-24

| Dependency | Official source | Checked? | Notes |
|---|---|---|---|
| Buildathon | https://www.bolna.ai/symphony | **Yes** | See §21.2 |
| Bolna API | https://docs.bolna.ai/api-reference/introduction and pages under https://www.bolna.ai/docs/ | **Yes (partial)** | See §21.3 |
| Bolna repo | https://github.com/bolna-ai/bolna | **Not read** (blocked by fetch tool) | Not on the critical path: we use the hosted API, not self-hosting. PyPI package `bolna` exists (seen in search). |
| Plivo | https://www.plivo.com/docs/voice/api/overview | **Not read** | Listed by Bolna as a supported telephony provider; we do **not** call Plivo directly (D-002). |
| Exotel | https://developer.exotel.com/ | **Not read** | Same. |
| Sarvam | https://docs.sarvam.ai/ | **Not read** | Bolna changelog mentions Sarvam models (VERIFIED) — optional, only via Bolna agent config. |
| Deepgram | https://developers.deepgram.com/docs | **Not read** | Not needed: Bolna bundles transcription. |
| Cartesia | https://docs.cartesia.ai/ | **Not read** | Not needed: Bolna bundles TTS. |

Everything marked "Not read" is **ASSUMPTION-free by design**: nothing in the architecture depends on it.

### 21.2 Buildathon facts

| Fact | Tag | Source |
|---|---|---|
| Build window 2026-10-15 → 2026-11-20 | VERIFIED | event page |
| Fully virtual build; finale 2026-11-20 at Abhyas Hall, The Lalit Ashok, Bengaluru | VERIFIED | event page |
| Theme: any idea, "voice is part of it" | VERIFIED | event page |
| Top 3 teams pitch at Symphony; organisers cover travel | VERIFIED | event page |
| ₹1.2 lakh cash for top three; winner gets a Y Combinator interview | VERIFIED | event page |
| Split ₹50,000 / ₹40,000 / ₹30,000 | ASSUMPTION (from project handoff; our read of the page did not confirm the split) | — |
| Plivo is the listed "Buildathon Partner" | VERIFIED | event page |
| Exotel, Sarvam, Cartesia, Deepgram listed as sponsors | ASSUMPTION (from handoff; not seen in our read of the page) | — |
| Judging criteria, judges | **Not published** (B-04) | — |
| Submission format and deadline | **Not published** (B-04) | — |
| API/platform credits for participants | **Not published**; do not assume | — |
| Eligibility, team size | **Not published** | — |
| An "Apply now" application exists | VERIFIED | event page |

### 21.3 Bolna — verified contract (2026-10-24)

Base URL: `https://api.bolna.ai`. Auth: HTTP Bearer (`Authorization: Bearer <API key>`).

**Start a call — `POST /call`** (VERIFIED, API reference + quickstart)

| Field | Type | Req | Notes |
|---|---|---|---|
| `agent_id` | UUID string | yes | The agent that places the call |
| `recipient_phone_number` | string | yes | E.164 |
| `from_phone_number` | string | no | E.164; must be a number purchased in the account, else 400; omitted → account default |
| `scheduled_at` | ISO-8601 with TZ | no | not used |
| `user_data` | object | no | dynamic variables for the prompt; extra properties allowed |
| `agent_data` | object | no | per-call overrides (`voice_id` or `language`, not both) |
| `retry_config` | object | no | provider-side retries: `enabled` (default false), `max_retries` 1–3, `retry_on_statuses`, `retry_intervals_minutes` (default 30/60/120) |
| `bypass_call_guardrails` | bool | no | default false; if true skips time validation. **We never set true.** |

Response `200`: `{ message, status: "queued", execution_id (UUID) }`. Errors: `400 { error: int, message: string }` (e.g. missing `agent_id`/`recipient_phone_number`, number not in account, invalid language config). No other status codes documented. **DECISION D-010:** we leave `retry_config` disabled; Sonar owns retry policy (its defaults are 30–120 min, far outside a live demo's window, and we need retry decisions in our state machine).

**Get execution — `GET /executions/{execution_id}`** (VERIFIED, quickstart). Bearer auth. Example includes `transcript`, `conversation_duration`, `total_cost`, `extracted_data`, `telephony_data.recording_url`. Final statuses per the page: `completed`, `no-answer`, `busy`, `failed`, `canceled`, `stopped`, `error`, `balance-low`. **Exact JSON field names/types must be captured in the spike** (S-6); only the names above are known.

Other VERIFIED endpoints (not needed for MVP): `GET /executions/{id}/log` (component logs), `GET /executions/{id}/debug` (added 2026-10-21), `POST /v2/agent` (create agent; body has `agent_config` and `agent_prompts`; returns 201 with `agent_id`).

**Execution statuses** (VERIFIED, call-flow page): `queued → initiated → ringing → in-progress → call-disconnected → completed`, plus `no-answer`, `busy`, `failed`, `canceled`, `stopped`, `error`, `balance-low`. At `call-disconnected`, `conversation_duration`, `total_cost`, `recording_url`, `extracted_data` are still null/0; use `completed`.

**Webhooks** (VERIFIED, webhook page)
- Configured **per agent**: dashboard → agent → Extractions tab → *Webhook Configuration* (URL, "Trigger on statuses", custom headers, "Send test" posts a sample `completed` payload); or `webhook_url` inside `agent_config` (field exists per quickstart; exact JSON shape undocumented there).
- Endpoint must be publicly accessible and accept HTTP POST.
- Bolna POSTs the execution payload at each status change (if `webhook_url` is set). Payload "matches the Get Execution API response".
- Source IPs to allow: `13.203.39.153`, `13.126.9.249`, `13.202.133.53`.
- **Not documented anywhere we read:** signature/HMAC verification; retry/redelivery behaviour; event ids. A delivery-health dashboard exists (14-day delivered/failed counts, failed-delivery CSV export — changelog 2026-10-23).
- Mitigation: **D-005 verify-by-pull** (§30.2).

**Extractions** (VERIFIED, migration docs): configured in the dashboard (name, question, answer type = pre-defined allowed values or free text, expected format for numbers/dates/booleans/emails/patterns). Results appear under `extracted_data`; each result has a value (`objective` for pre-defined, `subjective` for free text) plus a numeric `confidence`. A Dispositions API manages extractions programmatically (endpoints **not read**). **Conflict in docs:** one page shows nesting `extracted_data[category][name]`, another says "flat keys" → capture the real shape in S-7. `node_extracted_data` exists for graph agents (changelog). Reserved extraction names (`reasoning`, `confidence`, names starting `_`) are rejected.

**Concurrency/plan** (VERIFIED, concurrency page): Trial — up to **2** concurrent outbound calls, **verified phone numbers only**; Paid — starts at 10 and rises with usage; over-limit calls are queued, not rejected. **Pricing** (VERIFIED, cost page): prepaid wallet; flat per-minute voice-AI rate when using preferred models; telephony charged per minute by Bolna (or your own provider if bring-your-own); no free-credit/trial amounts stated; no figures stated. Record actual `total_cost` per call instead of assuming a price.

**Telephony providers via Bolna** (VERIFIED): Plivo, Exotel, Vobiz (India); Twilio (US/UK/SG/AU and others); own SIP trunk. All support inbound+outbound and bring-your-own account. No DLT/caller-ID guidance on that page.

## 22. Provider selection and fallbacks

**D-001 Voice orchestration: Bolna.** It provides agent, STT/LLM/TTS pipeline, outbound call API, status webhooks, extraction and cost in one place; the buildathon is Bolna's. *Fallback:* none cheap; if the spike fails, the smallest viable alternative is Bolna's own open-source stack (not read) or a different hosted voice-agent platform — a re-plan, not a tweak. **Gate G1 exists to find this out early.**

**D-002 Telephony: whatever route Bolna provides for our account (default number or one bring-your-own provider).** We do not integrate Plivo/Exotel APIs directly. *Escalation path if the default number is unusable in India (B-03):* connect one Bolna-supported provider (Plivo preferred only because it is the listed buildathon partner — not a verified advantage) via Bolna's setup. Never two.

**D-011 No separate STT/TTS/LLM providers.** Use Bolna's bundled pipeline and preferred models. Sarvam/Deepgram/Cartesia become relevant only if the spike shows poor accuracy on the target language/accent (then evaluate *through Bolna's agent configuration*).

**D-012 No second LLM for parsing/extraction in MVP.** Candidate values come from Bolna extractions; our deterministic validator decides what we store. *Revisit when:* validator rejects > N % of otherwise-good calls in rehearsal.

### 22.1 Optional sponsor stack (DEFERRED, P2; compact form, v2.1)
**Status of this section.** The v1.1 header referred to eleven sub-sections (§22.1–§22.11) that were never in the file. This single section replaces them, built only from what v1.1 said elsewhere (the header, §0.1, §2, B-07, B-08, D-001, D-002, D-011). It is a plan for *how sponsors may be shown honestly*, not a commitment to integrate any of them.

**Principle (D-023).** The production path is **Bolna-first and works with every optional provider disabled.** Nothing here is on the critical path to M1, M2 or M3.

**Allowed roles (D-024).** A sponsor enters in exactly one of two ways, never both for the same call:
1. **Agent variant:** a Bolna agent configured to use that sponsor's model or route (through Bolna's own settings), exercised on `TEAM_TEST_LINE` numbers only.
2. **Sponsor Lab:** an offline benchmark (below) on identical, consented, recorded test inputs.
One real call is **never** routed through several providers to "show them all".

| Sponsor | Possible role, via Bolna configuration only | Current status (§0.1 vocabulary) |
|---|---|---|
| Sarvam | Indic speech/LLM option in the agent configuration, if S-8 shows the default is weak on Hindi/Kannada (D-011) | `PROPOSED`; registration credit perk per the event page is ASSUMPTION A-02 |
| Deepgram | Alternative STT in the agent configuration | `PROPOSED` |
| Cartesia | Alternative TTS voice in the agent configuration | `PROPOSED` |
| Plivo, Exotel | Telephony route, only as one provider connected through Bolna's supported-provider setup (D-002, D-025); needs an India-registered business and KYC (B-07) | `PROPOSED`, `BLOCKED` until B-07 resolves |

No sponsor API is called directly by Sonar code (D-002, D-011).

**Sponsor Lab (D-027, P2).** A small offline harness (Build Map T19.1) that replays the same short, scripted, consented utterances (recorded by the team on test lines) through each available agent variant and compares: transcription correctness of item names and numbers (n/N), time to first spoken word, cost per minute as reported, and failure count. Results are labelled with provenance (`MEASURED`, `DOCUMENTED`, `NOT_MEASURED`); a variant with no access is `NOT_MEASURED` (D-030), never filled in from marketing material. The Lab never touches real businesses and never writes to `business_responses`.

**Claims rule (D-026, D-029).** The status vocabulary and demonstration depths (D0…D4) in §0.1 govern every use of a sponsor's name: in the README, the UI and the pitch, a sponsor may be described only at the highest depth actually reached (for example "documented" at D0, "measured on test lines in the Sponsor Lab" at D3). A logo or an installed SDK is never evidence.

## 23. Query parsing and answer extraction

### 23.1 Query parsing (D-013)
Two implementations behind `QueryParser`:
- **P0 `StructuredFormParser`:** the UI collects `category`, `item/service`, key `attributes`, `location`, `radius_km`; `query_text` is kept for display. The parser validates, normalises (units, radius), extracts a "within N km" hint from free text if present, and applies the rules below.
- **P2 `LLMQueryParser`** (DEFERRED): only if free-text demo feels too stiff. Decision criteria: parse accuracy on ≥ 30 labelled queries, added dependency cost, latency. Output would still pass the same validation.

Location: preset demo localities or browser geolocation → lat/lng. No geocoding API (avoids a dependency and terms question).

### 23.2 Handling table

| Situation | Behaviour |
|---|---|
| Missing location | `NEEDS_CLARIFICATION` ("Where should we search?") |
| Missing essential attribute (e.g. strength for a medicine, model for a part, device model for a repair) | `NEEDS_CLARIFICATION` listing the missing attributes; essential attributes are defined per category in config |
| Ambiguous item name | Clarify; never pick silently |
| Unsupported category | `UNSUPPORTED_QUERY` + list of supported categories |
| Invalid radius (≤ 0, > max) | `VALIDATION` with allowed range |
| No eligible businesses | job ends `FAILED/NO_ELIGIBLE_BUSINESSES`, message explains how many were in range and why excluded (counts only) |
| Conflicting criteria (e.g. "open now" + "tomorrow") | clarify |
| Prescription-only/controlled drug, dosing, interactions, "which should I take", legal/other advice | `UNSUPPORTED_QUERY` refusal, no job |
| Prompt-injection-looking input | treated as plain data; never concatenated into system prompts; only whitelisted fields flow to `user_data` (§30) |

### 23.3 Answer validation rules (deterministic; the heart of trust)

Input: provider record (`transcript`, `extracted_data`, status), the `ParsedQuery`. Output: `ValidatedAnswer`.

| Rule | Behaviour |
|---|---|
| V1 | Only attempts with provider status `completed` and a non-empty transcript are eligible. Otherwise **no response row** (attempt stays NO_ANSWER/FAILED/etc.). |
| V2 | `availability` must come from the allowed set (`available`, `not_available`, `unsure`, `declined`) produced by a pre-defined extraction; anything else → `UNCERTAIN`. |
| V3 | A positive or negative claim requires an **evidence excerpt**: the extraction's supporting quote must be found (case/space/punctuation-normalised substring) in the transcript. Not found → `UNCERTAIN`, flag `EVIDENCE_NOT_FOUND`. |
| V4 | `REPORTED_AVAILABLE` additionally requires `exact_match = CONFIRMED` (business confirmed the exact requested item/attributes). If only an alternative was offered → `ALTERNATIVE_ONLY`; if exact match unknown → `UNCERTAIN`. |
| V5 | Never mutate a requested attribute. `matched_attributes[attr]` is `CONFIRMED` only if the business confirmed it; `DIFFERENT` if they named a different value; else `UNKNOWN`. |
| V6 | Price: must be numeric, > 0, plausible (configurable per category upper bound), currency explicit (default INR only if the call was in India and the business stated rupees; otherwise null). The numeric value must appear (as digits or a recognised spoken-number form) in the transcript. Not quoted → `price_amount = NULL`. Never inferred. |
| V7 | Price quoted for a different item than the exact one → store in `price_note`, keep `price_amount` null, flag `PRICE_NOT_EXACT_ITEM`. |
| V8 | Quantity/wait/open status: stored only if explicitly stated and numerically valid; else null/`UNKNOWN`. |
| V9 | Contradiction (e.g. "available" extraction but transcript evidence says "finished") → `UNCERTAIN`, flag `CONTRADICTORY`, `verification_status` unchanged; the UI shows the contradiction instead of choosing. |
| V10 | `opt_out_requested = yes` → set business `OPTED_OUT`, response `DECLINED`. Highest precedence. |
| V11 | Provider `confidence` is stored raw (`provider_confidence`) for analysis. It is **not** displayed as a percentage and **not** used to promote an answer. We do not claim it is calibrated. |
| V12 | `answer_summary` is **templated** from validated fields only. Free LLM prose never reaches the UI. |
| V13 | Evidence excerpt is truncated to ≤ 600 chars and HTML-escaped on render; transcripts are never interpreted as instructions. |
| V14 | Voicemail/IVR/"wrong number" detected (extraction field `call_outcome`) → no response row; attempt marked `COMPLETED` with `failure_reason=NO_HUMAN`; treated like no answer in the UI. |

### 23.4 Category configuration (data, not code)
```yaml
categories:
  pharmacy:
    essential_attributes: [strength]        # per item; name always required
    blocked_terms_file: config/blocked_pharmacy_terms.txt   # prescription-only / controlled / dosing
    required_fields_default: [availability, price]
    price_max_plausible_inr: 20000
  computer_repair:
    essential_attributes: [device_model, problem]
    required_fields_default: [availability_today, price]
```
Extraction fields (names are ours; configured in the Bolna dashboard during the spike; **A-08** until confirmed): `availability`, `exact_match_confirmed`, `alternative_offered`, `price_amount`, `price_currency_stated`, `quantity_available`, `wait_time_minutes`, `open_now`, `opt_out_requested`, `call_outcome`, `supporting_quote`.

## 24. Business discovery and ranking

### 24.1 Discovery (D-014): curated directory only for MVP
A YAML/CSV seed of consenting businesses and test lines, loaded into `businesses`. *Why:* removes licensing/terms uncertainty (we did **not** verify any maps/directory API terms, and we do not scrape), makes tests deterministic, and matches the consent rule. Real phone numbers live in a git-ignored local file; the repo contains `data/businesses.example.yaml` with obviously fake placeholders.
Future directory sources (DEFERRED): a permitted maps/places API (terms, attribution, storage rules to be verified first) and a business onboarding flow.

### 24.2 Selection
Eligible = category match ∧ `participation_status ∈ {CONSENTED, TEST_LINE}` ∧ not opted out ∧ within radius (Haversine in Python; PostGIS **not** used — D-015, it adds nothing at < 100 rows) ∧ not at its daily call cap ∧ not called within the cooldown (unless cache covers it). Take the nearest `MAX_TARGETS_PER_SEARCH`.

### 24.3 Ranking (transparent, no invented scores; D-016)
Lexicographic ordering:
1. `REPORTED_AVAILABLE` with all required fields present
2. `REPORTED_AVAILABLE` missing a required field
3. `ALTERNATIVE_ONLY`
4. `UNCERTAIN`
5. `REPORTED_UNAVAILABLE`
6. `DECLINED`
7. `NO_ANSWER`, `CALL_FAILED`, `PENDING`, `CANCELLED` (grouped, shown below)

Within a tier: live-this-search before cached; then lower distance; then lower price when price was requested. The UI states the order in plain words (`ranking_explanation`). Rank position never implies truth.

## 25. Call scripts and conversation states

The agent is configured in the Bolna dashboard (D-017: dashboard-created agent for MVP; `POST /v2/agent` is VERIFIED but programmatic creation is P2). The prompt text is versioned in `docs/agent/` so it is reproducible. Per-call data goes through `user_data` (VERIFIED field); the **placeholder syntax for `user_data` in the prompt is A-09 — confirm in S-2**.

### 25.1 Conversation states
```mermaid
stateDiagram-v2
  [*] --> Greeting
  Greeting --> Opening: person answers
  Greeting --> End: voicemail / IVR (hang up, no data)
  Opening --> End: asks not to be called (record opt-out)
  Opening --> AskAvailability: agrees to continue
  AskAvailability --> ConfirmExact: says available
  AskAvailability --> Close: says not available
  AskAvailability --> Clarify: unsure / "something similar"
  Clarify --> ConfirmExact: gives specifics
  Clarify --> Close: still unsure
  ConfirmExact --> AskDetails: exact confirmed
  ConfirmExact --> Close: not exact
  AskDetails --> Close: price / quantity / timing collected or refused
  Close --> End: thank, no commitment, hang up
```

### 25.2 Script (English; wording is a starting point, tuned in Phase 11)
- **Opening (always, truthful):** "Hello, this is an automated assistant calling for Sonar. I'm checking a quick fact for a customer — is now an okay moment for one or two questions? This call is transcribed to record your answer."
- **If asked who/why:** "I'm an AI assistant. Sonar helps people find which shops have an item or service right now. I won't buy or reserve anything."
- **If they decline / ask to stop:** "Understood — I won't call again. Thank you." (then end; set `opt_out_requested = yes`).
- **Availability:** "Do you currently have {item} {attributes} available?"
- **Confirm exact:** "Just to be sure, is that exactly {item}, {attributes}?" (If a different strength/model: "Okay, that's a different one — I'll note it as different.")
- **Details (only fields in `required_fields`):** "Could you tell me the price for that one?" / "How many do you have?" / "Can you take it today?"
- **Close:** "Thank you, that's all I needed. I haven't committed to anything on anyone's behalf. Goodbye."
- **Never:** recommend alternatives, give medical/other advice, negotiate, promise a visit, repeat a refused question more than once, or continue past the first clear refusal.
- **Language:** English with Hindi capability is an **ASSUMPTION (A-10)**; Bolna docs show `agent_data.language` and multilingual agents (VERIFIED field), but accent/vocabulary quality for shopkeepers is untested.
- **Limits:** agent `call_terminate` (VERIFIED config field, example 90 s) and `hangup_after_silence` (example 10 s) — our values in §27.

## 26. State machines

### 26.1 Search job
```mermaid
stateDiagram-v2
  [*] --> CREATED
  CREATED --> NEEDS_CLARIFICATION: essential field missing
  NEEDS_CLARIFICATION --> [*]: user resubmits (new job)
  CREATED --> FAILED: no eligible businesses / refusal
  CREATED --> RUNNING: targets planned, dispatch begins
  RUNNING --> COMPLETED: all attempts terminal, all answered/definitive
  RUNNING --> COMPLETED_PARTIAL: all terminal, some no-answer/failed/timed out or deadline hit
  RUNNING --> CANCELLED: user cancels
  RUNNING --> FAILED: provider unusable (e.g. balance-low before any success)
  COMPLETED --> [*]
  COMPLETED_PARTIAL --> [*]
  CANCELLED --> [*]
  FAILED --> [*]
```
`COMPLETED` = every attempt reached a terminal state and **each business yielded a response row** (any availability value). `COMPLETED_PARTIAL` otherwise. A job can complete with zero positive results; that is still `COMPLETED`.

### 26.2 Call attempt
```mermaid
stateDiagram-v2
  [*] --> PENDING
  PENDING --> DISPATCHING: claimed by orchestrator
  PENDING --> CANCELLED: job cancelled
  DISPATCHING --> DIALING: POST /call ok, execution_id stored
  DISPATCHING --> FAILED: provider 4xx/5xx after bounded retries
  DISPATCHING --> DISPATCH_UNKNOWN: crash/timeout after sending, outcome unknown
  DIALING --> RINGING
  RINGING --> IN_PROGRESS
  DIALING --> IN_PROGRESS
  IN_PROGRESS --> PROCESSING: call-disconnected
  PROCESSING --> COMPLETED: completed + finalised
  DIALING --> NO_ANSWER
  RINGING --> NO_ANSWER
  RINGING --> BUSY
  DIALING --> FAILED
  RINGING --> FAILED
  IN_PROGRESS --> STOPPED
  DIALING --> TIMED_OUT: deadline / reconciler gave up
  RINGING --> TIMED_OUT
  IN_PROGRESS --> TIMED_OUT
  PROCESSING --> TIMED_OUT
  DIALING --> INSUFFICIENT_BALANCE
  NO_ANSWER --> [*]
  BUSY --> [*]
  COMPLETED --> [*]
```
A retry creates a **new** `call_attempts` row (`attempt_number + 1`, `not_before = now + backoff`), never reuses a row.

## 27. Retry, timeout, concurrency, idempotency rules

### 27.1 Configurable defaults (all **ASSUMPTION — tune in Phase 11**; env-driven, §36)

| Parameter | Default | Rationale |
|---|---|---|
| `MAX_TARGETS_PER_SEARCH` | 5 | keep cost and calling burden on consenting shops small |
| `MAX_CONCURRENT_CALLS` | 2 | equals documented Bolna trial concurrency (VERIFIED); raise only after confirming plan |
| `CALL_MAX_SECONDS` (agent `call_terminate`) | 120 | long enough for 3–4 questions; bounds cost |
| `HANGUP_AFTER_SILENCE_SECONDS` | 10 | matches documented example |
| `MAX_ATTEMPTS_PER_BUSINESS_PER_SEARCH` | 2 | one retry only |
| Retry conditions | `NO_ANSWER`, `BUSY`; `FAILED` once; **never** after answered/declined/opt-out | avoid re-bothering |
| Backoff | 120 s then (if configured) 600 s; live-demo mode may disable retries | Bolna's own 30/60/120 min defaults are unusable in a demo |
| `SEARCH_DEADLINE_SECONDS` | 300 | a judge will not wait longer; remaining calls → `TIMED_OUT` |
| `RECONCILE_AFTER_SECONDS` | 90 after last event on non-terminal attempt | covers lost webhooks |
| `BUSINESS_COOLDOWN_MINUTES` | 15 | avoid calling same shop for back-to-back searches |
| `BUSINESS_DAILY_CALL_CAP` | 4 | protects pilot goodwill |
| `GLOBAL_DAILY_CALL_BUDGET` | 40 | cost cap; stop dispatch with `BUDGET_EXCEEDED` |
| Calling hours | per-business `best_call_window`, default 09:00–20:00 IST; never `bypass_call_guardrails` | consent + courtesy |

### 27.2 Idempotency and ordering (normative)
1. **Dispatch:** insert attempt (`PENDING`) → claim → set `DISPATCHING` + commit → `POST /call` → store `execution_id` + `DIALING` + commit. Bolna's `POST /call` has no documented idempotency key (A-11), so a crash between send and commit leaves `DISPATCHING` with no id → on restart mark `DISPATCH_UNKNOWN` and **do not auto-retry** (a duplicate call to a shopkeeper is worse than a missed one); operator can inspect Bolna's call list.
2. **Webhook before id committed:** store as orphan; after `execution_id` commit, an `attach_orphans` step links events by `provider_call_id`.
3. **Duplicate events:** unique key `(provider, provider_call_id, provider_status, payload_sha256)`; insert-or-ignore.
4. **Out-of-order:** monotonic ranks (§19.3).
5. **Finalise exactly once:** `business_responses.call_attempt_id UNIQUE` + `INSERT … ON CONFLICT DO NOTHING`; job aggregation done under `SELECT … FOR UPDATE` on the `search_jobs` row.
6. **Concurrency cap:** in-process `asyncio.Semaphore(MAX_CONCURRENT_CALLS)` plus a DB count of non-terminal attempts as a guard; counted from `DISPATCHING` until terminal.
7. **Cancellation:** sets job `CANCELLED`, pending → `CANCELLED`. A documented stop-call endpoint was **not found** in the docs index (A-12), so in-flight calls are allowed to finish and are recorded.
8. **Restart:** on startup run reconciler: `DISPATCHING` w/o id → `DISPATCH_UNKNOWN`; non-terminal with id → poll `GET /executions/{id}`; jobs past deadline → close.

## 28. Freshness and revalidation

Per-field TTLs (ASSUMPTION A-13; env-configurable): availability **60 min**, quantity **30 min**, wait time **15 min**, open status **15 min**, price **24 h**.
- `FRESH` if `now − answer_timestamp ≤ TTL`, else `STALE`; `UNKNOWN` if the field is null.
- **Cache reuse (FR-30, P1):** a prior `LIVE_CALL` response is reusable only if it is `VALID`, the item/attributes match **exactly**, all `required_fields` are FRESH, the business remains eligible, and `force_fresh` is false. It is rendered as `CACHED_LIVE` with its **original** timestamp ("Earlier call, 41 min ago").
- STALE data is never shown as a current answer; it can be listed as "last reported …" and triggers a fresh call if the business is eligible.
- Simulated results are never cached into the live knowledge base and never reused for live searches.

## 29. Error handling and recovery

| Failure | Handling |
|---|---|
| Bolna `POST /call` 400 (bad number, bad agent) | attempt `FAILED`, `PROVIDER_REJECTED`, message stored; not retried |
| Bolna 5xx / timeout | retry dispatch with exponential backoff (≤ 2); then `FAILED/PROVIDER_UNAVAILABLE` |
| `balance-low` | stop all dispatching, job `FAILED/INSUFFICIENT_BALANCE` if nothing answered, loud log/alert |
| Webhook not received | reconciler polls after `RECONCILE_AFTER_SECONDS` |
| Webhook auth failure | 401, count metric, never persisted as a result |
| Pull of execution fails | retry with backoff; after limit mark attempt `ERROR`, keep raw event |
| Validator rejects | response row with `INVALID`/`UNCERTAIN`; never crash the job |
| DB unavailable | `/health/ready` fails; webhooks return 503 (so a retrying provider, if any, redelivers); reconciler repairs after recovery |
| Process crash | §27.2 restart recovery |
| Unknown provider status | log + keep non-terminal + reconcile; never invent a mapping |
| UI polling error | UI shows "Connection lost, retrying" and keeps last known state; never clears results |

User-facing error copy is reviewed for misleading claims (NFR-09; Build Map T9.5).

## 30. Security, privacy and safety

### 30.1 Threat model

| # | Threat | Impact | Mitigation |
|---|---|---|---|
| T1 | Provider API key leaks (repo, logs, browser) | Account abuse, spend | Server-only env; `.env` git-ignored; secret scanning (`gitleaks`-style check in CI, P1); automated bundle scan (NFR-07); logs never include headers |
| T2 | Forged webhook | Fake results | Secret path token + optional header secret + IP allowlist + **verify-by-pull** (never trust body) |
| T3 | Replay/duplicate webhook | Duplicate state | Dedupe key, monotonic ranks, unique response per attempt |
| T4 | Unauthorised call initiation / cost abuse | Spend, harassment | `X-Sonar-Key`, rate limit per IP, per-search target cap, global daily budget, per-business daily cap, only consenting businesses, no free-text phone numbers accepted anywhere in the API |
| T5 | Calling a non-consenting number | Legal/reputational | Selector + dispatcher both check `participation_status`; DB CHECK requires `consent_recorded_at`; no API to add businesses |
| T6 | Prompt injection via transcript or business speech ("ignore your instructions…") | Misleading results, data exfil | Transcript is data; validator is deterministic code; no LLM reads transcripts in MVP; whitelisted `user_data` fields; evidence rendered as escaped text |
| T7 | Prompt injection via user query | Agent misbehaviour | Only validated structured fields (`item.name`, attribute values, length-limited, charset-checked) enter `user_data`; free `query_text` is display-only |
| T8 | SQL injection | Data loss | SQLAlchemy parameterised queries only; no string-built SQL |
| T9 | PII exposure in logs | Privacy | Phone numbers masked (`+91*******123`); raw payloads stored in DB (redacted), not logged |
| T10 | Unauthorised access to a search | Privacy | UUIDv4 capability ids; no listing endpoint; rate limits |
| T11 | XSS via transcript/evidence | Browser compromise | React escaping; no `dangerouslySetInnerHTML`; CSP header |
| T12 | Recording/transcript over-retention | Privacy | No audio fetch/store; `recording_url` not persisted; transcript excerpt ≤ 600 chars; retention job (default 30 days for events/payloads, 90 days for responses) |
| T13 | Business opt-out ignored | Trust/legal | `OPTED_OUT` absolute exclusion; opt-out processing precedence V10 |
| T14 | Webhook endpoint DoS | Availability | Body cap, constant-time check first, cheap persist, rate limit |
| T15 | Simulated data mistaken for live | Deception | `data_origin`, permanent banner, simulator results never cached for live |
| T16 | Clinical-advice drift (pharmacy) | Harm | Blocked-terms refusal, agent never advises, UI disclaimer |

### 30.2 D-005 — verify-by-pull (key control)
Because no webhook signature scheme is documented (VERIFIED absence in pages read), a webhook is only a *hint that something changed*. Finalisation **always** calls `GET /executions/{execution_id}` with our Bearer key and uses **that** response. Consequences: a forged webhook can at worst trigger a harmless extra GET; it can never inject a result. The execution id must also match a `call_attempts` row we created.

### 30.3 Privacy policy (MVP, to publish in the README and UI footer)
- We call only businesses that agreed.
- Calls are transcribed. We store a short evidence excerpt and structured fields, not audio.
- Business contacts can ask to stop; it takes effect immediately and permanently for Sonar.
- Searches contain no personal user data beyond a coarse location and query; no accounts.
- Data retention periods as above; deletion on request via maintainer script (`scripts/delete_business_data.py`, Build Map T9.7, P1).
- **A-14:** whether Bolna retains recordings/transcripts and whether recording can be disabled is unknown → confirm in S-9 and disclose accordingly.

## 31. Compliance questions to verify (no compliance is claimed)

We read only a secondary law-firm commentary (Bar & Bench, 2026-03-09; not the regulation text). Items below are **questions**, not findings.

1. Are automated/AI-voice calls that only *ask a business a factual question* "commercial communication" under TRAI's TCCCPR framework, or outside it? (Commentary says TCCCPR "does not yet directly regulate AI as a risk category" and that AI-specific amendments were *reported as under consideration*.)
2. Which number series and registration (e.g. the 160 series for service/transactional calls, mentioned in the commentary) apply to our caller number, and does Bolna's default number comply?
3. Do DLT/principal-entity/telemarketer registrations apply?
4. Does DND/NCPR apply to business landlines/mobiles used as shop numbers?
5. How long does consent last, and what record is sufficient? (Commentary mentions Feb-2025 changes limiting inferred/explicit consent durations — **verify the actual rule**.)
6. Is disclosure of AI nature and transcription legally required and, if so, in what wording?
7. Recording/transcription consent requirements and storage obligations (DPDP Act implications).
8. Bolna/Plivo/Exotel acceptable-use terms for automated outbound calls.
9. Buildathon rules about third-party data/calls.

**Mitigation until resolved (D-004):** consenting businesses only; written/recorded consent before any live call; truthful AI disclosure on every call; immediate opt-out; low volume; test lines for development; no marketing content in any call.

## 32. Observability and logging

- JSON logs (structlog or stdlib JSON): fields `ts, level, event, request_id, search_id, attempt_id, business_id, provider_call_id, from_status, to_status, duration_ms`.
- Every state transition logs one line (NFR-14). Phone numbers masked; no transcripts in logs.
- `audit_events` rows for: dispatch, opt-out, cancel, manual review, budget stop.
- Metrics (P1): counters computed from DB per §39 (no Prometheus required).
- Webhook diagnostics: count of auth failures, orphans, duplicates; Bolna's delivery-health dashboard (VERIFIED) is the provider-side view.
- `/health`, `/health/ready`.

## 33. Testing strategy

### 33.1 Layers
- **Unit (pure):** query validation/parsing; attribute matching; validator rules V1–V14; freshness; ranking; status transitions & ranks; retry eligibility/backoff; idempotency keys; error classification; phone masking.
- **Integration (real Postgres):** migrations apply/rollback; constraints (CHECKs, UNIQUEs); orchestrator with `SimulatedVoiceProvider` and a mocked HTTP layer for `BolnaVoiceProvider` (`respx`/`httpx.MockTransport`); webhook endpoint (auth, dedupe, orphan, out-of-order) with captured fixtures; finalizer pull; reconciler.
- **Contract tests:** JSON fixtures captured in the spike (redacted) under `backend/tests/fixtures/bolna/`; API response schemas validated against Pydantic models; OpenAPI snapshot.
- **E2E (simulator):** §33.3 matrix; Playwright drives the real UI against the real backend in demo mode.
- **Live integration (manual, bounded):** only approved test numbers/consenting businesses; ≤ N calls per session; never replaces the above.
- **Security tests:** no secret in bundle; webhook with wrong token → 401; SQLi payloads in fields; XSS payload in transcript fixture renders inert.

### 33.2 Tooling (D-018)
Backend: `pytest`, `pytest-asyncio`, `httpx`, `respx`, `ruff` (lint+format), `mypy` (P1). Frontend: `vitest`, React Testing Library, Playwright (P1 for CI). Fixtures never contain real numbers or real shopkeeper speech beyond what consent allows.

### 33.3 E2E scenario matrix (simulator scenario ids)
| Scenario | Expected |
|---|---|
| `all_available` | all `REPORTED_AVAILABLE`, job `COMPLETED` |
| `one_no_answer` | that business `NO_ANSWER`, others fine, job `COMPLETED_PARTIAL`, no "unavailable" wording |
| `one_explicit_unavailable` | `REPORTED_UNAVAILABLE` with evidence |
| `one_ambiguous` | `UNCERTAIN`, flags shown |
| `one_missing_price` | price null, "price not quoted" shown |
| `duplicate_webhook` | no duplicate rows |
| `out_of_order_events` | final state correct |
| `one_call_failed` | `CALL_FAILED` shown, job proceeds |
| `partial_before_complete` | first result visible while others pending |
| `opt_out` | business excluded afterwards |
| `alternative_only` | `ALTERNATIVE_ONLY`, not available |
| `injection_in_transcript` | rendered inert, no state change |
| `deadline_hit` | stragglers `TIMED_OUT`, `COMPLETED_PARTIAL` |
| `restart_mid_search` | correct recovery, no double dial |

## 34. Performance and cost

- Load is tiny (≤ 5 calls per search); correctness and honesty dominate performance.
- **Latency is dominated by humans and telephony.** We measure *time to first useful result* and *time to complete* in rehearsals (§39); we publish those measured numbers only.
- **Cost drivers (VERIFIED qualitatively):** call minutes (flat voice-AI rate + per-minute telephony + platform fee), long calls, verbose LLM output, premium voices, international numbers. **No figures are assumed.** We record `total_cost` per call from the execution record (field named in the VERIFIED example) and compute cost per useful result from real data.
- Cost controls: call-duration cap, target cap, daily budget, retry cap, cooldown, cache reuse.

## 35. Deployment architecture

**D-019: decide the host after the local system works (Phase 10).** Criteria: public HTTPS URL; ability to run one always-on process (webhooks); managed Postgres or a container; secrets store; logs; cost; setup time. We do not assume any provider or free tier exists.

- Backend: container (`backend/Dockerfile`), **single uvicorn worker**, runs migrations on deploy (`alembic upgrade head` as a release step).
- Frontend: static build (`vite build`) served by any static host or by the backend.
- Database: PostgreSQL 15+ (managed or container with volume + backups).
- Public webhook URL: `https://<host>/api/webhooks/bolna/<token>`; set in the Bolna agent's Webhook Configuration; use the dashboard's "Send test" for a first check.
- Dev: HTTPS tunnel to localhost (S-3) — any tunneling tool; do not hard-code one.
- Health checks: `/health`, `/health/ready`. Logs to stdout.
- Rollback: keep previous image tag; migrations additive-only in MVP so rollback = redeploy previous image; DB restore from backup as last resort.
- Secrets: host secret store; never in image or repo.

## 36. Environment variables

These names are **our convention (D-020)**, not provider-mandated.

| Variable | Required | Example / default | Purpose |
|---|---|---|---|
| `SONAR_ENV` | yes | `dev`/`prod` | behaviour switches |
| `DATABASE_URL` | yes | `postgresql+psycopg://sonar:sonar@localhost:5432/sonar` | DB |
| `SONAR_ACCESS_KEY` | yes | long random | `X-Sonar-Key` for search creation |
| `BOLNA_API_KEY` | live only | — | Bearer token for `api.bolna.ai` |
| `BOLNA_API_BASE_URL` | no | `https://api.bolna.ai` | VERIFIED base |
| `BOLNA_AGENT_ID_<CATEGORY>` | live only | UUID | agent per vertical (e.g. `BOLNA_AGENT_ID_PHARMACY`) |
| `BOLNA_FROM_PHONE_NUMBER` | no | E.164 | omit to use account default |
| `WEBHOOK_SECRET_TOKEN` | yes | long random | path token for `/api/webhooks/bolna/{token}` |
| `WEBHOOK_HEADER_NAME`/`WEBHOOK_HEADER_VALUE` | no | — | only if S-5 confirms custom headers are delivered |
| `WEBHOOK_ALLOWED_IPS` | no | `13.203.39.153,13.126.9.249,13.202.133.53` | VERIFIED Bolna source IPs |
| `TRUSTED_PROXY_IPS` | no | — | to honour `X-Forwarded-For` |
| `BUSINESS_SEED_PATH` | yes | `data/businesses.local.yaml` | git-ignored real data |
| `MAX_TARGETS_PER_SEARCH`, `MAX_CONCURRENT_CALLS`, `CALL_MAX_SECONDS`, `HANGUP_AFTER_SILENCE_SECONDS`, `MAX_ATTEMPTS_PER_BUSINESS`, `SEARCH_DEADLINE_SECONDS`, `RECONCILE_AFTER_SECONDS`, `BUSINESS_COOLDOWN_MINUTES`, `BUSINESS_DAILY_CALL_CAP`, `GLOBAL_DAILY_CALL_BUDGET` | no | §27.1 | bounds |
| `FRESHNESS_TTL_*` | no | §28 | per-field TTLs |
| `RATE_LIMIT_SEARCH_PER_MINUTE` | no | `10` | per-IP limit |
| `RETENTION_EVENT_DAYS`, `RETENTION_RESPONSE_DAYS` | no | `30`, `90` | retention |
| `LOG_LEVEL` | no | `INFO` | |
| `ALLOWED_ORIGINS` | no | `http://localhost:5173` | CORS |
| `VITE_API_BASE_URL` | frontend | `/api` | the **only** frontend env; contains no secrets |

`.env.example` contains placeholders only. Any variable starting `VITE_` is public by construction and is checked by the bundle scan.

## 37. Demo workflow and presentation narrative

### 37.1 Script
1. **Problem (20 s):** open a normal listing for a local shop: hours, no stock, no price.
2. **Query:** enter a specific item/service + locality + radius.
3. **Plan:** show the businesses Sonar will call (names, distances, "consented" badge, test lines labelled).
4. **Start:** press search; job id returned instantly.
5. **Live progress:** rows move queued → ringing → in call → processing.
6. **First useful result** appears while others are pending.
7. **Evidence:** expand — transcript excerpt, timestamp, question asked, "reported by phone".
8. **Unknown ≠ unavailable:** show one unanswered/ambiguous row and its honest wording.
9. **Failure handled:** one failed call, job still completes `COMPLETED_PARTIAL`.
10. **Expansion:** category is configuration; one sentence on next verticals (no market claims).

**Wave 2 beats (insert only the ones that are built and rehearsed; each maps to a flag):**
- *After step 1:* speak the question (voice in, §52.1); show the parsed fields; confirm.
- *At step 4:* the radar pings; pins appear at their real bearing and distance (§52.2).
- *At step 5:* the live transcript ticker (and, for a consenting test line, the audio) shows the agent talking to a person in the room (§51).
- *After step 6:* **the stop rule fires**: "Sonar called 3 of 12 and stopped, because 2 had confirmed." Show the not-called rows and their wording (§48.4). Offer "ask everyone" to show `THOROUGH`.
- *At step 7:* the evidence panel highlights the validated quote in its context window (§51).
- *At step 8:* the trust ledger lists what Sonar declined to claim (§52.4).
- *Shop side (30 s):* open one shop's demand digest page and, if S-12 passed, call the inbound line and say what you have; show the self-reported row with its distinct label (§49–§50).
- *Closing:* the metrics slide shows only measured numbers with n: ground-truth agreement n/N, calls avoided, cost per useful result, and the manual baseline if measured (§54).
- *Judge-as-shopkeeper:* hand a test line to a judge and let them play a difficult shopkeeper (hedging, interrupting, switching language). A graceful `UNCERTAIN` is a success.

**Do not say:** that skipped shops are unavailable; that self-reports were verified by a call; that history is today's availability; that time was saved without the measured baseline; any accuracy figure without n/N.

### 37.2 Pitch narrative (draft; verify against built behaviour)
"Listings tell you a shop exists. They don't tell you if it has what you need right now. Sonar calls the shops for you, asks the right follow-up, and shows you exactly what each one said, when, with the evidence — and it never confuses silence with 'no'."

### 37.3 Rehearsal protocol
Run ≥ 3 times from a clean browser profile; record time to first result and total time each run; note any call that didn't connect.

### 37.4 Claim checklist (AC-10)
Every sentence in the pitch is mapped to a demonstrated screen/test. No claims about accuracy %, time saved, coverage, or market size unless measured and shown.

## 38. Backup demo strategy
1. **Tier 1:** live calls to consenting businesses/test lines.
2. **Tier 2:** live calls to team test lines only (labelled role-play).
3. **Tier 3:** `demo_mode` with the simulator — whole UI flow with a permanent amber "SIMULATED — not real calls" banner on every result and in the page header. The simulator uses scripted scenarios derived from real captured call structures where possible.
4. **Tier 4:** a pre-recorded screen capture of a real run, labelled with the date.
The operator toggles demo mode explicitly; there is no automatic silent fallback to simulation (it must be a visible, deliberate choice).

## 39. Evaluation metrics (definitions and denominators; no baselines assumed)

| Metric | Definition | Denominator |
|---|---|---|
| Call connection rate | attempts that reached `IN_PROGRESS` ÷ attempts dispatched | live attempts with `DIALING` reached |
| Structured answer completion rate | responses with all `required_fields` non-null and `extraction_status=VALID` ÷ attempts that reached `COMPLETED` | completed live attempts |
| Exact-match answer rate | responses with `exact_match=CONFIRMED` ÷ responses | live responses |
| Uncertain-result rate | responses `UNCERTAIN` ÷ responses | live responses |
| Median time to first useful result | median over searches of (first `REPORTED_*` `answer_timestamp` − `started_at`) | searches with ≥ 1 useful result |
| Time to complete | median (`completed_at` − `started_at`) | completed searches |
| Cost per useful result | Σ `cost_amount` of live attempts ÷ count of `REPORTED_*` responses | live searches in period |
| Stale-answer rate | responses displayed while `STALE` ÷ responses displayed | displayed responses |
| Human-verified extraction accuracy | (`HUMAN_REVIEWED` responses where reviewer agrees the stored fields match the call) ÷ reviewed responses | reviewed sample (report n) |
| **North-star:** useful-search rate | searches with ≥ 1 `REPORTED_*` response that is FRESH and validated, within `SEARCH_DEADLINE_SECONDS` ÷ searches | live searches |

Report small-n honestly (state n and that it is a rehearsal, not a benchmark).

Wave 2 adds ground-truth agreement, stop-rule saving, coverage loss, manual baseline, digest consent rate and self-report quarantine rate: see §54.2.

## 40. Risks, mitigations, unresolved questions

| ID | Risk | Likelihood/Impact (judgement) | Mitigation |
|---|---|---|---|
| R-01 | No consenting businesses (B-01) | High/High | Outreach day 1; test lines; label role-play |
| R-02 | Trial plan limits (verified numbers only) block real shops (B-02) | Medium/High | Verify numbers per Bolna's process or upgrade; decide at G1 |
| R-03 | Caller ID/default number unusable or low pickup in India (B-03) | Medium/High | Spike S-4; connect one Bolna-supported Indian provider |
| R-04 | Unknown rules/deadline (B-04) | Certain/Medium | Ask organisers now; treat 2026-11-20 as outer bound |
| R-05 | Compliance uncertainty (B-05) | Medium/High | Consent-only; disclose; low volume |
| R-06 | Agent speech quality/language on real shop calls | Medium/High | Rehearse with test lines; tune prompt; language A-10 |
| R-07 | Extraction field shape differs from docs (conflicting pages) | High/Medium | Capture real payloads S-6/S-7; contract fixtures |
| R-08 | Webhook lost / not retried / unsigned | Medium/Medium | Verify-by-pull + reconciler |
| R-09 | Duplicate dial after crash | Low/High | `DISPATCH_UNKNOWN`, no auto-retry |
| R-10 | Wallet runs out mid-demo | Medium/High | Pre-fund, budget cap, `balance-low` handling, Tier-3 fallback |
| R-11 | Demo shop doesn't pick up on the day | High/Medium | Several targets, test lines, graceful partials as a feature |
| R-12 | Time (≈ 27 days from today to the finale; deadline unknown) | High/High | Critical path first (M1), P1/P2 cut line |
| R-13 | Overbuilding frontend before call works | Medium/High | Phase gating: no frontend work before M1 |
| R-14 | Wave 2 scope creep starves the MVP | High/High | D-031: nothing before M1; every feature behind a flag; Build Map cut line orders Wave 2 items |
| R-15 | Prior ordering becomes a rich-get-richer loop that starves reliable-but-unlucky shops | Medium/Medium | Exploration epsilon (§48.3); `prior_snapshot` audit; measure coverage loss in paired `THOROUGH` runs |
| R-16 | Stop rule hides the nearest or cheapest shop | Medium/Medium | Honest "not called" wording; `THOROUGH` is one click; coverage-loss metric (§54.2) |
| R-17 | Listen-live or audio replay used on a party who did not consent | Low/Very high | Default `demo_audio_consent = false`; audio only for flagged lines; disclosure line; no storage (D-037) |
| R-18 | Inbound line abused (spoofed caller, fake stock, spam) | Medium/Medium | Quarantine unmatched callers, per-day cap, short TTL, distinct label, never outranks live calls (§50.1) |
| R-19 | Digest leaks that a particular user searched for something | Low/High | k-anonymity floor, structured item names only, no identifiers, live traffic only (NFR-16) |
| R-20 | Shops do not value the digest, so consent does not improve | Medium/High | Test the claim cheaply first (A-24, T13.2, n/N); keep test-line fallback (D-003) |
| R-21 | Browser speech support for Hindi or Kannada is poor on the demo machine | Medium/Low | S-14 before relying on it; the controls hide when unsupported; English fallback |
| R-22 | A model-based compiler is manipulated by hostile text | Low/Medium | Output re-validated by `StructuredFormParser`; user confirms; one call; no tool access (§53.1) |

### 40.1 Unresolved questions
See §45.3.

## 41. Roadmap after MVP (all DEFERRED)
Additional categories via config; permitted directory source; business onboarding page and consent management; merchant-side callback ("I have it now") *(promoted to Wave 2: §50)*; SSE/WebSocket; map; LLM query parsing; follow-up calls on user request; per-business reliability history; multilingual tuning (Sarvam via Bolna); proper user accounts; analytics.

## 42. Glossary
**Attempt** one call to one business. **Business kind** real vs team test line. **Doorbell** a webhook treated only as a hint to pull. **Execution** Bolna's record of a call (`execution_id`). **Evidence excerpt** transcript snippet backing a claim. **Reported** said by the business, unverified. **Stale** older than the field TTL. **Test line** team member phone role-playing a shop. **Verify-by-pull** fetch the authoritative record yourself.

## 43. Decision log

| ID | Decision | Rationale | Alternatives | Revisit when |
|---|---|---|---|---|
| D-001 | Bolna for voice orchestration | Bundled pipeline, API, webhooks, extraction; buildathon host | self-host Bolna OSS; other platform | G1 fails |
| D-002 | No direct telephony integration; use Bolna's route; at most one provider | simplicity | Plivo/Exotel direct | B-03 unresolved |
| D-003 | Vertical chosen by consent at G0 | B-01 | fix pharmacy | — |
| D-004 | Consenting businesses only | legal/ethical uncertainty | broader | compliance resolved |
| D-005 | Verify-by-pull; webhook is a doorbell | no documented signatures | trust body + IP list | Bolna documents HMAC |
| D-006 | Postgres as queue, single process | no extra infra | Redis/Celery | > 1 worker needed |
| D-007 | Polling for UI | simple, testable | SSE/WS | P1 |
| D-008 | SQLAlchemy 2 + Alembic; text+CHECK enums | maintainable | raw SQL; PG enums | — |
| D-009 | Shared access key + capability UUIDs, no accounts | MVP scope | full auth | public launch |
| D-010 | Provider `retry_config` disabled; Sonar owns retries | defaults too slow, need state-machine control | provider retries | — |
| D-011 | Use Bolna's bundled STT/LLM/TTS | no duplication | Deepgram/Sarvam/Cartesia direct | accuracy poor |
| D-012 | No second LLM for extraction in MVP *(extraction and validation stay LLM-free; one query-compiler call is allowed by D-039)* | determinism, simplicity | LLM validator | rejection rate high |
| D-013 | Structured-form parser P0; LLM parser deferred *(amended by D-039: compiler is P2 and always feeds the same parser)* | reliability | LLM-first | demo stiff |
| D-014 | Curated directory only | terms unverified, consent | maps API | scale |
| D-015 | Haversine, no PostGIS | tiny dataset | PostGIS | > thousands rows |
| D-016 | Lexicographic ranking, no numeric score | honesty | weighted score | metrics support it |
| D-017 | Agent built in dashboard, code only calls `/call` | minimal unknowns | `POST /v2/agent` | reproducibility need |
| D-018 | pytest/ruff/vitest/Playwright | standard | alternatives | — |
| D-019 | Hosting chosen in Phase 10 | after local works | — | — |
| D-020 | Env var names are ours | avoid pretending provider names | — | — |
| D-021 | No audio fetch/storage; excerpt-only evidence *(narrowly amended by D-037: on-demand playback for flagged lines; still no storage; evidence context window ≤ 1500 chars)* | privacy | store recordings | consent + need |
| D-022 | Simulator results never enter live cache *(extended: simulated attempts never update `business_stats` or the digest)* | integrity | — | — |
| D-023 | *(reconstructed v2.1)* Bolna-first production path that works with every optional provider disabled | reliability; stated in v1.1 §2 | sponsor-first stack | never |
| D-024 | *(reconstructed v2.1)* A sponsor appears only as an agent variant on test lines or in the Sponsor Lab; one real call is never routed through several providers | honesty; stated in v1.1 §2 | multi-provider live path | S-8 shows Bolna defaults are inadequate |
| D-025 | *(reconstructed v2.1)* If B-07 cannot be resolved, use a documentation-backed comparison plus Bolna's own route; no direct Plivo/Exotel integration | stated in v1.1 B-07 | direct telephony | B-03 unresolved |
| D-026 | *(reconstructed v2.1)* Integration-status vocabulary and D0…D4 depths (§0.1) are the only way to describe a sponsor integration | stated in v1.1 §0.1 | informal wording | — |
| D-027 | *(v2.1 proposal)* Sponsor Lab is a P2 offline harness, last in the cut order | keeps scope honest | build now | after M3 and spare capacity |
| D-028 | *(v2.1 proposal)* If an Indic-language upgrade is needed, evaluate Sarvam first, through Bolna's agent configuration | fits D-011 and the event's Indic context | other vendor first | S-8 result |
| D-029 | *(v2.1 proposal)* The pitch names a sponsor only at the depth reached (§22.1 claims rule) | WP-20 | logo wall | — |
| D-030 | *(v2.1 proposal)* No access means `NOT_MEASURED`; numbers are never copied from vendor material | WP-9 | fill from docs | — |
| D-031 | **Two waves.** Wave 1 = v1.1 MVP; Wave 2 (Part II) starts only after M1; docs and test-line spikes exempt; every Wave 2 feature behind a flag | protects the critical path (R-13, R-14) | one big scope | M1 reached and cut-line reviewed |
| D-032 | **Stop rule + prior ordering** in `FAST` mode (K=2 distinct exact confirmations; negatives never stop; `THOROUGH` available) | fewer calls, less shop nuisance, lower cost, novel | call everyone | coverage loss is high (§54.2) |
| D-033 | **Priors order calls only.** They never create, upgrade, hide or imply an answer; shown as `HISTORY` with n | honesty (WP-9) | blend into the score | — |
| D-034 | **Shop value first:** demand digest with k-anonymity, live traffic only, capability page, no new messaging provider | addresses B-01 | cold consent only | A-24 test fails |
| D-035 | **Inbound shop line** writes `shop_updates` (not `business_responses`); caller match is a soft check; quarantine unmatched; distinct label; never outranks live calls | integrity of call-attributable data | merge into responses | S-12 fails (then DEFERRED) |
| D-036 | **Voice in/out is client-side** (browser speech); speech reads only templated strings | no new provider; V12 preserved | server STT/TTS | S-14 shows poor support |
| D-037 | **Listen-live tiers** (ticker → audio replay → live audio if exposed); audio never stored; flagged lines only; disclosure line added | demo impact without consent risk | store recordings | A-20…A-22 resolved |
| D-038 | **SVG radar instead of map tiles** | no map or geocoding dependency (D-014, D-015) | map library | users need real maps |
| D-039 | **Question compiler = P2**, one LLM call behind an interface, output re-validated, user confirms | generality without weakening the safety floor | LLM-first parsing | ≥ 30 labelled queries pass (A-26) |
| D-040 | **Ground-truth study as a first-class measurement**; report n/N and inconclusives only | credibility; WP-9 | trust vendor confidence | — |
| D-041 | **Race clock** shows a comparison only with a dated, measured manual baseline | WP-20 | assumed average | — |
| D-042 | **Watches and `/api/v1/ask` are P2**; schema reserved now | L3/L5 story without MVP risk | build now | after Wave 2 |
| D-044 | **Sync SQLAlchemy 2 + psycopg3** (not async); FastAPI endpoints are plain `def`; background loops use threads/`to_thread` | simplest correct option for a single-process MVP; real Postgres in tests; concurrency proven by the `claim_next` race test | async SQLAlchemy | the orchestrator needs many concurrent in-flight calls (then move DB work off the event loop) |
| D-045 | **Local DB port 55432** (compose default); two native PostgreSQL servers already use 5432 and 5433 on the dev machine | stop tests silently hitting the wrong server | 5432 | the dev machine changes |
| D-043 | **Business model is hypotheses**, each with a cheapest test (§47) | honesty with YC audience | assert market size | customer discovery done |

## 44. Source links and research notes

Fetched/read 2026-10-24:
- Event page: https://www.bolna.ai/symphony
- Make call (API reference): https://www.bolna.ai/docs/api-reference/calls/make.md
- API quickstart: https://www.bolna.ai/docs/quickstarts/api.md
- Call flow & statuses: https://www.bolna.ai/docs/concepts/call-flow.md
- Webhooks: https://www.bolna.ai/docs/polling-call-status-webhooks.md
- Extractions: https://www.bolna.ai/docs/migrating-to-extractions/extraction.md and https://www.bolna.ai/docs/migrating-to-extractions/agent-extraction.md
- Execution logs: https://www.bolna.ai/docs/api-reference/executions/get_execution_raw_logs
- Concurrency: https://www.bolna.ai/docs/pricing/outbound-calling-concurrency.md
- Costs: https://www.bolna.ai/docs/get-started/what-it-costs.md
- Telephony providers: https://www.bolna.ai/docs/supported-telephony-providers.md
- Changelog (Oct 2026): https://www.bolna.ai/docs/changelog/october-2026.md
- Docs index: https://www.bolna.ai/docs/llms.txt
- TRAI commentary (secondary source): https://www.barandbench.com/view-point/trais-crackdown-on-spam-calls-and-ai-driven-telemarketing

Provided in the handoff but **not read** (fetch blocked or out of scope): the Bolna GitHub repo, Plivo, Exotel, Sarvam, Deepgram and Cartesia documentation, the Bolna `poll-call-data` URL as given (the equivalent webhook page was read at the `polling-call-status-webhooks` URL).

Research notes: pages we could not find — a dedicated Get-Execution reference page, a stop-call endpoint, an API rate-limit page, webhook signature docs, webhook retry docs, an "Errors & Status Codes" page (named but not fetched). These are carried as A-11, A-12, A-15, A-06 and S-tasks.

## 45. Register of assumptions, verified facts, and unknowns

### 45.1 VERIFIED (2026-10-24)
`POST /call` shape and fields; `GET /executions/{id}`; status list and transition order; webhook configuration, source IPs, "payload matches Get Execution"; `call-disconnected` payload fields are still null/0; extractions concept (pre-defined/free text, `objective`/`subjective`, `confidence`); trial concurrency 2 and verified-numbers-only; paid starts at 10; over-limit calls queue; telephony providers list; flat-rate voice-AI pricing model (no figures); event dates, venue, ₹1.2 lakh, YC interview, Plivo as buildathon partner.

### 45.2 ASSUMPTIONS (how to confirm)
| ID | Assumption | Confirm via |
|---|---|---|
| A-01 | Split ₹50k/40k/30k | event page/organisers |
| A-02 | Other sponsors listed (Exotel, Sarvam, Cartesia, Deepgram) | event page |
| A-03 | We can create an account/key and fund a wallet in time | S-1 |
| A-04 | A call to a team phone works on trial with number verification | S-4 |
| A-05 | Default `from` number works for Indian recipients | S-4 |
| A-06 | Bolna delivers configured custom webhook headers | S-5 |
| A-07 | Bolna redelivers on non-2xx | S-5 (return 500 once, observe) |
| A-08 | Extraction fields we need can be defined with pre-defined values + free-text quote | S-7 |
| A-09 | `user_data` variables are referenced in the prompt with a specific placeholder syntax | S-2 |
| A-10 | Hindi/English quality is adequate for shopkeepers | S-8 |
| A-11 | `POST /call` has no idempotency key | S-3 / docs |
| A-12 | No stop-call endpoint (cancel is dispatch-level only) | docs index re-check, S-3 |
| A-13 | TTL values are sensible | rehearsal data |
| A-14 | Bolna retention/recording controls | S-9 |
| A-15 | No documented API rate limit; unknown 429 behaviour | S-10 |
| A-16 | Submission = repo + demo + pitch (unknown) | B-04 |
| A-17 | A public tunnel is available to the team | S-3 |
| A-18 | Webhook payload includes `execution_id` and `status` top-level (must, if "matches Get Execution") | S-5 |
| A-19 | Bolna supports an inbound agent on a number we can obtain, and the inbound payload carries the caller number | S-12 |
| A-20 | Get Execution or a webhook exposes a partial transcript during `in-progress` | S-13 |
| A-21 | `recording_url` exists and is playable for a test-line call | S-13, S-9 |
| A-22 | Bolna offers live call monitoring or an audio stream (**UNVERIFIED**) | S-13 |
| A-23 | The demo browser's speech recognition and synthesis support English, Hindi and Kannada well enough | S-14 |
| A-24 | A demand digest raises shop consent compared with the plain script | T13.2 outreach test, n/N |
| A-25 | Prior ordering reduces calls versus distance ordering without a material coverage loss | simulator, then live paired runs |
| A-26 | One LLM call compiles free text to a valid `ParsedQuery` on ≥ 30 labelled queries | T18.1 |
| A-27 | Target payers and pricing unit in §47 (H-1, H-2) match what real buyers say | T13.2 customer discovery |

### 45.3 UNKNOWNS / open questions
Judging criteria; submission format/deadline; credits; eligibility; Bolna trial credit amount; whether paid plan is needed for non-verified numbers; exact execution JSON; which statuses carry `extracted_data`; DLT/caller-ID rules; recording defaults; compliance answers (§31); any consenting business.

### 45.4 BLOCKERS: see §0.2.

---

# PART II — WAVE 2: DIFFERENTIATORS (added in v2.0)

Part II adds the capabilities that turn Sonar from a reliable stock checker into a product with a story: **fewer calls for better answers, a reason for shops to say yes, a live experience judges remember, and numbers we can defend.** It does not change any Part I contract. Where Part II touches a Part I rule it says so, and the decision log (§43) records the amendment.

**Scope discipline (D-031).** Wave 1 = everything in §1–§45 (the v1.0 MVP). Wave 2 = this Part. **No Wave 2 code starts before milestone M1** (Build Map §0.4 rule 4 still governs). Documentation tasks and test-line-only spikes (S-12, S-13, S-14) may run at any time because they touch no real business.

Tags: Wave 2 items are P1 unless marked P2. Every Wave 2 behaviour is optional at runtime: with all Wave 2 flags off, the system behaves exactly like v1.1 (this is tested, NFR-15).

---

## 46. Product ladder and positioning

Sonar's thesis is unchanged: **search the real world by calling it.** The ladder says where that goes, so the pitch is a platform story and the MVP stays a single rung.

| Level | Name | What the user gets | Status |
|---|---|---|---|
| L1 | Stock check | "Does anyone near me have exactly this, now?" | **MVP (Wave 1)** |
| L2 | Capacity and quote | "Can you fix / supply / deliver this today, and for how much?" | Same engine; new category config (Wave 1 supports it by configuration, §23.4) |
| L3 | Standing watch | "Tell me when anyone reports this in stock." | P2, schema reserved (§53) |
| L4 | Shop line | Shopkeepers update their own stock by phone | Wave 2 (§50) |
| L5 | Phone-as-API | `POST /api/v1/ask` returns structured, timestamped answers from businesses that have no API | P2 (§53) |

One-line positioning: *"Sonar turns phone calls into a queryable, time-stamped, evidence-backed database of the offline world."*

## 47. Business model and hypotheses (HYPOTHESES, none measured)

Nothing here is a market claim. Each row is a hypothesis with the cheapest test that would confirm or kill it. The pitch (§37) may state a hypothesis only as a hypothesis.

| # | Hypothesis | Cheapest test | Tag |
|---|---|---|---|
| H-1 | **Who pays:** businesses that need real-time store-level facts and have no API to get them: e-pharmacies and quick-commerce (stock verification), distributors (shelf and price audits), insurers and hospitals (slot and bed checks), field-service marketplaces (capacity). Consumers use Sonar free. | 3 customer-discovery conversations (T13.2); record who said they would pay and for what | ASSUMPTION A-27 |
| H-2 | **Pricing unit:** per answered query (a validated `REPORTED_*` response), not per call attempted. | Compute measured cost per useful result (§39) and compare with what interviewees say a manual check costs them | ASSUMPTION A-27 |
| H-3 | **Moat:** (a) a freshness-stamped dataset of offline reality, (b) per-shop priors learned from every call (§48), (c) a two-sided network because shops get value back (§49, §50). | After ≥ 30 live calls, show that priors reorder targets and reduce calls (A-25) | ASSUMPTION A-25 |
| H-4 | **Why now:** voice agents can hold a natural call at usable latency and cost; Indic speech models handle code-switching. | Rehearsal evidence only (S-8); no external claim | ASSUMPTION A-10 |
| H-5 | **Shops opt in when given value.** A weekly demand digest is worth more to a shop than an unexplained call. | Outreach A/B: ask 10 shops with the old script and 10 with the digest script; record yes/no n/N (A-24) | ASSUMPTION A-24 |

Rules: no TAM numbers, no "X% faster", no revenue projections unless sourced and shown. If H-1 gets zero positive interviews, say so in `docs/BUSINESS_CASE.md` and re-frame the pitch around the impact story.

## 48. Active information gathering (stop rule) and the shop learning loop

**Problem.** v1.0 calls every selected shop. That is wasteful, annoying to shopkeepers, and it makes cost grow linearly with targets.

**Idea.** Call shops in the order most likely to give a useful answer, and **stop as soon as the user has enough.** The demo line is "Sonar called 3 of 12 shops and stopped", and it must be literally true and visibly labelled.

### 48.1 Search mode
`SearchMode ∈ {FAST, THOROUGH}`, default `FAST`.
- `THOROUGH` = v1.0 behaviour: call every selected target.
- `FAST` = prior-ordered dispatch with early stop.
The user can always choose `THOROUGH` ("ask everyone").

### 48.2 Stop rule (FR-37, pure function, D-032)
```
StopRule(K=2, min_distinct=K, require_fresh=true)
satisfied(responses) :=
  count of distinct businesses whose response is
    VALID, data_origin = LIVE_CALL (or fresh CACHED_LIVE),
    availability = REPORTED_AVAILABLE, exact_match = CONFIRMED,
    evidence_validated = true, required_fields non-null
  >= K
```
- When satisfied, all `PENDING` attempts of the job (not yet dispatched) become `CANCELLED` with `failure_reason = 'STOP_RULE_SATISFIED'` and `jobs.stopped_early = true`, `jobs.calls_avoided = n`. In-flight calls are not interrupted (no stop-call endpoint, A-12) and their results are recorded.
- **A negative never stops the search.** `REPORTED_UNAVAILABLE`, `UNCERTAIN`, no-answer do not count toward `K`. Stopping early on "no" would hide possible yeses.
- Simulated responses never satisfy the rule in a live job; in `demo_mode` they can, and the banner stays.
- If fewer than `K` positives exist, the job runs through every target and ends like v1.0.

### 48.3 Prior scoring and dispatch order (FR-38, D-032, D-033)
`PriorScorer` is a pure function that returns, per business, `priority_score ∈ [0,1]` plus a snapshot of its inputs:
- Inputs from `business_stats` (§48.5): connection rate in the current hour bucket, rate of positive validated answers for the same `category`, recency, mean call duration.
- Cold start (fewer than `PRIOR_MIN_OBSERVATIONS` attempts): neutral prior, distance breaks ties.
- **Exploration.** With probability `PRIOR_EXPLORATION_EPSILON` (default 0.15) a lower-ranked shop is promoted, so a shop that had one bad day is not buried forever. This is required (R-15), not optional.
- Dispatch happens in waves of at most `MAX_CONCURRENT_CALLS`, highest score first; the stop rule is evaluated after every finalised response.
- Priors only **order** calls. They never create, upgrade or hide an answer (D-033).

### 48.4 Not called is not unavailable (FR-40, NFR-09 extended)
`ResultState` gains `NOT_CALLED_STOP_RULE`. Copy: *"Not called: enough shops had already confirmed. This does not mean it is unavailable."* The copy-lint test (T9.5) is extended so this state may never contain "unavailable" or "out of stock" as a claim.

### 48.5 `business_stats` (learning loop, FR-38, FR-39)
Updated by the finalizer (and by the reconciler) on every terminal attempt, in the same transaction as the attempt update:
`attempts`, `connected`, `completed`, `no_answer`, `reported_available`, `reported_unavailable`, `uncertain`, `declined`, `total_duration_seconds`, `hour_bucket_stats` (jsonb, 24 buckets of `{attempts, connected}` in IST), `language_counts` (jsonb), `last_attempt_at`.
- **History display (FR-39).** A result card may show *"Reported available in 9 of its last 10 answered calls (history, not today's confirmation)"*. It is labelled `HISTORY`, shown only when ≥ 5 answered calls exist (else hidden), never replaces the live answer, never changes the result state, and never appears on a card whose live answer is absent.
- **Learned call window.** A suggestion shown to the operator only (`best_call_window` stays hand-set and consent-bound; the learned window never overrides what a business agreed to).
- Simulated attempts never update `business_stats` (extends D-022).

### 48.6 Metrics
`calls_avoided ÷ planned` (stop-rule saving), `useful_results_per_call`, and coverage loss (searches where the stop rule stopped but a later shop would have been the nearest or cheapest, measured only in `THOROUGH` rehearsals). Report n.

## 49. Giving shops a reason to say yes: the demand digest

**Problem.** B-01 (no consenting businesses) is the project's largest risk, and "please let a robot call you" is a weak ask.

**Offer.** Each consenting shop gets a weekly **demand digest**: *"This week, 12 searches near you asked for [item class]. 3 shops reported having it. You were one of them."* This is real information a small shop cannot get elsewhere.

### 49.1 Rules (FR-41, FR-42, NFR-16, D-034)
- Built only from **live** searches (`demo_mode = false`, `data_origin = LIVE_CALL`); simulated and test-line traffic are excluded.
- **k-anonymity:** a count is shown only if ≥ `DIGEST_MIN_K` (default 3) distinct searches contribute; otherwise the line is suppressed. No user identifiers are ever present; no free-text queries are shown, only the structured item name and category.
- Delivery for the MVP is a **capability page** `GET /api/shop/{digest_token}/digest` (unguessable token, rotateable, no phone number on the page) that the team shares by whatever channel the shop already uses. No SMS/WhatsApp provider is integrated (non-goal §7.2).
- The consent script (T13.3) leads with the digest, states plainly that calls are by an AI assistant, may be transcribed, and how to opt out. `businesses.digest_opt_in` is separate from call consent.
- The digest page carries an **opt-out button** that sets `OPTED_OUT` (same effect as saying it on a call).

## 50. The shop line (inbound agent)

**Idea.** Let shopkeepers call **Sonar** and say what they have: *"We just got paracetamol 500, ten strips, twenty rupees each."* This uses Bolna's inbound side, keeps the dataset fresh without outbound calls, and is a second demo moment.

**Status of the capability: UNVERIFIED (A-19, B-09).** We have not read Bolna's inbound documentation or confirmed an inbound-capable number. Spike **S-12** decides. If S-12 fails, this section stays DEFERRED and nothing else depends on it.

### 50.1 Data model and trust (FR-43, FR-44, FR-45, D-035)
- New table `shop_updates` (§19.4). New `DataOrigin` value `SHOP_SELF_REPORT`. Self-reports **never** enter `business_responses` (that table stays call-attributable).
- **Caller match is a soft signal, not authentication.** Caller ID can be spoofed. The inbound webhook (authenticated like the outbound one, D-005, and verified by pull) compares the caller number to the business's registered number:
  - match → `ACCEPTED`
  - no match, unknown number → `QUARANTINED` (stored, never displayed, reviewable by CLI)
  - business `OPTED_OUT` or caller asks to stop → `REJECTED`
- The same deterministic rules as §23.3 apply (evidence excerpt must appear in the transcript; numeric price must appear; unknown stays null). Rate limit: `SHOP_UPDATE_MAX_PER_DAY` per business.
- **TTL** for self-reports is shorter than for live calls (`SHOP_UPDATE_TTL_HOURS`, default 12) because nobody re-verifies them.
- **Display.** Always labelled *"Self-reported by the shop at HH:MM"*, with a distinct badge from *"Reported by phone to Sonar's assistant"*. Ranking: a fresh self-report ranks with, and after, an equally fresh live call at the same tier; it never outranks a live call (§24.3 extended in T16.6).
- A self-report that **contradicts** a live answer from the last hour is shown as a contradiction (flag `SELF_REPORT_CONTRADICTS_CALL`), the same way V9 handles contradictions. No silent choice.

## 51. Live experience: transcript ticker, listen-live, evidence replay

The strongest demo moment is hearing or seeing the agent talk to a real person as it happens. The capability depends on what Bolna exposes (A-20, A-21, A-22), so it ships in tiers and each tier has a fallback.

| Tier | What | Depends on | Consent rule |
|---|---|---|---|
| T-1 | **Live transcript ticker.** The latest lines of the conversation update while the call is `IN_PROGRESS`. | Bolna returning a partial transcript during `in-progress` (A-20, S-13) | Real businesses: only if `demo_audio_consent`; test lines: always |
| T-2 | **Audio replay** of a finished call in the UI, streamed from the provider URL on demand, **never stored by Sonar** | `recording_url` exists and is playable (A-21, S-9, S-13) | Test lines and `demo_audio_consent` businesses only (FR-47, P2) |
| T-3 | **True live audio** into the room | Bolna exposing live monitoring (A-22, UNVERIFIED) | Same as T-2; announced before the call starts |

Rules (D-037, amends D-021): audio is never fetched in bulk, never written to disk or DB; the backend returns a short-lived redirect or proxied stream per request, only for flagged businesses; the opening disclosure for flagged lines adds *"this call may be shown to an audience."* `businesses.demo_audio_consent` is set only with a recorded note. The default for every real business is `false`.

**Ticker (FR-46, NFR-19).** `GET /api/searches/{id}/live` returns, per in-call attempt, the last `LIVE_TICKER_LINES` (default 6) transcript lines, each ≤ 200 chars, text only, HTML-escaped on render, with `updated_at`. Hidden for non-flagged real businesses.

**Evidence replay (FR-52).** The result card's evidence panel shows a bounded **context window** (`evidence_context`, ≤ 1500 chars around the validated quote) with the quote highlighted. This slightly widens D-021's excerpt-only rule and is covered by retention (NFR-13): `evidence_context` is purged with the transcript excerpt. Where `evidence_context` is absent, fall back to the 600-char excerpt.

## 52. Voice front door and the radar view

### 52.1 Voice in, voice out (FR-48, FR-49, NFR-18, D-036)
- **Voice in.** The browser's speech recognition (Web Speech API) fills the search form: the user speaks, the UI shows the recognised text and the parsed fields, and **never auto-submits**; the user confirms. Languages follow the demo browser's support (A-23, S-14). Client-side only: no audio leaves the browser through Sonar and no provider key is involved.
- **Voice out.** When results land, the UI reads a summary using the browser's speech synthesis. **The spoken text is exactly the templated `answer_summary` strings and the ranking explanation** (V12): the test asserts that the spoken string equals the rendered text. No free prose is generated for speech.
- Both are progressive enhancements. If the browser lacks support, the controls are hidden and nothing else changes.

### 52.2 Radar view (FR-50, D-038)
A pure SVG view: the user at the centre, concentric rings at 1/2/3 km, each business as a pin at its bearing and distance (computed with the existing haversine helper plus a bearing function). A ping animation emanates from the centre when the search starts; pins pulse while ringing, fill when answered, and show the same text labels as the list (status is never colour-only, NFR-12). **No map tiles, no geocoding, no third-party map dependency** (supersedes the "map" item in FR-36 for the MVP).

### 52.3 Race clock (FR-51, D-041)
A timeline of the parallel calls with the search's elapsed time. It may display a comparison ("calling these by hand took the team about N minutes") **only** when `docs/BASELINE_MANUAL.md` exists with the date, the number of shops, the method and who measured it. Without that file the comparison is not rendered.

### 52.4 Trust ledger (FR-53)
A panel listing every shop Sonar **declined to make a claim about** and why, using validation flags and states in plain language: *"Shop C hedged ('maybe, let me check'), so it is shown as Uncertain."*, *"Shop D was not called: enough shops had confirmed."*, *"Shop E did not answer."* It is generated from `validation_flags` and `result_state`, not from free text.

## 53. Platform surfaces (P2)

### 53.1 Question compiler (FR-55, D-039)
Free text becomes a `ParsedQuery` candidate: *"is anyone near Indiranagar open with the iPhone 13 screen today?"* → category, item/problem, attributes, location label, radius. **Safety floor unchanged:** the candidate is passed through the same `StructuredFormParser` validation, category config, blocked-terms check and charset whitelist (§23.2); the model never writes `user_data`, never decides eligibility, and its output is shown to the user for confirmation. Exactly one LLM call per query, behind a `QueryCompiler` interface with the structured form as the fallback. Accuracy target: measured on ≥ 30 labelled queries before it is enabled (A-26). This amends D-012 and D-013: still no LLM in extraction or validation.

### 53.2 Standing watches (FR-56)
`watches` table (§19.4): a parsed query, a capability token, cadence (`WATCH_MIN_INTERVAL_MINUTES`, floor 120), `max_polls`, `expires_at`, last state. A watch re-runs the normal search path (consent, caps, budgets all apply); a state change (nothing → reported available) shows on the watch page. No push channel is integrated in the MVP. Watches count against the per-business daily cap (§27) so they cannot become spam.

### 53.3 Phone-as-API (FR-57)
`POST /api/v1/ask` is a thin wrapper over `POST /api/searches` that returns the same ranked results with `origin`, `answer_timestamp`, `freshness`, evidence references, and `stopped_early`. It exists to make L5 demonstrable in one request. It inherits every guardrail; there is no path that bypasses consent, caps or labelling.

## 54. Measurement: the credibility experiment

Part I measures engineering health. Part II adds the numbers a sceptical reviewer would ask for.

### 54.1 Ground-truth study (FR-54, D-040)
For each reviewed live response the team independently establishes reality (visit, ask the shop in person, or a second human call) and records `ground_truth_checks(response_id, checked_at, checker, method, outcome ∈ {AGREE, DISAGREE, INCONCLUSIVE}, note)`.
- Reported as **agreement n/N**, plus the count of `INCONCLUSIVE`; never a bare percentage, never extrapolated.
- A `DISAGREE` on a `REPORTED_AVAILABLE` is the most important failure to publish; it must be listed in `docs/LIMITATIONS.md`.

### 54.2 New metric rows (extends §39)
| Metric | Definition | Denominator |
|---|---|---|
| Ground-truth agreement | `AGREE` ÷ (`AGREE` + `DISAGREE`) | checked live responses (report n and inconclusive count) |
| Stop-rule saving | Σ `calls_avoided` ÷ Σ `planned_targets` in `FAST` live searches | `FAST` live searches |
| Coverage loss | `FAST` searches whose nearest/cheapest answer was among uncalled shops in a paired `THOROUGH` run ÷ paired searches | paired rehearsals |
| Manual baseline | median minutes for the team to answer the same query by hand | measured trials (report n) |
| Digest consent rate | shops that agreed with the digest script ÷ shops asked | outreach attempts (report n) |
| Self-report quarantine rate | `QUARANTINED` ÷ received updates | inbound updates |

## 55. Wave 2 acceptance criteria

- **AC-11** In the simulator, a `FAST` search stops early once `K` distinct exact confirmations exist; remaining targets show `NOT_CALLED_STOP_RULE`; `THOROUGH` runs all; a negative or uncertain answer never triggers a stop.
- **AC-12** With all Wave 2 flags off, the full Part I acceptance suite (AC-1…AC-10) passes unchanged (NFR-15).
- **AC-13** A self-reported update from an unmatched number is quarantined and never rendered; a matched one renders with the distinct label and the shorter TTL (only if S-12 passed).
- **AC-14** The text the browser speaks equals the rendered `answer_summary` for every `ResultState` fixture (NFR-18).
- **AC-15** A digest line is suppressed when fewer than `DIGEST_MIN_K` searches contribute; digest data contains no user identifiers and no demo/simulated traffic.
- **AC-16** `docs/METRICS.md` reports ground-truth agreement as n/N with the inconclusive count, or states "not measured".

## 56. Wave 2 environment variables (extends §36)

| Variable | Default | Meaning |
|---|---|---|
| `STOP_RULE_K` | 2 | Distinct exact confirmations needed to stop (`FAST`) |
| `PRIOR_MIN_OBSERVATIONS` | 5 | Attempts before a shop's prior is used |
| `PRIOR_EXPLORATION_EPSILON` | 0.15 | Chance a lower-ranked shop is promoted |
| `HISTORY_MIN_ANSWERED` | 5 | Answered calls needed before history is displayed |
| `DIGEST_MIN_K` | 3 | Minimum contributing searches for a digest count |
| `SHOP_UPDATE_MAX_PER_DAY` | 6 | Accepted self-reports per business per day |
| `SHOP_UPDATE_TTL_HOURS` | 12 | Freshness window for self-reports |
| `LIVE_TICKER_LINES` | 6 | Lines returned per in-call attempt |
| `WATCH_MIN_INTERVAL_MINUTES` | 120 | Floor for watch cadence |
| `BOLNA_AGENT_ID_INBOUND` | — | Inbound shop-line agent (only if S-12 passes) |
| `FEATURE_STOP_RULE`, `FEATURE_HISTORY`, `FEATURE_DIGEST`, `FEATURE_SHOP_LINE`, `FEATURE_LIVE_TICKER`, `FEATURE_AUDIO_REPLAY`, `FEATURE_VOICE_UI`, `FEATURE_COMPILER`, `FEATURE_WATCHES` | `false` | Each Wave 2 capability is off until enabled (NFR-15) |

### 19.4 Schema additions for Wave 2 (additive migrations `0002`…; Part I tables are unchanged except for the added columns)

```sql
-- search_jobs / call_attempts
ALTER TABLE search_jobs   ADD COLUMN mode text NOT NULL DEFAULT 'FAST' CHECK (mode IN ('FAST','THOROUGH'));
ALTER TABLE search_jobs   ADD COLUMN stop_rule jsonb;               -- {"k":2,...} snapshot
ALTER TABLE search_jobs   ADD COLUMN stopped_early boolean NOT NULL DEFAULT false;
ALTER TABLE search_jobs   ADD COLUMN calls_avoided int NOT NULL DEFAULT 0;
ALTER TABLE call_attempts ADD COLUMN priority_score numeric(5,4);
ALTER TABLE call_attempts ADD COLUMN prior_snapshot jsonb;          -- inputs used, for audit

-- businesses
ALTER TABLE businesses ADD COLUMN demo_audio_consent boolean NOT NULL DEFAULT false;
ALTER TABLE businesses ADD COLUMN digest_opt_in boolean NOT NULL DEFAULT false;
ALTER TABLE businesses ADD COLUMN digest_token text UNIQUE;
ALTER TABLE businesses ADD COLUMN inbound_enabled boolean NOT NULL DEFAULT false;
-- evidence context on responses
ALTER TABLE business_responses ADD COLUMN evidence_context text CHECK (char_length(evidence_context) <= 1500);

CREATE TABLE business_stats (
  business_id            uuid PRIMARY KEY REFERENCES businesses(id) ON DELETE CASCADE,
  attempts               int NOT NULL DEFAULT 0,
  connected              int NOT NULL DEFAULT 0,
  completed              int NOT NULL DEFAULT 0,
  no_answer              int NOT NULL DEFAULT 0,
  reported_available     int NOT NULL DEFAULT 0,
  reported_unavailable   int NOT NULL DEFAULT 0,
  uncertain              int NOT NULL DEFAULT 0,
  declined               int NOT NULL DEFAULT 0,
  total_duration_seconds int NOT NULL DEFAULT 0,
  hour_bucket_stats      jsonb NOT NULL DEFAULT '{}',   -- IST hour -> {attempts, connected}
  language_counts        jsonb NOT NULL DEFAULT '{}',
  last_attempt_at        timestamptz,
  updated_at             timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE shop_updates (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  business_id      uuid REFERENCES businesses(id),          -- null while unmatched
  provider         text NOT NULL,
  provider_call_id text NOT NULL,
  status           text NOT NULL CHECK (status IN ('ACCEPTED','QUARANTINED','REJECTED','EXPIRED')),
  caller_match     boolean NOT NULL,
  item_name        text,
  attributes       jsonb NOT NULL DEFAULT '{}',
  availability     text CHECK (availability IN ('REPORTED_AVAILABLE','REPORTED_UNAVAILABLE','UNCERTAIN')),
  price_amount     numeric(12,2),
  price_currency   text,
  quantity_reported int,
  evidence_excerpt text,
  evidence_validated boolean NOT NULL DEFAULT false,
  validation_flags text[] NOT NULL DEFAULT '{}',
  answer_timestamp timestamptz NOT NULL,
  expires_at       timestamptz NOT NULL,
  created_at       timestamptz NOT NULL DEFAULT now(),
  UNIQUE (provider, provider_call_id)
);

CREATE TABLE ground_truth_checks (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  response_id  uuid NOT NULL REFERENCES business_responses(id) ON DELETE CASCADE,
  checked_at   timestamptz NOT NULL DEFAULT now(),
  checker      text NOT NULL,
  method       text NOT NULL CHECK (method IN ('IN_PERSON','SECOND_CALL','OTHER')),
  outcome      text NOT NULL CHECK (outcome IN ('AGREE','DISAGREE','INCONCLUSIVE')),
  note         text,
  UNIQUE (response_id, checker)
);

CREATE TABLE watches (                                    -- P2, reserved
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  token        text NOT NULL UNIQUE,
  parsed_query jsonb NOT NULL,
  interval_minutes int NOT NULL CHECK (interval_minutes >= 120),
  max_polls    int NOT NULL CHECK (max_polls BETWEEN 1 AND 24),
  polls_done   int NOT NULL DEFAULT 0,
  last_state   text,
  expires_at   timestamptz NOT NULL,
  created_at   timestamptz NOT NULL DEFAULT now()
);
```

**Enum additions** (identical in code, DB, API, UI; the Build Map's enum-parity test covers them): `SearchMode {FAST, THOROUGH}`; `ResultState` += `NOT_CALLED_STOP_RULE`; `DataOrigin` += `SHOP_SELF_REPORT`; `UpdateStatus {ACCEPTED, QUARANTINED, REJECTED, EXPIRED}`; `GroundTruthOutcome {AGREE, DISAGREE, INCONCLUSIVE}`; `ErrorClass` unchanged.

### 20.5 API additions for Wave 2
- `POST /api/searches` gains optional `mode` (`FAST` default, `THOROUGH`).
- `GET /api/searches/{id}` gains `stopped_early`, `calls_avoided`, `mode`.
- `GET /api/searches/{id}/results` result items gain `source` (`LIVE_CALL`/`CACHED_LIVE`/`SHOP_SELF_REPORT`/`SIMULATED`), optional `history` (`{answered, reported_available, label: "HISTORY"}`), and `priority_rank` (explanatory only).
- `GET /api/searches/{id}/live` (FR-46) → per in-call attempt `{attempt_id, lines[], updated_at}`; 404 when the flag is off; hidden for non-flagged real businesses.
- `GET /api/searches/{id}/attempts/{attempt_id}/audio` (FR-47, P2) → short-lived redirect or proxied stream; 403 unless `demo_audio_consent` or `TEAM_TEST_LINE`.
- `GET /api/shop/{digest_token}/digest`; `POST /api/shop/{digest_token}/opt-out` (FR-41).
- `POST /api/webhooks/bolna-inbound/{secret_token}` (FR-43, only if S-12 passes).
- `POST /api/query/compile` (FR-55, P2): `{text}` → `ParsedQuery` candidate or `Clarification`/`Refusal`; never creates a job.
- `POST /api/watches`, `GET /api/watches/{token}` (FR-56, P2). `POST /api/v1/ask` (FR-57, P2).

---

## Part II — spike items (cross-referenced from the Build Map)

| Spike | Question | Resolves |
|---|---|---|
| S-12 | Does Bolna support an inbound agent on a number we can obtain, and what does the inbound webhook/execution payload look like (caller number field)? | A-19, B-09 |
| S-13 | During `in-progress`, does Get Execution (or a webhook) return a partial transcript, and how fresh is it? Is `recording_url` playable for a test-line call, and is there any live-monitoring feature? | A-20, A-21, A-22 |
| S-14 | Which languages does the demo browser's speech recognition and synthesis support well enough for the demo (English, Hindi, Kannada)? | A-23 |

### 45.5 Wave 2 status summary
Nothing in Part II is VERIFIED. Every Wave 2 capability that depends on Bolna behaviour (inbound, partial transcript, recording playability, live monitoring) is an ASSUMPTION until its spike runs. The stop rule, learning loop, digest, radar, trust ledger, ground-truth study, and race clock depend only on data Sonar already holds and can be built and tested with the simulator.
