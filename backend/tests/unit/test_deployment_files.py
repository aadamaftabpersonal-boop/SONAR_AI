"""Static checks on the deployment files: the properties that make a deployment safe."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DOCKERFILE = (ROOT / "backend" / "Dockerfile").read_text(encoding="utf-8")
COMPOSE = (ROOT / "docker-compose.prod.example.yml").read_text(encoding="utf-8")
IGNORE = (ROOT / ".dockerignore").read_text(encoding="utf-8")


def test_the_container_runs_as_a_non_root_user():
    assert re.search(r"^USER sonar$", DOCKERFILE, re.MULTILINE)
    assert "useradd" in DOCKERFILE


def test_exactly_one_worker_because_the_call_limit_lives_in_process():
    cmd = next(line for line in DOCKERFILE.splitlines() if line.startswith("CMD"))
    assert '"--workers", "1"' in cmd


def test_migrations_are_never_run_implicitly_by_the_app_container():
    cmd = next(line for line in DOCKERFILE.splitlines() if line.startswith("CMD"))
    assert "alembic upgrade" not in cmd
    assert 'command: ["alembic", "upgrade", "head"]' in COMPOSE
    assert "service_completed_successfully" in COMPOSE  # the app waits for the migration


def test_no_secret_or_local_data_is_baked_into_the_image():
    for needed in (".env", "data/businesses.local.yaml", "spikes/**/captures", ".git"):
        assert needed in IGNORE
    assert not re.search(r"^ENV .*(KEY|TOKEN|PASSWORD)=", DOCKERFILE, re.MULTILINE)
    assert "COPY .env" not in DOCKERFILE and "COPY data/ " not in DOCKERFILE


def test_the_image_serves_the_built_web_app_and_has_a_health_check():
    assert "FRONTEND_DIST=/app/frontend_dist" in DOCKERFILE
    assert "COPY --from=web /web/dist /app/frontend_dist" in DOCKERFILE
    assert "HEALTHCHECK" in DOCKERFILE and "/health/ready" in DOCKERFILE


def test_the_database_is_not_published_and_has_no_default_password():
    db = COMPOSE.split("  db:")[1].split("  migrate:")[0]
    assert "ports:" not in db
    assert "POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?" in db  # refuses to start without one
    assert "sonar:sonar" not in COMPOSE


def test_real_shop_data_is_mounted_read_only_not_copied():
    assert "businesses.local.yaml:/app/data/businesses.local.yaml:ro" in COMPOSE


def test_the_app_starts_only_with_an_env_file_and_restarts_on_failure():
    app = COMPOSE.split("  app:")[1].split("volumes:")[0]
    assert "env_file: .env.prod" in app and "restart: unless-stopped" in app


def test_the_dockerfile_installs_editable_so_the_config_folder_is_found():
    """app.config.ROOT is two levels above the package: a regular install would lose /app/config."""
    assert "pip install -e ./backend" in DOCKERFILE
    assert "COPY config ./config" in DOCKERFILE
