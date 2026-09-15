## Context

- **Build:** `transcriber-sidecar.spec` builds a one-file `EXE` with `runtime_tmpdir=None` (PyInstaller 6.22.2), so the bootloader unpacks into the OS temp directory: `TMPDIR` or `/tmp` on POSIX, `%TEMP%` on Windows. `std::env::temp_dir()` resolves the same way.
- **Folder name,** verified on 2026-09-15: `_MEI` + the **bootloader process's PID as 8 lowercase hex digits** + a random suffix. Parent PID 751204 gave `_MEI000b7664m8XSeA`.
- **Which endings clean up,** measured with a signalled file run: normal exit, SIGINT and SIGTERM remove the folder, because the bootloader waits for its child and then deletes it. SIGKILL leaves it.
- **Stop:** `sidecar.rs` `terminate_process_tree(pid)` sends SIGINT to the worker and the bootloader, polls `pid_alive` for up to **3 s**, then SIGKILLs survivors. Windows `stop_live_session` uses `taskkill /F /T`, an immediate kill.
- **Engine shutdown after SIGINT:** close the mic (bounded at 5 s), stop the capture, join both workers (up to 60 s each, only while a chunk is mid-inference), close the transcript. With the base model on CPU a chunk takes a few seconds; larger models take longer.
- **Exit:** `main.rs` has no setup hook or exit handling, and `tauri-plugin-shell` kills spawned children when the app exits.

## Goals / Non-Goals

**Goals:**
- A normal Stop leaves no unpacked copy behind.
- Every copy leaked some other way is gone after the next app start, without ever touching a live copy or another app's folder.

**Non-Goals:**
- Replacing the one-file build with a folder build.
- A graceful engine stop on app quit, or on Windows. Their leftovers are covered by the startup cleanup.
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
