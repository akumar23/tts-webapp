# TTS Service

Production-ready Text-to-Speech API using [Edge TTS](https://github.com/rany2/edge-tts) - Microsoft's free neural TTS service with high-quality voices.

## Features

- **High-quality neural voices** - 400+ voices across 100+ languages
- **No API key required** - Free to use
- **Multiple formats** - WAV, MP3, OGG output
- **Streaming support** - Real-time audio streaming
- **OpenAI compatible** - Drop-in replacement for OpenAI TTS API
- **Web UI included** - Built-in frontend for easy testing
- **Production ready** - Docker support, health checks, metrics

## Quick Start

### 1. Install dependencies

```bash
cd tts-service

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Run the server

```bash
# Development
uvicorn src.main:app --reload

# Production
uvicorn src.main:app --host 0.0.0.0 --port 8000
```

### 3. Open the Web UI

Visit http://localhost:8000 in your browser to use the built-in TTS interface.

### 4. Or use the API

```bash
# Synthesize speech
curl -X POST http://localhost:8000/v1/tts/synthesize \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello, welcome to the text-to-speech service!", "voice": "en-US-JennyNeural"}' \
  --output speech.mp3

# List available voices
curl http://localhost:8000/v1/tts/voices
```

## API Endpoints

### Synthesize Speech

```
POST /v1/tts/synthesize
```

Request body:
```json
{
  "text": "Text to synthesize",
  "voice": "en-US-JennyNeural",
  "speed": 1.0,
  "format": "mp3"
}
```

### Stream Speech

```
POST /v1/tts/stream
```

Returns chunked audio for real-time playback.

### OpenAI Compatible

```
POST /v1/tts/audio/speech
```

Compatible with OpenAI's TTS API format:
```json
{
  "input": "Text to synthesize",
  "voice": "en-US-JennyNeural",
  "response_format": "mp3",
  "speed": 1.0
}
```

### List Voices

```
GET /v1/tts/voices
```

## Available Voices

| Voice ID | Name | Language | Gender |
|----------|------|----------|--------|
| en-US-JennyNeural | Jenny | en-US | Female |
| en-US-AriaNeural | Aria | en-US | Female |
| en-US-SaraNeural | Sara | en-US | Female |
| en-US-GuyNeural | Guy | en-US | Male |
| en-US-ChristopherNeural | Christopher | en-US | Male |
| en-GB-SoniaNeural | Sonia | en-GB | Female |
| en-GB-RyanNeural | Ryan | en-GB | Male |
| en-AU-NatashaNeural | Natasha | en-AU | Female |
| en-AU-WilliamNeural | William | en-AU | Male |
| en-IN-NeerjaNeural | Neerja | en-IN | Female |
| en-IN-PrabhatNeural | Prabhat | en-IN | Male |

For more voices, Edge TTS supports 400+ voices. See the full list with:
```bash
edge-tts --list-voices
```

## Docker Deployment

```bash
# Build and run
docker-compose up --build

# Or build manually
docker build -t tts-service .
docker run -p 8000:8000 tts-service
```

## Configuration

Environment variables (or `.env` file):

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_NAME` | TTS Service | Application name |
| `DEBUG` | false | Enable debug mode |
| `TTS_MODEL` | edge-tts | TTS engine |
| `DEFAULT_VOICE` | en-US-JennyNeural | Default voice ID |
| `SAMPLE_RATE` | 24000 | Audio sample rate |
| `DEFAULT_FORMAT` | mp3 | Default audio format |
| `MAX_TEXT_LENGTH` | 5000 | Maximum text length |
| `HOST` | 0.0.0.0 | Server host |
| `PORT` | 8000 | Server port |

## Development

### Run tests

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run with coverage
pytest --cov=src
```

### Code quality

```bash
# Format code
ruff format .

# Lint code
ruff check .

# Type check
mypy src
```

## Project Structure

```
tts-service/
├── src/
│   ├── api/
│   │   ├── routes/       # API endpoints
│   │   └── schemas/      # Request/Response models
│   ├── core/
│   │   └── tts_engine.py # Edge TTS wrapper
│   ├── static/
│   │   └── index.html    # Web UI
│   ├── utils/
│   │   └── logging.py    # Structured logging
│   ├── config.py         # Application settings
│   └── main.py           # FastAPI application
├── tests/                # Test suite
├── Dockerfile            # Docker build
├── docker-compose.yml    # Docker Compose config
└── requirements.txt      # Python dependencies
```

## Monitoring

- Health check: `GET /health`
- Readiness: `GET /health/ready`
- Liveness: `GET /health/live`
- Prometheus metrics: `GET /metrics`

## License

This project is MIT licensed. Edge TTS uses Microsoft's Edge browser TTS service.

## Acknowledgments

- [Edge TTS](https://github.com/rany2/edge-tts) - Python module for Edge's TTS
- [FastAPI](https://fastapi.tiangolo.com/) - Web framework
- [soundfile](https://pysoundfile.readthedocs.io/) - Audio I/O
