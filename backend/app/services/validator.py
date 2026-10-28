"""AnswerValidator (Bible 23.3, rules V1-V14). Pure and deterministic.

This is the heart of trust: a model's extraction is only a *candidate*. Nothing is stored or shown
as a claim unless it passes these rules. Unknown stays unknown; silence is never "unavailable".
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any
from zoneinfo import ZoneInfo

from app.domain.enums import Availability, ExactMatch, ExtractionStatus
from app.domain.schemas import ParsedQuery

IST = ZoneInfo("Asia/Kolkata")
MAX_EXCERPT = 600

_AVAILABILITY_VALUES = {"available", "not_available", "unsure", "declined"}
_NON_HUMAN = {"voicemail", "ivr", "wrong_number"}
_RUPEE_TOKENS = ("rupee", "rupees", "rs", "inr", "₹")
_NEGATIVE_CUES = (
    "finished",
    "out of stock",
    "not available",
    "not in stock",
    "don't have",
    "do not have",
    "dont have",
    "no stock",
    "sold out",
    "not have",
)
_POSITIVE_CUES = ("we have it", "in stock", "have it", "available")


@dataclass
class ValidatedAnswer:
    create_response: bool
    failure_reason: str | None = None
    opt_out: bool = False
    availability: Availability = Availability.UNCERTAIN
    exact_match: ExactMatch = ExactMatch.UNKNOWN
    matched_attributes: dict[str, str] = field(default_factory=dict)
    alternative_note: str | None = None
    price_amount: Decimal | None = None
    price_currency: str | None = None
    price_note: str | None = None
    quantity_reported: int | None = None
    wait_time_minutes: int | None = None
    open_status: str | None = None
    answer_summary: str = ""
    evidence_excerpt: str | None = None
    evidence_validated: bool = False
    extraction_status: ExtractionStatus = ExtractionStatus.INVALID
    validation_flags: list[str] = field(default_factory=list)
    provider_confidence: Decimal | None = None


# --- text helpers ---------------------------------------------------------------------------


def normalize(text: str) -> str:
    """Case, whitespace and punctuation insensitive form used for substring evidence checks."""
    return " ".join(re.sub(r"[^\w\s]", " ", text.lower()).split())


def _clean_excerpt(text: str) -> str:
    text = "".join(ch for ch in text if ch == "\n" or ch >= " ")  # strip control characters
    return text.strip()[:MAX_EXCERPT]


_ONES = (
    "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen "
    "fifteen sixteen seventeen eighteen nineteen"
).split()
_TENS = "_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()


def number_words(n: int) -> set[str]:
    """Spoken English forms of a whole number up to 99,999 (normalised: no hyphens)."""
    if n < 0 or n > 99999:
        return set()
    if n < 20:
        return {_ONES[n]}
    if n < 100:
        tens, ones = divmod(n, 10)
        return {_TENS[tens]} if ones == 0 else {f"{_TENS[tens]} {_ONES[ones]}"}
    if n < 1000:
        hundreds, rest = divmod(n, 100)
        head = f"{_ONES[hundreds]} hundred"
        if rest == 0:
            return {head}
        return {f"{head} {w}" for w in number_words(rest)} | {
            f"{head} and {w}" for w in number_words(rest)
        }
    thousands, rest = divmod(n, 1000)
    head = f"{' '.join(sorted(number_words(thousands)))} thousand"
    if rest == 0:
        forms = {head}
    else:
        forms = {f"{head} {w}" for w in number_words(rest)} | {
            f"{head} and {w}" for w in number_words(rest)
        }
    # "twelve hundred (and fifty)": how 1,250 is often said, in India too
    hundreds, tail = divmod(n, 100)
    if n < 10000 and hundreds % 10 != 0:
        for h in number_words(hundreds):
            base = f"{h} hundred"
            forms |= (
                {base}
                if tail == 0
                else {f"{base} {w}" for w in number_words(tail)}
                | {f"{base} and {w}" for w in number_words(tail)}
            )
    return forms


def number_in_transcript(value: Decimal, transcript: str) -> bool:
    """True if the number appears as digits or as spoken words."""
    flat = re.sub(r"(?<=\d),(?=\d)", "", transcript.lower())
    candidates = {format(value.normalize(), "f")}
    if value == value.to_integral_value():
        candidates.add(str(int(value)))
    for c in candidates:
        if re.search(rf"(?<![\d.]){re.escape(c)}(?![\d])", flat):
            return True
    if value == value.to_integral_value():
        spoken = normalize(transcript)
        return any(
            re.search(rf"(?<!\w){re.escape(w)}(?!\w)", spoken) for w in number_words(int(value))
        )
    return False


def _to_decimal(value: Any) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        d = Decimal(str(value).strip().replace(",", ""))
    except (InvalidOperation, ValueError):
        return None
    return d if d.is_finite() else None


def _has_cue(text: str, cues: tuple[str, ...]) -> bool:
    n = normalize(text)
    return any(normalize(c) in n for c in cues)


_SHOP_SPEAKERS = ("user:", "shop:")


def _shop_turns(transcript: str) -> list[str]:
    """The business's own lines. Bolna labels them `user:`, the simulator `shop:`."""
    turns = []
    for line in transcript.splitlines():
        stripped = line.strip()
        low = stripped.lower()
        for label in _SHOP_SPEAKERS:
            if low.startswith(label):
                text = stripped[len(label) :].strip()
                if text:
                    turns.append(text)
                break
    return turns


def _reaffirmed_at_the_end(transcript: str) -> bool:
    """True if the shop's last line is a plain "we have it" with no negative words.

    Catches a call where speech-to-text mangled a word, the agent noted "a different one", and
    the shop then corrected it ("yes we have it"). An exact-match "no" is then not trustworthy.
    """
    turns = _shop_turns(transcript)
    if not turns:
        return False
    last = turns[-1]
    return _has_cue(last, _POSITIVE_CUES) and not _has_cue(last, _NEGATIVE_CUES)


def _said_by_shop(text: str, transcript: str) -> bool:
    turns = _shop_turns(transcript)
    haystack = normalize(" ".join(turns)) if turns else normalize(transcript)
    return bool(normalize(text)) and normalize(text) in haystack


def _stated_rupees(stated: Any) -> bool:
    if not isinstance(stated, str):
        return False
    low = stated.lower()
    return "₹" in low or any(
        re.search(rf"(?<!\w){re.escape(t)}(?!\w)", low) for t in _RUPEE_TOKENS if t != "₹"
    )


# --- the validator --------------------------------------------------------------------------


def validate(
    *,
    provider_status: str,
    transcript: str | None,
    extracted: dict[str, Any] | None,
    query: ParsedQuery,
    answer_time: datetime,
    price_max: int = 100000,
) -> ValidatedAnswer:
    # V1: only completed calls with a transcript can yield a response row
    if provider_status != "completed" or not (transcript or "").strip():
        return ValidatedAnswer(create_response=False, failure_reason="NOT_COMPLETED")

    ex = extracted or {}
    transcript = transcript or ""
    flags: list[str] = []

    # V14: voicemail / IVR / wrong number is not an answer
    if str(ex.get("call_outcome") or "human").lower() in _NON_HUMAN:
        return ValidatedAnswer(create_response=False, failure_reason="NO_HUMAN")

    quote_raw = ex.get("supporting_quote")
    quote = quote_raw.strip() if isinstance(quote_raw, str) and quote_raw.strip() else None
    quote_found = bool(quote) and normalize(quote) in normalize(transcript)
    excerpt = _clean_excerpt(quote) if quote_found else None

    # V10: an explicit "stop calling me" has the highest precedence
    if str(ex.get("opt_out_requested") or "").lower() == "yes":
        return ValidatedAnswer(
            create_response=True,
            opt_out=True,
            availability=Availability.DECLINED,
            answer_summary=_summary(Availability.DECLINED, answer_time, None, query),
            evidence_excerpt=excerpt,
            evidence_validated=quote_found,
            extraction_status=ExtractionStatus.VALID,
            validation_flags=["OPT_OUT_REQUESTED"],
        )

    if extracted is None:
        return ValidatedAnswer(
            create_response=True,
            availability=Availability.UNCERTAIN,
            answer_summary=_summary(Availability.UNCERTAIN, answer_time, None, query),
            extraction_status=ExtractionStatus.MISSING,
            validation_flags=["NO_EXTRACTION"],
        )

    # V2: availability must come from the allowed set
    raw_avail = str(ex.get("availability") or "").lower()
    if raw_avail not in _AVAILABILITY_VALUES:
        return ValidatedAnswer(
            create_response=True,
            availability=Availability.UNCERTAIN,
            answer_summary=_summary(Availability.UNCERTAIN, answer_time, None, query),
            evidence_excerpt=excerpt,
            evidence_validated=quote_found,
            extraction_status=ExtractionStatus.INVALID,
            validation_flags=["INVALID_AVAILABILITY"],
        )

    exact_raw = str(ex.get("exact_match_confirmed") or "").lower()
    alternative = ex.get("alternative_offered")
    alternative = (
        alternative.strip() if isinstance(alternative, str) and alternative.strip() else None
    )

    availability = Availability.UNCERTAIN
    exact = ExactMatch.UNKNOWN

    if raw_avail == "declined":
        availability = Availability.DECLINED
    elif raw_avail == "unsure":
        availability = Availability.UNCERTAIN
        flags.append("BUSINESS_UNSURE")
    else:
        # a positive or negative claim needs evidence found in the transcript (V3)
        if not quote_found:
            flags.append("EVIDENCE_NOT_FOUND")
        elif raw_avail == "available":
            # V9: contradiction between the extraction and the words the shop actually said
            if _has_cue(quote or "", _NEGATIVE_CUES):
                flags.append("CONTRADICTORY")
            elif exact_raw == "yes":  # V4: exact match must be confirmed by the business
                availability, exact = Availability.REPORTED_AVAILABLE, ExactMatch.CONFIRMED
            elif exact_raw == "no" and _reaffirmed_at_the_end(transcript):
                # V9: "not exact" but the shop's last word was "yes, we have it" (first live
                # call, 2026-10-25: "milligrams" heard as "millie gills"). Show neither claim.
                flags += ["CONTRADICTORY", "SHOP_REAFFIRMED_AT_END"]
            elif exact_raw == "no" and alternative and not _said_by_shop(alternative, transcript):
                # V3 for alternatives: an alternative is shown only in the shop's own words
                flags += ["ALTERNATIVE_NOT_IN_TRANSCRIPT", "EXACT_MATCH_NOT_CONFIRMED"]
                exact = ExactMatch.NOT_CONFIRMED
            elif exact_raw == "no" and alternative:
                availability, exact = Availability.ALTERNATIVE_ONLY, ExactMatch.NOT_CONFIRMED
            elif exact_raw == "no":
                flags.append("EXACT_MATCH_NOT_CONFIRMED")
                exact = ExactMatch.NOT_CONFIRMED
            else:
                flags.append("EXACT_MATCH_UNKNOWN")
        else:  # not_available
            if _has_cue(quote or "", _POSITIVE_CUES) and not _has_cue(quote or "", _NEGATIVE_CUES):
                flags.append("CONTRADICTORY")
            else:
                availability, exact = Availability.REPORTED_UNAVAILABLE, ExactMatch.UNKNOWN

    # V5: never mutate a requested attribute; CONFIRMED only if the business confirmed the item
    matched = {
        attr: "CONFIRMED" if exact is ExactMatch.CONFIRMED else "UNKNOWN"
        for attr in query.attributes
    }

    # V6 / V7: price
    price_amount: Decimal | None = None
    price_currency: str | None = None
    price_note: str | None = None
    raw_price = _to_decimal(ex.get("price_amount"))
    if ex.get("price_amount") is not None and raw_price is None:
        flags.append("PRICE_NOT_NUMERIC")
    elif raw_price is not None:
        if raw_price <= 0 or raw_price > Decimal(price_max):
            flags.append("PRICE_IMPLAUSIBLE")
        elif not number_in_transcript(raw_price, transcript):
            flags.append("PRICE_NOT_IN_TRANSCRIPT")
        elif availability is Availability.REPORTED_AVAILABLE:
            price_amount = raw_price
            if _stated_rupees(ex.get("price_currency_stated")):
                price_currency = "INR"
            else:
                flags.append("PRICE_CURRENCY_UNSTATED")
        elif availability is Availability.ALTERNATIVE_ONLY:
            price_note = f"Price {raw_price.normalize():f} was quoted for a different item"
            flags.append("PRICE_NOT_EXACT_ITEM")
        # prices are ignored for every other state: nothing exact was confirmed

    # V8: quantity, wait time, open status only if explicit and valid
    quantity = _int_in_transcript(ex.get("quantity_available"), transcript, 100000)
    wait = _int_in_transcript(ex.get("wait_time_minutes"), transcript, 10080)
    open_status = _open_status(ex.get("open_now"))
    if availability is not Availability.REPORTED_AVAILABLE:
        quantity = None

    # required-field completeness decides VALID vs PARTIAL
    needed = set(query.required_fields)
    missing = []
    if "price" in needed and price_amount is None:
        missing.append("price")
    if "quantity" in needed and quantity is None:
        missing.append("quantity")
    if "wait_time" in needed and wait is None:
        missing.append("wait_time")
    if "open_status" in needed and open_status is None:
        missing.append("open_status")
    if availability is Availability.REPORTED_AVAILABLE and missing:
        flags += [f"MISSING_{m.upper()}" for m in missing]
    if availability in {Availability.REPORTED_AVAILABLE, Availability.REPORTED_UNAVAILABLE}:
        status = ExtractionStatus.PARTIAL if missing else ExtractionStatus.VALID
    else:
        status = ExtractionStatus.PARTIAL if flags else ExtractionStatus.VALID

    return ValidatedAnswer(
        create_response=True,
        availability=availability,
        exact_match=exact,
        matched_attributes=matched,
        alternative_note=alternative if availability is Availability.ALTERNATIVE_ONLY else None,
        price_amount=price_amount,
        price_currency=price_currency,
        price_note=price_note,
        quantity_reported=quantity,
        wait_time_minutes=wait,
        open_status=open_status,
        answer_summary=_summary(availability, answer_time, price_amount, query, price_currency),
        evidence_excerpt=excerpt,
        evidence_validated=quote_found,
        extraction_status=status,
        validation_flags=flags,
        provider_confidence=_to_decimal(ex.get("confidence")),
    )


def _int_in_transcript(value: Any, transcript: str, upper: int) -> int | None:
    d = _to_decimal(value)
    if d is None or d != d.to_integral_value() or d < 0 or d > upper:
        return None
    return int(d) if number_in_transcript(d, transcript) else None


def _open_status(value: Any) -> str | None:
    if isinstance(value, bool):
        return "OPEN" if value else "CLOSED"
    if isinstance(value, str):
        low = value.strip().lower()
        if low in {"yes", "true", "open"}:
            return "OPEN"
        if low in {"no", "false", "closed"}:
            return "CLOSED"
    return None


def _summary(
    availability: Availability,
    at: datetime,
    price: Decimal | None,
    query: ParsedQuery,
    currency: str | None = None,
) -> str:
    """Templated from validated fields only (V12). Free model prose never reaches the UI."""
    when = at.astimezone(IST).strftime("%H:%M")
    head = f"Reported by phone at {when} IST:"
    if availability is Availability.REPORTED_AVAILABLE:
        if price is not None:
            amount = f"{price.normalize():f}"
            tail = (
                f"price ₹{amount}" if currency == "INR" else f"price {amount} (currency not stated)"
            )
        elif "price" in query.required_fields:
            tail = "price not quoted"
        else:
            tail = None
        return f"{head} exact item available" + (f"; {tail}." if tail else ".")
    return {
        Availability.REPORTED_UNAVAILABLE: f"{head} said the item is not available.",
        Availability.ALTERNATIVE_ONLY: f"{head} offered something other than the exact item.",
        Availability.DECLINED: f"{head} declined to answer.",
        Availability.UNCERTAIN: f"{head} unsure or could not be confirmed.",
    }[availability]
