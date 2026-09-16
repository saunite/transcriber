"""
Self-check for the Ctrl+C-hang fix in wasapi_capture.py.

Simulates a WASAPI loopback stream whose read() stalls indefinitely (the
failure mode reported after long recording sessions) and asserts that
capture_stream() still returns promptly once shutdown is requested, instead
of blocking forever on the stalled read.

Run: python test_wasapi_capture.py
"""
import sys
import threading
import time
import types
from unittest import mock

import numpy as np


class _FakeStream:
    """Mimics a pyaudiowpatch stream whose read() blocks until stop_stream()
    is called from another thread -- mirrors the real stall scenario where
    the WASAPI shared-mode engine stops delivering data."""

    def __init__(self, chunk_bytes):
        self._chunk_bytes = chunk_bytes
        self._stopped = threading.Event()
        self.reads_before_stall = 3

    def read(self, chunk_size, exception_on_overflow=False):
        if self.reads_before_stall > 0:
            self.reads_before_stall -= 1
            return self._chunk_bytes
        # Simulate a stalled read: blocks until the stream is closed.
        self._stopped.wait()
        raise IOError("Stream closed")

    def stop_stream(self):
        self._stopped.set()

    def close(self):
        self._stopped.set()


def _make_fake_pyaudio_module(fake_stream, rate=16000):
    fake_pyaudio = types.SimpleNamespace()
    fake_pyaudio.paInt16 = 8
    fake_pyaudio.paInputOverflowed = -9981

    class FakePyAudio:
        def open(self, **kwargs):
            return fake_stream

        def get_default_output_device_info(self):
            return {"name": "Speakers"}

        def get_loopback_device_info_generator(self):
            yield {
                "name": "Speakers [Loopback]",
                "index": 0,
                "maxInputChannels": 1,
                "defaultSampleRate": rate,
            }

        def get_device_info_by_index(self, index):
            return {
                "name": "Speakers [Loopback]",
                "index": index,
                "maxInputChannels": 1,
                "defaultSampleRate": rate,
            }

        def terminate(self):
            pass

    fake_pyaudio.PyAudio = FakePyAudio
    return fake_pyaudio


def test_capture_stream_exits_promptly_when_read_stalls():
    chunk = np.zeros(1024, dtype=np.int16).tobytes()
    fake_stream = _FakeStream(chunk)
    fake_pyaudio_module = _make_fake_pyaudio_module(fake_stream)

    with mock.patch.dict(sys.modules, {"pyaudiowpatch": fake_pyaudio_module}):
        # Import after the fake module is installed so `import pyaudiowpatch
        # as pyaudio` inside wasapi_capture resolves to the fake.
        sys.modules.pop("wasapi_capture", None)
        import wasapi_capture

        capture = wasapi_capture.WASAPICapture()
        chunks_received = []

        def callback(audio_chunk):
            chunks_received.append(audio_chunk)
            # Once we've seen the first few chunks (before the stall),
            # request shutdown -- like a user pressing Ctrl+C -- while the
            # background reader is about to (or already has) stalled.
            if len(chunks_received) == 2:
                capture.is_capturing = False

        start = time.monotonic()
        capture.capture_stream(callback=callback, device_index=0)
        elapsed = time.monotonic() - start

        assert elapsed < 2.0, (
            f"capture_stream() took {elapsed:.1f}s to return after shutdown "
            "was requested against a stalled read -- Ctrl+C would hang"
        )
        assert len(chunks_received) >= 2

    print(f"OK: capture_stream() returned in {elapsed:.3f}s despite a stalled read")


def test_sample_rate_is_the_device_rate():
    """transcriber.py used to assume every WASAPI loopback ran at 48 kHz, so a
    44.1 kHz output device reached Whisper ~9% slow
    (openspec/changes/01-merge-dual-capture-paths)."""
    fake_stream = _FakeStream(np.zeros(1024, dtype=np.int16).tobytes())
    with mock.patch.dict(sys.modules, {"pyaudiowpatch": _make_fake_pyaudio_module(fake_stream, rate=44100)}):
        sys.modules.pop("wasapi_capture", None)
        import wasapi_capture

        capture = wasapi_capture.WASAPICapture()
        assert capture.sample_rate is None
        seen = []

        def callback(audio_chunk):
            seen.append(capture.sample_rate)
            capture.is_capturing = False

        capture.capture_stream(callback=callback, device_index=0)
        assert seen and seen[0] == 44100, seen

    print("OK: sample_rate reports the device's 44100 Hz while streaming")


def _loopback_pick(wasapi_default, loopback_names):
    """get_default_loopback_device() against a fake whose MME default is the
    truncated "Headphones" and whose WASAPI default is `wasapi_default`."""
    fake_pyaudio = _make_fake_pyaudio_module(None)

    class FakePyAudio(fake_pyaudio.PyAudio):
        def get_default_output_device_info(self):
            return {"name": "Headphones"}

        def get_default_wasapi_device(self, d_out=False):
            assert d_out, "the reference must be the default *output*"
            return {"name": wasapi_default}

        def get_loopback_device_info_generator(self):
            for i, name in enumerate(loopback_names):
                yield {"name": name, "index": i}

    fake_pyaudio.PyAudio = FakePyAudio
    with mock.patch.dict(sys.modules, {"pyaudiowpatch": fake_pyaudio}):
        sys.modules.pop("wasapi_capture", None)
        import wasapi_capture
        return wasapi_capture.WASAPICapture().get_default_loopback_device()


def test_default_output_own_loopback_among_similar_names():
    """A substring match on the MME name picked "Headphones (2- Bluetooth)"
    when "Headphones" was the default (openspec/changes/03-fix-audit-edges-windows)."""
    device = _loopback_pick(
        "Headphones",
        ["Headphones (2- Bluetooth) [Loopback]", "Headphones [Loopback]"],
    )
    assert device["name"] == "Headphones [Loopback]", device
    print("OK: the default output's own loopback wins over a similarly named one")


def test_no_exact_match_falls_back_to_first_loopback():
    device = _loopback_pick("Speakers", ["Monitor A [Loopback]", "Monitor B [Loopback]"])
    assert device["name"] == "Monitor A [Loopback]", device
    print("OK: no exact match falls back to the first loopback")


if __name__ == "__main__":
    test_capture_stream_exits_promptly_when_read_stalls()
    test_sample_rate_is_the_device_rate()
    test_default_output_own_loopback_among_similar_names()
    test_no_exact_match_falls_back_to_first_loopback()
