"""Request and response models for the Sonar API (Bible 20)."""

from __future__ import annotations

import unicodedata
from datetime import datetime
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.domain.enums import (
    BusinessKind,
    CallStatus,
    DataOrigin,
    ErrorClass,
    ExactMatch,
    Freshness,
    PlanTier,
    ResultState,
    SearchMode,
    SearchStatus,
    VerificationStatus,
)

MIN_RADIUS_KM = 0.5
MAX_RADIUS_KM = 25.0

# Letters, combining marks and digits in any script (so Hindi/Kannada product names survive; `\w`
# would reject vowel signs), plus space and a few punctuation marks used in product names.
# Anything else is rejected, never escaped (Bible 23.2).
_SAFE_PUNCTUATION = frozenset(" .,/%+-")


_QUESTION_PUNCTUATION = frozenset(" .,/%+-?'()&:₹")


def is_safe_question(value: str) -> bool:
    """Like is_safe_text, but a question may also contain ? ' ( ) & : and the rupee sign."""
    if not 3 <= len(value) <= 140:
        return False
    return all(
        ch in _QUESTION_PUNCTUATION or unicodedata.category(ch)[0] in {"L", "M", "N"}
        for ch in value
    )


def is_safe_text(value: str) -> bool:
    if not 1 <= len(value) <= 80:
        return False
    return all(
        ch in _SAFE_PUNCTUATION or unicodedata.category(ch)[0] in {"L", "M", "N"} for ch in value
    )


class Location(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    label: str | None = Field(default=None, max_length=80)


class ItemSpec(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    attributes: dict[str, str] = Field(default_factory=dict)

    @field_validator("attributes")
    @classmethod
    def _limit_attributes(cls, v: dict[str, str]) -> dict[str, str]:
        if len(v) > 8:
            raise ValueError("at most 8 attributes")
        return v


class QuestionKind(StrEnum):
    YES_NO = "yes_no"
    NUMBER = "number"
    TEXT = "text"


class QuestionSpec(BaseModel):
    """One thing the user wants every shop asked (D-062). The text is checked like any other
    user input before it can reach the voice agent (query.parse)."""

    text: str = Field(min_length=3, max_length=140)
    kind: QuestionKind = QuestionKind.YES_NO
    want: Literal["yes", "no"] | None = None  # yes/no only: the answer the user needs
    unit: str | None = Field(default=None, max_length=30)  # number only, e.g. "rupees per hour"
    rank: Literal["lowest", "highest"] | None = None  # number only: order shops by this answer


class Question(QuestionSpec):
    key: str  # q1, q2, ... assigned by the server, never by the client


MAX_QUESTIONS = 5


class SearchRequest(BaseModel):
    query_text: str = Field(min_length=1, max_length=500)
    category: str = Field(min_length=1, max_length=40)
    item: ItemSpec
    location: Location | None = None
    radius_km: float = 3.0
    required_fields: list[str] | None = None
    force_fresh: bool = False
    demo_mode: bool = False
    mode: SearchMode = SearchMode.FAST
    plan: PlanTier | None = None  # demo setting (D-060); None keeps the server-wide limits
    # Custom questions (D-062): when present, the general agent asks exactly these
    questions: list[QuestionSpec] | None = Field(default=None, max_length=MAX_QUESTIONS)


class ParsedQuery(BaseModel):
    """A validated query. Only these fields can ever reach the voice agent (Bible 30)."""

    query_text: str
    category: str
    item_name: str
    attributes: dict[str, str]
    lat: float
    lng: float
    location_label: str | None = None
    radius_km: float
    required_fields: list[str]
    force_fresh: bool = False
    demo_mode: bool = False
    mode: SearchMode = SearchMode.FAST
    plan: PlanTier | None = None
    questions: list[Question] = Field(default_factory=list)


class ClarificationQuestion(BaseModel):
    field: str
    question: str


class Clarification(BaseModel):
    questions: list[ClarificationQuestion]


class Refusal(BaseModel):
    code: ErrorClass = ErrorClass.UNSUPPORTED_QUERY
    message: str


class QueryValidationError(Exception):
    """Invalid input; maps to HTTP 422 VALIDATION with the offending field."""

    def __init__(self, field: str, message: str):
        super().__init__(message)
        self.field = field
        self.message = message


class ErrorBody(BaseModel):
    code: ErrorClass
    message: str
    field: str | None = None
    request_id: str | None = None


class ErrorEnvelope(BaseModel):
    error: ErrorBody


class BusinessRef(BaseModel):
    id: UUID
    name: str
    kind: BusinessKind
    distance_km: float | None = None
    bearing_deg: float | None = None  # compass bearing from the search centre (radar view)
    address: str | None = None


class PlannedTarget(BaseModel):
    business_id: UUID
    name: str
    kind: BusinessKind
    distance_km: float


class SearchCreated(BaseModel):
    search_id: UUID
    status: SearchStatus
    planned_targets: list[PlannedTarget] = Field(default_factory=list)
    clarification: Clarification | None = None
    error_code: ErrorClass | None = None
    message: str | None = None


class AttemptView(BaseModel):
    attempt_id: UUID
    business: BusinessRef
    status: CallStatus
    attempt_number: int
    updated_at: datetime
    result_state: ResultState


class Counts(BaseModel):
    planned: int = 0
    pending: int = 0
    in_call: int = 0
    answered: int = 0
    no_answer: int = 0
    failed: int = 0
    cancelled: int = 0


class SearchView(BaseModel):
    search_id: UUID
    status: SearchStatus
    demo_mode: bool
    category: str | None = None
    custom_questions: bool = False
    mode: SearchMode | None = None
    radius_km: float | None = None
    center_lat: float | None = None  # the search point, so the map can place shops from
    center_lng: float | None = None  # their distance and bearing
    stopped_early: bool = False
    calls_avoided: int = 0
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    deadline_at: datetime | None = None
    counts: Counts
    attempts: list[AttemptView]
    error: dict[str, Any] | None = None


class Evidence(BaseModel):
    excerpt: str | None = None
    validated: bool = False
    question_asked: str | None = None


class ReportedPrice(BaseModel):
    amount: float | None = None
    currency: str | None = None
    note: str | None = None


class Reported(BaseModel):
    exact_match: ExactMatch = ExactMatch.UNKNOWN
    price: ReportedPrice | None = None
    quantity: int | None = None
    wait_time_minutes: int | None = None
    open_status: str | None = None


class HistoryView(BaseModel):
    """Past record, shown beside (never instead of) a live answer, and always labelled."""

    answered: int
    reported_available: int
    label: str = "HISTORY"


class AnswerView(BaseModel):
    """One custom question's validated answer (D-062). `value` is None unless validated."""

    key: str
    question: str
    kind: QuestionKind
    value: bool | float | str | None = None
    unit: str | None = None
    quote: str | None = None
    validated: bool = False
    meets: bool | None = None
    flag: str | None = None


class ResultView(BaseModel):
    history: HistoryView | None = None
    answers: list[AnswerView] | None = None  # custom-question searches only
    rank_value: float | None = None
    business: BusinessRef
    result_state: ResultState
    data_origin: DataOrigin
    answer_timestamp: datetime | None = None
    freshness: dict[str, Freshness] = Field(default_factory=dict)
    reported: Reported | None = None
    answer_summary: str | None = None
    evidence: Evidence | None = None
    verification_status: VerificationStatus | None = None
    flags: list[str] = Field(default_factory=list)
    note: str | None = None


class ResultsView(BaseModel):
    search_id: UUID
    complete: bool
    ranking_explanation: str
    results: list[ResultView]
