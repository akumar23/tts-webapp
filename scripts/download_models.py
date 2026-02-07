#!/usr/bin/env python3
"""Script to download and cache Kokoro TTS models."""

import sys


def download_kokoro_model():
    """Download Kokoro model and voice tensors."""
    print("Downloading Kokoro TTS model...")

    try:
        from kokoro import KPipeline

        # Initialize pipeline - this downloads the model
        print("Initializing Kokoro pipeline (this may take a few minutes)...")
        pipeline = KPipeline(lang_code="a")

        # Test with a simple phrase to verify
        print("Testing model with sample text...")
        for chunk in pipeline("Hello, model download complete.", voice="af_heart"):
            if chunk.audio is not None:
                print(f"  Generated {len(chunk.audio)} audio samples")

        print("\n✓ Kokoro model downloaded and verified successfully!")
        print("\nAvailable voices:")
        voices = [
            "af_heart",
            "af_bella",
            "af_nicole",
            "af_sarah",
            "af_sky",
            "am_adam",
            "am_michael",
            "bf_emma",
            "bf_isabella",
            "bm_george",
            "bm_lewis",
        ]
        for voice in voices:
            print(f"  - {voice}")

    except ImportError:
        print("Error: Kokoro is not installed.")
        print("\nTo install Kokoro:")
        print("  For GPU (faster): pip install kokoro torch")
        print("  For CPU only:     pip install kokoro onnxruntime")
        sys.exit(1)
    except Exception as e:
        print(f"Error downloading model: {e}")
        sys.exit(1)


if __name__ == "__main__":
    download_kokoro_model()
