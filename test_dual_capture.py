#!/usr/bin/env python3
"""Checks for the shared dual-capture runner (openspec/changes/01-merge-dual-capture-paths).

Linux, WASAPI and Core Audio live capture all run through
transcriber._run_dual_capture, so this drives it directly: a fake engine,
a fake sounddevice, and a run_sys that feeds synthetic audio. No audio
hardware or model is needed. Run: python test_dual_capture.py
"""
from __future__ import annotations

import contextlib
import io
import os
import sys
import tempfile
import time
import types

import numpy as np

import transcriber


class _FakeEngine:
    device, compute_type = "cpu", "int8"

    def __init__(self, text="hello"):
        self.text = text
        self.chunk_lengths = []

    def transcribe_chunk(self, audio, language=None):
        self.chunk_lengths.append(len(audio))
        return [{"text": self.text, "start": 0.0, "end": 1.0}] if self.text else []

    def format_timestamp(self, start, end):
        return f"[{start:05.2f} -> {end:05.2f}]"


class _FakeInputStream:
    """Delivers one 5-second block of audible mic audio when started."""

    def __init__(self, device=None, channels=1, samplerate=16000, blocksize=None, callback=None):
        self.callback, self.samplerate = callback, samplerate

    def start(self):
        self.callback(np.full((5 * self.samplerate, 1), 0.5, dtype=np.float32), 0, None, None)

    def stop(self):
        pass

    def close(self):
        pass


def _args(output, **overrides):
    values = dict(output=output, model="base", model_label="base", language=None, silence_timeout=0,
                  chunk_duration=1, actual_time=False, verbose=False, audio_device=-1, include_mic=True)
    values.update(overrides)
    return types.SimpleNamespace(**values)


def _run(engine, args, **kwargs):
    """Run the runner with sounddevice faked; return (exit code, printed output)."""
    fake_sd = types.ModuleType("sounddevice")
    fake_sd.InputStream = _FakeInputStream
    real_sd = sys.modules.get("sounddevice")
    sys.modules["sounddevice"] = fake_sd
    out = io.StringIO()
    try:
        with contextlib.redirect_stdout(out):
            code = transcriber._run_dual_capture(engine, args, **kwargs)
    finally:
        if real_sd is None:
            del sys.modules["sounddevice"]
        else:
            sys.modules["sounddevice"] = real_sd
    return code, out.getvalue()


def _feed(blocks, then=KeyboardInterrupt, gap=0.0):
    """A run_sys that hands blocks to on_chunk, lets the workers catch up, then
    stops. A gap longer than the worker's 50 ms poll makes it take one block
    at a time, so chunk boundaries are deterministic."""
    def run_sys(on_chunk, enqueue, check_silence):
        for block in blocks:
            on_chunk(block)
            time.sleep(gap)
        time.sleep(0.3)
        raise then()
    return run_sys


def main() -> None:
    mic = transcriber.MicConfig(device=3, channels=1, name="Fake Mic", rate=16000)

    with tempfile.TemporaryDirectory() as tmp:
        # 1. System audio at 44.1 kHz reaches the engine as 16 kHz: twelve
        #    4410-frame blocks resample to 19200 samples in total, less at most
        #    the resampler's 16 held samples (a wrongly assumed 48 kHz would give
        #    17640). A 2-frame block, too short to yield a sample, must neither
        #    crash the worker nor stop the run.
        output = os.path.join(tmp, "one.txt")
        engine = _FakeEngine()
        blocks = [np.zeros(4410, np.float32)] * 5 + [np.zeros(2, np.float32)] + [np.zeros(4410, np.float32)] * 7
        resampled = []
        real_resample = transcriber._resample

        def counting_resample(resampler, block, rate, flush=False):
            result = real_resample(resampler, block, rate, flush)
            resampled.append(len(result))
            return result

        transcriber._resample = counting_resample
        try:
            code, out = _run(engine, _args(output), title="Test Loopback + Microphone", mode_summary="Test",
                             sys_rate=lambda: 44100, run_sys=_feed(blocks, gap=0.12), mic=mic)
        finally:
            transcriber._resample = real_resample
        assert code == 0, out
        assert 19200 - 16 <= sum(resampled) <= 19200, (sum(resampled), resampled)
        assert any(n != 5 * 16000 for n in engine.chunk_lengths), engine.chunk_lengths  # system audio was transcribed
        assert "Listening..." in out, out
        written = open(output, encoding="utf-8").read()
        assert written.startswith("# Live Transcription (Test Loopback + Microphone)\n"), written
        assert "[SYS] hello" in written and "[MIC] hello" in written, written
        assert "[SYS] hello" in out and "[MIC] hello" in out, out

        # 2. The silence timeout ends the run through check_silence(), as the
        #    Linux --audio-device poll loop uses it.
        def poll(on_chunk, enqueue, check_silence):
            deadline = time.time() + 5
            while time.time() < deadline:
                check_silence()
                time.sleep(0.05)
            raise AssertionError("check_silence() never stopped the run")

        start = time.time()
        code, out = _run(_FakeEngine(text=""), _args(os.path.join(tmp, "two.txt"), silence_timeout=0.2),
                         title="T", mode_summary="T", sys_rate=lambda: 16000, run_sys=poll, mic=None)
        assert code == 0 and "Auto-stop" in out, out
        assert time.time() - start < 3, "the silence timeout did not stop the run promptly"

        # 3. A listed capture error ends the session with exit code 1 and still
        #    closes the transcript file.
        class CaptureFailed(Exception):
            pass

        opened = []
        real_open = open

        def tracking_open(*a, **k):
            f = real_open(*a, **k)
            opened.append(f)
            return f

        transcriber.open = tracking_open
        try:
            code, out = _run(_FakeEngine(), _args(os.path.join(tmp, "three.txt")), title="T", mode_summary="T",
                             sys_rate=lambda: 16000, run_sys=_feed([], then=CaptureFailed), mic=None,
                             capture_errors=(CaptureFailed,))
        finally:
            del transcriber.open
        assert code == 1 and "❌" in out, out
        assert opened and all(f.closed for f in opened), "the transcript file was left open"

    # 4. The platform functions hand the runner the right pieces. The runner is
    #    replaced by a recorder, so no capture loop runs; the capture classes
    #    are faked because neither Windows nor macOS is available here.
    recorded = {}

    def record(engine, args, **kwargs):
        recorded.clear()
        recorded.update(kwargs)
        return 0

    class FakeWasapi:
        def __init__(self):
            self.sample_rate = None
            self.cleaned = False

        def get_default_loopback_device(self):
            return {"index": 7, "name": "Speakers [Loopback]"}

        def capture_stream(self, callback, device_index=None, verbose=False):
            self.sample_rate = 44100  # a 44.1 kHz output device
            callback(np.zeros(4, np.float32))

        def cleanup(self):
            self.cleaned = True

    class FakeMac(FakeWasapi):
        def get_default_loopback_device(self):
            return {"index": 0, "name": "System audio"}

        def capture_stream(self, callback, device_index=None, verbose=False):
            self.sample_rate = 48000  # from the helper's header

    wasapi_mod = types.ModuleType("wasapi_capture")
    wasapi_mod.WASAPICapture = FakeWasapi
    mac_mod = types.ModuleType("macos_capture")
    mac_mod.MacOSCapture = FakeMac
    for name in ("UnsupportedMacOSVersionError", "AudioCapturePermissionError", "MacOSCaptureError"):
        setattr(mac_mod, name, type(name, (Exception,), {}))

    real_runner = transcriber._run_dual_capture
    saved = {m: sys.modules.get(m) for m in ("wasapi_capture", "macos_capture")}
    sys.modules.update({"wasapi_capture": wasapi_mod, "macos_capture": mac_mod})
    transcriber._run_dual_capture = record
    try:
        args = _args(None, audio_device=-1, include_mic=False)
        assert transcriber.transcribe_live_wasapi(_FakeEngine(), args) == 0
        chunks = []
        recorded["run_sys"](chunks.append, None, None)
        assert chunks, "run_sys did not feed on_chunk"
        assert recorded["sys_rate"]() == 44100, "WASAPI must pass the rate its capture opened"
        assert recorded["title"] == "WASAPI Loopback" and recorded["mic"] is None, recorded
        recorded["cleanup"]()
        assert recorded["cleanup"].__self__.cleaned

        assert transcriber.transcribe_live_coreaudio_tap(_FakeEngine(), args) == 0
        recorded["run_sys"](None, None, None)
        assert recorded["sys_rate"]() == 48000, "Core Audio must pass the rate from the helper's header"
        assert {e.__name__ for e in recorded["capture_errors"]} == {
            "UnsupportedMacOSVersionError", "AudioCapturePermissionError", "MacOSCaptureError"}, recorded
        assert recorded["title"] == "Core Audio Process Tap", recorded
    finally:
        transcriber._run_dual_capture = real_runner
        for m, mod in saved.items():
            if mod is None:
                sys.modules.pop(m, None)
            else:
                sys.modules[m] = mod

    print("test_dual_capture: all checks passed")


if __name__ == "__main__":
    sys.exit(main())
