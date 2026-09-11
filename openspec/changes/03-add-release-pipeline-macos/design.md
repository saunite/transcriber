## Context

See proposal.md - Why. `01`'s design covers the workflow shape, the smoke test, and the CLI archive; this design covers only what is macOS-specific.

- **Helper lookup.** `macos_capture._helper_path()` returns `<dir of macos_capture module>/macos/audiotap-helper/audiotap-helper`. In a PyInstaller onefile build, the module's directory is the runtime extraction directory, so the helper must be added at `macos/audiotap-helper/` inside the frozen archive. `build_sidecar.py` adds nothing today.
- **Helper build.** `macos/audiotap-helper/build.sh` builds a universal binary with `swift build --arch arm64 --arch x86_64`. That fails with Command Line Tools alone, but works on GitHub's macOS runners because they ship full Xcode.
- **Known from a local Mac build** (`06` task 3.1): the frozen macOS sidecar runs correctly from a venv; the bundle has no signature at all; and a locally built app carries no quarantine attribute, so its Gatekeeper behavior tells you nothing about a downloaded copy.
- **No Mac is available** for this change. Verification is limited to what a headless CI runner can prove.

## Goals / Non-Goals

**Goals:**
- Produce macOS artifacts at all, from CI.
- Close the helper-bundling gap in a way CI can verify deterministically.
- Be honest in the README about what is untested.

**Non-Goals:**
- Intel or universal builds. Python wheels (ctranslate2, onnxruntime) are per-architecture, so universal would mean two sidecar freezes merged with `lipo`, which isn't worth doing without a Mac to test on.
- Notarization, or enabling GUI live capture on macOS.

## Decisions

### 1. `macos-latest` (arm64) only

This was the user's decision. `macos-latest` is Apple Silicon. The app also runs on Intel Macs only if Rosetta can run arm64 code, and it can't, so Intel users aren't served. The README says so.

### 2. `build_sidecar.py` adds the helper on macOS and refuses to freeze without it

On Darwin, it adds `--add-binary macos/audiotap-helper/audiotap-helper:macos/audiotap-helper`, and exits non-zero first if that file doesn't exist. Failing loudly is the point: a silent omission is exactly the gap being fixed. The workflow runs `macos/audiotap-helper/build.sh` unchanged first; its universal output is fine on the runner and simply larger than needed. The Windows and Linux code paths are untouched.

**Verifying without a Mac:** list the frozen archive's contents with `pyi-archive_viewer` and check for `macos/audiotap-helper/audiotap-helper`. That's deterministic. Actually running `--coreaudio-tap` on a runner is not: it needs a capture permission a headless runner can't grant. So that stays in the testers call.

### 3. Ad-hoc signing with `signingIdentity: "-"`

Apple Silicon won't execute unsigned arm64 code, and a quarantined (downloaded) app with no valid signature can be reported as "damaged", with no Open Anyway path. An ad-hoc signature is valid, needs no Apple account, and is expected to produce the ordinary "Apple could not verify…" dialog, which System Settings → Privacy & Security → Open Anyway resolves. That's what the README documents.

This is the expected behavior from Apple's documented Gatekeeper rules, but it can't be verified here, and it's listed in the testers call. For the CLI binary, PyInstaller ad-hoc signs its output on macOS. Confirm that with `codesign -dv` in the leg.

### 4. The `.dmg` comes from Tauri's bundler

Tauri's bundler builds the `.dmg` on the runner; that's the normal Tauri path on GitHub macOS runners. After building, `hdiutil verify` checks the image. This change adds no custom DMG layout.

### 5. Launcher fallback mirrors the Linux launcher

`mac-start-transcription.sh` gets the same `[ -x "$SCRIPT_DIR/transcriber" ]` branch as `linux-start-transcription.sh` (`01` Decision 11). It can't be exercised for real without a Mac, so it's checked for syntax and by comparing it line for line with the Linux launcher, which is tested on hardware.

## Risks / Trade-offs

- **[Risk]** Every macOS artifact ships unverified on hardware → the README states it plainly and asks for reports. CI proves the sidecar runs, the model loads, the helper is bundled, the signatures are valid, and the `.dmg` is well formed.
- **[Risk]** The Gatekeeper wording or flow differs from what's documented → a tester report would correct the README. No code depends on it.
- **[Risk]** The helper is bundled but fails at runtime (for example over a permission-prompt attribution quirk in a frozen parent process) → invisible without hardware. It's named explicitly in the testers call.
- **[Risk]** `macos-latest` moves to a newer macOS image and the build breaks → pin a specific `macos-NN` image if that happens.
- **[Trade-off]** The universal helper binary is about twice the size of an arm64-only one, a few hundred KB, in exchange for leaving `build.sh` untouched.
