## Why

The transcriber is CLI-only today: installing it means Python 3.9+, `pip install`, and a separate ffmpeg install (choco/scoop/apt), then remembering flag combinations like `--live --wasapi --include-mic`. That's a real barrier for a non-technical user who just wants to record a meeting. A native desktop GUI removes the setup steps and flag-memorization, while reusing the existing, working Python engine as-is.

## What Changes

- New Tauri desktop application (Rust shell + webview frontend) that wraps the existing Python CLI (`transcriber.py` and friends) as a bundled sidecar process — no rewrite of the transcription/capture engine.
- Installer bundles a frozen Python sidecar executable, the `base` Whisper model weights, and ffmpeg, so the app works fully offline immediately after install (no first-run download).
- GUI surfaces the CLI's existing capabilities: start/stop live capture (system audio + optional mic, mirroring `--wasapi --include-mic`), device selection (wraps `--list-devices`), model/language/task selection, live scrolling transcript with `[SYS]`/`[MIC]` tags, and drag-and-drop file transcription (video/audio → txt/srt/vtt).
- Frontend visual design is produced with the `impeccable` skill (direction → comp → build → finish-review) rather than hand-rolled styling, replacing the initial unstyled HTML/CSS/JS pass — the app is meant for a non-technical user, so it needs an actual design pass, not just working controls.
- Sidecar process lifecycle is owned by the Rust backend: launch on demand (not at app startup), clean stop on user request or app quit, and crash detection with a user-facing error instead of a hung UI.
- Cold-open and responsiveness are explicit, testable requirements (see design.md for numeric budgets) — the window must appear and be interactive before the sidecar/model finish loading.
- Windows and Linux are full GUI targets (both already have working live-capture backends). macOS is a UI-shell-only target in this proposal: the app builds and runs there and file transcription works, but live system-audio capture is explicitly out of scope pending the separate `add-macos-capture` change — the GUI must degrade gracefully (disable/hide live-capture controls) on macOS until that capability lands.
- Out of scope for this change: rewriting the engine in Rust/whisper.cpp, mobile (Android/iOS) support.

## Capabilities

### New Capabilities
- `desktop-gui`: Tauri-based desktop application — installer packaging (bundled model + ffmpeg), sidecar process lifecycle, UI for live capture and file transcription, and startup/responsiveness requirements.

### Modified Capabilities
- `cli`: adds a `--list-devices-json` flag that emits the audio device list as JSON instead of the current multi-line human-readable text. Additive only — `--list-devices` behavior is unchanged; the GUI needs a structured device list for its picker and the existing text format is not reliably machine-parseable (multi-line per device, no delimiter).

(Live transcript output is unchanged — the GUI's sidecar wrapper parses the existing single-line, bracket-delimited stdout format directly; see design.md.)

## Impact

- **New code**: Tauri project (Rust `src-tauri/` + web frontend), sidecar packaging scripts (PyInstaller or equivalent), CI build pipeline producing per-OS installers.
- **Unchanged**: `transcriber.py`, `transcription_engine.py`, `audio_capture.py`, `wasapi_capture.py`, `audio_extractor.py` — consumed as a subprocess, not modified.
- **New dependencies**: Rust toolchain, Tauri CLI, a Python freezing tool (e.g. PyInstaller), platform installer tooling (WiX/NSIS for Windows, AppImage/deb for Linux via `tauri-bundler`).
- **Installer size**: dominated by the frozen Python interpreter + faster-whisper/ctranslate2 + bundled `base` model (~145MB) + ffmpeg binary, not by the Tauri shell itself (~3-10MB). Expect installer size in the several-hundred-MB range — see design.md for the breakdown and any mitigation considered.
- **Distribution**: adds code-signing/notarization concerns per OS that don't exist for the current CLI (unsigned installers trigger OS warnings on Windows/macOS).
