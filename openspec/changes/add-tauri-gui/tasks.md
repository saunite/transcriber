## 1. Engine: minimal additive changes

- [ ] 1.1 Add `--list-devices-json` flag to `transcriber.py` that reuses the existing device enumeration and prints a JSON array (index, name, max_input_channels, default_samplerate) to stdout
- [ ] 1.2 Verify `--list-devices` text output is byte-for-byte unchanged
- [ ] 1.3 Add a fixture test that runs the engine's live/file paths and asserts the transcript-line regex (from design.md) matches every emitted line, so future engine output changes fail CI instead of silently breaking the GUI

## 2. Sidecar packaging

- [ ] 2.1 Freeze the Python engine with PyInstaller (`--onefile`) for Windows
- [ ] 2.2 Freeze the Python engine with PyInstaller for Linux
- [ ] 2.3 Freeze the Python engine with PyInstaller for macOS (shell-only target; sidecar still needed for file transcription)
- [ ] 2.4 Smoke-test each frozen binary standalone (`--list-devices-json`, `--file` on a sample clip) before wiring into Tauri
- [ ] 2.5 Bundle the `base` faster-whisper model files into installer resources per OS
- [ ] 2.6 Bundle a static ffmpeg binary into installer resources per OS

## 3. Tauri shell scaffold

- [ ] 3.1 Scaffold Tauri project (`src-tauri/` + chosen frontend framework)
- [ ] 3.2 Wire frozen sidecar binary + model + ffmpeg as Tauri bundled resources/external binaries
- [ ] 3.3 Implement window creation with no sidecar/model load in the startup path

## 4. Sidecar process management (Rust)

- [ ] 4.1 Implement on-demand sidecar spawn (translate UI state → CLI flags, e.g. `--live --wasapi --include-mic --model base ...`)
- [ ] 4.2 Implement async, non-blocking stdout/stderr reader on a background task
- [ ] 4.3 Implement transcript-line regex parser and `transcript-line` event emission to the webview
- [ ] 4.4 Implement fallback `sidecar-log` event for unmatched stdout lines
- [ ] 4.5 Implement graceful stop (signal + timeout) and clean-exit handling
- [ ] 4.6 Implement crash detection (unexpected exit) → error event + UI reset to idle
- [ ] 4.7 Implement device listing via `--list-devices-json`, parsed as JSON

## 5. Frontend UI

- [ ] 5.1 Idle/home screen: start live session, drop/browse a file, open settings
- [ ] 5.2 Device picker populated from the sidecar's JSON device list
- [ ] 5.3 Model/language/task selection controls (mirroring `--model`/`--language`/`--task`)
- [ ] 5.4 Live transcript view: scrolling list of `transcript-line` events, `[SYS]`/`[MIC]` tag styling
- [ ] 5.5 Collapsible debug/log panel fed by `sidecar-log` events
- [ ] 5.6 File transcription flow: drag-and-drop + browse, progress indicator, output format choice (txt/srt/vtt)
- [ ] 5.7 Error/toast surface for sidecar crash and unsupported file drops
- [ ] 5.8 Platform-gate: detect macOS at runtime and disable/hide live-capture controls with an explanatory message. Unblock once `add-macos-capture` tasks.md section 5 (hardware-dependent verification) is complete — until then, `--coreaudio-tap` exists at the CLI/sidecar level but is unverified against real hardware, so the GUI should keep macOS live-capture controls disabled even after the sidecar wiring supports the flag.

## 6. Performance verification

- [ ] 6.1 Scripted launch-timing harness: assert window-shown and UI-interactive budgets from design.md on a cold OS file cache
- [ ] 6.2 Verify no UI-thread block/dropped-frame regression during sidecar start and live transcript streaming
- [ ] 6.3 Record actual installer size per OS and cold sidecar-start time as a baseline for future comparison

## 7. Packaging & release

- [ ] 7.1 Configure `tauri-bundler` targets: `.msi` (Windows), `.AppImage`/`.deb` (Linux), `.dmg` (macOS, shell-only)
- [ ] 7.2 CI build matrix producing per-OS installers
- [ ] 7.3 Manual install + fully-offline transcription test per OS (network disabled) confirming no download is attempted
- [ ] 7.4 Update README with GUI install/usage instructions alongside the existing CLI instructions
