import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.domain.enums import BusinessKind, ParticipationStatus
from app.services.selector import Candidate, in_window, parse_window, select

# 11:00 IST on a Monday (05:30 UTC), inside the default 09:00-20:00 window
NOW = datetime(2026, 11, 2, 5, 30, tzinfo=UTC)
CENTER = (12.9716, 77.5946)


def cand(name="Shop", dlat=0.0, **over) -> Candidate:
    fields = {
        "business_id": uuid.uuid4(),
        "name": name,
        "kind": BusinessKind.TEAM_TEST_LINE,
        "participation_status": ParticipationStatus.TEST_LINE,
        "lat": CENTER[0] + dlat,
        "lng": CENTER[1],
    }
    fields.update(over)
    return Candidate(**fields)


def run(candidates, **over):
    args = {
        "lat": CENTER[0],
        "lng": CENTER[1],
        "radius_km": 5,
        "now": NOW,
        "max_targets": 5,
        "daily_cap": 4,
        "cooldown_minutes": 15,
    }
    args.update(over)
    return select(candidates, **args)


def test_nearest_first_and_distance_reported():
    far, near = cand("far", dlat=0.03), cand("near", dlat=0.005)
    result = run([far, near])
    assert [t.name for t in result.targets] == ["near", "far"]
    assert result.targets[0].distance_km < result.targets[1].distance_km


def test_target_cap_is_honoured_and_counted():
    cands = [cand(f"s{i}", dlat=0.001 * (i + 1)) for i in range(8)]
    result = run(cands, max_targets=5)
    assert len(result.targets) == 5
    assert result.excluded["over_target_cap"] == 3
    assert [t.name for t in result.targets] == ["s0", "s1", "s2", "s3", "s4"]


def test_outside_radius_excluded():
    result = run([cand(dlat=0.5)], radius_km=3)
    assert result.targets == []
    assert result.excluded == {"outside_radius": 1}


@pytest.mark.parametrize(
    "status",
    [
        ParticipationStatus.INVITED,
        ParticipationStatus.DECLINED,
        ParticipationStatus.OPTED_OUT,
    ],
)
def test_non_consented_never_selected_even_if_passed_in(status):
    result = run([cand(participation_status=status)])
    assert result.targets == []
    assert result.excluded == {"not_consented": 1}


def test_opted_out_flag_wins_even_with_consented_status():
    result = run([cand(participation_status=ParticipationStatus.CONSENTED, opted_out=True)])
    assert result.targets == []


def test_daily_cap_boundary():
    assert run([cand(calls_today=3)]).targets
    assert run([cand(calls_today=4)]).excluded == {"daily_cap": 1}


def test_cooldown_boundary():
    inside = cand(last_call_at=NOW - timedelta(minutes=14, seconds=59))
    outside = cand(last_call_at=NOW - timedelta(minutes=15))
    assert run([inside]).excluded == {"cooldown": 1}
    assert len(run([outside]).targets) == 1


def test_missing_coordinates_excluded():
    assert run([cand(lat=None, lng=None)]).excluded == {"no_location": 1}


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("10:00-13:00 IST", ("10:00", "13:00")),
        ("9:30 - 18:15", ("09:30", "18:15")),
        (None, ("09:00", "20:00")),
        ("whenever", ("09:00", "20:00")),
        ("25:00-26:00", ("09:00", "20:00")),
    ],
)
def test_window_parsing(text, expected):
    start, end = parse_window(text)
    assert (start.strftime("%H:%M"), end.strftime("%H:%M")) == expected


def test_call_window_boundaries_in_ist():
    window = "10:00-13:00 IST"
    # 10:00 IST == 04:30 UTC (inclusive), 13:00 IST == 07:30 UTC (exclusive)
    assert in_window(datetime(2026, 11, 2, 4, 30, tzinfo=UTC), window)
    assert not in_window(datetime(2026, 11, 2, 4, 29, tzinfo=UTC), window)
    assert in_window(datetime(2026, 11, 2, 7, 29, tzinfo=UTC), window)
    assert not in_window(datetime(2026, 11, 2, 7, 30, tzinfo=UTC), window)


def test_outside_window_is_excluded_with_reason():
    night = datetime(2026, 11, 2, 18, 0, tzinfo=UTC)  # 23:30 IST
    result = run([cand()], now=night)
    assert result.excluded == {"outside_call_window": 1}


def test_no_candidates_reports_nothing_considered():
    result = run([])
    assert result.targets == [] and result.considered == 0


def test_ties_are_stable_by_business_id():
    a = cand("a", dlat=0.01, business_id=uuid.UUID(int=1))
    b = cand("b", dlat=0.01, business_id=uuid.UUID(int=2))
    assert [t.name for t in run([b, a]).targets] == ["a", "b"]
