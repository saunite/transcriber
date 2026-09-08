"""
macOS system-audio loopback capture via a native Core Audio Process Tap
helper (macOS 14.4+). No virtual audio driver required.

The Process Tap / aggregate-device API isn't reachable from pure
Python/PortAudio, so the heavy lifting lives in a small native Swift helper
(macos/audiotap-helper/main.swift), spawned as a subprocess. This module
reads the helper's self-describing header once, then streams raw
interleaved float32 PCM frames from its stdout -- mirroring how
WASAPICapture reads on a background thread so a blocked read never stalls
shutdown.

Native helper builds and runs on real macOS 14.4+ hardware, confirmed
against the actual header format this module parses (see
openspec/changes/add-macos-capture/tasks.md section 5). Not yet verified
against real captured audio content or a permission-denied path -- both
need non-virtualized hardware (tasks.md 5.3-5.6).
"""
import os
import platform
import queue
import struct
import subprocess
import threading
import time
from typing import Callable, Optional

import numpy as np

_MIN_MACOS_VERSION = (14, 4)
_FIRST_CHUNK_TIMEOUT_SECONDS = 5

# Wire format written once by the native helper before any PCM data:
# sample_rate (uint32 LE), channels (uint16 LE), reserved (uint16 LE).
_HEADER_FORMAT = "<IHH"
_HEADER_SIZE = struct.calcsize(_HEADER_FORMAT)

_HELPER_RELATIVE_PATH = os.path.join("macos", "audiotap-helper", "audiotap-helper")

# Exit codes the helper is documented to use (see main.swift HelperExitCode).
_EXIT_CODE_UNSUPPORTED_OS = 10
_EXIT_CODE_PERMISSION_DENIED = 11
_EXIT_CODE_TAP_CREATION_FAILED = 12


class UnsupportedMacOSVersionError(RuntimeError):
    """Raised when the installed macOS version predates the Process Tap API."""


class AudioCapturePermissionError(RuntimeError):
    """Raised when the OS denies the audio-capture permission the tap needs."""


class NoAudioDataError(AudioCapturePermissionError):
    """Raised when the tap creates and starts with no error, but delivers zero
    PCM frames within a reasonable window.

    Confirmed on real hardware: an unauthorized-but-not-yet-denied Process Tap
    does not fail at creation or at AudioDeviceStart -- every call reports
    success, and the IOProc callback simply never fires. macOS only shows the
    one-time authorization prompt for this to a process launched via
    LaunchServices as a proper .app bundle; a bare CLI binary invoked via
    subprocess.Popen (as this module does) never gets prompted at all, no
    matter what a Terminal-level Privacy & Security toggle shows. This is a
    real, silent hang otherwise -- see openspec/changes/add-macos-capture/
    design.md and tasks.md section 5 for how this was diagnosed.
    """


class MacOSCaptureError(RuntimeError):
    """Raised for any other native-helper failure."""


_EXIT_CODE_ERRORS = {
    _EXIT_CODE_UNSUPPORTED_OS: UnsupportedMacOSVersionError,
    _EXIT_CODE_PERMISSION_DENIED: AudioCapturePermissionError,
    _EXIT_CODE_TAP_CREATION_FAILED: MacOSCaptureError,
}


def _macos_version() -> tuple:
    """Parse platform.mac_ver()'s version string into a (major, minor) tuple."""
    version_str = platform.mac_ver()[0]
    parts = version_str.split(".") if version_str else []
    try:
        return tuple(int(p) for p in parts[:2])
    except ValueError:
        return (0, 0)


def _helper_path() -> str:
    """Locate the bundled native helper binary next to this module."""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), _HELPER_RELATIVE_PATH)


def _parse_header(header_bytes: bytes):
    """Decode the helper's fixed-size header. Raises struct.error if short/malformed."""
    sample_rate, channels, _reserved = struct.unpack(_HEADER_FORMAT, header_bytes)
    return sample_rate, channels


def _pcm_bytes_to_mono_float32(data: bytes, channels: int) -> np.ndarray:
    """Convert raw interleaved float32LE PCM bytes to a mono float32 array.

    Pulled out as a pure function (no subprocess/queue involved) so it can
    be unit-tested with synthetic bytes, matching how WASAPICapture's
    int16->float32 conversion is a small inline step rather than something
    hidden behind a live stream.
    """
    frame = np.frombuffer(data, dtype="<f4")
    if channels > 1:
        frame = frame.reshape(-1, channels).mean(axis=1)
    return frame.astype(np.float32)


class MacOSCapture:
    """macOS system-audio loopback capture via the Core Audio Process Tap.

    Mirrors WASAPICapture's interface (get_default_loopback_device,
    capture_stream, cleanup) so transcriber.py's call sites need minimal
    platform branching. There is exactly one capturable "device" (the
    system output tap); device_index is accepted for interface parity with
    WASAPICapture and otherwise unused.
    """

    def __init__(self):
        self._process: Optional[subprocess.Popen] = None
        self.is_capturing = False
        self.sample_rate: Optional[int] = None
        self.channels: Optional[int] = None

    def get_default_loopback_device(self):
        """Return a WASAPICapture-shaped device descriptor for the system tap,
        or None if the running macOS version predates the Process Tap API."""
        if _macos_version() < _MIN_MACOS_VERSION:
            return None
        return {"index": 0, "name": "System Audio (Core Audio Process Tap)"}

    def capture_stream(
        self,
        callback: Callable[[np.ndarray], None],
        device_index: Optional[int] = None,  # unused; kept for interface parity with WASAPICapture
        verbose: bool = False,
    ):
        """
        Capture system audio via the native helper.

        The helper's stdout is read on a background thread so a blocked or
        slow read never stalls shutdown -- the main thread only ever blocks
        on a short-timeout queue read, mirroring WASAPICapture.capture_stream.
        """
        if _macos_version() < _MIN_MACOS_VERSION:
            raise UnsupportedMacOSVersionError(
                f"macOS {_MIN_MACOS_VERSION[0]}.{_MIN_MACOS_VERSION[1]}+ is required for native "
                "system-audio capture. Use a virtual audio driver (BlackHole/Loopback) with "
                "--live --audio-device instead."
            )

        helper_path = _helper_path()
        if not os.path.isfile(helper_path):
            raise MacOSCaptureError(
                f"Native capture helper not found at {helper_path}. Build it with "
                "macos/audiotap-helper/build.sh on a macOS machine."
            )

        if verbose:
            print("🎙️  Capturing system audio via Core Audio Process Tap...")

        self._process = subprocess.Popen(
            [helper_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.is_capturing = True

        header = self._process.stdout.read(_HEADER_SIZE)
        if len(header) < _HEADER_SIZE:
            self._raise_if_failed()
            raise MacOSCaptureError("Native capture helper closed before sending its stream header.")
        self.sample_rate, self.channels = _parse_header(header)
        bytes_per_frame = 4 * self.channels  # float32 per channel

        audio_queue = queue.Queue()

        def _read_loop():
            stdout = self._process.stdout
            while self.is_capturing:
                data = stdout.read(bytes_per_frame * 1024)
                if not data:
                    self.is_capturing = False
                    break
                audio_queue.put(_pcm_bytes_to_mono_float32(data, self.channels))

        reader_thread = threading.Thread(target=_read_loop, daemon=True)
        reader_thread.start()

        first_chunk_deadline = time.monotonic() + _FIRST_CHUNK_TIMEOUT_SECONDS
        received_first_chunk = False
        try:
            if verbose:
                print(f"🎙️  Capturing audio ({self.sample_rate} Hz, {self.channels} ch)... Press Ctrl+C to stop\n")
            while self.is_capturing:
                try:
                    chunk = audio_queue.get(timeout=0.1)
                except queue.Empty:
                    if not received_first_chunk and time.monotonic() > first_chunk_deadline:
                        raise NoAudioDataError(
                            "No audio data received from the system-audio tap after "
                            f"{_FIRST_CHUNK_TIMEOUT_SECONDS}s. The tap likely isn't authorized: "
                            "macOS only shows the one-time permission prompt for this to an app "
                            "launched as a proper .app bundle, not a bare command-line process -- "
                            "check System Settings > Privacy & Security > System Audio Recording "
                            "Only, and note this capture mode may only work once packaged as an app."
                        )
                    continue
                received_first_chunk = True
                callback(chunk)
        except KeyboardInterrupt:
            if verbose:
                print("\n✓ Capture stopped by user")
        finally:
            self.is_capturing = False
            self._stop_helper()
            reader_thread.join(timeout=5)
            self._raise_if_failed()

    def _stop_helper(self):
        if self._process and self._process.poll() is None:
            try:
                self._process.stdin.close()
            except Exception:
                pass
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.terminate()

    def _raise_if_failed(self):
        """Raise a specific exception if the helper process exited with an error.
        A still-running (None) or clean (0) exit is not an error."""
        if self._process is None:
            return
        exit_code = self._process.poll()
        if not exit_code:
            return
        stderr = self._process.stderr.read().decode(errors="replace").strip() if self._process.stderr else ""
        error_cls = _EXIT_CODE_ERRORS.get(exit_code, MacOSCaptureError)
        raise error_cls(stderr or f"native capture helper exited with code {exit_code}")

    def cleanup(self):
        """Ensure the helper process is not left running."""
        self._stop_helper()
