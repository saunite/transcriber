## ADDED Requirements

### Requirement: Diarize audio to identify speakers
The system SHALL identify speaker turns in audio using pyannote.audio when diarization is enabled, returning diarization segments (start, end, speaker label), and SHALL require a Hugging Face token (via `--hf-token` or `HUGGINGFACE_TOKEN` env var) for authentication.

#### Scenario: Diarization with token provided
- **WHEN** a user enables diarization with a valid Hugging Face token
- **THEN** the system runs speaker diarization and produces speaker-labeled segments

#### Scenario: Diarization without token
- **WHEN** a user enables diarization without a valid token
- **THEN** the system reports that the Hugging Face token is required

### Requirement: Constrain speaker count
The system SHALL accept exact, minimum, and maximum speaker counts to guide diarization, with exact count taking precedence when provided.

#### Scenario: Exact number of speakers
- **WHEN** a user supplies an exact speaker count
- **THEN** the system diarizes expecting that number of speakers

#### Scenario: Speaker count range
- **WHEN** a user supplies only min and max speakers
- **THEN** the system diarizes within that range

### Requirement: Merge transcription with diarization
The system SHALL merge transcription segments with diarization segments, assigning each transcribed segment a speaker label based on time overlap.

#### Scenario: Segments get speaker labels
- **WHEN** diarization completes after transcription
- **THEN** each transcription segment is tagged with a speaker label (e.g., SPEAKER_00)

### Requirement: Report speaker statistics
The system SHALL compute and print per-speaker statistics including total duration, number of segments, and word counts.

#### Scenario: Statistics printed after diarization
- **WHEN** diarization completes
- **THEN** the system prints each speaker's total duration, segment count, and word count

### Requirement: Format transcript with speaker labels
The system SHALL format TXT transcripts with speaker labels prefixed per segment when diarization is enabled.

#### Scenario: TXT output with speakers
- **WHEN** a user requests TXT output with diarization
- **THEN** the system writes each segment prefixed with its speaker label

### Requirement: Gracefully handle missing diarization dependencies
The system SHALL degrade gracefully when torch/pyannote.audio are not installed, noting that diarization is unavailable and continuing with transcription in simple chunked mode.

#### Scenario: Diarization dependencies missing
- **WHEN** a user enables live transcription without torch installed
- **THEN** the system warns that diarization is unavailable and proceeds without it
