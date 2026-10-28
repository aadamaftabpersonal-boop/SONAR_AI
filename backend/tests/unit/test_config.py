import os

from app.config import Settings


def make_settings() -> Settings:
    # ignore any local .env so the test checks the code defaults
    return Settings(_env_file=None)


def test_defaults_match_bible_27_1():
    s = make_settings()
    assert s.max_targets_per_search == 5
    assert s.max_concurrent_calls == 2
    assert s.call_max_seconds == 120
    assert s.hangup_after_silence_seconds == 10
    assert s.max_attempts_per_business == 2
    assert s.search_deadline_seconds == 300
    assert s.reconcile_after_seconds == 90
    assert s.business_cooldown_minutes == 15
    assert s.business_daily_call_cap == 4
    assert s.global_daily_call_budget == 40


def test_wave2_features_off_by_default(monkeypatch):
    # check-wave2 turns every FEATURE_* on in the environment; the code defaults must still be off
    for name in list(os.environ):
        if name.upper().startswith("FEATURE_"):
            monkeypatch.delenv(name)
    s = make_settings()
    flags = {k: v for k, v in s.model_dump().items() if k.startswith("feature_")}
    assert flags, "expected feature flags to exist"
    assert not any(flags.values())


def test_wave2_defaults_match_bible_56():
    s = make_settings()
    assert s.stop_rule_k == 2
    assert s.prior_exploration_epsilon == 0.15
    assert s.digest_min_k == 3
    assert s.watch_min_interval_minutes == 120
