"""VoiceProvider interface (Bible 15, T5.1). Everything provider-specific stays behind this."""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Any, Literal, Protocol
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

E164 = re.compile(r"^\+[1-9][0-9]{7,14}$")
_MAX_VALUE_LEN = 200


class ProviderError(Exception):
    """Base class for provider failures."""


class ProviderRejected(ProviderError):
    """The provider refused the request (4xx). Never retried."""


class ProviderUnavailable(ProviderError):
    """5xx or network failure. May be retried with backoff."""


class ProviderTimeout(ProviderError):
    """No response in time. The call may or may not have started (see DISPATCH_UNKNOWN)."""


class ProviderBalanceLow(ProviderError):
    """Out of credit. Stop dispatching and alert the operator."""


class CallRequest(BaseModel):
    attempt_id: UUID
    agent_key: str  # e.g. "pharmacy" resolves to BOLNA_AGENT_ID_PHARMACY
    to_e164: str
    from_e164: str | None = None
    user_data: dict[str, str] = Field(default_factory=dict)  # whitelisted values only

    @field_validator("to_e164", "from_e164")
    @classmethod
    def _e164(cls, v: str | None) -> str | None:
        if v is not None and not E164.match(v):
            raise ValueError("phone number must be E.164")
        return v

    @field_validator("user_data")
    @classmethod
    def _bounded(cls, v: dict[str, str]) -> dict[str, str]:
        for key, value in v.items():
            if not isinstance(value, str) or len(value) > _MAX_VALUE_LEN:
                raise ValueError(f"user_data[{key!r}] must be a string of at most 200 characters")
        return v


class ProviderCallRef(BaseModel):
    provider: Literal["bolna", "simulated"]
    provider_call_id: str
    provider_status: str


class ProviderCallRecord(BaseModel):
    provider_call_id: str
    provider_status: str
    transcript: str | None = None
    extracted: dict[str, Any] | None = None  # raw and untrusted
    duration_seconds: int | None = None
    cost_amount: Decimal | None = None
    cost_currency: str | None = None
    raw: dict[str, Any] = Field(default_factory=dict)  # redacted before persistence


class VoiceProvider(Protocol):
    name: str

    async def start_call(self, req: CallRequest) -> ProviderCallRef: ...

    async def get_call(self, provider_call_id: str) -> ProviderCallRecord: ...
