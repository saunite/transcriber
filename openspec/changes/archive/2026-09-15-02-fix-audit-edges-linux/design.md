> **Superseded by task 1.1 (2026-09-15):** neither decision below was needed. On PipeWire with WirePlumber's default policy, today's explicit `<default sink>.monitor` recording already follows a default-output change, and the user chose no code change (see proposal.md, "Outcome of verification"). What keeps it working is that auto-detection picks the monitor of the sink that is the default at start; `test_linux_loopback_capture.py` pins that.

## Context

`LinuxLoopbackCapture.get_default_loopback_device()` lists sources with `pactl list sources short`, reads `pactl get-default-sink`, and returns `<default sink>.monitor`, or the first monitor. `capture_stream` then runs `parec --device=<that name>`. A stream with an explicit device is not moved when the default changes. This machine runs PulseAudio on PipeWire 1.6.8 (`pactl info`), and `pactl`'s man page documents `@DEFAULT_MONITOR@` as a special name.

## Goals / Non-Goals

**Goals:**
- Capture follows the default output on PipeWire. PulseAudio proper is also supported if the same mechanism works there.

**Non-Goals:**
- Following a change of the *microphone* default.
- Windows (`03-fix-audit-edges-windows` parks it).
- Changing which source the start-up check and status line report.

## Decisions

### 1. Try `parec --device=@DEFAULT_MONITOR@` first

It's one argument, and the server decides what "default" means. It's only acceptable if a recording connected that way is actually **moved** when the default sink changes, not just resolved once at connect. That isn't documented locally, so task 1.1 verifies it before any code changes.

### 2. Fallback: restart `parec` when the default sink changes

If the recording isn't moved, the main loop in `capture_stream` reads `pactl get-default-sink` about every 2 s while waiting for audio. When it differs from the sink being captured, it terminates `parec` and starts a new one on the new sink's monitor. The reader thread is restarted on the new process's stdout.
- **Cost:** a short gap (the restart), and one `pactl` call every 2 s.
- **Why this over `pactl subscribe`:** no long-lived second subprocess to parse and clean up.

The capture must not report a lost source during a planned restart. The reader's EOF handling today ends capture (`is_capturing = False`), so a restart has to swap the process before the old reader sees EOF, or tell the two apart.

### 3. Start-up check and status line stay as they are

`get_default_loopback_device()` still runs, to fail early when no monitor exists and to name the device in the compact status line. Only what `parec` records changes.

## Risks / Trade-offs

- **[The special name resolves once and doesn't move]** → Task 1.1 decides, and Decision 2 is the fallback.
- **[Verification changes the user's default output]** → Task 1.1 uses two null sinks and a generated tone, restores the original default sink and unloads the modules afterwards, and runs only with the user's go-ahead (their audio is redirected for a few seconds).
- **[A monitor of a sink with a different channel layout]** → `parec` requests 16 kHz mono and the server converts, same as today.
