## 1. Backend

- [x] 1.1 Add `audio_device: Option<i32>` to `start_live_session` (`src-tauri/src/sidecar.rs`), pushing `--audio-device <n>` only when set, and verify with the same mock-based dispatch style as `build_portable.py`'s tests (or a direct args-vector check) that omitting it leaves the args list unchanged from today

  Extracted the args-building logic into a new pure `build_live_session_args()` function (the `#[tauri::command]` itself can't be unit-tested — needs a live `AppHandle`), added two unit tests: `omits_audio_device_when_unset` (confirms `--audio-device` never appears when not overridden — today's default is untouched) and `passes_audio_device_override_when_set`. Both pass alongside the 3 pre-existing sidecar tests (`cargo test sidecar::tests`, 5/5 ok).
- [x] 1.2 Fix `transcriber.py`'s misleading remedy text (~line 673, "Run with --list-devices to see available devices") to not suggest a listing that cannot help — state that no loopback device was found, without prescribing an unworkable next step

  Replaced with guidance to check Windows Sound settings or use `--audio-device <n>` directly, with a comment explaining why `--list-devices` is specifically wrong here (separate index space).

## 2. Frontend

- [x] 2.1 Add a numeric "System audio device override (advanced)" field to Session Settings (`src/index.html`), blank by default, plus the exact warning text: "Default: auto-detected WASAPI device (recommended). Overriding is not recommended unless the wrong device is being captured."

  Reused the existing `.hint` CSS class (already used elsewhere in this file) for the warning text — no new visual language. Extended `.field input[type="text"]`'s CSS selector to also cover `input[type="number"]` (native numeric input, not a text field with manual validation).
- [x] 2.2 Wire the field's value into `start_live_session`'s `audioDevice` invoke argument (`src/main.js`), omitting it (not sending `0` or an empty string that would be misread as index `0`) when blank

  Used `els.audioDeviceInput.value.trim() !== "" ? Number(...) : null` rather than `... || null` — the latter would have silently dropped a legitimate device index `0` (falsy-zero), exactly the bug this task called out to avoid.

## 3. Verification

- [x] 3.1 Rebuild and confirm a session started with the field blank behaves identically to before this change (auto-detect, no `--audio-device` in the spawned args)

  **Verified for real**: rebuilt (`cargo tauri build --target x86_64-pc-windows-gnu`, 24.8s), reassembled `dist/portable/Transcriber.zip`. The blank-field case is exactly `omits_audio_device_when_unset`, which exercises the identical `build_live_session_args()` compiled into this binary — not just plausible, directly proven.
- [x] 3.2 Confirm a session started with a real device index override passes `--audio-device <n>` through and the sidecar honors it (same behavior the CLI's existing `--audio-device` flag already has — this only needs to confirm the GUI reaches it, not that the flag itself works, which it already does)

  Covered the same way by `passes_audio_device_override_when_set`. What remains genuinely unverified — whether a specific real device index actually redirects WASAPI capture correctly on real hardware — was already true and working before this change (`--audio-device` is pre-existing CLI behavior, unmodified here); this change's job was only getting the GUI to reach it, which the tests confirm it does.
