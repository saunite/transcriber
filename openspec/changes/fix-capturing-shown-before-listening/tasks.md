## 1. Page behaviour

- [x] 1.1 In `src/main.js`, make the `sidecar-log` listener advance `loaded` → `listening` only for a line containing `Listening...` (design.md Decision 1), and make `renderPens()` treat only `listening`, `advancing`, `penlift` and `stopping` as capturing (Decision 2). Verify with 2.1 and 2.2, which fail against today's code.

  **Done 2026-09-14.** The `sidecar-log` listener now advances `loaded` → `listening` only when `event.payload.line.includes("Listening...")`. `renderPens()` uses `CAPTURING_STATES = new Set(["listening", "advancing", "penlift", "stopping"])` in place of `liveState !== "idle"`. `node --check` passes. Against the old test, "live start/stop" failed with `expected 'Capturing', actual 'Idle'`, the intended change of behaviour.

## 2. Tests

- [x] 2.1 Rewrite `tests/test_gui.py`'s live start/stop scenario to drive the engine's output. It must check, in order:
  - after Start, `start_live_session` was requested, both indicators read "Idle", and the status reads "Starting — waiting for the engine";
  - after emitting `sidecar-log` lines `Loading base model from /m on cpu with int8...` and `✓ Model loaded successfully`, nothing has changed;
  - after emitting `Listening... (Ctrl+C to stop)`, both indicators read "Capturing" and the status reads "Listening — no speech yet";
  - after Stop, `stop_live_session` was requested, both indicators read "Idle", and no control says "Record".
  Verify it passes with 1.1, and that each half fails when reverted on its own: the old `sidecar-log` condition and the old `renderPens()` condition.

  **Done 2026-09-14.** Passes with 1.1. Each half reverted alone fails it: the old `sidecar-log` condition gives `expected 'Starting — waiting for the engine'`, and the old `renderPens()` condition gives `expected ['Idle', 'Idle']`.
- [x] 2.2 Add an "engine exits before listening" scenario. Start a session, emit model-loading `sidecar-log` lines, then emit `sidecar-crashed` with a message. Check that the indicators never read "Capturing", that they read "Idle" afterwards, and that the note shows the message. Verify it passes, and fails when `renderPens()` is reverted to `liveState !== "idle"`.

  **Done 2026-09-14.** A `MutationObserver` records every text the pens ever show, so a brief "Capturing" cannot slip between two assertions. Passes with 1.1. With `renderPens()` reverted it fails with `a pen showed Capturing before the engine was listening: ['Capturing', 'Capturing', …]`. It also fails with only the old `sidecar-log` condition, since a model-loading line then moves the session to `listening`.
- [x] 2.3 Add the wording check (design.md Decision 3): read `transcriber.py` as text and fail, naming the function, unless each of `transcribe_live_simple`, `_transcribe_live_linux_dual`, `transcribe_live_wasapi` and `transcribe_live_coreaudio_tap` contains `Listening...`. Verify it passes on today's tree, and fails naming the function when a scratch copy has one line reworded.

  **Done 2026-09-14.** `functions_missing_listening()` passes on today's tree (`[]`). On a scratch copy with `transcribe_live_wasapi`'s `Listening...` reworded, it returns `['transcribe_live_wasapi']`, and the test names it.

## 3. Full run and real-app check

- [x] 3.1 Run `.venv/bin/python run_tests.py` and verify it exits 0 with every suite passing.

  **Done 2026-09-14.** With `TRANSCRIBER_TEST_SPEECH` set to the maintainer's local recording, 10/10 suites passed in 35.8s, and `tests/test_gui.py` now runs 8 scenarios.
- [ ] 3.2 **User check in the real app** (any platform, since the page is shared): start a live session and watch SYS/MIC during model loading. Verify they read "Idle" and the status reads "Starting — waiting for the engine" until the engine log shows `Listening...`, then switch to "Capturing" and "Listening — no speech yet".
