## Why

The sidecar is a one-file PyInstaller build. Every run unpacks about 350 MB into a `_MEI<pid><random>` folder in the system temp directory, and the bootloader deletes it when the engine exits. That cleanup doesn't happen when the engine is killed with SIGKILL, which the app does in several places:
- **Stop** escalates to SIGKILL when the engine hasn't exited 3 s after SIGINT, and the engine can easily take longer: it finishes the chunk it is transcribing and joins its worker threads.
- **Quitting the app** mid-session kills the engine.
- **The end-to-end suite** ends apps with signals.

On Linux the temp directory is a RAM-backed tmpfs, so each leak costs memory until reboot. Measured on 2026-09-15: normal exit, SIGINT and SIGTERM remove the folder, SIGKILL leaves it. One end-to-end run leaked 7 copies, and 79 leftover copies (9.3 GB) had filled `/tmp` until test runs failed with "Disk quota exceeded".

## What Changes

- **More time before SIGKILL:** stopping a live session waits up to 15 s after the graceful signal, up from 3 s, while the UI shows "Stopping". The engine usually exits on its own within that window, so the bootloader cleans up. Survivors are still killed and reported as before.
- **Cleanup of dead copies at app start:** in the background, so the window still opens immediately, the shell removes leftover extraction folders in the system temp directory that belong to this app's sidecar and whose bootloader process no longer exists. That covers every way a copy can be leaked: a kill after the grace period, an app quit, a crash, a power loss, or a CLI run of the packaged `transcriber-sidecar` that was killed.
- **Ownership is proven before deleting:** a folder counts only if its name encodes a PID that isn't running and it contains a marker file the sidecar build adds. Other applications' PyInstaller folders, and a copy still used by another running instance, are never touched.
- **Graceful stop when the app quits** (added during apply, 2026-09-15): the user's check found that closing the window mid-session left the live engine running and capturing, orphaned under the user's systemd. The `desktop-gui` spec already requires stopping the engine "on user request or app quit". On exit, the app now stops a running live or file engine the same way Stop does, so the engine ends and removes its own copy.
- **Not in this change:**
  - building the sidecar as a folder, which would avoid extraction altogether;
  - a graceful stop on Windows, where `taskkill /F` still kills immediately (its leftovers are removed at the next start).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `desktop-gui`: added "The engine does not leave its unpacked copy behind", covering the longer graceful stop, the graceful stop on app quit, and startup removal of dead extraction folders owned by the app's sidecar.

## Impact

- **`src-tauri/src/sidecar.rs`:** a stop grace constant of 15 s, and a pure `stale_extraction_dirs(entries, is_alive)` selector with unit tests. A cleanup runs once from the app's setup on a background task.
- **`transcriber-sidecar.spec`:** adds a marker file to the bundle's data files, so the sidecar must be rebuilt. `main.rs` calls the cleanup at setup.
- **`tests/test_e2e_linux.py`:** a scenario where a started app removes a dead, marked folder but keeps a live one and an unmarked one. The suite gives each app its own `TMPDIR`, so it never scans the real `/tmp`.
- **README:** a note on where the sidecar unpacks, and that leftovers are cleaned at the next start.
- **No new dependencies.**
