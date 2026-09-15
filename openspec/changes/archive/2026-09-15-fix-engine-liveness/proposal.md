## Why

The logic audit (2026-09-15, cluster A) found that the desktop app can say it is recording when it isn't. Five problems:
1. **Silent auto-stop.** The GUI never passes `--silence-timeout`, so the engine's 600 s default applies. After 10 minutes without speech the engine exits with code 0, and `sidecar.rs` reports an exit only when the code is non-zero. The UI keeps showing "Listening" or "stalled" while nothing is captured. The `desktop-gui` spec already requires the app to "detect unexpected sidecar exit and surface an error".
2. **Capture loss also exits 0.** When the audio source goes away (`parec` EOF after a PipeWire restart, a WASAPI read error when a headset disconnects), `capture_stream` just returns, the engine exits 0, and the session ends invisibly.
3. **A quiet room reads as "stalled".** `vad_filter` drops silent chunks without printing anything, and the GUI calls any 20 s without a transcript line a stall. A healthy quiet room shows "Transcribing stalled — no output", which contradicts "A stalled capture is distinguishable from a silent one".
4. **No one-engine guard on live start.** `start_live_session` checks for neither a running file transcription nor a live engine, so pressing Start during a file run starts a second engine.
5. **A late exit can hit the next session.** The previous session's exit event clears `child` and `session_active` unconditionally. After a quick Stop then Start, it can wipe the new session's handle, so Stop can't kill it, and send a false crash.

## What Changes

- **Engine:**
  - A live capture whose audio source ends on its own, not through Ctrl+C or the silence timeout, exits non-zero with a message saying capture ended.
  - A hidden `--heartbeat` flag makes the engine print one heartbeat line per processed or skipped chunk, per source. It never runs in normal CLI output.
- **Shell:**
  - Every exit of the current live session that the user didn't request reaches the page as a `live-session-ended` event, with the exit code and the engine's last output line, whatever the code. This replaces `sidecar-crashed`.
  - Live and file runs carry a session generation, so an exit event from an older run can't touch newer state.
  - A live session is refused while a live or file engine is still running.
  - Heartbeat lines become a `sidecar-heartbeat` event, not engine-log lines.
- **GUI:**
  - **New setting:** stop after silence, in minutes. The default is 10, 0 means never, it's remembered, and it's passed as `--silence-timeout`.
  - **Notice when a session ends by itself:** a silence stop is a clean exit (code 0), shown as information, not an error: "Stopped after 10 minutes of silence. The transcript so far is saved." Any other self-ended session is an error with the engine's last line. Either way the UI returns to idle.
  - **Stall detection counts heartbeats as liveness:** a quiet room shows a listening state, and "stalled" appears only when neither heartbeats nor lines arrive for 3× the chunk length (30 s).
- **Not in this change:** audit clusters B (flow routing), C (time axis) and D (CLI and launcher edges), which are recorded in `openspec/backlog.md`. Also a microphone stream that errors while system audio continues, and recovering a session after the page reloads.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `desktop-gui`:
  - "On-demand sidecar lifecycle with crash recovery": any unrequested end of a live session is surfaced, whatever the exit code; a live start is refused while an engine runs; a finished older session never affects a newer one.
  - "A stalled capture is distinguishable from a silent one": a quiet room after speech stays distinguishable from a stall.
  - Added "Live sessions stop after a configurable silence": the setting, its default and the notice.
- `cli`: added "Live capture reports a lost audio source": a non-zero exit with a message when the audio source ends on its own.

## Impact

- **`transcriber.py`:** `_run_dual_capture` and `transcribe_live_simple` exit non-zero when the source ends on its own, and gain the hidden `--heartbeat` flag. Unit tests in `test_dual_capture.py`.
- **`src-tauri/src/sidecar.rs`:** session generations, a `file_running` flag replacing the per-OS PID check, the live-start guard, `live-session-ended` and `sidecar-heartbeat` events, and `--heartbeat --silence-timeout <s>` in the live arguments. `cargo test` for the pure decision helpers.
- **`src/index.html`, `src/style.css`, `src/main.js`:** the silence setting (layout change, so designed and reviewed with the Impeccable skill) and the new liveness and notice logic. GUI scenarios in `tests/test_gui.py`, including simulated time for the stall threshold.
- **README:** the GUI setting, and the CLI's non-zero exit on a lost source.
- **No new dependencies.** The CLI's own defaults, output and `--silence-timeout` semantics are unchanged.
