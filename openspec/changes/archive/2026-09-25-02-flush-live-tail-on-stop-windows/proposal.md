## Why

On Windows, the desktop app's Stop ends the engine with `taskkill /F /T` (`src-tauri/src/sidecar.rs`, `stop_live_session`). The engine gets no chance to run its shutdown, so anything captured but not yet transcribed is lost. `01-flush-live-tail-on-stop` makes the engine transcribe the remaining audio when it stops, but a forced kill skips that. It also breaks two scenarios of the existing "On-demand sidecar lifecycle" requirement on Windows: "signals the sidecar to stop gracefully", and "given the chance to flush and close its transcript file". The code's own comment names the fix: "a stdin-based stop protocol in transcriber.py if abrupt termination is found to drop buffered transcript lines". It has now been found to.

## What Changes

- **Engine:** a hidden `--stop-on-stdin` flag starts a thread that reads the engine's standard input. A `stop` line, or the input closing, takes the same path as Ctrl+C (`_thread.interrupt_main()`, as `_print_or_stop` already does). A normal shutdown then follows, including 01's final chunk.
- **App, Windows only:**
  - starts live sessions with `--stop-on-stdin`;
  - on Stop, writes `stop` to the engine's input;
  - waits for the engine to exit, up to the same 15 s grace as Linux and macOS;
  - uses `taskkill /F /T` only if the engine is still running after that, so a hung engine still can't hold the audio device.
- Linux and macOS are unchanged: they keep SIGINT.
- Depends on `01-flush-live-tail-on-stop` for the final chunk. Without it, a graceful stop still closes the transcript cleanly but loses the tail as before.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `desktop-gui`: "On-demand sidecar lifecycle with crash recovery" adds a Windows scenario, since stopping there is graceful too, with the forced kill only as a fallback.

## Impact

- `transcriber.py` (the hidden flag and a stdin reader thread).
- `src-tauri/src/sidecar.rs` (the Windows stop path and live-session arguments).
- Must be verified in a Windows session: the engine, the app and the frozen sidecar (the PyInstaller bootloader and its re-executed worker) all have to pass the stop along.
