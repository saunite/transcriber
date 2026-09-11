## MODIFIED Requirements

### Requirement: Live session transcript is saved to a file
The system SHALL save every live session's transcript to a file, defaulting to an auto-generated, timestamped file in the user's Documents folder (the home folder if the system reports no Documents folder) when the user has not specified one, and SHALL show the full path of that file in the output field. It SHALL let the user choose a different file location and name via a native save dialog before starting a session, and SHALL save a bare filename typed into the output field in the same default folder. The filename actually used SHALL be stamped with the current local time at the moment each session starts — not fixed once when the app opens or once when a path is chosen — so starting another session without editing the output field never overwrites a previous session's transcript.

#### Scenario: Default output filename
- **WHEN** a user starts a live session without changing the output file field
- **THEN** the transcript is saved in the Documents folder using an auto-generated timestamped filename, the output field shows that file's full path, and the file exists after the session ends

#### Scenario: Starting a second session without editing the output field
- **WHEN** a user stops a live session and starts a new one without editing the output file field
- **THEN** the new session's transcript is saved to a freshly-timestamped file distinct from the first, and the first session's transcript file is left intact

#### Scenario: User picks a custom output location
- **WHEN** a user selects "Browse…" and chooses a file location and name before starting a live session
- **THEN** the transcript is saved to that location, with the current timestamp stamped into the filename so reusing the same browsed location across two starts still doesn't collide

#### Scenario: User types a bare filename
- **WHEN** a user types a filename without a folder (for example `standup.txt`) into the output field and starts a session
- **THEN** the transcript is saved in the Documents folder under that name, with the session's timestamp stamped in

#### Scenario: Timestamp uses local time
- **WHEN** a session starts at 15:43:34 local time
- **THEN** the stamped filename contains `_154334`, whatever the system's UTC offset

## ADDED Requirements

### Requirement: File transcripts are saved next to the recording
The system SHALL save the transcript of a dropped or chosen file in the same folder as that file, named `<recording name>_transcript_<timestamp>.<format>`, independent of the folder the application was started from.

#### Scenario: Transcribing a recording from another folder
- **WHEN** a user transcribes `~/Downloads/talk.mp4` as txt
- **THEN** the transcript is saved as `~/Downloads/talk_transcript_<timestamp>.txt`, and no transcript is written to the application's working directory
