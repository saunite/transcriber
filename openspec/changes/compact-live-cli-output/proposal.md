## Why

Live/Teams-mode startup output is roughly 35 lines of ceremony before a single transcript line appears, and shutdown adds 2-3 more — traced during this session to four independent print sites that don't coordinate: `start_teams_transcription.bat`'s own banner, `transcriber.py`'s generic CLI banner, `transcriber.py`'s live-mode banner plus device-detection prints, and `wasapi_capture.py`'s own capture-start/stop prints. Nothing printed is wrong — it's the same handful of facts (output filename, device names, "starting"/"stopped") each stated multiple times in different words by different files that don't know about each other.

## What Changes

- `transcriber.py`: new `--verbose` flag (default off). Default live-mode output collapses to a 3-line preamble (identity/output file; model+language+capture-mode+device summary; listening/auto-stop line) plus a one-line stop summary. The existing `===` banners, explicit per-device auto-detect prints, and the Model/Language/Chunk/Mode block move behind `--verbose`.
- `wasapi_capture.py`: its own "Capturing from"/"Capturing audio..."/"Capture stopped by user" prints move behind the same `verbose` flag, passed through from `transcriber.py`.
- `start_teams_transcription.bat`: its own banner (title, `[SYS]`/`[MIC]` legend, output-filename notice, auto-stop notice) is removed and replaced with echoing the literal `python transcriber.py ...` command line about to run — built into one variable and both echoed and executed from it, so the printed line can never drift from what actually runs.
- Scoped to the live/Teams path only — file-mode's end-of-run `Transcription Summary` block is untouched (a smaller, one-time summary, not the repeated-every-run ceremony this targets).

**Deliberately not building**: deleting the detail outright. It's genuinely useful when an auto-detected device is wrong — this project's own history has more than one real bug found exactly that way during hardware testing. Gating it behind an opt-in flag keeps it one flag away instead of gone.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `cli`: adds a new requirement — live-capture output is compact by default, with a `--verbose` flag restoring today's full detail.
- `teams-launcher`: adds a new requirement — the launcher prints the literal command it's about to run instead of its own banner.

## Impact

- **Changed**: `transcriber.py`, `wasapi_capture.py`, `start_teams_transcription.bat`.
- **Unaffected**: `transcription_engine.py` (its "Loading model..."/"✓ Model loaded successfully" lines stay as the one always-on loading-progress beat, unchanged), file-mode's summary output, the GUI/sidecar (`src-tauri/src/sidecar.rs`'s `TRANSCRIPT_LINE_RE` already only recognizes `[ts] [tag] text`-shaped lines and routes everything else — banners included — to the debug log panel; that routing is unchanged by this proposal).
