"""Edge TTS Provider - Microsoft's free neural TTS."""

import tempfile
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import AsyncGenerator

import edge_tts
import numpy as np
import soundfile as sf

from src.api.schemas.tts import VoiceInfo
from src.core.providers.base import TTSProvider, ProviderInfo


@dataclass
class WordTiming:
    """Timing information for a single word."""
    word: str
    start_ms: float  # Start time in milliseconds
    end_ms: float    # End time in milliseconds
    char_start: int  # Character offset in original text
    char_end: int    # Character end offset


@dataclass
class SynthesisResult:
    """Result of synthesis with timing data."""
    audio_data: bytes       # MP3 audio bytes
    word_timings: list[WordTiming]
    duration_ms: float


EDGE_VOICES = {
    # American English - Female
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
    "en-US-SaraNeural": VoiceInfo(
        id="en-US-SaraNeural",
        name="Sara",
        language="en-US",
        gender="female",
        description="Cheerful young American voice",
    ),
    "en-US-MichelleNeural": VoiceInfo(
        id="en-US-MichelleNeural",
        name="Michelle",
        language="en-US",
        gender="female",
        description="Warm and calm American voice",
    ),
    # American English - Male
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
    "en-US-EricNeural": VoiceInfo(
        id="en-US-EricNeural",
        name="Eric",
        language="en-US",
        gender="male",
        description="Authoritative American male voice",
    ),
    # British English - Female
    "en-GB-SoniaNeural": VoiceInfo(
        id="en-GB-SoniaNeural",
        name="Sonia",
        language="en-GB",
        gender="female",
        description="Professional British female voice",
    ),
    "en-GB-LibbyNeural": VoiceInfo(
        id="en-GB-LibbyNeural",
        name="Libby",
        language="en-GB",
        gender="female",
        description="Friendly British female voice",
    ),
    # British English - Male
    "en-GB-RyanNeural": VoiceInfo(
        id="en-GB-RyanNeural",
        name="Ryan",
        language="en-GB",
        gender="male",
        description="Professional British male voice",
    ),
    # Australian English
    "en-AU-NatashaNeural": VoiceInfo(
        id="en-AU-NatashaNeural",
        name="Natasha",
        language="en-AU",
        gender="female",
        description="Friendly Australian female voice",
    ),
    "en-AU-WilliamNeural": VoiceInfo(
        id="en-AU-WilliamNeural",
        name="William",
        language="en-AU",
        gender="male",
        description="Professional Australian male voice",
    ),
    # Indian English
    "en-IN-NeerjaNeural": VoiceInfo(
        id="en-IN-NeerjaNeural",
        name="Neerja",
        language="en-IN",
        gender="female",
        description="Clear Indian English female voice",
    ),
    "en-IN-PrabhatNeural": VoiceInfo(
        id="en-IN-PrabhatNeural",
        name="Prabhat",
        language="en-IN",
        gender="male",
        description="Professional Indian English male voice",
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

    async def synthesize_with_timing(
        self,
        text: str,
        voice: str = "en-US-JennyNeural",
        speed: float = 1.0,
    ) -> SynthesisResult:
        """
        Synthesize text and extract word-level timing data.

        Returns audio bytes and timing information for karaoke-style highlighting.
        """
        rate_percent = int((speed - 1.0) * 100)
        rate = f"+{rate_percent}%" if rate_percent >= 0 else f"{rate_percent}%"

        communicate = edge_tts.Communicate(text, voice, rate=rate)

        audio_chunks: list[bytes] = []
        word_timings: list[WordTiming] = []
        char_position = 0
        last_end_ms = 0.0

        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_chunks.append(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                word = chunk["text"]
                # Convert ticks to milliseconds (1 tick = 100 nanoseconds)
                start_ms = chunk["offset"] / 10000
                duration_ms = chunk["duration"] / 10000
                end_ms = start_ms + duration_ms

                # Find word position in original text
                # Search from current position to handle repeated words
                char_start = text.find(word, char_position)
                if char_start == -1:
                    # Fallback: search from beginning
                    char_start = text.find(word)
                if char_start == -1:
                    # Word not found (punctuation or special case)
                    char_start = char_position
                char_end = char_start + len(word)
                char_position = char_end

                word_timings.append(WordTiming(
                    word=word,
                    start_ms=round(start_ms, 2),
                    end_ms=round(end_ms, 2),
                    char_start=char_start,
                    char_end=char_end,
                ))
                last_end_ms = end_ms

        audio_data = b"".join(audio_chunks)

        return SynthesisResult(
            audio_data=audio_data,
            word_timings=word_timings,
            duration_ms=last_end_ms,
        )
