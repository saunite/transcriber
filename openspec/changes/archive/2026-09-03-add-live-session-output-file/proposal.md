## Why

Live sessions started from the GUI were never saved to disk — `transcriber.py` only opens an output file when `--output` is given, and the GUI never passed one. A user's transcript existed only in the live view and vanished when the app closed. Separately, live capture defaulted to system-audio-only (microphone unchecked), which is silent for the tool's primary "meeting transcription" use case unless the user manually enables mic capture every session. Both surfaced from real testing on Windows hardware during `05-remove-installer-packaging-windows`'s verification; fixed directly per explicit request, tracked here after the fact.

## What Changes

- **New: live-session output file selection.** A "Output file" field in Session Settings, pre-filled with an auto-generated timestamped filename (`transcript_YYYYMMDD_HHMMSS.txt`), with a "Browse…" button opening a native save dialog to override the location/name. `start_live_session` gained an `output_path` parameter, passed through as `--output <path>` when non-empty.
- **Changed default: live capture is dual-source (system + mic) by default.** "Include microphone" now defaults to checked (was unchecked), and the microphone device selector is visible immediately rather than only after the user opts in.
- **Changed default: live sessions always pass `--chunk-duration 10 --actual-time`.** Not user-configurable — matches `start_teams_transcription.bat`'s fixed invocation shape, which this change's defaults are modeled on end-to-end: `python transcriber.py --live --wasapi --include-mic --model base --output "%output_file%" --chunk-duration 10 --actual-time %REST%`.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `desktop-gui`: adds two requirements — live-session transcript persistence (was entirely absent before) and dual-source-by-default live capture. Neither changes existing requirement text; both are genuinely new behavior with no prior requirement covering them.

## Impact

- **Changed**: `src-tauri/src/sidecar.rs` (`start_live_session` gains `output_path` param, always-on `--chunk-duration`/`--actual-time`), `src/index.html` (output-file field, mic checkbox default, mic-device field default-visible), `src/main.js` (dialog wiring, default-filename generation, `outputPath` passthrough), `src/style.css` (`.field-row`/`.browse-btn`, reusing existing `.settings-toggle`-style visual language — no new design direction).
- **Unaffected**: `transcriber.py`/`transcription_engine.py` (no CLI-side changes — `--output`/`--chunk-duration`/`--actual-time`/`--include-mic` all pre-existing flags), file transcription (out of scope — this only touches the live-session flow), macOS/Linux (the command this touches is already gated to the Windows-only live-capture UI path; no platform-specific code diverges here, it's identically Windows-only regardless).
- **Status**: already implemented and verified on real Windows hardware before this change was written — see tasks.md.
