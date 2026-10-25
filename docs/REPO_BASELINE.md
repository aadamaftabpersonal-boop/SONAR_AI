# Repo baseline (T0.1, recorded 2026-10-25)

## What existed
- `SONAR_BIBLE_v2.md`, `SONAR_BUILD_MAP_v2.md` (the plan, v2.1). Originals `SONAR_BIBLE.md` / `SONAR_BUILD_MAP.md` live one level up in `D:\` and are not part of this project.
- `.claude/` (editor settings). Ignored for the build.
- No application code, no git repository of its own. `D:\` is itself a git repository that tracks nothing; this project gets its own repo (`git init` inside `D:\bolnabuildathon`).

## Toolchain found (T0.2)
| Tool | Version | Note |
|---|---|---|
| Python | 3.14.6 (also 3.11 via uv) | Bible suggested 3.12; 3.14 installs every approved dependency, so `.python-version` is `3.14`. `requires-python >= 3.11`. |
| Node | 24.18.0 | Needed from Phase 8 only. |
| Docker | 29.6.1 | Compose v2 works. |
| make | not installed | `tasks.ps1` mirrors the `Makefile`. |

## Decisions made while setting up
- **Database port 55432, not 5432.** Two native PostgreSQL servers already listen on 5432 and 5433 on this machine and shadow the container. The container publishes on `POSTGRES_PORT` (default 55432). Do not point Sonar at a native instance.
- **Secret check is Python** (`scripts/check_no_secrets.py`), not a shell script, so it runs on Windows and in CI.
- **Real phone numbers and keys** stay in `.env` and `data/businesses.local.yaml`, both git-ignored.

## Reuse / ignore
| Item | Decision |
|---|---|
| Bible and Build Map v2 | Reuse as the source of truth |
| `.claude/` | Ignore |
