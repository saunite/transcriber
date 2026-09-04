## ADDED Requirements

### Requirement: Live session transcript is saved to a file
The system SHALL save every live session's transcript to a file, defaulting to an auto-generated, timestamped filename when the user has not specified one, and SHALL let the user choose a different file location and name via a native save dialog before starting a session.

#### Scenario: Default output filename
- **WHEN** a user starts a live session without changing the output file field
- **THEN** the transcript is saved using an auto-generated timestamped filename, and the file exists after the session ends

#### Scenario: User picks a custom output location
- **WHEN** a user selects "Browse…" and chooses a file location and name before starting a live session
- **THEN** the transcript is saved to that location instead of the default

### Requirement: Live capture defaults to dual-source (system + microphone) capture
The system SHALL default a new live session to capturing both system audio and the microphone, with a 10-second transcription chunk duration and wall-clock timestamps, while still letting the user disable microphone capture before starting.

#### Scenario: Default session captures both sources
- **WHEN** a user starts a live session without changing the microphone setting
- **THEN** both system audio and microphone audio are captured and tagged accordingly in the transcript

#### Scenario: User disables microphone capture
- **WHEN** a user unchecks "Include microphone" before starting a live session
- **THEN** only system audio is captured
