"""Refuse to deploy with a missing, default or weak configuration (Build Map T10.3).

    python scripts/check_prod_env.py               # checks the process environment
    python scripts/check_prod_env.py --env-file .env.prod

Exit code 1 means do not deploy. Warnings are advice and do not fail the check.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

WEAK = {
    "",
    "changeme",
    "change-me",
    "password",
    "secret",
    "test",
    "admin",
    "local-dev-key-not-secret",
    "local-dev-hook-token",
}
MIN_SECRET_LENGTH = 24
BOLNA_IPS = {"13.203.39.153", "13.126.9.249", "13.202.133.53"}


def _weak(value: str) -> str | None:
    value = value.strip()
    if value.lower() in WEAK:
        return "is empty or a known placeholder"
    if len(value) < MIN_SECRET_LENGTH:
        return f"is shorter than {MIN_SECRET_LENGTH} characters"
    if len(set(value)) < 8:
        return "has too little variety to be random"
    return None


def check(env: dict[str, str]) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    def get(name: str) -> str:
        return env.get(name, "").strip()

    if get("SONAR_ENV") != "prod":
        errors.append("SONAR_ENV must be 'prod'")
    for name in ("SONAR_ACCESS_KEY", "WEBHOOK_SECRET_TOKEN"):
        problem = _weak(get(name))
        if problem:
            errors.append(
                f'{name} {problem}; generate one with `python -c "import secrets; print(secrets.token_urlsafe(32))"`'
            )

    db = get("DATABASE_URL")
    if not db:
        errors.append("DATABASE_URL is not set")
    elif "sonar:sonar@" in db:
        errors.append("DATABASE_URL still uses the default sonar:sonar credentials")

    origins = [o.strip() for o in get("ALLOWED_ORIGINS").split(",") if o.strip()]
    if not origins:
        errors.append("ALLOWED_ORIGINS is not set (use the public https URL of the app)")
    for origin in origins:
        if origin == "*":
            errors.append("ALLOWED_ORIGINS must not be '*'")
        elif not origin.startswith("https://"):
            errors.append(f"ALLOWED_ORIGINS entry {origin!r} must be https in production")

    live = bool(get("BOLNA_API_KEY"))
    agents = [k for k, v in env.items() if k.startswith("BOLNA_AGENT_ID_") and v.strip()]
    if live and not agents:
        errors.append("BOLNA_API_KEY is set but no BOLNA_AGENT_ID_<CATEGORY> is")
    if agents and not live:
        errors.append("a BOLNA_AGENT_ID_* is set but BOLNA_API_KEY is not")
    if not live:
        warnings.append("live calling is off (no Bolna key): only demo mode will work")
    if live:
        allowed = {ip.strip() for ip in get("WEBHOOK_ALLOWED_IPS").split(",") if ip.strip()}
        if not allowed:
            warnings.append(
                "WEBHOOK_ALLOWED_IPS is empty; consider "
                + ",".join(sorted(BOLNA_IPS))
                + " (the token still protects the endpoint)"
            )
        elif not allowed & BOLNA_IPS:
            warnings.append("WEBHOOK_ALLOWED_IPS contains none of Bolna's documented IPs")
        try:
            budget = int(get("GLOBAL_DAILY_CALL_BUDGET") or "40")
        except ValueError:
            errors.append("GLOBAL_DAILY_CALL_BUDGET is not a number")
        else:
            if budget > 200:
                warnings.append(
                    "GLOBAL_DAILY_CALL_BUDGET is above 200; is that what you can afford?"
                )
    if not get("FRONTEND_DIST"):
        warnings.append("FRONTEND_DIST is not set, so the API will not serve the web app")
    return errors, warnings


def load_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            values[key.strip()] = value.strip().strip("'\"")
    return values


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path)
    args = parser.parse_args(argv)
    env = load_env_file(args.env_file) if args.env_file else dict(os.environ)
    errors, warnings = check(env)
    for w in warnings:
        print(f"warning: {w}")
    for e in errors:
        print(f"ERROR: {e}")
    if errors:
        print(f"\n{len(errors)} problem(s): do not deploy.")
        return 1
    print("production config: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
