"""Tests for TTS endpoints."""

import pytest


def test_list_voices(client):
    """Test listing available voices."""
    response = client.get("/v1/tts/voices")
    assert response.status_code == 200
    voices = response.json()
    assert isinstance(voices, list)
    assert len(voices) > 0
    # Check voice structure
    voice = voices[0]
    assert "id" in voice
    assert "name" in voice
    assert "language" in voice


def test_get_voice(client):
    """Test getting a specific voice."""
    response = client.get("/v1/tts/voices/af_heart")
    assert response.status_code == 200
    voice = response.json()
    assert voice["id"] == "af_heart"
    assert voice["language"] == "en-US"


def test_get_voice_not_found(client):
    """Test getting a non-existent voice."""
    response = client.get("/v1/tts/voices/nonexistent")
    assert response.status_code == 404


@pytest.mark.skip(reason="Requires Kokoro model to be installed")
def test_synthesize_basic(client, sample_text):
    """Test basic speech synthesis."""
    response = client.post(
        "/v1/tts/synthesize",
        json={
            "text": sample_text,
            "voice": "af_heart",
            "format": "wav",
        },
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/wav"
    assert len(response.content) > 0


@pytest.mark.skip(reason="Requires Kokoro model to be installed")
def test_synthesize_mp3(client, sample_text):
    """Test MP3 synthesis."""
    response = client.post(
        "/v1/tts/synthesize",
        json={
            "text": sample_text,
            "voice": "af_heart",
            "format": "mp3",
        },
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/mpeg"


def test_synthesize_invalid_voice(client, sample_text):
    """Test synthesis with invalid voice returns error."""
    response = client.post(
        "/v1/tts/synthesize",
        json={
            "text": sample_text,
            "voice": "invalid_voice",
        },
    )
    # Should fail with 400 bad request
    assert response.status_code in [400, 500]


def test_synthesize_empty_text(client):
    """Test synthesis with empty text returns error."""
    response = client.post(
        "/v1/tts/synthesize",
        json={
            "text": "",
            "voice": "af_heart",
        },
    )
    assert response.status_code == 422  # Validation error


def test_synthesize_text_too_long(client):
    """Test synthesis with text exceeding max length."""
    long_text = "x" * 6000  # Exceeds 5000 char limit
    response = client.post(
        "/v1/tts/synthesize",
        json={
            "text": long_text,
            "voice": "af_heart",
        },
    )
    assert response.status_code == 422  # Validation error


@pytest.mark.skip(reason="Requires Kokoro model to be installed")
def test_openai_compatible_endpoint(client, sample_text):
    """Test OpenAI-compatible endpoint."""
    response = client.post(
        "/v1/tts/audio/speech",
        json={
            "input": sample_text,
            "voice": "af_heart",
            "response_format": "mp3",
        },
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/mpeg"
