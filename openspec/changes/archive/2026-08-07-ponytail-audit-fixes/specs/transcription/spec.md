# Transcription

## MODIFIED Requirements

### Requirement: Transcribe audio files
The system SHALL transcribe an audio file using faster-whisper and return a list of segments (start, end, text) plus metadata (language, language probability, duration), applying voice activity detection to filter silence.

#### Scenario: Transcribe a file with detected language
- **WHEN** a user transcribes an audio file without specifying a language
- **THEN** the system auto-detects the language and returns segments with timestamps and the detected language with its probability

#### Scenario: Transcribe a missing file
- **WHEN** a user requests transcription of a file that does not exist
- **THEN** the system raises a file-not-found error
