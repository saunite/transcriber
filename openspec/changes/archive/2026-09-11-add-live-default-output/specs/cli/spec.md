## ADDED Requirements

### Requirement: Live capture saves a transcript by default
When `--live` is run without `--output`, the system SHALL save the transcript to a new file named `transcript_<YYYYMMDD_HHMMSS>.txt` in the current directory, stamped with the time the session starts, and SHALL name that file in its first output line. `--output <path>` SHALL save to the given path instead. `--no-output` SHALL print the transcript without saving it, and combining `--no-output` with `--output` SHALL be rejected with an error.

#### Scenario: Bare live capture
- **WHEN** a user runs `--live` with neither `--output` nor `--no-output`
- **THEN** the transcript is written to `transcript_<YYYYMMDD_HHMMSS>.txt` in the current directory, and the first output line names that file

#### Scenario: Explicit output path
- **WHEN** a user runs `--live --output meeting.txt`
- **THEN** the transcript is written to `meeting.txt`, as before

#### Scenario: Print-only session
- **WHEN** a user runs `--live --no-output`
- **THEN** the transcript is printed only, no file is created, and the output states that no transcript file is being saved

#### Scenario: Conflicting flags
- **WHEN** a user runs `--live --output meeting.txt --no-output`
- **THEN** the command exits with an error explaining that the two flags cannot be combined, before any capture starts

#### Scenario: Consecutive sessions
- **WHEN** a user runs two bare `--live` sessions one after another
- **THEN** each session writes its own, differently stamped file, and neither overwrites the other
