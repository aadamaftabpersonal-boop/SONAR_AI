# Handoff: Sonar, 2026-10-29

From Russel, for whoever picks this up next. Read this first, then `CLAUDE.md` (rules, stack,
commands) and the two source-of-truth docs it points to. Everything below was re-checked on
2026-10-29 against `main` at `f21829b`, which is pushed (`origin/main` = local `main`).

## TL;DR

- **The code is in good shape.** All suites pass with default flags: 691 backend unit, 225
  integration (real Postgres, migrations 0001→0006), 134 frontend, ruff, tsc, build.
- **Custom questions (D-062) is merged into `main`.** `CLAUDE.md` still says it isn't. See "CLAUDE.md
  is partly stale" below.
- **The blocker is not code, it is M1.** No real call has gone through the whole app yet (search →
  Bolna → webhook → finalizer → validator → results). The Bolna agent has no webhook URL. Do that
  before any new feature.
- **The deadline may be 31 Oct 2026** (`docs/SUBMISSION.md`, unconfirmed). Confirm it with the
  organisers today.

## Getting set up on your machine

Needs Python 3.11+ (3.12 used here), Node 24, Git, and **Docker Desktop running** (Postgres lives
in Docker on port **55432**).

```powershell
.\tasks.ps1 setup                       # backend venv + deps
.\tasks.ps1 db-up                       # Postgres 16 on 55432
cd backend; .\.venv\Scripts\alembic upgrade head; cd ..
cd frontend; npm install; cd ..         # NOT `npm --prefix frontend install`; that breaks on Windows npm 9
copy .env.example .env                  # then fill in the Bolna values (ask Russel/Aadam, never commit)
```

Then check that everything is green:

```powershell
.\tasks.ps1 check          # lint + unit + secret scan + claims scan
.\tasks.ps1 test-int       # integration, needs the db
cd frontend; npm test; npm run lint; npm run build; cd ..
```

## Verified on 2026-10-29

| Suite | Result |
| --- | --- |
| Backend unit (`tasks.ps1 test`) | 691 passed |
| Backend integration (`tasks.ps1 test-int`) | 225 passed |
| Migrations | at `0006 (head)` |
| ruff check + format | clean |
| Frontend Vitest | 134 passed (11 files) |
| Frontend `tsc -b` | clean |
| Frontend oxlint | 0 errors, 2 warnings (`QuestionBuilder.tsx:16` only-export-components, `Ticker.tsx:49` setState in effect) |
| Unit tests with all 13 `FEATURE_*` flags on | 691 passed |
| Playwright e2e (`e2e/`) | **never run** (needs API + web running and `SONAR_ACCESS_KEY`) |

## Known test issues (small, worth fixing first)

1. **Logging is wiped when unit and integration tests run in one process.** `pytest -m "not live"`
   gives 915 passed and 1 failed:
   `tests/unit/test_bolna_provider.py::test_logs_never_contain_the_key_or_the_full_number`.
   Cause: `backend/alembic/env.py` calls `fileConfig(config.config_file_name)`, whose default
   `disable_existing_loggers=True` silences `sonar.bolna` once the integration fixtures run
   migrations in-process. Fix: `fileConfig(config.config_file_name, disable_existing_loggers=False)`.
   It doesn't show up in `tasks.ps1 test` / `test-int` because they run separately. Production is
   unaffected (compose runs alembic as its own process), but fix it anyway.
2. **The all-flags-on run (NFR-15) has 9 more failures that are expected, not bugs.** They are tests
   of the *flag-off* path (`test_flag_off_calls_again`, `test_discover_is_off_by_default`,
   `test_history_is_off_by_default`, the digest/opt-in "looks like 404 when off" tests, …) and they
   read the process environment, so forcing `FEATURE_*=true` overrides the setting they rely on.
   `test_concurrency_cap_is_never_exceeded` hits the stop rule (stops after `stop_rule_k = 2`
   yeses, so 2 calls, not 5). Suggested fix: those tests should clear `FEATURE_*` env vars with
   `monkeypatch` (as `tests/unit/test_config.py` now does) or build `Settings` with explicit flags.
   Until then `check-wave2` in `tasks.ps1`/`Makefile` only runs the unit tests and only turns on 7
   of the 13 flags. Add `FEATURE_CACHE_REUSE` and `FEATURE_CUSTOM_QUESTIONS` to that list.

## CLAUDE.md is partly stale (update it in your first commit)

- The section "Custom questions (D-062, commit `dd0f5fa`) — NOT on this branch" is now wrong. It
  was merged in `05a3766`, and `f21829b` fixed a test in it that had broken 16 others.
  `services/general.py`, `QuestionBuilder.tsx`, `docs/agent/prompt_general_v1.md` and migration
  0006 all exist.
- "Still never run: `check-wave2`" now has results; see above.
- "Next free decision id: **D-062**": that id is used. The next one is **D-063**.
- In the Bolna table, the "Sonar General" agent was wired into `BOLNA_AGENT_ID_COMPUTER_REPAIR` as
  a stopgap. Now that `BOLNA_AGENT_ID_GENERAL` exists in `app/config.py`, move it there and leave
  computer-repair empty until a real agent exists. Otherwise a computer-repair search dials a shop
  with the wrong prompt. (I didn't check the current `.env`; please do.)
- "What to do next" step 1 (verify, push) is done.

## What to do next, in order

1. **Fix the two test issues above** (about 30 minutes) and update `CLAUDE.md`.
2. **Finish the Bolna agent** (our trial account; check the wallet balance first):
   - Pharmacy agent: check its voice, transcriber, call settings and the 11 extraction names
     against `docs/agent/prompt_v1.md` (§1–§3). Nobody has checked this yet.
     `backend/_bolna_probe.py` (local, untracked, read-only) prints the agent config for this.
     Run it from `backend/` with the venv python.
   - General agent ("Sonar General"): prompt from `docs/agent/prompt_general_v1.md`, extraction
     `answers_json`, put its id in `BOLNA_AGENT_ID_GENERAL`.
   - `BOLNA_FROM_PHONE_NUMBER` was empty. On the trial plan only verified numbers can be called,
     so verify the team phones in the Bolna dashboard.
3. **Webhooks (spikes S-3/S-5).** Start a tunnel (cloudflared or ngrok) and run
   `spikes/bolna/webhook_capture.py`. Set the agent's webhook URL to
   `https://<tunnel-host>/api/webhooks/bolna/<WEBHOOK_SECRET_TOKEN>`. Place 3 calls (answered,
   ring-out, hang-up mid-sentence) and record the results in `docs/FEASIBILITY.md` S-3, S-5, S-8.
4. **G1 decision (S-11), then M1:** one real call through the app, 4 runs, evidence in
   `docs/M1_EVIDENCE.md`. Opt-in live test: `RUN_LIVE=1` with `pytest -m live
   tests/live/test_m1_live.py`. Then apply the cut line from the Build Map §4.
5. **Run the e2e test once** (`.\tasks.ps1 e2e` with API on :8000, web on :5173, `SONAR_ACCESS_KEY`
   set).
6. Deploy (Phase 10), rehearse 3× (`docs/REHEARSAL_LOG.md`), record a backup video, run once from a
   clean clone, submit (`docs/SUBMISSION.md`).

Custom questions has only run against the simulator. Prove M1 with the pharmacy agent before
putting a real call through the general agent.

## Rules you must not break (short version; full list in CLAUDE.md)

- No call to a shop without recorded consent. The AI never asks a shop for permission.
- Silence, failure or "not sure" is never shown as "unavailable".
- Never trust a webhook body. The finalizer re-fetches the execution from Bolna.
- No secrets or real phone numbers in git. `.env` is ignored. Tests use `+91 00000xxxxx`, and
  `scripts/check_no_secrets.py` enforces it.
- Every new feature goes behind a `FEATURE_*` flag, default off.
- Commits start with the Build Map task id (`T7.4: ...`), one topic per commit.

## Loose files in Russel's folder (not in git, don't look for them)

- `verify_all.ps1` / `verify_log.txt`: local all-in-one check script. Russel's copy has two fixes:
  `${name}:` on line 26 (the original doesn't parse), and the npm `--prefix install` problem is
  still in it. The commands above do the same thing.
- `claude-work.bundle`: the D-062 commit as a git bundle. Already merged, safe to delete.
- `backend/_bolna_probe.py`: the read-only agent probe from step 2.

## Remote branches

- `origin/main`: current, includes everything above.
- `origin/claude/build-map-and-map-feature` and `origin/custom-questions`: both merged into
  `main`, can be deleted once Aadam agrees.

## People

- Repo owner: Aadam (`aadamaftabpersonal-boop/SONAR_AI`). The 2026-10-25 calls used his Bolna account.
- Russel: this handoff. The current Bolna agents are in Russel's own trial account. Ask him for
  access or the keys over a private channel.
- Credits requested 2026-10-27: Bolna +$15, Sarvam $10, Deepgram $10 (status unknown; check).
