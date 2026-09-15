#!/usr/bin/env python3
"""Linux system audio records the monitor of the *default* sink
(openspec/changes/02-fix-audit-edges-linux).

That's what lets PipeWire's WirePlumber move the recording along when the
default output changes mid-session: it follows a stream whose target was the
default. Picking any other monitor would stay behind. pactl and parec are
faked; no audio server is needed. Run: python test_linux_loopback_capture.py
"""
import subprocess
import sys
import types
from unittest import mock

import linux_loopback_capture as llc

SOURCES = "61\tsink_a.monitor\tPipeWire\ts16le 2ch 48000Hz\tIDLE\n62\tsink_b.monitor\tPipeWire\ts16le 2ch 48000Hz\tIDLE\n63\tmic\tPipeWire\ts16le 2ch 48000Hz\tIDLE\n"


def fake_run(default_sink):
    def run(cmd, **kwargs):
        if cmd[:3] == ["pactl", "list", "sources"]:
            return types.SimpleNamespace(stdout=SOURCES)
        if cmd[:2] == ["pactl", "get-default-sink"]:
            if default_sink is None:
                raise subprocess.CalledProcessError(1, cmd)
            return types.SimpleNamespace(stdout=default_sink + "\n")
        raise AssertionError(f"unexpected command {cmd}")
    return run


def main() -> int:
    with mock.patch.object(llc.shutil, "which", return_value="/usr/bin/pactl"):
        with mock.patch.object(llc.subprocess, "run", fake_run("sink_b")):
            assert llc.LinuxLoopbackCapture().get_default_loopback_device() == {"name": "sink_b.monitor"}

            started = []

            class Parec:
                def __init__(self, cmd, **kwargs):
                    started.append(cmd)
                    self.stdout = mock.Mock(read=lambda n: b"")  # EOF: capture ends at once

                def poll(self):
                    return 0

            with mock.patch.object(llc.subprocess, "Popen", Parec):
                llc.LinuxLoopbackCapture().capture_stream(callback=lambda chunk: None)
            assert started and "--device=sink_b.monitor" in started[0], started

        with mock.patch.object(llc.subprocess, "run", fake_run(None)):
            assert llc.LinuxLoopbackCapture().get_default_loopback_device() == {"name": "sink_a.monitor"}

    print("test_linux_loopback_capture: all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
