"""Base TTS Provider interface."""

from abc import ABC, abstractmethod
from typing import AsyncGenerator

import numpy as np
from pydantic import BaseModel, Field

from src.api.schemas.tts import VoiceInfo


class ProviderInfo(BaseModel):
    """Information about a TTS provider."""

    id: str = Field(description="Provider identifier")
    name: str = Field(description="Provider display name")
    description: str = Field(description="Provider description")
    requires_api_key: bool = Field(description="Whether API key is required")
    api_key_url: str | None = Field(default=None, description="URL to get API key")
    is_local: bool = Field(default=False, description="Whether provider runs locally")
    supports_streaming: bool = Field(default=True, description="Whether streaming is supported")


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
