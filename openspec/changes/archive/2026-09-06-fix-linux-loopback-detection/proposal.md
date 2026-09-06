## Why

`AudioCapture.get_loopback_device()`'s Linux branch (`audio_capture.py`) picks a loopback device by name from `sounddevice`/PortAudio's enumerated device list ("monitor", "pipewire", "default"). On any machine whose PortAudio build has no "pulse" host API (the common case for prebuilt `sounddevice` wheels — confirmed here via `sd.query_hostapis()`: only ALSA and JACK), none of those ALSA-visible names actually carry the real PipeWire/PulseAudio sink-monitor signal — they silently capture pure silence instead of system audio. This was found while verifying `add-linux-dual-source-live-capture`'s task 3.1: every candidate device (`pipewire`, `default`, the JACK bridge) captured `0.0` RMS while real audio played through the speakers. The same silence reproduces on the already-shipped single-source `--live` path with the identical test, so this is a pre-existing bug in the currently-shipped Linux system-audio capture feature, not something introduced by that change. Confirmed the fix direction works: `parec` against the real monitor source name (found via `pactl list sources short`) captured genuine, non-zero audio energy in the same test where PortAudio's ALSA enumeration captured silence.

## What Changes

- Replace `AudioCapture`'s Linux loopback acquisition with a `pactl`-discovered real monitor source name, captured via a `parec` subprocess (raw PCM piped to stdout, read on a background thread) — the same shape `wasapi_capture.py` and `macos_capture.py` already use for their own native-loopback paths (native tool/subprocess → background reader thread → queue → `capture_stream(callback, ...)`).
- `transcribe_live_simple`'s single-source system-audio path, and `add-linux-dual-source-live-capture`'s new dual-source system-audio path, both switch to this corrected loopback source. The microphone side (plain `sounddevice`, already cross-platform) is untouched.
- Add a clear, actionable error (matching the existing WASAPI/Core-Audio-Tap style) for the case where `pactl` isn't available or no monitor source can be found, instead of silently proceeding with a device that captures nothing.
- **BREAKING (internal only)**: `AudioCapture.get_loopback_device()`'s Linux return value changes from a `sounddevice` integer device index to a monitor source name (string). Nothing outside this codebase depends on it; no CLI-facing flag changes.

## Capabilities

### Modified Capabilities
- `audio-capture`: the Linux system-audio loopback requirement changes from "auto-detect via PortAudio device enumeration" to "auto-detect via `pactl`, captured via a native subprocess" — the former does not reliably capture real audio on machines without a PortAudio pulse host API.

## Impact

- **Changed**: `audio_capture.py` (Linux loopback acquisition), `transcriber.py` (`transcribe_live_simple`'s system-audio stream setup, and `_transcribe_live_linux_dual`'s system-audio stream setup from `add-linux-dual-source-live-capture`).
- **New**: a small Linux-native loopback capture helper, matching `macos_capture.py`'s existing shape (subprocess + background reader thread + queue).
- **Unchanged**: `wasapi_capture.py`, `macos_capture.py`, the microphone-side code (already cross-platform via `sounddevice`), the CLI flag contract (`--audio-device`, `--include-mic`, `--mic-device`, etc.).
- **Unblocks**: `add-linux-dual-source-live-capture` task 3.1 (real end-to-end dual-source verification), and gives the already-shipped single-source Linux path working system-audio capture for the first time on machines like this one.
