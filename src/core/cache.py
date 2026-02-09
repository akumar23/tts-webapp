"""Audio caching layer using Redis."""

import hashlib
from typing import Optional

import redis.asyncio as redis
import structlog

from src.config import get_settings

logger = structlog.get_logger(__name__)


class AudioCache:
    """Redis-based cache for synthesized audio."""

    def __init__(self) -> None:
        self._client: Optional[redis.Redis] = None
        self._connected: bool = False
        self._settings = get_settings()

    async def connect(self) -> bool:
        """Initialize Redis connection."""
        if not self._settings.cache_enabled:
            logger.info("Cache disabled via configuration")
            return False

        try:
            self._client = redis.from_url(
                self._settings.redis_url,
                encoding="utf-8",
                decode_responses=False,
            )
            await self._client.ping()
            self._connected = True
            logger.info("Redis cache connected", url=self._settings.redis_url)
            return True
        except Exception as e:
            logger.warning("Redis connection failed, caching disabled", error=str(e))
            self._connected = False
            self._client = None
            return False

    async def disconnect(self) -> None:
        """Close Redis connection."""
        if self._client:
            await self._client.close()
            self._connected = False
            logger.info("Redis cache disconnected")

    @property
    def is_connected(self) -> bool:
        """Check if cache is available."""
        return self._connected and self._client is not None

    @staticmethod
    def generate_key(
        text: str,
        provider: str,
        voice: str,
        speed: float,
        audio_format: str,
    ) -> str:
        """Generate a cache key from synthesis parameters."""
        key_data = f"{text}:{provider}:{voice}:{speed}:{audio_format}"
        key_hash = hashlib.sha256(key_data.encode()).hexdigest()
        return f"tts:audio:{key_hash}"

    async def get(self, key: str) -> Optional[bytes]:
        """Retrieve cached audio data."""
        if not self.is_connected:
            return None

        try:
            data = await self._client.get(key)
            if data:
                logger.debug("Cache hit", key=key[:32])
            return data
        except Exception as e:
            logger.warning("Cache get failed", key=key[:32], error=str(e))
            return None

    async def set(self, key: str, data: bytes, ttl: Optional[int] = None) -> bool:
        """Store audio data in cache."""
        if not self.is_connected:
            return False

        try:
            cache_ttl = ttl or self._settings.cache_ttl
            await self._client.set(key, data, ex=cache_ttl)
            logger.debug("Cache set", key=key[:32], ttl=cache_ttl, size_bytes=len(data))
            return True
        except Exception as e:
            logger.warning("Cache set failed", key=key[:32], error=str(e))
            return False

    async def delete(self, key: str) -> bool:
        """Remove cached audio data."""
        if not self.is_connected:
            return False

        try:
            await self._client.delete(key)
            return True
        except Exception as e:
            logger.warning("Cache delete failed", key=key[:32], error=str(e))
            return False

    async def clear_all(self) -> int:
        """Clear all TTS cache entries. Returns count of deleted keys."""
        if not self.is_connected:
            return 0

        try:
            keys = await self._client.keys("tts:audio:*")
            if keys:
                count = await self._client.delete(*keys)
                logger.info("Cache cleared", deleted_keys=count)
                return count
            return 0
        except Exception as e:
            logger.warning("Cache clear failed", error=str(e))
            return 0

    async def stats(self) -> dict:
        """Get cache statistics."""
        if not self.is_connected:
            return {"connected": False}

        try:
            info = await self._client.info("memory")
            keys = await self._client.keys("tts:audio:*")
            return {
                "connected": True,
                "cached_items": len(keys),
                "memory_used": info.get("used_memory_human", "unknown"),
            }
        except Exception as e:
            logger.warning("Cache stats failed", error=str(e))
            return {"connected": False, "error": str(e)}


# Singleton instance
_cache: Optional[AudioCache] = None


def get_audio_cache() -> AudioCache:
    """Get or create the audio cache singleton."""
    global _cache
    if _cache is None:
        _cache = AudioCache()
    return _cache
