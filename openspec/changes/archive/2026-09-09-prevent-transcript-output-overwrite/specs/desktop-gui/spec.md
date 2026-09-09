## MODIFIED Requirements

### Requirement: Live session transcript is saved to a file
The system SHALL save every live session's transcript to a file, defaulting to an auto-generated, timestamped filename when the user has not specified one, and SHALL let the user choose a different file location and name via a native save dialog before starting a session. The filename actually used SHALL be stamped with the current time at the moment each session starts — not fixed once when the app opens or once when a path is chosen — so starting another session without editing the output field never overwrites a previous session's transcript.

#### Scenario: Default output filename
- **WHEN** a user starts a live session without changing the output file field
- **THEN** the transcript is saved using an auto-generated timestamped filename, and the file exists after the session ends

#### Scenario: Starting a second session without editing the output field
- **WHEN** a user stops a live session and starts a new one without editing the output file field
- **THEN** the new session's transcript is saved to a freshly-timestamped file distinct from the first, and the first session's transcript file is left intact

#### Scenario: User picks a custom output location
- **WHEN** a user selects "Browse…" and chooses a file location and name before starting a live session
- **THEN** the transcript is saved to that location, with the current timestamp stamped into the filename so reusing the same browsed location across two starts still doesn't collide
