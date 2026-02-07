"""Base TTS Provider interface."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import AsyncGenerator

import numpy as np

from src.api.schemas.tts import VoiceInfo


@dataclass
class ProviderInfo:
    """Information about a TTS provider."""

    id: str
    name: str
    description: str
    requires_api_key: bool
    api_key_url: str | None = None
    is_local: bool = False
    supports_streaming: bool = True


class TTSProvider(ABC):
    """Abstract base class for TTS providers."""

    @property
    @abstractmethod
    def info(self) -> ProviderInfo:
        """Return provider information."""
        pass

    @abstractmethod
    async def synthesize(
        self,
        text: str,
        voice: str,
        speed: float = 1.0,
        api_key: str | None = None,
    ) -> np.ndarray:
        """
        Synthesize text to audio array.

        Args:
            text: Text to synthesize
            voice: Voice ID to use
            speed: Speech speed multiplier
            api_key: Optional API key (for cloud providers)

        Returns:
            NumPy array of audio samples
        """
        pass

    @abstractmethod
    async def synthesize_stream(
        self,
        text: str,
        voice: str,
        speed: float = 1.0,
        api_key: str | None = None,
    ) -> AsyncGenerator[bytes, None]:
        """Stream synthesized audio chunks."""
        pass

    @abstractmethod
    def get_voices(self, api_key: str | None = None) -> list[VoiceInfo]:
        """Return list of available voices."""
        pass

    def validate_api_key(self, api_key: str | None) -> bool:
        """Validate that API key is provided if required."""
        if self.info.requires_api_key and not api_key:
            return False
        return True
