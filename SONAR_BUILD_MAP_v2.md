# SONAR BUILD MAP

**Execution plan for Sonar — Bolna Buildathon 2026.** Written 2026-10-24. **v2.0** adds **Wave 2** (Phases S2, 13–18, milestones M2 and M3, appended after §5).
**Companion:** `SONAR_BIBLE_v2.md` (the *what* and *why*).

> **v2.0 change log.** (1) Wave 2 phases appended, with their own traceability table; Phases 0–12 and §3–§5 are unchanged except for the additions marked *(Wave 2)*. (2) New gating rule 6 (§0.4). (3) Cut line extended (§4). (4) Acceptance checklist extended (§3). (5) Task IDs: S-12…S-14, T13.x…T18.x. (6) **Not changed on purpose:** the schedule and deadline logic (§0.5, T12.1, T12.6). (7) **v2.1:** the Bible's dangling sponsor references are now resolved in compact form (Bible §22.1, D-023…D-030). This file gains **Phase 19 (optional sponsor annex, P2, deferred)** with SP-1 and T19.1; the plan stays Bolna-only and Phase 19 can never block M1, M2 or M3. This file is the *order and the checks*. IDs (`FR-*`, `NFR-*`, `D-*`, `A-*`, `B-*`, `WP-*`, `S-*`) are shared with the Bible. Enum names, API paths and table names here are copied from the Bible; if they differ, fix both in one commit.

Status tags are the same as in the Bible: **VERIFIED / ASSUMPTION / BLOCKER / DECISION / DEFERRED**. Every task below says which of these it depends on and which it resolves.

---

## 0. How to use this plan

### 0.1 Priorities
- **P0** — needed for a functioning end-to-end MVP.
- **P1** — strengthens the demo; cut first when time runs short.
- **P2** — future; never blocks submission.

### 0.2 Baseline Definition of Done (applies to every task that changes code)
A task is done only when **all** are true, in addition to its own "Done when":
1. The tests listed in the task exist and pass (`make test`).
2. `make check` (ruff lint + format check + all unit tests) is green.
3. No new dependency outside the approved list (§1.3) unless a decision-log entry (Bible §43) was added.
4. No secret, real phone number or real transcript committed (`git diff --cached` reviewed).
5. If the task changed a fact in the Bible (a VERIFIED/ASSUMPTION), the Bible register (§45) was updated in the same commit.
6. Commit message starts with the task ID, e.g. `T6.3: finalizer pulls execution and validates`.

### 0.3 Task template (fields every task has)
`ID · Priority · Purpose · Prerequisites · Actions · Files · Interfaces/schemas · Commands · Tests · Acceptance · Verification checkpoint · Done when · Depends on · Risks · Blocks?`
Where a field would only repeat the baseline, it says "baseline".

### 0.4 Hard gating rules (these encode the five mistakes to avoid)
1. **Spike before integration.** No code that calls Bolna is written (T5.3, T6.x) until gate **G1** passes. Provider facts come from captured real payloads (S-5, S-6), not from this document. (WP-4)
2. **Consent before calls.** No live call to anyone who has not consented; before any real shop is called, `participation_status` and `consent_recorded_at` are set. (B-01, D-004)
3. **Simplicity.** No Redis/Celery/Kafka/vector DB/PostGIS/second LLM/extra telephony. (D-006, D-011, D-012, D-015)
4. **One real call before any frontend.** Phase 8 does not start until milestone **M1** (a real consenting/test-line call travels the whole pipeline and is readable via the API/curl). (R-13)
5. **No generic tasks.** Every task has tests and a "Done when"; "build the backend" is not a task.
6. **Wave 2 is gated and flagged.** *(Wave 2)* No code from Phases 14–18 before **M1**. Documents (Phase 13) and test-line spikes (S-12…S-14) are exempt. Every Wave 2 feature is behind a `FEATURE_*` flag, default off; with all flags off the Part I suite must pass unchanged (NFR-15). Wave 2 may never weaken a Part I invariant: consent checks, verify-by-pull, label honesty, simulation labelling.

### 0.5 Time handling
No per-task time estimates (they would be invented). Instead:
- **Checkpoint rule:** when M1 is reached, compute the days left to the verified submission deadline (B-04) — or to the outer bound **2026-11-20** if still unknown — and cut P1 items that do not fit. Record the cut in the Bible decision log.
- Today is 2026-10-24; the finale is 2026-11-20 (VERIFIED). Order below is dependency order, shaped so M1 comes as early as external blockers allow.

---

## 1. Conventions

### 1.1 Repository layout (target)
```
.
├── SONAR_BIBLE.md  SONAR_BUILD_MAP.md  README.md
├── Makefile  docker-compose.yml  .env.example  .gitignore
├── backend/
│   ├── pyproject.toml  alembic.ini
│   ├── alembic/versions/
│   ├── app/
│   │   ├── main.py  config.py  logging_setup.py
│   │   ├── api/        (searches.py webhooks.py health.py businesses.py deps.py errors.py)
│   │   ├── domain/     (enums.py schemas.py transitions.py)
│   │   ├── db/         (models.py session.py repositories.py)
│   │   ├── services/   (query.py directory.py selector.py orchestrator.py finalizer.py
│   │   │                validator.py freshness.py ranking.py reconciler.py retention.py)
│   │   └── providers/  (base.py bolna.py simulated.py)
│   └── tests/ {unit, integration, e2e, fixtures/bolna}
├── frontend/           (created in Phase 8)
├── config/             categories.yaml  blocked_pharmacy_terms.txt
├── data/               businesses.example.yaml   (businesses.local.yaml is git-ignored)
├── docs/               FEASIBILITY.md  agent/prompt_v1.md  DEMO_SCRIPT.md  OPERATIONS.md
├── spikes/bolna/       throwaway scripts (httpx only)
└── scripts/            seed, delete_business_data, review CLI
```
*(Wave 2 additions)* `backend/app/services/{stats.py priors.py stoprule.py digest.py shop_updates.py compiler.py}` · `backend/app/api/{shop.py live.py watches.py ask.py}` · `frontend/src/components/{Radar.tsx RaceClock.tsx Ticker.tsx TrustLedger.tsx VoiceControls.tsx}` · `docs/{BUSINESS_CASE.md DISCOVERY_LOG.md BASELINE_MANUAL.md M2_EVIDENCE.md M3_EVIDENCE.md METRICS.md}` · `docs/agent/inbound_prompt_v1.md` · `scripts/{ground_truth.py check_claims.sh}`. New Makefile target: `make check-wave2` (Part I suite with all `FEATURE_*` flags on).

### 1.2 Makefile targets (created in T0.3)
`make setup` · `make db-up` · `make db-down` · `make migrate` · `make seed` · `make run` · `make test` · `make lint` · `make fmt` · `make check` · `make web-dev` (Phase 8) · `make e2e` (Phase 9).

### 1.3 Approved dependency list (MVP)
Backend: `fastapi`, `uvicorn`, `pydantic`, `pydantic-settings`, `sqlalchemy>=2`, `alembic`, `psycopg[binary]`, `httpx`, `pyyaml`, `structlog` (or stdlib JSON logging), `slowapi` (or small in-house limiter), dev: `pytest`, `pytest-asyncio`, `respx`, `ruff`, `pytest-cov`, `mypy` (P1). Frontend: `react`, `react-dom`, `typescript`, `vite`, `tailwindcss`, dev: `vitest`, `@testing-library/react`, `@playwright/test` (P1). Anything else → decision-log entry first.

### 1.4 Branching
`main` always green. One short branch per task (`t6-3-finalizer`). Squash-merge with the task ID in the title.

---

## 2. Critical path and external blockers

### 2.1 Critical path
`T0.7 (start long-lead items) → S-1 → S-3 → S-4 → S-5/S-6/S-7 → S-11 (G1) → T5.3 → T6.1–T6.6 → T6.7 (M1) → T8.x → T9.x → T10.x → T11.x → T12.x`
Provider-agnostic work (Phases 2–4, T5.1–T5.2) runs in parallel after **G1a** (S-1…S-4 passed: a real call was placed).

### 2.2 External blockers (must be actively worked, not waited on)

| Blocker | What unblocks it | Task | Needed before |
|---|---|---|---|
| B-01 consenting businesses | ≥ 3 businesses with recorded consent + ≥ 2 test lines | T0.7, T11.1 | M1 needs ≥ 1 test line; demo needs real businesses |
| B-02 Bolna account/plan | key, funded wallet, plan limits known; verified numbers per trial rules | S-1 | S-4 |
| B-03 caller-ID/number route | successful call from the chosen `from` number to a team phone | S-4 | G1 |
| B-04 rules/deadline | written answer from organisers or page; confirmed application | T0.7, T12.1 | cut-line decision at M1 |
| B-05 compliance | answers in Bible §31 as far as obtainable; consent-only stays | T0.7, T11.1 | any real-shop call |
| B-06 public HTTPS webhook | tunnel in dev; hosted URL later | S-3, T10.4 | S-5 |

---

## PHASE 0 — Repository reconnaissance and project setup

### T0.1 — Inspect the repository and record the baseline · P0
- **Purpose:** never assume an empty repo (the working directory inspected on 2026-10-24 held no project files and was **not a git repository**).
- **Prerequisites:** none.
- **Actions:** list files; `git status`, `git log`, `git remote -v`; look for `package.json`, `pyproject.toml`, `requirements*.txt`, `Dockerfile`, existing `README`. If the team's real repo is elsewhere, copy `SONAR_BIBLE.md` and `SONAR_BUILD_MAP.md` into its root. If no repo exists, `git init -b main`. Record findings in `docs/REPO_BASELINE.md` (what exists, what is reused, what is not).
- **Files:** `docs/REPO_BASELINE.md`.
- **Commands:** `git status; git log --oneline | head; ls -la; git remote -v`
- **Tests:** none (documentation task).
- **Acceptance:** baseline doc lists existing code and an explicit "reuse / ignore" decision per item.
- **Verification:** reviewer can tell from the doc what was already there.
- **Done when:** doc committed; repo is a git repo on `main` with the two spec files at root.
- **Depends on:** —  **Risks:** existing code conflicts with layout (then adapt §1.1, log a decision).  **Blocks:** T0.2.

### T0.2 — Pin toolchain versions and document them · P0
- **Purpose:** reproducible environments.
- **Prerequisites:** T0.1.
- **Actions:** detect installed Python/Node/Docker/Postgres client; **DECISION:** Python 3.12 and Node 22 LTS unless the machine/CI forces otherwise (record in Bible §43 if changed). Add `.python-version`, `.nvmrc`. Write setup steps to `README.md` (stub).
- **Files:** `.python-version`, `.nvmrc`, `README.md`.
- **Commands:** `python3 --version; node --version; docker --version; docker compose version`
- **Tests:** a `make doctor` target that fails with a clear message if a version is wrong.
- **Acceptance:** `make doctor` passes on a clean machine following README.
- **Verification:** run it.
- **Done when:** versions pinned, README stub lists prerequisites.
- **Depends on:** T0.1.  **Risks:** no Docker available → then a local Postgres install path is documented instead.  **Blocks:** T0.3.

### T0.3 — Backend scaffold with lint, format and test commands · P0
- **Purpose:** a green empty pipeline before any logic.
- **Prerequisites:** T0.2.
- **Actions:** create `backend/pyproject.toml` with approved deps; ruff config (line length 100, `I`, `E`, `F`, `B`, `UP`); pytest config (`asyncio_mode=auto`); `backend/app/main.py` with FastAPI app and `GET /health` returning `{"status":"ok"}`; Makefile targets (§1.2); `tests/unit/test_health.py`.
- **Files:** `backend/pyproject.toml`, `backend/app/main.py`, `backend/tests/unit/test_health.py`, `Makefile`.
- **Interfaces:** `GET /health` → `{"status":"ok"}`.
- **Commands:** `make setup && make check && make run` then `curl -s localhost:8000/health`
- **Tests:** health returns 200 and body.
- **Acceptance:** `make check` green; server starts.
- **Verification:** curl output matches.
- **Done when:** baseline + curl verified.
- **Depends on:** T0.2.  **Risks:** dependency resolution issues.  **Blocks:** T0.4, all backend tasks.

### T0.4 — Environment conventions, `.env.example`, secret hygiene · P0
- **Purpose:** secrets stay out of Git from the first commit (WP-6).
- **Prerequisites:** T0.3.
- **Actions:** write `backend/app/config.py` using `pydantic-settings` (all variables in Bible §36; `BOLNA_API_KEY` etc. optional in dev); create `.env.example` with placeholders only; `.gitignore` must include `.env`, `.env.*` (except `.env.example`), `data/businesses.local.yaml`, `*.pem`, `node_modules`, `.venv`, `__pycache__`, `spikes/**/captures/` (raw captures hold real data until redacted); add a pre-commit-style script `scripts/check_no_secrets.sh` that greps staged files for `BOLNA_API_KEY=` values, long hex/base64 tokens and `+91` followed by 10 digits outside `*.example.*`.
- **Files:** `backend/app/config.py`, `.env.example`, `.gitignore`, `scripts/check_no_secrets.sh`.
- **Interfaces:** `Settings` (typed; defaults from Bible §27.1).
- **Commands:** `make check` (extend to run the secret check), `git check-ignore -v .env data/businesses.local.yaml`
- **Tests:** `test_config_defaults_match_bible` (asserts §27.1 defaults); `test_secret_check_flags_fixture` (the script flags a planted fake key/number in a temp dir).
- **Acceptance:** defaults equal Bible §27.1; secret script fails on planted secret, passes on clean tree.
- **Verification:** run both cases.
- **Done when:** baseline + both tests pass.
- **Depends on:** T0.3.  **Risks:** false positives (tune patterns).  **Blocks:** S-1 (needs `.env` handling).

### T0.5 — Local PostgreSQL via Docker Compose · P0
- **Purpose:** same DB locally, in tests and in production (WP-3).
- **Prerequisites:** T0.3.
- **Actions:** `docker-compose.yml` with `postgres:15` (or 16), named volume, healthcheck, port 5432; two databases or schemas: `sonar` and `sonar_test`; `make db-up/db-down`; `DATABASE_URL` in `.env.example`.
- **Files:** `docker-compose.yml`, `Makefile`.
- **Commands:** `make db-up && docker compose exec db pg_isready`
- **Tests:** `tests/integration/test_db_connect.py` — connects, `SELECT 1`, and verifies `gen_random_uuid()` works.
- **Acceptance:** test passes against the compose DB.
- **Verification:** `make db-up && pytest tests/integration/test_db_connect.py`.
- **Done when:** baseline + test passes.
- **Depends on:** T0.3.  **Risks:** no Docker (fallback documented in T0.2).  **Blocks:** Phase 2.

### T0.6 — Development workflow doc · P1
- **Purpose:** agree how work is done.
- **Prerequisites:** T0.3.
- **Actions:** write `docs/WORKFLOW.md`: branch/commit rules, how to run tests, how fixtures are captured/redacted, where tags are updated, how to add a decision-log entry.
- **Files:** `docs/WORKFLOW.md`.  **Tests:** none.  **Acceptance:** doc covers the five topics.  **Done when:** merged.
- **Depends on:** T0.3.  **Risks:** none.  **Blocks:** no.

### T0.7 — Start the long-lead external items (do this first, in parallel) · P0
- **Purpose:** B-01, B-02, B-04, B-05 take calendar time that code cannot shorten.
- **Prerequisites:** none — start immediately.
- **Actions (checklist, owner + date per line in `docs/EXTERNAL_ITEMS.md`):**
  1. Confirm the team's buildathon application is submitted (event page has an "Apply now"); capture the confirmation.
  2. Ask the organisers (email/community channel named in the confirmation) for: submission format and deadline, judging criteria, credits entitlement, eligibility/team size. Record answers verbatim; update Bible §21.2 and B-04.
  3. Create the Bolna account; note plan, wallet, whether free credits exist (S-1 continues this).
  4. List 10+ candidate businesses (pharmacy **and** computer-repair/electronics). Ask each for consent; script: who we are, what the call is, that it is an AI assistant, that calls are transcribed, how to opt out, calling window, who to contact. Record consent per business (date, how, by whom) in `data/businesses.local.yaml` (git-ignored). Target ≥ 3 per category; stop at the first category with ≥ 3 (D-003).
  5. Collect ≥ 2 team phone numbers to act as `TEAM_TEST_LINE` shops (Bolna trial: verified numbers only, VERIFIED).
  6. Draft the compliance question list (Bible §31) and seek competent advice if available. Do not claim compliance.
- **Files:** `docs/EXTERNAL_ITEMS.md`, `data/businesses.local.yaml` (ignored).
- **Tests:** none.
- **Acceptance:** each of the six items has an owner and a status; consent records exist for every business that will ever be called.
- **Verification:** weekly review of `EXTERNAL_ITEMS.md` against gates.
- **Done when:** B-01 has ≥ 3 consented businesses **or** an explicit decision to demo with labelled test lines only (logged as D-0xx).
- **Depends on:** —  **Risks:** shops refuse/ignore (expected); organisers slow.  **Blocks:** M1 needs at least test lines; T11.1 needs the business list.

---

## PHASE 1 — API and provider feasibility spike (Bolna)

**Rules for the whole phase:** throwaway scripts in `spikes/bolna/` using plain `httpx`; no app code; every observation recorded in `docs/FEASIBILITY.md` with date and raw capture path; raw captures stay git-ignored until redacted. Calls go **only** to verified team phones (`TEAM_TEST_LINE`) in this phase. Keep each call ≤ 120 s. Stop after the first failure in a step and record it rather than working around it silently.

### S-1 — Account, API key, wallet, plan limits · P0 (resolves A-03, B-02)
- **Prerequisites:** T0.4.
- **Actions:** create account; create API key; put in local `.env` as `BOLNA_API_KEY`; record plan (trial/paid), wallet balance, concurrency shown in the dashboard; `GET`-style sanity call that is documented (e.g. list executions is **not** verified — use the dashboard to confirm key validity, or a harmless documented call); note whether trial requires phone verification and how to verify a number.
- **Files:** `docs/FEASIBILITY.md` (section S-1).
- **Commands:** `python spikes/bolna/s1_whoami.py` only if a documented read call is found; otherwise manual.
- **Tests:** manual checklist.
- **Acceptance:** key works for at least one authenticated request recorded in the doc; plan and limits written down.
- **Verification:** screenshot/notes in the doc with secrets redacted.
- **Done when:** B-02's status updated (resolved / needs upgrade / needs verified-number process).
- **Depends on:** T0.4.  **Risks:** account approval delay (escalate via T0.7).  **Blocks:** S-2…S-11.

### S-2 — Create the agent in the dashboard and test prompt variables · P0 (resolves A-09; D-017)
- **Prerequisites:** S-1.
- **Actions:** create one agent (dashboard Auto Build or manual) with the call script of Bible §25 (English first); set `call_terminate` (≈120) and `hangup_after_silence` (≈10) via the dashboard fields; define prompt placeholders for `item`, `attributes`, `required_fields`; determine the **exact placeholder syntax** and how `user_data` binds to it by a test call; save the final prompt to `docs/agent/prompt_v1.md`; note the agent id (UUID) in `.env` as `BOLNA_AGENT_ID_<CATEGORY>`.
- **Files:** `docs/agent/prompt_v1.md`, `docs/FEASIBILITY.md`.
- **Tests:** manual: dashboard test or S-4 call shows variables filled.
- **Acceptance:** documented placeholder syntax; agent id recorded.
- **Verification:** the first spoken question contains the substituted item.
- **Done when:** A-09 resolved in Bible §45.2.
- **Depends on:** S-1.  **Risks:** variable syntax differs (adjust prompt only).  **Blocks:** S-4.

### S-3 — Public webhook receiver and tunnel · P0 (resolves A-17, B-06; checks A-11, A-12)
- **Prerequisites:** S-1.
- **Actions:** write `spikes/bolna/webhook_capture.py` (tiny HTTP server; logs method, source IP, **all headers**, raw body, timestamp to `spikes/bolna/captures/`; configurable response code and a switch to return 500 once); expose it via an HTTPS tunnel (any tool; record which); configure the URL in the agent's Webhook Configuration; use "Send test" and confirm a sample `completed` payload arrives; re-read the Bolna docs index for a stop-call and idempotency mention; record result for A-11/A-12.
- **Files:** `spikes/bolna/webhook_capture.py`, `docs/FEASIBILITY.md`.
- **Commands:** `python spikes/bolna/webhook_capture.py --port 9000 --fail-once`
- **Tests:** manual.
- **Acceptance:** test payload received; headers/IP captured.
- **Verification:** capture file exists and contains source IP.
- **Done when:** B-06 status recorded.
- **Depends on:** S-1.  **Risks:** tunnel instability (note it; production needs a stable URL).  **Blocks:** S-5.

### S-4 — First real call to a verified test number · P0 (resolves A-04, A-05, B-03)
- **Prerequisites:** S-2, S-3; a team phone number verified in Bolna per the trial rules.
- **Actions:** `spikes/bolna/s4_make_call.py` posts `POST /call` with `agent_id`, `recipient_phone_number` (E.164), optional `from_phone_number`, `user_data`; **do not** set `retry_config` or `bypass_call_guardrails`; print the response (`status`, `execution_id`); answer the call as a shopkeeper (script: available/exact/price); end naturally.
- **Files:** `spikes/bolna/s4_make_call.py`, `docs/FEASIBILITY.md`.
- **Commands:** `python spikes/bolna/s4_make_call.py --to +91XXXXXXXXXX --item "…" `
- **Tests:** manual.
- **Acceptance:** `200 queued` + `execution_id` returned; phone rings; conversation proceeds; record caller number shown on the phone and whether the call was blocked/labelled spam.
- **Verification:** execution visible in the Bolna dashboard.
- **Done when:** **G1a passes** (a real call was placed). Provider-agnostic phases (2–4) may now start.
- **Depends on:** S-2, S-3.  **Risks:** B-02/B-03 (trial limits, number route); India caller-ID treatment unknown.  **Blocks:** G1a, S-5…S-10.

### S-5 — Capture webhook behaviour for a complete call · P0 (resolves A-06, A-07, A-18)
- **Prerequisites:** S-4.
- **Actions:** place 2–3 calls: (a) answered and completed, (b) not answered (let it ring out), (c) answered then hung up mid-sentence. Save every webhook (headers+body+IP+time). Record: set of statuses delivered, their order, duplicates, fields present at each status (esp. `call-disconnected` vs `completed`), whether `execution_id` and `status` are top-level fields (A-18), whether configured custom headers arrive (A-06), whether Bolna redelivers after a 500 (A-07; use `--fail-once` on one call), whether a webhook can arrive before our `POST /call` response is processed (compare timestamps).
- **Files:** `spikes/bolna/captures/` (ignored), then redacted copies to `backend/tests/fixtures/bolna/webhook_*.json`, `docs/FEASIBILITY.md`.
- **Tests:** redaction script `scripts/redact_fixture.py` + `test_redact_removes_numbers_and_recording_urls`.
- **Acceptance:** one redacted fixture per observed status; written conclusions for A-06, A-07, A-18.
- **Verification:** fixtures contain no real numbers or recording URLs (script test).
- **Done when:** fixtures committed; Bible A-06/A-07/A-18 updated.
- **Depends on:** S-4.  **Risks:** unsigned/unretried webhooks (already handled by D-005).  **Blocks:** T6.1, T6.2.

### S-6 — Capture the Get Execution payload · P0
- **Prerequisites:** S-4.
- **Actions:** `GET /executions/{execution_id}` after each call from S-5 and also **during** `in-progress` and at `call-disconnected` and `completed`; save bodies; compare to the matching webhook body; document field names/types for `status`, `transcript` (string or structured? speaker labels?), `conversation_duration`, `total_cost` (+ currency?), `extracted_data`, `telephony_data` (esp. `recording_url`), timestamps, any error field; record response for an unknown id and for a wrong key (error shapes and status codes).
- **Files:** `backend/tests/fixtures/bolna/execution_*.json` (redacted), `docs/FEASIBILITY.md` (field table).
- **Tests:** none yet (T5.3 and T6.3 consume the fixtures).
- **Acceptance:** field table complete; both error shapes recorded; confirmation of whether webhook body == execution body.
- **Verification:** two people read the table and agree.
- **Done when:** Bible §21.3 "exact JSON field names" caveat replaced by the real table (move to VERIFIED).
- **Depends on:** S-4.  **Risks:** transcript lacks speaker labels (affects V3 matching — design around it).  **Blocks:** T5.3, T6.3, T6.4.

### S-7 — Configure and capture extractions · P0 (resolves A-08)
- **Prerequisites:** S-6.
- **Actions:** in the agent's Extractions tab define the fields in Bible §23.4 — `availability` (pre-defined: `available|not_available|unsure|declined`), `exact_match_confirmed` (`yes|no|unsure`), `alternative_offered` (free text), `price_amount` (number), `price_currency_stated` (free text/pre-defined), `quantity_available` (number), `wait_time_minutes` (number), `open_now` (boolean-ish), `opt_out_requested` (`yes|no`), `call_outcome` (`human|voicemail|ivr|wrong_number`), `supporting_quote` (free text). Re-run calls; record the exact JSON shape of `extracted_data` (nested vs flat — docs conflict), whether `confidence` appears per field, which statuses populate it, behaviour when a field was never discussed, and whether `supporting_quote` is reliably a verbatim substring of the transcript.
- **Files:** `backend/tests/fixtures/bolna/execution_extracted_*.json`, `docs/FEASIBILITY.md`.
- **Tests:** none (consumed by T6.4).
- **Acceptance:** the shape is documented; the verbatim-substring rate of `supporting_quote` over ≥ 5 calls is recorded **as n/N**, not a percentage claim.
- **Verification:** the fixture parses with the Pydantic model written in T5.1.
- **Done when:** A-08 resolved; if `supporting_quote` is unreliable, switch V3 to a transcript keyword check (log a decision).
- **Depends on:** S-6.  **Risks:** Dispositions API needed for programmatic setup (not needed — dashboard only).  **Blocks:** T6.4.

### S-8 — Language and accent trial · P0 (resolves A-10)
- **Prerequisites:** S-4.
- **Actions:** run scripted calls in English and Hindi/English mix with teammates doing natural, fast, noisy, interrupting shopkeeper speech; note STT errors on product names/numbers; test `agent_data.language` if the agent is multilingual (VERIFIED field; do not combine with `voice_id`).
- **Files:** `docs/FEASIBILITY.md` (table of cases and outcomes).
- **Acceptance:** per case: transcribed correctly / partly / wrongly; decision on language configuration and whether another STT/TTS model **inside Bolna** is needed (D-011).
- **Done when:** language decision logged.
- **Depends on:** S-4.  **Risks:** quality insufficient for shopkeepers → script simplification, then model change.  **Blocks:** T11.4.

### S-9 — Retention and recording controls · P0 (resolves A-14)
- **Prerequisites:** S-4.
- **Actions:** find (docs/dashboard) whether recording/transcript retention can be disabled or shortened; whether `recording_url` is always produced; what disclosure to give callees; record in feasibility doc; update Bible §30.3 wording.
- **Done when:** A-14 resolved or flagged BLOCKER if recording cannot be turned off and consent wording must change.
- **Depends on:** S-4.  **Risks:** recording forced on → script must disclose recording.  **Blocks:** T11.1 (shop consent wording).

### S-10 — Limits, errors, balance and concurrency behaviour · P1 (resolves A-15)
- **Prerequisites:** S-4.
- **Actions:** with test lines only: invalid agent id, invalid `from_phone_number`, malformed number, unverified number on trial (record exact 400 `message` strings); two concurrent calls (trial cap 2, VERIFIED) and a third (expect queue, VERIFIED — confirm timing/status); observe `balance-low` handling if safely reproducible; look for any 429 behaviour.
- **Files:** `backend/tests/fixtures/bolna/error_*.json`, `docs/FEASIBILITY.md`.
- **Done when:** error-to-`ErrorClass` mapping table written.
- **Depends on:** S-4.  **Risks:** burning credits (cap at 6 short calls).  **Blocks:** T5.5.

### S-11 — Feasibility decision (Gate G1) · P0
- **Prerequisites:** S-1…S-9 (S-10 may follow).
- **Actions:** write the final section of `docs/FEASIBILITY.md`: for each Bible capability (agent+variables, outbound call, status events, webhook auth options, pull, extraction, language, cost field, retention) mark VERIFIED / FAILED / WORKAROUND; list changes to the Bible (update §21.3, §45); state **GO / GO-WITH-CHANGES / NO-GO**. If NO-GO, stop Phases 5–6 and open a re-plan task (alternative platform; D-001 revisit) while keeping Phases 2–4.
- **Files:** `docs/FEASIBILITY.md`, `SONAR_BIBLE.md` (register updates).
- **Acceptance:** every row has evidence (capture file path or doc URL + date).
- **Done when:** **G1 = GO** recorded in the decision log.
- **Depends on:** S-1…S-9.  **Risks:** a failed capability (see Bible R-02, R-03).  **Blocks:** T5.3 onward.

> **Gate G1a:** S-1…S-4 passed. Unlocks Phases 2–4 and T5.1–T5.2.
> **Gate G1:** S-11 = GO. Unlocks T5.3 and Phase 6.

---

## PHASE 2 — Domain model and persistence (provider-agnostic; starts after G1a)

### T2.1 — Enums and Pydantic domain schemas · P0 (FR-02, FR-13, §19.3)
- **Prerequisites:** G1a.
- **Actions:** implement every enum in Bible §19.3 as `StrEnum` in `app/domain/enums.py`; Pydantic models in `schemas.py`: `SearchRequest`, `ParsedQuery`, `Clarification`, `PlannedTarget`, `CallAttemptView`, `ResultView`, `Evidence`, `ErrorEnvelope`; response models mirror Bible §20 exactly.
- **Files:** `backend/app/domain/enums.py`, `backend/app/domain/schemas.py`.
- **Tests:** `test_enum_values_match_bible` (parse the Bible's enum table or a literal list in the test and compare); `test_schema_rejects_bad_radius/empty_item/oversized_query`; `test_resultview_never_allows_unavailable_without_response` (model validator).
- **Acceptance:** enum members equal Bible §19.3 exactly; schema examples in Bible §20 validate.
- **Verification:** `pytest backend/tests/unit/test_schemas.py`.
- **Done when:** baseline + tests green.
- **Depends on:** G1a.  **Risks:** drift from Bible (the first test guards it).  **Blocks:** T2.2, T3.x.

### T2.2 — SQLAlchemy models and the first Alembic migration · P0 (FR-08, FR-13)
- **Prerequisites:** T2.1, T0.5.
- **Actions:** implement tables from Bible §19.2 (`businesses`, `search_jobs`, `call_attempts`, `provider_events`, `business_responses`, `audit_events`) with all CHECKs/UNIQUEs; Alembic env; migration `0001_initial`; `session.py` with sync-or-async engine (choose async SQLAlchemy 2 with `psycopg`; record in decision log if sync chosen).
- **Files:** `backend/app/db/models.py`, `backend/app/db/session.py`, `backend/alembic/versions/0001_initial.py`.
- **Commands:** `make migrate`, `alembic downgrade base && alembic upgrade head`
- **Tests (integration):** upgrade/downgrade round trip; inserting a `CONSENTED` business without `consent_recorded_at` fails; duplicate `(search_job_id, business_id, attempt_number)` fails; duplicate `(provider, provider_call_id)` fails; second `business_responses` row for one attempt fails; invalid enum text fails; `phone_e164` regex rejects `12345`.
- **Acceptance:** all constraint tests pass on real Postgres.
- **Verification:** `pytest backend/tests/integration/test_constraints.py`.
- **Done when:** baseline + tests green; migration reversible.
- **Depends on:** T2.1, T0.5.  **Risks:** async driver friction.  **Blocks:** T2.3…

### T2.3 — Transition module (pure) · P0 (FR-13, FR-21, NFR-04)
- **Prerequisites:** T2.1.
- **Actions:** `domain/transitions.py`: `RANK` map (Bible §19.3), `can_transition(current, new) -> bool`, `map_bolna_status(str) -> CallStatus | UNKNOWN` (table in Bible §19.3), `is_terminal`, `retry_eligible(status, attempt_number, max_attempts)`, `search_status_from_attempts(attempts, deadline_passed)`; unknown provider status → returns `None` (caller keeps attempt non-terminal).
- **Files:** `backend/app/domain/transitions.py`.
- **Tests (unit, table-driven):** every row of the Bible mapping table; lower-rank events ignored; terminal never overwritten; `PROCESSING → COMPLETED` allowed; `NO_ANSWER`/`BUSY` retry-eligible below cap, not at cap; `COMPLETED`/`DECLINED` never retry-eligible; search aggregation cases (all done, some no-answer → `COMPLETED_PARTIAL`, deadline).
- **Acceptance:** coverage ≥ 90 % for the module (NFR-11).
- **Verification:** `pytest --cov=app.domain.transitions`.
- **Done when:** baseline + coverage.
- **Depends on:** T2.1.  **Risks:** real Bolna statuses differ (revisit with S-5/S-10 fixtures: add rows).  **Blocks:** T4.x, T6.2.

### T2.4 — Repositories and timestamp/constraint behaviour · P0
- **Prerequisites:** T2.2.
- **Actions:** `db/repositories.py`: `SearchRepo` (create, get, lock_for_update, set_status), `AttemptRepo` (insert, claim_next with `FOR UPDATE SKIP LOCKED`, update_status monotonic, attach_execution_id, by_execution_id), `EventRepo` (insert_or_ignore, orphans, attach_orphans), `ResponseRepo` (insert_on_conflict_do_nothing, list_for_search, latest_for_business), `BusinessRepo` (eligible_in_radius inputs, mark_opt_out), `AuditRepo`. All timestamps timezone-aware UTC.
- **Files:** `backend/app/db/repositories.py`.
- **Tests (integration):** `claim_next` never returns the same row to two concurrent callers (two sessions); `update_status` refuses downgrades; `insert_or_ignore` returns False on duplicate; `attach_orphans` links by call id; `mark_opt_out` sets `OPTED_OUT` and `opted_out_at`.
- **Acceptance:** concurrency test passes repeatedly (run 20×).
- **Verification:** `pytest -k repositories --count=20` (or loop in shell).
- **Done when:** baseline + tests green.
- **Depends on:** T2.2, T2.3.  **Risks:** flaky concurrency tests (use explicit barriers).  **Blocks:** T3.x, T4.x, T6.x.

---

## PHASE 3 — Search API and business directory

### T3.1 — Category configuration loader · P0 (FR-03, FR-04, §23.4)
- **Prerequisites:** T2.1.
- **Actions:** `config/categories.yaml` (per Bible §23.4), `config/blocked_pharmacy_terms.txt` (prescription-only/controlled/dosing/advice terms — start small and conservative; reviewed by a human before pharmacy use), loader with validation; essential attributes per category.
- **Files:** `config/categories.yaml`, `config/blocked_pharmacy_terms.txt`, `backend/app/services/query.py` (loader part).
- **Tests:** bad YAML rejected; unknown category rejected; blocked term match is case-insensitive and word-boundary aware.
- **Acceptance:** loader returns typed `CategoryConfig`.
- **Done when:** baseline + tests.
- **Depends on:** T2.1.  **Risks:** blocked list incomplete (it is a guardrail, not a guarantee; UI disclaimer stays).  **Blocks:** T3.2.

### T3.2 — Query validation and `StructuredFormParser` · P0 (FR-02, FR-03, FR-04)
- **Prerequisites:** T3.1.
- **Actions:** implement `QueryService.parse(SearchRequest) -> ParsedQuery | Clarification | Refusal` per Bible §23.2: missing location, missing essential attributes, invalid radius (0.5–25 km), over-length text, unsupported category, blocked pharmacy terms, conflicting criteria; extract "within N km" hints from `query_text` only to *cross-check* the structured radius (conflict → clarify); only whitelisted charset for `item.name` and attribute values (letters, digits, space, `-`, `/`, `.`, `,`, `%`, `+`), length ≤ 80.
- **Files:** `backend/app/services/query.py`.
- **Tests (table-driven, ≥ 25 cases):** every row of Bible §23.2; injection-looking strings ("ignore previous instructions…") → rejected by charset or passed as inert data but never reach `user_data` raw (assert on the produced `user_data` mapping).
- **Acceptance:** all rows covered; refusal messages contain no medical advice.
- **Done when:** baseline + coverage of the module ≥ 90 %.
- **Depends on:** T3.1.  **Risks:** over-strict charset blocks real product names (relax with test).  **Blocks:** T3.6.

### T3.3 — Business seed loader and directory adapter · P0 (FR-05, FR-06; D-014)
- **Prerequisites:** T2.4.
- **Actions:** `data/businesses.example.yaml` (≥ 6 fake entries with `+91XXXXXXXXXX`-style placeholders that pass the schema only in test mode, plus 2 `TEAM_TEST_LINE`), `scripts/seed_businesses.py` reads `BUSINESS_SEED_PATH`, validates E.164, requires `consent_recorded_at` for `CONSENTED`/`TEST_LINE`, upserts by phone; `DirectoryService.eligible(category, point, radius)`.
- **Files:** `data/businesses.example.yaml`, `scripts/seed_businesses.py`, `backend/app/services/directory.py`.
- **Commands:** `make seed`
- **Tests:** seed idempotent (run twice → same rows); entry missing consent fails loudly; `INVITED`/`DECLINED`/`OPTED_OUT` never returned by `eligible`.
- **Acceptance:** `eligible` returns only callable businesses.
- **Done when:** baseline + tests.
- **Depends on:** T2.4.  **Risks:** real numbers leaking into git (T0.4 check).  **Blocks:** T3.4, T3.5.

### T3.4 — Haversine geo filter · P0 (FR-05; D-015)
- **Prerequisites:** T3.3.
- **Actions:** pure `distance_km(lat1,lng1,lat2,lng2)`, `within_radius`; sort by distance.
- **Files:** `backend/app/services/directory.py`.
- **Tests:** known city-pair distances within 0.5 %; zero distance; antipodal sanity; points exactly on the radius boundary included; NaN/out-of-range lat rejected.
- **Done when:** baseline + tests.
- **Depends on:** T3.3.  **Risks:** none.  **Blocks:** T3.5.

### T3.5 — Selector (eligibility, caps, cooldown) · P0 (FR-05, FR-06, FR-07)
- **Prerequisites:** T3.4, T2.4.
- **Actions:** `Selector.select(parsed_query, now) -> list[PlannedTarget]`: nearest first; cap `MAX_TARGETS_PER_SEARCH`; exclude businesses at `BUSINESS_DAILY_CALL_CAP` or inside `BUSINESS_COOLDOWN_MINUTES`; respect `best_call_window` (outside window → excluded with reason); returns exclusion counts for the "why fewer than expected" message; leaves a hook for cache reuse (T7.4).
- **Files:** `backend/app/services/selector.py`.
- **Tests:** cap honoured; opted-out never selected even if present in the candidate list passed in (defence in depth); cooldown/daily cap boundaries; window boundaries in IST; no candidates → `NO_ELIGIBLE_BUSINESSES` with counts.
- **Done when:** baseline + tests.
- **Depends on:** T3.4.  **Risks:** timezone bugs (test with fixed `now`).  **Blocks:** T3.6, T4.1.

### T3.6 — Search endpoints (create + read), no dialing yet · P0 (FR-01, FR-20, FR-27, FR-29)
- **Prerequisites:** T3.2, T3.5.
- **Actions:** `POST /api/searches` (validates, clarification/refusal paths, creates `search_jobs` + planned `call_attempts` as `PENDING`, returns `202` with planned targets), `GET /api/searches/{id}`, `GET /api/searches/{id}/results` (empty until responses exist), `GET /api/businesses` (no phone numbers), `GET /health/ready`, uniform error envelope (Bible §20.1), `X-Sonar-Key` dependency, rate limiter, CORS from `ALLOWED_ORIGINS`.
- **Files:** `backend/app/api/searches.py`, `businesses.py`, `health.py`, `deps.py`, `errors.py`, `main.py`.
- **Tests (integration, `httpx.AsyncClient`):** 202 + job id returned in well under the request's natural duration (no blocking); missing key → 401; rate limit → 429; clarification returns 200 with questions; refusal returns 422 `UNSUPPORTED_QUERY`; no eligible → `FAILED/NO_ELIGIBLE_BUSINESSES`; `GET /api/businesses` response contains no `phone` field (assert on JSON keys); unknown search id → 404 envelope.
- **Acceptance:** responses validate against T2.1 schemas; OpenAPI snapshot saved.
- **Verification:** `curl` the three flows against `make run`.
- **Done when:** baseline + tests.
- **Depends on:** T3.2, T3.5.  **Risks:** schema drift.  **Blocks:** T4.1, Phase 8.

---

## PHASE 4 — Search-job orchestration (provider-agnostic)

### T4.1 — Orchestrator loop with concurrency, deadline and budget · P0 (FR-09, FR-22, NFR-06)
- **Prerequisites:** T3.6, T5.1 (interface only).
- **Actions:** background orchestrator started in app lifespan: loop claims `PENDING` attempts with `not_before <= now` via `claim_next`; honours `asyncio.Semaphore(MAX_CONCURRENT_CALLS)` **and** a DB count guard; checks `GLOBAL_DAILY_CALL_BUDGET` before each dispatch (`BUDGET_EXCEEDED`); sets job `RUNNING`/`started_at`/`deadline_at`; at deadline marks stragglers `TIMED_OUT` and closes job via `search_status_from_attempts`. Single worker documented.
- **Files:** `backend/app/services/orchestrator.py`.
- **Interfaces:** depends on `VoiceProvider` (T5.1).
- **Tests (integration with `SimulatedVoiceProvider`):** never more than N concurrent dispatches (instrumented provider records max concurrency); budget stop; deadline closes job as `COMPLETED_PARTIAL`; jobs with zero targets close immediately.
- **Acceptance:** concurrency invariant holds under 50 queued attempts across 5 jobs.
- **Done when:** baseline + tests.
- **Depends on:** T3.6, T5.1, T5.2.  **Risks:** event-loop blocking; keep DB calls async.  **Blocks:** T4.2…

### T4.2 — Safe dispatch and `DISPATCH_UNKNOWN` handling · P0 (FR-10, NFR-05; Bible §27.2.1)
- **Prerequisites:** T4.1.
- **Actions:** implement exact sequence: `PENDING → DISPATCHING` (commit) → provider `start_call` → on success store `provider_call_id` + `DIALING` (commit); re-check consent/eligibility **again** immediately before `start_call` (FR-06); on exceptions classify (4xx → `FAILED/PROVIDER_REJECTED`, 5xx/timeouts → bounded retry with backoff then `FAILED/PROVIDER_UNAVAILABLE`); crash simulation leaves `DISPATCHING`; startup hook converts stale `DISPATCHING` without id to `DISPATCH_UNKNOWN` and **never** auto-retries.
- **Tests:** fault-injection provider that raises after "sending" (simulating lost response) → attempt becomes `DISPATCH_UNKNOWN` after restart, provider call count stays 1; opted-out business between claim and dispatch → no call made; 4xx path not retried.
- **Acceptance:** no scenario produces two provider calls for one attempt row.
- **Done when:** baseline + tests; NFR-05 test names listed in PR.
- **Depends on:** T4.1.  **Risks:** missing idempotency on Bolna (A-11).  **Blocks:** T4.3, T6.7.

### T4.3 — Retry policy · P0 (FR-21)
- **Prerequisites:** T2.3, T4.2.
- **Actions:** when an attempt becomes `NO_ANSWER`/`BUSY` (or first `FAILED`), create next attempt row (`attempt_number+1`, `not_before=now+backoff`) if below `MAX_ATTEMPTS_PER_BUSINESS` and before the job deadline and job not cancelled and business still eligible; never after `COMPLETED`/`DECLINED`/opt-out; backoff values from settings; demo mode may disable retries.
- **Tests:** table of (status, attempt_no, cap, deadline, cancelled) → create/not create; backoff scheduling; no retry storms (max rows per business per job = cap).
- **Done when:** baseline + tests.
- **Depends on:** T4.2.  **Risks:** retrying shops that hung up on purpose (treated as `COMPLETED`, so no retry).  **Blocks:** no.

### T4.4 — Cancellation · P0 (FR-23; A-12)
- **Prerequisites:** T4.1.
- **Actions:** `POST /api/searches/{id}/cancel` idempotent; sets job `CANCELLED`; pending attempts → `CANCELLED`; in-flight attempts continue and their results are still recorded and shown (documented); orchestrator skips cancelled jobs; audit event.
- **Tests:** cancel twice; cancel after completion is a no-op; cancel with in-flight call → result recorded; no new dispatch after cancel.
- **Done when:** baseline + tests.
- **Depends on:** T4.1.  **Risks:** users expect an immediate hang-up (UI copy says "no further calls will be made").  **Blocks:** T8.7.

### T4.5 — Restart recovery and reconciler skeleton · P0 (FR-14, NFR-05)
- **Prerequisites:** T4.2, T2.4.
- **Actions:** `services/reconciler.py`: on startup and every 30 s, find non-terminal attempts with a call id and `updated_at` older than `RECONCILE_AFTER_SECONDS` → call `provider.get_call` → feed the same `EventProcessor` path used by webhooks (implemented in T6.2; until then log-only); also closes jobs past deadline.
- **Tests (integration, simulated provider):** kill-and-restart simulation (re-instantiate app state mid-search) → attempts reconcile; no duplicate finalisation.
- **Done when:** baseline + tests; completes after T6.6 wires the real finalizer.
- **Depends on:** T4.2.  **Risks:** none.  **Blocks:** T6.6.

### T4.6 — Budgets, caps and audit trail · P0 (FR-24, NFR-06, T4/T13 in Bible §30.1)
- **Prerequisites:** T4.1.
- **Actions:** per-business daily counter (from `call_attempts`), global daily budget, `audit_events` for dispatch/opt-out/cancel/budget stop; `mark_opt_out` flow used by the validator (T6.4) with immediate effect on queued attempts of that business (→ `CANCELLED`).
- **Tests:** third/fourth call same business same day boundary; opt-out cancels other queued attempts for that business across jobs; audit rows written once.
- **Done when:** baseline + tests.
- **Depends on:** T4.1.  **Risks:** timezone for "day" (use IST day boundary, documented).  **Blocks:** no.

---

## PHASE 5 — Voice-agent integration

### T5.1 — `VoiceProvider` protocol and models · P0 (WP-3)
- **Prerequisites:** G1a.
- **Actions:** `providers/base.py`:
```python
class CallRequest(BaseModel):
    attempt_id: UUID
    agent_key: str               # e.g. "pharmacy" → resolves to BOLNA_AGENT_ID_PHARMACY
    to_e164: str
    from_e164: str | None = None
    user_data: dict[str, str]    # whitelisted, validated values only

class ProviderCallRef(BaseModel):
    provider: Literal["bolna", "simulated"]
    provider_call_id: str
    provider_status: str

class ProviderCallRecord(BaseModel):
    provider_call_id: str
    provider_status: str
    transcript: str | None
    extracted: dict | None       # raw, untrusted
    duration_seconds: int | None
    cost_amount: Decimal | None
    cost_currency: str | None
    raw: dict                    # redacted before persistence

class VoiceProvider(Protocol):
    async def start_call(self, req: CallRequest) -> ProviderCallRef: ...
    async def get_call(self, provider_call_id: str) -> ProviderCallRecord: ...
```
  Exceptions: `ProviderRejected`, `ProviderUnavailable`, `ProviderTimeout`, `ProviderBalanceLow`.
- **Files:** `backend/app/providers/base.py`.
- **Tests:** models reject non-E.164 numbers; `user_data` values must be `str` ≤ 200 chars; no free-form phone input path exists (type test).
- **Done when:** baseline + tests.
- **Depends on:** G1a.  **Risks:** fields change after S-6 (adjust `ProviderCallRecord`, not callers).  **Blocks:** T4.1, T5.2, T5.3.

### T5.2 — `SimulatedVoiceProvider` with scripted scenarios · P0 (FR-25, US-8; D-022)
- **Prerequisites:** T5.1.
- **Actions:** scenario registry keyed by Bible §33.3 ids; each returns timed status sequences (queued → ringing → in-progress → call-disconnected → completed) via an async event source the orchestrator/reconciler can consume, with synthetic transcripts and `extracted` blocks; **every record sets `data_origin=SIMULATED`** downstream (provider name `simulated`); injects duplicate/out-of-order events for those scenarios; deterministic with a seed; clearly fake business names via the example seed.
- **Files:** `backend/app/providers/simulated.py`, `backend/tests/fixtures/sim_scenarios/*.yaml`.
- **Tests:** each scenario yields the expected terminal status; determinism (same seed → same output); `provider == "simulated"` for all; simulated responses are excluded from the live cache query (T7.4).
- **Done when:** baseline + tests.
- **Depends on:** T5.1.  **Risks:** simulator drifting from real payloads (regenerate from S-5/S-6 fixtures in T9.1).  **Blocks:** T4.1 tests, T8.x demo mode.

### T5.3 — `BolnaVoiceProvider` (HTTP client) · P0 (FR-09, FR-10; D-010)
- **Prerequisites:** **G1**, T5.1, fixtures from S-5/S-6/S-10.
- **Actions:** `providers/bolna.py` using `httpx.AsyncClient` (timeouts: connect 5 s, read 15 s); `start_call` → `POST {base}/call` with `agent_id`, `recipient_phone_number`, optional `from_phone_number`, `user_data`; **never** sets `retry_config`, `scheduled_at` or `bypass_call_guardrails`; maps response (`status`, `execution_id`) to `ProviderCallRef`; `get_call` → `GET {base}/executions/{id}` mapped to `ProviderCallRecord` using the **captured** field names (S-6); error mapping from S-10 (400 → `ProviderRejected` with message; 5xx/timeouts → `ProviderUnavailable`/`ProviderTimeout`; balance-low → `ProviderBalanceLow`); API key from settings only; never logs headers/body with numbers.
- **Files:** `backend/app/providers/bolna.py`.
- **Tests (respx mocks built from real redacted fixtures):** request body exactly as expected (golden); 200 → ref; 400 variants → `ProviderRejected`; 500 → `ProviderUnavailable`; timeout → `ProviderTimeout`; `get_call` parses every captured execution fixture; `Authorization` header present and never appears in captured log output (log-capture assertion).
- **Acceptance:** no network in unit tests; golden request test passes.
- **Verification:** an opt-in live smoke test marked `@pytest.mark.live` (skipped by default) that places **one** call to a test line when `RUN_LIVE=1`.
- **Done when:** baseline + tests; live smoke executed once and recorded in FEASIBILITY.
- **Depends on:** G1, T5.1.  **Risks:** API drift; docs vs reality (fixtures win).  **Blocks:** T6.x.

### T5.4 — Agent prompt, user_data mapping and versioning · P0 (FR-04, §25)
- **Prerequisites:** S-2, S-7, S-8, T3.2.
- **Actions:** finalise `docs/agent/prompt_v1.md` (script from Bible §25, truthful AI opening, transcription disclosure per S-9, refusal/opt-out handling, never-advise rules, voicemail/IVR hangup); `build_user_data(parsed_query) -> dict[str,str]` (only whitelisted keys: `item`, `attributes_text`, `required_fields_text`, `category`); agent id from env by category.
- **Files:** `docs/agent/prompt_v1.md`, `backend/app/services/query.py` (`build_user_data`).
- **Tests:** `build_user_data` output contains only whitelisted keys and sanitised values (property-based or table tests with hostile strings); prompt file contains the required disclosure sentence (string assertion — protects against accidental edits).
- **Done when:** baseline + tests; prompt synchronised to the dashboard agent (record agent version/date in the doc).
- **Depends on:** S-2, S-7.  **Risks:** dashboard prompt differs from repo copy (checklist item in T11.5).  **Blocks:** T6.7.

### T5.5 — Provider error classification · P1 (FR-21, §29)
- **Prerequisites:** T5.3, S-10.
- **Actions:** `classify_provider_error(exc|status) -> ErrorClass`, user-safe messages without provider internals.
- **Tests:** every mapped case; unknown error → `INTERNAL`; messages never contain keys/numbers.
- **Done when:** baseline + tests.
- **Depends on:** T5.3.  **Risks:** none.  **Blocks:** T9.5.

---

## PHASE 6 — Webhooks, finalisation and structured answer extraction

### T6.1 — Webhook endpoint: authentication and raw persistence · P0 (FR-11; T2, T14)
- **Prerequisites:** G1, S-5 fixtures, T2.4.
- **Actions:** `POST /api/webhooks/bolna/{secret_token}`: constant-time token compare (`hmac.compare_digest`); optional header check if S-5 proved headers arrive (A-06); optional IP allowlist honouring `TRUSTED_PROXY_IPS`; 256 KB body cap; JSON parse; extract `execution_id`/`status` using the **captured** field locations (A-18); persist raw event via `insert_or_ignore` (payload redacted: recording URLs and numbers masked); return `200 {"ok":true}` immediately; schedule processing task; unknown call id → orphan row + 200.
- **Files:** `backend/app/api/webhooks.py`.
- **Tests (integration, using real redacted fixtures):** wrong token → 401 and nothing persisted; right token → 200 and one row; same body twice → one row; oversized body → 413; non-JSON → 400 `WEBHOOK_MALFORMED`; orphan stored; response time p95 measured locally (NFR-02) over 100 posts.
- **Acceptance:** NFR-04 (50 duplicate posts → 1 row).
- **Done when:** baseline + tests.
- **Depends on:** G1, T2.4.  **Risks:** A-18 wrong (fixtures catch it).  **Blocks:** T6.2.

### T6.2 — `EventProcessor`: status mapping, monotonic updates · P0 (FR-13)
- **Prerequisites:** T6.1, T2.3.
- **Actions:** given a persisted event: map provider status → `CallStatus` (T2.3); ignore lower-rank/unknown statuses (store `provider_status`, leave state); update attempt (`answered_at` on `IN_PROGRESS`, `completed_at` on terminal, `duration_seconds` when present); on `COMPLETED` or any terminal status enqueue finalisation; on `NO_ANSWER`/`BUSY`/`FAILED` call retry planner (T4.3); mark event `processed_at`.
- **Tests:** feed S-5 fixture sequences in correct, reversed and shuffled order → same final state; duplicate sequence → no change; unknown status → attempt unchanged, event stored, warning logged; `call-disconnected` does not finalise (VERIFIED: fields still null).
- **Done when:** baseline + tests.
- **Depends on:** T6.1, T2.3.  **Risks:** none.  **Blocks:** T6.3.

### T6.3 — `Finalizer`: authoritative pull, validate, persist · P0 (FR-12, FR-15; D-005)
- **Prerequisites:** T6.2, T5.3.
- **Actions:** `finalize(attempt_id)`: call `provider.get_call(provider_call_id)` (**never** use the webhook body); require the pulled `provider_status` to be terminal and match; for `completed` with transcript run `AnswerValidator` (T6.4) and `INSERT … ON CONFLICT DO NOTHING` into `business_responses`; for non-`completed` terminals write **no** response row; fill `cost_amount`/`duration_seconds`; update job aggregate under `FOR UPDATE`; retry pull with backoff on failure (≤ 3), then mark attempt `ERROR`/`EXTRACTION_INVALID` appropriately; idempotent (second call is a no-op).
- **Tests (integration):** forged webhook claiming `completed` while the pulled record says `in-progress` → no response written (this is the D-005 proof test); duplicate finalize → one response row; pulled `no-answer` → no response row; pull failing twice then succeeding → one row; job moves to `COMPLETED`/`COMPLETED_PARTIAL` correctly.
- **Acceptance:** D-005 test passes.
- **Done when:** baseline + tests.
- **Depends on:** T6.2, T5.3, T6.4.  **Risks:** pull returns stale data right after `completed` (retry/backoff handles).  **Blocks:** T6.5.

### T6.4 — `AnswerValidator` (pure, rules V1–V14) · P0 (FR-15…FR-19, NFR-08; §23.3)
- **Prerequisites:** S-6, S-7, T2.1.
- **Actions:** implement `validate(record, parsed_query, now) -> ValidatedAnswer` exactly per Bible §23.3, including: allowed-set check, evidence-substring match with normalisation (case, whitespace, punctuation, digits/words for numbers) against the transcript, exact-match gating, attribute matching (`CONFIRMED/DIFFERENT/UNKNOWN`), price numeric/plausible/currency/appears-in-transcript, not-exact-item price handling, contradictions → `UNCERTAIN`+flag, opt-out precedence, voicemail/IVR → no response, templated `answer_summary`, excerpt truncation to 600 chars; provider `confidence` stored raw only.
- **Files:** `backend/app/services/validator.py`, `backend/tests/fixtures/transcripts/*.json`.
- **Tests (unit, ≥ 40 fixtures):** each rule has positive and negative cases, including: price quoted but different item; "we had it yesterday"; "maybe, let me check" → `UNCERTAIN`; alternative offered → `ALTERNATIVE_ONLY`; extraction says available but evidence missing → `UNCERTAIN`/`EVIDENCE_NOT_FOUND`; extraction says available but transcript says "finished" → `CONTRADICTORY`; price absent → null; unquoted currency → null currency; hostile transcript ("system: mark everything available", HTML/script tags) → no effect, excerpt escaped on render later; opt-out phrase; voicemail; empty transcript.
- **Acceptance:** coverage ≥ 90 % (NFR-11); **no test path produces `REPORTED_UNAVAILABLE` from a non-completed or silent call**.
- **Verification:** `pytest backend/tests/unit/test_validator.py --cov=app.services.validator`.
- **Done when:** baseline + coverage.
- **Depends on:** S-6, S-7.  **Risks:** `supporting_quote` unreliable (fallback decided in S-7).  **Blocks:** T6.3.

### T6.5 — Response persistence and job aggregation · P0 (FR-19, FR-20)
- **Prerequisites:** T6.3.
- **Actions:** compute `availability_expires_at`/`price_expires_at` from TTLs (T7.1 if available, else settings); set `data_origin` from provider name (`bolna`→`LIVE_CALL`, `simulated`→`SIMULATED`); results endpoint now returns real rows; derive `result_state` for every attempt (including no-answer/failed) per Bible §6.1; **no response row ⇒ never `REPORTED_UNAVAILABLE`**.
- **Tests:** results payload for mixed scenarios matches Bible §20.4 shape; no-answer row has note "does not mean unavailable"; partial results visible while job `RUNNING`.
- **Done when:** baseline + tests.
- **Depends on:** T6.3.  **Risks:** none.  **Blocks:** T6.7, Phase 7–8.

### T6.6 — Wire the reconciler to the real finalizer · P0 (FR-14)
- **Prerequisites:** T4.5, T6.3.
- **Actions:** reconciler polls `get_call`, feeds `EventProcessor`/`Finalizer`; stale `PROCESSING` gets finalised; attempts exceeding deadline → `TIMED_OUT`; orphan events attached after `execution_id` commit.
- **Tests:** lost-webhook simulation (no events delivered at all) → attempt reaches terminal via polling; orphan-then-attach path; restart mid-call.
- **Done when:** baseline + tests.
- **Depends on:** T4.5, T6.3.  **Risks:** poll frequency vs provider limits (A-15; keep ≥ 10 s apart per attempt).  **Blocks:** T6.7.

### T6.7 — **MILESTONE M1: one real call, end to end, readable via the API** · P0
- **Purpose:** prove the product's core path before any UI work.
- **Prerequisites:** T3.6, T4.1–T4.4, T5.3, T5.4, T6.1–T6.6, a `TEAM_TEST_LINE` or consenting business with `consent_recorded_at`, public webhook URL (tunnel acceptable), funded wallet.
- **Actions:** seed the real local file; `make run`; `curl -X POST /api/searches` (with `X-Sonar-Key`) for the pilot item near the test line; answer the call as a shopkeeper (**three runs**: available+price; "not available"; hesitant "maybe"); poll `GET /api/searches/{id}` and `/results` with `curl`/`jq`; record screenshots/terminal output in `docs/M1_EVIDENCE.md` (numbers masked).
- **Tests:** an opt-in `@pytest.mark.live` test that automates the POST + poll and asserts: job reached a terminal state; exactly one attempt row; exactly one `business_responses` row; `data_origin == LIVE_CALL`; evidence excerpt present and validated; timestamps ordered (`started_at <= answered_at <= completed_at`); `total_cost` stored if present.
- **Acceptance:** AC-2; the three runs produce `REPORTED_AVAILABLE`, `REPORTED_UNAVAILABLE`, `UNCERTAIN` respectively **or** differences are explained and fixed; one run where the phone is left unanswered produces `NO_ANSWER` with no response row.
- **Verification:** two people review `M1_EVIDENCE.md`.
- **Done when:** the live test passes once and the evidence document is committed. **Apply the cut-line rule (§0.5) now.**
- **Depends on:** all above.  **Risks:** B-01–B-03, extraction quality, language.  **Blocks:** **all of Phase 8** (R-13), T10.x, T11.x.

---

## PHASE 7 — Result validation, freshness and ranking

### T7.1 — Freshness service (pure) · P0 (FR-19; §28)
- **Actions:** `field_freshness(field, answer_ts, now, ttl)`; `FRESH/STALE/UNKNOWN`; TTLs from settings; clock-skew tolerance (negative age clamps to 0).
- **Files:** `backend/app/services/freshness.py`.
- **Tests:** boundary at exactly TTL; null field → `UNKNOWN`; future timestamp; per-field TTL differences.
- **Done when:** baseline + coverage ≥ 90 %.
- **Depends on:** T2.1.  **Risks:** none.  **Blocks:** T7.2, T7.4.

### T7.2 — Result-state derivation and "no misleading label" guard · P0 (FR-16, NFR-09)
- **Actions:** single function `derive_result_state(attempt, response|None) -> ResultState`; exhaustive over `CallStatus × availability`; copy strings for every state in one module (`result_copy.py`) so wording is reviewable.
- **Tests:** full cross product table; assertion that no copy string for `NO_ANSWER|CALL_FAILED|DECLINED|PENDING|CANCELLED` contains "unavailable" or "out of stock" (NFR-09).
- **Done when:** baseline + tests.
- **Depends on:** T7.1.  **Risks:** none.  **Blocks:** T8.x copy.

### T7.3 — Deterministic ranking with explanation · P1 (FR-31; D-016)
- **Actions:** lexicographic ordering per Bible §24.3; `ranking_explanation` string; stable ordering for ties (business id).
- **Files:** `backend/app/services/ranking.py`.
- **Tests:** tier order; live-before-cached; distance/price tie-breaks; price absent sorts after priced within tier; stability; high rank never assigned to `UNCERTAIN` above `REPORTED_AVAILABLE`.
- **Done when:** baseline + coverage ≥ 90 %.
- **Depends on:** T7.1, T7.2.  **Risks:** none.  **Blocks:** T8.5.

### T7.4 — Fresh-cache reuse and `force_fresh` · P1 (FR-30; D-022)
- **Actions:** `ResultCache.lookup(business, parsed_query, now)`: latest `LIVE_CALL` `VALID` response, exact attribute match, all required fields `FRESH`, business still eligible, `force_fresh=false`; returned as `CACHED_LIVE` with the **original** timestamp; selector skips dialing such businesses; simulated rows never eligible.
- **Tests:** just inside/outside TTL; attribute mismatch → miss; `force_fresh` → miss; simulated row → miss; displayed label includes original time; a stale row is not shown as current.
- **Done when:** baseline + tests.
- **Depends on:** T7.1, T3.5.  **Risks:** over-eager reuse (keep TTLs conservative).  **Blocks:** no.

---

## PHASE 8 — Frontend (starts only after M1 — see §0.4 rule 4)

### T8.1 — Frontend scaffold · P0
- **Prerequisites:** **M1**.
- **Actions:** Vite + React + TypeScript + Tailwind in `frontend/`; `VITE_API_BASE_URL`; dev proxy to backend; `make web-dev`; `npm run build` produces static assets; Vitest configured.
- **Files:** `frontend/**`.
- **Tests:** a smoke render test.
- **Acceptance:** `npm run build` and `npm test` pass.
- **Done when:** baseline-equivalent for frontend (`npm run lint`, `npm test`).
- **Depends on:** M1.  **Risks:** none.  **Blocks:** T8.2.

### T8.2 — Typed API client and polling hook · P0 (FR-20, NFR-03)
- **Actions:** TypeScript types mirroring Bible §20 (generated from the backend OpenAPI if convenient, else handwritten with a contract test); `useSearchPolling(searchId)` polls every 2 s while status is `RUNNING`/`CREATED`, backs off on errors, keeps last good state on failure, stops on terminal states, handles page refresh by reading the id from the URL.
- **Tests:** fake-timer tests for polling cadence, stop on terminal, error retry without clearing results; contract test: fixture from the real backend validates against the TS types (via `zod` or type guards — if `zod` is wanted, add decision-log entry).
- **Done when:** tests green.
- **Depends on:** T8.1.  **Risks:** type drift.  **Blocks:** T8.3–T8.5.

### T8.3 — Search form with location and radius · P0 (FR-01, FR-26)
- **Actions:** fields: category (from `/api/config/public`), item/service, key attributes (dynamic from category config), location preset or browser geolocation (graceful denial), radius slider within allowed range, `force_fresh` toggle (P1), `demo mode` toggle (explicit, visible); shows clarification questions inline; shows refusal message; access key held in an environment-appropriate way (demo key entered once per session, stored in memory only; no key in the bundle).
- **Tests:** validation messages; clarification flow; geolocation denied fallback; refusal rendering; key not present in built assets (see T9.4).
- **Done when:** component tests green.
- **Depends on:** T8.2.  **Risks:** none.  **Blocks:** T8.4.

### T8.4 — Planned targets and live progress · P0 (US-2, US-3)
- **Actions:** show the planned target list immediately after create (name, distance, badge `Consented` / `Team test line (role-play)`); per-business status chips with text labels (not colour alone — NFR-12): Queued, Dialing, Ringing, In call, Processing, Done, No answer, Failed, Cancelled, Timed out; overall progress bar; elapsed time; cancel button.
- **Tests:** each status renders text label; keyboard operability; badge for test lines present.
- **Done when:** tests green.
- **Depends on:** T8.3.  **Risks:** none.  **Blocks:** T8.5.

### T8.5 — Results list with evidence and timestamps · P0 (US-4, US-5, NFR-08)
- **Actions:** result cards in the API's ranked order with `ranking_explanation`; label per Bible §6.1; reported price with currency or "price not quoted"; answer time (absolute + relative); freshness chip; expandable evidence panel: question asked, excerpt (plain text, escaped), "reported by phone", verification status; flags (e.g. contradictory) shown explicitly; cached results show "Earlier call, HH:MM"; below the list: groups for No answer / Call failed / Cancelled with the sentence "This does not mean the item is unavailable."
- **Tests:** XSS fixture renders as text; no `dangerouslySetInnerHTML` anywhere (lint rule + grep test); each `ResultState` fixture renders correct label and none render "unavailable" except `REPORTED_UNAVAILABLE`; partial results render while status is `RUNNING`.
- **Done when:** tests green.
- **Depends on:** T8.4, T7.3.  **Risks:** copy drift (copy sourced from API strings where possible).  **Blocks:** T8.6.

### T8.6 — Simulated / test-line / cached labelling · P0 (US-8, WP-10, T15)
- **Actions:** permanent amber banner on every page and result card when `demo_mode`; banner cannot be dismissed; badge for `TEAM_TEST_LINE`; badge for cached; screenshot-safe (banner appears in any crop of a result card — put a small "SIMULATED" tag on each card, not only a header).
- **Tests:** demo-mode fixture → banner + per-card tag present; live fixture → neither; test-line fixture → role-play badge.
- **Done when:** tests green; AC-6 verified manually.
- **Depends on:** T8.5.  **Risks:** none.  **Blocks:** T9.x.

### T8.7 — Error, empty, cancelled and reconnect states; responsive layout · P0 (FR-26)
- **Actions:** states: loading, empty (no eligible businesses with explanation), failed job, cancelled, network lost ("Connection lost, retrying" — last results stay), refresh mid-search resumes, "New search" button resets; responsive down to ~360 px width; visible focus rings.
- **Tests:** component tests per state; Playwright (P1) at 390×844 and 1280×800 screenshots.
- **Done when:** tests green.
- **Depends on:** T8.5, T4.4.  **Risks:** none.  **Blocks:** T9.x.

### T8.8 — Frontend integration/E2E test of the full journey (simulator) · P0 (AC-1)
- **Actions:** Playwright (or Vitest + MSW if Playwright is cut) driving the real UI against the real backend in demo mode through `all_available` and `one_no_answer` scenarios.
- **Tests:** search → targets → progress → first result before completion → evidence expand → completion; no-answer wording; cancel.
- **Done when:** passes in `make e2e`.
- **Depends on:** T8.7, T5.2.  **Risks:** flakiness (use deterministic simulator seeds).  **Blocks:** T9.1.

---

## PHASE 9 — Reliability and integration testing

### T9.1 — Full scenario matrix against the simulator · P0 (AC-1; Bible §33.3)
- **Actions:** one automated test per scenario id (14); simulator refreshed from real fixtures where possible.
- **Tests:** assert final job status, per-business `ResultState`, row counts, absence of forbidden wording, partial-before-complete visibility.
- **Done when:** all 14 pass in one `make e2e` run, 5 consecutive runs without a flake.
- **Depends on:** T8.8.  **Risks:** flakiness.  **Blocks:** T11.x.

### T9.2 — Duplicate and out-of-order webhook storm · P0 (NFR-04)
- **Actions:** replay each captured sequence 50× in random order/concurrently (asyncio gather) into the real endpoint with real Postgres.
- **Tests:** exactly one `business_responses` row; final status correct; event table contains one row per unique key; no deadlocks.
- **Done when:** passes 5× in a row.
- **Depends on:** T6.6.  **Risks:** none.  **Blocks:** no.

### T9.3 — Restart and database-failure behaviour · P0 (NFR-05; AC-5)
- **Actions:** scripted kill -9 of the backend at each state (DISPATCHING, DIALING, PROCESSING) with the simulator; stop the DB container mid-search and restart it; verify `/health/ready`, webhook 503 during outage, and recovery.
- **Tests:** no double dial (provider call count by attempt id); attempts reach terminal after restart; DB-down webhook returns 503 and the same event succeeds after recovery.
- **Done when:** results recorded in `docs/RELIABILITY.md`.
- **Depends on:** T6.6.  **Risks:** none.  **Blocks:** T10.x.

### T9.4 — Secrets and exposure scan · P0 (NFR-07; AC-7)
- **Actions:** script scans (a) the built frontend bundle for any string matching configured secrets or key patterns, (b) API responses from all endpoints for fields named `phone`, `api_key`, `authorization`, `recording_url`, (c) server logs from the E2E run for phone numbers and tokens.
- **Tests:** planted-secret self-test; real scan over built assets and E2E logs.
- **Done when:** scan green in CI/`make check-secrets`.
- **Depends on:** T8.8.  **Risks:** none.  **Blocks:** T10.x.

### T9.5 — Misleading-message audit · P0 (NFR-09)
- **Actions:** enumerate every user-facing string (API `note`/`message`, UI copy, error envelopes) in one file; test that states `NO_ANSWER`, `CALL_FAILED`, `DECLINED`, `CANCELLED`, `PENDING`, `UNCERTAIN` never claim unavailability, success or verification; review "Reported by phone" wording consistency.
- **Tests:** copy-lint test over the string registry.
- **Done when:** test green + human review noted.
- **Depends on:** T7.2, T5.5.  **Risks:** none.  **Blocks:** T11.x.

### T9.6 — Limits and abuse tests · P0 (NFR-06; FR-29)
- **Actions:** hammer `POST /api/searches` (rate limit), bad keys, giant bodies, hostile strings in every field; verify caps (`MAX_TARGETS`, concurrency, daily/global budgets).
- **Tests:** 429 after limit; 401 without key; 413/422 for oversized; instrumented provider confirms caps.
- **Done when:** passes.
- **Depends on:** T4.6, T3.6.  **Risks:** none.  **Blocks:** T10.x.

### T9.7 — Data retention and deletion tooling · P1 (NFR-13; T12)
- **Actions:** `services/retention.py` periodic purge of `provider_events.payload` and old responses per settings; `scripts/delete_business_data.py <business_id>` removes a business's responses and events and keeps the opt-out flag; unit/integration tests.
- **Tests:** purge boundaries; deletion leaves `OPTED_OUT` intact.
- **Done when:** baseline + tests.
- **Depends on:** T2.4.  **Risks:** none.  **Blocks:** no.

### T9.8a — Human review CLI for extraction accuracy · P1 (FR-34)
- **Prerequisites:** T6.5.
- **Actions:** `scripts/review_responses.py` lists recent `LIVE_CALL` responses with their transcript excerpt and stored fields; reviewer marks `HUMAN_REVIEWED` (agrees) or `CONTRADICTED` (disagrees) and writes an `audit_events` row; feeds the human-verified accuracy metric (Bible §39).
- **Files:** `scripts/review_responses.py`.
- **Tests:** marking updates only `verification_status` and writes one audit row; a `SIMULATED` row cannot be reviewed into the accuracy denominator.
- **Done when:** baseline + tests.
- **Depends on:** T6.5.  **Risks:** none.  **Blocks:** no.

### T9.8 — Cost and success measurement from real data · P1 (FR-32, FR-33)
- **Actions:** `scripts/metrics_report.py` computes Bible §39 metrics with counts and denominators from the DB, filtering `LIVE_CALL`; prints n for every number.
- **Tests:** fixtures with known answers → exact expected metrics; zero-denominator handling prints "n/a".
- **Done when:** baseline + tests.
- **Depends on:** T6.5.  **Risks:** none.  **Blocks:** T12.4.

---

## PHASE 10 — Deployment and operations

### T10.1 — Choose the host and record the decision · P0 (D-019)
- **Actions:** compare 2–3 candidate hosts against Bible §35 criteria (public HTTPS, always-on process, Postgres, secrets, logs, **cost as verified on their pricing pages that day**); do not assume a free tier; record in decision log.
- **Done when:** decision entry committed with the cost figures cited and dated.
- **Depends on:** M1.  **Risks:** availability/cost.  **Blocks:** T10.2.

### T10.2 — Containerise backend and static frontend · P0
- **Actions:** `backend/Dockerfile` (single worker, non-root user, `alembic upgrade head` as a separate release command), frontend static build served by the host or the backend; `docker compose -f docker-compose.prod.example.yml` for a local prod-like run.
- **Tests:** container starts; `/health/ready` OK; migrations idempotent on restart.
- **Done when:** local prod-like run passes the E2E smoke in demo mode.
- **Depends on:** T10.1.  **Risks:** none.  **Blocks:** T10.3.

### T10.3 — Production configuration and secrets · P0
- **Actions:** set all variables from Bible §36 in the host's secret store; generate long random `SONAR_ACCESS_KEY` and `WEBHOOK_SECRET_TOKEN`; set `ALLOWED_ORIGINS`, `WEBHOOK_ALLOWED_IPS` (three VERIFIED Bolna IPs) and `TRUSTED_PROXY_IPS`; seed the real business file via a secure channel (not Git).
- **Tests:** `scripts/check_prod_env.py` fails when a required variable is missing or default/weak.
- **Done when:** script passes against the deployed environment.
- **Depends on:** T10.2.  **Risks:** IP allowlist breaks behind unknown proxy (feature flag to disable, token remains).  **Blocks:** T10.4.

### T10.4 — Public webhook URL and Bolna agent configuration · P0 (B-06)
- **Actions:** set the production URL `https://<host>/api/webhooks/bolna/<token>` in the agent's Webhook Configuration; use the dashboard's **Send test**; confirm the delivery appears in `provider_events`; check Bolna's Webhook delivery health view after a real call.
- **Tests:** the test payload is received and stored; deliveries from non-allowlisted IPs (simulated by curl from elsewhere with the right token) behave per config.
- **Done when:** test delivery + one real call's events visible.
- **Depends on:** T10.3.  **Risks:** TLS/DNS delays.  **Blocks:** T10.5.

### T10.5 — Live end-to-end call in production · P0
- **Actions:** repeat the M1 procedure against the deployed system with a test line; verify logs, costs, timestamps; record in `docs/OPERATIONS.md`.
- **Tests:** the live test (`RUN_LIVE=1`) pointed at the production URL.
- **Done when:** passes; evidence committed.
- **Depends on:** T10.4.  **Risks:** none new.  **Blocks:** T11.x.

### T10.6 — Rollback, health checks, logs, cost notes · P0
- **Actions:** rehearse rollback (redeploy previous image, confirm migrations additive); alert/notes for `/health/ready` failures; where logs are read; write `docs/OPERATIONS.md` with restart procedure, wallet top-up check, opt-out handling procedure, and the measured cost per call from real data (never assumed).
- **Tests:** rollback rehearsal logged with outcome.
- **Done when:** doc complete; rehearsal done once.
- **Depends on:** T10.5.  **Risks:** none.  **Blocks:** T12.x.

---

## PHASE 11 — Demo hardening

### T11.1 — Lock the pilot business set and consents · P0 (B-01, B-05)
- **Actions:** final list ≥ 3 consenting businesses (or labelled test lines), each re-confirmed within the last few days; verify each number by a manual human call or message; confirm calling windows; confirm opt-out route; update `participation_status`/`consent_recorded_at`; update consent wording if S-9 changed disclosure.
- **Tests:** seed validation passes; `eligible()` returns exactly the intended set.
- **Done when:** `docs/PILOT_SET.md` (numbers masked) lists status per business.
- **Depends on:** T0.7, S-9.  **Risks:** B-01.  **Blocks:** T11.3.

### T11.2 — Choose the demo query and scripted shopkeeper roles · P0
- **Actions:** pick the single demo query (item/service + attributes + locality + radius); write `docs/DEMO_SCRIPT.md` with roles for test lines (available / unavailable / hesitant / not answering) so every demo type is covered.
- **Done when:** script reviewed by a second person.
- **Depends on:** T11.1.  **Risks:** none.  **Blocks:** T11.3.

### T11.3 — Rehearsal runs with measurements · P0 (AC-8)
- **Actions:** run the full demo ≥ 3 times from a clean browser profile; record per run: time to first result, total time, which calls connected, any anomalies; run `metrics_report.py`; keep numbers as measurements with n.
- **Done when:** `docs/REHEARSAL_LOG.md` has ≥ 3 runs; all anomalies have an issue or a fix.
- **Depends on:** T11.2, T10.5.  **Risks:** shop availability.  **Blocks:** T11.6.

### T11.4 — Tune the call script · P1 (R-06)
- **Actions:** use rehearsal transcripts (with consent) to shorten and clarify prompts; re-run S-8-style cases; version the prompt (`prompt_v2.md`) and sync to the dashboard.
- **Tests:** prompt-disclosure assertion (T5.4) still passes.
- **Done when:** measured improvement noted (n/N), or "no change needed".
- **Depends on:** T11.3.  **Risks:** over-tuning to friendly testers.  **Blocks:** no.

### T11.5 — Fallback tiers and pre-flight checklist · P0 (§38)
- **Actions:** verify demo-mode toggle end-to-end; prepare a dated screen recording of a real run (Tier 4); write the pre-flight checklist (wallet balance, webhook delivery health, agent prompt version equals repo version, tunnel/host up, phones charged and in range, browser clean profile, demo key ready, DB reachable); rehearse a deliberate failure (disable webhook) and recovery.
- **Done when:** checklist signed off on the day before presenting.
- **Depends on:** T10.6.  **Risks:** none.  **Blocks:** T11.6.

### T11.6 — Pitch and claim verification · P0 (AC-10; WP-20)
- **Actions:** write the pitch/narrative (Bible §37); build the claim table: each claim → screen/test/measurement; delete any claim without evidence; no accuracy %, time-saved, coverage or market-size claims unless measured and shown with n.
- **Done when:** claim table complete and reviewed.
- **Depends on:** T11.3.  **Risks:** none.  **Blocks:** T12.x.

### T11.7 — Clean-session full demo run · P0
- **Actions:** from a fresh clone on a fresh machine/profile (or container), follow README, deploy/run, and perform the full demo, including the failure moment.
- **Done when:** run recorded in `docs/REHEARSAL_LOG.md` with no manual interventions beyond README.
- **Depends on:** T11.5, T11.6.  **Risks:** hidden local state.  **Blocks:** T12.x.

---

## PHASE 12 — Submission readiness

### T12.1 — Verify official submission requirements and deadline · P0 (B-04)
- **Actions:** re-check the event page and any organiser communications; record format, deadline, judging criteria, eligibility, team rules in `docs/SUBMISSION.md` with sources and dates; adjust remaining tasks to them.
- **Done when:** document committed; Bible §21.2 updated; unknowns that remain are listed as unknown.
- **Depends on:** T0.7.  **Risks:** requirements arrive late.  **Blocks:** T12.6. **Start this early and repeat before submitting.**

### T12.2 — README and reproducibility · P0 (NFR-10; AC-9)
- **Actions:** README covers: what Sonar is and is not, honesty/consent model, architecture (diagram from Bible §16), setup (prereqs, `make setup`, `make db-up`, `make migrate`, `make seed`, `make run`, `make web-dev`), demo mode, env vars (names only), live-call setup (agent, extractions, webhook), tests, deployment pointer, limitations, license decision (log it).
- **Done when:** a teammate follows README from a clean clone to a running demo mode without help.
- **Depends on:** T10.2.  **Risks:** none.  **Blocks:** T12.6.

### T12.3 — Limitations and honest-claims document · P0
- **Actions:** `docs/LIMITATIONS.md`: pilot-scale, consenting businesses only, reported-not-verified, cancel semantics (no stop-call endpoint found), single-process orchestrator, no accounts, language coverage as tested, compliance not claimed, costs as measured.
- **Done when:** matches Bible §7.2/§31/§40 and the pitch.
- **Depends on:** T11.6.  **Risks:** none.  **Blocks:** T12.6.

### T12.4 — Metrics summary from real data · P1 (FR-32)
- **Actions:** run `metrics_report.py` over rehearsal and pilot calls; publish in `docs/METRICS.md` with n and dates; label rehearsal data as rehearsal; no baselines invented.
- **Done when:** every number has a denominator.
- **Depends on:** T9.8, T11.3.  **Risks:** tiny n (state it).  **Blocks:** no.

### T12.5 — Repository hygiene pass · P0
- **Actions:** `scripts/check_no_secrets.sh` over full history (`git log -p` scan or `git secrets`-style); remove real numbers/transcripts from fixtures; verify `.gitignore`; delete spike captures; confirm `data/businesses.example.yaml` contains placeholders only; license file.
- **Tests:** history scan clean.
- **Done when:** scan clean; if a secret was ever committed, **rotate it** and note in OPERATIONS.
- **Depends on:** T9.4.  **Risks:** leaked key in history (rotate).  **Blocks:** T12.6.

### T12.6 — Run the acceptance checklist and submit · P0
- **Actions:** execute the final checklist below; submit through the official channel before the verified deadline (or earlier than 2026-11-20 by a safe margin if still unknown); archive submission confirmation.
- **Done when:** confirmation saved.
- **Depends on:** T12.1–T12.5, T11.7.  **Risks:** B-04.  **Blocks:** —.

---

## 3. Final demo and acceptance checklist

**Acceptance (Bible §12)**
- [ ] AC-1 all 14 simulator scenarios pass in one run, 5× without flake (T9.1)
- [ ] AC-2 live M1 evidence committed (T6.7) and repeated in production (T10.5)
- [ ] AC-3 unanswered call shows "No answer", never "unavailable" (T7.2, T9.5)
- [ ] AC-4 duplicate webhook changes nothing (T9.2)
- [ ] AC-5 restart mid-search: correct state, no double dial (T9.3)
- [ ] AC-6 simulation banner + per-card tag cannot be hidden (T8.6)
- [ ] AC-7 no secrets in bundle/logs/responses (T9.4)
- [ ] AC-8 demo ran ≥ 3 times from a clean browser profile (T11.3, T11.7)
- [ ] AC-9 README reproduces setup from a clean clone (T12.2)
- [ ] AC-10 every pitch claim mapped to evidence (T11.6)

**Wave 2 acceptance (only for features enabled in the demo)**
- [ ] AC-11 simulator: `FAST` stops early on K exact confirmations, negatives never stop, `THOROUGH` runs all (T14.5, T14.7)
- [ ] AC-12 all `FEATURE_*` flags off: AC-1…AC-10 still pass (`make check`)
- [ ] AC-13 unmatched inbound caller quarantined and never rendered; matched one labelled and short-TTL (T16.6, only if S-12 = GO)
- [ ] AC-14 spoken text equals rendered text for every `ResultState` (T15.8)
- [ ] AC-15 digest suppresses counts below `DIGEST_MIN_K`, contains no identifiers or demo traffic (T16.1)
- [ ] AC-16 `docs/METRICS.md` shows ground-truth agreement n/N with inconclusives, or "not measured" (T17.4)
- [ ] M2 evidence committed (`docs/M2_EVIDENCE.md`); M3 evidence committed if the inbound line is in the demo

**Pre-flight on the day**
- [ ] Wallet balance covers the planned calls plus margin
- [ ] Production webhook URL set; delivery-health view clean
- [ ] Dashboard agent prompt version == `docs/agent/prompt_v*.md`
- [ ] Pilot businesses/test lines reachable; phones charged
- [ ] `/health/ready` OK; logs visible
- [ ] Demo query and roles ready (`docs/DEMO_SCRIPT.md`)
- [ ] Demo-mode toggle tested; banner visible
- [ ] Backup recording available (dated)
- [ ] Browser clean profile; access key at hand

**Never in the demo:** simulated data presented as live; a role-played test line presented as an independent shop; accuracy, savings or market claims without measurement; a business called without recorded consent. *(Wave 2)* A shop skipped by the stop rule described as unavailable; a self-report described as confirmed by a call; history described as today's availability; audio of a party who did not consent; a time-saved comparison without `docs/BASELINE_MANUAL.md`; a ground-truth percentage without n.

**Wave 2 pre-flight additions:** feature flags set exactly as rehearsed; `demo_audio_consent` true only for the lines announced to the room; inbound number and agent prompt version match the repo (if used); browser language support re-checked on the demo machine (S-14); digest pages open for the demo shop; metrics slide regenerated from the latest `metrics_report.py` run.

---

## 4. Cut line

If time runs short after M1, cut in this order (all are P1/P2; the optional sponsor annex, Phase 19, is cut before everything else): SSE (FR-35) → LLM parser (FR-36) → map (FR-36) → cache reuse (T7.4) → prompt tuning (T11.4) → metrics doc (T12.4) → retention tooling (T9.7) → ranking polish (T7.3 keeps tier order only). **Never cut:** consent checks, verify-by-pull, label honesty (T7.2/T9.5), duplicate/out-of-order handling (T6.2/T9.2), simulation labelling (T8.6), the clean-session run (T11.7).

**Wave 2 cut order** *(Wave 2)*, cut first to last, after M1 and only if time runs short: `/api/v1/ask` (T18.3) → watches (T18.2) → audio replay (T15.9) → question compiler (T18.1) → paired FAST/THOROUGH rehearsal (T17.5) → evidence replay (T15.5) → race clock (T15.4) → voice input (T15.7) → inbound line (T16.3–T16.6) → voice output (T15.8) → trust ledger (T15.6) → digest (T16.1–T16.2) → radar (T15.3) → ticker (T15.1–T15.2) → history line (T14.8) → **stop rule and learning loop (T14.x)**. The stop rule is last because it is the cheapest to build, needs no new Bolna capability, and is the most original idea in the product. **Never cut from Wave 2:** the not-called wording (T14.6), the flag isolation test (NFR-15), the ground-truth CLI if any accuracy number is shown (T17.1), and the k-anonymity floor if the digest is shown (T16.1).

## 5. Traceability (requirements → tasks)

| Requirement | Tasks |
|---|---|
| FR-01, FR-02, FR-03, FR-04 | T3.1, T3.2, T3.6 |
| FR-05, FR-06, FR-07 | T3.3–T3.5, T4.2 |
| FR-08–FR-10 | T2.2, T4.1, T4.2, T5.3 |
| FR-11–FR-14 | T6.1, T6.2, T6.3, T6.6, T4.5 |
| FR-15–FR-19 (FR-17 unknowns stay null: T6.4 rules V6–V8; FR-18 excerpt-only evidence, no audio/recording URL stored: T6.1 redaction, T6.3, T9.4 scan) | T6.4, T6.5, T7.1, T7.2 |
| FR-20 | T3.6, T6.5, T8.2 |
| FR-21, FR-22, FR-23 | T4.3, T4.1, T4.4 |
| FR-24 | T4.6, T6.4 |
| FR-25 | T5.2, T8.6 |
| FR-26 | T8.3–T8.8 |
| FR-27, FR-28, FR-29 | T3.6, T0.3, T3.6/T9.6 |
| FR-30–FR-36 (P1/P2) | T7.4, T7.3, T9.8, T9.8, T9.7 (partial), cut-line items |
| NFR-01–NFR-14 | T3.6, T6.1, T8.2, T9.2, T9.3, T4.1/T9.6, T9.4, T6.4/T8.5, T7.2/T9.5, T12.2, per-module coverage gates, T9.7, T0.3 |

---

# WAVE 2 — DIFFERENTIATORS (added in v2.0)

Wave 2 implements Bible Part II (§46–§56). **Nothing in Phases 14–18 starts before M1** (§0.4 rule 4). Phase 13 (documents and outreach) and spikes S-12…S-14 (test lines only) may run at any time. Every Wave 2 feature ships behind its `FEATURE_*` flag, default off (NFR-15). Baseline Definition of Done (§0.2) applies, plus: **the Part I suite must still pass with all flags off** (`make check` runs it with flags off; `make check-wave2` runs it with flags on).

New milestones: **M2 — "fewer calls, visible call"** (Phase 14 + T15.1–T15.4 + T15.8 on the simulator and on one real test-line call). **M3 — "shop-side loop"** (Phase 16 on test lines).

---

## PHASE S2 — Wave 2 spikes (test lines only; no app code)

Rules as Phase 1: throwaway scripts in `spikes/bolna/`, raw captures git-ignored until redacted, findings in `docs/FEASIBILITY.md`, calls only to verified team phones.

### S-12 — Inbound agent feasibility · P1 (resolves A-19, B-09)
- **Prerequisites:** S-1, S-3.
- **Actions:** read Bolna's inbound documentation (not read in v1); determine whether an inbound agent can be created, whether a number is available to us, and any KYC; place a call from a team phone; capture the webhook and Get Execution payloads; record which field carries the caller number and whether it is present for every call.
- **Done when:** A-19 and B-09 updated; **decision logged: Phase 16 inbound tasks GO / DEFERRED.**
- **Risks:** number unavailable or KYC needed (then T16.3–T16.6 stay DEFERRED; the digest still ships).

### S-13 — Live transcript, recording playback, monitoring · P1 (resolves A-20, A-21, A-22)
- **Prerequisites:** S-6, S-9.
- **Actions:** during an `in-progress` test call, poll `GET /executions/{id}` every 2 s and record whether and how the transcript grows (full vs partial, latency, speaker labels); check webhook payloads at each status for transcript fields; test whether `recording_url` plays in a browser tag and how long it lives; search the docs and dashboard for any live-monitoring or listen-in feature.
- **Done when:** the ticker design (T15.1) is fixed to what was actually observed; tiers T-2/T-3 marked GO / NO-GO.

### S-14 — Browser speech support · P1 (resolves A-23)
- **Actions:** on the demo machine and browser, test speech recognition and synthesis for English, Hindi, Kannada with scripted phrases (item names, numbers, "within 2 kilometres"); record accuracy as n/N correct fields.
- **Done when:** supported languages listed; unsupported ones hide their controls (T15.7).

---

## PHASE 13 — Positioning, customer discovery and consent script (documents; start any time) · P1

### T13.1 — Product ladder and business case document · P1
- **Purpose:** the story YC reviewers ask for, written as hypotheses (Bible §46, §47, D-043).
- **Actions:** write `docs/BUSINESS_CASE.md`: the ladder L1–L5, H-1…H-5 each with its cheapest test, who is not a customer, what would kill the idea. No market-size, savings or revenue numbers unless cited with a source and date.
- **Tests:** a doc-lint test greps for unsourced `%`, `crore`, `lakh`, `billion` and `TAM` outside quoted sources (`scripts/check_claims.sh`, shared with T11.6).
- **Done when:** doc committed; every hypothesis has a test and an owner.
- **Depends on:** — **Risks:** none.

### T13.2 — Customer discovery and consent A/B · P1 (resolves A-24, A-27)
- **Purpose:** find out whether payers and shops exist before building around them.
- **Actions:** (a) 3 conversations with potential payers (e-pharmacy, distributor, service marketplace, or a clinic receptionist): ask what they do today to check stock or capacity and what it costs; record verbatim. (b) outreach to shops with two scripts (plain, and digest-first); record yes/no per shop; n per arm. Store results in `docs/DISCOVERY_LOG.md` (names masked).
- **Done when:** A-24 and A-27 updated with n/N; if zero positive payer conversations, say so in `docs/BUSINESS_CASE.md`.
- **Depends on:** T0.7 (consent records). **Risks:** tiny n (state it).

### T13.3 — Consent script v2 and digest opt-in · P1 (FR-42)
- **Actions:** rewrite the consent script to lead with the digest, the AI-assistant disclosure, transcription and opt-out; add `digest_opt_in` and `demo_audio_consent` to the seed schema with a required `consent_note` whenever either is true.
- **Tests:** seed loader rejects `demo_audio_consent = true` without a note; rejects `digest_opt_in = true` without `consent_recorded_at`.
- **Done when:** baseline + tests.
- **Depends on:** T3.3. **Blocks:** T16.1.

---

## PHASE 14 — Stop rule and shop learning loop · P1 (FR-37…FR-40)

### T14.1 — Migration 0002 and enum parity · P1
- **Prerequisites:** M1.
- **Actions:** implement Bible §19.4 as Alembic `0002_wave2` (additive; Part I tables only gain columns); add `SearchMode`, `UpdateStatus`, `GroundTruthOutcome`; extend `ResultState` with `NOT_CALLED_STOP_RULE` and `DataOrigin` with `SHOP_SELF_REPORT`.
- **Tests:** upgrade/downgrade round trip; the enum-parity test (T2.1) now covers the new values; constraint tests (`mode` CHECK, `interval_minutes >= 120`, `UNIQUE (provider, provider_call_id)` on `shop_updates`); **all Part I constraint tests still pass.**
- **Done when:** baseline + tests; downgrade removes only Wave 2 objects.
- **Depends on:** M1.

### T14.2 — `business_stats` updater · P1 (FR-38)
- **Actions:** `services/stats.py`: pure `apply_attempt(stats, attempt, response|None, now) -> stats`; repository upsert in the finalizer's transaction; IST hour buckets; simulated attempts excluded.
- **Tests (unit):** each terminal status increments the right counters; hour-bucket boundaries in IST; simulated ignored; idempotent on a duplicate finalise (the second call changes nothing); coverage ≥ 90 %.
- **Done when:** baseline + coverage.
- **Depends on:** T14.1, T6.3.

### T14.3 — `PriorScorer` (pure) · P1 (FR-38; D-032, D-033)
- **Actions:** `services/priors.py`: `score(stats, hour_ist, category, distance_km, cfg) -> (priority_score, snapshot)`; cold start neutral; epsilon exploration implemented with an injected RNG for determinism; no function here can read or write answers.
- **Tests:** cold start orders by distance; high connection rate in the current hour outranks low; exploration promotes a lower-ranked shop at the configured rate over a seeded run; snapshot contains every input; property test: scores in [0, 1] and monotone in positive-answer rate.
- **Done when:** baseline + coverage ≥ 90 %.
- **Depends on:** T14.2.

### T14.4 — `StopRule` (pure) · P1 (FR-37; D-032)
- **Actions:** `services/stoprule.py`: `satisfied(responses, k) -> bool` exactly as Bible §48.2: distinct businesses, `LIVE_CALL` or fresh `CACHED_LIVE`, `REPORTED_AVAILABLE`, `exact_match=CONFIRMED`, `evidence_validated`, required fields non-null.
- **Tests (table-driven):** two positives from the same business count once; `UNCERTAIN`, `ALTERNATIVE_ONLY`, unavailable, no-answer never count; stale cached answers don't count; simulated doesn't count unless `demo_mode`; K=1 and K=3 boundaries; **no input produces `True` from negatives alone.**
- **Done when:** baseline + coverage ≥ 90 %.
- **Depends on:** T14.1.

### T14.5 — Wave dispatch in the orchestrator · P1 (FR-37, FR-38, NFR-06)
- **Actions:** in `FAST` mode, order `PENDING` attempts by `priority_score` and dispatch in waves capped by `MAX_CONCURRENT_CALLS`; after each finalised response evaluate `StopRule`; on satisfaction cancel remaining `PENDING` attempts with `failure_reason='STOP_RULE_SATISFIED'`, set `stopped_early` and `calls_avoided`, write an audit event; `THOROUGH` and `FEATURE_STOP_RULE=false` take the unchanged Part I path.
- **Tests (integration, simulator):** early stop with 3 positives among 8; `THOROUGH` calls all 8; concurrent finalisation of two positives cancels each remaining attempt exactly once; in-flight calls are recorded not interrupted; a business that opted out is never revived; flag off → identical dispatch order and counts to Part I (golden comparison).
- **Done when:** baseline + tests; AC-11 passes on the simulator.
- **Depends on:** T14.3, T14.4, T4.1, T6.3.

### T14.6 — Not-called state, copy and ledger source · P1 (FR-40, NFR-09)
- **Actions:** `derive_result_state` returns `NOT_CALLED_STOP_RULE` for attempts cancelled with that reason; copy added to `result_copy.py`; trust ledger source rows (T15.6) read the same fields.
- **Tests:** full cross product re-run; copy-lint: the new copy contains "does not mean it is unavailable" and never asserts unavailability; an attempt cancelled by the *user* is still `CANCELLED`, not `NOT_CALLED_STOP_RULE`.
- **Done when:** baseline + tests.
- **Depends on:** T14.5, T7.2.

### T14.7 — Simulator scenarios for Wave 2 · P1
- **Actions:** add scenarios: `stop_rule_early`, `stop_rule_negatives_dont_stop`, `thorough_all_called`, `prior_ordering_cold_vs_warm`, `exploration_promotes_one`; seeded and deterministic.
- **Tests:** each yields the expected `calls_avoided`, order and states.
- **Done when:** scenarios run inside `make e2e` (and inside T9.1's matrix).
- **Depends on:** T14.5, T5.2.

### T14.8 — History line API · P1 (FR-39; D-033)
- **Actions:** results include `history` only when `answered >= HISTORY_MIN_ANSWERED`; never present for simulated; never changes `result_state`; copy source in `result_copy.py`.
- **Tests:** below threshold → absent; simulated excluded; presence does not alter ranking; copy says "history" and includes n.
- **Done when:** baseline + tests.
- **Depends on:** T14.2, T6.5.

> **Milestone M2 (part 1):** the simulator demo shows an early stop and the real run records `calls_avoided`.

---

## PHASE 15 — Live and wow surfaces · P1

### T15.1 — Live transcript endpoint · P1 (FR-46; NFR-19)
- **Prerequisites:** M1, S-13, T14.1.
- **Actions:** `GET /api/searches/{id}/live` returns the last `LIVE_TICKER_LINES` lines for in-call attempts, built from what S-13 observed (partial transcript via Get Execution on the existing reconcile cadence, rate-limited ≥ 2 s per attempt); hidden unless the business is `TEAM_TEST_LINE` or `demo_audio_consent`; text-only, each line ≤ 200 chars, redacted of phone numbers.
- **Tests:** unflagged real business → no lines; test line → lines; numbers masked; provider partial data absent → empty list with `reason="no_live_text"` (never invented); flag off → 404; polling cap respected.
- **Done when:** baseline + tests.
- **Depends on:** S-13, M1.

### T15.2 — Ticker UI · P1
- **Actions:** per-call panel showing live lines with timestamps, "no live text yet" state, HTML-escaped plain text, `aria-live="polite"`.
- **Tests:** XSS fixture renders as text; empty state; screen-reader live region present.
- **Depends on:** T15.1, T8.4.

### T15.3 — Radar view · P1 (FR-50; D-038)
- **Actions:** pure `bearing_km(lat1, lng1, lat2, lng2)` helper beside haversine; SVG component with rings at 1/2/3 km (scaled to radius), centre marker, pins with text status labels, ping animation on start (`prefers-reduced-motion` disables animation); list view remains the accessible source of truth.
- **Tests:** bearing at known compass points within 1°; pin placement for fixtures; status text present on every pin; reduced-motion respected; no network request for tiles.
- **Done when:** component tests green; visual check at 390×844 and 1280×800.
- **Depends on:** T8.4, T3.4.

### T15.4 — Race clock and manual baseline · P1 (FR-51; D-041)
- **Actions:** timeline component of attempt start/answer/finish times; reads `docs/BASELINE_MANUAL.md` (a small front-matter file: `date`, `shops`, `minutes_median`, `n`, `method`, `measured_by`) via a build-time import; renders the comparison only when it exists and validates.
- **Tests:** file absent → no comparison text; malformed → no comparison text and a console warning; present → text includes date, shops and n.
- **Done when:** baseline + tests.
- **Depends on:** T8.5.

### T15.5 — Evidence replay with context window · P1 (FR-52; D-037)
- **Actions:** finalizer stores `evidence_context` (≤ 1500 chars around the validated quote, with the quote offsets); retention job purges it with excerpts; UI highlights the quote inside the context; fallback to the 600-char excerpt.
- **Tests:** quote offset inside the stored window; truncation at the cap; escaped render; purge boundary; context never stored for simulated rows beyond the scripted text.
- **Done when:** baseline + tests.
- **Depends on:** T6.4, T8.5, T9.7.

### T15.6 — Trust ledger panel · P1 (FR-53)
- **Actions:** `ledger_entries(results, attempts)` pure function mapping states and `validation_flags` to plain-language sentences from one copy module; panel lists each unclaimed shop and why (hedged, contradictory, evidence not found, price for another item, not called, no answer, failed).
- **Tests:** one fixture per flag and state; copy-lint (no "unavailable" for non-explicit states); every `validation_flags` value has a sentence (exhaustiveness test).
- **Done when:** baseline + tests.
- **Depends on:** T14.6, T7.2, T8.5.

### T15.7 — Voice input (client-side) · P1 (FR-48; D-036)
- **Prerequisites:** S-14.
- **Actions:** mic button feature-detects speech recognition; recognised text fills `query_text` and a fields preview; the user must press Search; unsupported languages hide their option; no audio leaves the browser through Sonar.
- **Tests:** unsupported browser → control hidden; recognised text never auto-submits; hostile transcript string is treated as inert text and goes through the same server validation.
- **Done when:** baseline + tests.
- **Depends on:** S-14, T8.3.

### T15.8 — Voice output (client-side) · P1 (FR-49, NFR-18; D-036)
- **Actions:** "Read summary" button speaks, in order: the ranking explanation and each top result's templated `answer_summary` plus its label; the spoken string is built from the same function that renders the text.
- **Tests:** for every `ResultState` fixture, `spoken === rendered`; unsupported browser → button hidden; `NOT_CALLED_STOP_RULE` and `NO_ANSWER` spoken with their non-misleading copy.
- **Done when:** baseline + tests; AC-14 passes.
- **Depends on:** T8.5, T14.6.

### T15.9 — Audio replay for flagged lines · P2 (FR-47; D-037)
- **Prerequisites:** S-13 GO for tier T-2.
- **Actions:** `GET /api/searches/{id}/attempts/{attempt_id}/audio` returns a short-lived redirect or streamed proxy; allowed only for `TEAM_TEST_LINE` or `demo_audio_consent`; no bytes written to disk or DB; the opening disclosure for flagged lines adds the audience sentence (prompt `v2`).
- **Tests:** unflagged real business → 403; test line → 200; filesystem and DB unchanged after a request (assertion); disclosure sentence present in the prompt file (T5.4 style).
- **Depends on:** S-13, T11.4.

> **Milestone M2 (part 2):** a real test-line call is visible on the radar and ticker, the stop rule is demonstrated, and the summary is read back. Record in `docs/M2_EVIDENCE.md`; apply the cut line (§4).

---

## PHASE 16 — Shop-side value: digest and inbound line · P1

### T16.1 — Digest generator · P1 (FR-41, NFR-16; D-034)
- **Actions:** `services/digest.py`: aggregate, per business and ISO week, the count of distinct live searches within that business's radius, grouped by `category` and structured item name; suppress any line with fewer than `DIGEST_MIN_K` contributors; exclude `demo_mode`, simulated and test-line-only traffic; include the business's own outcome ("you reported having it") only for that business.
- **Tests:** k-anonymity boundary (2 vs 3); demo/simulated excluded; no user id, IP or free text in the output (schema test); one business's digest never contains another business's name or answers.
- **Done when:** baseline + tests; AC-15 passes.
- **Depends on:** T13.3, T14.1.

### T16.2 — Digest page and opt-out · P1 (FR-41)
- **Actions:** `GET /api/shop/{digest_token}/digest` and `POST …/opt-out` (sets `OPTED_OUT`, writes an audit event, effect immediate on queued attempts); token rotation script; page shows no phone number; tokens are 32+ random bytes.
- **Tests:** unknown token → 404 envelope; opt-out cancels queued attempts across jobs; token not guessable (length/entropy check); page contains no `phone` field.
- **Depends on:** T16.1, T4.6.

### T16.3 — Inbound agent and prompt · P1 (FR-43; D-035)
- **Prerequisites:** S-12 = GO, M1.
- **Actions:** create the inbound agent in the dashboard; `docs/agent/inbound_prompt_v1.md` (identifies itself as an assistant, says calls are transcribed, asks item, attributes, quantity, price, never promises anything, ends politely); extraction fields mirror §23.4 where relevant; record the agent id as `BOLNA_AGENT_ID_INBOUND`.
- **Tests:** prompt-disclosure assertion; prompt forbids advice and commitments (string assertions).
- **Depends on:** S-12.

### T16.4 — Inbound webhook with verify-by-pull · P1 (FR-43, NFR-17)
- **Actions:** `POST /api/webhooks/bolna-inbound/{secret_token}` authenticated exactly like T6.1 (constant-time token, optional IP allowlist), raw event persisted, then **pull** the execution before using any field (D-005); caller number taken from the pulled record; caller-match against `businesses.phone_e164`.
- **Tests:** forged payload with a matching caller but a pulled record that disagrees → nothing written; unmatched → `QUARANTINED`; opted-out business → `REJECTED`; duplicate delivery → one row (`UNIQUE (provider, provider_call_id)`).
- **Depends on:** T16.3, T6.1.

### T16.5 — Self-report validation · P1 (FR-44)
- **Actions:** reuse validator rules V2–V8, V10, V13 for shop updates (evidence excerpt must appear in the transcript; numeric price must appear; unknowns stay null); per-business daily cap; `expires_at = answer_timestamp + SHOP_UPDATE_TTL_HOURS`; a nightly job sets `EXPIRED`.
- **Tests:** ≥ 20 transcript fixtures including hostile text; cap boundary; expiry boundary; quarantined rows never returned by any read endpoint (assertion over all routes).
- **Done when:** baseline + coverage ≥ 90 % for the new module.
- **Depends on:** T16.4, T6.4.

### T16.6 — Result merge, ranking and labels · P1 (FR-45; D-035)
- **Actions:** extend `ranking.py` so a self-report ranks with equally fresh live calls but after them; add `source` to result items; badge copy "Self-reported by the shop at HH:MM"; contradiction with a live answer from the last hour sets `SELF_REPORT_CONTRADICTS_CALL` and renders both.
- **Tests:** fresh self-report vs fresh live → live first; stale self-report excluded; contradiction rendered with both labels; no state where a self-report is labelled "reported by phone to Sonar's assistant".
- **Done when:** baseline + tests; AC-13 passes.
- **Depends on:** T16.5, T7.3, T8.5.

> **Milestone M3:** on test lines, a shop calls in, the update is validated and displayed with its own label, and a spoofed caller is quarantined. Record in `docs/M3_EVIDENCE.md`.

---

## PHASE 17 — Measurement and credibility · P1

### T17.1 — Ground-truth check CLI · P1 (FR-54; D-040)
- **Actions:** `scripts/ground_truth.py` lists unchecked `LIVE_CALL` responses, records `AGREE`/`DISAGREE`/`INCONCLUSIVE` with checker and method, refuses simulated rows, writes an audit event.
- **Tests:** simulated row rejected; unique `(response_id, checker)`; outcome stored; audit row written.
- **Depends on:** T14.1, T6.5.

### T17.2 — Wave 2 metrics in the report · P1 (§54.2)
- **Actions:** extend `scripts/metrics_report.py` with ground-truth agreement (n, inconclusive), stop-rule saving, coverage loss (paired runs), manual baseline, digest consent rate, self-report quarantine rate; every number prints its denominator; zero denominators print "n/a".
- **Tests:** fixtures with known answers give exact values; AC-16 text rendered ("not measured" when empty).
- **Depends on:** T17.1, T9.8.

### T17.3 — Manual baseline measurement · P1 (D-041)
- **Actions:** the team answers the demo query by hand (calling the same consenting lines) at least 3 times, timing each; write `docs/BASELINE_MANUAL.md` with date, shops, method, median and n.
- **Done when:** file validates against the loader in T15.4; if not done, the race clock stays comparison-free.
- **Depends on:** T11.2.

### T17.4 — Run the accuracy study · P1 (AC-16)
- **Actions:** verify at least the responses from rehearsal and pilot calls by independent means; publish `docs/METRICS.md` with agreement n/N, inconclusive count and every `DISAGREE` explained; add disagreements to `docs/LIMITATIONS.md`.
- **Done when:** AC-16 satisfied or "not measured" stated.
- **Depends on:** T17.1, T17.2, T11.3.

### T17.5 — Paired FAST/THOROUGH rehearsal · P1 (A-25, R-16)
- **Actions:** for the demo query, run `FAST` and `THOROUGH` back to back on test lines (or consented shops) at least 3 times; compare calls made, time to first useful result, and whether the nearest/cheapest answer was missed; log in `docs/REHEARSAL_LOG.md`.
- **Done when:** A-25 updated with n; coverage loss reported honestly.
- **Depends on:** T14.5, T11.3.

---

## PHASE 18 — Platform surfaces · P2

### T18.1 — Question compiler · P2 (FR-55; D-039; A-26)
- **Prerequisites:** M1, a decision-log entry approving the LLM dependency (Baseline DoD item 3).
- **Actions:** `QueryCompiler` interface; one LLM call (hosted API through `httpx`, key server-side only) producing a `ParsedQuery` candidate; the candidate is passed through `StructuredFormParser` unchanged; `POST /api/query/compile` never creates a job; UI shows the parsed fields for confirmation; compiled output never reaches `user_data` directly.
- **Tests:** ≥ 30 labelled queries (accuracy reported n/N); hostile text produces a clarification/refusal or inert data, never a changed prompt; blocked pharmacy terms still refuse; provider outage falls back to the structured form.
- **Done when:** A-26 resolved with n; otherwise the feature stays off.

### T18.2 — Standing watches · P2 (FR-56)
- **Actions:** `POST /api/watches`, watch page by token; scheduler enqueues a normal search at the cadence floor; caps and consent apply; state change recorded; expiry enforced.
- **Tests:** floor enforced; `max_polls` stops the watch; per-business daily cap shared with normal searches; expired watch makes no calls.
- **Depends on:** T14.1, T4.6.

### T18.3 — `POST /api/v1/ask` · P2 (FR-57)
- **Actions:** thin wrapper over search creation returning ranked results with `source`, timestamps, freshness, evidence refs, `stopped_early`; identical guardrails and key requirement.
- **Tests:** every guardrail test from T3.6/T9.6 re-run against the wrapper; no field absent from the base response is invented.
- **Depends on:** T3.6, T14.5.

---

## Wave 2 traceability

| Requirement | Tasks |
|---|---|
| FR-37, FR-40 | T14.4, T14.5, T14.6, T14.7 |
| FR-38, FR-39 | T14.2, T14.3, T14.8 |
| FR-41, FR-42 | T13.3, T16.1, T16.2 |
| FR-43, FR-44, FR-45 | S-12, T16.3, T16.4, T16.5, T16.6 |
| FR-46, FR-47, FR-52 | S-13, T15.1, T15.2, T15.5, T15.9 |
| FR-48, FR-49 | S-14, T15.7, T15.8 |
| FR-50, FR-51, FR-53 | T15.3, T15.4, T15.6 |
| FR-54 | T17.1, T17.2, T17.4 |
| FR-55, FR-56, FR-57 | T18.1, T18.2, T18.3 |
| NFR-15 | T14.1 (flags), `make check` / `make check-wave2` |
| NFR-16 | T16.1 |
| NFR-17 | T16.4, T16.5 |
| NFR-18 | T15.8 |
| NFR-19 | T15.1 |
| AC-11 | T14.5, T14.7 |
| AC-12 | `make check` with flags off |
| AC-13 | T16.6 |
| AC-14 | T15.8 |
| AC-15 | T16.1 |
| AC-16 | T17.2, T17.4 |
| A-24, A-27 | T13.2 |
| A-25 | T14.7, T17.5 |
| A-26 | T18.1 |

---

## PHASE 19 — Optional sponsor annex (P2, DEFERRED; added in v2.1)

Implements Bible §22.1 (D-023…D-030). **Never on the critical path:** no task here is a prerequisite of M1, M2, M3 or any Phase 0–18 task, and Baseline DoD item 3 still forbids new dependencies without a decision-log entry. If time is short, this phase is cut first (§4).

### SP-1 — Sponsor access and eligibility check · P2 (resolves B-07, B-08; supports D-025, D-030)
- **Prerequisites:** none (documents and accounts only; no calls).
- **Actions:** for Sarvam, Deepgram, Cartesia, Plivo and Exotel, record in `docs/SPONSORS.md`: whether the team can obtain access (signup terms read on the day, credits per the organisers' answer from T0.7), whether an India-registered business and KYC are required (B-07), and what Bolna's own configuration already exposes for that vendor (from Bolna's docs, with the URL and date). Assign each an integration status from Bible §0.1 (`PROPOSED`, `BLOCKED`, `UNVERIFIED`, `VERIFIED_NOT_IMPLEMENTED`). Do not call any sponsor API.
- **Tests:** a doc-lint test that every sponsor row has a status from the allowed vocabulary and a dated source (`scripts/check_claims.sh`).
- **Done when:** B-07 and B-08 each carry a current status; unknowns are listed as unknown.
- **Depends on:** T0.7. **Risks:** access or KYC unavailable (then the vendor stays `BLOCKED` and `NOT_MEASURED`; nothing else changes).

### T19.1 — Sponsor Lab harness · P2 (D-027; Bible §22.1)
- **Prerequisites:** M1, S-8 (language results), SP-1, and at least one variant beyond the default configured in Bolna.
- **Actions:** `spikes/sponsor_lab/` (kept out of `backend/app`): replay a fixed set of scripted utterances recorded by the team on test lines through each available agent variant; compute transcription correctness for item names and numbers (n/N), time to first spoken word, reported cost per minute and failure count; write results to `docs/SPONSOR_LAB.md` with a provenance label per cell (`MEASURED`, `DOCUMENTED`, `NOT_MEASURED`).
- **Rules:** test lines only; never a real business; never writes to `business_responses`, `business_stats` or the digest; no result is filled from vendor marketing material.
- **Tests:** the harness refuses a non-`TEAM_TEST_LINE` target; a cell without access renders `NOT_MEASURED`; the report lists n for every number.
- **Done when:** `docs/SPONSOR_LAB.md` committed with honest provenance, or the file states that nothing was measured.
- **Depends on:** SP-1, M1, S-8. **Risks:** small n (state it); variants differ by more than the model (record the configuration).

### Phase 19 traceability
| Item | Tasks |
|---|---|
| B-07, B-08, D-025, D-030 | SP-1 |
| D-024, D-026, D-027, D-029 | T19.1, SP-1 (claims lint) |
| Bible §22.1 | SP-1, T19.1 |
