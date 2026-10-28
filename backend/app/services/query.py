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
    Question,
    QuestionKind,
    QuestionSpec,
    Refusal,
    SearchRequest,
    is_safe_question,
    is_safe_text,
)
from app.services.categories import ALLOWED_REQUIRED_FIELDS, CategoryConfig, get_categories
from app.services.plans import radius_error

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


_MAX_QUESTION_WORDS = 25


def _checked_questions(specs: list[QuestionSpec]) -> list[Question]:
    """Validate custom questions (D-062) and give them server-side keys q1..qN.

    A question is spoken to a shopkeeper by the agent, so it gets the same treatment as any user
    text that reaches the agent: a character whitelist, a length limit and the instruction-like
    check. Options that do not fit the question's kind are rejected, not ignored."""
    out: list[Question] = []
    ranked = 0
    for i, spec in enumerate(specs, start=1):
        field = f"questions.{i - 1}"
        text = " ".join(spec.text.split())
        if (
            not is_safe_question(text)
            or len(text.split()) > _MAX_QUESTION_WORDS
            or _INSTRUCTION_LIKE.search(text)
        ):
            raise QueryValidationError(field, f"question {i} is not an acceptable question")
        if spec.kind != QuestionKind.YES_NO and spec.want is not None:
            raise QueryValidationError(
                field, f"question {i}: only yes/no questions take a wanted answer"
            )
        if spec.kind != QuestionKind.NUMBER and (spec.unit or spec.rank):
            raise QueryValidationError(
                field, f"question {i}: only number questions take a unit or ranking"
            )
        unit = " ".join(spec.unit.split()) if spec.unit else None
        if unit and (not is_safe_text(unit) or _unsafe_free_text(unit)):
            raise QueryValidationError(field, f"question {i}: the unit is not acceptable")
        if spec.rank:
            ranked += 1
        out.append(
            Question(
                key=f"q{i}", text=text, kind=spec.kind, want=spec.want, unit=unit, rank=spec.rank
            )
        )
    if ranked > 1:
        raise QueryValidationError("questions", "only one question can be used to rank shops")
    return out


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

    questions = _checked_questions(request.questions or [])

    # 2. Category
    cfg = categories.get(request.category)
    if cfg is None:
        supported = ", ".join(sorted(categories))
        return Refusal(message=f"Unsupported category. Supported categories: {supported}.")

    # 3. High-risk content (applies to everything the user typed, including free text)
    texts = [request.item.name, request.query_text, *attributes.values()]
    texts += [q.text for q in questions] + [q.unit or "" for q in questions]
    if cfg.blocked_terms and _blocked_term(texts, cfg.blocked_terms):
        return Refusal(message=REFUSAL_MESSAGE)

    # 4. Radius
    if not MIN_RADIUS_KM <= request.radius_km <= MAX_RADIUS_KM:
        raise QueryValidationError(
            "radius_km", f"radius_km must be between {MIN_RADIUS_KM:g} and {MAX_RADIUS_KM:g}"
        )

    plan_problem = radius_error(request.plan, request.radius_km)
    if plan_problem:
        raise QueryValidationError("radius_km", plan_problem)

    # 5. Required fields
    required = request.required_fields or list(cfg.required_fields_default)
    unknown = set(required) - ALLOWED_REQUIRED_FIELDS
    if unknown:
        raise QueryValidationError(
            "required_fields", f"unknown required fields: {', '.join(sorted(unknown))}"
        )

    # 6. Anything essential that is missing or conflicting becomes a question, never a guess.
    # With custom questions the user has said exactly what to ask, so the category's essential
    # attributes (e.g. a medicine's strength) are not required.
    clarify: list[ClarificationQuestion] = []
    if request.location is None:
        clarify.append(ClarificationQuestion(field="location", question="Where should we search?"))
    for attr in [] if questions else cfg.essential_attributes:
        if not attributes.get(attr):
            label = attr.replace("_", " ")
            clarify.append(
                ClarificationQuestion(
                    field=f"item.attributes.{attr}", question=f"What {label} should we ask about?"
                )
            )
    hint = _WITHIN_KM.search(request.query_text)
    if hint and abs(float(hint.group(1)) - request.radius_km) > 1e-9:
        clarify.append(
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
        clarify.append(
            ClarificationQuestion(
                field="query_text", question="Do you need it open now, or tomorrow?"
            )
        )
    if clarify:
        return Clarification(questions=clarify)

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
        plan=request.plan,
        questions=questions,
    )


_SPOKEN_UNITS = {
    "mg": "milligrams",
    "mcg": "micrograms",
    "ml": "millilitres",
    "kg": "kilograms",
    "g": "grams",
}
_UNIT = re.compile(r"(?<=\d)\s*(mcg|mg|ml|kg|g)\b", re.IGNORECASE)


def spoken(text: str) -> str:
    """Units written out in full: the voice says them and the shop answers in the same words.
    A live call heard '500 mg' and the shopkeeper's 'milligrams' was transcribed 'millie gills',
    which read as a different product (2026-10-25)."""
    return _UNIT.sub(lambda m: f" {_SPOKEN_UNITS[m.group(1).lower()]}", text)


def build_user_data(parsed: ParsedQuery, business_kind: str = "business") -> dict[str, str]:
    """The only data that flows to the voice agent (Bible 30). Whitelisted keys, safe values."""
    attributes_text = spoken(
        ", ".join(f"{k.replace('_', ' ')} {v}" for k, v in parsed.attributes.items())
    )
    data = {
        "category": parsed.category,
        "item": parsed.item_name,
        "attributes_text": attributes_text,
        "required_fields_text": ", ".join(f.replace("_", " ") for f in parsed.required_fields),
    }
    if parsed.questions:
        data.update(question_user_data(parsed, business_kind))
    return data


_HINT = {
    QuestionKind.YES_NO: "answer yes or no",
    QuestionKind.NUMBER: "a number",
    QuestionKind.TEXT: "a short answer",
}


def question_user_data(parsed: ParsedQuery, business_kind: str = "business") -> dict[str, str]:
    """The general agent's call data (D-062): numbered questions with an answer hint each."""
    lines = []
    for n, q in enumerate(parsed.questions, start=1):
        hint = _HINT[q.kind]
        if q.kind == QuestionKind.NUMBER and q.unit:
            hint = f"a number, in {q.unit}"
        lines.append(f"{n}. {spoken(q.text)} ({hint})")
    return {
        "business_kind": business_kind,
        "topic": spoken(" ".join([parsed.item_name, *parsed.attributes.values()]).strip()),
        "questions_text": "\n".join(lines),
        "questions_kinds": ",".join(q.kind.value for q in parsed.questions),
    }


GENERAL_AGENT = "general"


def agent_key_for(parsed: ParsedQuery) -> str:
    """Searches with custom questions use the general agent; the rest the category's agent."""
    return GENERAL_AGENT if parsed.questions else parsed.category


def business_noun(category: str) -> str:
    cfg = get_categories().get(category)
    return cfg.business_noun if cfg else "business"
