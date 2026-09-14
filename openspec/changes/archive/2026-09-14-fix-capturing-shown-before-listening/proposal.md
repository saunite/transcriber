## Why

When a live session starts, the GUI shows SYS and MIC as "Capturing" and soon moves the status to "Listening — no speech yet", while the engine is still loading its model and nothing is being captured. The user found this testing the Windows build on 2026-09-14. It is not Windows-specific: the same page runs on every platform. It tells the user they are being transcribed when they are not, so whatever is said during those seconds is silently lost.

## What Changes

- **The capture indicators stay idle until the engine is listening.** Today `renderPens()` (`src/main.js`) treats every non-idle state as capturing, including the `loaded` state ("Starting — waiting for the engine"), which begins the moment `start_live_session` returns.
- **The status moves from "Starting" to "Listening" only on the engine's listening confirmation.** Today any `sidecar-log` line advances it, including model-loading output. The CLI already prints that confirmation in every live capture path: `cli` "compact live output" requires the line, and it reads `Listening... (Ctrl+C to stop…)`. It is printed after the model has loaded, and stdout is line-buffered, so it reaches the GUI promptly.
- **The GUI start/stop test is updated** so it drives the engine's output. It checks that the indicators stay idle through model-loading output and switch to capturing only on the listening line.
- **Not in scope:**
  - The elapsed-time clock, which still counts from the moment Start is pressed.
  - Any change to the engine, its output or the Rust sidecar code.
  - The file view.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `desktop-gui`: adds a requirement that the live session presents capture as active only once the engine confirms it is listening. It is added rather than modifying "On-demand sidecar lifecycle with crash recovery", whose "starting state until output begins" wording is loose enough to allow today's bug, because `fix-live-stop-orphans-engine` still has that requirement open as a MODIFIED delta.

## Impact

- **Changed:** `src/main.js` (how the capture indicators and the start-up status are derived), `tests/test_gui.py` (the live start/stop scenario).
- **Unchanged:** `transcriber.py`, `src-tauri/`, packaging, and every platform's capture code.
- **Relies on:** the CLI's listening confirmation keeping the text `Listening...`. A GUI test checks that the engine still prints it, so a reworded line fails the tests instead of silently leaving the GUI stuck on "Starting".
