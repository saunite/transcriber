## 1. Surface the real stop result

- [x] 1.1 In `stop_live_session` (`src-tauri/src/sidecar.rs`), stop discarding `taskkill`'s `Output` — capture it and check `.status.success()`
- [x] 1.2 On success, emit a `sidecar-log` event confirming the session stopped
- [x] 1.3 On failure, emit a `sidecar-log` event stating the stop did not succeed (include the exit code for anyone diagnosing it later)

## 2. Verification

- [x] 2.1 Rebuild and confirm a normal Stop click now shows a confirmation line in the debug/engine log panel

  Confirmed on real Windows hardware (run directly from the `\\wsl.localhost\...` build path — no extraction-to-local-disk needed, per the UNC fix already landed in `05-remove-installer-packaging-windows` task 2.0): engine log shows `— stop requested · 10:44:28 —` immediately followed by `Capture engine stopped.`
- [x] 2.2 Confirm `sidecar-crashed` still does not fire for a deliberate stop (unrelated code path — `was_active` already reads `false` by the time `Terminated` fires, since `session_active` is set before `taskkill` runs; this task only re-confirms that ordering wasn't disturbed)

  Confirmed in the same run: status returned cleanly to "Not recording" with no crash/error note shown.
- [ ] 2.3 If feasible, force a failure case (e.g. stop after the process has already exited on its own) and confirm the failure message appears rather than nothing

  Attempted on real Windows hardware: ending `transcriber-sidecar.exe` via Task Manager without clicking Stop first triggers the pre-existing `sidecar-crashed` path instead ("Capture engine exited unexpectedly") — confirms 2.2 further, but doesn't exercise 1.3's new taskkill-failure branch. That branch needs Stop clicked *before* the app's own crash-detection listener notices the process is gone and clears its handle — a narrow race between two things watching the same dead process, not reliably reproducible by hand. Leaving open per the task's own "if feasible" — the code path itself (`Ok(output)` non-success / `Err(e)` arms in `stop_live_session`) is simple enough to be confident in by inspection even without hitting it live.
