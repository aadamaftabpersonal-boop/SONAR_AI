# POSIX equivalent of tasks.ps1 (Windows users: .\tasks.ps1 <task>)
PY := backend/.venv/bin/python

.PHONY: setup doctor db-up db-down run test test-int lint fmt secrets check

setup:
	python3 -m venv backend/.venv
	$(PY) -m pip install --upgrade pip
	cd backend && .venv/bin/python -m pip install -e ".[dev]"

doctor:
	python3 --version; docker --version; git --version

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

check: lint test secrets
