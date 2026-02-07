#!/usr/bin/env python3
"""Benchmark script for TTS service performance."""

import argparse
import statistics
import time

import httpx


def benchmark_tts(
    base_url: str,
    text: str,
    voice: str,
    num_requests: int,
    format: str = "mp3",
) -> dict:
    """Run TTS benchmark and return statistics."""
    latencies = []
    audio_durations = []
    errors = 0

    print(f"Benchmarking {num_requests} requests...")
    print(f"  Text length: {len(text)} characters")
    print(f"  Voice: {voice}")
    print(f"  Format: {format}")
    print()

    with httpx.Client(timeout=60.0) as client:
        for i in range(num_requests):
            try:
                start = time.perf_counter()
                response = client.post(
                    f"{base_url}/v1/tts/synthesize",
                    json={
                        "text": text,
                        "voice": voice,
                        "format": format,
                    },
                )
                elapsed = (time.perf_counter() - start) * 1000  # ms

                if response.status_code == 200:
                    latencies.append(elapsed)
                    if "X-Audio-Duration-Seconds" in response.headers:
                        audio_durations.append(
                            float(response.headers["X-Audio-Duration-Seconds"])
                        )
                    print(f"  Request {i + 1}: {elapsed:.2f}ms")
                else:
                    errors += 1
                    print(f"  Request {i + 1}: ERROR ({response.status_code})")

            except Exception as e:
                errors += 1
                print(f"  Request {i + 1}: EXCEPTION ({e})")

    if not latencies:
        return {"error": "All requests failed"}

    results = {
        "total_requests": num_requests,
        "successful_requests": len(latencies),
        "failed_requests": errors,
        "latency_ms": {
            "min": min(latencies),
            "max": max(latencies),
            "mean": statistics.mean(latencies),
            "median": statistics.median(latencies),
            "stdev": statistics.stdev(latencies) if len(latencies) > 1 else 0,
            "p95": sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0,
        },
    }

    if audio_durations:
        avg_duration = statistics.mean(audio_durations)
        avg_latency_s = statistics.mean(latencies) / 1000
        results["audio_duration_seconds"] = avg_duration
        results["real_time_factor"] = avg_latency_s / avg_duration if avg_duration > 0 else 0

    return results


def main():
    parser = argparse.ArgumentParser(description="Benchmark TTS service")
    parser.add_argument(
        "--url",
        default="http://localhost:8000",
        help="Base URL of TTS service",
    )
    parser.add_argument(
        "--text",
        default="Hello, this is a benchmark test of the text-to-speech service. "
        "It generates natural sounding speech from text input.",
        help="Text to synthesize",
    )
    parser.add_argument(
        "--voice",
        default="af_heart",
        help="Voice to use",
    )
    parser.add_argument(
        "--requests",
        type=int,
        default=10,
        help="Number of requests to make",
    )
    parser.add_argument(
        "--format",
        default="mp3",
        choices=["wav", "mp3", "ogg"],
        help="Audio format",
    )

    args = parser.parse_args()

    print("=" * 50)
    print("TTS Service Benchmark")
    print("=" * 50)
    print()

    results = benchmark_tts(
        base_url=args.url,
        text=args.text,
        voice=args.voice,
        num_requests=args.requests,
        format=args.format,
    )

    print()
    print("=" * 50)
    print("Results")
    print("=" * 50)
    print()

    if "error" in results:
        print(f"Error: {results['error']}")
        return

    print(f"Total requests:      {results['total_requests']}")
    print(f"Successful:          {results['successful_requests']}")
    print(f"Failed:              {results['failed_requests']}")
    print()
    print("Latency (ms):")
    print(f"  Min:               {results['latency_ms']['min']:.2f}")
    print(f"  Max:               {results['latency_ms']['max']:.2f}")
    print(f"  Mean:              {results['latency_ms']['mean']:.2f}")
    print(f"  Median:            {results['latency_ms']['median']:.2f}")
    print(f"  Std Dev:           {results['latency_ms']['stdev']:.2f}")
    print(f"  P95:               {results['latency_ms']['p95']:.2f}")

    if "real_time_factor" in results:
        print()
        print(f"Audio duration:      {results['audio_duration_seconds']:.2f}s")
        print(f"Real-time factor:    {results['real_time_factor']:.2f}x")
        if results["real_time_factor"] < 1:
            print("  (faster than real-time)")


if __name__ == "__main__":
    main()
