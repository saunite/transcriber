## Why

`start_teams_transcription.bat` (Windows-only dual-capture launcher for Teams meetings) has no Linux or macOS counterpart today. A user on those platforms has to hand-build the equivalent `transcriber.py` invocation themselves, with no equivalent of the Windows script's sensible defaults (wall-clock timestamps, output filename, chunk duration).

## What Changes

- **Rename** `start_teams_transcription.bat` → `win-start-transcription.bat` (behavior unchanged — same flags, same defaults, same `--wasapi --include-mic` dual-capture).
- **Add** `linux-start-transcription.sh`, mirroring the Windows script's structure (name-prefix argument, pass-through flags, timestamped output filename, wall-clock timestamps by default) but capturing **system audio only** — `--include-mic` dual-capture is not implemented for Linux's capture path (`transcribe_live_simple` never checks `args.include_mic`; only the WASAPI and Core Audio Tap paths do). The script SHALL NOT pass `--include-mic`, and SHALL say so in its own banner/comments, rather than silently dropping the microphone while claiming parity with the Windows script. Linux dual-capture is scoped out to a separate change (see below).
- **Add** `mac-start-transcription.sh`, mirroring the same structure using `--coreaudio-tap --include-mic` (macOS's dual-capture path, per `add-macos-capture`) — genuine behavioral parity with the Windows script, since macOS's engine path already supports dual-capture.
- Existing `linux_start_transcription.sh` (underscore-named, at repo root, simple auto-detect live transcription — a different, pre-existing script) is left untouched; it serves a different purpose (general-purpose live transcription, not the Teams-meeting-specific defaults) and this change does not touch, rename, or fold it in.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `teams-launcher`: the existing "Default to wall-clock timestamps" requirement is generalized from naming one Windows-only script to covering all three platform launchers identically. New requirements added for the Linux and macOS scripts' own defaults and for the Linux script's explicit mic-capture limitation.

## Impact

- **Renamed**: `start_teams_transcription.bat` → `win-start-transcription.bat` (content unchanged).
- **New files**: `linux-start-transcription.sh`, `mac-start-transcription.sh`.
- **Unchanged**: `transcriber.py` and all engine code — this is launcher-script-only, no `--include-mic` behavior is added for Linux by this change.
- **Coordination — same file, a still-open change**: `compact-live-cli-output` (in-progress, 13/15 tasks, paused on Windows-hardware verification) already changed `start_teams_transcription.bat`'s content (the compact command-echo behavior) and has its own **unarchived** delta spec at `openspec/changes/compact-live-cli-output/specs/teams-launcher/spec.md` that still names the file by its pre-rename name. This change's tasks include updating that pending delta's filename reference, so it stays correct whenever `compact-live-cli-output` eventually archives and syncs — the two changes are otherwise unrelated (one is command-echo behavior, this one is the rename + new platform scripts) and don't need to apply in a specific order, but the stale-filename text would otherwise slip through unnoticed.
- **Deliberately out of scope**: implementing `--include-mic` support for Linux's `transcribe_live_simple` capture path — real engine work (a second `sounddevice` stream plus mixing), tracked as its own separate change.
