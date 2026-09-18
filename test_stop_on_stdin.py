#!/usr/bin/env python3
"""--stop-on-stdin stops a live session the way Ctrl+C does, on a "stop" line
or when stdin closes (openspec/changes/02-flush-live-tail-on-stop-windows).

The desktop app on Windows can't send SIGINT to its console-less engine, so it
writes "stop" instead. Each case runs the real engine entry point (argument
parsing, the SIGINT handler, the live runner) in a subprocess, with only the
model and the audio source faked, and compares its exit with a Ctrl+C.
No model, audio or Windows needed. Run: python test_stop_on_stdin.py
"""
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DRIVER = r"""
import sys, time, numpy as np
sys.path.insert(0, sys.argv.pop(1))
import transcriber

class Engine:
    device, compute_type = "cpu", "int8"
    def __init__(self, **kw): pass
    def transcribe_chunk(self, audio, language=None): return []
    def format_timestamp(self, start, end): return ""

def fake_live(engine, args):
    def run_sys(on_chunk, enqueue, check_silence):
        print("LISTENING", flush=True)
        while True:  # a capture that runs until the session is stopped
            on_chunk(np.zeros(1600, np.float32))
            time.sleep(0.1)
    return transcriber._run_dual_capture(engine, args, title="T", mode_summary="T",
                                         sys_rate=lambda: 16000, run_sys=run_sys, mic=None)

transcriber.TranscriptionEngine = Engine
transcriber.transcribe_live_simple = fake_live
sys.argv = ["transcriber.py"] + sys.argv[1:]
sys.exit(transcriber.main())
"""


def start(*flags):
    # Its own folder: a live session writes an auto-named transcript into its
    # working directory.
    cwd = tempfile.mkdtemp(prefix="stop-on-stdin-")
    proc = subprocess.Popen([sys.executable, "-c", DRIVER, str(ROOT), "--live", "--silence-timeout", "0", *flags],
                            cwd=cwd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True)
    proc.cwd = cwd
    assert proc.stdout.readline().strip() == "LISTENING" or _wait_listening(proc), "the session never started"
    return proc


def _wait_listening(proc):
    for line in proc.stdout:
        if line.strip() == "LISTENING":
            return True
    return False


def finish(proc, timeout=15):
    out, _ = proc.communicate(timeout=timeout)
    shutil.rmtree(proc.cwd, ignore_errors=True)
    # The transcript's auto-generated name carries the time; only its shape matters.
    stop_lines = [re.sub(r"transcript_\d{8}_\d{6}", "transcript_<time>", l)
                  for l in out.splitlines() if l.startswith("Stopped")]
    return proc.returncode, stop_lines, out


def main() -> int:
    # Reference: Ctrl+C (SIGINT) with no flag.
    proc = start()
    proc.send_signal(signal.SIGINT)
    ref_code, ref_stop, ref_out = finish(proc)
    assert ref_stop, f"Ctrl+C gave no stop line:\n{ref_out}"

    # A "stop" line ends the session the same way.
    proc = start("--stop-on-stdin")
    proc.stdin.write("stop\n")
    proc.stdin.flush()
    code, stop, out = finish(proc)
    assert (code, stop) == (ref_code, ref_stop), f"'stop' gave {code} {stop}, Ctrl+C gave {ref_code} {ref_stop}:\n{out}"

    # stdin closing (the app went away) does too.
    proc = start("--stop-on-stdin")
    proc.stdin.close()
    code, stop, out = finish(proc)
    assert (code, stop) == (ref_code, ref_stop), f"EOF gave {code} {stop}:\n{out}"

    # Without the flag, stdin is ignored: "stop" does nothing, Ctrl+C still works.
    proc = start()
    proc.stdin.write("stop\n")
    proc.stdin.flush()
    time.sleep(1.0)
    assert proc.poll() is None, "without --stop-on-stdin, a 'stop' line ended the session"
    proc.send_signal(signal.SIGINT)
    code, stop, _ = finish(proc)
    assert (code, stop) == (ref_code, ref_stop)

    print(f"PASS  --stop-on-stdin: 'stop' and EOF end the session like Ctrl+C (exit {ref_code}, {ref_stop[0]!r}); "
          "ignored without the flag")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except AssertionError as exc:
        print(f"FAIL  --stop-on-stdin: {exc}")
        sys.exit(1)
