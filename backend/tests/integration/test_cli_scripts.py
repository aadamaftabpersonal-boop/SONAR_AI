"""The command-line tools, driven against the test database."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
from sqlalchemy import func, select

from app.db.models import Business, BusinessResponse
from tests.integration.test_measurement import answered

pytestmark = pytest.mark.integration

ROOT = Path(__file__).resolve().parents[3]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


ground_truth = load("ground_truth")
delete_cli = load("delete_business_data")
digest_cli = load("enable_digest")


def count(session, model):
    return session.execute(select(func.count()).select_from(model)).scalar_one()


def test_list_shows_unchecked_live_answers_and_never_simulated_ones(
    session, session_factory, capsys
):
    live = answered(session)
    answered(session, origin="SIMULATED")
    assert ground_truth.run(["list"], session_factory) == 0
    out = capsys.readouterr().out
    assert str(live.id) in out and out.count("quote:") == 1


def test_an_empty_list_says_so(session, session_factory, capsys):
    ground_truth.run(["list"], session_factory)
    assert "nothing to check" in capsys.readouterr().out


def test_recording_a_check_and_a_review(session, session_factory, capsys):
    r = answered(session)
    assert (
        ground_truth.run(
            [
                "check",
                str(r.id),
                "--checker",
                "Asha",
                "--method",
                "IN_PERSON",
                "--outcome",
                "AGREE",
                "--note",
                "saw it on the shelf",
            ],
            session_factory,
        )
        == 0
    )
    assert (
        ground_truth.run(["review", str(r.id), "--reviewer", "Asha", "--agrees"], session_factory)
        == 0
    )
    session.expire_all()
    assert session.get(BusinessResponse, r.id).verification_status == "HUMAN_REVIEWED"
    assert "recorded" in capsys.readouterr().out


def test_a_simulated_answer_and_a_repeat_check_are_refused_with_a_message(
    session, session_factory, capsys
):
    sim = answered(session, origin="SIMULATED")
    code = ground_truth.run(
        ["check", str(sim.id), "--checker", "A", "--method", "OTHER", "--outcome", "AGREE"],
        session_factory,
    )
    assert code == 1 and "simulated" in capsys.readouterr().err
    live = answered(session)
    args = ["check", str(live.id), "--checker", "A", "--method", "OTHER", "--outcome", "AGREE"]
    assert ground_truth.run(args, session_factory) == 0
    assert ground_truth.run(args, session_factory) == 1


def test_delete_is_a_dry_run_unless_confirmed(session, session_factory, capsys):
    biz = real_shop_with_answer(session)
    assert delete_cli.run([str(biz.id)], session_factory) == 0
    assert "dry run" in capsys.readouterr().out
    assert count(session, BusinessResponse) == 1  # nothing was deleted

    assert delete_cli.run([str(biz.id), "--yes"], session_factory) == 0
    session.expire_all()
    assert count(session, BusinessResponse) == 0
    assert session.get(Business, biz.id) is not None  # the shop (and any opt-out) is kept


def real_shop_with_answer(session):
    biz = real_shop_row(session)
    answered(session, biz=biz)
    return biz


def real_shop_row(session):
    from tests.factories import make_business

    return make_business(session, kind="REAL_BUSINESS", participation_status="CONSENTED")


def test_delete_for_an_unknown_business_is_an_error(session, session_factory, capsys):
    assert delete_cli.run(["00000000-0000-0000-0000-000000000000"], session_factory) == 1
    assert "no such business" in capsys.readouterr().err


def test_enable_digest_prints_a_private_link_and_refuses_an_opted_out_shop(
    session, session_factory, capsys
):
    biz = real_shop_row(session)
    assert (
        digest_cli.run([str(biz.id), "--base-url", "https://sonar.example.org/"], session_factory)
        == 0
    )
    out = capsys.readouterr().out
    assert "https://sonar.example.org/shop/" in out and "like a password" in out

    from app.db.repositories import BusinessRepo

    BusinessRepo(session).mark_opt_out(biz.id)
    session.commit()
    assert digest_cli.run([str(biz.id)], session_factory) == 1
    assert "opted out" in capsys.readouterr().err
