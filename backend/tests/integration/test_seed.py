from pathlib import Path

import pytest
from sqlalchemy import func, select

from app.config import ROOT
from app.db.models import Business
from app.db.repositories import BusinessRepo
from app.services.seed import SeedError, load_seed, read_seed

pytestmark = pytest.mark.integration

EXAMPLE = ROOT / "data" / "businesses.example.yaml"


def count(session) -> int:
    return session.execute(select(func.count()).select_from(Business)).scalar_one()


def test_example_file_is_valid_and_fictional():
    rows = read_seed(EXAMPLE)
    assert len(rows) >= 6
    assert all(r.phone_e164.startswith("+9100000") for r in rows)


def test_seed_is_idempotent(session):
    first = load_seed(session, EXAMPLE)
    n = count(session)
    second = load_seed(session, EXAMPLE)
    assert count(session) == n
    assert first["created"] == n and second["created"] == 0 and second["updated"] == n


def test_only_callable_businesses_are_eligible(session):
    load_seed(session, EXAMPLE)
    names = {b.name for b in BusinessRepo(session).callable_in_category("pharmacy")}
    assert "Example Pharmacy Invited" not in names
    assert "Example Pharmacy One" in names
    assert "Team Test Line A (role-play)" in names
    assert "Example Repair Shop" not in names  # other category


def test_reseeding_never_revives_an_opt_out(session):
    load_seed(session, EXAMPLE)
    one = session.execute(
        select(Business).where(Business.name == "Example Pharmacy One")
    ).scalar_one()
    BusinessRepo(session).mark_opt_out(one.id)
    session.commit()
    summary = load_seed(session, EXAMPLE)
    assert summary["opt_outs_preserved"] == 1
    session.refresh(one)
    assert one.participation_status == "OPTED_OUT"


def _write(tmp_path: Path, body: str) -> Path:
    p = tmp_path / "seed.yaml"
    p.write_text(body, encoding="utf-8")
    return p


def test_consented_entry_without_consent_record_fails_loudly(tmp_path):
    p = _write(
        tmp_path,
        "businesses:\n  - name: X\n    phone_e164: '+910000000050'\n    category: pharmacy\n"
        "    kind: REAL_BUSINESS\n    participation_status: CONSENTED\n",
    )
    with pytest.raises(SeedError, match="requires consent_recorded_at"):
        read_seed(p)


def test_bad_phone_fails(tmp_path):
    p = _write(
        tmp_path,
        "businesses:\n  - name: X\n    phone_e164: '12345'\n    category: pharmacy\n"
        "    kind: REAL_BUSINESS\n    participation_status: INVITED\n",
    )
    with pytest.raises(SeedError):
        read_seed(p)


def test_duplicate_phone_fails(tmp_path):
    entry = (
        "  - name: {n}\n    phone_e164: '+910000000051'\n    category: pharmacy\n"
        "    kind: REAL_BUSINESS\n    participation_status: INVITED\n"
    )
    p = _write(tmp_path, "businesses:\n" + entry.format(n="A") + entry.format(n="B"))
    with pytest.raises(SeedError, match="duplicate"):
        read_seed(p)


def test_naive_consent_timestamp_fails(tmp_path):
    p = _write(
        tmp_path,
        "businesses:\n  - name: X\n    phone_e164: '+910000000052'\n    category: pharmacy\n"
        "    kind: REAL_BUSINESS\n    participation_status: CONSENTED\n"
        "    consent_recorded_at: '2026-10-26T10:00:00'\n    consent_note: n\n",
    )
    with pytest.raises(SeedError, match="timezone"):
        read_seed(p)


def test_missing_file_fails():
    with pytest.raises(SeedError, match="not found"):
        read_seed(Path("does-not-exist.yaml"))
