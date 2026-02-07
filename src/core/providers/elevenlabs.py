"""ElevenLabs TTS Provider."""

import tempfile
from pathlib import Path
from typing import AsyncGenerator

import httpx
import numpy as np
import soundfile as sf

from src.api.schemas.tts import VoiceInfo
from src.core.providers.base import TTSProvider, ProviderInfo


# Default ElevenLabs voices (can be extended via API)
ELEVENLABS_VOICES = {
    "21m00Tcm4TlvDq8ikWAM": VoiceInfo(
        id="21m00Tcm4TlvDq8ikWAM",
        name="Rachel",
        language="en",
        gender="female",
        description="Calm, young American female",
    ),
    "AZnzlk1XvdvUeBnXmlld": VoiceInfo(
        id="AZnzlk1XvdvUeBnXmlld",
        name="Domi",
        language="en",
        gender="female",
        description="Strong, confident female",
    ),
    "EXAVITQu4vr4xnSDxMaL": VoiceInfo(
        id="EXAVITQu4vr4xnSDxMaL",
        name="Bella",
        language="en",
        gender="female",
        description="Soft, warm female voice",
    ),
    "ErXwobaYiN019PkySvjV": VoiceInfo(
        id="ErXwobaYiN019PkySvjV",
        name="Antoni",
        language="en",
        gender="male",
        description="Well-rounded male voice",
    ),
    "VR6AewLTigWG4xSOukaG": VoiceInfo(
        id="VR6AewLTigWG4xSOukaG",
        name="Arnold",
        language="en",
        gender="male",
        description="Crisp, authoritative male",
    ),
    "pNInz6obpgDQGcFmaJgB": VoiceInfo(
        id="pNInz6obpgDQGcFmaJgB",
        name="Adam",
        language="en",
        gender="male",
        description="Deep, narrative male voice",
    ),
    "yoZ06aMxZJJ28mfd3POQ": VoiceInfo(
        id="yoZ06aMxZJJ28mfd3POQ",
        name="Sam",
        language="en",
        gender="male",
        description="Dynamic young male voice",
    ),
}


class ElevenLabsTTSProvider(TTSProvider):
    """ElevenLabs TTS API provider."""

    API_URL = "https://api.elevenlabs.io/v1"

    @property
    def info(self) -> ProviderInfo:
        return ProviderInfo(
            id="elevenlabs",
            name="ElevenLabs",
            description="Premium AI voice synthesis with voice cloning",
            requires_api_key=True,
            api_key_url="https://elevenlabs.io/app/settings/api-keys",
            is_local=False,
            supports_streaming=True,
        )

    async def synthesize(
        self,
        text: str,
        voice: str = "21m00Tcm4TlvDq8ikWAM",
        speed: float = 1.0,
        api_key: str | None = None,
    ) -> np.ndarray:
        if not api_key:
            raise ValueError("ElevenLabs API key is required")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.API_URL}/text-to-speech/{voice}",
                headers={
                    "xi-api-key": api_key,
                    "Content-Type": "application/json",
                },
                json={
                    "text": text,
                    "model_id": "eleven_monolingual_v1",
                    "voice_settings": {
                        "stability": 0.5,
                        "similarity_boost": 0.75,
                    },
                },
                timeout=60.0,
            )

            if response.status_code != 200:
                error_msg = response.text
                raise RuntimeError(f"ElevenLabs API error: {error_msg}")

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
        voice: str = "21m00Tcm4TlvDq8ikWAM",
        speed: float = 1.0,
        api_key: str | None = None,
    ) -> AsyncGenerator[bytes, None]:
        if not api_key:
            raise ValueError("ElevenLabs API key is required")

        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                f"{self.API_URL}/text-to-speech/{voice}/stream",
                headers={
                    "xi-api-key": api_key,
                    "Content-Type": "application/json",
                },
                json={
                    "text": text,
                    "model_id": "eleven_monolingual_v1",
                    "voice_settings": {
                        "stability": 0.5,
                        "similarity_boost": 0.75,
                    },
                },
                timeout=60.0,
            ) as response:
                if response.status_code != 200:
                    raise RuntimeError(f"ElevenLabs API error: {response.status_code}")
                async for chunk in response.aiter_bytes():
                    yield chunk

    def get_voices(self, api_key: str | None = None) -> list[VoiceInfo]:
        # Return default voices; could fetch from API with key
        return list(ELEVENLABS_VOICES.values())
