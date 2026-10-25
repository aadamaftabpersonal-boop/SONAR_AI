"""Stop rule (Bible 48.2, D-032): stop calling once enough shops have *confirmed*.

Only positives count. A "no", an "unsure", silence or a failure never stops a search, because
stopping on those would hide shops that might say yes.
"""

from __future__ import annotations

from dataclasses import dataclass

# failure_reason stamped on attempts that were never dialed because enough shops had confirmed
STOP_REASON = "STOP_RULE_SATISFIED"


@dataclass(frozen=True)
class Confirmation:
    business_id: str
    data_origin: str
    availability: str
    exact_match: str
    evidence_validated: bool
    price_present: bool


def counts_as_confirmation(c: Confirmation, *, require_price: bool, allow_simulated: bool) -> bool:
    if c.data_origin == "SIMULATED" and not allow_simulated:
        return False  # simulated answers never satisfy a live job (D-022)
    if c.data_origin not in {"LIVE_CALL", "SIMULATED"}:
        return False
    return (
        c.availability == "REPORTED_AVAILABLE"
        and c.exact_match == "CONFIRMED"
        and c.evidence_validated
        and (c.price_present or not require_price)
    )


def satisfied(
    items: list[Confirmation], *, k: int, require_price: bool, allow_simulated: bool
) -> bool:
    """True when at least `k` *distinct* businesses gave a validated, exact, positive answer."""
    shops = {
        c.business_id
        for c in items
        if counts_as_confirmation(c, require_price=require_price, allow_simulated=allow_simulated)
    }
    return len(shops) >= k
