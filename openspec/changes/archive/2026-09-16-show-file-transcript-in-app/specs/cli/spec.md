## ADDED Requirements

### Requirement: File transcription prints its transcript as it goes
When transcribing a file, the system SHALL print each transcribed segment to standard output as it is produced, in the same timestamped form it writes to the output file, so a caller reading the process's output sees the transcript while the run is in progress rather than only when it ends. Progress display SHALL NOT be mixed into that output.

#### Scenario: Transcribing a recording from the command line
- **WHEN** a user transcribes a file
- **THEN** each segment appears on standard output, timestamped, as it is transcribed, and the saved transcript file contains the same lines

#### Scenario: Progress does not corrupt the transcript output
- **WHEN** a caller reads only the standard output of a file transcription
- **THEN** it contains the transcript lines and no progress-bar redraws
