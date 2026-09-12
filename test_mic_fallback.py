#!/usr/bin/env python3
"""Checks for microphone resolution (openspec/changes/fix-linux-live-capture-alsa).

The bug this guards against: a CI-built sidecar on a distribution whose ALSA
layout differs from the build host's sees no default input device, so
`sd.query_devices(kind='input')` raises -- and the old code printed
"Could not auto-detect microphone" and exited, killing the live session even
though usable input devices were present.

Fakes the device layer rather than touching real audio hardware, so it runs
anywhere. Run: python test_mic_fallback.py
"""
from __future__ import annotations

import sys
import types

import transcriber


class _FakeSd:
    """Minimal stand-in for the sounddevice surface the helper uses."""

    def __init__(self, devices, default_input_index):
        self._devices = devices
        self._default = default_input_index

    def query_devices(self, device=None, kind=None):
        if kind == "input":
            if self._default is None:
                raise RuntimeError("Error querying device -1")
            return self._devices[self._default]
        if device is None:
            return self._devices
        return self._devices[device]


def _args(mic_device=-1, verbose=False):
    return types.SimpleNamespace(mic_device=mic_device, verbose=verbose)


MIC = {"index": 3, "name": "Real Mic", "max_input_channels": 2, "default_samplerate": 48000.0}
SPEAKERS = {"index": 0, "name": "HDMI 0", "max_input_channels": 0, "default_samplerate": 44100.0}
MONITOR = {"index": 1, "name": "HDMI 1", "max_input_channels": 0, "default_samplerate": 44100.0}


def _run(devices, default_index, mic_device=-1):
    """Call the helper with a faked device layer; return (result, output).

    The helper does its own `import sounddevice as sd` (deferred, so a --file
    run never initialises PortAudio), so the fake has to go into sys.modules
    rather than onto the transcriber module.
    """
    printed: list[str] = []
    fake = types.ModuleType("sounddevice")
    fake.query_devices = _FakeSd(devices, default_index).query_devices
    real_module = sys.modules.get("sounddevice")
    sys.modules["sounddevice"] = fake
    try:
        import builtins

        real_print = builtins.print
        builtins.print = lambda *a, **k: printed.append(" ".join(str(x) for x in a))
        try:
            result = transcriber._resolve_mic_device(_args(mic_device=mic_device))
        finally:
            builtins.print = real_print
    finally:
        if real_module is None:
            del sys.modules["sounddevice"]
        else:
            sys.modules["sounddevice"] = real_module
    return result, "\n".join(printed)


def main() -> None:
    # 1. A resolvable default input is used as-is.
    result, out = _run([SPEAKERS, MONITOR, MIC, MIC], default_index=2)
    assert result == 3, (result, out)

    # 2. No default input, but real inputs exist -> fall back, and say which.
    #    This is the exact Fedora-on-Ubuntu-build case.
    result, out = _run([SPEAKERS, MONITOR, MIC], default_index=None)
    assert result == 3, (result, out)
    assert "Real Mic" in out, f"fallback must name the device it chose: {out!r}"

    # 3. No input devices at all -> fatal, with actionable guidance.
    result, out = _run([SPEAKERS, MONITOR], default_index=None)
    assert result is None, (result, out)
    assert "--list-devices" in out and "--mic-device" in out, (
        f"failure must name the commands for listing and selecting devices: {out!r}"
    )

    # 4. An explicit device is passed through untouched, even a nonsensical
    #    one -- validation of it belongs to the caller, whose
    #    "Invalid microphone device" behaviour this change does not alter.
    result, out = _run([SPEAKERS, MONITOR, MIC], default_index=2, mic_device=1)
    assert result == 1, (result, out)
    assert out == "", f"explicit selection should print nothing: {out!r}"

    print("test_mic_fallback: all checks passed")


if __name__ == "__main__":
    sys.exit(main())
