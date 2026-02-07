"""Edge TTS Provider - Microsoft's free neural TTS."""

import tempfile
from pathlib import Path
from typing import AsyncGenerator

import edge_tts
import numpy as np
import soundfile as sf

from src.api.schemas.tts import VoiceInfo
from src.core.providers.base import TTSProvider, ProviderInfo


EDGE_VOICES = {
    "en-US-JennyNeural": VoiceInfo(
        id="en-US-JennyNeural",
        name="Jenny",
        language="en-US",
        gender="female",
        description="Friendly conversational American voice",
    ),
    "en-US-AriaNeural": VoiceInfo(
        id="en-US-AriaNeural",
        name="Aria",
        language="en-US",
        gender="female",
        description="Professional and clear American voice",
    ),
    "en-US-GuyNeural": VoiceInfo(
        id="en-US-GuyNeural",
        name="Guy",
        language="en-US",
        gender="male",
        description="Casual friendly American male voice",
    ),
    "en-US-ChristopherNeural": VoiceInfo(
        id="en-US-ChristopherNeural",
        name="Christopher",
        language="en-US",
        gender="male",
        description="Professional American male voice",
    ),
    "en-GB-SoniaNeural": VoiceInfo(
        id="en-GB-SoniaNeural",
        name="Sonia",
        language="en-GB",
        gender="female",
        description="Professional British female voice",
    ),
    "en-GB-RyanNeural": VoiceInfo(
        id="en-GB-RyanNeural",
        name="Ryan",
        language="en-GB",
        gender="male",
        description="Professional British male voice",
    ),
    "en-AU-NatashaNeural": VoiceInfo(
        id="en-AU-NatashaNeural",
        name="Natasha",
        language="en-AU",
        gender="female",
        description="Friendly Australian female voice",
    ),
    "en-IN-NeerjaNeural": VoiceInfo(
        id="en-IN-NeerjaNeural",
        name="Neerja",
        language="en-IN",
        gender="female",
        description="Clear Indian English female voice",
    ),
}


class EdgeTTSProvider(TTSProvider):
    """Edge TTS - Microsoft's free neural TTS service."""

    @property
    def info(self) -> ProviderInfo:
        return ProviderInfo(
            id="edge",
            name="Edge TTS",
            description="Microsoft's free neural TTS - no API key required",
            requires_api_key=False,
            is_local=False,
            supports_streaming=True,
        )

    async def synthesize(
        self,
        text: str,
        voice: str = "en-US-JennyNeural",
        speed: float = 1.0,
        api_key: str | None = None,
    ) -> np.ndarray:
        rate_percent = int((speed - 1.0) * 100)
        rate = f"+{rate_percent}%" if rate_percent >= 0 else f"{rate_percent}%"

        communicate = edge_tts.Communicate(text, voice, rate=rate)

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_file:
            tmp_path = tmp_file.name

        try:
            await communicate.save(tmp_path)
            audio_array, sample_rate = sf.read(tmp_path)

            if len(audio_array.shape) > 1:
                audio_array = audio_array.mean(axis=1)

            return audio_array.astype(np.float32)
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    async def synthesize_stream(
        self,
        text: str,
        voice: str = "en-US-JennyNeural",
        speed: float = 1.0,
        api_key: str | None = None,
    ) -> AsyncGenerator[bytes, None]:
        rate_percent = int((speed - 1.0) * 100)
        rate = f"+{rate_percent}%" if rate_percent >= 0 else f"{rate_percent}%"

        communicate = edge_tts.Communicate(text, voice, rate=rate)

        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                yield chunk["data"]

    def get_voices(self, api_key: str | None = None) -> list[VoiceInfo]:
        return list(EDGE_VOICES.values())
