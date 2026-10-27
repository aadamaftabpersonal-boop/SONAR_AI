"""D-059: OpenStreetMap discovery parsing, phone normalisation and de-duplication."""

import json
from pathlib import Path

import pytest

from app.services.osm import FoundShop, build_query, dedupe, normalize_in_phone, parse

FIXTURE = Path(__file__).parents[1] / "fixtures" / "osm" / "overpass_pharmacies.json"


def test_query_covers_nodes_and_ways_for_every_tag():
    q = build_query(["amenity=pharmacy", "healthcare=pharmacy"], 12.97, 77.59, 3)
    assert q.count("around:3000,12.970000,77.590000") == 4
    assert 'node["amenity"="pharmacy"]' in q and 'way["healthcare"="pharmacy"]' in q
    assert q.startswith("[out:json]") and "out center tags;" in q


@pytest.mark.parametrize("bad", [[], ["amenity"], ['amenity="x"];out;'], ["a=b c"]])
def test_query_rejects_missing_or_unsafe_tags(bad):
    with pytest.raises(ValueError):
        build_query(bad, 12.97, 77.59, 3)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("+91 98765 43210", "+919876543210"),
        ("098765 43210", "+919876543210"),
        ("9876543210", "+919876543210"),
        ("91 9876543210", "+919876543210"),
        ("0091-98765-43210", "+919876543210"),
        ("011 2345 6789", "+911123456789"),  # STD landline
        ("2345 6789", None),  # landline without STD code
        ("+91 12345", None),
        ("", None),
        (None, None),
        ("2345 6789; +91 98765 43210", "+919876543210"),
        ("98765 43210 / 98765 01234", "+919876543210"),
        ("+44 20 7946 0958", "+442079460958"),
    ],
)
def test_phone_normalisation(raw, expected):
    assert normalize_in_phone(raw) == expected


def test_parse_keeps_named_positioned_shops_and_dedupes():
    shops = parse(json.loads(FIXTURE.read_text(encoding="utf-8")))
    names = [s.name for s in shops]
    assert names == ["Fixture Pharmacy One", "Fixture Medicals", "No Phone Chemist"]
    one, way, nophone = shops
    assert one.osm_id == "node/1001" and one.address == "12 Example Road, Bengaluru"
    assert one.opening_hours == "Mo-Sa 09:00-21:00"
    assert way.osm_id == "way/2002" and (way.lat, way.lng) == (12.9750, 77.5990)
    assert nophone.phone_e164 is None


def test_dedupe_by_phone_and_by_name_nearby():
    a = FoundShop("node/1", "A", 12.97, 77.59, "+919876543210")
    same_phone = FoundShop("node/2", "Other name", 12.98, 77.60, "+919876543210")
    same_name_near = FoundShop("node/3", "a", 12.97001, 77.59001, None)
    same_name_far = FoundShop("node/4", "A", 12.99, 77.62, None)
    assert dedupe([a, same_phone, same_name_near, same_name_far]) == [a, same_name_far]


def test_parse_tolerates_junk():
    assert parse({}) == []
    assert parse({"elements": [None, 3, {"type": "node", "tags": {"name": "x"}}]}) == []
