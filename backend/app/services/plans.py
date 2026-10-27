"""Plan tiers (D-060): how far a search may reach and how many shops it may ask.

A demo setting chosen in the search form. There is no payment and no account behind it, so it is
never presented as billing or access control.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.enums import PlanTier


@dataclass(frozen=True)
class PlanLimits:
    display_name: str
    max_radius_km: float
    max_targets: int


PLANS: dict[PlanTier, PlanLimits] = {
    PlanTier.FREE: PlanLimits("Free", 3.0, 5),
    PlanTier.PLUS: PlanLimits("Plus", 6.0, 8),
    PlanTier.PRO: PlanLimits("Pro", 10.0, 10),
}


def radius_error(plan: PlanTier | None, radius_km: float) -> str | None:
    """A user-facing message if the radius is beyond the plan, else None (no plan: no limit)."""
    if plan is None:
        return None
    limits = PLANS[plan]
    if radius_km > limits.max_radius_km:
        return (
            f"The {limits.display_name} plan searches up to {limits.max_radius_km:g} km. "
            "Choose a smaller radius or another plan."
        )
    return None


def max_targets(plan: PlanTier | None, configured: int) -> int:
    """Shops per search: the plan's number, never more than the server's own cap."""
    return configured if plan is None else min(configured, PLANS[plan].max_targets)
