"""Provider Manager - handles multiple TTS providers."""

from typing import AsyncGenerator

import numpy as np

from src.api.schemas.tts import VoiceInfo
from src.core.providers.base import TTSProvider, ProviderInfo
from src.core.providers.edge import EdgeTTSProvider
from src.core.providers.openai import OpenAITTSProvider
from src.core.providers.elevenlabs import ElevenLabsTTSProvider


class ProviderManager:
    """Manages multiple TTS providers."""

    def __init__(self) -> None:
        self._providers: dict[str, TTSProvider] = {
            "edge": EdgeTTSProvider(),
            "openai": OpenAITTSProvider(),
            "elevenlabs": ElevenLabsTTSProvider(),
        }

    def get_provider(self, provider_id: str) -> TTSProvider:
        """Get a provider by ID."""
        if provider_id not in self._providers:
            available = ", ".join(self._providers.keys())
            raise ValueError(f"Unknown provider '{provider_id}'. Available: {available}")
        return self._providers[provider_id]

    def list_providers(self) -> list[ProviderInfo]:
        """List all available providers."""
        return [p.info for p in self._providers.values()]

    def get_voices(self, provider_id: str, api_key: str | None = None) -> list[VoiceInfo]:
        """Get voices for a specific provider."""
        provider = self.get_provider(provider_id)
        return provider.get_voices(api_key)

    async def synthesize(
        self,
        text: str,
        provider_id: str = "edge",
        voice: str | None = None,
        speed: float = 1.0,
        api_key: str | None = None,
    ) -> np.ndarray:
        """Synthesize text using the specified provider."""
        provider = self.get_provider(provider_id)

        if not provider.validate_api_key(api_key):
            raise ValueError(f"{provider.info.name} requires an API key")

        # Use default voice if not specified
        if not voice:
            voices = provider.get_voices(api_key)
            voice = voices[0].id if voices else None

        if not voice:
            raise ValueError("No voice specified and no default available")

        return await provider.synthesize(text, voice, speed, api_key)

    async def synthesize_stream(
        self,
        text: str,
        provider_id: str = "edge",
        voice: str | None = None,
        speed: float = 1.0,
        api_key: str | None = None,
    ) -> AsyncGenerator[bytes, None]:
        """Stream audio from the specified provider."""
        provider = self.get_provider(provider_id)

        if not provider.validate_api_key(api_key):
            raise ValueError(f"{provider.info.name} requires an API key")

        if not voice:
            voices = provider.get_voices(api_key)
            voice = voices[0].id if voices else None

        if not voice:
            raise ValueError("No voice specified and no default available")

        async for chunk in provider.synthesize_stream(text, voice, speed, api_key):
            yield chunk


# Singleton instance
_manager: ProviderManager | None = None


def get_provider_manager() -> ProviderManager:
    """Get or create the provider manager singleton."""
    global _manager
    if _manager is None:
        _manager = ProviderManager()
    return _manager
