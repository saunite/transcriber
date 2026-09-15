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
import threading
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
                  chunk_duration=1, actual_time=False, verbose=False, audio_device=-1, include_mic=True,
                  heartbeat=False)
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
    at a time, so chunk boundaries are deterministic. then=None returns
    normally, as a capture does when its audio source ends on its own."""
    def run_sys(on_chunk, enqueue, check_silence):
        for block in blocks:
            on_chunk(block)
            time.sleep(gap)
        time.sleep(0.3)
        if then is not None:
            raise then()
    return run_sys


class _SegmentsEngine(_FakeEngine):
    """Returns the same segments, at the given starts, for every chunk."""

    def __init__(self, *starts):
        super().__init__()
        self.starts = starts

    def transcribe_chunk(self, audio, language=None):
        self.chunk_lengths.append(len(audio))
        return [{"text": f"at {s}", "start": s, "end": s + 0.2} for s in self.starts]


class _PacedMicStream(_FakeInputStream):
    """Delivers a silent 5-second mic block, then an audible one, apart."""

    def start(self):
        def feed():
            for level in (0.0, 0.5):
                self.callback(np.full((5 * self.samplerate, 1), level, dtype=np.float32), 0, None, None)
                time.sleep(0.3)
        threading.Thread(target=feed, daemon=True).start()


def _lines(out, tag):
    return [line for line in out.splitlines() if f"[{tag}]" in line]


def _check_time_axis(mic):
    """Stamps are positions in the audio stream (openspec/changes/fix-true-scale-time-axis)."""
    one_second = [np.zeros(16000, np.float32)] * 4  # 2 s chunks, so starts at 0, 1 and 2 s

    # Position: the carried 1 s overlap is not counted twice.
    code, out = _run(_SegmentsEngine(0.6), _args(None, chunk_duration=2, include_mic=False), title="T",
                     mode_summary="T", sys_rate=lambda: 16000, run_sys=_feed(one_second, gap=0.12), mic=None)
    assert code == 0, out
    stamps = [line.split("]")[0] + "]" for line in _lines(out, "SYS")]
    assert stamps == ["[00.60 -> 00.80]", "[01.60 -> 01.80]", "[02.60 -> 02.80]"], stamps

    # Skipped chunk: a silent mic chunk still takes its time.
    def idle(on_chunk, enqueue, check_silence):
        time.sleep(1.5)
        raise KeyboardInterrupt

    global _FakeInputStream
    real_stream, _FakeInputStream = _FakeInputStream, _PacedMicStream
    try:
        code, out = _run(_SegmentsEngine(1.2), _args(None), title="T", mode_summary="T",
                         sys_rate=lambda: 16000, run_sys=idle, mic=mic)
    finally:
        _FakeInputStream = real_stream
    assert code == 0, out
    stamps = [line.split("]")[0] + "]" for line in _lines(out, "MIC")]
    assert stamps == ["[05.20 -> 05.40]"], stamps

    # Speech time: stream start plus position, whatever the clock reads when a
    # line is printed. The clock is frozen at noon for the whole run, so the
    # first 1 s block started at 11:59:59.
    class Noon(transcriber.datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 9, 15, 12, 0, 0)

    real_datetime, transcriber.datetime = transcriber.datetime, Noon
    try:
        code, out = _run(_SegmentsEngine(0.1, 1.4), _args(None, chunk_duration=2, include_mic=False,
                                                          actual_time=True),
                         title="T", mode_summary="T", sys_rate=lambda: 16000,
                         run_sys=_feed(one_second[:3], gap=0.12), mic=None)
    finally:
        transcriber.datetime = real_datetime
    assert code == 0, out
    stamps = [line.split("]")[0] + "]" for line in _lines(out, "SYS")]
    # Chunk 1 (0-2 s) keeps both segments; chunk 2 (1-3 s) drops 0.1, which
    # lies in the overlap chunk 1 already covered.
    assert stamps == ["[2026-09-15 11:59:59]", "[2026-09-15 12:00:00]", "[2026-09-15 12:00:01]"], stamps
    print("OK: time axis -- positions, skipped chunks, speech-time stamps")


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

    # 3b. A system source that ends on its own -- run_sys returns with no stop
    #     requested -- is a lost source: exit 1, a message, and the transcript
    #     keeps what was written (openspec/changes/fix-engine-liveness).
    with tempfile.TemporaryDirectory() as tmp:
        lost = os.path.join(tmp, "lost.txt")
        code, out = _run(_FakeEngine(), _args(lost), title="T", mode_summary="T", sys_rate=lambda: 16000,
                         run_sys=_feed([np.zeros(16000, np.float32)] * 2, then=None, gap=0.12), mic=None)
        assert code == 1 and out.rstrip().splitlines()[-1] == transcriber.LOST_SOURCE_MESSAGE, out
        assert "[SYS] hello" in open(lost, encoding="utf-8").read(), "the transcript lost its lines"

        # 3b'. After the audio server restarts, the mic stream's stop() never
        #      returns; the lost source must still end the run, promptly, with
        #      the lost-source line last (openspec/changes/fix-engine-liveness).
        class _HangingStream(_FakeInputStream):
            def stop(self):
                threading.Event().wait()

        real_stream = _FakeInputStream
        globals()["_FakeInputStream"] = _HangingStream
        try:
            start = time.time()
            code, out = _run(_FakeEngine(), _args(os.path.join(tmp, "hang.txt")), title="T", mode_summary="T",
                             sys_rate=lambda: 16000, mic=mic,
                             run_sys=_feed([np.zeros(16000, np.float32)], then=None, gap=0.12))
        finally:
            globals()["_FakeInputStream"] = real_stream
        assert code == 1 and out.rstrip().splitlines()[-1] == transcriber.LOST_SOURCE_MESSAGE, out
        assert time.time() - start < 15, f"shutdown hung for {time.time() - start:.0f}s on a stuck mic stream"

        # 3b''. The app went away: stdout is a broken pipe. A worker's print must
        #       stop the whole session, not just kill its thread and leave the
        #       capture loop recording, orphaned (openspec/changes/fix-sidecar-temp-leak).
        class _GoneReader(io.StringIO):
            def write(self, text):
                if "HEARTBEAT" in text:
                    raise BrokenPipeError(32, "Broken pipe")
                return super().write(text)

        def capture_until_interrupted(on_chunk, enqueue, check_silence):
            try:  # like every real capture_stream: a stop returns normally
                deadline = time.time() + 20
                while time.time() < deadline:
                    on_chunk(np.zeros(1600, np.float32))
                    time.sleep(0.01)
            except KeyboardInterrupt:
                return

        start = time.time()
        gone = os.path.join(tmp, "gone.txt")
        # The engine's real SIGINT handler, which ignores repeats once a stop
        # is under way: the broken-pipe stop must still get through it.
        import signal
        previous = signal.signal(signal.SIGINT, transcriber._make_signal_handler(verbose=False))
        try:
            with contextlib.redirect_stdout(_GoneReader()):
                code = transcriber._run_dual_capture(
                    _FakeEngine(), _args(gone, heartbeat=True), title="T", mode_summary="T",
                    sys_rate=lambda: 16000, run_sys=capture_until_interrupted, mic=None)
        finally:
            signal.signal(signal.SIGINT, previous)
        assert time.time() - start < 10, f"the session kept running {time.time() - start:.0f}s with nobody reading stdout"
        assert code == 0, f"a vanished reader is a stop, not a lost source: exit {code}"
        assert "[SYS] hello" in open(gone, encoding="utf-8").read(), "the transcript lost its lines"

        # 3c. Every real capture_stream swallows KeyboardInterrupt and returns
        #     normally, so a silence stop raised inside it must still exit 0
        #     and not be reported as a lost source.
        def swallowing(on_chunk, enqueue, check_silence):
            try:
                deadline = time.time() + 5
                while time.time() < deadline:
                    on_chunk(np.zeros(160, np.float32))
                    time.sleep(0.05)
            except KeyboardInterrupt:
                return

        code, out = _run(_FakeEngine(text=""), _args(os.path.join(tmp, "quiet.txt"), silence_timeout=0.2),
                         title="T", mode_summary="T", sys_rate=lambda: 16000, run_sys=swallowing, mic=None)
        assert code == 0 and "Auto-stop" in out and "ended unexpectedly" not in out, out

    # 3d. --heartbeat: a silent engine still reports every chunk it processed,
    #     for both sources, and nothing is printed without the flag. The MIC
    #     block is audible (gate passes) and the SYS one silent.
    with tempfile.TemporaryDirectory() as tmp:
        for heartbeat in (True, False):
            code, out = _run(_FakeEngine(text=""), _args(os.path.join(tmp, f"hb{heartbeat}.txt"), heartbeat=heartbeat),
                             title="T", mode_summary="T", sys_rate=lambda: 16000,
                             run_sys=_feed([np.zeros(16000, np.float32)] * 2, gap=0.12), mic=mic)
            beats = {line for line in out.splitlines() if line.startswith("HEARTBEAT")}
            if heartbeat:
                assert beats == {"HEARTBEAT SYS", "HEARTBEAT MIC"}, out
            else:
                assert not beats, out
    help_text = io.StringIO()
    with contextlib.redirect_stdout(help_text), contextlib.suppress(SystemExit):
        sys.argv = ["transcriber.py", "--help"]
        transcriber.main()
    assert "--heartbeat" not in help_text.getvalue(), "--heartbeat must stay hidden from --help"

    # 3e. A repeat SIGINT while a stop is under way is ignored: the app's stop
    #     plus the PyInstaller launcher's forwarded copy reach the engine
    #     twice, and the second one used to wreck the cleanup
    #     (openspec/changes/fix-sidecar-temp-leak).
    handler = transcriber._make_signal_handler(verbose=False)
    transcriber._stop_requested = False
    try:
        handler(2, None)
        raise AssertionError("the first SIGINT must stop the session")
    except KeyboardInterrupt:
        pass
    handler(2, None)  # must return, not raise, now that a stop is under way
    transcriber._stop_requested = False

    _check_time_axis(mic)

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
