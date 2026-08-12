## Why

`--actual-time` (wall-clock timestamps) was fixed to read the live system clock in `fix-actual-time-drift`, but it's still an opt-in flag. Nothing in `start_teams_transcription.bat` passes it, so anyone launching a Teams meeting transcription the normal way still gets timestamps relative to the meeting/session start rather than the real clock. The user ran the launcher script as-is, didn't add the flag themselves, and got relative time.

## What Changes

- `start_teams_transcription.bat` passes `--actual-time` by default in its `transcriber.py` invocation, so wall-clock timestamps are on without the user having to remember the flag.
- No change to `transcriber.py` itself — `--actual-time` keeps working exactly as before and can still be combined with other flags passed to the launcher.

## Capabilities

### New Capabilities
- `teams-launcher`: Default arguments `start_teams_transcription.bat` passes to `transcriber.py` (currently undocumented as a spec-level contract). This change adds the requirement that it defaults to wall-clock timestamps.

### Modified Capabilities
(none — `transcription`'s timestamp-formatting requirement and the `cli` spec's `--actual-time` flag behavior are unchanged; only the Teams launcher's default arguments change)

## Impact

- `start_teams_transcription.bat`: default `transcriber.py` invocation gains `--actual-time`.
- `start_transcription.sh` (Linux launcher) is out of scope for this change — not what was asked.
