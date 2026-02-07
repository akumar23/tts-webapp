"""TTS request and response schemas."""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class AudioFormat(str, Enum):
    """Supported audio output formats."""

    WAV = "wav"
    MP3 = "mp3"
    OGG = "ogg"


class TTSRequest(BaseModel):
    """Text-to-speech synthesis request."""

    text: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="Text to synthesize into speech",
    )
    provider: str = Field(
        default="edge",
        description="TTS provider to use (edge, openai, elevenlabs)",
    )
    voice: Optional[str] = Field(
        default=None,
        description="Voice ID to use for synthesis",
    )
    speed: float = Field(
        default=1.0,
        ge=0.5,
        le=2.0,
        description="Speech speed multiplier (0.5-2.0)",
    )
    format: AudioFormat = Field(
        default=AudioFormat.MP3,
        description="Output audio format",
    )
    api_key: Optional[str] = Field(
        default=None,
        description="API key for the provider (if required)",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "text": "Hello, welcome to the text-to-speech service!",
                    "provider": "edge",
                    "voice": "en-US-JennyNeural",
                    "speed": 1.0,
                    "format": "mp3",
                }
            ]
        }
    }


class TTSResponse(BaseModel):
    """TTS synthesis response metadata."""

    duration_seconds: float = Field(description="Duration of generated audio in seconds")
    processing_time_ms: float = Field(description="Time taken to process the request")
    provider: str = Field(description="Provider used for synthesis")
    voice: str = Field(description="Voice used for synthesis")
    format: str = Field(description="Audio format of the response")


class VoiceInfo(BaseModel):
    """Information about an available voice."""

    id: str = Field(description="Unique voice identifier")
    name: str = Field(description="Human-readable voice name")
    language: str = Field(description="Voice language code")
    gender: Optional[str] = Field(default=None, description="Voice gender")
    description: Optional[str] = Field(default=None, description="Voice description")


class ProviderInfoResponse(BaseModel):
    """Information about a TTS provider."""

    id: str = Field(description="Provider identifier")
    name: str = Field(description="Provider display name")
    description: str = Field(description="Provider description")
    requires_api_key: bool = Field(description="Whether API key is required")
    api_key_url: Optional[str] = Field(default=None, description="URL to get API key")
    is_local: bool = Field(description="Whether provider runs locally")
    supports_streaming: bool = Field(description="Whether streaming is supported")


class OpenAISpeechRequest(BaseModel):
    """OpenAI-compatible speech request format."""

    model: str = Field(default="tts-1", description="TTS model to use")
    input: str = Field(..., min_length=1, max_length=5000, description="Text to synthesize")
    voice: str = Field(default="alloy", description="Voice to use")
    response_format: str = Field(default="mp3", description="Audio format")
    speed: float = Field(default=1.0, ge=0.25, le=4.0, description="Speech speed")
