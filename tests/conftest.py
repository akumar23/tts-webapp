"""Pytest configuration and fixtures."""

import pytest
from fastapi.testclient import TestClient

from src.main import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def sample_text():
    """Sample text for TTS testing."""
    return "Hello, this is a test of the text-to-speech service."
