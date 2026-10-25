"""The production-config check and the bundle secret scan: they exist to say no, so test no."""

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


prod = load("check_prod_env")
bundle = load("check_bundle")

STRONG_A = "Xk3pQ9vL2mT7rW5yB8nD4hJ6cF1gZ0aS"
STRONG_B = "Rq7Yt2Ue5Io9Pl3Kj6Hg1Fd4Sa8Zx0Cv"


def good_env(**over):
    env = {
        "SONAR_ENV": "prod",
        "SONAR_ACCESS_KEY": STRONG_A,
        "WEBHOOK_SECRET_TOKEN": STRONG_B,
        "DATABASE_URL": "postgresql+psycopg://sonar:Zr4Tn8Qw2Lp6Vb0Mc@db:5432/sonar",
        "ALLOWED_ORIGINS": "https://sonar.example.org",
        "FRONTEND_DIST": "/app/frontend_dist",
        "BOLNA_API_KEY": "sk-live-abcdefghijklmnop",
        "BOLNA_AGENT_ID_PHARMACY": "agent-1",
        "WEBHOOK_ALLOWED_IPS": "13.203.39.153,13.126.9.249,13.202.133.53",
    }
    env.update(over)
    return env


# --- production config -----------------------------------------------------------------------


def test_a_good_config_passes_cleanly():
    errors, warnings = prod.check(good_env())
    assert errors == [] and warnings == []


@pytest.mark.parametrize("secret", ["SONAR_ACCESS_KEY", "WEBHOOK_SECRET_TOKEN"])
@pytest.mark.parametrize(
    "bad", ["", "changeme", "local-dev-key-not-secret", "short", "a" * 40, "ab" * 20]
)
def test_weak_or_missing_secrets_are_refused(secret, bad):
    errors, _ = prod.check(good_env(**{secret: bad}))
    assert any(secret in e for e in errors)


def test_the_environment_must_be_prod():
    assert any("SONAR_ENV" in e for e in prod.check(good_env(SONAR_ENV="dev"))[0])


def test_default_database_credentials_are_refused():
    errors, _ = prod.check(good_env(DATABASE_URL="postgresql+psycopg://sonar:sonar@db:5432/sonar"))
    assert any("default" in e for e in errors)
    assert any("DATABASE_URL" in e for e in prod.check(good_env(DATABASE_URL=""))[0])


@pytest.mark.parametrize(
    "origins", ["", "*", "http://example.org", "https://ok.org,http://bad.org"]
)
def test_origins_must_be_explicit_and_https(origins):
    assert any("ALLOWED_ORIGINS" in e for e in prod.check(good_env(ALLOWED_ORIGINS=origins))[0])


def test_a_key_without_an_agent_and_an_agent_without_a_key_are_both_refused():
    no_agent = good_env()
    del no_agent["BOLNA_AGENT_ID_PHARMACY"]
    assert any("no BOLNA_AGENT_ID" in e for e in prod.check(no_agent)[0])
    no_key = good_env(BOLNA_API_KEY="")
    assert any("BOLNA_API_KEY is not" in e for e in prod.check(no_key)[0])


def test_demo_only_deployment_is_allowed_with_a_warning():
    env = good_env(BOLNA_API_KEY="")
    del env["BOLNA_AGENT_ID_PHARMACY"]
    errors, warnings = prod.check(env)
    assert errors == [] and any("demo mode" in w for w in warnings)


def test_advice_not_failures_for_optional_hardening():
    _, warnings = prod.check(good_env(WEBHOOK_ALLOWED_IPS="", FRONTEND_DIST=""))
    assert any("WEBHOOK_ALLOWED_IPS" in w for w in warnings)
    assert any("FRONTEND_DIST" in w for w in warnings)
    _, warnings = prod.check(good_env(WEBHOOK_ALLOWED_IPS="1.2.3.4"))
    assert any("none of Bolna's" in w for w in warnings)


def test_a_non_numeric_budget_is_an_error():
    assert any(
        "GLOBAL_DAILY_CALL_BUDGET" in e
        for e in prod.check(good_env(GLOBAL_DAILY_CALL_BUDGET="lots"))[0]
    )


def test_the_cli_exit_codes(tmp_path, capsys):
    ok = tmp_path / "ok.env"
    ok.write_text("\n".join(f"{k}={v}" for k, v in good_env().items()), encoding="utf-8")
    assert prod.main(["--env-file", str(ok)]) == 0
    bad = tmp_path / "bad.env"
    bad.write_text("SONAR_ENV=dev\n", encoding="utf-8")
    assert prod.main(["--env-file", str(bad)]) == 1
    assert "do not deploy" in capsys.readouterr().out


def test_the_secrets_in_the_real_dev_env_would_not_pass_production():
    """Guard: the local dev values must never be mistaken for deployable ones."""
    local = {"SONAR_ENV": "dev", "SONAR_ACCESS_KEY": "local-dev-key-not-secret"}
    assert prod.check(local)[0]


# --- bundle scan -----------------------------------------------------------------------------


def make_dist(tmp_path, files):
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<html></html>", encoding="utf-8")
    for name, text in files.items():
        (dist / "assets" / name).write_text(text, encoding="utf-8")
    return dist


def test_a_clean_bundle_passes(tmp_path):
    dist = make_dist(tmp_path, {"app.js": "fetch('/api/searches',{headers:{'X-Sonar-Key':k}})"})
    assert bundle.scan_bundle(dist, {"SONAR_ACCESS_KEY": STRONG_A}) == []


def test_a_configured_secret_value_in_the_bundle_is_caught(tmp_path):
    dist = make_dist(tmp_path, {"app.js": f"const k='{STRONG_A}'"})
    found = bundle.scan_bundle(dist, {"SONAR_ACCESS_KEY": STRONG_A})
    assert any("value of SONAR_ACCESS_KEY" in f for f in found)


@pytest.mark.parametrize(
    ("snippet", "label"),
    [
        ("sk-abcdefghijklmnopqrstuv", "API-key-shaped"),
        ("Authorization: Bearer abcdefghijklmnopqrstuvwxyz", "bearer"),
        ("a" * 32 + "", "long hex"),
        ("call +91 98765 43210 now", "phone"),
        ("https://api.bolna.ai/call", "direct provider"),
        ("postgresql+psycopg://u:p@h/db", "database"),
        ("process.env.BOLNA_API_KEY", "secret variable"),
    ],
)
def test_secret_shaped_content_is_caught(tmp_path, snippet, label):
    dist = make_dist(tmp_path, {"app.js": snippet})
    found = bundle.scan_bundle(dist, {})
    assert found, label


def test_short_secret_values_are_not_matched_against_ordinary_text(tmp_path):
    dist = make_dist(tmp_path, {"app.js": "const x = 'abc'"})
    assert bundle.scan_bundle(dist, {"SONAR_ACCESS_KEY": "abc"}) == []  # too short to be a secret


def test_binary_files_are_skipped(tmp_path):
    dist = make_dist(tmp_path, {})
    (dist / "assets" / "logo.png").write_bytes(b"\x89PNG" + STRONG_A.encode())
    assert bundle.scan_bundle(dist, {"SONAR_ACCESS_KEY": STRONG_A}) == []


def test_missing_build_is_a_distinct_error(tmp_path):
    assert bundle.main([str(tmp_path / "nothing")]) == 2


def test_cli_returns_one_on_findings_and_zero_when_clean(tmp_path):
    dirty = make_dist(tmp_path, {"app.js": "https://api.bolna.ai"})
    assert bundle.main([str(dirty)]) == 1
    clean = tmp_path / "c"
    (clean).mkdir()
    (clean / "index.html").write_text("<html></html>", encoding="utf-8")
    assert bundle.main([str(clean)]) == 0
