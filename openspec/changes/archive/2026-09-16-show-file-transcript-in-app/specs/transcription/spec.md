## MODIFIED Requirements

### Requirement: Transcribe audio files
The system SHALL transcribe an audio file using faster-whisper and return a list of segments (start, end, text) plus metadata (language, language probability, duration), applying voice activity detection to filter silence. Each segment SHALL be reported as it is produced, not only when the whole file is done.

#### Scenario: Transcribe a file with detected language
- **WHEN** a user transcribes an audio file without specifying a language
- **THEN** the system auto-detects the language and returns segments with timestamps and the detected language with its probability

#### Scenario: Transcribe a missing file
- **WHEN** a user requests transcription of a file that does not exist
- **THEN** the system raises a file-not-found error

#### Scenario: Segments are reported while the file is transcribed
- **WHEN** a long recording is transcribed
- **THEN** each segment is both written to the output file and reported to the caller as it is produced, so a caller can show the transcript building up
