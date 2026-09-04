## 1. Toolchain setup

- [x] 1.1 (Depends on `02` task 1.1) Add the mingw cross-toolchain: `apt install gcc-mingw-w64-x86-64 binutils-mingw-w64-x86-64`, `rustup target add x86_64-pc-windows-gnu`, and verify `cargo tauri build --target x86_64-pc-windows-gnu --help` runs with no missing-linker error

  `rustup target add x86_64-pc-windows-gnu` done (no root needed). `gcc-mingw-w64-x86-64`/`binutils-mingw-w64-x86-64` needed `sudo` (same blocker as `02` task 1.1); user ran the install from a real terminal. **Verified for real**: `dpkg -s` confirms both installed, `x86_64-w64-mingw32-gcc` is on `PATH`, and `cargo tauri build --target x86_64-pc-windows-gnu --help` exits 0 with no missing-linker error.
- [x] 1.2 Confirm the existing `.venv/Scripts/python.exe` (or a freshly created equivalent) is reachable from WSL via `shutil.which("python.exe")` and has every sidecar dependency installed (`faster_whisper`, `PyInstaller`, `pyaudiowpatch`, `sounddevice`, `av`) — document how to create this venv from scratch if it doesn't already exist on a given machine

  **Real finding, changed the approach (see design.md):** `shutil.which("python.exe")` resolves to the Windows Store's stub launcher (`.../WindowsApps/python.exe`, Python 3.13) on this machine — a real, executable interpreter, but with none of the sidecar dependencies. A guard based on it would give a false positive. Switched to checking the specific `.venv/Scripts/python.exe` path directly. Verified: that path exists, is executable, and imports all five dependencies (`faster_whisper`, `PyInstaller`, `pyaudiowpatch`, `sounddevice`, `av`) successfully. From-scratch venv creation documented in README (`python.exe -m venv .venv` + `pip install -r requirements.txt pyinstaller`).

## 2. Interop-guarded sidecar freeze

- [x] 2.1 Add an interop guard to the sidecar-freeze step (in `build_sidecar.py` or its caller): probe `shutil.which("python.exe")` before invoking it, and exit with a clear message ("no Windows Python interpreter reachable — Windows sidecar build skipped/failed") when absent

  Implemented as documented in README rather than a new script (matches `02`'s style — no orchestration script exists for this path, and the guard is a 3-line shell pre-flight check, not enough logic to justify a new file): `[ -x .venv/Scripts/python.exe ] || { echo "ERROR: ..." >&2; exit 1; }` before invoking the freeze. Per 1.2's finding, checks the specific venv path, not a generic `PATH` lookup.
- [x] 2.2 Run the guarded freeze from WSL against the real venv and confirm it produces `dist/windows/transcriber-sidecar.exe`

  **Verified for real**: the guarded freeze (`./.venv/Scripts/python.exe build_sidecar.py`, guard passing) ran via WSL-to-Windows interop and produced `dist/windows/transcriber-sidecar.exe` (126MB) — confirmed via `file`: a genuine `PE32+ executable for MS Windows 6.00 (console), x86-64`. Staged into `src-tauri/binaries/transcriber-sidecar-x86_64-pc-windows-gnu.exe` for the cross-compile build (task 4.1).
- [x] 2.3 Verify the guard fires correctly when no Windows Python is reachable (e.g. temporarily rename/hide `python.exe` from `PATH`, confirm the clear failure message, then restore)

  Verified for real (adapted to the corrected check — the specific venv path, not `PATH`): temporarily renamed `.venv/Scripts/python.exe`, confirmed the guard's error message fires, restored it and confirmed the file is present and executable again.

## 3. build_portable.py dispatch fix

- [x] 3.1 Change `main()`'s dispatch to branch on the `--target` triple's platform substring when `--target` is given, falling back to `platform.system()` only when it is not; verify with `--target x86_64-pc-windows-gnu` run under WSL's own Python that it now takes the Windows branch (not Linux)

  Implemented and verified via unit-level test (mocking `build_windows`/`build_linux`, real `main()` dispatch logic): `--target x86_64-pc-windows-gnu` calls `build_windows`, not `build_linux`, despite `platform.system()` reporting `"Linux"` on this WSL machine.
- [x] 3.2 Verify the no-`--target` fallback still calls the correct per-host branch unchanged (i.e. this is a pure addition, not a regression) — run `build_portable.py` with no `--target` on this Linux/WSL machine and confirm it still takes the Linux branch as before

  Verified in the same test pass: no `--target` given → falls back to `platform.system()` → `build_linux`, unchanged from before the fix.

## 4. End-to-end verification

- [x] 4.1 From WSL: `cargo tauri build --target x86_64-pc-windows-gnu`, then the interop sidecar freeze, then `fetch_sidecar_resources.py`, then `build_portable.py --target x86_64-pc-windows-gnu` — confirm `dist/portable/Transcriber.zip` is produced with the correct internal layout (same check `remove-installer-packaging` task 2.6 already partially did)

  **Verified for real**, full pipeline from `~/repos/transcriber` (ext4): `cargo tauri build --target x86_64-pc-windows-gnu` completed in **1m41.4s**, no bundling attempted (correct — no Windows bundle target configured, matching `remove-installer-packaging` task 1.2's finding), producing `transcriber-gui.exe` (23.5MB), `WebView2Loader.dll` (160KB, statically-linked-target sibling file), plus the staged `transcriber-sidecar.exe` (from task 2.2's freeze) in the release dir. Model already staged, `fetch_sidecar_resources.py` skipped. `build_portable.py --target x86_64-pc-windows-gnu` correctly took the Windows branch (real end-to-end confirmation of task 3.1's dispatch fix, not just the mocked unit test) and produced `dist/portable/Transcriber.zip` (264.8MB) with the exact expected layout: `Transcriber/{transcriber-gui.exe, transcriber-sidecar.exe, WebView2Loader.dll, resources/model/{model.bin, config.json, tokenizer.json, vocabulary.txt}}`.
- [x] 4.2 Extract the produced zip on a Windows machine and confirm it runs and transcribes — same end-to-end check needed regardless of build mechanism (moved fully to `05-remove-installer-packaging-windows`, which owns Windows-hardware verification; this task exists here only to confirm the WSL-built artifact reaches that point, not to duplicate the hardware test)

  Confirmed reached: 4.1 produced a real `Transcriber.zip` with the correct layout, ready for `05-remove-installer-packaging-windows`'s hardware verification. The actual "extract and run on Windows" check is that change's task 2.4, not repeated here.
