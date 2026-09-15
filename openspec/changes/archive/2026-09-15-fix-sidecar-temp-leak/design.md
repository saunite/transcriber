## Context

- **Build:** `transcriber-sidecar.spec` builds a one-file `EXE` with `runtime_tmpdir=None` (PyInstaller 6.22.2), so the bootloader unpacks into the OS temp directory: `TMPDIR` or `/tmp` on POSIX, `%TEMP%` on Windows. `std::env::temp_dir()` resolves the same way.
- **Folder name,** verified on 2026-09-15: `_MEI` + the **bootloader process's PID as 8 lowercase hex digits** + a random suffix. Parent PID 751204 gave `_MEI000b7664m8XSeA`.
- **Which endings clean up,** measured with a signalled file run: normal exit, SIGINT and SIGTERM remove the folder, because the bootloader waits for its child and then deletes it. SIGKILL leaves it.
- **Stop:** `sidecar.rs` `terminate_process_tree(pid)` sends SIGINT to the worker and the bootloader, polls `pid_alive` for up to **3 s**, then SIGKILLs survivors. Windows `stop_live_session` uses `taskkill /F /T`, an immediate kill.
- **Engine shutdown after SIGINT:** close the mic (bounded at 5 s), stop the capture, join both workers (up to 60 s each, only while a chunk is mid-inference), close the transcript. With the base model on CPU a chunk takes a few seconds; larger models take longer.
- **Exit:** `main.rs` has no setup hook or exit handling. `tauri-plugin-shell` does **not** end spawned children when the app exits; the user's check found a live engine still capturing after the window was closed (Decision 6).

## Goals / Non-Goals

**Goals:**
- A normal Stop leaves no unpacked copy behind.
- Every copy leaked some other way is gone after the next app start, without ever touching a live copy or another app's folder.

**Non-Goals:**
- Replacing the one-file build with a folder build.
- A graceful engine stop on Windows, where the stop is still `taskkill /F`. Its leftovers are covered by the startup cleanup.
- Cleaning folders under a different temp directory than the app's own `std::env::temp_dir()`.

## Decisions

### 1. Stop grace: 15 s before SIGKILL
`terminate_process_tree` waits `STOP_GRACE = 15 s` instead of 3 s. The page already shows "Stopping" and keeps Stop disabled while it waits, so a longer wait is visible, not mysterious. 15 s covers the 5 s mic bound plus a chunk mid-inference on the bundled model with margin. A process that exits earlier ends the wait immediately, since the loop polls every 100 ms.

- *Alternative:* make the engine skip the in-flight chunk on SIGINT. That changes what a stopped transcript contains, against the "graceful stop preserves the transcript" scenario. Rejected.

### 2. Ownership: a marker file bundled into the sidecar
The spec adds `resources/transcriber-sidecar.marker`, a one-line text file, to `datas` at the bundle root, so every unpacked copy of *this* sidecar contains `transcriber-sidecar.marker`. A folder without it is never considered, whatever its name.

- *Alternative:* identify our copies by content, such as `faster_whisper/assets`. Other apps can bundle the same library. Rejected.
- *Alternative:* a dedicated extraction folder through the `TMPDIR` environment variable. It changes where every run unpacks and doesn't cover the packaged CLI run directly. Rejected for now.

### 3. Pure selection, platform-specific liveness
`stale_extraction_dirs(dir: &Path, is_alive: impl Fn(u32) -> bool) -> Vec<PathBuf>` lists entries that are directories named `^_MEI[0-9a-f]{8}`, contain the marker file, and whose parsed PID is not alive. Liveness:
- **Unix:** the existing `pid_alive` (`ps -o stat=`). A zombie counts as dead, which is correct: a zombie holds no open files.
- **Windows:** `tasklist /FI "PID eq <n>" /NH /FO CSV` with `CREATE_NO_WINDOW`, the same no-console pattern as `taskkill`. If `tasklist` itself fails, the folder counts as **alive**, so nothing is removed on uncertainty.

A reused PID (a dead bootloader's number now owned by an unrelated process) reads as alive and the folder is kept until a later start. That errs toward keeping.

- **Platform rule:** this stays one change. The only per-OS code is the few lines of `is_alive`, which already exist in `sidecar.rs` for stopping; the selection, the marker and the cleanup are shared.

### 4. Cleanup runs once, off the UI path
`main.rs` gains `.setup(|app| { spawn_blocking(|| sidecar::remove_stale_extractions(&std::env::temp_dir())); Ok(()) })`. Removal uses `std::fs::remove_dir_all`, and each failure is skipped. The count removed goes to stderr, which is visible in `tauri dev`. The window never waits for it (specs/desktop-gui "Fast, non-blocking app open").

### 6. Stop running engines when the app exits (added during apply)
The user's Linux check found a live engine still running under `systemd --user` after closing the window mid-session. `tauri-plugin-shell` doesn't end children on exit, so the engine kept capturing, and its copy stayed in use. `main.rs` switches from `.run(context)` to `.build(context)?.run(|app, event| …)`, and on `RunEvent::Exit` calls `sidecar::stop_all_engines(app)`. That takes the live and file children out of `SidecarManager` and ends each one the way Stop does: `terminate_process_tree` on Unix (SIGINT, `STOP_GRACE`, SIGKILL fallback), `taskkill /F /T` on Windows. The terminate/`taskkill` logic moves out of `stop_live_session` into a shared `end_engine_tree(pid) -> Vec<u32>`, used by both. Exit blocks for at most `STOP_GRACE` after the window has already closed.

- *Alternative:* `RunEvent::ExitRequested` with `prevent_exit`, then exiting after the stop. It adds a second exit path for no visible benefit, since the window is gone either way. Rejected.

### 7. The engine stops itself when nobody reads its output (added during apply)
Found while verifying Decision 6. The app reads the engine's stdout; when the app goes away (closed, crashed, killed) that pipe breaks. A live engine prints transcript lines and heartbeats from its **worker threads**, so the failing `print` killed only that thread while the main capture loop kept recording. Reproduced with the frozen engine and a stdout reader that quit after "Listening...": 25 s later the engine still ran with 25 threads and `parec`, and its copy was in use. A file run prints from the main thread, so it exited instead, which is why a file run can't show the orphan.

`transcriber.py` gains `_print_or_stop(line)`, used for transcript lines (written to the file **before** printing) and heartbeats. On `BrokenPipeError` or a closed stdout, it marks a requested stop and raises `KeyboardInterrupt` in the main thread (`_thread.interrupt_main()`), which takes the normal graceful stop: the transcript is kept, exit 0, and the bootloader removes the copy. With `--heartbeat` the engine notices within about one chunk. This covers the crash and kill cases where `RunEvent::Exit` never runs; Decision 6 stays for an immediate stop on a normal quit.

### 8. A repeat SIGINT during a stop is ignored (added during apply)
The second user check found the copy still left after both Stop and quit, even though the engine now stopped. Reproduced with a Python stand-in for the app that gives the engine piped stdin, stdout and stderr like `tauri-plugin-shell`, then signals it like Stop.
- **Why it leaked:** Stop sends SIGINT to the worker, `parec` and the launcher, and the launcher forwards its SIGINT to the worker, so the worker gets it twice. The second `KeyboardInterrupt` landed mid-cleanup ("⚠️ Interrupted by user"), abandoned the worker joins, and the interpreter crashed on exit with native threads still running ("free(): invalid size"). The abort outlasted the 15 s grace, SIGKILL followed, and the launcher never deleted the copy.
- **Fix:** the engine's SIGINT handler returns immediately once `_stop_requested` is set, so the forwarded duplicate, or a double Ctrl+C, is harmless.
- **Consequence for Decision 7:** `_thread.interrupt_main()` runs that same handler, so the broken-pipe guard must not pre-set the flag, or its own interrupt is ignored as a repeat. That was found in the same repro, when a quit hung. The handler now marks the stop itself.

The shell's signalling is unchanged.

### 5. Tests
- **`cargo test`:**
  - `stale_extraction_dirs` against a temp directory holding a dead marked folder (selected), a live marked folder (kept), a dead unmarked folder (kept), a non-`_MEI` folder (kept), and a file named `_MEI…` (kept);
  - the grace: `terminate_process_tree` on `sh -c 'trap "sleep 5; exit 0" INT; sleep 60'` returns no survivors, and the process exited by itself (exit code 0, not killed by signal 9).
- **End-to-end:** each app gets `TMPDIR` under the scenario directory. `stale extraction cleaned` pre-creates the four folders from the unit test, using a PID from a finished `true` process as "dead" and the test's own PID as "alive", then starts the app and waits for only the dead marked folder to disappear.

## Risks / Trade-offs

- **A stuck engine now takes up to 15 s to stop instead of 3.** → The UI already shows "Stopping", and an engine that stops cleanly returns as soon as it has exited.
- **Deleting in a shared temp directory.** → A folder is removed only with all three proofs: the `_MEI` name pattern, our marker, and a dead PID. It's our own user's temp dir, and removal errors are ignored.
- **Existing leftovers from builds without the marker aren't cleaned.** → Once only. The folders already seen here were removed by hand, and new builds carry the marker.
- **A PyInstaller upgrade could change the folder naming.** → The unit test pins the pattern, and the end-to-end scenario uses the real app. A naming change makes cleanup a no-op, never a wrong deletion, because the marker is still required.

## Migration Plan

- The sidecar must be rebuilt to include the marker. Older staged builds simply aren't cleaned.
- Rollback: revert. Nothing persists.
