## 1. Native helper (Swift/Objective-C)

- [x] 1.1 Create the native helper project (command-line tool target, Xcode Command Line Tools / `swiftc`)
- [x] 1.2 Implement Process Tap creation for the default output device (`AudioHardwareCreateProcessTap`)
- [x] 1.3 Stream captured PCM frames to stdout in a fixed, documented format (sample rate/format/channel layout recorded in code comments and design.md once confirmed)
- [x] 1.4 Implement distinct exit codes/stderr messages for: unsupported OS version, permission denied, other tap-creation failure
- [x] 1.5 Handle clean shutdown on stdin close / SIGTERM (mirrors how `WASAPICapture` relies on `stream.close()` to unblock its reader)
- [x] 1.6 Build as a universal binary (arm64 + x86_64) if toolchain supports it without hardware to verify the x86_64 leg; otherwise arm64-only with a note in design.md's Open Questions

  Note: 1.1–1.6 are implemented in `macos/audiotap-helper/main.swift` and `build.sh`, written without macOS/Xcode available to compile or run against — treat as an unverified first draft (see design.md). `build.sh` produces an arm64 binary by default with documented `lipo` steps for a universal build, matching 1.6's fallback condition.

## 2. Python integration

- [x] 2.1 Create `macos_capture.py` with the same interface shape as `WASAPICapture` (`get_default_loopback_device`, `capture_stream`, `cleanup`)
- [x] 2.2 Spawn the native helper as a subprocess; background thread reads stdout and pushes chunks to a queue (mirror `WASAPICapture._read_loop`)
- [x] 2.3 Convert captured PCM to float32 mono for the existing transcription pipeline
- [x] 2.4 Detect macOS version via `platform.mac_ver()` before spawning the helper; fail fast with the fallback pointer on < 14.4
- [x] 2.5 Map the helper's distinct failure exit codes/stderr to clear, distinct user-facing error messages (version / permission / other)

## 3. CLI wiring

- [x] 3.1 Add `--coreaudio-tap` flag to `transcriber.py`, gated to macOS
- [x] 3.2 Add `transcribe_live_coreaudio_tap` following the shape of `transcribe_live_wasapi` (reuse `_process_audio_chunk`, `_setup_output_files`, `_print_summary`, etc. — no duplication of the chunking/transcription logic)
- [x] 3.3 Reject `--coreaudio-tap` on non-macOS and `--wasapi` on non-Windows with a clear, platform-naming error
- [x] 3.4 Confirm `--include-mic` dual-capture works unchanged on macOS (already cross-platform via `sounddevice`)

## 4. Automated tests (no macOS hardware required)

- [x] 4.1 Unit tests for `macos_capture.py`'s PCM parsing/resampling against synthetic stdin data (bypassing the real native helper)
- [x] 4.2 Unit tests for CLI flag validation (platform-mismatch rejection, version-gate fail-fast path) using a mocked `platform.mac_ver()`
- [ ] 4.3 Native helper: unit-testable logic (argument parsing, PCM framing) separated from the untestable-without-hardware tap-creation call, so as much as possible is covered by CI

  Not done: no Swift/XCTest target exists yet — this session has no Xcode/macOS to create or run one. `main.swift` has no separate argument-parsing step to extract (it takes no CLI args), so what remains here is adding an XCTest target for the header-construction logic once someone has a Mac to set it up.

## 5. Hardware-dependent verification (deferred — requires real macOS 14.4+ hardware)

- [ ] 5.1 Verify native helper builds and the permission prompt appears on first run
- [ ] 5.2 Verify captured audio format matches the assumption in design.md; adjust `macos_capture.py`'s conversion step if not
- [ ] 5.3 Verify capture works with a Bluetooth output device (the Windows WASAPI path's key selling point — confirm macOS parity)
- [ ] 5.4 Verify permission-denied and tap-creation-failure error paths produce the intended user-facing messages
- [ ] 5.5 Verify the fallback virtual-driver path (`--live --audio-device N` with BlackHole/Loopback installed) as a sanity check that it still works unchanged
- [ ] 5.6 Once native tap is verified, confirm whether permission grants require a proper `.app` bundle (relevant to `add-tauri-gui` integration) or work from a bare CLI binary

  Deferred: genuinely requires real macOS 14.4+ hardware, which isn't available in this session (per the user's explicit note). Everything in sections 1–4 was built to keep this section as small and isolated as possible — code-complete work does not block on it, but this change should not be considered production-ready until section 5 is done.

## 6. Documentation

- [x] 6.1 README: macOS setup section — native tap (recommended, 14.4+, permission prompt) and virtual-driver fallback (older macOS), mirroring the existing Windows Stereo-Mix/VB-Cable structure
- [x] 6.2 README: `--coreaudio-tap` usage examples alongside existing `--wasapi` examples
- [x] 6.3 Note in `add-tauri-gui`'s tracking that macOS live-capture GUI support is unblocked once section 5 above is complete
