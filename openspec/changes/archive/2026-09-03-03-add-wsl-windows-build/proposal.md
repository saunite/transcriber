## Why

Windows is the priority artifact. The Windows build has two halves with different portability: the Tauri shell cross-compiles cleanly via `rustc`'s `x86_64-pc-windows-gnu` target, but the sidecar is a PyInstaller freeze, and PyInstaller does not cross-compile — it must run under a genuine Windows Python (`docker/build.ps1` never actually solved this either; `src-tauri/binaries/transcriber-sidecar-x86_64-pc-windows-gnu.exe` was built by running `build_sidecar.py` under a real Windows Python outside the container). This change reproduces both halves without Docker: the mingw cross-compile runs directly in WSL, and the PyInstaller freeze runs via WSL's ability to execute Windows `.exe` binaries directly against the repo's existing Windows Python venv — confirmed working on this machine. Builds on `02-add-wsl-linux-build`'s toolchain setup.

## What Changes

- Add the `x86_64-pc-windows-gnu` mingw cross-compile toolchain to the WSL environment (`rustup target add x86_64-pc-windows-gnu`, `apt install gcc-mingw-w64-x86-64 binutils-mingw-w64-x86-64`), building on `02`'s base Rust/tauri-cli install.
- Freeze the Windows sidecar via interop: invoke the existing Windows Python venv's interpreter (`./.venv/Scripts/python.exe build_sidecar.py`) from WSL — WSL can execute Windows `.exe` binaries directly, and this venv already has every sidecar dependency installed, confirmed working. Guard this step by checking for that specific `.venv/Scripts/python.exe` path (existence + executable), not a generic `PATH` lookup — `shutil.which("python.exe")` was tried first and rejected: on this machine it resolves to the Windows Store's stub launcher, a real interpreter with none of the sidecar dependencies, which would make the guard pass and then fail confusingly inside the freeze itself.
- Fix `build_portable.py`'s platform dispatch: `main()` currently branches on `platform.system()` of the *running interpreter*, so invoking it from WSL (Linux) with `--target x86_64-pc-windows-gnu` takes the Linux branch and looks for an AppImage instead of the Windows files. Dispatch on the `--target` triple when one is given (its substring already names the platform unambiguously), falling back to `platform.system()` only when no target is passed. Note: `build_windows()` itself is pure file-copying (`shutil.copy2`, `zipfile`) — it needs no Windows execution, only correct dispatch, so no interop is needed for this step, only for the PyInstaller freeze above.
- Windows artifact assembly (`fetch_sidecar_resources.py`, `build_portable.py --target x86_64-pc-windows-gnu`) runs the same as it does today, unchanged, now driven from a WSL shell instead of `docker/build.ps1`.

## Capabilities

### New Capabilities
- `wsl-windows-build`: native (containerless) cross-compile of the Windows desktop artifact, including the Windows sidecar freeze, from a WSL environment.

### Modified Capabilities
(none — `docker-build`'s requirements are retired in `04-remove-ci-and-container-builds`, once this change and `02` both prove their replacements work)

## Impact

- **Changed**: `build_portable.py` (`main()`'s dispatch logic; `_release_dir()` already fixed in `02` to honor `CARGO_TARGET_DIR`, reused here unchanged).
- **New**: WSL mingw toolchain setup (documented, same style as `02`'s), a documented interop invocation for the sidecar freeze.
- **Unaffected**: `docker/`, `.github/workflows/` (removed in `04`), all Python/Rust application code, `src-tauri/binaries/transcriber-sidecar-x86_64-pc-windows-gnu.exe` (still produced the same way, just via a different driving process).
- **Depends on**: `02-add-wsl-linux-build` for the base Rust/tauri-cli toolchain and `CARGO_TARGET_DIR` setup — this change only adds the Windows-specific pieces on top.
