"""Guards drift between code enums and the Bible's 19.3 table (T2.1)."""

import re
from pathlib import Path

import pytest

from app.domain import enums

BIBLE = Path(__file__).resolve().parents[3] / "SONAR_BIBLE_v2.md"

# Wave 2 values are added to some enums in Bible 19.4 prose, not the 19.3 table.
WAVE2_EXTRA = {
    "ResultState": {"NOT_CALLED_STOP_RULE"},
    "DataOrigin": {"SHOP_SELF_REPORT"},
}
# 19.3 lists ErrorClass without the API-only codes added in Bible 20.1.
API_ONLY_ERRORS = {"RATE_LIMITED", "UNAUTHORIZED", "NOT_FOUND"}


def bible_enum_table() -> dict[str, set[str]]:
    rows: dict[str, set[str]] = {}
    in_table = False
    for line in BIBLE.read_text(encoding="utf-8").splitlines():
        if line.startswith("| Enum | Values |"):
            in_table = True
            continue
        if in_table:
            if not line.startswith("|"):
                break
            m = re.match(r"\|\s*`(\w+)`(?:\s*\(UI-derived\))?\s*\|\s*(.+?)\s*\|\s*$", line)
            if m:
                rows[m.group(1)] = set(re.findall(r"`([A-Z_]+)`", m.group(2)))
    return rows


def test_bible_table_was_found():
    assert "CallStatus" in bible_enum_table()


@pytest.mark.parametrize("name", sorted(bible_enum_table()))
def test_enum_values_match_bible(name):
    expected = bible_enum_table()[name]
    actual = {m.value for m in getattr(enums, name)}
    actual -= WAVE2_EXTRA.get(name, set())
    if name == "ErrorClass":
        actual -= API_ONLY_ERRORS
    assert actual == expected


def test_member_name_equals_value():
    for cls in (
        enums.SearchStatus,
        enums.CallStatus,
        enums.ParticipationStatus,
        enums.Availability,
        enums.ResultState,
        enums.ErrorClass,
    ):
        assert all(m.name == m.value for m in cls)
