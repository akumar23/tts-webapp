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
)
from src.config import Settings, get_settings
from src.core.cache import AudioCache, get_audio_cache
from src.core.provider_manager import ProviderManager, get_provider_manager
from src.core.providers.base import ProviderInfo

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


@router.get("/providers", response_model=list[ProviderInfo])
async def list_providers(
    manager: Annotated[ProviderManager, Depends(get_provider_manager)],
) -> list[ProviderInfo]:
    """List all available TTS providers."""
    return manager.list_providers()


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
    cache: Annotated[AudioCache, Depends(get_audio_cache)],
) -> Response:
    """
    Synthesize text to speech using the specified provider.

    Returns audio file in the requested format. Results are cached for faster
    subsequent requests with identical parameters.
    """
    start_time = time.perf_counter()

    if len(request.text) > settings.max_text_length:
        raise HTTPException(
            status_code=400,
            detail=f"Text exceeds maximum length of {settings.max_text_length} characters",
        )

    voice = request.voice or settings.default_voice
    cache_key = cache.generate_key(
        text=request.text,
        provider=request.provider,
        voice=voice,
        speed=request.speed,
        audio_format=request.format.value,
    )

    # Check cache first
    cached_audio = await cache.get(cache_key)
    if cached_audio:
        processing_time_ms = (time.perf_counter() - start_time) * 1000
        return Response(
            content=cached_audio,
            media_type=MEDIA_TYPES[request.format],
            headers={
                "X-Processing-Time-Ms": f"{processing_time_ms:.2f}",
                "X-Provider": request.provider,
                "X-Voice": voice,
                "X-Cache": "HIT",
                "Content-Disposition": f'attachment; filename="speech.{request.format.value}"',
            },
        )

    # Synthesize audio
    try:
        audio_array = await manager.synthesize(
            text=request.text,
            provider_id=request.provider,
            voice=voice,
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
    audio_bytes = buffer.read()

    # Store in cache (async, don't wait)
    await cache.set(cache_key, audio_bytes)

    processing_time_ms = (time.perf_counter() - start_time) * 1000
    duration_seconds = len(audio_array) / settings.sample_rate

    return Response(
        content=audio_bytes,
        media_type=MEDIA_TYPES[request.format],
        headers={
            "X-Processing-Time-Ms": f"{processing_time_ms:.2f}",
            "X-Audio-Duration-Seconds": f"{duration_seconds:.2f}",
            "X-Provider": request.provider,
            "X-Voice": voice,
            "X-Cache": "MISS",
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
    cache: Annotated[AudioCache, Depends(get_audio_cache)],
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

    cache_key = cache.generate_key(
        text=request.input,
        provider=provider_id,
        voice=request.voice,
        speed=request.speed,
        audio_format=request.response_format,
    )

    # Check cache first
    cached_audio = await cache.get(cache_key)
    if cached_audio:
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
            content=cached_audio,
            media_type=media_type,
            headers={
                "X-Processing-Time-Ms": f"{processing_time_ms:.2f}",
                "X-Cache": "HIT",
            },
        )

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
    audio_bytes = buffer.read()

    # Store in cache
    await cache.set(cache_key, audio_bytes)

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
        content=audio_bytes,
        media_type=media_type,
        headers={
            "X-Processing-Time-Ms": f"{processing_time_ms:.2f}",
            "X-Cache": "MISS",
        },
    )


@router.get("/cache/stats")
async def cache_stats(
    cache: Annotated[AudioCache, Depends(get_audio_cache)],
) -> dict:
    """Get cache statistics."""
    return await cache.stats()


@router.delete("/cache")
async def clear_cache(
    cache: Annotated[AudioCache, Depends(get_audio_cache)],
) -> dict:
    """Clear all cached audio data."""
    deleted = await cache.clear_all()
    return {"deleted_keys": deleted}
