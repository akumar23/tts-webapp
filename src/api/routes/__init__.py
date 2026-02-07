"""API routes."""

from src.api.routes.health import router as health_router
from src.api.routes.tts import router as tts_router

__all__ = ["health_router", "tts_router"]
