#!/usr/bin/env python3
"""Checks for the PyAV resampler that replaced scipy.signal.resample
(openspec/changes/02-resample-with-pyav). Run: python test_resample.py
"""
from __future__ import annotations

import sys

import numpy as np

import transcriber


def _peak_hz(samples: np.ndarray, rate: int = 16000) -> float:
    window = samples[rate:2 * rate]  # skip the filter's warm-up
    return float(np.argmax(np.abs(np.fft.rfft(window))) * rate / len(window))


def main() -> None:
    # 1. A 1 kHz tone fed in 1,024-frame blocks through one resampler keeps its
    #    pitch, and the stream's total length matches the rate ratio exactly.
    for rate in (48000, 44100):
        tone = (0.5 * np.sin(2 * np.pi * 1000 * np.arange(3 * rate) / rate)).astype(np.float32)
        resampler = transcriber._new_resampler()
        parts = [transcriber._resample(resampler, tone[i:i + 1024], rate) for i in range(0, len(tone), 1024)]
        parts.append(transcriber._resample(resampler, np.empty(0, np.float32), rate, flush=True))
        out = np.concatenate(parts)
        assert out.dtype == np.float32, out.dtype
        assert len(out) == len(tone) * 16000 // rate, (rate, len(out))
        assert abs(_peak_hz(out) - 1000) <= 1, (rate, _peak_hz(out))

    # 2. A block too short to yield a sample returns an empty array, no error.
    assert len(transcriber._resample(transcriber._new_resampler(), np.zeros(3, np.float32), 48000)) == 0

    # 3. A one-off 10-second chunk, flushed, comes out exactly the right length.
    chunk = np.random.default_rng(0).uniform(-0.5, 0.5, 10 * 44100).astype(np.float32)
    out = transcriber._resample(transcriber._new_resampler(), chunk, 44100, flush=True)
    assert len(out) == 160000, len(out)

    # 4. _process_audio_chunk (the single-source live path) hands the engine
    #    16 kHz float32 audio, however the chunk was captured.
    class Engine:
        received = None

        def transcribe_chunk(self, audio, language=None):
            Engine.received = audio
            return []

    transcriber._process_audio_chunk(Engine(), chunk.astype(np.float64), 0.0, sample_rate=44100)
    assert Engine.received.dtype == np.float32, Engine.received.dtype
    assert len(Engine.received) == round(len(chunk) * 16000 / 44100), len(Engine.received)

    print("test_resample: all checks passed")


if __name__ == "__main__":
    sys.exit(main())
