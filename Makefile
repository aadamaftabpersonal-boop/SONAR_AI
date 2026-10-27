# POSIX equivalent of tasks.ps1 (Windows users: .\tasks.ps1 <task>)
PY := backend/.venv/bin/python

.PHONY: setup doctor db-up db-down run test test-int lint fmt secrets check check-wave2 e2e

setup:
	python3 -m venv backend/.venv
	$(PY) -m pip install --upgrade pip
	cd backend && .venv/bin/python -m pip install -e ".[dev]"

doctor:
	python3 --version; node --version; docker --version; git --version
	@python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 'Python 3.11+ needed')"
	@node -e "process.exit(+process.versions.node.split('.')[0] >= 22 ? 0 : 1)" || (echo "Node 22+ needed (.nvmrc)"; exit 1)

db-up:
	docker compose up -d --wait db

db-down:
	docker compose down

run:
	cd backend && .venv/bin/python -m uvicorn app.main:app --reload --port 8000

test:
	cd backend && .venv/bin/python -m pytest

test-int:
	cd backend && .venv/bin/python -m pytest -m integration

lint:
	cd backend && .venv/bin/python -m ruff check . && .venv/bin/python -m ruff format --check .

fmt:
	cd backend && .venv/bin/python -m ruff check --fix . && .venv/bin/python -m ruff format .

secrets:
	$(PY) scripts/check_no_secrets.py

claims:
	$(PY) scripts/check_claims.py

check-bundle:
	npm --prefix frontend run build
	$(PY) scripts/check_bundle.py

check: lint test secrets claims

# NFR-15 / AC-12: the Part I suite must also pass with every Wave 2 flag on
check-wave2:
	cd backend && FEATURE_STOP_RULE=true FEATURE_HISTORY=true FEATURE_DIGEST=true \
	  FEATURE_LIVE_TICKER=true FEATURE_VOICE_UI=true FEATURE_DISCOVERY=true FEATURE_OPT_IN=true \
	  .venv/bin/python -m pytest

# T8.8: browser journey against the running API (demo mode); see e2e/README.md
e2e:
	npm --prefix e2e test
