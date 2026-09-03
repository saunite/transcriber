## Why

`add-tauri-gui` task 2.2 ("Freeze the Python engine with PyInstaller for Linux") was left undone because no Linux host was available in that session. A mechanism already exists — `.github/workflows/build-gui.yml`'s `ubuntu-latest` matrix entry runs `build_sidecar.py` on Linux — but it has never actually been triggered or verified; the workflow is still marked `UNVERIFIED` in its own header comment. Until it runs once for real and the resulting Linux sidecar is smoke-tested, "Linux support" is unverified in every place it's claimed (README, workflow comments, `remove-installer-packaging`'s AppImage path, which assumes a working Linux sidecar already exists).

## What Changes

- Trigger `build-gui.yml`'s `ubuntu-latest` job (via `workflow_dispatch` or a qualifying push) and confirm it completes.
- Smoke-test the resulting frozen Linux `transcriber-sidecar` binary standalone (`--list-devices-json`, `--file` on a sample clip) — the same check `add-tauri-gui` task 2.4 already did for Windows — before trusting it's wired correctly into the Tauri Linux bundle.
- Fix whatever the first real run surfaces (the Windows sidecar freeze needed two real fixes — a UTF-8 stdout crash and a missing PyInstaller `--add-data` for faster-whisper's bundled VAD model — that no one could have predicted without actually running it; Linux gets the same treatment).
- Remove the workflow's `UNVERIFIED` header comment once it's confirmed working.

## Capabilities

### New Capabilities
- `linux-sidecar-build`: the CI mechanism that freezes the Python transcription engine into a standalone Linux binary for bundling into the Tauri Linux build.

### Modified Capabilities
(none — desktop-gui's shipped behavior on Windows is unaffected; this only stands up the previously-unverified Linux leg)

## Impact

- Affected: `.github/workflows/build-gui.yml` (the `ubuntu-latest` matrix entry), possibly `build_sidecar.py` or `transcriber.py` if the first real run surfaces a Linux-specific bug (mirroring what happened on Windows).
- No Windows or macOS code paths are touched.
- Unblocks `remove-installer-packaging`'s Linux AppImage path, which currently assumes a working frozen Linux sidecar without that ever having been confirmed.
