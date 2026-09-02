# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Vanilla HTML/CSS/JS, no framework, no build step (confirmed by user). Tauri's webview serves `src/index.html`/`main.js`/`style.css` directly.

## Users

Non-technical people who need to transcribe meetings/recordings and don't want to touch a CLI: install Python 3.9+, `pip install`, a separate ffmpeg install, then remember flag combinations like `--live --wasapi --include-mic`. The desktop app exists specifically to remove that setup and flag-memorization barrier for this audience.

## Product Purpose

A desktop app that wraps an existing, working Python transcription engine (Whisper-based) so a non-technical user can transcribe a live meeting or a recorded file without any command-line setup. Success is: install, open, and get a transcript — no terminal, no network required.

## Positioning

Fully offline after install (bundled Whisper model + bundled ffmpeg, no first-run download, no account/cloud dependency) and native system-audio capture without a virtual audio driver (WASAPI Process Loopback on Windows, Core Audio Process Tap on macOS 14.4+) — including Bluetooth output devices, which many competing "install a virtual cable" approaches don't handle cleanly.

## Operating Context

- Two core flows: (1) start a live capture session during a meeting/call and watch a transcript build in real time, tagged by source (`[SYS]` system audio / `[MIC]` microphone) when both are captured; (2) drop or browse an existing video/audio file and get a transcript file back (txt/srt/vtt).
- The transcription/capture engine runs as a bundled Python "sidecar" subprocess launched on demand by the Tauri/Rust shell — never at app startup — so the window opens and is interactive immediately, independent of model load time.
- Settings a session needs: audio input device, Whisper model size, language, and (file flow only) task (transcribe vs. translate).
- A collapsible debug/log view exists for sidecar output that isn't a recognized transcript line (headers, warnings, status messages) — not user-facing by default, but must not be silently dropped.

## Capabilities and Constraints

- Windows and Linux are full targets today (live capture + file transcription). macOS currently ships as a GUI shell with file transcription only; live capture on macOS is gated behind a separate in-progress capability (native Core Audio tap) and must degrade gracefully — controls disabled with an explanation, not hidden as a bug, not silently broken.
- No network calls anywhere in the app; everything (model, ffmpeg) ships in the installer.
- The Rust/Tauri backend already exposes: `transcript-line`, `sidecar-log`, and `file-transcription-complete` events, and a `get_platform` command. These names and the sidecar CLI-flag contract are fixed — the frontend rebuild must consume them as-is, not rename or restructure them.
- File Browse is not yet wired to a real OS file picker (currently stubbed) — needs `@tauri-apps/plugin-dialog` in this pass, drag-and-drop already works.
- Sidecar crashes must surface an error and return the UI to idle — never a silently hung "listening…" state.

## Evidence on Hand

- `openspec/changes/add-tauri-gui/proposal.md` and `design.md` — the accepted proposal and design rationale for this GUI, including numeric cold-open/responsiveness budgets.
- `openspec/changes/add-tauri-gui/specs/desktop-gui/spec.md` — the functional requirements (scenarios) the rebuilt UI must satisfy.
- `README.md` — existing CLI usage/positioning language (flags, setup instructions) that motivates the GUI's simplification.
- No logo, brand guide, or marketing copy exists yet; app is currently named "Transcriber" in `tauri.conf.json`/window title.

## Product Principles

- Remove setup friction, don't add configuration. Every control mirrors an existing CLI flag; no new capability is invented at the UI layer.
- Never let the user wonder if it's working: sidecar starting/crashed/idle states must always be visible, never a silent hang.
- Offline and private by default — no design decision should imply or require network access.
- Calm over clever. The audience is here to run a meeting, not to learn a tool.
