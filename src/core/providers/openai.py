"""OpenAI TTS Provider."""

import tempfile
from pathlib import Path
from typing import AsyncGenerator

import httpx
import numpy as np
import soundfile as sf

from src.api.schemas.tts import VoiceInfo
from src.core.providers.base import TTSProvider, ProviderInfo


OPENAI_VOICES = {
    "alloy": VoiceInfo(
        id="alloy",
        name="Alloy",
        language="en",
        gender="neutral",
        description="Balanced, versatile voice",
    ),
    "echo": VoiceInfo(
        id="echo",
        name="Echo",
        language="en",
        gender="male",
        description="Warm, confident male voice",
    ),
    "fable": VoiceInfo(
        id="fable",
        name="Fable",
        language="en",
        gender="neutral",
        description="Expressive, dynamic voice",
    ),
    "onyx": VoiceInfo(
        id="onyx",
        name="Onyx",
        language="en",
        gender="male",
        description="Deep, authoritative male voice",
    ),
    "nova": VoiceInfo(
        id="nova",
        name="Nova",
        language="en",
        gender="female",
        description="Warm, engaging female voice",
    ),
    "shimmer": VoiceInfo(
        id="shimmer",
        name="Shimmer",
        language="en",
        gender="female",
        description="Clear, optimistic female voice",
    ),
}


class OpenAITTSProvider(TTSProvider):
    """OpenAI TTS API provider."""

    API_URL = "https://api.openai.com/v1/audio/speech"

    @property
    def info(self) -> ProviderInfo:
        return ProviderInfo(
            id="openai",
            name="OpenAI TTS",
            description="OpenAI's high-quality TTS API",
            requires_api_key=True,
            api_key_url="https://platform.openai.com/api-keys",
            is_local=False,
            supports_streaming=True,
        )

    async def synthesize(
        self,
        text: str,
        voice: str = "alloy",
        speed: float = 1.0,
        api_key: str | None = None,
    ) -> np.ndarray:
        if not api_key:
            raise ValueError("OpenAI API key is required")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.API_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "tts-1",
                    "input": text,
                    "voice": voice,
                    "speed": speed,
                    "response_format": "mp3",
                },
                timeout=60.0,
            )

            if response.status_code != 200:
                error_msg = response.text
                raise RuntimeError(f"OpenAI API error: {error_msg}")

            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_file:
                tmp_file.write(response.content)
                tmp_path = tmp_file.name

            try:
                audio_array, _ = sf.read(tmp_path)
                if len(audio_array.shape) > 1:
                    audio_array = audio_array.mean(axis=1)
                return audio_array.astype(np.float32)
            finally:
                Path(tmp_path).unlink(missing_ok=True)

    async def synthesize_stream(
        self,
        text: str,
        voice: str = "alloy",
        speed: float = 1.0,
        api_key: str | None = None,
    ) -> AsyncGenerator[bytes, None]:
        if not api_key:
            raise ValueError("OpenAI API key is required")

        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                self.API_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "tts-1",
                    "input": text,
                    "voice": voice,
                    "speed": speed,
                    "response_format": "mp3",
                },
                timeout=60.0,
            ) as response:
                if response.status_code != 200:
                    raise RuntimeError(f"OpenAI API error: {response.status_code}")
                async for chunk in response.aiter_bytes():
                    yield chunk

    def get_voices(self, api_key: str | None = None) -> list[VoiceInfo]:
        return list(OPENAI_VOICES.values())
