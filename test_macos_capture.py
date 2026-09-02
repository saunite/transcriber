"""
Self-check for macOS Core Audio Process Tap support: PCM/header parsing in
macos_capture.py and the CLI's platform-mismatch flag validation.

These exercise only pure Python logic against synthetic data -- no macOS
hardware, native helper binary, or real subprocess involved (see
openspec/changes/add-macos-capture/tasks.md section 5 for the
hardware-dependent verification this does NOT cover).

Run: python test_macos_capture.py
"""
import platform
import struct
import types
from unittest import mock

import numpy as np

import macos_capture


def test_parse_header_roundtrip():
    packed = struct.pack(macos_capture._HEADER_FORMAT, 48000, 2, 0)
    sample_rate, channels = macos_capture._parse_header(packed)
    assert sample_rate == 48000
    assert channels == 2
    print("OK: header parses to (sample_rate=48000, channels=2)")


def test_pcm_bytes_to_mono_float32_mono_input():
    samples = np.array([0.5, -0.5, 1.0, -1.0], dtype="<f4")
    result = macos_capture._pcm_bytes_to_mono_float32(samples.tobytes(), channels=1)
    assert result.dtype == np.float32
    np.testing.assert_allclose(result, samples)
    print("OK: mono PCM bytes decode unchanged")


def test_pcm_bytes_to_mono_float32_stereo_input_averages_channels():
    # Interleaved stereo: (L, R) pairs -- averaging should collapse to mono.
    interleaved = np.array([1.0, -1.0, 0.5, 0.5], dtype="<f4")  # frame1: L=1,R=-1 ; frame2: L=0.5,R=0.5
    result = macos_capture._pcm_bytes_to_mono_float32(interleaved.tobytes(), channels=2)
    np.testing.assert_allclose(result, np.array([0.0, 0.5], dtype=np.float32))
    print("OK: stereo PCM bytes average to mono")


def test_macos_version_below_minimum_blocks_capture():
    capture = macos_capture.MacOSCapture()
    with mock.patch.object(platform, "mac_ver", return_value=("13.6.0", ("", "", ""), "")):
        assert capture.get_default_loopback_device() is None
        try:
            capture.capture_stream(callback=lambda chunk: None)
            assert False, "expected UnsupportedMacOSVersionError"
        except macos_capture.UnsupportedMacOSVersionError:
            pass
    print("OK: macOS < 14.4 is rejected before spawning the native helper")


def test_macos_version_at_minimum_is_accepted_by_version_gate():
    with mock.patch.object(platform, "mac_ver", return_value=("14.4.0", ("", "", ""), "")):
        capture = macos_capture.MacOSCapture()
        device = capture.get_default_loopback_device()
        assert device == {"index": 0, "name": "System Audio (Core Audio Process Tap)"}
    print("OK: macOS 14.4 passes the version gate")


def test_missing_helper_binary_raises_clear_error():
    with mock.patch.object(platform, "mac_ver", return_value=("14.4.0", ("", "", ""), "")):
        with mock.patch.object(macos_capture, "_helper_path", return_value="/nonexistent/audiotap-helper"):
            capture = macos_capture.MacOSCapture()
            try:
                capture.capture_stream(callback=lambda chunk: None)
                assert False, "expected MacOSCaptureError"
            except macos_capture.MacOSCaptureError as e:
                assert "Build it with" in str(e)
    print("OK: a missing native helper binary raises a clear, actionable error")


def test_validate_live_capture_platform_flag_mismatch():
    import transcriber

    args = types.SimpleNamespace(wasapi=True, coreaudio_tap=False)
    with mock.patch.object(platform, "system", return_value="Darwin"):
        error = transcriber._validate_live_capture_platform(args)
        assert error is not None and "--wasapi" in error
    print("OK: --wasapi on macOS is rejected with a clear error")

    args = types.SimpleNamespace(wasapi=False, coreaudio_tap=True)
    with mock.patch.object(platform, "system", return_value="Windows"):
        error = transcriber._validate_live_capture_platform(args)
        assert error is not None and "--coreaudio-tap" in error
    print("OK: --coreaudio-tap on Windows is rejected with a clear error")

    with mock.patch.object(platform, "system", return_value="Darwin"):
        error = transcriber._validate_live_capture_platform(args)
        assert error is None
    print("OK: --coreaudio-tap on macOS passes platform validation")


if __name__ == "__main__":
    test_parse_header_roundtrip()
    test_pcm_bytes_to_mono_float32_mono_input()
    test_pcm_bytes_to_mono_float32_stereo_input_averages_channels()
    test_macos_version_below_minimum_blocks_capture()
    test_macos_version_at_minimum_is_accepted_by_version_gate()
    test_missing_helper_binary_raises_clear_error()
    test_validate_live_capture_platform_flag_mismatch()
