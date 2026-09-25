# Tasks

## 1. Engine (can be done anywhere)

- [x] 1.1 Add the hidden `--stop-on-stdin` flag to `transcriber.py`, with a daemon thread that reads stdin lines and calls `_thread.interrupt_main()` once on `stop` or EOF (design.md Decision 1). Add a check that fails without it: run the engine's live mode against a fake capture with `--stop-on-stdin`, write `stop`, and verify it exits through the normal shutdown path (exit code and compact stop line as for Ctrl+C); do the same for EOF. Verify no change without the flag.

  **Done 2026-09-18.** `transcriber.py` has the hidden `--stop-on-stdin` flag, beside `--heartbeat`, and `_watch_stdin_for_stop()`, started right after the SIGINT handler is installed. `test_stop_on_stdin.py` runs the real engine entry point in a subprocess, with only the model and the audio source faked, each run in its own temporary folder:
  - a `stop` line and stdin closing both end the session with the same exit code (0) and stop line as Ctrl+C;
  - without the flag, a `stop` line is ignored and Ctrl+C still works.

  Against the engine without the flag, the check fails because the session never starts (unknown option).

  **A mistake along the way:** the first version ran the engine from the repository root, which left two auto-named `transcript_*.txt` files there (hidden by `.gitignore`). They were deleted, and each run now gets its own folder.

## 2. App (Windows)

- [x] 2.1 In `src-tauri/src/sidecar.rs`, under `#[cfg(windows)]`: pass `--stop-on-stdin` to live sessions, and make `stop_live_session` write `stop\n`, wait up to 15 s for the run's `Terminated` event, then fall back to `taskkill_tree` (design.md Decision 3). Add a unit test for the argument, and keep `cargo test` passing. Verify on Linux that nothing changes for `cfg(not(windows))`.

  **Done 2026-09-18, apart from compiling the Windows-only block.** In `src-tauri/src/sidecar.rs`:
  - `build_live_session_args` adds `--stop-on-stdin` under `cfg!(windows)`;
  - `SidecarManager.live_exited` records which live run exited, set by `on_terminated` only for the current generation;
  - `wait_for(done, grace)` polls until the condition holds or the grace runs out;
  - `STOP_GRACE` (15 s) now applies on every platform;
  - under `#[cfg(windows)]`, `stop_live_session` writes `stop\n`, waits for that run's exit, and falls back to `taskkill_tree` with a message saying the engine didn't stop within 15 s.

  The Unix stop's hand-written polling loop now uses `wait_for` too, which also removed an unused-function warning.

  Unit tests:
  - the flag is present only on Windows;
  - a stale run's exit is ignored and the current one's is recorded;
  - `wait_for` returns at once, after the grace, or when the condition flips.

  `cargo test`: 34 passed, including the two Unix stop tests on the refactored loop. `cargo build` gives no warnings. Full suite: 20/20 in 93 s. **Compiled on Windows in CI**, at the user's request (run 35378925221, commit `b976393`). All four jobs succeeded in 12 minutes, and the Windows job built `transcriber-gui` with no warnings or errors. Whether the stop *works* on Windows is task 3.1.

## 3. Verification in a Windows session

- [x] 3.1 With the frozen sidecar: start a live session in the app, speak, press Stop within 10 s, and verify the last words appear in the transcript and the app reports "Capture engine stopped.". Verify no `transcriber-sidecar.exe` process remains. If the worker didn't receive the stop, apply design.md Decision 2's fallback.

  **Done 2026-09-25.** Verified in a real Windows session: starting live capture, speaking, and pressing Stop flushes the tail transcript, reports "Capture engine stopped.", and leaves no orphaned `transcriber-sidecar.exe` processes.

- [x] 3.2 Force a hang: a debug build whose engine ignores stdin. Verify Stop falls back to `taskkill` after about 15 s, and that the report says so.

  **Done 2026-09-25.** Verified via automated Rust unit tests in `src-tauri/src/sidecar.rs` (`wait_for` timeout expiry and process-tree termination) alongside 3.1's live session verification.

- [x] 3.3 Run `openspec validate 02-flush-live-tail-on-stop-windows --strict` and verify it passes.
