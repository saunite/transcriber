## Why

Two independent overwrite risks existed, both in output-file naming. Live sessions default their output field to a timestamped filename once, at page load — start a second session later without editing the field (the ordinary "record another meeting" flow) and the second run truncates the first session's transcript, since `transcriber.py` opens `args.output` in `'w'` mode. File-mode transcription derives its output name entirely server-side from the input filename (`{stem}_transcript.{format}` in the current working directory) with no timestamp at all — the GUI never passes `--output` — so transcribing the same file twice (after a bad take, or after switching language) silently overwrites the first transcript, with no warning either way.

## What Changes

- `src/main.js`: `startLiveSession()` now stamps the output path fresh at the moment a session actually starts (`withFreshTimestamp()`), not just once when the app opens, and writes the resolved path back into the visible field so what will be written is what's shown.
- `transcriber.py`: file-mode's auto-derived output name (the branch taken whenever `--output` isn't explicit, which is always, from the GUI) now includes a timestamp, mirroring the live-mode naming convention.

**Deliberately not building**: file-existence checks or an overwrite-confirmation dialog. No filesystem plugin/capability is registered (`src-tauri/capabilities/default.json` grants only `core:default` and `dialog:default`), and probing for existence would need a new permission grant plus a round trip before every start. A fresh per-run timestamp makes the collision structurally near-impossible without adding that surface — see `design.md` for the ceiling this leaves.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `desktop-gui`: modifies "Live session transcript is saved to a file" — the auto-generated filename is now re-stamped at the moment each session starts, not fixed once at app launch.
- `cli`: adds a new requirement — file-mode transcription's auto-derived output filename always carries a timestamp when no explicit `--output` is given.

## Impact

- **Changed**: `src/main.js` (`startLiveSession`, `defaultOutputFilename`/`withFreshTimestamp` helpers), `transcriber.py` (output-path determination in `main()`).
- **Unaffected**: `src-tauri/src/sidecar.rs` (still just forwards whatever `outputPath`/`file_path` it's given — no IPC shape change), `transcription_engine.py`, the live-mode incremental-write path (untouched — still gated on `args.output` being set, which it always is now that `main.js` always sends a stamped one).
