## Why

`01-add-release-pipeline` creates the release workflow with a Linux leg. The Windows leg needs its own implementation: a GNU (mingw-w64) toolchain on a Windows runner, a per-user NSIS installer, and batch-file launchers. Per the project's platform-split rule, those belong in their own change. Installing without administrator rights matters to the user, so the installer has to be per-user.

## What Changes

- **Windows leg in `release.yml`** on `windows-latest`:
  - Freeze the sidecar with python.org Python and `requirements.txt`.
  - Build the Tauri shell for `x86_64-pc-windows-gnu` with a **GNU host toolchain**, so the Rust side of the build runs entirely on open-source tools, the same target triple as the local WSL build.
  - Produce the NSIS installer, then run `build_portable.py` for the portable zip and the CLI zip.
  - Smoke-test the sidecar and upload.
- **Per-user NSIS installer:** `bundle.windows.nsis.installMode: "currentUser"`. It installs into the user's profile with no UAC prompt, and adds a Start Menu entry and an uninstaller.
- **Windows launchers prefer the bundled binary:** `win-start-transcription.bat` and `transcribe_file.bat` run `transcriber.exe` when it sits next to them, and otherwise fall back to Python as today.
- **README Windows download instructions:** the installer, the portable zip, the CLI zip, and the SmartScreen prompt for unsigned files.
- **Takes over the clean-machine check** moved from `05-remove-installer-packaging-windows` task 2.4, now run against CI-built artifacts, together with the installer's non-admin install check.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `release-build`: adds the Windows release-artifacts requirement.
- `desktop-gui`: adds the requirement that the Windows installer installs per-user without administrator rights.
- `teams-launcher`: "Launcher prints the literal command instead of a banner" names `python transcriber.py` literally in its scenario, so it's updated to allow the bundled `transcriber.exe` command.

## Impact

- **Changed**:
  - `.github/workflows/release.yml`: Windows leg.
  - `src-tauri/tauri.conf.json`: `bundle.windows.nsis`.
  - `win-start-transcription.bat`, `transcribe_file.bat`.
  - `README.md`.
- **Unchanged**: the local WSL Windows build (`wsl-windows-build`), `src-tauri/.cargo/config.toml` (the same mingw linker setting serves both paths), and all Rust and Python application code.
- **Depends on**: `01-add-release-pipeline`.
