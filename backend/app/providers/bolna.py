"""BolnaVoiceProvider (T5.3): the only code that speaks Bolna's HTTP API.

Built from the documented contract (Bible 21.3, read 2026-10-24). Everything we *assume* about
payload shapes lives in the FIELD NAMES block below, so when real payloads are captured in the
Phase 1 spike only that block and the normalisers need to change.

Safety rules enforced here:
- never sets retry_config, scheduled_at or bypass_call_guardrails (D-010)
- the API key is sent only as a Bearer header and never appears in logs, errors or records
- a request that MAY have reached Bolna and gave no clear answer is an UNKNOWN outcome
  (ProviderTimeout), never a retryable failure: POST /call has no idempotency key (A-11), and a
  duplicate call to a shopkeeper is worse than a missed one (D-048)
"""

from __future__ import annotations

import copy
import logging
import re
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx

from app.providers.base import (
    CallRequest,
    ProviderBalanceLow,
    ProviderCallRecord,
    ProviderCallRef,
    ProviderRejected,
    ProviderTimeout,
    ProviderUnavailable,
)

log = logging.getLogger("sonar.bolna")

# --- FIELD NAMES (documented, NOT yet captured: re-base on the spike's real payloads) ----------
CALL_RESPONSE_ID = "execution_id"  # POST /call -> { message, status, execution_id }
CALL_RESPONSE_STATUS = "status"
EXEC_STATUS = "status"  # GET /executions/{id}
EXEC_TRANSCRIPT = "transcript"
EXEC_DURATION = "conversation_duration"
EXEC_COST = "total_cost"
EXEC_EXTRACTED = "extracted_data"
EXEC_TELEPHONY = "telephony_data"
EXEC_RECORDING_URL = "recording_url"
# extraction names we configure in the dashboard (docs/agent/prompt_v1.md section 3)
KNOWN_EXTRACTIONS = frozenset(
    {
        "availability",
        "exact_match_confirmed",
        "alternative_offered",
        "price_amount",
        "price_currency_stated",
        "quantity_available",
        "wait_time_minutes",
        "open_now",
        "opt_out_requested",
        "call_outcome",
        "supporting_quote",
    }
)
_VALUE_KEYS = ("objective", "subjective", "value", "answer")  # how a wrapped answer may appear
# ------------------------------------------------------------------------------------------------

TIMEOUT = httpx.Timeout(connect=5.0, read=15.0, write=10.0, pool=5.0)
_BALANCE_HINTS = ("balance", "insufficient", "credit", "wallet")
_PHONE = re.compile(r"\+\d[\d\s\-]{8,}\d|(?<![\w.\-])(?:91|0)?[6-9]\d{9}(?![\w\-])")


def mask_phone(value: str) -> str:
    digits = re.sub(r"\D", "", value)
    return "***" if len(digits) < 8 else f"+{digits[:2]}{'*' * (len(digits) - 5)}{digits[-3:]}"


def _redact(value: Any, key: str = "") -> Any:
    """Strip recording URLs and phone numbers from the raw record kept for debugging."""
    if key.lower() == EXEC_RECORDING_URL:
        return "<redacted>"
    if isinstance(value, dict):
        return {k: _redact(v, k) for k, v in value.items()}
    if isinstance(value, list):
        return [_redact(v, key) for v in value]
    if isinstance(value, str):
        return _PHONE.sub(lambda m: mask_phone(m.group(0)), value)
    return value


def _message(response: httpx.Response) -> str:
    try:
        body = response.json()
        if isinstance(body, dict) and isinstance(body.get("message"), str):
            return body["message"][:200]
    except ValueError:
        pass
    return (response.text or f"HTTP {response.status_code}")[:200]


def _json_object(response: httpx.Response) -> dict[str, Any] | None:
    try:
        body = response.json()
    except ValueError:
        return None
    return body if isinstance(body, dict) else None


# --- normalisers (the shapes the docs disagree about) ------------------------------------------


def normalize_transcript(value: Any) -> str | None:
    """A string, or a list of turns, becomes plain 'speaker: text' lines."""
    if isinstance(value, str):
        return value or None
    if isinstance(value, list):
        lines = []
        for turn in value:
            if isinstance(turn, dict):
                who = turn.get("role") or turn.get("speaker") or "unknown"
                text = turn.get("content") or turn.get("text") or ""
                lines.append(f"{who}: {text}")
            elif isinstance(turn, str):
                lines.append(turn)
        return "\n".join(lines) or None
    return None


def _unwrap(value: Any) -> tuple[Any, float | None]:
    """An answer may be a plain value or {objective|subjective|value: ..., confidence: ...}."""
    if isinstance(value, dict):
        confidence = value.get("confidence")
        for key in _VALUE_KEYS:
            if key in value:
                inner = value[key]
                return (None if inner == "" else inner), (
                    float(confidence) if isinstance(confidence, int | float) else None
                )
        return None, None
    return (None if value == "" else value), None


def normalize_extracted(data: Any) -> dict[str, Any] | None:
    """Flatten extracted_data to {extraction_name: value}. The docs show both a flat shape and a
    nested `extracted_data[category][name]` shape, so both are accepted. Unknown names are ignored.
    The single `confidence` we keep is the lowest per-field one, stored raw and never used to
    promote an answer (V11)."""
    if not isinstance(data, dict) or not data:
        return None
    found: dict[str, Any] = {}
    confidences: list[float] = []

    def take(name: str, raw: Any) -> None:
        value, confidence = _unwrap(raw)
        found[name] = value
        if confidence is not None:
            confidences.append(confidence)

    for key, value in data.items():
        if key in KNOWN_EXTRACTIONS:
            take(key, value)
        elif isinstance(value, dict):  # a category group
            for inner_key, inner_value in value.items():
                if inner_key in KNOWN_EXTRACTIONS:
                    take(inner_key, inner_value)
    if not found:
        return None
    if confidences:
        found["confidence"] = min(confidences)
    return found


def _decimal(value: Any) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        d = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    return d if d.is_finite() else None


def _cost(value: Any) -> Decimal | None:
    """A cost is never negative; anything else is unknown rather than stored as a nonsense value."""
    d = _decimal(value)
    return d if d is not None and d >= 0 else None


def _seconds(value: Any) -> int | None:
    d = _decimal(value)
    return None if d is None or d < 0 else int(d)


# --- the provider ------------------------------------------------------------------------------


class BolnaVoiceProvider:
    name = "bolna"

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.bolna.ai",
        agent_ids: dict[str, str] | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("BolnaVoiceProvider needs an API key")
        self._key = api_key
        self._base = base_url.rstrip("/")
        self._agent_ids = {k: v for k, v in (agent_ids or {}).items() if v}
        self._client = client or httpx.AsyncClient(timeout=TIMEOUT)

    async def aclose(self) -> None:
        await self._client.aclose()

    def has_agent(self, agent_key: str) -> bool:
        """Whether a Bolna agent is configured for this category (checked before planning)."""
        return agent_key in self._agent_ids

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._key}", "Content-Type": "application/json"}

    # POST /call ----------------------------------------------------------------------------

    def _call_body(self, req: CallRequest) -> dict[str, Any]:
        agent_id = self._agent_ids.get(req.agent_key)
        if not agent_id:
            raise ProviderRejected(f"no Bolna agent is configured for '{req.agent_key}'")
        body: dict[str, Any] = {
            "agent_id": agent_id,
            "recipient_phone_number": req.to_e164,
            "user_data": req.user_data,
        }
        if req.from_e164:
            body["from_phone_number"] = req.from_e164
        # Deliberately absent: retry_config, scheduled_at, bypass_call_guardrails (D-010).
        return body

    async def start_call(self, req: CallRequest) -> ProviderCallRef:
        body = self._call_body(req)  # raises before any network use if misconfigured
        try:
            response = await self._client.post(
                f"{self._base}/call", headers=self._headers(), json=body
            )
        except (httpx.ConnectError, httpx.ConnectTimeout, httpx.PoolTimeout) as exc:
            # the request never left this machine: safe to treat as a retryable failure
            raise ProviderUnavailable(f"cannot reach Bolna ({type(exc).__name__})") from None
        except httpx.TransportError as exc:
            # it may have been received: the outcome is unknown, so it is never retried
            raise ProviderTimeout(f"no clear answer from Bolna ({type(exc).__name__})") from None

        status = response.status_code
        if status == 200:
            data = _json_object(response)
            call_id = data.get(CALL_RESPONSE_ID) if data else None
            if not call_id:
                # a 200 without an id: the call may exist, so do not redial
                raise ProviderTimeout("Bolna accepted the request but returned no execution id")
            log.info("call queued to %s", mask_phone(req.to_e164))
            return ProviderCallRef(
                provider="bolna",
                provider_call_id=str(call_id),
                provider_status=str(data.get(CALL_RESPONSE_STATUS) or "queued"),
            )
        message = _message(response)
        if status == 400:
            if any(hint in message.lower() for hint in _BALANCE_HINTS):
                raise ProviderBalanceLow(message)
            raise ProviderRejected(message)
        if status in (401, 403):
            raise ProviderRejected("Bolna rejected the API key (check BOLNA_API_KEY)")
        if status == 429:
            raise ProviderUnavailable("Bolna rate limit reached")
        if 400 <= status < 500:
            raise ProviderRejected(message)
        # 5xx: the call may or may not have started
        raise ProviderTimeout(f"Bolna server error {status}; outcome unknown")

    # GET /executions/{id} --------------------------------------------------------------------

    async def get_call(self, provider_call_id: str) -> ProviderCallRecord:
        try:
            response = await self._client.get(
                f"{self._base}/executions/{provider_call_id}", headers=self._headers()
            )
        except httpx.TransportError as exc:
            # reads are safe to repeat
            raise ProviderUnavailable(f"cannot read from Bolna ({type(exc).__name__})") from None

        status = response.status_code
        if status in (401, 403):
            raise ProviderRejected("Bolna rejected the API key (check BOLNA_API_KEY)")
        if status == 404:
            raise ProviderRejected("Bolna has no such execution")
        if status == 429 or status >= 500:
            raise ProviderUnavailable(f"Bolna returned {status}")
        if status != 200:
            raise ProviderRejected(_message(response))
        data = _json_object(response)
        if data is None:
            raise ProviderUnavailable("Bolna returned a response that is not a JSON object")

        return ProviderCallRecord(
            provider_call_id=provider_call_id,
            provider_status=str(data.get(EXEC_STATUS) or ""),
            transcript=normalize_transcript(data.get(EXEC_TRANSCRIPT)),
            extracted=normalize_extracted(data.get(EXEC_EXTRACTED)),
            duration_seconds=_seconds(data.get(EXEC_DURATION)),
            cost_amount=_cost(data.get(EXEC_COST)),
            cost_currency=None,  # unknown until the spike (S-6) shows what the field means
            raw=_redact(copy.deepcopy(data)),
        )
