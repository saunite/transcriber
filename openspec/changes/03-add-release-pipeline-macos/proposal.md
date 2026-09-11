## Why

No Mac is available, so a GitHub-hosted macOS runner is the only way to build macOS artifacts at all. Exploration also turned up a real packaging gap. `macos_capture.py` looks for its Swift `audiotap-helper` next to the Python module, but `build_sidecar.py` never bundles the helper into the frozen binary. So the standalone macOS CLI's `--coreaudio-tap`, its main reason to exist on a Mac, can't find the helper. The macOS artifacts will ship for Apple Silicon only, ad-hoc signed and untested, with an open call for testers.

## What Changes

- **macOS leg in `release.yml`** on `macos-latest` (Apple Silicon): build the Swift helper, freeze the sidecar with the helper inside it, smoke-test, build the `.app` and `.dmg`, then run `build_portable.py` for the zipped `.app` and the CLI `.tar.gz`, and upload.
- **`build_sidecar.py` bundles `audiotap-helper` on macOS** at the path `macos_capture.py` resolves, and fails the macOS freeze if the helper hasn't been built.
- **Ad-hoc signing** of the app bundle (`bundle.macOS.signingIdentity: "-"`). It needs no Apple account, and Apple Silicon requires a valid signature (see design.md).
- **`mac-start-transcription.sh` prefers the bundled binary**, falling back to Python as today.
- **README macOS section:**
  - The artifacts are built automatically but untested on real hardware, and testers are welcome.
  - Arm64 only.
  - Opening an unsigned app now goes through System Settings → Privacy & Security → Open Anyway. That replaces the stale right-click → Open advice, which no longer works on macOS 15 and later.
  - The CLI needs `xattr -d com.apple.quarantine` after download.
- **Carries over `06-remove-installer-packaging-macos`'s untested gaps** (file transcription through the GUI, and a downloaded copy's Gatekeeper behavior) into the testers call.
- **Out of scope:**
  - Intel or universal builds.
  - Developer ID signing and notarization (no paid Apple account).
  - Enabling GUI live capture on macOS. It stays disabled per `desktop-gui` "Graceful macOS degradation", so the helper fix benefits the CLI now and the GUI later.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `release-build`: adds a macOS release-artifacts requirement (including the untested notice) and the requirement that the macOS standalone CLI carries its audio-tap helper.

## Impact

- **Changed**:
  - `.github/workflows/release.yml`: macOS leg.
  - `build_sidecar.py`: the helper as an added binary on macOS.
  - `src-tauri/tauri.conf.json`: `bundle.macOS.signingIdentity`.
  - `mac-start-transcription.sh`.
  - `README.md`.
- **Unchanged**: `macos_capture.py`, since its relative-path lookup already matches the bundled location, and `macos/audiotap-helper/` sources.
- **Depends on**: `01-add-release-pipeline`.
