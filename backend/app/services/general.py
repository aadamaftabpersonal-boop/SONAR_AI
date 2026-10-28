"""Validator for custom questions (D-062). Pure and deterministic, like validator.py.

The extractor returns, per question, an answer and the shop's exact words. Nothing is accepted
unless those words are in the shop's own lines of the transcript; numbers must have been said;
unclear, hedged or contradictory answers stay unknown. Free model prose never reaches the UI: a
text answer is shown as the shop's own quote.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any

from app.domain.enums import Availability, ExactMatch, ExtractionStatus
from app.domain.schemas import ParsedQuery, Question, QuestionKind
from app.services.validator import (
    IST,
    MAX_EXCERPT,
    _clean_excerpt,
    _has_cue,
    _said_by_shop,
    _to_decimal,
    normalize,
    number_in_transcript,
)

ANSWERS_EXTRACTION = "answers_json"
_NON_HUMAN = {"voicemail", "ivr", "wrong_number"}
_YES = {"yes", "y", "true", "haan", "han", "ha", "ji", "haa"}
_NO = {"no", "n", "false", "nahi", "nahin", "na"}
_HEDGE = (
    "not sure",
    "maybe",
    "don't know",
    "dont know",
    "do not know",
    "let me check",
    "pata nahi",
)
_NEG = ("no", "not", "don't", "dont", "nahi", "closed", "finished", "never")
_POS = ("yes", "haan", "we do", "we have", "open", "available", "sure")
_MAX_TEXT = 200


@dataclass
class QuestionAnswer:
    key: str
    question: str
    kind: str
    value: bool | float | str | None = None
    unit: str | None = None
    quote: str | None = None
    validated: bool = False
    meets: bool | None = None  # yes/no questions with a wanted answer only
    flag: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "question": self.question,
            "kind": self.kind,
            "value": self.value,
            "unit": self.unit,
            "quote": self.quote,
            "validated": self.validated,
            "meets": self.meets,
            "flag": self.flag,
        }


@dataclass
class GeneralAnswer:
    create_response: bool
    failure_reason: str | None = None
    opt_out: bool = False
    availability: Availability = Availability.UNCERTAIN
    exact_match: ExactMatch = ExactMatch.UNKNOWN
    answers: list[QuestionAnswer] = field(default_factory=list)
    rank_value: Decimal | None = None
    answer_summary: str = ""
    evidence_excerpt: str | None = None
    evidence_validated: bool = False
    extraction_status: ExtractionStatus = ExtractionStatus.INVALID
    validation_flags: list[str] = field(default_factory=list)


def parse_answers(raw: Any) -> dict[str, Any] | None:
    """The extractor's answer object. Accepts a dict, or JSON text (also inside ``` fences)."""
    if isinstance(raw, dict):
        return raw
    if not isinstance(raw, str) or not raw.strip():
        return None
    text = raw.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1)
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        data = json.loads(text[start : end + 1])
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


def _entry(answers: dict[str, Any], q: Question, index: int) -> tuple[Any, str | None]:
    raw = answers.get(q.key, answers.get(str(index), answers.get(f"q{index}")))
    if isinstance(raw, dict):
        answer = raw.get("answer", raw.get("value"))
        quote = raw.get("quote")
    else:
        answer, quote = raw, None
    quote = quote.strip() if isinstance(quote, str) and quote.strip() else None
    return answer, quote


def _yes_no(answer: Any) -> bool | None:
    if isinstance(answer, bool):
        return answer
    if isinstance(answer, str):
        word = normalize(answer).split(" ")[0] if normalize(answer) else ""
        if word in _YES:
            return True
        if word in _NO:
            return False
    return None


def check_one(q: Question, index: int, answers: dict[str, Any], transcript: str) -> QuestionAnswer:
    out = QuestionAnswer(key=q.key, question=q.text, kind=q.kind.value, unit=q.unit)
    answer, quote = _entry(answers, q, index)
    if answer is None or (isinstance(answer, str) and not answer.strip()):
        out.flag = "NOT_ANSWERED"
        return out
    if not quote or not _said_by_shop(quote, transcript):
        out.flag = "EVIDENCE_NOT_FOUND"
        return out
    out.quote = _clean_excerpt(quote)[:_MAX_TEXT]
    if _has_cue(quote, _HEDGE):
        out.flag = "BUSINESS_UNSURE"
        return out

    if q.kind == QuestionKind.YES_NO:
        value = _yes_no(answer)
        if value is None:
            out.flag = "NOT_A_YES_OR_NO"
            return out
        # the shop's own words must not say the opposite
        said = normalize(quote)
        negative = any(re.search(rf"(?<!\w){re.escape(c)}(?!\w)", said) for c in _NEG)
        positive = any(normalize(c) in said for c in _POS)
        if (value and negative and not positive) or (not value and positive and not negative):
            out.flag = "CONTRADICTORY"
            return out
        out.value, out.validated = value, True
        if q.want is not None:
            out.meets = value == (q.want == "yes")
        return out

    if q.kind == QuestionKind.NUMBER:
        number = _to_decimal(re.sub(r"[^\d.,-]", "", str(answer)) or None)
        if number is None or number < 0:
            out.flag = "NOT_A_NUMBER"
            return out
        if not number_in_transcript(number, transcript):
            out.flag = "NUMBER_NOT_HEARD"
            return out
        out.value, out.validated = float(number), True
        return out

    # text: show the shop's own words, never the model's paraphrase (V12)
    out.value, out.validated = out.quote, True
    return out


def validate_general(
    *,
    provider_status: str,
    transcript: str | None,
    extracted: dict[str, Any] | None,
    query: ParsedQuery,
    answer_time: datetime,
) -> GeneralAnswer:
    if provider_status != "completed" or not (transcript or "").strip():
        return GeneralAnswer(create_response=False, failure_reason="NOT_COMPLETED")
    ex = extracted or {}
    transcript = transcript or ""
    if str(ex.get("call_outcome") or "human").lower() in _NON_HUMAN:
        return GeneralAnswer(create_response=False, failure_reason="NO_HUMAN")
    if str(ex.get("opt_out_requested") or "").lower() == "yes":
        return GeneralAnswer(
            create_response=True,
            opt_out=True,
            availability=Availability.DECLINED,
            answer_summary=_summary(answer_time, "the business asked not to be called again"),
            extraction_status=ExtractionStatus.VALID,
            validation_flags=["OPT_OUT_REQUESTED"],
        )

    answers = parse_answers(ex.get(ANSWERS_EXTRACTION))
    flags: list[str] = []
    if answers is None:
        flags.append("ANSWERS_UNREADABLE")
        answers = {}
    checked = [check_one(q, i, answers, transcript) for i, q in enumerate(query.questions, 1)]
    for a in checked:
        if a.flag and a.flag not in flags:
            flags.append(a.flag)

    criteria = [a for a in checked if a.meets is not None or _wanted(query, a.key)]
    answered = [a for a in checked if a.validated]
    if any(a.meets is False for a in criteria):
        availability, exact = Availability.REPORTED_UNAVAILABLE, ExactMatch.NOT_CONFIRMED
    elif criteria and all(a.meets is True for a in criteria):
        availability, exact = Availability.REPORTED_AVAILABLE, ExactMatch.CONFIRMED
    elif not criteria and answered:
        availability, exact = Availability.REPORTED_AVAILABLE, ExactMatch.CONFIRMED
    else:
        availability, exact = Availability.UNCERTAIN, ExactMatch.UNKNOWN

    ranked = next((q for q in query.questions if q.rank), None)
    rank_value = None
    if ranked:
        hit = next((a for a in checked if a.key == ranked.key and a.validated), None)
        if hit is not None and isinstance(hit.value, float):
            rank_value = Decimal(str(hit.value))

    first_quote = next((a.quote for a in checked if a.validated and a.quote), None)
    total = len(checked)
    if criteria:
        met = sum(a.meets is True for a in criteria)
        detail = (
            f"meets {met} of {len(criteria)} of what you asked; answered {len(answered)} of {total}"
        )
    else:
        detail = f"answered {len(answered)} of {total} questions"
    if len(answered) == total:
        status = ExtractionStatus.VALID
    elif answered:
        status = ExtractionStatus.PARTIAL
    else:
        status = (
            ExtractionStatus.INVALID if "ANSWERS_UNREADABLE" in flags else ExtractionStatus.PARTIAL
        )
    return GeneralAnswer(
        create_response=True,
        availability=availability,
        exact_match=exact,
        answers=checked,
        rank_value=rank_value,
        answer_summary=_summary(answer_time, detail),
        evidence_excerpt=(first_quote or None) and _clean_excerpt(first_quote)[:MAX_EXCERPT],
        evidence_validated=first_quote is not None,
        extraction_status=status,
        validation_flags=flags,
    )


def _wanted(query: ParsedQuery, key: str) -> bool:
    return any(q.key == key and q.want is not None for q in query.questions)


def _summary(at: datetime, detail: str) -> str:
    """Templated from validated fields only (V12)."""
    return f"Reported by phone at {at.astimezone(IST).strftime('%H:%M')} IST: {detail}."
