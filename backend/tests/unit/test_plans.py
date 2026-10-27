"""D-060: plan tiers bound radius and shops per search; no plan keeps the server limits."""

import pytest

from app.domain.enums import PlanTier
from app.services.plans import PLANS, max_targets, radius_error


@pytest.mark.parametrize(
    ("plan", "ok_km", "too_far_km"),
    [(PlanTier.FREE, 3.0, 3.1), (PlanTier.PLUS, 6.0, 6.5), (PlanTier.PRO, 10.0, 10.5)],
)
def test_radius_is_bounded_by_the_plan(plan, ok_km, too_far_km):
    assert radius_error(plan, ok_km) is None
    message = radius_error(plan, too_far_km)
    assert message and PLANS[plan].display_name in message and f"{ok_km:g} km" in message


def test_no_plan_means_no_extra_limit():
    assert radius_error(None, 25) is None
    assert max_targets(None, 5) == 5


def test_plan_never_raises_the_server_cap():
    assert max_targets(PlanTier.PRO, 5) == 5
    assert max_targets(PlanTier.FREE, 20) == 5
    assert max_targets(PlanTier.PLUS, 20) == 8


def test_plans_grow_with_the_tier():
    free, plus, pro = (PLANS[p] for p in (PlanTier.FREE, PlanTier.PLUS, PlanTier.PRO))
    assert free.max_radius_km < plus.max_radius_km < pro.max_radius_km
    assert free.max_targets <= plus.max_targets <= pro.max_targets
