# CLAUDE.md: Sonar (Bolna Buildathon 2026)

Context for Claude Code. Written 2026-10-28. Facts here were checked against the repo at commit
`bda295d` (local `main`, 13 commits ahead of `origin/main` at `b5df3ea`). If this file and the code
disagree, the code wins; fix this file.

## Sources of truth (read before changing anything substantial)

- `SONAR_BIBLE_v2.md`: the *what* and *why*: requirements (FR/NFR), decisions (§43, D-001…D-062),
  assumptions and verified facts (§45), validator rules V1–V14 (§23.3).
- `SONAR_BUILD_MAP_v2.md`: the *order*: phases, task IDs (T0.1…T20.x), gates G1a/G1, milestones
  M1/M2/M3, Definition of Done (§0.2), gating rules (§0.4), cut line (§4).
- `docs/FEASIBILITY.md`: what real Bolna calls actually showed (overrides the Bible's assumptions).
- `docs/LIMITATIONS.md`: what is and is not proven. Keep every claim consistent with it.
- `HANDOFF_PROMPT.md` (if present) is **stale**: it predates the frontend, the Bolna provider and
  the first live calls. Use this file instead.

## What Sonar is

"Search the real world by calling it." A user asks for an item near a location (e.g. Paracetamol
500 mg). Sonar picks up to N nearby shops **that have consented**, phones them with a Bolna voice
agent that says it is an AI, extracts structured answers, validates them deterministically against
the transcript, and shows what each shop *reported*, with a quote and a time. It reports; it never
guarantees.

## Rules that are never broken

1. **Consent first.** No live call to a business without recorded consent (`CONSENTED` with
   `consent_recorded_at`, or `TEAM_TEST_LINE`). Consent is re-checked before every dial. The AI never
   asks shops for permission (D-061); shops opt in themselves or a person records their yes.
2. **Silence is never "unavailable".** No answer, failed, declined, uncertain, skipped and not-joined
   never read as "unavailable"/"out of stock". Copy tests enforce this (backend and frontend).
3. **Never trust a webhook body** (D-005). A webhook is a doorbell; the finalizer pulls
   `GET /executions/{id}` before writing any result.
4. **Evidence or nothing.** A yes needs the shop's own words in the transcript; prices must be heard;
   unknown stays unknown. When in doubt the validator says Uncertain.
5. **Label honesty.** `data_origin` is `LIVE_CALL`, `CACHED_LIVE` or `SIMULATED`; simulated results
   carry a permanent banner and a per-card tag; test lines say "Team test line (role-play)".
6. **A duplicate call is worse than a missed one.** Uncertain dispatches become `DISPATCH_UNKNOWN`
   and are never auto-retried (D-048).
7. **No secrets or real numbers in git.** `.env`, `data/businesses.local.yaml` and
   `spikes/bolna/captures/` are git-ignored. Tests use dummy numbers `+91 00000xxxxx` or the
   allow-listed `9876543210`; `scripts/check_no_secrets.py` fails otherwise.
8. **Simplicity** (D-006): no Redis, Celery, Kafka, vector DB, PostGIS, second LLM or second
   telephony provider. New dependencies need a decision-log entry.
9. **No claims without measurement.** Numbers go in only with n/N; `scripts/check_claims.py` lints
   the business docs.

## Stack and layout

- Backend: Python 3.11+ (dev machine has 3.14), FastAPI with **sync** SQLAlchemy 2 + psycopg3
  (D-044, endpoints are plain `def`), Alembic, PostgreSQL 16 as datastore **and** job queue.
- Postgres runs in Docker on **port 55432** (D-045; native servers use 5432/5433 on this machine).
- Frontend: React 19 + TypeScript + Vite + Tailwind 4, Leaflet/OpenStreetMap map, Vitest.
- Voice: Bolna (`app/providers/bolna.py`) behind a `VoiceProvider` protocol, plus
  `SimulatedVoiceProvider` for demo mode.
- `backend/app/{api,domain,db,providers,services}`, `backend/alembic/versions` (0001–0005),
  `backend/tests/{unit,integration,live,fixtures}`, `frontend/src`, `e2e/` (Playwright),
  `config/categories.yaml` (categories are data), `scripts/`, `spikes/bolna/`, `docs/`.

## Commands (Windows, PowerShell, from the repo root; `make` has the same targets elsewhere)

```powershell
.\tasks.ps1 setup          # venv + deps
.\tasks.ps1 check          # ruff lint + format check + unit tests + secret scan + claims scan
.\tasks.ps1 db-up          # Postgres on 55432 (Docker Desktop must be running)
cd backend; .\.venv\Scripts\alembic upgrade head; cd ..
.\tasks.ps1 test-int       # database tests
.\tasks.ps1 check-wave2    # full suite with every FEATURE_* flag on (NFR-15)
.\tasks.ps1 run            # API on :8000
npm --prefix frontend install; npm --prefix frontend test; npm --prefix frontend run build
npm --prefix frontend run dev   # web app on :5173 (proxies /api to :8000)
.\tasks.ps1 e2e            # Playwright, needs API + web running and SONAR_ACCESS_KEY set
powershell -ExecutionPolicy Bypass -File .\verify_all.ps1   # runs all of the above, logs to verify_log.txt
backend\.venv\Scripts\python scripts\seed_businesses.py data\businesses.example.yaml
```

## Where the project stands (2026-10-28)

**Checkpoint: past Gate G1a, before G1 and milestone M1.**

- 4 real Bolna calls to team phones on 2026-10-25, placed with the spike scripts (not through the
  app). They showed: the call path works; extractions arrive nested as
  `extracted_data.sonar.<field>` with `objective`/`subjective` (parser fixed); STT heard "500
  milligrams" as "millie gills"; voicemail detection hung up on a quiet person; trial plan calls
  verified numbers only; cost looks like 3.0 per started 30 s (unit unconfirmed). Details:
  `docs/FEASIBILITY.md`, `docs/IMPROVEMENTS.md` §0.
- **Not yet done:** webhooks received from Bolna (spikes S-3, S-5), the G1 decision (S-11), and
  **M1: one real call through the whole app** (search → orchestrator → Bolna → webhook → finalizer
  pull → validator → `/results`). Steps and evidence template: `docs/M1_EVIDENCE.md`; opt-in live
  test: `backend/tests/live/test_m1_live.py` (`RUN_LIVE=1`, `-m live`).
- The build ran ahead of the plan's gates (frontend and Wave 2 before M1). Known deviation; the
  priority now is M1, not new features.

### Built (all tests written; see "Verification status")

Phases 0–6 (backend pipeline, validator, Bolna provider, simulator, webhooks, reconciler), Phase 8
(frontend: search form, live progress, results with evidence, map and radar, trust ledger,
read-aloud), much of 9–10 tooling (secret/claims/bundle/prod-env checkers, retention, review and
ground-truth CLIs, Docker image), Phase 12 docs. Wave 2 behind flags: stop rule + shop history
(T14), digest page (T16.1–16.2), radar, trust ledger, read-aloud.

Added 2026-10-27/28 (commits `6f6b0d9`…`bda295d`):
- **Validator** (D-055): an exact-match "no" followed by the shop reaffirming ("yes we have it") is
  Uncertain (`CONTRADICTORY`, `SHOP_REAFFIRMED_AT_END`); an alternative must be in the shop's own
  lines (`ALTERNATIVE_NOT_IN_TRANSCRIPT`). Regression test from the real call in `test_validator.py`.
- **T7.4 cache reuse** (`FEATURE_CACHE_REUSE`, D-057): a shop's fresh live answer to the same
  question is shown as `CACHED_LIVE` ("Earlier call, HH:MM") instead of a new call. Migration 0004.
- **T8.8** Playwright journey test in `e2e/` (demo mode, desktop and phone).
- **T15.1/15.2 live ticker** (`FEATURE_LIVE_TICKER`, D-058): `GET /api/searches/{id}/live`, only for
  test lines and simulated calls; the simulator reveals its script line by line.
- **Plan tiers** (D-060): `plan` = FREE 3 km/5 shops, PLUS 6 km/8, PRO 10 km/10. Demo setting, not
  billing. `app/services/plans.py`, mirrored in `frontend/src/api.ts` `PLANS`.
- **OpenStreetMap discovery** (`FEATURE_DISCOVERY`, D-059): `POST /api/businesses/discover` (access
  key) queries Overpass with `osm_tags` from `config/categories.yaml`; found shops are stored as
  `REAL_BUSINESS`/`INVITED` and **never called**; consent decisions are never overwritten.
  `GET /api/businesses/nearby` lists known shops for the map (never phone numbers). Migration 0005.
- **Shop self opt-in** (`FEATURE_OPT_IN`, D-061): `scripts/invite_shop.py` makes a single-use 14-day
  invite link (hash stored only); the shop agrees on `/join/{token}` and becomes `CONSENTED`
  (`consent_source = SELF_OPT_IN`) with a private `/stop/{token}` link that works even with the
  flag off. Public `/join` only records a request; `scripts/approve_opt_in.py` after a human checks
  the number.
- **Map** (`frontend/src/pins.ts`, `ResultsMap.tsx`): every nearby shop with its state ("Said yes",
  "Said no", "Not sure", "No answer", "Not called", "Joined Sonar, not called this time", "Not
  joined yet (never called)"), legend with counts and filters, list view; plan selector in the form.
- Docs: `docs/agent/ACCEPTANCE_CALLS.md` (12-call script), `docs/agent/VOICE_AND_TRANSCRIBER.md`
  (D-056), `docs/OUTREACH_KIT.md`, `docs/EXTERNAL_ITEMS.md`, `docs/M1_EVIDENCE.md`,
  `docs/M2_EVIDENCE.md`, updated LIMITATIONS/FEASIBILITY/METRICS/SPONSORS/OPERATIONS/CONSENT_SCRIPT.

### Verification status (important)

The 2026-10-27/28 work was written in an environment without PyPI or npm, so for a while only the
stdlib-only backend unit tests, ruff and the secret/claims scans had ever run.

**Run on 2026-10-28 (venv and node_modules are now fully installed, Python 3.12.10):**

- `tasks.ps1 check`: 660 backend unit tests passed; ruff lint + format clean; secret and claims
  scans clean.
- Migrations 0001→0005 applied clean against Postgres on 55432.
- `tasks.ps1 test-int`: 221 integration tests passed, after the three fixes below.
- Frontend: 125 Vitest tests passed; `tsc -b && vite build` clean.
- API and web both boot (`/health` → ok, `/health/ready` → ready; Vite on 5173).

Three things had to be fixed to get there:

1. **Real bug, `services/orchestrator.py` `drain()`.** It looped forever. `asyncio.gather` over
   tasks that are already finished returns without yielding to the event loop, so the
   `add_done_callback` that removes them from `_tasks` never got to run and `while self._tasks`
   never became false. This is why the integration suite had never completed — it hung, it did not
   fail. It would also have hung graceful shutdown in production. Fixed by removing the batch from
   `_tasks` before awaiting it.
2. **Stale test, `test_constraints.py`.** It asserted `CACHED_LIVE` can never be stored, but T7.4
   (D-057) deliberately stores it and migration 0004 permits it. Split into one test that it is
   accepted and one that a bogus origin is still rejected.
3. **Stale test, `test_cache_reuse.py::test_a_newer_unclear_answer_blocks_an_older_clear_one`.** It
   put the newer answer 10 minutes back, inside `business_cooldown_minutes` (15), so the shop was
   dropped as a candidate and zero attempts were planned. Moved to 20 minutes: past the cooldown,
   still inside the 60-minute availability TTL.

Still never run: `check-wave2` (all `FEATURE_*` flags on) and the Playwright e2e suite.

### Deliberately not built / deferred

Race clock (T15.4), evidence replay (T15.5), voice input (T15.7), audio replay (T15.9), inbound shop
line (T16.3–16.6), question compiler, watches, `/api/v1/ask` (T18), sponsor annex (Phase 19). A UI
button for discovery (API exists). Hindi opt-in page (needs a native speaker review; no machine
translation of consent text).

### Custom questions (D-062, commit `dd0f5fa`) — NOT on this branch

**Status (checked 2026-10-28): `dd0f5fa` is a dangling commit on no branch.** Its parent is
`bda295d`, so it is a sibling of `b14e5fd`, not an ancestor of `claude/build-map-and-map-feature`.
None of the files below exist here: no `services/general.py`, no `QuestionBuilder.tsx`, no
`docs/agent/prompt_general_v1.md`, and `alembic/versions` stops at 0005. The only thing on this
branch that mentions `FEATURE_CUSTOM_QUESTIONS` is this file. The work is preserved in
`claude-work.bundle` (`refs/heads/main` → `dd0f5fa`) and must be cherry-picked or merged before any
of the description below is true. Until then, treat this section as a plan, not as built code.

Sonar is not only for stock checks. Behind `FEATURE_CUSTOM_QUESTIONS` a search can carry up to 5
questions the user writes ("Are you open until 12 midnight tonight?", "What is the price per
hour?"), each yes/no, number or text; a yes/no can say which answer is needed and one number can
rank shops lowest/highest first. Flow: `services/query.py` (`_checked_questions`, safety checks,
keys `q1..`) → `build_user_data` (`questions_text`, `questions_kinds`, `business_kind`, `topic`)
→ the **general** Bolna agent `BOLNA_AGENT_ID_GENERAL` ("Sonar General" in the dashboard, prompt in
`docs/agent/prompt_general_v1.md`) → extraction `answers_json` → `services/general.py`
(quote must be in the shop's own lines, yes/no not contradicted, number heard) → `business_responses.answers`
and `rank_value` (migration 0006) → `results.sort_results` ranks by the chosen number. UI:
`QuestionBuilder.tsx`, the answers table in `Results.tsx`, and map labels "Meets what you asked" /
"Doesn't meet what you asked" / "Unclear answer" with the best shop marked. Such searches always
ask every shop and never reuse cached answers. Only tested on the simulator so far.

### Bolna account state (read-only probe, 2026-10-28)

`BOLNA_API_KEY` authenticates (`GET /v2/agent/all` → 200). Two agents exist and both resolve:

| Agent | Id | Wired to |
| --- | --- | --- |
| Sonar Pharmacy | `fd8901b8-…405f` | `BOLNA_AGENT_ID_PHARMACY` |
| Sonar General | `74b6f306-…c93b3d` | `BOLNA_AGENT_ID_COMPUTER_REPAIR` |

Three things still block M1 — none of them are code:

1. **`webhook_url` on the pharmacy agent is `None`.** Nothing will call back into the app, so the
   finalizer never runs. Needs the tunnel from step 3 below.
2. **`BOLNA_AGENT_ID_COMPUTER_REPAIR` points at "Sonar General".** That is the D-062 general agent,
   which has a different prompt and different extractions. Since D-062 is not on this branch there
   is no `BOLNA_AGENT_ID_GENERAL` setting for it to live in, so a `computer_repair` search would
   dial a shop with the wrong prompt. Either leave the slot empty or build a real computer-repair
   agent before using that category.
3. **`BOLNA_FROM_PHONE_NUMBER` is empty**, and the agent has no `inbound_phone_number`.

The agent's voice, transcriber, call settings and the 11 extraction names were not checked against
`docs/agent/prompt_v1.md` yet — that is the next read-only probe.

## What to do next, in order

1. Run `verify_all.ps1`; fix failures. Push branch `claude/build-map-and-map-feature`, open a PR.
2. **Bolna agent** (user's own account, trial, $5 wallet seen on 2026-10-28): welcome message and
   prompt from `docs/agent/prompt_v1.md` (§1a, §2); call settings (§1: 120 s max, 10 s silence
   hang-up, retries off, voicemail detection off); the 11 extractions with exact names (§3,
   `price_currency_stated` free text); voice Sarvam `bulbul:v3` `en` (lower voice e.g. shubh/rahul,
   speed 0.9–1.0); transcriber Sarvam `saaras:v4` `en` with keywords (Deepgram is the comparison
   arm). Sarvam/Deepgram are chosen *inside* Bolna; no partner API keys are needed. Verify team
   phones in Bolna (trial). Put `BOLNA_API_KEY`, `BOLNA_AGENT_ID_PHARMACY` in `.env`.
3. **S-3/S-5**: tunnel (cloudflared or ngrok) + `spikes/bolna/webhook_capture.py`, webhook URL
   `https://<host>/api/webhooks/bolna/<WEBHOOK_SECRET_TOKEN>` on the agent; 3 calls (answered,
   ring-out, hang-up mid-sentence) + the acceptance calls; fill FEASIBILITY S-3, S-5, S-8.
4. **S-11 G1 decision**, then **M1** (`docs/M1_EVIDENCE.md`: four runs). Then apply the cut line.
5. Deploy (Phase 10), rehearse 3× (`docs/REHEARSAL_LOG.md`), backup recording, clean-clone run,
   submission (`docs/SUBMISSION.md`). **Deadline unconfirmed**: `docs/SUBMISSION.md` says 31 Oct
   2026 from a fetch of the event page; confirm with the organisers. Finale 20 Nov.

## Conventions

- Commit messages start with the Build Map task ID (`T7.4: ...`); one topic per commit.
- A changed rule or fact gets a Bible decision-log row (§43) or register update (§45) in the same
  commit. Amend, never delete. Next free decision id: **D-062**.
- Every feature is behind a `FEATURE_*` flag, default off; with all flags off the Part I suite must
  pass unchanged.
- Pure logic in modules that import only stdlib/pydantic, with unit tests; anything touching the DB
  gets an integration test against real Postgres (never a DB mock).
- Copy: plain words, never claim unavailability without an explicit "no"; every new validation
  flag needs text in `frontend/src/copy.ts` `FLAG_TEXT`.
- Phone numbers are masked in logs (last 3 digits); no number ever leaves a public API.

## People and accounts

- Team repo: `github.com/aadamaftabpersonal-boop/SONAR_AI` (owner Aadam). This clone belongs to
  Russel (russelgandhi@gmail.com); push access to the repo may need to be granted.
- Bolna: the user is setting up an agent in their own account; the 2026-10-25 calls used Aadam's.
- Credits requested 2026-10-27: Bolna +$15, Sarvam $10, Deepgram $10 (status unknown).
