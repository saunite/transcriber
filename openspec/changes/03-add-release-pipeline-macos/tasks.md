## 1. Helper bundling and signing

- [ ] 1.1 In `build_sidecar.py`, on Darwin, exit non-zero with a clear message when `macos/audiotap-helper/audiotap-helper` is missing; otherwise add it with `--add-binary …:macos/audiotap-helper` (design.md Decision 2). Verify that the Linux leg from `01` stays green, since the non-Darwin path must be unchanged, and verify on the macOS leg as 2.2 describes.
- [ ] 1.2 Add `bundle.macOS.signingIdentity: "-"` to `src-tauri/tauri.conf.json`. Verify in the macOS leg's log that `codesign -dv` on the built `.app` reports an ad-hoc signature.
- [ ] 1.3 Give `mac-start-transcription.sh` the bundled-binary fallback, mirroring `linux-start-transcription.sh` from `01` task 1.3. Verify with `bash -n` and a side-by-side diff against the Linux launcher. The only differences should be the platform flags already present today.

## 2. macOS leg in `release.yml`

- [ ] 2.1 On `macos-latest`: set up Python 3.14 with a venv containing `requirements-macos.txt` and `pyinstaller`, run `macos/audiotap-helper/build.sh`, then `build_sidecar.py`, staged as `src-tauri/binaries/transcriber-sidecar-aarch64-apple-darwin`, then `fetch_sidecar_resources.py`, then the smoke test from `01`. Verify that the smoke-test step passes in the run log.
- [ ] 2.2 List the frozen sidecar's contents with `pyi-archive_viewer` and fail the leg unless `macos/audiotap-helper/audiotap-helper` is present. Verify it passes. Then, in a scratch run that skips `build.sh`, confirm the freeze itself fails with the missing-helper message (1.1).
- [ ] 2.3 Run `npx --yes @tauri-apps/cli@<pinned> build --bundles app,dmg`, then `hdiutil verify` on the `.dmg`, then `build_portable.py` for the zipped `.app` and the CLI `.tar.gz`, and upload all three (release on tag runs, artifact on dispatch runs). Also run `codesign -dv` on the CLI binary and record the result. Verify with a `workflow_dispatch` run that all three are downloadable.

## 3. Documentation

- [ ] 3.1 Fill in README's macOS download subsection:
  - "Built automatically on Apple Silicon GitHub runners, but untested on real hardware. Testers welcome." Link to the issue tracker, and name the specific open questions: does the `.dmg` or the zipped `.app` open after Open Anyway; does file transcription work in the GUI; does `--coreaudio-tap` live capture work from the CLI.
  - Arm64 only.
  - System Settings → Privacy & Security → Open Anyway, replacing the stale right-click → Open text.
  - `xattr -d com.apple.quarantine ./transcriber` for the CLI.
  - macOS 14.4 or later for CLI system-audio capture.

  Verify that the stale right-click instruction no longer appears anywhere in the README.
- [ ] 3.2 Record here, for whoever tests first, `06-remove-installer-packaging-macos`'s untested items that this change inherits: GUI file transcription from the `.app`, and Gatekeeper behavior of a downloaded (quarantined) copy. Verify that both appear in the README testers call from 3.1.
