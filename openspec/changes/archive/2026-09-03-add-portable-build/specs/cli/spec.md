## ADDED Requirements

### Requirement: Accept an explicit local model path
The system SHALL provide `--model-path <dir>` to load the whisper model from a local directory directly, bypassing the network/cache-based model name lookup, for both file and live transcription modes.

#### Scenario: File transcription with explicit model path
- **WHEN** a user runs `--file audio.wav --model-path C:\path\to\model`
- **THEN** the system loads the model from the given directory instead of resolving `--model` by name

#### Scenario: Live capture with explicit model path
- **WHEN** a user runs `--live --model-path C:\path\to\model`
- **THEN** the system loads the model from the given directory instead of resolving `--model` by name

#### Scenario: No model path given
- **WHEN** `--model-path` is not passed
- **THEN** the system behaves exactly as before, resolving `--model` by name
