# Sonar

Search the real world by calling it. Sonar phones a small set of **consenting** businesses with a voice agent, extracts structured answers, validates them, and shows what each business *reported*, with evidence and timestamps. It reports; it does not guarantee.

Plan: `SONAR_BIBLE_v2.md` (what and why) and `SONAR_BUILD_MAP_v2.md` (order and checks).

## Status
Phase 0 (setup) done: backend scaffold, typed config, secret check, local Postgres. Next: Phase 1, the Bolna feasibility spike (needs an account, API key and a verified test phone).

## Prerequisites
Python 3.11+, Docker with Compose, Git. (Node 22+ from Phase 8.)

## Setup (Windows)
```powershell
.\tasks.ps1 setup      # venv + dependencies
copy .env.example .env # then edit if needed
.\tasks.ps1 db-up      # Postgres on localhost:55432
.\tasks.ps1 check      # lint + unit tests + secret scan
.\tasks.ps1 test-int   # needs db-up
.\tasks.ps1 run        # http://localhost:8000/health
```
On macOS/Linux use `make setup`, `make db-up`, `make check`, and so on.

## Notes
- The database uses port **55432** because other PostgreSQL servers commonly occupy 5432/5433.
- Never commit `.env`, real phone numbers or transcripts. `.\tasks.ps1 secrets` scans for them.
- No live call is placed to anyone who has not consented (Bible D-004).
