"""Maps a provider name stored on an attempt to a VoiceProvider instance."""

from __future__ import annotations

from app.providers.base import ProviderUnavailable, VoiceProvider


class ProviderRegistry:
    def __init__(self, providers: dict[str, VoiceProvider] | None = None) -> None:
        self._providers: dict[str, VoiceProvider] = dict(providers or {})

    def register(self, name: str, provider: VoiceProvider) -> None:
        self._providers[name] = provider

    def get(self, name: str) -> VoiceProvider:
        try:
            return self._providers[name]
        except KeyError:
            raise ProviderUnavailable(f"provider '{name}' is not configured") from None

    def has(self, name: str) -> bool:
        return name in self._providers
