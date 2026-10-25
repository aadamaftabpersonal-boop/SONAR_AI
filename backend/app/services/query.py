"""Query validation and parsing (Bible 23.1-23.2): StructuredFormParser, no LLM (D-013).

Treat everything as untrusted data. Only the whitelisted fields built by `build_user_data` can
ever reach the voice agent.
"""

from __future__ import annotations

import re

from app.domain.schemas import (
    MAX_RADIUS_KM,
    MIN_RADIUS_KM,
    Clarification,
    ClarificationQuestion,
    ParsedQuery,
    QueryValidationError,
    Refusal,
    SearchRequest,
    is_safe_text,
)
from app.services.categories import ALLOWED_REQUIRED_FIELDS, CategoryConfig

_ATTR_KEY = re.compile(r"^[a-z][a-z0-9_]{0,29}$")
_WITHIN_KM = re.compile(
    r"within\s+(\d+(?:\.\d+)?)\s*(?:km|kms|kilomet(?:re|er)s?)\b", re.IGNORECASE
)

# Second layer after the charset whitelist: a plain-English sentence passes the whitelist, so
# item text that reads like an instruction to the agent is rejected, and names stay short.
_MAX_WORDS = 8
_INSTRUCTION_LIKE = re.compile(
    r"\b(ignore|disregard|forget|override)\b.{0,40}\b(instructions?|prompts?|rules?)\b"
    r"|\bsystem\s*(prompt|message)\b|\byou\s+(are|must|should)\b|\bact\s+as\b|\bsay\s+yes\b",
    re.IGNORECASE,
)


def _unsafe_free_text(value: str) -> bool:
    return len(value.split()) > _MAX_WORDS or bool(_INSTRUCTION_LIKE.search(value))


REFUSAL_MESSAGE = (
    "Sonar can't help with that kind of question. It only checks whether a shop reports having "
    "a specific non-prescription item or service. It does not give medical advice."
)


def _blocked_term(texts: list[str], terms: list[str]) -> str | None:
    haystack = " ".join(texts).lower()
    for term in terms:
        if re.search(rf"(?<!\w){re.escape(term)}(?!\w)", haystack):
            return term
    return None


def parse(
    request: SearchRequest, categories: dict[str, CategoryConfig]
) -> ParsedQuery | Clarification | Refusal:
    """Return a ParsedQuery, a Clarification (ask the user) or a Refusal. Raises
    QueryValidationError for malformed input."""
    # 1. Charset whitelist first: hostile strings are rejected, never escaped.
    if not is_safe_text(request.item.name) or _unsafe_free_text(request.item.name):
        raise QueryValidationError("item.name", "item name is not an acceptable product name")
    attributes: dict[str, str] = {}
    for key, value in request.item.attributes.items():
        if not _ATTR_KEY.match(key):
            raise QueryValidationError(f"item.attributes.{key}", "invalid attribute name")
        if not is_safe_text(value) or _unsafe_free_text(value):
            raise QueryValidationError(
                f"item.attributes.{key}", "attribute value is not acceptable"
            )
        attributes[key] = value.strip()

    # 2. Category
    cfg = categories.get(request.category)
    if cfg is None:
        supported = ", ".join(sorted(categories))
        return Refusal(message=f"Unsupported category. Supported categories: {supported}.")

    # 3. High-risk content (applies to everything the user typed, including free text)
    texts = [request.item.name, request.query_text, *attributes.values()]
    if cfg.blocked_terms and _blocked_term(texts, cfg.blocked_terms):
        return Refusal(message=REFUSAL_MESSAGE)

    # 4. Radius
    if not MIN_RADIUS_KM <= request.radius_km <= MAX_RADIUS_KM:
        raise QueryValidationError(
            "radius_km", f"radius_km must be between {MIN_RADIUS_KM:g} and {MAX_RADIUS_KM:g}"
        )

    # 5. Required fields
    required = request.required_fields or list(cfg.required_fields_default)
    unknown = set(required) - ALLOWED_REQUIRED_FIELDS
    if unknown:
        raise QueryValidationError(
            "required_fields", f"unknown required fields: {', '.join(sorted(unknown))}"
        )

    # 6. Anything essential that is missing or conflicting becomes a question, never a guess
    questions: list[ClarificationQuestion] = []
    if request.location is None:
        questions.append(
            ClarificationQuestion(field="location", question="Where should we search?")
        )
    for attr in cfg.essential_attributes:
        if not attributes.get(attr):
            label = attr.replace("_", " ")
            questions.append(
                ClarificationQuestion(
                    field=f"item.attributes.{attr}", question=f"What {label} should we ask about?"
                )
            )
    hint = _WITHIN_KM.search(request.query_text)
    if hint and abs(float(hint.group(1)) - request.radius_km) > 1e-9:
        questions.append(
            ClarificationQuestion(
                field="radius_km",
                question=(
                    f"Your text says within {hint.group(1)} km but the search radius is "
                    f"{request.radius_km:g} km. Which should we use?"
                ),
            )
        )
    lowered = request.query_text.lower()
    if "open now" in lowered and "tomorrow" in lowered:
        questions.append(
            ClarificationQuestion(
                field="query_text", question="Do you need it open now, or tomorrow?"
            )
        )
    if questions:
        return Clarification(questions=questions)

    assert request.location is not None
    return ParsedQuery(
        query_text=request.query_text,
        category=request.category,
        item_name=request.item.name.strip(),
        attributes=attributes,
        lat=request.location.lat,
        lng=request.location.lng,
        location_label=request.location.label,
        radius_km=request.radius_km,
        required_fields=required,
        force_fresh=request.force_fresh,
        demo_mode=request.demo_mode,
        mode=request.mode,
    )


def build_user_data(parsed: ParsedQuery) -> dict[str, str]:
    """The only data that flows to the voice agent (Bible 30). Whitelisted keys, safe values."""
    attributes_text = ", ".join(f"{k.replace('_', ' ')} {v}" for k, v in parsed.attributes.items())
    return {
        "category": parsed.category,
        "item": parsed.item_name,
        "attributes_text": attributes_text,
        "required_fields_text": ", ".join(f.replace("_", " ") for f in parsed.required_fields),
    }
