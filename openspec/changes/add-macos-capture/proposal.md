## Why

The transcriber has no macOS live-capture path today — only Windows (WASAPI loopback) and Linux (PulseAudio/PipeWire monitor) can capture system audio for live meeting transcription. macOS users can only transcribe pre-recorded files. This blocks macOS from being a real target for the in-progress desktop GUI (`add-tauri-gui`), which currently ships macOS as a shell-only, file-transcription-only build pending this change.

**Explicit assumption**: this proposal is authored without access to macOS hardware to test against during authoring. The design and tasks are structured so the riskiest, least-verifiable piece (a native Core Audio tap) is isolated behind a documented, already-working fallback (a virtual audio driver, mirroring the existing Windows Stereo-Mix-or-VB-Cable pattern), so macOS users have a working path the moment this ships even before the native tap is hardware-validated.

## What Changes

- New `macos_capture.py` module, mirroring `wasapi_capture.py`'s interface (`get_default_loopback_device`, `capture_stream`, `cleanup`), providing native system-audio loopback capture on macOS via the Core Audio **Process Tap API** (`AudioHardwareCreateProcessTap`, macOS 14.4+) — no virtual audio driver required, analogous to WASAPI's Bluetooth-compatible loopback on Windows.
- The Core Audio tap itself is implemented as a small native Swift/Objective-C helper binary invoked as a subprocess (mirroring the existing ffmpeg-subprocess pattern already used by `audio_extractor.py`), keeping the tap/permission-handling native code isolated and the Python/numpy pipeline untouched.
- New `--coreaudio-tap` CLI flag (macOS-only), directly analogous to `--wasapi`, selecting native loopback capture. Existing `--live` (simple/sounddevice mode) continues to work on macOS as-is for users on macOS < 14.4 or those using a virtual audio driver (BlackHole/Loopback), matching the fallback pattern already documented for Windows.
- `--include-mic` dual-capture (system + mic, tagged `[SYS]`/`[MIC]`) extends to macOS with no changes needed — it already uses cross-platform `sounddevice`.
- README updated with macOS setup instructions: native tap (recommended, macOS 14.4+, first-run permission prompt) and virtual-driver fallback (older macOS).
- Once validated, this removes the macOS live-capture restriction called out in `add-tauri-gui`'s design (GUI's platform-gate on live-capture controls can be lifted for macOS).
- Out of scope: bundling/shipping the native helper inside the Tauri GUI installer (tracked as a follow-up to `add-tauri-gui` once this capability exists and is hardware-validated), Linux/Windows changes.

## Capabilities

### New Capabilities
(none — this extends the existing `audio-capture` and `cli` capabilities with a new platform, following the same shape as the existing WASAPI support)

### Modified Capabilities
- `audio-capture`: adds native macOS system-audio loopback capture (Core Audio Process Tap) as a new capture path alongside existing WASAPI (Windows) and PulseAudio/PipeWire monitor (Linux) support, including permission-denied and unsupported-OS-version handling.
- `cli`: adds `--coreaudio-tap` flag (macOS-only) analogous to `--wasapi`, and error handling when `--wasapi`/`--coreaudio-tap` are used on the wrong platform.

## Impact

- **New code**: `macos_capture.py`, a native Swift/Objective-C helper binary + its build step, CLI flag wiring in `transcriber.py`.
- **Unchanged**: Windows (`wasapi_capture.py`) and Linux capture paths, transcription engine, mic capture, WAV saving/merging.
- **New build dependency**: Xcode Command Line Tools (`swiftc`) to build the native helper on macOS; this is a build-time dependency only, not a new Python package.
- **New runtime concern**: macOS will prompt for a privacy permission (audio capture / screen recording, OS-version-dependent) on first use; the app must handle "permission denied" and "permission not yet granted" states explicitly rather than failing silently.
- **Known validation gap**: the native tap path cannot be exercised on real macOS hardware during authoring of this change (see design.md Risks). It ships behind a task list that separates code-complete work from hardware-dependent verification, and the pre-existing virtual-driver fallback path provides a working alternative in the meantime.
