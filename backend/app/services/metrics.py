"""Measured numbers for the pitch (Bible 39, 54.2). Every figure carries its denominator.

Rules: live calls only unless asked otherwise (simulated runs prove nothing about reality), a zero
denominator is reported as n/a rather than 0, and nothing here estimates or extrapolates.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import BusinessResponse, CallAttempt, GroundTruthCheck, SearchJob

USEFUL = ("REPORTED_AVAILABLE", "REPORTED_UNAVAILABLE")


@dataclass(frozen=True)
class Ratio:
    numerator: int
    denominator: int

    @property
    def value(self) -> float | None:
        return None if self.denominator == 0 else self.numerator / self.denominator

    @property
    def text(self) -> str:
        if self.denominator == 0:
            return "n/a (no data yet)"
        return f"{self.numerator} of {self.denominator}"


@dataclass(frozen=True)
class Measured:
    value: float | Decimal | None
    n: int
    unit: str = ""

    @property
    def text(self) -> str:
        if self.value is None or self.n == 0:
            return "n/a (no data yet)"
        number = f"{self.value:.2f}" if isinstance(self.value, Decimal) else f"{self.value:.0f}"
        return f"{number}{self.unit} (n={self.n})"


def compute(
    session: Session, *, since: datetime | None = None, include_simulated: bool = False
) -> dict[str, Ratio | Measured | int]:
    origins = ["LIVE_CALL", "SIMULATED"] if include_simulated else ["LIVE_CALL"]
    providers = ["bolna", "simulated"] if include_simulated else ["bolna"]

    attempts = select(CallAttempt).where(CallAttempt.provider.in_(providers))
    responses = select(BusinessResponse).where(BusinessResponse.data_origin.in_(origins))
    jobs = select(SearchJob).where(SearchJob.demo_mode.is_(include_simulated) | include_simulated)
    if since is not None:
        attempts = attempts.where(CallAttempt.created_at >= since)
        responses = responses.where(BusinessResponse.created_at >= since)
        jobs = jobs.where(SearchJob.created_at >= since)

    att = session.execute(attempts).scalars().all()
    resp = session.execute(responses).scalars().all()
    job_rows = session.execute(jobs).scalars().all()

    dispatched = [a for a in att if a.provider_call_id]
    completed = [a for a in dispatched if a.status == "COMPLETED"]
    useful = [r for r in resp if r.availability in USEFUL]

    costed = [a.cost_amount for a in dispatched if a.cost_amount is not None]
    cost_per_useful = (
        Measured(sum(costed, Decimal(0)) / len(useful), len(useful))
        if useful and costed
        else Measured(None, 0)
    )

    # time to first useful answer, and to completion, per search
    first_useful: list[float] = []
    total_time: list[float] = []
    for job in job_rows:
        if job.started_at and job.completed_at:
            total_time.append((job.completed_at - job.started_at).total_seconds())
        mine = [r for r in useful if r.search_job_id == job.id]
        if job.started_at and mine:
            first = min(r.answer_timestamp for r in mine)
            first_useful.append((first - job.started_at).total_seconds())

    started = [j for j in job_rows if j.started_at]
    on_time = {
        j.id
        for j in started
        for r in useful
        if r.search_job_id == j.id
        and r.evidence_validated
        and (j.deadline_at is None or r.answer_timestamp <= j.deadline_at)
    }

    fast = [j for j in job_rows if j.stop_rule is not None]  # searches that ran with the stop rule
    reviewed_ok = sum(r.verification_status == "HUMAN_REVIEWED" for r in resp)
    reviewed_bad = sum(r.verification_status == "CONTRADICTED" for r in resp)

    truth = dict(
        session.execute(
            select(GroundTruthCheck.outcome, func.count())
            .join(BusinessResponse, BusinessResponse.id == GroundTruthCheck.response_id)
            .where(BusinessResponse.data_origin.in_(origins))
            .group_by(GroundTruthCheck.outcome)
        ).all()
    )
    agree, disagree = truth.get("AGREE", 0), truth.get("DISAGREE", 0)

    return {
        "call_connection_rate": Ratio(len(completed), len(dispatched)),
        "structured_answer_completion": Ratio(
            sum(r.extraction_status == "VALID" for r in resp), len(completed)
        ),
        "exact_match_rate": Ratio(sum(r.exact_match == "CONFIRMED" for r in resp), len(resp)),
        "uncertain_rate": Ratio(sum(r.availability == "UNCERTAIN" for r in resp), len(resp)),
        "median_seconds_to_first_useful_result": Measured(
            statistics.median(first_useful) if first_useful else None, len(first_useful), " s"
        ),
        "median_seconds_to_complete": Measured(
            statistics.median(total_time) if total_time else None, len(total_time), " s"
        ),
        "cost_per_useful_result": cost_per_useful,
        "useful_search_rate": Ratio(len(on_time), len(started)),
        "stop_rule_saving": Ratio(
            sum(j.calls_avoided for j in fast), sum(j.planned_targets for j in fast)
        ),
        "human_verified_accuracy": Ratio(reviewed_ok, reviewed_ok + reviewed_bad),
        "ground_truth_agreement": Ratio(agree, agree + disagree),
        "ground_truth_inconclusive": truth.get("INCONCLUSIVE", 0),
    }


LABELS = {
    "call_connection_rate": "Call connection rate (completed / dispatched)",
    "structured_answer_completion": "Structured answers valid / completed calls",
    "exact_match_rate": "Exact match confirmed / responses",
    "uncertain_rate": "Uncertain / responses",
    "median_seconds_to_first_useful_result": "Median time to first useful result",
    "median_seconds_to_complete": "Median time to complete a search",
    "cost_per_useful_result": "Cost per useful result (reported call cost)",
    "useful_search_rate": "Searches with a validated useful answer in time",
    "stop_rule_saving": "Calls avoided by the stop rule / calls planned",
    "human_verified_accuracy": "Human review agreed / reviewed",
    "ground_truth_agreement": "Independent check agreed / checked (excludes inconclusive)",
    "ground_truth_inconclusive": "Independent checks that were inconclusive",
}


def render(metrics: dict[str, Ratio | Measured | int], title: str = "Sonar metrics") -> str:
    lines = [
        f"# {title}",
        "",
        "Live calls only. Every figure shows its denominator and nothing is estimated.",
        "`n/a` means there is no data yet, which is not the same as zero.",
        "",
        "| Metric | Result |",
        "|---|---|",
    ]
    for key, label in LABELS.items():
        m = metrics[key]
        lines.append(f"| {label} | {m if isinstance(m, int) else m.text} |")
    return "\n".join(lines) + "\n"
