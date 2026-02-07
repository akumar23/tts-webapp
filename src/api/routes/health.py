"""Health check endpoints."""

from fastapi import APIRouter

from src.config import get_settings

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check() -> dict:
    """Basic health check endpoint."""
    return {"status": "healthy"}


@router.get("/health/ready")
async def readiness_check() -> dict:
    """Readiness check - verifies service is ready to accept requests."""
    settings = get_settings()
    return {
        "status": "ready",
        "model": settings.tts_model,
        "default_voice": settings.default_voice,
    }


@router.get("/health/live")
async def liveness_check() -> dict:
    """Liveness check - verifies service is running."""
    return {"status": "alive"}
