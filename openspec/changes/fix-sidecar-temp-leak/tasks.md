## 1. Stop grace

- [x] 1.1 In `src-tauri/src/sidecar.rs`, replace the 3 s wait in `terminate_process_tree` with a named `STOP_GRACE` of 15 s (design.md Decision 1), and update its doc comment. Add a Unix unit test: `terminate_process_tree` on `sh -c 'trap "sleep 5; exit 0" INT; sleep 60'` returns no survivors, and the process ended with exit code 0, not killed by signal 9. Verify `cargo test` passes, and the new test fails with the grace set back to 3 s.

  **Done 2026-09-15.** `STOP_GRACE` (15 s, Unix) replaces the 3 s deadline in `terminate_process_tree`, and the doc comments explain the unpacked-copy reason.

  **Deviation from the task text:** the planned `sh -c 'trap ... INT; sleep 60'` stand-in doesn't behave like an engine. A foreground `sleep` makes `sh` exit 130 without running the trap, and a background one ignores SIGINT, so a variant loop hung. The test `a_slow_graceful_exit_is_not_killed` uses a `python3` stand-in instead: SIGINT handler sleeps 5 s then exits 0; it prints "ready" before the signal; the test skips if `python3` is missing. It asserts no survivors, no terminating signal, exit code 0, and that the wait ended before 10 s.

  Passes in 5.1 s. With the grace set back to 3 s it fails with "the engine was killed (… 9) instead of exiting by itself". `cargo test`: 30 passed, 1 ignored. The suite now takes about 15 s, because `finds_and_terminates_a_whole_process_tree`'s background `sleep` ignores SIGINT and waits out the grace before the SIGKILL fallback it tests.

## 2. Marker and cleanup

- [x] 2.1 Add `resources/transcriber-sidecar.marker` (one line naming what it is for) to `transcriber-sidecar.spec`'s `datas` at the bundle root (Decision 2). Rebuild with `build_sidecar.py` and stage it. Verify an unpacked copy of the rebuilt sidecar contains `transcriber-sidecar.marker`, by listing the `_MEI*` folder while a `--file` run is in progress.

  **Done 2026-09-15.** `resources/transcriber-sidecar.marker` (one line) is added to the spec's `datas` at `"."`. Rebuilt with `build_sidecar.py` (exit 0) and copied to `src-tauri/binaries/`. During a `--file` run with `TMPDIR` pointed at a scratch folder, `_MEI000ba0e7VlOIPp/transcriber-sidecar.marker` existed with that line, and the folder was gone after the run exited.

- [x] 2.2 In `sidecar.rs`, add:
  - `stale_extraction_dirs(dir, is_alive)`, which selects directories named `^_MEI[0-9a-f]{8}` containing the marker whose PID isn't alive;
  - `remove_stale_extractions(dir)`, which removes them with `remove_dir_all`, skipping errors, and prints the count to stderr;
  - the per-OS `is_alive`: `pid_alive` on Unix, and on Windows `tasklist` with `CREATE_NO_WINDOW` that counts as alive when `tasklist` fails (Decision 3).

  Unit tests over a temp directory:
  - a dead marked folder is selected;
  - kept: a live marked folder, a dead unmarked folder, a non-`_MEI` folder, and a file named like `_MEI00000001x`;
  - the PID is parsed from the 8 hex digits (`_MEI000b7664m8XSeA` → 751204).

  Verify `cargo test` passes.

  **Done 2026-09-15.** In `sidecar.rs`:
  - `EXTRACTION_MARKER`;
  - `stale_extraction_dirs(dir, is_alive)`: the name must be `_MEI` + 8 ASCII hex digits parsed as the PID, the entry must be a directory, it must contain the marker, and `!is_alive(pid)`;
  - `extraction_owner_alive(pid)`: `pid_alive` on Unix; on Windows `tasklist /FI "PID eq n" /NH /FO CSV` with `CREATE_NO_WINDOW`, looking for `"<pid>"`, and alive if `tasklist` fails;
  - `remove_stale_extractions(dir)`, which removes with `remove_dir_all`, skips errors, and prints the count to stderr.

  `only_this_sidecars_dead_copies_are_stale` selects only the dead marked `_MEI000b7664m8XSeA` (PID 751204). It keeps a live marked folder (PID 2), a dead unmarked one, `_MEIzzzzzzzz…`, a non-`_MEI` folder, and a `_MEI…` *file*. `cargo test` passes. The Windows branch isn't compiled here, since no Windows target is installed on this machine; the release workflow's Windows build compiles it.

- [x] 2.3 Call the cleanup once from `main.rs` `.setup(...)` on `tauri::async_runtime::spawn_blocking`, with `std::env::temp_dir()` (Decision 4). Verify `cargo build` has no warnings. Verify it by hand: create a marked `_MEI` folder named after a dead PID in `/tmp`, start the debug app, and check it's gone while the window opened at once.

  **Done 2026-09-15.** `main.rs` `.setup(...)` runs `remove_stale_extractions(&std::env::temp_dir())` on `spawn_blocking`. `cargo build` has no warnings. Checked by hand in the real `/tmp`, with the debug app:
  - a marked `_MEI<dead pid>manualtest` folder was removed 0.4 s after launch, while the window opened;
  - the unmarked `_MEI<dead pid>unmarked` was kept;
  - stderr printed "Removed 1 leftover sidecar copies from /tmp";
  - no other `_MEI*` folder remained afterwards.

- [x] 2.4 **Stop engines on app exit** (Decision 6, added during apply): move the terminate logic into `end_engine_tree(pid)`, used by `stop_live_session`; add `stop_all_engines(app)`, which takes and ends the live and file children; call it from `RunEvent::Exit` in `main.rs`. Verify `cargo test` and `cargo build` pass. Also verify by hand: start the debug app, begin a file run on a long file, close the window, and check that no `transcriber-sidecar` process remains and the run's `_MEI*` copy is gone.

  **Done 2026-09-15.**
  - **Code:** the Windows `taskkill` logic moves into a shared `taskkill_tree(pid)`, used by `stop_live_session`. `stop_all_engines(app)` marks both sessions inactive, takes the live and file children, and ends each with `terminate_process_tree` on Unix (survivors to stderr) or `taskkill_tree` on Windows. `main.rs` uses `.build(context)` and `.run(|app, event| …)`, calling it on `RunEvent::Exit`. `cargo build` has no warnings, and `cargo test` passes 31.
  - **By hand:** a file run on a 3-hour silent WAV, then closing the WebDriver session, left no engine and no copy. The same happened *without* the exit call, though, so that check doesn't show the handler's effect. A file engine exits on its own once its stdout pipe breaks, which led to Decision 7. The handler's effect on a live session is covered by the user check (5.2).
- [x] 2.5 **Engine stops itself when its stdout reader is gone** (Decision 7, added during apply): in `transcriber.py`, add `_print_or_stop` for transcript lines (file first) and heartbeats. On a broken or closed stdout, it marks a requested stop and interrupts the main thread. Verify a `test_dual_capture.py` scenario, and a repro with the rebuilt frozen engine.

  **Done 2026-09-15.**
  - **Before the fix,** with the frozen engine: `--live --include-mic --heartbeat` with its stdout reader quitting after "Listening..." still ran 25 s later (25 threads, `parec`, copy present).
  - **The fix:** `_print_or_stop` catches `BrokenPipeError` or `ValueError`, sets `_stop_requested` and calls `_thread.interrupt_main()`. `_emit` now writes the transcript file before printing.
  - **New test 3b''** in `test_dual_capture.py`: a stdout whose writes raise `BrokenPipeError` on heartbeats, and a capture loop that swallows `KeyboardInterrupt` like the real ones. The run ends in under 10 s with exit 0, and the transcript keeps `[SYS] hello`. With the heartbeat print reverted to plain `print`, it fails with "the session kept running 20s with nobody reading stdout".
  - **Checks:** all nine root test scripts pass. Rebuilt and staged the sidecar; the same repro now ends about 6 s after the reader leaves, with no process, no `parec` and 0 copies left.

- [x] 2.6 **Ignore a repeat SIGINT during a stop** (Decision 8, added during apply): the engine's SIGINT handler returns once a stop is requested, and `_print_or_stop` leaves the marking to that handler. Verify unit tests, and an app-like repro with the rebuilt engine.

  **Done 2026-09-15.**
  - **Second user check:** the engine stopped correctly on both Stop and quit, but `_MEI000c53019jdD6g` (358 MB, marked, launcher dead) stayed in `/tmp`.
  - **Repro, a Python "app" giving the frozen engine piped stdin, stdout and stderr:**
    - Stop, the old engine: "⚠️ Interrupted by user", then "free(): invalid size", worker and launcher still alive at 16 s, 1 copy left.
    - Stop, with the handler fix: exit 0 in 1.9 s and 2.0 s, 0 copies.
    - Quit, with the first version of the fix: hung for minutes with `parec` still reading. `interrupt_main()` hit the new ignore check because `_print_or_stop` had pre-set the flag.
    - Quit, after fixing that: 3.2 s twice, 0 copies.
  - **Tests** in `test_dual_capture.py`:
    - 3e: a second handler call returns instead of raising (fails without the guard);
    - 3b'' now runs under the engine's real SIGINT handler, and fails with the pre-marking put back ("the session kept running 20s").
  - **Full suite:** 13/13 passed.

## 3. End-to-end

- [x] 3.1 In `tests/test_e2e_linux.py`, give each app its own `TMPDIR` under the scenario directory (in `app_env`). Add `stale extraction cleaned` (Decision 5):
  - pre-create a dead marked, a live marked, a dead unmarked and a non-`_MEI` folder;
  - start the app;
  - wait for only the dead marked folder to disappear.

  Verify it passes, all other scenarios still pass, and it fails with the cleanup call removed from `main.rs`.
- [ ] 3.2 Add `engine stopped on quit` (Decision 6): start a file run on a WAV long enough to still be running, close the app the way a user does, then assert that within `STOP_GRACE` plus margin no engine process started by that app remains and its `TMPDIR` holds no `_MEI*` copy. Verify it passes, and fails with the `RunEvent::Exit` call removed.

  **Done 2026-09-15.** `app_env` gives every app its own `TMPDIR` (`<scenario>/tmp`). `test_stale_extraction_cleaned` pre-creates four entries, starts the app, waits for the stale folder to disappear, then checks the other three one second later:
  - `_MEI<dead pid>stale` with the marker (the dead PID is from a finished `true` process);
  - `_MEI<test's own pid>live` with the marker;
  - `_MEI<dead pid>foreign` without it;
  - `not-an-extraction`.

  Passes, and all 10 end-to-end scenarios pass (exit 0). The real `/tmp` held 0 `_MEI*` folders before and after the suite; the previous run had leaked 7. With the cleanup call replaced in `main.rs` and the app rebuilt, it failed with "timed out waiting for the dead copy to be removed". Reverted and rebuilt.

  A first mutation attempt with `sed` didn't apply (the `||` clashed with its delimiter) and gave a meaningless pass; it was redone with a Python edit.

## 4. Docs

- [x] 4.1 README "Building it yourself" or the Linux download notes: the engine unpacks about 350 MB into the temp directory per run; a normal stop removes it; leftovers from killed runs are removed the next time the app starts. Verify the note exists.

  **Done 2026-09-15.** README "Download and run" → Linux gains a paragraph after the `transcriber-sidecar` note:
  - the engine unpacks about 350 MB into the temporary folder (`/tmp`, often RAM) per run and removes it on exit;
  - Stop allows up to 15 s to finish;
  - leftovers from a quit or a killed engine are removed at the next app start, only this engine's copies and only when unused.

## 5. Verification

- [x] 5.1 Run `.venv/bin/python run_tests.py` with `TRANSCRIBER_TEST_SPEECH` set and a network that reaches GitHub. Verify it exits 0, and that `find /tmp -maxdepth 1 -name '_MEI*'` finds nothing new after the run, since the suite now uses its own `TMPDIR`.

  **Done 2026-09-15.** With `TRANSCRIBER_TEST_SPEECH` set and GitHub reachable: 13/13 suites passed, exit 0. `cargo test` took 24.9 s, including the 15 s grace in the process-tree test. `find /tmp -maxdepth 1 -name '_MEI*'` found 0 before and 0 after; the equivalent run before this change leaked 7.

- [x] 5.2 **User check on Linux** (`cargo tauri dev`): start a live session, speak for a bit, press Stop, and wait for "Not transcribing". Verify `find /tmp -maxdepth 1 -name '_MEI*'` finds nothing. Then quit the app during a session, reopen it, and verify the leftover copy is gone a few seconds after the window opens.

  **User check, first run (2026-09-15), failed:**
  1. **After Stop, `/tmp/_MEI000be019T89Jhh` was left.** The next app start removed it, so the startup cleanup works. The Stop itself didn't let the engine clean up. A CLI repro of a quiet live session stopped cleanly in under 1 s both ways (SIGINT to the launcher only, and to the whole tree with the app's flags). The remaining suspect is speech: after Stop the engine finishes transcribing queued audio, which may exceed the 15 s grace on CPU. Not confirmed.
  2. **After closing the window mid-session,** `_MEI000be84dR2hLrw` belonged to a **still-running, orphaned live engine** (parent `systemd --user`), still capturing. It was stopped with SIGINT (clean in 0.5 s). The root cause and its fixes are tasks 2.4 and 2.5.

  **Full suite after 2.4 and 2.5:** 13/13 passed. One earlier full run had `tests/test_engine.py` fail once, with its output not captured; it passed 5 times alone and in the next full run. Recorded as an unexplained intermittent failure.

  **Done 2026-09-15 (third run).** With the engine rebuilt after task 2.6, the user reported both checks passed:
  1. Stop after speaking: `find /tmp -maxdepth 1 -name '_MEI*'` found nothing.
  2. Closing the window mid-session: no `_MEI*` copy, and no `transcriber-sidecar` process.
