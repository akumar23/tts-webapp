"""Text-to-Speech API endpoints with multi-provider support."""

import time
from io import BytesIO
from typing import Annotated

import soundfile as sf
from fastapi import APIRouter, Depends, HTTPException, Response, Query
from fastapi.responses import StreamingResponse

from src.api.schemas.tts import (
    AudioFormat,
    OpenAISpeechRequest,
    TTSRequest,
    VoiceInfo,
    ProviderInfoResponse,
)
from src.config import Settings, get_settings
from src.core.provider_manager import ProviderManager, get_provider_manager

router = APIRouter(prefix="/v1/tts", tags=["Text-to-Speech"])


MEDIA_TYPES = {
    AudioFormat.WAV: "audio/wav",
    AudioFormat.MP3: "audio/mpeg",
    AudioFormat.OGG: "audio/ogg",
}

FORMAT_MAP = {
    AudioFormat.WAV: "WAV",
    AudioFormat.MP3: "MP3",
    AudioFormat.OGG: "OGG",
}


@router.get("/providers", response_model=list[ProviderInfoResponse])
async def list_providers(
    manager: Annotated[ProviderManager, Depends(get_provider_manager)],
) -> list[ProviderInfoResponse]:
    """List all available TTS providers."""
    providers = manager.list_providers()
    return [
        ProviderInfoResponse(
            id=p.id,
            name=p.name,
            description=p.description,
            requires_api_key=p.requires_api_key,
            api_key_url=p.api_key_url,
            is_local=p.is_local,
            supports_streaming=p.supports_streaming,
        )
        for p in providers
    ]


@router.get("/voices", response_model=list[VoiceInfo])
async def list_voices(
    manager: Annotated[ProviderManager, Depends(get_provider_manager)],
    provider: str = Query(default="edge", description="Provider ID"),
    api_key: str | None = Query(default=None, description="API key if required"),
) -> list[VoiceInfo]:
    """List available voices for a provider."""
    try:
        return manager.get_voices(provider, api_key)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/synthesize")
async def synthesize_speech(
    request: TTSRequest,
    manager: Annotated[ProviderManager, Depends(get_provider_manager)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> Response:
    """
    Synthesize text to speech using the specified provider.

    Returns audio file in the requested format.
    """
    start_time = time.perf_counter()

    if len(request.text) > settings.max_text_length:
        raise HTTPException(
            status_code=400,
            detail=f"Text exceeds maximum length of {settings.max_text_length} characters",
        )

    try:
        audio_array = await manager.synthesize(
            text=request.text,
            provider_id=request.provider,
            voice=request.voice,
            speed=request.speed,
            api_key=request.api_key,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=f"TTS synthesis failed: {e}")

    if len(audio_array) == 0:
        raise HTTPException(status_code=500, detail="No audio generated")

    buffer = BytesIO()
    sf.write(buffer, audio_array, settings.sample_rate, format=FORMAT_MAP[request.format])
    buffer.seek(0)

    processing_time_ms = (time.perf_counter() - start_time) * 1000
    duration_seconds = len(audio_array) / settings.sample_rate

    return Response(
        content=buffer.read(),
        media_type=MEDIA_TYPES[request.format],
        headers={
            "X-Processing-Time-Ms": f"{processing_time_ms:.2f}",
            "X-Audio-Duration-Seconds": f"{duration_seconds:.2f}",
            "X-Provider": request.provider,
            "X-Voice": request.voice or "default",
            "Content-Disposition": f'attachment; filename="speech.{request.format.value}"',
        },
    )


@router.post("/stream")
async def stream_speech(
    request: TTSRequest,
    manager: Annotated[ProviderManager, Depends(get_provider_manager)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> StreamingResponse:
    """
    Stream synthesized speech in real-time.

    Audio is streamed as chunks for low-latency playback.
    """
    if len(request.text) > settings.max_text_length:
        raise HTTPException(
            status_code=400,
            detail=f"Text exceeds maximum length of {settings.max_text_length} characters",
        )

    async def audio_generator():
        try:
            async for chunk in manager.synthesize_stream(
                text=request.text,
                provider_id=request.provider,
                voice=request.voice,
                speed=request.speed,
                api_key=request.api_key,
            ):
                yield chunk
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Streaming failed: {e}")

    return StreamingResponse(
        audio_generator(),
        media_type="audio/mpeg",
        headers={
            "Transfer-Encoding": "chunked",
            "X-Provider": request.provider,
        },
    )


# OpenAI-Compatible Endpoint
@router.post("/audio/speech")
async def openai_compatible_speech(
    request: OpenAISpeechRequest,
    manager: Annotated[ProviderManager, Depends(get_provider_manager)],
    settings: Annotated[Settings, Depends(get_settings)],
    api_key: str | None = Query(default=None, alias="api-key"),
) -> Response:
    """
    OpenAI-compatible TTS endpoint.

    Matches the OpenAI /v1/audio/speech API format.
    Uses OpenAI provider if API key provided, otherwise Edge TTS.
    """
    start_time = time.perf_counter()

    # Determine provider based on API key
    provider_id = "openai" if api_key else "edge"

    try:
        audio_array = await manager.synthesize(
            text=request.input,
            provider_id=provider_id,
            voice=request.voice,
            speed=request.speed,
            api_key=api_key,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=f"TTS synthesis failed: {e}")

    buffer = BytesIO()
    format_mapping = {"wav": "WAV", "mp3": "MP3", "opus": "OGG", "ogg": "OGG", "flac": "FLAC"}
    audio_format = format_mapping.get(request.response_format, "MP3")
    sf.write(buffer, audio_array, settings.sample_rate, format=audio_format)
    buffer.seek(0)

    media_type_mapping = {
        "wav": "audio/wav",
        "mp3": "audio/mpeg",
        "opus": "audio/ogg",
        "ogg": "audio/ogg",
        "flac": "audio/flac",
    }
    media_type = media_type_mapping.get(request.response_format, "audio/mpeg")

    processing_time_ms = (time.perf_counter() - start_time) * 1000

    return Response(
        content=buffer.read(),
        media_type=media_type,
        headers={
            "X-Processing-Time-Ms": f"{processing_time_ms:.2f}",
        },
    )
