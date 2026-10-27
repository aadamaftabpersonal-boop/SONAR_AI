"""OpenStreetMap discovery (D-059): find shops near a point with the Overpass API.

Pure parsing and phone normalisation live here (testable without a network); `fetch` is the only
function that makes a request. Discovered shops are stored as INVITED: they are never called until
the shop opts in itself (D-061). Data is © OpenStreetMap contributors (ODbL); show attribution.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.services.geo import distance_km

USER_AGENT = "Sonar/0.1 (Bolna Buildathon student project; shop discovery, low volume)"
ATTRIBUTION = "© OpenStreetMap contributors"
_TAG = re.compile(r"^([a-z_:]+)=([A-Za-z0-9_;:\-]+)$")
_E164 = re.compile(r"^\+[1-9][0-9]{7,14}$")
_SPLIT = re.compile(r"[;,/]|\bor\b")


@dataclass(frozen=True)
class FoundShop:
    osm_id: str  # "node/123" or "way/456"
    name: str
    lat: float
    lng: float
    phone_e164: str | None
    address: str | None = None
    opening_hours: str | None = None
    tags: dict[str, str] = field(default_factory=dict, compare=False, hash=False)


def build_query(tags: list[str], lat: float, lng: float, radius_km: float) -> str:
    """Overpass QL for nodes and ways with any of `tags` (each `key=value`) within the radius."""
    if not tags:
        raise ValueError("no OpenStreetMap tags configured for this category")
    radius_m = int(round(radius_km * 1000))
    parts = []
    for tag in tags:
        m = _TAG.match(tag.strip())
        if not m:
            raise ValueError(f"invalid OpenStreetMap tag: {tag!r}")
        key, value = m.groups()
        for kind in ("node", "way"):
            parts.append(f'  {kind}["{key}"="{value}"](around:{radius_m},{lat:.6f},{lng:.6f});')
    return "[out:json][timeout:25];\n(\n" + "\n".join(parts) + "\n);\nout center tags;"


def normalize_in_phone(raw: str | None) -> str | None:
    """The first usable Indian (or already international) number in an OSM phone tag, as E.164."""
    if not raw:
        return None
    for chunk in _SPLIT.split(raw):
        chunk = chunk.strip()
        if not chunk:
            continue
        plus = chunk.startswith("+")
        digits = re.sub(r"\D", "", chunk)
        if plus:
            candidate = "+" + digits
        elif digits.startswith("0091"):
            candidate = "+" + digits[2:]
        elif digits.startswith("91") and len(digits) == 12:
            candidate = "+" + digits
        elif digits.startswith("0") and len(digits) == 11:
            candidate = "+91" + digits[1:]  # trunk prefix: mobile or STD landline
        elif len(digits) == 10 and digits[0] in "6789":
            candidate = "+91" + digits
        else:
            continue  # a local landline without its STD code cannot be dialled reliably
        if candidate.startswith("+91") and len(candidate) != 13:
            continue
        if _E164.match(candidate):
            return candidate
    return None


def _address(tags: dict[str, str]) -> str | None:
    if tags.get("addr:full"):
        return tags["addr:full"]
    street = " ".join(p for p in (tags.get("addr:housenumber"), tags.get("addr:street")) if p)
    parts = [
        street,
        tags.get("addr:suburb") or tags.get("addr:neighbourhood"),
        tags.get("addr:city"),
    ]
    text = ", ".join(p for p in parts if p)
    return text or None


def parse(payload: dict) -> list[FoundShop]:
    """Shops with a name and a position. Phone may be None (stored as not contactable)."""
    shops: list[FoundShop] = []
    for el in payload.get("elements") or []:
        if not isinstance(el, dict):
            continue
        tags = el.get("tags") or {}
        name = (tags.get("name") or tags.get("name:en") or "").strip()
        if not name:
            continue  # unnamed shops cannot be shown or invited meaningfully
        if el.get("type") == "node":
            lat, lng = el.get("lat"), el.get("lon")
        else:
            center = el.get("center") or {}
            lat, lng = center.get("lat"), center.get("lon")
        if not isinstance(lat, int | float) or not isinstance(lng, int | float):
            continue
        phone = None
        for key in ("phone", "contact:phone", "contact:mobile", "mobile"):
            phone = normalize_in_phone(tags.get(key))
            if phone:
                break
        shops.append(
            FoundShop(
                osm_id=f"{el.get('type')}/{el.get('id')}",
                name=name[:120],
                lat=float(lat),
                lng=float(lng),
                phone_e164=phone,
                address=_address(tags),
                opening_hours=(tags.get("opening_hours") or None),
                tags={k: v for k, v in tags.items() if isinstance(v, str)},
            )
        )
    return dedupe(shops)


def dedupe(shops: list[FoundShop], same_place_m: float = 50.0) -> list[FoundShop]:
    """One entry per OSM id, per phone number, and per name within `same_place_m` metres."""
    kept: list[FoundShop] = []
    seen_ids: set[str] = set()
    seen_phones: set[str] = set()
    for s in shops:
        if s.osm_id in seen_ids or (s.phone_e164 and s.phone_e164 in seen_phones):
            continue
        if any(
            k.name.casefold() == s.name.casefold()
            and distance_km(k.lat, k.lng, s.lat, s.lng) * 1000 <= same_place_m
            for k in kept
        ):
            continue
        kept.append(s)
        seen_ids.add(s.osm_id)
        if s.phone_e164:
            seen_phones.add(s.phone_e164)
    return kept


def fetch(url: str, query: str, timeout: float) -> dict:
    """One POST to Overpass. No retries: a failure is reported, never hammered (usage policy)."""
    import httpx  # imported here so the pure helpers above load without it

    response = httpx.post(
        url, data={"data": query}, headers={"User-Agent": USER_AGENT}, timeout=timeout
    )
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, dict):
        raise ValueError("Overpass returned something other than a JSON object")
    return data
