# Teams Launcher

## Purpose

Provide a batch script launcher for Teams meeting transcription with sensible defaults for wall-clock timestamps and silence auto-stop.

## Requirements

### Requirement: Default to wall-clock timestamps
`start_teams_transcription.bat` SHALL pass `--actual-time` to `transcriber.py` by default, so a user running the script without extra flags gets wall-clock timestamps rather than timestamps relative to the meeting/session start. Additional flags passed to the script SHALL still be appended after the defaults.

#### Scenario: Launch with no extra flags
- **WHEN** a user runs `start_teams_transcription.bat` with no arguments (or only a name prefix)
- **THEN** the underlying `transcriber.py` invocation includes `--actual-time`, and output timestamps are wall-clock rather than relative

#### Scenario: Launch with additional flags
- **WHEN** a user runs `start_teams_transcription.bat sprint-review --silence-timeout 0`
- **THEN** the underlying invocation includes both the default `--actual-time` and the user-supplied `--silence-timeout 0`
