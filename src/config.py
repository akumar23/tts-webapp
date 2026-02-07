"""Application configuration using Pydantic settings."""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    app_name: str = "TTS Service"
    debug: bool = False

    # TTS Configuration
    tts_model: str = "edge-tts"
    model_path: str = "./models"
    default_voice: str = "en-US-JennyNeural"

    # Audio Settings
    sample_rate: int = 24000
    default_format: Literal["wav", "mp3", "ogg"] = "mp3"

    # Performance
    max_text_length: int = 5000
    cache_enabled: bool = True
    cache_ttl: int = 3600

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
