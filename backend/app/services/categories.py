"""Category configuration loader (Bible 23.4)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from app.config import ROOT

DEFAULT_CATEGORIES_PATH = ROOT / "config" / "categories.yaml"

# Fields the agent may be asked to collect. Anything else is rejected at the API.
ALLOWED_REQUIRED_FIELDS = frozenset(
    {"availability", "availability_today", "price", "quantity", "wait_time", "open_status"}
)


class CategoryConfig(BaseModel):
    display_name: str
    essential_attributes: list[str] = Field(default_factory=list)
    blocked_terms_file: str | None = None
    required_fields_default: list[str]
    price_max_plausible_inr: int = 100000
    blocked_terms: list[str] = Field(default_factory=list)
    osm_tags: list[str] = Field(default_factory=list)  # OpenStreetMap discovery (D-059)
    business_noun: str = "business"  # how the general agent refers to the shop (D-062)


class CategoryError(ValueError):
    pass


def load_blocked_terms(path: Path) -> list[str]:
    terms: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip().lower()
        if line and not line.startswith("#"):
            terms.append(line)
    return terms


def load_categories(path: Path = DEFAULT_CATEGORIES_PATH) -> dict[str, CategoryConfig]:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise CategoryError(f"invalid categories YAML: {exc}") from exc
    if not isinstance(data, dict) or not isinstance(data.get("categories"), dict):
        raise CategoryError("categories file must contain a 'categories' mapping")

    result: dict[str, CategoryConfig] = {}
    for name, raw in data["categories"].items():
        cfg = CategoryConfig.model_validate(raw)
        unknown = set(cfg.required_fields_default) - ALLOWED_REQUIRED_FIELDS
        if unknown:
            raise CategoryError(f"{name}: unknown required fields {sorted(unknown)}")
        if cfg.blocked_terms_file:
            terms_path = ROOT / cfg.blocked_terms_file
            if not terms_path.is_file():
                raise CategoryError(f"{name}: blocked terms file not found: {terms_path}")
            cfg.blocked_terms = load_blocked_terms(terms_path)
        result[name] = cfg
    return result


@lru_cache
def get_categories() -> dict[str, CategoryConfig]:
    return load_categories()
