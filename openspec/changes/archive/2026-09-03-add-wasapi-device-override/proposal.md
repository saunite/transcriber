## Why

The WASAPI loopback (system-audio) source is always auto-detected, with zero visibility or override anywhere — CLI or GUI. `--audio-device N` exists as a CLI flag but is unreachable from the GUI, and the CLI's own error message when auto-detection fails ("Run with --list-devices to see available devices") is actively wrong: `--list-devices`/`--list-devices-json` enumerate `sounddevice`'s device list, a completely separate index space from `pyaudiowpatch`'s WASAPI loopback devices — that list never contains a usable value for `--audio-device`. Surfaced during real-hardware testing in `05-remove-installer-packaging-windows`.

## What Changes

- Add an optional "System audio device override (advanced)" field to Session Settings: a numeric input, blank by default (= auto-detect). Paired with an explicit, always-visible message: **"Default: auto-detected WASAPI device (recommended). Overriding is not recommended unless the wrong device is being captured."**
- `start_live_session` gains an `audio_device: Option<i32>` parameter; passes `--audio-device N` only when the field is non-blank, otherwise omits it entirely (preserving today's auto-detect default exactly).
- Fix the CLI's misleading remedy text in `transcriber.py` (currently pointing at `--list-devices`, which cannot help here) to something accurate.

**Deliberately not building**: a full WASAPI loopback device *listing* UI (dropdown populated from `pyaudiowpatch.get_loopback_device_info_generator()`). That's a real feature (new backend enumeration split from the existing mic-only `list_devices_json()`, a new Rust response shape, a new dropdown) with no evidence yet that auto-detection is actually picking the wrong device for anyone — this change ships the escape hatch and the warning; a proper device browser is a natural follow-up if auto-detect ever proves wrong in practice, not before.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `desktop-gui`: adds one requirement — an optional, clearly-discouraged WASAPI device override, default behavior (auto-detect) unchanged.

## Impact

- **Changed**: `src-tauri/src/sidecar.rs` (`start_live_session` gains `audio_device` param), `src/index.html`/`src/main.js` (new advanced field + warning text), `transcriber.py` (one error-message string, no behavior change — `--audio-device` already existed and already worked from the CLI).
- **Unaffected**: `wasapi_capture.py`, `audio_capture.py`, the microphone device list (`list_devices`/`list_devices_json` untouched — still `sounddevice`-only, still mic-scoped) — no risk of index-space collision since this change never merges the two device universes.
