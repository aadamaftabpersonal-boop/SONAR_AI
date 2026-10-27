# Milestone M1 evidence (Build Map T6.7)

**Status: not reached.** M1 means one real call travels the whole of Sonar: a search through the
API, a dispatch by the orchestrator, Bolna's webhook, the finalizer's pull of the execution record,
the validator, and a result readable through `GET /api/searches/{id}/results`. Spike-script calls
do not count.

Two people review this file before it counts. No phone numbers, no recording links, no full
transcripts of anyone outside the team.

## Prerequisites (tick before the first run)

- [ ] Webhook reaches the API: tunnel or host URL set in the agent as
      `https://<host>/api/webhooks/bolna/<WEBHOOK_SECRET_TOKEN>` (spike S-3 passed)
- [ ] `.env`: `BOLNA_API_KEY`, `BOLNA_AGENT_ID_PHARMACY`, `SONAR_ACCESS_KEY`, `WEBHOOK_SECRET_TOKEN`
- [ ] `data/businesses.local.yaml` has the verified team phone as a `TEAM_TEST_LINE` with
      `consent_recorded_at` set, and it is seeded (`scripts/seed_businesses.py`)
- [ ] Only that one test line is inside the search radius, so exactly one call is placed
- [ ] The agent in the dashboard matches `docs/agent/prompt_v1.md` (or the newer version in use)
- [ ] Wallet balance noted: ______ (before) / ______ (after), which also confirms the cost unit

## The four runs

Run the API (`make run` or `tasks.ps1 run`), then for each run:

```powershell
$env:RUN_LIVE="1"; $env:SONAR_ACCESS_KEY="..."; $env:M1_LAT="..."; $env:M1_LNG="..."
$env:M1_EXPECT="REPORTED_AVAILABLE"   # change per run
$env:DATABASE_URL="postgresql+psycopg://sonar:sonar@localhost:55432/sonar"
cd backend; .\.venv\Scripts\python -m pytest -m live tests\live -s
```

Answer the phone as the shopkeeper and play the line for that run. Paste the printed summary below.

| # | Play | `M1_EXPECT` | Passed? | Seconds | Notes |
|---|---|---|---|---|---|
| 1 | "Yes, exactly that, forty two rupees." | `REPORTED_AVAILABLE` | | | |
| 2 | "No, it's finished." | `REPORTED_UNAVAILABLE` | | | |
| 3 | "Maybe... I'm not sure." | `UNCERTAIN` | | | |
| 4 | Let it ring out | `NO_ANSWER` | | | |

### Run 1 output

```
(paste)
```

### Run 2 output

```
(paste)
```

### Run 3 output

```
(paste)
```

### Run 4 output

```
(paste)
```

## Sign-off

- Reviewed by: ______ and ______, date ______
- Anything that differed from the expected state, and what was fixed:
- Cut-line decision (Build Map §0.5), recorded in the Bible decision log on: ______
