## Context

See proposal.md - Why. `start_live_session` (`src-tauri/src/sidecar.rs`) already builds the sidecar's argument list from UI-controlled parameters (`model`, `language`, `include_mic`, `mic_device`); this change adds one more (`output_path`) and two always-on flags. `transcriber.py` already supports `--output`, `--chunk-duration`, and `--actual-time` — no CLI-side changes needed, only how the GUI drives it.

## Goals / Non-Goals

**Goals:**
- Live sessions started from the GUI are saved to disk by default, with no required user action.
- Defaults match `start_teams_transcription.bat`'s invocation exactly, since that script is this project's own reference for the primary "meeting transcription" use case.

**Non-Goals:**
- File transcription's output handling — untouched, out of scope.
- Exposing `--chunk-duration`/`--actual-time` as user-adjustable settings — the `.bat` reference doesn't expose them either, so neither does this change.
- macOS/Linux live capture — `start_live_session` is already reachable only from the Windows-gated live-capture UI path (see `main.js`'s platform gate); this change doesn't add or remove that gating.

## Decisions

**Bare filename default, not a full path.** `defaultOutputFilename()` generates `transcript_YYYYMMDD_HHMMSS.txt` with no directory — mirroring `start_teams_transcription.bat`'s own relative `"%output_file%"`, which saves to the script's working directory. The sidecar inherits the GUI process's working directory the same way, so this reaches an equivalent (not identical) default location without needing a new dependency to resolve a "Documents" or similar directory. The Browse button (native save dialog, `tauri-plugin-dialog`'s existing `dialog:default` capability — already grants `allow-save`, confirmed against the plugin's own permission schema, no capability file change needed) covers anyone who wants a specific location.

**Hardcode `--chunk-duration 10 --actual-time`, don't expose new settings.** Matches the `.bat` reference's own fixed invocation. Alternative considered: add UI controls for these — rejected as speculative; the reference implementation this change is modeled on doesn't expose them, and no one has asked for them.

**Mic-default and output-path shipped together, one change.** They were implemented and tested together, and both trace back to the same reference invocation (`start_teams_transcription.bat`) and the same real-world testing session. Splitting them into two changes would be process overhead with no benefit — this isn't a platform split (per `01-adopt-platform-split-requirements`'s trigger: "different implementation required," which doesn't apply here) and both changes are small enough to review as one unit.

## Risks / Trade-offs

- [Default save location (GUI process's working directory) may not be obvious to a user who doesn't check Settings before starting] → Mitigation: the output-path field is pre-filled and visible in Session Settings before starting, not hidden; a user who opens Settings at all sees exactly where it's headed.
- [Hardcoded `--chunk-duration`/`--actual-time` can't be changed without a code change] → Accepted deliberately, matches proposal's Non-Goals; revisit if a real user asks for it.
