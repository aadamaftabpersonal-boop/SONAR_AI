"""Typed settings. Names are our convention (Bible D-020); defaults follow Bible 27.1 and 56."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    sonar_env: str = "dev"
    database_url: str = "postgresql+psycopg://sonar:sonar@localhost:55432/sonar"
    sonar_access_key: str = ""
    webhook_secret_token: str = ""
    bolna_api_key: str = ""
    bolna_api_base_url: str = "https://api.bolna.ai"
    bolna_from_phone_number: str = ""
    bolna_agent_id_pharmacy: str = ""
    bolna_agent_id_computer_repair: str = ""
    business_seed_path: str = "data/businesses.local.yaml"
    allowed_origins: str = "http://localhost:5173"
    log_level: str = "INFO"
    rate_limit_search_per_minute: int = 10

    # Bible 27.1 bounds
    max_targets_per_search: int = 5
    max_concurrent_calls: int = 2
    call_max_seconds: int = 120
    hangup_after_silence_seconds: int = 10
    max_attempts_per_business: int = 2
    search_deadline_seconds: int = 300
    reconcile_after_seconds: int = 90
    business_cooldown_minutes: int = 15
    business_daily_call_cap: int = 4
    global_daily_call_budget: int = 40

    # Orchestrator and webhook (Bible 27, 20.6)
    orchestrator_enabled: bool = True
    orchestrator_poll_seconds: float = 1.0
    retry_backoff_seconds: int = 120
    dispatch_stale_seconds: int = 60
    sim_step_seconds: float = 0.6  # pacing of simulated calls so the UI shows progress
    webhook_allowed_ips: str = ""  # comma-separated; empty disables the IP check
    webhook_max_body_bytes: int = 256 * 1024

    # Bible 28 per-field freshness (ASSUMPTION A-13, tune in rehearsal)
    freshness_ttl_availability_minutes: int = 60
    freshness_ttl_quantity_minutes: int = 30
    freshness_ttl_wait_minutes: int = 15
    freshness_ttl_open_minutes: int = 15
    freshness_ttl_price_minutes: int = 1440

    # Bible 56 (Wave 2); every feature is off until enabled (NFR-15)
    stop_rule_k: int = 2
    prior_min_observations: int = 5
    prior_exploration_epsilon: float = 0.15
    history_min_answered: int = 5
    digest_min_k: int = 3
    shop_update_max_per_day: int = 6
    shop_update_ttl_hours: int = 12
    live_ticker_lines: int = 6
    watch_min_interval_minutes: int = 120
    # Keep simulator runs out of the shop history by default so demos never pollute real stats
    # (D-022 extended). Tests and rehearsals of the learning loop switch it on.
    stats_include_simulated: bool = False
    feature_stop_rule: bool = False
    feature_history: bool = False
    feature_digest: bool = False
    feature_shop_line: bool = False
    feature_live_ticker: bool = False
    feature_audio_replay: bool = False
    feature_voice_ui: bool = False
    feature_compiler: bool = False
    feature_watches: bool = False


def bolna_agent_ids(settings: Settings) -> dict[str, str]:
    """Category -> Bolna agent id, for the categories that have one configured."""
    ids = {
        "pharmacy": settings.bolna_agent_id_pharmacy,
        "computer_repair": settings.bolna_agent_id_computer_repair,
    }
    return {category: agent for category, agent in ids.items() if agent}


@lru_cache
def get_settings() -> Settings:
    return Settings()
