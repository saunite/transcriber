## Why

`start_teams_transcription.bat` (Windows-only dual-capture launcher for Teams meetings) has no Linux or macOS counterpart today. A user on those platforms has to hand-build the equivalent `transcriber.py` invocation themselves, with no equivalent of the Windows script's sensible defaults (wall-clock timestamps, output filename, chunk duration).

## What Changes

- **Rename** `start_teams_transcription.bat` → `win-start-transcription.bat` (behavior unchanged — same flags, same defaults, same `--wasapi --include-mic` dual-capture).
- **Add** `linux-start-transcription.sh`, mirroring the Windows script's structure (name-prefix argument, pass-through flags, timestamped output filename, wall-clock timestamps by default) with `--include-mic` dual-capture (system audio + microphone, tagged `[SYS]`/`[MIC]`) — genuine parity with the Windows and macOS launchers. This capability landed in the meantime via `add-linux-dual-source-live-capture` (real dual-source engine support for `transcribe_live_simple`) and `fix-linux-loopback-detection` (real system-audio auto-detection via `pactl`/`parec`, verified with actual audio); this proposal originally scoped Linux to system-audio-only pending that work, but it's done and verified now, so the launcher should reflect that instead of shipping a disclosure that's no longer true.
- **Add** `mac-start-transcription.sh`, mirroring the same structure using `--coreaudio-tap --include-mic` (macOS's dual-capture path, per `add-macos-capture`) — genuine behavioral parity with the Windows script, since macOS's engine path already supports dual-capture.
- Existing `linux_start_transcription.sh` (underscore-named, at repo root, simple auto-detect live transcription — a different, pre-existing script) is left untouched; it serves a different purpose (general-purpose live transcription, not the Teams-meeting-specific defaults) and this change does not touch, rename, or fold it in.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `teams-launcher`: the existing "Default to wall-clock timestamps" requirement is generalized from naming one Windows-only script to covering all three platform launchers identically. A new requirement added: all three platforms' launchers use the same dual-capture argument convention (`--include-mic` plus the platform's own system-audio flag/default).

## Impact

- **Renamed**: `start_teams_transcription.bat` → `win-start-transcription.bat` (content unchanged).
- **New files**: `linux-start-transcription.sh`, `mac-start-transcription.sh`.
- **Unchanged**: `transcriber.py` and all engine code — this is launcher-script-only; Linux's `--include-mic` dual-capture engine support already exists (`add-linux-dual-source-live-capture`, `fix-linux-loopback-detection`), this change just wires the launcher to use it.
- **Coordination — same file, a still-open change**: `compact-live-cli-output` (in-progress, 13/15 tasks, paused on Windows-hardware verification) already changed `start_teams_transcription.bat`'s content (the compact command-echo behavior) and has its own **unarchived** delta spec at `openspec/changes/compact-live-cli-output/specs/teams-launcher/spec.md` that still names the file by its pre-rename name. This change's tasks include updating that pending delta's filename reference, so it stays correct whenever `compact-live-cli-output` eventually archives and syncs — the two changes are otherwise unrelated (one is command-echo behavior, this one is the rename + new platform scripts) and don't need to apply in a specific order, but the stale-filename text would otherwise slip through unnoticed.
- **Coordination — `add-linux-dual-source-live-capture`**: that change's own task 4.1 ("update `linux-start-transcription.sh` to pass `--include-mic` and drop its system-audio-only disclosure, and update the corresponding `teams-launcher` spec requirement") is satisfied by this change writing the script correctly from the start, since that change landed first.
