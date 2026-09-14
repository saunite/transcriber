## 1. Helper bundling and signing

- [x] 1.1 In `build_sidecar.py`, on Darwin, exit non-zero with a clear message when `macos/audiotap-helper/audiotap-helper` is missing; otherwise add it with `--add-binary …:macos/audiotap-helper` (design.md Decision 2). Verify that the Linux leg from `01` stays green, since the non-Darwin path must be unchanged, and verify on the macOS leg as 2.2 describes.

  **Implemented 2026-09-13; local half verified, CI half open.** The mechanism differs from the task text, for a reason outside this change. Since `fix-linux-live-capture-alsa`, the sidecar is frozen from `transcriber-sidecar.spec`, and a spec-based build ignores command-line flags such as `--add-binary`. So the helper is added in the spec's `Analysis(binaries=…)` on Darwin, packed at `macos/audiotap-helper/` to match `macos_capture._HELPER_RELATIVE_PATH = macos/audiotap-helper/audiotap-helper`. The missing-helper guard stays in `build_sidecar.py` and runs before PyInstaller does. The behaviour the spec requires is unchanged: the helper is inside the executable, and the build fails without it. design.md Decision 2 records the change.
  - **Simulated macOS run, missing helper:** running `build_sidecar.py` with `platform.system()` forced to `Darwin` exits **1** with `ERROR: the macOS audio-tap helper has not been built (…/macos/audiotap-helper/audiotap-helper is missing). Run macos/audiotap-helper/build.sh first…`. Neither `dist/darwin` nor `build/darwin` was created, so PyInstaller never started.
  - **Linux path unchanged in effect:** a Linux rebuild exits 0. `EXE-00.toc` has **0** `audiotap` entries and PyAV's `av.libs/libasound` is still packed, while the top-level `libasound.so.2` stays excluded. `pyi-archive_viewer -l` also lists no `audiotap` entry.
  - **Still open:** the helper actually being inside the macOS binary, which 2.2's listing checks in CI.
  - **CI half verified, 2026-09-14** (`workflow_dispatch` run 34856241319 on `main` at `6c33bd5`, runner image `macos-26-arm64`, all four jobs green; the macOS job took 3m53s): the listing step printed `28557180, 13527, 92912, 1, 'b', 'macos/audiotap-helper/audiotap-helper'`, so the helper is inside the binary. The same entry is present in the CLI binary inside the downloaded `transcriber-cli_0.1.0_macos-arm64.tar.gz`, listed with `pyi-archive_viewer -l` on Linux.
- [x] 1.2 Add `bundle.macOS.signingIdentity: "-"` to `src-tauri/tauri.conf.json`. Verify in the macOS leg's log that `codesign -dv` on the built `.app` reports an ad-hoc signature.

  **Implemented 2026-09-13; CI verification open.** `bundle.macOS.signingIdentity: "-"` is in `src-tauri/tauri.conf.json`. The key is real: tauri-utils 2.9.3's `MacConfig` has `signing_identity`, serialised under `"macOS"` (alias `"macos"`). The JSON parses and `cargo check` accepts it. The macOS job runs `codesign -dv` on the built `.app`, which is where the ad-hoc signature is confirmed.
  **Verified 2026-09-14** (`workflow_dispatch` run 34856241319 on `main` at `6c33bd5`, runner image `macos-26-arm64`, all four jobs green; the macOS job took 3m53s). Tauri logged `Signing with identity "-"`, re-signing the bundled sidecar and then the app. After `build_portable.py` copied the notices in, `codesign -dv` on `Transcriber.app` reported `Signature=adhoc`, `flags=0x10002(adhoc,runtime)`, `Sealed Resources version=2 rules=13 files=10`, and `codesign --verify --deep --strict` passed, so the post-signing copy did not break the seal. Tauri skipped notarization, as expected with no Apple credentials.
  **Added beyond the task text:** `build_portable.py`'s `build_macos` copies the licence notices into `Transcriber.app/Contents/Resources` *after* Tauri has signed the bundle, which can invalidate the signature. On Apple Silicon that shows as "damaged", with no Open Anyway path. It is expected to hold, because Tauri's `bundle.resources` already places identical notice files at those paths and a signature seals file contents, not timestamps. Rather than rely on that, the job runs `codesign --verify --deep --strict` on the app after assembly, so a broken seal fails the run instead of shipping.
- [x] 1.3 Give `mac-start-transcription.sh` the bundled-binary fallback, mirroring `linux-start-transcription.sh` from `01` task 1.3. Verify with `bash -n` and a side-by-side diff against the Linux launcher. The only differences should be the platform flags already present today.

  **Done and verified 2026-09-13.** `mac-start-transcription.sh` now prefers `${SCRIPT_DIR}/transcriber`, then the venv, then `python3`, via the same `RUN` array as `linux-start-transcription.sh`. `bash -n` passes and no `PY_CMD` references remain. `diff` against the Linux launcher shows only the platform description comments and `--coreaudio-tap` in `CMD`, which are the differences that already existed.

## 2. macOS leg in `release.yml`

- [x] 2.1 On `macos-latest`: set up Python 3.14 with a venv containing `requirements-macos.txt` and `pyinstaller`, run `macos/audiotap-helper/build.sh`, then `build_sidecar.py`, staged as `src-tauri/binaries/transcriber-sidecar-aarch64-apple-darwin`, then `fetch_sidecar_resources.py`, then the smoke test from `01`. Verify that the smoke-test step passes in the run log.

  **Implemented 2026-09-13; run-log verification open.** The `macos` job (`needs: preflight`, `runs-on: macos-latest`) sets up Python 3.14 with a pip cache keyed on `requirements-macos.txt`. It runs `macos/audiotap-helper/build.sh`, freezes with `build_sidecar.py`, stages the result as `src-tauri/binaries/transcriber-sidecar-aarch64-apple-darwin`, runs `fetch_sidecar_resources.py`, then `.github/smoke-test.sh`. The smoke test needs only `python` and `mktemp`, so it runs on macOS unchanged. The workflow YAML parses, with jobs `preflight`, `linux`, `windows`, `macos`, and the macOS job has 13 steps.
  **Verified 2026-09-14** (`workflow_dispatch` run 34856241319 on `main` at `6c33bd5`, runner image `macos-26-arm64`, all four jobs green; the macOS job took 3m53s). `build.sh` built the universal helper, the freeze and staging succeeded, and the smoke test ended `Smoke test passed: dist/darwin/transcriber-sidecar` (a 2.0 s silent clip, 0 segments).
- [x] 2.2 List the frozen sidecar's contents with `pyi-archive_viewer` and fail the leg unless `macos/audiotap-helper/audiotap-helper` is present. Verify it passes. Then, in a scratch run that skips `build.sh`, confirm the freeze itself fails with the missing-helper message (1.1).

  **Implemented 2026-09-13; CI verification open.** The job runs `pyi-archive_viewer -l` on the frozen sidecar and fails unless the output contains `'macos/audiotap-helper/audiotap-helper'`. The listing command was checked here first: on the Linux sidecar it lists without interaction and prints each entry as a quoted-name tuple (for example `'av.libs/libasound-c7818c60.so.2.0.0'` and `'faster_whisper/assets/silero_vad_v6.onnx'`), so the quoted-path grep matches the real format.
  **The "scratch run that skips `build.sh`" sub-check was exercised locally instead of in CI:** forcing `platform.system()` to `Darwin` made the freeze refuse with the missing-helper message (recorded under 1.1). It is the same code path, without spending a CI run on a missing-file error. **The user accepted the local check in place of a CI scratch run (2026-09-14)**, so 2.2 only waits on the listing check passing in a real run.
  **Verified 2026-09-14** (`workflow_dispatch` run 34856241319 on `main` at `6c33bd5`, runner image `macos-26-arm64`, all four jobs green; the macOS job took 3m53s): the "Helper is bundled in the sidecar" step passed, matching the entry quoted under 1.1.
- [ ] 2.3 Run `npx --yes @tauri-apps/cli@<pinned> build --bundles app,dmg`, then `hdiutil verify` on the `.dmg`, then `build_portable.py` for the zipped `.app` and the CLI `.tar.gz`, and upload all three (release on tag runs, artifact on dispatch runs). Also run `codesign -dv` on the CLI binary and record the result. Verify with a `workflow_dispatch` run that all three are downloadable.

  **Implemented 2026-09-13; dispatch-run verification open.** It builds `--bundles app,dmg`, then runs `hdiutil verify` on `src-tauri/target/release/bundle/dmg/*.dmg`. Next come `build_portable.py`, then `codesign -dv` and `codesign --verify --deep --strict` on the app (see 1.2), then the copy into `out/`. File names come from source rather than guesswork:
  - `Transcriber_<version>_aarch64.dmg`: tauri-bundler 2.9.4 `dmg/mod.rs` builds `{product_name}_{version}_{arch}` into `bundle/dmg`, with `aarch64` for Apple Silicon;
  - `Transcriber_<version>_macos-arm64.zip` and `transcriber-cli_<version>_macos-arm64.tar.gz`: `build_portable.py` `PLATFORM_LABEL["darwin"]`.
  The CLI binary's `codesign -dv` is recorded with `|| true`, not asserted, because the smoke test cannot run an unsigned arm64 binary anyway. Upload is split like the other jobs: the draft release on tag runs, a `macos` artifact on dispatch runs.
  **First run, 2026-09-14** (`workflow_dispatch` run 34856241319 on `main` at `6c33bd5`, runner image `macos-26-arm64`, all four jobs green; the macOS job took 3m53s):
  - `hdiutil verify`: `checksum of "…/Transcriber_0.1.0_aarch64.dmg" is VALID`.
  - The CLI binary is `Format=Mach-O thin (arm64)`, `Signature=adhoc`, so PyInstaller's ad-hoc signing is confirmed.
  - The `macos` run artifact (655,367,773 bytes) downloaded with `gh run download`, holding all three files with the expected names: `Transcriber_0.1.0_aarch64.dmg` (220,163,400 bytes, UDIF `koly` trailer), `Transcriber_0.1.0_macos-arm64.zip` (219,643,214) and `transcriber-cli_0.1.0_macos-arm64.tar.gz` (215,802,350). The tarball holds `transcriber` (Mach-O arm64), `mac-start-transcription.sh`, `model/` and the three notices.
  - **Bug found: the zip did not unpack to an app.** Its entries began at `Contents/…` rather than `Transcriber.app/Contents/…`, because `ditto -c -k` archives only a folder's contents unless given `--keepParent`. Unzipping would have produced a loose `Contents` folder, not the `Transcriber.app` the README tells people to open. **Fixed:** `build_portable.py` now passes `--keepParent` (the non-macOS `_zip_dir` fallback already kept the parent). The macOS job now fails unless `unzip -l` lists `Transcriber.app/Contents/Info.plist`. That check rejects this run's zip and accepts a correctly rooted one.
  - **Still open:** a run with the fix, confirming the zip now unpacks to `Transcriber.app`.

## 3. Documentation

- [x] 3.1 Fill in README's macOS download subsection:
  - "Built automatically on Apple Silicon GitHub runners, but untested on real hardware. Testers welcome." Link to the issue tracker, and name the specific open questions: does the `.dmg` or the zipped `.app` open after Open Anyway; does file transcription work in the GUI; does `--coreaudio-tap` live capture work from the CLI.
  - Arm64 only.
  - System Settings → Privacy & Security → Open Anyway, replacing the stale right-click → Open text.
  - `xattr -d com.apple.quarantine ./transcriber` for the CLI.
  - macOS 14.4 or later for CLI system-audio capture.

  Verify that the stale right-click instruction no longer appears anywhere in the README.

  **Done and verified 2026-09-13.** README's macOS subsection now has:
  - the "Built automatically on Apple Silicon GitHub runners, but not yet tested on a real Mac. Testers welcome." notice, linking to the issue tracker with four open questions;
  - a download table using the real file names;
  - "Apple Silicon (arm64) only";
  - System Settings → Privacy & Security → **Open Anyway** in place of the stale advice.
  The CLI archive section gains `xattr -d com.apple.quarantine ./transcriber`, the `./mac-start-transcription.sh` launcher, and the macOS 14.4 requirement for `--coreaudio-tap`.
  **Stale instruction gone:** `control-click`, `choose Open to bypass` and `right-click (or` each match **0** times. The only remaining "Right-click" lines (386, 388) are the unrelated Windows Sound-settings steps, not Gatekeeper advice. The new text deliberately never mentions right-clicking, so this check stays unambiguous.
- [x] 3.2 Record here, for whoever tests first, `06-remove-installer-packaging-macos`'s untested items that this change inherits: GUI file transcription from the `.app`, and Gatekeeper behavior of a downloaded (quarantined) copy. Verify that both appear in the README testers call from 3.1.

  **Recorded 2026-09-13 for whoever tests first.** Untested items inherited from `06-remove-installer-packaging-macos`:
  1. **GUI file transcription from the `.app`.** `06` built and launched the app on a Mac but never ran a file transcription through the GUI.
  2. **Gatekeeper behaviour of a downloaded (quarantined) copy.** A locally built app carries no quarantine attribute, so how it behaves at first open says nothing about what a downloaded copy will do. This is also why the README's Open Anyway flow is expected from Apple's documented rules, not observed.
  Both are in the README's call for testers: "Does file transcription work in the app?" and "Does a *downloaded* copy behave as described below the first time you open it?".
