"""Edge TTS Engine wrapper - uses Microsoft's free neural TTS."""

import asyncio
import tempfile
from functools import lru_cache
from io import BytesIO
from pathlib import Path
from typing import AsyncGenerator

import edge_tts
import numpy as np
import soundfile as sf
import structlog

from src.api.schemas.tts import VoiceInfo
from src.config import get_settings

logger = structlog.get_logger(__name__)

# Popular Edge TTS voices with metadata
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


class EdgeTTSEngine:
    """Edge TTS Engine - Microsoft's free neural TTS service."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self._loaded = True  # No model loading needed for edge-tts

    async def load_model(self) -> None:
        """No model loading needed for edge-tts."""
        logger.info("Edge TTS engine initialized (no model download needed)")

    async def synthesize(
        self,
        text: str,
        voice: str = "en-US-JennyNeural",
        speed: float = 1.0,
    ) -> np.ndarray:
        """
        Synthesize text to audio array.

        Args:
            text: Text to synthesize
            voice: Voice ID to use
            speed: Speech speed multiplier (0.5-2.0)

        Returns:
            NumPy array of audio samples
        """
        if voice not in EDGE_VOICES:
            available = ", ".join(list(EDGE_VOICES.keys())[:5]) + "..."
            raise ValueError(f"Unknown voice '{voice}'. Available: {available}")

        # Convert speed to rate string (+50% = "+50%", -25% = "-25%")
        rate_percent = int((speed - 1.0) * 100)
        rate = f"+{rate_percent}%" if rate_percent >= 0 else f"{rate_percent}%"

        communicate = edge_tts.Communicate(text, voice, rate=rate)

        # Use temporary file for audio
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_file:
            tmp_path = tmp_file.name

        try:
            await communicate.save(tmp_path)

            # Read the audio file
            audio_array, sample_rate = sf.read(tmp_path)

            # Convert to mono if stereo
            if len(audio_array.shape) > 1:
                audio_array = audio_array.mean(axis=1)

            # Resample to target sample rate if needed
            if sample_rate != self.settings.sample_rate:
                # Simple resampling (for better quality, use librosa)
                duration = len(audio_array) / sample_rate
                target_samples = int(duration * self.settings.sample_rate)
                indices = np.linspace(0, len(audio_array) - 1, target_samples).astype(int)
                audio_array = audio_array[indices]

            logger.info(
                "Synthesized audio",
                text_length=len(text),
                voice=voice,
                speed=speed,
                audio_samples=len(audio_array),
                duration_seconds=len(audio_array) / self.settings.sample_rate,
            )

            return audio_array.astype(np.float32)

        finally:
            # Clean up temp file
            Path(tmp_path).unlink(missing_ok=True)

    async def synthesize_stream(
        self,
        text: str,
        voice: str = "en-US-JennyNeural",
        speed: float = 1.0,
    ) -> AsyncGenerator[bytes, None]:
        """
        Stream synthesized audio chunks.

        Yields MP3 audio chunks for low-latency playback.

        Args:
            text: Text to synthesize
            voice: Voice ID to use
            speed: Speech speed multiplier

        Yields:
            Bytes of audio data
        """
        if voice not in EDGE_VOICES:
            available = ", ".join(list(EDGE_VOICES.keys())[:5]) + "..."
            raise ValueError(f"Unknown voice '{voice}'. Available: {available}")

        rate_percent = int((speed - 1.0) * 100)
        rate = f"+{rate_percent}%" if rate_percent >= 0 else f"{rate_percent}%"

        communicate = edge_tts.Communicate(text, voice, rate=rate)

        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                yield chunk["data"]

    def get_available_voices(self) -> list[VoiceInfo]:
        """Return list of available voices."""
        return list(EDGE_VOICES.values())

    def is_loaded(self) -> bool:
        """Check if engine is ready."""
        return self._loaded


# Alias for backward compatibility
KokoroEngine = EdgeTTSEngine

# Singleton engine instance
_engine_instance: EdgeTTSEngine | None = None


@lru_cache
def get_tts_engine() -> EdgeTTSEngine:
    """Get or create the TTS engine singleton."""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = EdgeTTSEngine()
    return _engine_instance
