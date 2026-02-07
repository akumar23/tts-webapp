"""TTS Providers - Multiple backend support."""

from src.core.providers.base import TTSProvider, ProviderInfo
from src.core.providers.edge import EdgeTTSProvider
from src.core.providers.openai import OpenAITTSProvider
from src.core.providers.elevenlabs import ElevenLabsTTSProvider

__all__ = [
    "TTSProvider",
    "ProviderInfo",
    "EdgeTTSProvider",
    "OpenAITTSProvider",
    "ElevenLabsTTSProvider",
]
