# Tasks

## 1. Engine (can be done anywhere)

- [ ] 1.1 Add the hidden `--stop-on-stdin` flag to `transcriber.py`, with a daemon thread that reads stdin lines and calls `_thread.interrupt_main()` once on `stop` or EOF (design.md Decision 1). Add a check that fails without it: run the engine's live mode against a fake capture with `--stop-on-stdin`, write `stop`, and verify it exits through the normal shutdown path (exit code and compact stop line as for Ctrl+C); do the same for EOF. Verify no change without the flag.

## 2. App (Windows)

- [ ] 2.1 In `src-tauri/src/sidecar.rs`, under `#[cfg(windows)]`: pass `--stop-on-stdin` to live sessions, and make `stop_live_session` write `stop\n`, wait up to 15 s for the run's `Terminated` event, then fall back to `taskkill_tree` (design.md Decision 3). Add a unit test for the argument, and keep `cargo test` passing. Verify on Linux that nothing changes for `cfg(not(windows))`.

## 3. Verification in a Windows session

- [ ] 3.1 With the frozen sidecar: start a live session in the app, speak, press Stop within 10 s, and verify the last words appear in the transcript and the app reports "Capture engine stopped.". Verify no `transcriber-sidecar.exe` process remains. If the worker didn't receive the stop, apply design.md Decision 2's fallback.
- [ ] 3.2 Force a hang: a debug build whose engine ignores stdin. Verify Stop falls back to `taskkill` after about 15 s, and that the report says so.
- [ ] 3.3 Run `openspec validate 02-flush-live-tail-on-stop-windows --strict` and verify it passes.
