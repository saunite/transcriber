## Why

Logic audit cluster D, item D6, the Linux half (2026-09-15, `openspec/backlog.md`). Linux system-audio capture resolves the default sink's monitor once, when the session starts, and runs `parec --device=<that sink>.monitor`. If the default output changes mid-session, for example Bluetooth headphones connecting or the user switching output in the desktop's sound menu, the meeting's audio moves to the new sink. The session keeps recording the old sink's monitor, and everything the other side says after that is lost, with no error. The shared and Windows halves of cluster D are `01-fix-audit-edges` and `03-fix-audit-edges-windows`.

## What Changes

- **System audio follows the default output on Linux:** a live session captures whatever the current default output device plays, including after the default changes mid-session.
- **Unchanged:** the start-up check that a monitor source exists, and the device name shown in the status line (the default at start).
- **Not in this change:** Windows WASAPI following a default-output change. The user scoped it out, and `03-fix-audit-edges-windows` parks it in the backlog.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `audio-capture`, "Capture live system audio": on Linux, capture follows the default output device when it changes during a session.

## Impact

- **`linux_loopback_capture.py`:** `capture_stream` targets the default monitor so it follows changes. It uses PipeWire's `@DEFAULT_MONITOR@` special name if that proves to follow the default, or else restarts `parec` when `pactl get-default-sink` changes (design.md).
- **`transcriber.py`:** only if the passed device name changes. The Linux auto-detect `run_sys` passes the resolved name today.
- **Tests:** a unit test with a faked `Popen`/`pactl`, plus a one-off verification with two null sinks, recorded in the tasks.
- **Docs:** the README's Linux notes.
- **No GUI, shell or dependency changes.**
