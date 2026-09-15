## Context

- **Engine:**
  - `transcriber.py` `_run_dual_capture` (Linux with mic, WASAPI, Core Audio) runs `run_sys(...)` on the main thread. `run_sys` returns only when the source ends (`parec` EOF, a WASAPI read error making `capture_stream` leave its loop) or raises `KeyboardInterrupt` (user stop, or `check_silence`).
  - Both paths exit 0 today. `transcribe_live_simple` (Linux without mic) has the same shape through `LinuxLoopbackCapture.capture_stream` or `AudioCapture.capture_stream`.
  - Silent chunks print nothing: `vad_filter=True` returns no segments, and the MIC worker skips quiet chunks entirely through its `gate`. The simple path alone prints "  (no speech detected)".
- **Shell:**
  - `sidecar.rs` `spawn_sidecar_events(app, rx, mark_inactive_on_exit)`. On `Terminated` for a live run, it clears `session_active` and `child` unconditionally, and emits `sidecar-crashed` only when `was_active && code != Some(0)`.
  - `stop_live_session` clears `session_active` before killing, which is how a user stop is told apart from a crash.
  - `start_file_transcription` guards against a live engine, plus a PID check that does nothing on Windows. `start_live_session` has no guard.
  - `build_live_session_args` is the unit-tested builder.
- **Page (`src/main.js`):**
  - States `idle → loaded → listening → advancing ⇄ penlift → stopping`. `tickInstrument` switches to `penlift` when `Date.now() - lastLineAt > STALL_MS` (20 s), and only after the first line.
  - "Listening..." in `sidecar-log` moves `loaded → listening`.
  - `sidecar-crashed` resets to idle and shows a note.
- **Tests:** `tests/test_dual_capture.py` fakes `run_sys` with `_feed(...)`, which returns normally at the end; its first scenario expects exit 0 from that.

## Goals / Non-Goals

**Goals:**
- Every way a live session ends is visible to the user, with the right tone: a silence stop is information, anything else unrequested is an error.
- "Stalled" means the engine stopped working, never "nobody is talking".
- At most one engine at a time in both directions, with no cross-talk between an old session's exit and a new session.

**Non-Goals:**
- A microphone stream failing while system audio continues; `sounddevice` keeps calling back with status flags. That's a separate problem.
- Recovering the UI for an engine still running after a page reload.
- Changing the CLI's default silence timeout (600 s) or its output. The heartbeat is opt-in and hidden.

## Decisions

### 1. The engine exits 1 when the source ends on its own
In `_run_dual_capture`, reaching the line after `run_sys(...)` without an exception means the source ended on its own. The engine prints `❌ System audio capture ended unexpectedly` and sets `exit_code = 1`. The existing `finally` still joins the workers and closes the transcript, so everything transcribed so far is kept. `KeyboardInterrupt` (user or `check_silence`) keeps exit 0. `transcribe_live_simple` gets the same treatment after its `capture_stream(...)` call.

**Corrected while applying (task 1.1):** "a normal return means the source ended" is not enough on its own. Every `capture_stream` (Linux, WASAPI, macOS, generic) catches `KeyboardInterrupt` and returns normally, so a user stop or a silence stop also returns. `transcriber.py` therefore records a requested stop: the SIGINT handler and both silence checks call `_request_stop()`, which sets `_stop_requested` and raises. A normal return counts as a lost source only when no stop was requested. The flag is reset at the start of each live session.

**Found in the user's Linux check (task 5.2):** after `systemctl --user restart pipewire pipewire-pulse`, `parec` exited as expected, but `_run_dual_capture`'s cleanup blocked forever in `mic_stream.stop()`, which waits on the PipeWire connection that went away. The engine stayed alive and silent, so the app only showed "stalled". Two fixes: the mic stream is closed on a helper thread and abandoned after 5 s (`_close_stream_bounded`); and when a lost source was detected, `__main__` flushes output and exits with `os._exit(code)`, because `sounddevice`'s PortAudio termination at interpreter exit can block the same way. Both flags reset at each session start.

- *Alternative:* have each `capture_stream` raise on EOF or read error. That touches three platform modules, one of them (macOS) untestable here, for the same observable result. Rejected.

### 2. `--heartbeat`: one line per chunk, per source, hidden from help
`argparse` gets `--heartbeat` with `help=argparse.SUPPRESS`. When set, `_drain_and_transcribe` prints `HEARTBEAT <TAG>` every time a buffer reaches its threshold. That includes a MIC chunk skipped by the gate, and it's printed after the transcription attempt, so a heartbeat means "a chunk went through the pipeline". `transcribe_live_simple` prints `HEARTBEAT SYS` per processed chunk.

The line has no brackets, so it can never match the transcript regex. Only the GUI passes the flag, so CLI output is unchanged.

- *Alternative:* reuse "(no speech detected)" as a log line. It's printed only on one path, it's text the user might read, and it would flood the engine log. Rejected.

### 3. Shell: one `live-session-ended` event, session generations, symmetric guards
`SidecarManager` gains:
- `live_generation: u64` and `file_generation: u64`, bumped on each spawn;
- `file_running: bool`, set on file spawn and cleared by that run's `Terminated`, replacing the per-OS `pid_alive` check;
- `last_line: String`, the last non-empty stdout or stderr line of the current live run, excluding heartbeats.

`spawn_sidecar_events` receives the generation it belongs to. On `Terminated` it changes shared state only if the stored generation still equals its own; an older run's exit is ignored. For the current live run, if `session_active` was still true (no user stop), it emits `live-session-ended { code, lastLine }` for **any** code. That replaces `sidecar-crashed`.

A pure `engine_busy(state) -> Option<&'static str>` returns the refusal message. It's used by both start commands:
- "A live session is still running. Stop it before transcribing a file."
- "A file transcription is still running. Wait for it to finish before starting a live session."

Heartbeat lines emit `sidecar-heartbeat { tag }` instead of `sidecar-log`. `build_live_session_args` gains `silence_timeout_secs: u32` and always adds `--heartbeat --silence-timeout <n>`.

- *Alternative:* compare `CommandChild` PIDs instead of generations. PIDs can be reused, and a generation is a plain integer that's easy to unit-test. Rejected.

### 4. Page: activity-based stall, notices from `live-session-ended`
- **Activity:** `lastActivityAt` is set by a transcript line or a heartbeat. The first heartbeat after "Listening..." counts like a line for leaving `loaded`/`listening`.
- **States:** `advancing` while lines arrive. After `QUIET_MS` (2× chunk, 20 s) with heartbeats but no line, the state returns to `listening`; its label becomes "Listening — no speech right now", while "no speech yet" stays for before the first line. `penlift` only when `Date.now() - lastActivityAt > STALL_MS`, now 3× chunk (30 s), to cover slow CPU inference on a 10 s chunk.
- **Session end:** on `live-session-ended`, set `sessionRunning = false`, idle, and a note:
  - `code === 0 && lastLine` includes "minutes of silence" → "Stopped after N minutes of silence. The transcript so far is saved." N is the setting the session was started with, not parsed text.
  - otherwise → "Transcription ended unexpectedly: <lastLine>" (or the exit code when there is no line).

  The "minutes of silence" text comes from the engine's existing auto-stop print, which both paths share. The GUI test pins that coupling, and `test_listening_wording` is the precedent.

### 5. The silence setting is designed with the Impeccable skill
A new live-only field: minutes as a number, default 10, with 0 or a clear "Never" choice to turn it off. It's stored in `localStorage` (`transcriber-silence-minutes`, the theme's try/catch pattern) and sent as `silenceTimeoutMinutes`. The shell converts to seconds.

The Impeccable pass settles placement (likely the Live panel near the device fields), the control type (number input vs select of common values), the copy, and how the status copy from Decision 4 reads. It follows `DESIGN.md`, fits both rail widths, adds no new colours, respects the strict CSP, and ends with the `impeccable-finish-reviewer` agent.

## Risks / Trade-offs

- **Slow inference** (large model on CPU) can exceed 30 s per chunk and show a false stall. → The threshold is a named constant. Heartbeats come after inference, so a real stall and slow inference look alike; the stall detail text points to the engine log. Accepted.
- **The silence notice depends on the engine's wording.** → A GUI test pins the phrase, and an engine test pins the print. If either drifts, a test fails.
- **An engine older than this change** (a stale staged sidecar) doesn't know `--heartbeat` and fails to start with an argparse error. → The shell, page and engine ship together; a local dev build needs `build_sidecar.py`, noted in the tasks. The error surfaces as a session-ended note, never silently.
- **Stricter guard.** Pressing Start during a file run is now refused, where it used to "work" with two engines. Intended.

## Migration Plan

- Stored settings: new key only, absent means 10 minutes.
- The event rename (`sidecar-crashed` → `live-session-ended`) is internal to one binary; the page and shell ship together.
- Rollback: revert. Nothing persisted depends on the new events.
