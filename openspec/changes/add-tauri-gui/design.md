## Context

The transcriber's engine (`transcriber.py` + helpers) is a working, tested Python CLI. It already does everything the GUI needs: file transcription, live dual-stream capture (WASAPI loopback + mic), device enumeration, and incremental output to stdout and a transcript file. The engine's live-mode output is already line-oriented and stable: each emitted transcript line is a single `print` (and matching file write) in one of two forms:

- Relative: `[MM:SS -> MM:SS] text` or `[MM:SS -> MM:SS] [SYS] text` / `[MIC] text`
- Wall-clock (`--actual-time`): `[YYYY-MM-DD HH:MM:SS] text` / with `[SYS]`/`[MIC]` tag

`--list-devices` output is multi-line per device (name, channel count, sample rate across 3 separate `print`s) with no delimiter — not safely machine-parseable as-is.

No JS/web or Rust code exists in this repo yet; this is a greenfield addition alongside the existing Python tool, which stays a fully independent, still-supported CLI.

## Goals / Non-Goals

**Goals:**
- App window opens and is interactive quickly, independent of Python/model load time.
- Reuse the existing engine unmodified for all transcription/capture logic — the GUI is a shell, not a reimplementation.
- Fully offline after install: bundled model + bundled ffmpeg, no first-run download.
- Live transcript, device picker, and file-drop transcription, matching what the CLI already supports (no new engine capabilities beyond the one JSON device-list flag).
- Graceful degradation on macOS: GUI runs, file transcription works, live-capture controls are disabled with an explanatory message until `add-macos-capture` lands.

**Non-Goals:**
- Rewriting the engine in Rust/whisper.cpp (tracked as a future option, not this change).
- Mobile support.
- Speaker diarization, translation UI beyond what `--task translate` already exposes, or any new transcription feature — this change is packaging/UI only.
- macOS live capture implementation (separate change).

## Decisions

### 1. Sidecar, not a rewrite
The Python engine ships as a frozen executable (PyInstaller `--onefile`, one build per OS) and is bundled as a Tauri external binary. Rust spawns it as a subprocess and communicates over its stdout/stdin, exactly as a human would run the CLI today.

**Alternative considered**: rewrite the engine in Rust (whisper-rs/cpal). Rejected for v1 — throws away tested, working capture/transcription code for a size win that hasn't been measured yet. Revisit only if the sidecar's real-world installer size or cold-start proves unacceptable (see Open Questions).

### 2. IPC = parse the existing stdout line format; one small additive JSON flag for devices
Live transcript lines are already single-line and bracket-delimited, so the Rust sidecar wrapper reads stdout line-by-line and matches them with a small regex:

```
^\[(?<ts>[^\]]+)\](?:\s\[(?<tag>SYS|MIC)\])?\s(?<text>.*)$
```

Matched lines become `transcript-line` events (`{ ts, tag: "SYS"|"MIC"|null, text }`) emitted to the webview over a Tauri event channel. Unmatched lines (headers, warnings, `(no speech detected)`, emoji-prefixed status prints) are forwarded as raw `sidecar-log` events into a collapsible debug panel — never dropped, never crash the parser.

Device enumeration is the one place plain regex parsing is a bad fit (multi-line records, no delimiter), so the engine gains a small additive flag, `--list-devices-json`, that prints the same device data as a JSON array instead of the current human-readable text. `--list-devices` itself is untouched. This is the only engine change in this proposal.

**Alternative considered**: a full structured event protocol (JSON-lines) for *all* engine output. Rejected — it would touch every print/emit call in a working, tested module for marginal robustness gain over regexing an already-stable, single-purpose log format; the one genuinely fragile case (multi-line device list) is fixed directly instead.

### 3. Sidecar lifecycle: launch on demand, not at app startup
The Rust backend does **not** spawn the Python sidecar (or load the model) when the app opens. The window renders and becomes interactive immediately; the sidecar is spawned only when the user starts a live session or submits a file for transcription. This is what makes "opens quickly" achievable at all — model load time (see below) is decoupled from app-open time.

- **Start**: spawn on first action; UI shows a "starting engine…" state until the sidecar's first output line arrives (or a `--warmup`/ready marker if load time proves user-visible enough to need one — see Open Questions).
- **Stop**: on explicit user stop, send Ctrl-C-equivalent (the engine already handles `SIGINT` gracefully via its existing handler) and wait for clean exit with a timeout; on app quit, the same stop path runs before the window closes.
- **Crash**: if the sidecar process exits unexpectedly (non-zero/unsignaled exit while the UI expects it running), the Rust backend surfaces an error toast with the sidecar's last stderr output and returns the UI to idle state — never a silently hung "listening…" indicator.

### 4. Cold-open / responsiveness — concrete budgets
"Lightweight = opens quickly and is responsive" is operationalized as:

| Metric | Budget | Notes |
|---|---|---|
| Window shown | < 300ms from launch | Tauri window creation only; no Python involved |
| UI interactive (menus, file drop target, settings) | < 500ms from launch | Never blocks on sidecar/model |
| Sidecar process spawned → first stdout line | tracked, not gated | Cold model load (~1-3s typical for `base` on CPU/SSD); shown as a distinct "starting…" state, not counted against app-open |
| UI thread blocked on sidecar I/O | 0ms, always | stdout reader runs on a background task; UI updates via async events only |

Acceptance test: launch the packaged app with a cold OS file cache, assert window-shown and UI-interactive timings via a scripted harness; assert no UI-thread frame exceeds a responsiveness threshold (e.g. no single dropped frame > 100ms) during sidecar start and during live transcript streaming.

### 5. Installer packaging: bundle model + ffmpeg
The installer bundles: the frozen sidecar binary, the `base` faster-whisper model files (~145MB, matching the CLI's existing default), and a static ffmpeg binary per OS. Total installer size will land in the several-hundred-MB range — this is expected and accepted per the explicit "bundle the model, no download step" requirement; it trades installer size for a fully offline first run.

Build pipeline per OS (CI matrix, one job per target):
1. Freeze the Python engine (PyInstaller) → platform sidecar binary.
2. Download/verify the `base` model files and the ffmpeg binary for that OS into Tauri's bundled resources.
3. `tauri build` → native installer (`.msi` on Windows, `.AppImage`/`.deb` on Linux, `.dmg` shell-only on macOS per this proposal's scope).

**Alternative considered**: download the model on first run to keep the installer small. Rejected per explicit user requirement — offline-first-run matters more than installer size here.

## Risks / Trade-offs

- **[Risk]** Regex-based stdout parsing couples the GUI to the exact wording/format of engine log lines → engine changes could silently break the GUI's transcript view. **Mitigation**: a small fixture test in the sidecar-wrapper test suite that runs the real engine against a short sample and asserts the regex captures every emitted transcript line; CI fails loudly on drift instead of the GUI silently misparsing in the field.
- **[Risk]** Installer size (several hundred MB) partially undercuts "lightweight" in the download-size sense, even though it serves the "opens quickly, offline" sense the user actually asked for. **Mitigation**: none needed for v1 per explicit requirement; revisit only if user feedback flags install size as a real problem.
- **[Risk]** PyInstaller freezing of `faster-whisper`/`ctranslate2` can be finicky (hidden imports, native library bundling) and differs per OS. **Mitigation**: build and smoke-test the frozen sidecar per OS in CI before wiring it into the Tauri bundle.
- **[Risk]** macOS shell ships with live-capture controls visibly present but non-functional if not carefully gated. **Mitigation**: the UI must check platform at runtime and disable/hide live-capture affordances on macOS (not just document it), so this proposal doesn't ship a broken-looking feature.

## Open Questions

- Does model load time (~1-3s+ on slower disks/CPUs) need an explicit "ready" marker from the engine, or is "first output line" a good enough readiness signal for the UI's "starting…" state? Lean toward reusing existing output rather than adding a marker unless real testing shows it's needed.
- Should the bundled model size (`base`, ~145MB) be user-configurable at install time (e.g. offer `tiny` for a smaller installer), or fixed for v1 simplicity? Proposal assumes fixed `base` for v1, matching the CLI default.
