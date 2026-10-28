"""Orchestrator (Bible 14, 27; T4.x). Postgres is the queue (D-006); one process, bounded.

Safety rules enforced here:
- consent and opt-out are re-checked immediately before every dial (FR-06)
- DISPATCHING is committed *before* the network call, and an uncertain dispatch becomes
  DISPATCH_UNKNOWN and is never auto-retried (a duplicate call is worse than a missed one)
- concurrency, daily budget and search deadline are all bounded (FR-09, FR-22, NFR-06)
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from collections.abc import Callable
from datetime import datetime, timedelta

from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings
from app.db.models import Business, CallAttempt, SearchJob
from app.db.repositories import AttemptRepo, AuditRepo, SearchRepo
from app.domain.enums import CallStatus, ErrorClass, SearchStatus
from app.domain.schemas import ParsedQuery
from app.domain.transitions import is_terminal, map_bolna_status
from app.providers.base import (
    CallRequest,
    ProviderBalanceLow,
    ProviderRejected,
    ProviderTimeout,
    ProviderUnavailable,
)
from app.providers.registry import ProviderRegistry
from app.services.directory import ist_day_start
from app.services.finalizer import (
    business_is_callable,
    finalize_attempt,
    plan_retry,
)
from app.services.jobs import enforce_deadlines, refresh_job
from app.services.query import build_user_data
from app.services.retention import purge_old

log = logging.getLogger("sonar.orchestrator")


class Orchestrator:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        providers: ProviderRegistry,
        settings: Settings,
        clock: Callable[[], datetime],
    ) -> None:
        self.sf = session_factory
        self.providers = providers
        self.settings = settings
        self.clock = clock
        self.paused = False  # set when the provider reports a low balance
        self._tasks: set[asyncio.Task] = set()

    # --- startup recovery -------------------------------------------------------------------

    def recover_on_start(self) -> int:
        with self.sf() as s:
            n = AttemptRepo(s).dispatch_unknown_on_start()
            s.commit()
        if n:
            log.warning("%d attempt(s) were mid-dispatch at restart; marked DISPATCH_UNKNOWN", n)
        return n

    # --- one scheduling pass ----------------------------------------------------------------

    async def tick(self) -> None:
        now = self.clock()
        with self.sf() as s:
            enforce_deadlines(s, now)
            s.commit()
        while not self.paused and await self.dispatch_one():
            pass
        await self.reconcile()

    async def dispatch_one(self) -> bool:
        """Claim and dial one due attempt. Returns False when there is nothing to do."""
        now = self.clock()
        with self.sf() as s:
            repo = AttemptRepo(s)
            if repo.count_active() >= self.settings.max_concurrent_calls:
                return False
            attempt = repo.claim_next(now)
            if attempt is None:
                s.commit()
                return False
            job = s.get(SearchJob, attempt.search_job_id)
            business = s.get(Business, attempt.business_id)
            assert job is not None and business is not None

            blocked = self._blocked_reason(s, repo, attempt, job, business, now)
            if blocked:
                terminal = (
                    CallStatus.FAILED
                    if blocked == ErrorClass.BUDGET_EXCEEDED
                    else CallStatus.CANCELLED
                )
                repo.update_status(
                    attempt.id, terminal, failure_reason=str(blocked), error_class=str(blocked)
                )
                refresh_job(s, job.id, now)
                s.commit()
                return True

            parsed = ParsedQuery.model_validate(job.parsed_query)
            request = CallRequest(
                attempt_id=attempt.id,
                agent_key=job.category or parsed.category,
                to_e164=business.phone_e164,
                from_e164=self.settings.bolna_from_phone_number or None,
                user_data=build_user_data(parsed),
            )
            attempt_id, provider_name, job_id = attempt.id, attempt.provider, job.id
            if job.status == SearchStatus.CREATED:
                SearchRepo(s).set_status(job.id, SearchStatus.RUNNING, started_at=now)
            AuditRepo(s).add(
                "system", "call_dispatched", search_job_id=job.id, business_id=business.id
            )
            s.commit()  # DISPATCHING is durable before anything leaves the building

        await self._start_call(attempt_id, job_id, provider_name, request)
        return True

    def _blocked_reason(
        self,
        session: Session,
        repo: AttemptRepo,
        attempt: CallAttempt,
        job: SearchJob,
        business: Business,
        now: datetime,
    ) -> str | None:
        """Second line of defence (FR-06): re-check everything right before dialing."""
        if job.status == SearchStatus.CANCELLED:
            return "JOB_CANCELLED"
        if not business_is_callable(business):
            return "NOT_CONSENTED"
        if attempt.provider != "simulated":
            used = repo.dispatched_since(ist_day_start(now), attempt.provider)
            if used >= self.settings.global_daily_call_budget:
                return ErrorClass.BUDGET_EXCEEDED
        return None

    async def _start_call(
        self, attempt_id: uuid.UUID, job_id: uuid.UUID, provider_name: str, request: CallRequest
    ) -> None:
        try:
            provider = self.providers.get(provider_name)
            ref = await provider.start_call(request)
        except ProviderRejected as exc:
            self._fail(attempt_id, job_id, ErrorClass.PROVIDER_REJECTED, str(exc), retry=False)
        except ProviderBalanceLow:
            self.paused = True
            self._fail(
                attempt_id,
                job_id,
                ErrorClass.INSUFFICIENT_BALANCE,
                "balance low",
                retry=False,
                status=CallStatus.INSUFFICIENT_BALANCE,
            )
            log.error("provider balance is low; dispatching paused")
        except ProviderTimeout:
            with self.sf() as s:
                AttemptRepo(s).mark_dispatch_unknown(attempt_id, "PROVIDER_TIMEOUT")
                s.commit()
        except ProviderUnavailable as exc:
            self._fail(attempt_id, job_id, ErrorClass.PROVIDER_UNAVAILABLE, str(exc), retry=True)
        else:
            with self.sf() as s:
                repo = AttemptRepo(s)
                repo.attach_execution_id(attempt_id, ref.provider_call_id)
                repo.update_status(
                    attempt_id, CallStatus.DIALING, provider_status=ref.provider_status
                )
                s.commit()
            if provider_name == "simulated":
                self._spawn(self._drive_simulated(attempt_id, ref.provider_call_id, provider))

    def _fail(
        self,
        attempt_id: uuid.UUID,
        job_id: uuid.UUID,
        error: ErrorClass,
        reason: str,
        *,
        retry: bool,
        status: CallStatus = CallStatus.FAILED,
    ) -> None:
        now = self.clock()
        with self.sf() as s:
            repo = AttemptRepo(s)
            applied = repo.update_status(
                attempt_id, status, failure_reason=reason[:200], error_class=str(error)
            )
            job = SearchRepo(s).lock(job_id)
            attempt = repo.get(attempt_id)
            if retry and applied and job is not None and attempt is not None:
                plan_retry(s, attempt, job, now, self.settings)
            refresh_job(s, job_id, now)
            s.commit()

    # --- simulated calls --------------------------------------------------------------------

    def _spawn(self, coro) -> None:
        task = asyncio.create_task(coro)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def _drive_simulated(self, attempt_id: uuid.UUID, call_id: str, provider) -> None:
        """Walk a simulated call through its statuses so the UI shows live progress, then
        finalize exactly like a real call: by pulling the record (never from a body)."""
        try:
            sequence = provider.status_sequence(call_id)
            for raw in sequence[:-1]:
                await asyncio.sleep(self.settings.sim_step_seconds)
                mapped = map_bolna_status(raw)
                if mapped is not None and not is_terminal(mapped):
                    with self.sf() as s:
                        AttemptRepo(s).update_status(attempt_id, mapped, provider_status=raw)
                        s.commit()
            await asyncio.sleep(self.settings.sim_step_seconds)
            await finalize_attempt(self.sf, attempt_id, self.providers, self.settings, self.clock)
        except Exception:
            log.exception("simulated call driver failed for attempt %s", attempt_id)

    async def drain(self) -> None:
        """Wait for in-flight simulated calls (used by tests and graceful shutdown)."""
        while self._tasks:
            batch = list(self._tasks)
            # Drop them here: gather() over already-finished tasks returns without yielding, so
            # the add_done_callback that normally discards them would never get to run.
            self._tasks.difference_update(batch)
            await asyncio.gather(*batch, return_exceptions=True)

    # --- reconciler (lost webhooks, restarts) -----------------------------------------------

    async def reconcile(self) -> int:
        now = self.clock()
        cutoff = now - timedelta(seconds=self.settings.reconcile_after_seconds)
        with self.sf() as s:
            stale = [a.id for a in AttemptRepo(s).stale_in_flight(cutoff)]
        for attempt_id in stale:
            await finalize_attempt(self.sf, attempt_id, self.providers, self.settings, self.clock)
        return len(stale)

    # --- long-running loop ------------------------------------------------------------------

    def maintenance(self) -> dict[str, int]:
        """Hourly housekeeping: delete raw provider events and clear old call excerpts."""
        with self.sf() as s:
            counts = purge_old(
                s,
                self.clock(),
                event_days=self.settings.retention_event_days,
                response_days=self.settings.retention_response_days,
            )
            s.commit()
        if any(counts.values()):
            log.info("retention purge: %s", counts)
        return counts

    async def run_forever(self) -> None:
        self.recover_on_start()
        last_maintenance = 0.0
        while True:
            try:
                await self.tick()
                if time.monotonic() - last_maintenance > 3600:
                    last_maintenance = time.monotonic()
                    self.maintenance()
            except Exception:
                log.exception("orchestrator tick failed")
            await asyncio.sleep(self.settings.orchestrator_poll_seconds)
