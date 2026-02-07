# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common Commands

```bash
# Development server with hot reload
uvicorn src.main:app --reload

# Production server
uvicorn src.main:app --host 0.0.0.0 --port 8000

# Run tests
pytest
pytest --cov=src              # with coverage
pytest tests/test_tts.py -v   # single test file

# Code quality
ruff format .                 # format code
ruff check .                  # lint code
mypy src                      # type check

# Docker
docker-compose up --build     # CPU deployment
```

## Architecture

This is a multi-provider Text-to-Speech API built with FastAPI. The core abstraction is the **Provider Pattern**:

### Provider System (`src/core/`)
- `providers/base.py` - Abstract `TTSProvider` class defining the interface all providers must implement
- `providers/edge.py` - Microsoft Edge TTS (free, no API key)
- `providers/openai.py` - OpenAI TTS (requires API key)
- `providers/elevenlabs.py` - ElevenLabs TTS (requires API key)
- `provider_manager.py` - Singleton that orchestrates providers, routes synthesis requests
- `tts_engine.py` - Legacy Edge TTS engine (kept for backward compatibility)

To add a new provider: implement `TTSProvider` abstract class and register it in `ProviderManager.__init__()`.

### API Layer (`src/api/`)
- `routes/tts.py` - TTS endpoints: `/v1/tts/synthesize`, `/v1/tts/stream`, `/v1/tts/audio/speech` (OpenAI-compatible)
- `routes/health.py` - Health check endpoints
- `schemas/` - Pydantic models for request/response validation

### Configuration
- `src/config.py` - Pydantic Settings loading from environment variables
- Settings are cached via `@lru_cache` on `get_settings()`
- Copy `.env.example` to `.env` for local configuration

### Key Design Decisions
- Providers return `np.ndarray` audio data; format conversion happens at the API layer using `soundfile`
- Streaming uses async generators yielding bytes
- Edge TTS is the default provider (free, no authentication required)
- The OpenAI-compatible endpoint (`/v1/tts/audio/speech`) auto-selects provider based on API key presence

## Dependencies
- Python 3.10+
- `edge-tts` for Microsoft neural TTS
- `soundfile` + `numpy` for audio processing
- `prometheus-fastapi-instrumentator` for metrics at `/metrics`
- `structlog` for structured logging
