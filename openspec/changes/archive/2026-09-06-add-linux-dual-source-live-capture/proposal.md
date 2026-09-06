## Why

Dual-source live capture (system audio + microphone, tagged `[SYS]`/`[MIC]`) exists on Windows (WASAPI) and macOS (Core Audio Tap), but not on Linux — `transcribe_live_simple`, the function that runs when neither `--wasapi` nor `--coreaudio-tap` is passed, never checks `--include-mic`. Unlike Windows, Linux needs no special API for this: PulseAudio/PipeWire already exposes a monitor (loopback) source as an ordinary capture-capable device through plain PortAudio/`sounddevice` — the same library already used for the microphone side on every platform. The capability gap is a missing code path, not a missing OS feature. This was scoped out of `add-cross-platform-launcher-scripts` specifically so that change's new Linux launcher wouldn't silently claim mic capture it can't yet deliver.

## What Changes

- **Linux gains dual-source live capture**: when `--live --include-mic` is run with neither `--wasapi` nor `--coreaudio-tap` (i.e., on Linux), the system captures system audio (via the existing auto-detected monitor/loopback device) and the microphone concurrently, tagging segments `[SYS]`/`[MIC]` exactly like the Windows and macOS paths.
- **Reuses existing machinery**: the auto-detected loopback device lookup (`AudioCapture.get_loopback_device()`) and the `--save-audio` sys+mic WAV merge (`_merge_sys_mic_wav`, from `drop-ffmpeg-dependency`) are reused as-is, not reimplemented.
- **`linux-start-transcription.sh`'s disclosure is removed** once this lands — a follow-up one-line edit to that script and its spec requirement (added in `add-cross-platform-launcher-scripts`), tracked here since it depends on this change, not the other way around.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `audio-capture`: adds a requirement for Linux dual-source capture, alongside the existing platform-specific WASAPI requirement.
- `cli`: adds a requirement for selecting dual-source capture on Linux (the default/no-flag live path), alongside the existing WASAPI-specific selection requirement.

## Impact

- **Changed**: `transcriber.py` (`transcribe_live_simple` gains an `--include-mic` branch, following the existing WASAPI dual-queue/tagging/merge structure) — no other engine files change.
- **Unchanged**: `wasapi_capture.py`, `macos_capture.py`, the sidecar CLI flag contract (`--include-mic`/`--mic-device` already exist as flags; this just makes them functional on Linux), the GUI's IPC contract.
- **Follow-up, not blocking**: once this lands, `linux-start-transcription.sh` can drop its system-audio-only disclosure and pass `--include-mic` like the other two launchers — a small edit to `add-cross-platform-launcher-scripts`'s output, done as a task here rather than reopening that change.
- **Verifiable in this environment**: unlike the Windows/macOS dual-capture paths, this can be built and tested end-to-end on ordinary Linux audio hardware (confirmed present and working in this session: a real mic device and, needed for this change, a working PulseAudio/PipeWire monitor source) — no "unverified, no hardware" caveat should be needed here.
