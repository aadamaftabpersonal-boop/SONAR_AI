"""Metrics, review, ground truth, retention, deletion and the digest, against real Postgres."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from app.db.models import (
    AuditEvent,
    Business,
    BusinessResponse,
    BusinessStats,
    CallAttempt,
    GroundTruthCheck,
    ProviderEvent,
    SearchJob,
)
from app.db.repositories import EventRepo, StatsRepo
from app.domain.enums import GroundTruthOutcome as G
from app.services import digest as digest_mod
from app.services import metrics as metrics_mod
from app.services import retention, review
from app.services.stats import StatsData
from tests.factories import make_attempt, make_business, make_job

pytestmark = pytest.mark.integration

NOW = datetime.now(UTC)


def answered(
    session,
    *,
    origin="LIVE_CALL",
    availability="REPORTED_AVAILABLE",
    biz=None,
    job=None,
    cost="0.40",
    **over,
):
    biz = biz or make_business(session)
    job = job or make_job(
        session,
        started_at=NOW - timedelta(seconds=40),
        completed_at=NOW,
        deadline_at=NOW + timedelta(minutes=5),
    )
    provider = "bolna" if origin == "LIVE_CALL" else "simulated"
    att = session.execute(
        select(CallAttempt).where(
            CallAttempt.search_job_id == job.id, CallAttempt.business_id == biz.id
        )
    ).scalar_one_or_none()
    if att is None:
        att = make_attempt(session, job, biz, provider=provider)
    att.status, att.provider_call_id, att.cost_amount = (
        "COMPLETED",
        f"c-{uuid.uuid4()}",
        Decimal(cost),
    )
    session.commit()
    fields = {
        "call_attempt_id": att.id,
        "search_job_id": job.id,
        "business_id": biz.id,
        "data_origin": origin,
        "availability": availability,
        "exact_match": "CONFIRMED",
        "answer_summary": "x",
        "evidence_validated": True,
        "extraction_status": "VALID",
        "answer_timestamp": NOW - timedelta(seconds=5),
        "evidence_excerpt": "yes we have it",
        "provider_extracted": {"availability": "available"},
    }
    fields.update(over)
    r = BusinessResponse(**fields)
    session.add(r)
    session.commit()
    return r


# --- metrics ---------------------------------------------------------------------------------


def test_with_no_data_every_metric_is_not_available_rather_than_zero(session):
    m = metrics_mod.compute(session)
    for key in ("call_connection_rate", "exact_match_rate", "ground_truth_agreement"):
        assert m[key].denominator == 0 and m[key].value is None and "n/a" in m[key].text
    assert "n/a" in m["cost_per_useful_result"].text
    assert "n/a" in metrics_mod.render(m)


def test_metrics_report_live_numbers_with_their_denominators(session):
    answered(session, availability="REPORTED_AVAILABLE", cost="0.40")
    answered(session, availability="REPORTED_UNAVAILABLE", cost="0.20")
    answered(session, availability="UNCERTAIN", cost="0.30")
    m = metrics_mod.compute(session)
    assert m["call_connection_rate"].text == "3 of 3"
    assert m["exact_match_rate"].text == "3 of 3"
    assert m["uncertain_rate"].text == "1 of 3"
    # (0.40 + 0.20 + 0.30) over the 2 useful results
    assert (
        m["cost_per_useful_result"].value == Decimal("0.45") and m["cost_per_useful_result"].n == 2
    )
    assert "n=2" in m["cost_per_useful_result"].text
    assert m["useful_search_rate"].text == "2 of 3"


def test_simulated_runs_never_count_unless_asked(session):
    answered(session, origin="SIMULATED")
    assert metrics_mod.compute(session)["exact_match_rate"].denominator == 0
    assert metrics_mod.compute(session, include_simulated=True)["exact_match_rate"].denominator == 1


def test_time_to_first_useful_result_is_a_median_with_its_sample_size(session):
    for seconds in (10, 20, 60):
        job = make_job(
            session,
            started_at=NOW - timedelta(seconds=seconds + 5),
            completed_at=NOW,
            deadline_at=NOW + timedelta(minutes=5),
        )
        answered(session, job=job, answer_timestamp=NOW - timedelta(seconds=5))
    m = metrics_mod.compute(session)["median_seconds_to_first_useful_result"]
    assert m.n == 3 and m.value == 20


def test_a_late_answer_does_not_count_as_a_useful_search(session):
    job = make_job(
        session, started_at=NOW - timedelta(minutes=10), deadline_at=NOW - timedelta(minutes=5)
    )
    answered(session, job=job, answer_timestamp=NOW)
    assert metrics_mod.compute(session)["useful_search_rate"].text == "0 of 1"


def test_stop_rule_saving_counts_only_searches_that_used_it(session):
    answered(
        session,
        job=make_job(
            session, started_at=NOW, stop_rule={"k": 2}, calls_avoided=3, planned_targets=5
        ),
    )
    answered(session, job=make_job(session, started_at=NOW, planned_targets=5))  # rule off
    assert metrics_mod.compute(session)["stop_rule_saving"].text == "3 of 5"


# --- human review and ground truth -----------------------------------------------------------


def test_only_live_answers_can_be_reviewed(session):
    sim = answered(session, origin="SIMULATED")
    with pytest.raises(review.ReviewError, match="simulated"):
        review.mark_review(session, sim.id, agrees=True, reviewer="a")
    with pytest.raises(review.ReviewError, match="simulated"):
        review.record_ground_truth(
            session, sim.id, checker="a", method="IN_PERSON", outcome=G.AGREE
        )


def test_a_reviewer_marks_agreement_or_contradiction_and_it_feeds_the_metric(session):
    good, bad = answered(session), answered(session)
    review.mark_review(session, good.id, agrees=True, reviewer="asha")
    review.mark_review(session, bad.id, agrees=False, reviewer="asha")
    session.commit()
    session.refresh(good), session.refresh(bad)
    assert (
        good.verification_status == "HUMAN_REVIEWED" and bad.verification_status == "CONTRADICTED"
    )
    assert metrics_mod.compute(session)["human_verified_accuracy"].text == "1 of 2"
    assert (
        session.execute(
            select(func.count())
            .select_from(AuditEvent)
            .where(AuditEvent.action == "response_reviewed")
        ).scalar_one()
        == 2
    )


def test_ground_truth_is_reported_as_agreement_out_of_checked_excluding_inconclusive(session):
    rs = [answered(session) for _ in range(4)]
    for r, outcome in zip(rs, (G.AGREE, G.AGREE, G.DISAGREE, G.INCONCLUSIVE), strict=True):
        review.record_ground_truth(
            session, r.id, checker="ravi", method="IN_PERSON", outcome=outcome
        )
    session.commit()
    m = metrics_mod.compute(session)
    assert m["ground_truth_agreement"].text == "2 of 3"
    assert m["ground_truth_inconclusive"] == 1


def test_a_checker_cannot_check_the_same_answer_twice_and_must_be_named(session):
    r = answered(session)
    review.record_ground_truth(session, r.id, checker="ravi", method="SECOND_CALL", outcome=G.AGREE)
    with pytest.raises(review.ReviewError, match="already"):
        review.record_ground_truth(
            session, r.id, checker="ravi", method="SECOND_CALL", outcome=G.AGREE
        )
    with pytest.raises(review.ReviewError, match="who"):
        review.record_ground_truth(session, r.id, checker=" ", method="OTHER", outcome=G.AGREE)
    with pytest.raises(review.ReviewError, match="method"):
        review.record_ground_truth(session, r.id, checker="x", method="GUESS", outcome=G.AGREE)


def test_unchecked_list_excludes_checked_and_simulated_answers(session):
    a, b = answered(session), answered(session)
    answered(session, origin="SIMULATED")
    review.record_ground_truth(session, a.id, checker="c", method="OTHER", outcome=G.AGREE)
    session.commit()
    assert [r.id for r in review.list_unchecked(session)] == [b.id]


# --- retention and deletion ------------------------------------------------------------------


def test_old_events_are_deleted_and_old_excerpts_are_cleared_but_counts_survive(session):
    repo = EventRepo(session)
    repo.insert_or_ignore(
        provider="bolna", provider_call_id="old", provider_status="x", payload={"a": 1}
    )
    repo.insert_or_ignore(
        provider="bolna", provider_call_id="new", provider_status="x", payload={"b": 2}
    )
    old_event = session.execute(
        select(ProviderEvent).where(ProviderEvent.provider_call_id == "old")
    ).scalar_one()
    old_event.received_at = NOW - timedelta(days=40)
    old_resp = answered(session)
    old_resp.created_at = NOW - timedelta(days=100)
    fresh_resp = answered(session)
    session.commit()

    counts = retention.purge_old(session, NOW, event_days=30, response_days=90)
    session.commit()
    assert counts == {"events_deleted": 1, "responses_cleared": 1}
    session.refresh(old_resp), session.refresh(fresh_resp)
    assert old_resp.evidence_excerpt is None and old_resp.provider_extracted is None
    assert "RETENTION_PURGED" in old_resp.validation_flags
    assert old_resp.availability == "REPORTED_AVAILABLE"  # the outcome itself is kept
    assert fresh_resp.evidence_excerpt == "yes we have it"
    assert session.execute(select(func.count()).select_from(ProviderEvent)).scalar_one() == 1


def test_purging_twice_changes_nothing_more(session):
    r = answered(session)
    r.created_at = NOW - timedelta(days=200)
    session.commit()
    retention.purge_old(session, NOW, event_days=30, response_days=90)
    again = retention.purge_old(session, NOW, event_days=30, response_days=90)
    assert again == {"events_deleted": 0, "responses_cleared": 0}
    session.refresh(r)
    assert r.validation_flags.count("RETENTION_PURGED") == 1


def test_deleting_a_shops_data_keeps_the_shop_and_its_opt_out(session):
    biz = make_business(session)
    r = answered(session, biz=biz)
    review.record_ground_truth(session, r.id, checker="c", method="OTHER", outcome=G.AGREE)
    StatsRepo(session).update(biz.id, lambda _: StatsData(attempts=3, connected=2))
    EventRepo(session).insert_or_ignore(
        provider="bolna",
        provider_call_id="orphan-1",
        provider_status="completed",
        payload={"t": "secret words"},
    )
    att = session.execute(select(BusinessResponse.call_attempt_id)).scalar_one()
    from app.db.models import CallAttempt

    session.get(CallAttempt, att).provider_call_id = "orphan-1"
    session.commit()
    other = answered(session)  # a different shop's answer must survive

    counts = retention.delete_business_data(session, biz.id)
    session.commit()
    assert counts["responses"] == 1 and counts["events"] == 1 and counts["stats"] == 1
    assert session.execute(select(func.count()).select_from(GroundTruthCheck)).scalar_one() == 0
    assert session.get(BusinessStats, biz.id) is None
    assert session.get(Business, biz.id) is not None
    assert session.get(BusinessResponse, other.id) is not None
    audit = session.execute(
        select(AuditEvent).where(AuditEvent.action == "business_data_deleted")
    ).scalar_one()
    assert audit.business_id == biz.id and "secret words" not in str(audit.detail)


# --- the digest ------------------------------------------------------------------------------


def search_for(
    session, biz, item="Paracetamol", demo=False, provider="bolna", created=None, kind_ok=True
):
    job = make_job(
        session, demo_mode=demo, parsed_query={"item_name": item, "category": "pharmacy"}
    )
    if created:
        job.created_at = created
    make_attempt(session, job, biz, provider=provider)
    session.commit()
    return job


def real_shop(session, **over):
    return make_business(session, kind="REAL_BUSINESS", participation_status="CONSENTED", **over)


def test_a_line_appears_only_when_enough_searches_contribute(session):
    shop = real_shop(session)
    for _ in range(3):
        search_for(session, shop, "Paracetamol")
    for _ in range(2):
        search_for(session, shop, "Cetirizine")
    d = digest_mod.generate(session, shop, NOW, min_k=3)
    assert [(line.item, line.searches) for line in d.lines] == [("paracetamol", 3)]
    assert d.suppressed_lines == 1
    assert "cetirizine" not in str(d).lower()  # a hidden item is never named


def test_demo_simulated_and_old_traffic_is_excluded(session):
    shop = real_shop(session)
    for _ in range(3):
        search_for(session, shop, "Demo item", demo=True)
        search_for(session, shop, "Sim item", provider="simulated")
        search_for(session, shop, "Old item", created=NOW - timedelta(days=30))
    d = digest_mod.generate(session, shop, NOW, min_k=3)
    assert d.lines == [] and d.suppressed_lines == 0


def test_traffic_that_only_ever_targeted_team_test_lines_is_not_demand(session):
    test_line = make_business(session)  # TEAM_TEST_LINE
    for _ in range(4):
        search_for(session, test_line, "Rehearsal item")
    assert digest_mod.generate(session, test_line, NOW, min_k=3).lines == []


def test_the_digest_says_how_often_this_shop_reported_having_it(session):
    shop = real_shop(session)
    jobs = [search_for(session, shop) for _ in range(3)]
    answered(session, biz=shop, job=jobs[0], availability="REPORTED_AVAILABLE")
    answered(session, biz=shop, job=jobs[1], availability="REPORTED_UNAVAILABLE")
    line = digest_mod.generate(session, shop, NOW, min_k=3).lines[0]
    assert line.searches == 3 and line.you_reported_available == 1


def test_one_shops_digest_never_contains_another_shops_data(session):
    mine, theirs = real_shop(session, name="Mine"), real_shop(session, name="Theirs")
    for _ in range(3):
        search_for(session, theirs, "Secret item")
    d = digest_mod.generate(session, mine, NOW, min_k=3)
    assert d.lines == [] and "Theirs" not in str(d)


def test_the_digest_carries_no_identifiers_and_admits_what_it_counts(session):
    shop = real_shop(session)
    for _ in range(3):
        search_for(session, shop)
    d = digest_mod.generate(session, shop, NOW, min_k=3)
    text = str(d)
    assert shop.phone_e164 not in text and "ip" not in {f for f in vars(d)}
    assert "searches, not people" in d.note and "at least 3 times" in d.note


def test_enabling_the_digest_makes_a_long_private_token_and_keeps_it(session):
    shop = real_shop(session)
    t1 = digest_mod.enable_digest(session, shop.id)
    t2 = digest_mod.enable_digest(session, shop.id)
    assert t1 == t2 and len(t1) >= 40 and shop.digest_opt_in
    assert digest_mod.business_for_token(session, t1).id == shop.id


def test_unknown_blank_opted_in_false_and_opted_out_tokens_find_nothing(session):
    shop = real_shop(session)
    token = digest_mod.enable_digest(session, shop.id)
    assert digest_mod.business_for_token(session, "nope") is None
    assert digest_mod.business_for_token(session, "") is None
    shop.digest_opt_in = False
    assert digest_mod.business_for_token(session, token) is None
    shop.digest_opt_in = True
    from app.db.repositories import BusinessRepo

    BusinessRepo(session).mark_opt_out(shop.id)
    session.commit()
    session.refresh(shop)
    assert digest_mod.business_for_token(session, token) is None
    with pytest.raises(ValueError, match="opted out"):
        digest_mod.enable_digest(session, shop.id)


def test_a_search_is_a_search_search_models_exist():
    assert SearchJob.__tablename__ == "search_jobs"
