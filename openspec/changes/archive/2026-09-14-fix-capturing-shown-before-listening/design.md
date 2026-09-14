## Context

See proposal.md - Why. How the page decides today, all in `src/main.js`:

- **Start.** `startLiveSession()` awaits `start_live_session`, which returns once the sidecar is spawned, then sets `liveState = "loaded"` ("Starting — waiting for the engine").
- **Indicators.** `renderPens()` computes `capturing = liveState !== "idle"`, so SYS and MIC read "Capturing" from `loaded` onwards.
- **Status.** The `sidecar-log` listener moves `loaded` to `listening` on *any* engine line (`if (currentFlow !== "file" && liveState === "loaded")`). Model loading prints `Loading base model from … on cpu with int8...` and `✓ Model loaded successfully` first (`transcription_engine.py`), so the status reads "Listening" while the model is still loading.
- **Transcript lines.** `markLineArrived()` already moves the session to `advancing` on the first `transcript-line`.

What the engine gives us:

- The engine loads the model in `main()` before any live function runs. Each of the four live paths (`transcribe_live_simple`, `_transcribe_live_linux_dual`, `transcribe_live_wasapi`, `transcribe_live_coreaudio_tap`) then prints a line containing `Listening...`. `cli` "compact live output" requires that confirmation.
- `sys.stdout` is reconfigured with `line_buffering=True`, so the line is flushed as soon as it is printed.
- `sidecar.rs` forwards every non-transcript stdout line as a `sidecar-log` event, unchanged.

## Goals / Non-Goals

**Goals:**
- Tie "Capturing" and "Listening" to the engine's own confirmation, using only what the engine already prints.
- Make a future rewording of that line fail a test, rather than leave the GUI stuck on "Starting".

**Non-Goals:**
- A structured readiness event from Rust or the engine.
- The elapsed-time clock, which keeps counting from the moment Start is pressed.
- The start-up time itself: model loading takes as long as it takes.

## Decisions

### 1. The listening line is the signal, matched in the page

The `sidecar-log` listener advances `loaded` → `listening` only when the line includes `Listening...`. A `transcript-line` keeps advancing the session as it does today, because a transcript can only exist once capture is running.

**Rejected: a new Tauri event emitted by `sidecar.rs` when it sees the line.** It is the same string match, moved into Rust. It adds an event, a payload and a listener to maintain, and nothing else gets that event.

**Rejected: a machine-readable status line from the engine**, such as a JSON `{"status": "listening"}`. It changes the CLI's user-facing output that `cli` specifies, for a problem the existing line already solves.

### 2. The indicators follow the session state, not "anything but idle"

`renderPens()` treats the session as capturing in `listening`, `advancing`, `penlift` and `stopping`, and not in `idle` or `loaded`. `stopping` stays capturing because the engine still holds the audio devices until the stop returns. The page already moves to `idle` only then, which the stop fix established.

**Rejected: a separate `engineListening` flag next to `liveState`.** The state machine already has a "starting" state. A second flag would be one more thing to reset on stop and on crash, and able to disagree with the state.

### 3. A test pins the engine's wording

`tests/test_gui.py` already reads `src-tauri/src/main.rs` as text for its command-name check. In the same way, it reads `transcriber.py` and fails unless every live capture function prints a line containing `Listening...`, naming any that doesn't. Rewording the CLI line in one path then fails the tests instead of silently leaving that platform's GUI on "Starting".

## Risks / Trade-offs

- **[Risk]** The listening line is printed a few statements before the capture streams actually open, so a device that fails to open shows "Capturing" for an instant before the engine exits. → The engine exits with its error, and `sidecar-crashed` returns the page to idle with the message. The window is milliseconds, against the seconds of model loading this change removes.
- **[Risk]** A future engine path forgets the line. → The Decision 3 test covers every live function by name. A new function added without it would still read "Starting" until its first transcript line arrives, which is wrong in the safe direction.
- **[Trade-off]** The page depends on a human-readable CLI string. It is specified in `cli` and now tested, which is cheaper than a new protocol.
