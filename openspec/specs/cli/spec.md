# CLI

## Purpose

Provide a command-line interface for the transcriber: selecting input sources, help/setup utilities, WASAPI live capture mode, and graceful interruption handling.

## Requirements

### Requirement: Accept input source flags
The system SHALL require exactly one input source: `--file` for file transcription or `--live` for live capture, and SHALL print usage and exit with an error when neither is given.

#### Scenario: No input source specified
- **WHEN** a user runs the CLI without `--file` or `--live`
- **THEN** the system prints help and an error message and exits with a non-zero code

#### Scenario: File input
- **WHEN** a user passes `--file path/to/video.mp4`
- **THEN** the system transcribes the file

#### Scenario: Live input
- **WHEN** a user passes `--live`
- **THEN** the system captures and transcribes audio in real time

### Requirement: Provide help and setup utilities
The system SHALL provide `--list-devices` to enumerate audio devices and `--setup-help` to print audio loopback setup instructions, each exiting after printing.

#### Scenario: List devices requested
- **WHEN** a user runs with `--list-devices`
- **THEN** the system prints audio devices and exits without transcribing

#### Scenario: Setup help requested
- **WHEN** a user runs with `--setup-help`
- **THEN** the system prints loopback setup instructions and exits

### Requirement: Select WASAPI live capture mode
The system SHALL route live capture through WASAPI loopback on Windows when `--wasapi` is set, with optional concurrent microphone capture via `--include-mic` and `--mic-device`.

#### Scenario: WASAPI with microphone
- **WHEN** a user runs `--live --wasapi --include-mic --mic-device N`
- **THEN** the system captures system audio via WASAPI loopback and microphone concurrently, labeling segments `[SYS]` and `[MIC]`

#### Scenario: WASAPI without microphone
- **WHEN** a user runs `--live --wasapi` without `--include-mic`
- **THEN** the system captures only system audio via WASAPI loopback

### Requirement: Handle interruption gracefully
The system SHALL handle Ctrl+C by stopping capture, finalizing the transcript, cleaning up resources, and exiting without a crash.

#### Scenario: User interrupts live capture
- **WHEN** the user presses Ctrl+C during live capture
- **THEN** the system stops capture and worker threads, closes output and WAV files, releases audio devices, and saves any transcript produced

#### Scenario: User interrupts file transcription
- **WHEN** the user presses Ctrl+C during file transcription
- **THEN** the system stops cleanly and exits with the interrupted exit code
