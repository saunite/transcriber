# Teams Launcher

## Purpose

Provide a batch script launcher for Teams meeting transcription with sensible defaults for wall-clock timestamps and silence auto-stop.

## Requirements

### Requirement: Default to wall-clock timestamps
Each platform's launcher script (`win-start-transcription.bat` on Windows, `linux-start-transcription.sh` on Linux, `mac-start-transcription.sh` on macOS) SHALL pass `--actual-time` to `transcriber.py` by default, so a user running the script without extra flags gets wall-clock timestamps rather than timestamps relative to the meeting/session start. Additional flags passed to the script SHALL still be appended after the defaults.

#### Scenario: Launch with no extra flags
- **WHEN** a user runs a platform's launcher script with no arguments (or only a name prefix)
- **THEN** the underlying `transcriber.py` invocation includes `--actual-time`, and output timestamps are wall-clock rather than relative

#### Scenario: Launch with additional flags
- **WHEN** a user runs a platform's launcher script with a name prefix and an additional flag (for example, `--silence-timeout 0`)
- **THEN** the underlying invocation includes both the default `--actual-time` and the user-supplied flag

### Requirement: An equivalent launcher exists on every supported platform
The system SHALL provide a platform-appropriate Teams-meeting launcher script for each of Windows, Linux, and macOS, sharing the same name-prefix-plus-pass-through-flags argument convention, producing a timestamped default output filename, and capturing both system audio and microphone (`--include-mic`) on all three platforms.

#### Scenario: Windows launcher uses WASAPI dual-capture
- **WHEN** a user runs `win-start-transcription.bat`
- **THEN** it launches `transcriber.py` with `--wasapi --include-mic`, capturing both system audio and microphone

#### Scenario: macOS launcher uses Core Audio Tap dual-capture
- **WHEN** a user runs `mac-start-transcription.sh`
- **THEN** it launches `transcriber.py` with `--coreaudio-tap --include-mic`, capturing both system audio and microphone

#### Scenario: Linux launcher uses the default dual-source capture path
- **WHEN** a user runs `linux-start-transcription.sh`
- **THEN** it launches `transcriber.py` with `--include-mic` (no `--wasapi`/`--coreaudio-tap`, since Linux's dual-source auto-detection is the default `--live` path), capturing both the real system-audio monitor and the microphone

### Requirement: Launcher prints the literal command instead of a banner
`win-start-transcription.bat` SHALL NOT print its own descriptive banner (title, source legend, output-filename notice). Instead, it SHALL print the exact `transcriber.py` command line it is about to execute, built and executed from the same value so the printed line cannot drift from the actual invocation.

#### Scenario: Launch prints the real command
- **WHEN** a user runs `win-start-transcription.bat sprint-review --silence-timeout 0`
- **THEN** the script prints the literal `python transcriber.py ...` invocation, including the resolved output filename and all passed-through flags, before running that exact command

#### Scenario: No separate banner text
- **WHEN** a user runs the launcher with any arguments
- **THEN** no title banner, source legend, or separately-worded output-filename notice is printed by the launcher itself
