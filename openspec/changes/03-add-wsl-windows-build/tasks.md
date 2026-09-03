## 1. Toolchain setup

- [ ] 1.1 (Depends on `02` task 1.1) Add the mingw cross-toolchain: `apt install gcc-mingw-w64-x86-64 binutils-mingw-w64-x86-64`, `rustup target add x86_64-pc-windows-gnu`, and verify `cargo tauri build --target x86_64-pc-windows-gnu --help` runs with no missing-linker error
- [ ] 1.2 Confirm the existing `.venv/Scripts/python.exe` (or a freshly created equivalent) is reachable from WSL via `shutil.which("python.exe")` and has every sidecar dependency installed (`faster_whisper`, `PyInstaller`, `pyaudiowpatch`, `sounddevice`, `av`) — document how to create this venv from scratch if it doesn't already exist on a given machine

## 2. Interop-guarded sidecar freeze

- [ ] 2.1 Add an interop guard to the sidecar-freeze step (in `build_sidecar.py` or its caller): probe `shutil.which("python.exe")` before invoking it, and exit with a clear message ("no Windows Python interpreter reachable — Windows sidecar build skipped/failed") when absent
- [ ] 2.2 Run the guarded freeze from WSL against the real venv and confirm it produces `dist/windows/transcriber-sidecar.exe`
- [ ] 2.3 Verify the guard fires correctly when no Windows Python is reachable (e.g. temporarily rename/hide `python.exe` from `PATH`, confirm the clear failure message, then restore)

## 3. build_portable.py dispatch fix

- [ ] 3.1 Change `main()`'s dispatch to branch on the `--target` triple's platform substring when `--target` is given, falling back to `platform.system()` only when it is not; verify with `--target x86_64-pc-windows-gnu` run under WSL's own Python that it now takes the Windows branch (not Linux)
- [ ] 3.2 Verify the no-`--target` fallback still calls the correct per-host branch unchanged (i.e. this is a pure addition, not a regression) — run `build_portable.py` with no `--target` on this Linux/WSL machine and confirm it still takes the Linux branch as before

## 4. End-to-end verification

- [ ] 4.1 From WSL: `cargo tauri build --target x86_64-pc-windows-gnu`, then the interop sidecar freeze, then `fetch_sidecar_resources.py`, then `build_portable.py --target x86_64-pc-windows-gnu` — confirm `dist/portable/Transcriber.zip` is produced with the correct internal layout (same check `remove-installer-packaging` task 2.6 already partially did)
- [ ] 4.2 Extract the produced zip on a Windows machine and confirm it runs and transcribes — same end-to-end check needed regardless of build mechanism (moved fully to `05-remove-installer-packaging-windows`, which owns Windows-hardware verification; this task exists here only to confirm the WSL-built artifact reaches that point, not to duplicate the hardware test)
