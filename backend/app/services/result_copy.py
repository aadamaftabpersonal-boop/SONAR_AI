"""All user-facing wording for result states lives here so it can be reviewed in one place.

Rule (NFR-09): only an explicit, validated "not available" answer may ever read as unavailable.
Silence, failure, refusal, uncertainty and skipped calls must never be worded as unavailability.
"""

from __future__ import annotations

from app.domain.enums import ResultState

LABELS: dict[ResultState, str] = {
    ResultState.REPORTED_AVAILABLE: "Reported available by phone",
    ResultState.REPORTED_UNAVAILABLE: "Reported unavailable by phone",
    ResultState.ALTERNATIVE_ONLY: "Alternative only",
    ResultState.UNCERTAIN: "Uncertain",
    ResultState.DECLINED: "Declined to answer",
    ResultState.NO_ANSWER: "No answer",
    ResultState.CALL_FAILED: "Call failed",
    ResultState.PENDING: "Pending",
    ResultState.CANCELLED: "Cancelled",
    ResultState.NOT_CALLED_STOP_RULE: "Not called (enough answers)",
}

NOT_UNAVAILABLE = "This does not mean the item is unavailable."

NOTES: dict[ResultState, str] = {
    ResultState.NO_ANSWER: f"Call was not answered. {NOT_UNAVAILABLE}",
    ResultState.CALL_FAILED: f"The call could not be completed. {NOT_UNAVAILABLE}",
    ResultState.DECLINED: f"The business declined to answer. {NOT_UNAVAILABLE}",
    ResultState.PENDING: "Waiting for this call to finish.",
    ResultState.CANCELLED: f"Cancelled before an answer was recorded. {NOT_UNAVAILABLE}",
    ResultState.UNCERTAIN: (
        f"The business was unsure, or the answer could not be validated. {NOT_UNAVAILABLE}"
    ),
    ResultState.ALTERNATIVE_ONLY: "The business offered something other than the exact item.",
    ResultState.NOT_CALLED_STOP_RULE: (
        f"Not called: enough shops had already confirmed. {NOT_UNAVAILABLE}"
    ),
}

RETRYING_NOTE = f"Not answered on the first try; calling again. {NOT_UNAVAILABLE}"

RANKING_EXPLANATION = (
    "Ordered by: exact reported matches first, then by freshness, distance, and price. "
    "Order does not mean one answer is more true than another."
)

SIMULATED_BANNER = "SIMULATED: not real calls"
