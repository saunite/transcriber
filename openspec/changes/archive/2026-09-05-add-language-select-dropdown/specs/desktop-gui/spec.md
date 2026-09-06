## ADDED Requirements

### Requirement: Language selection is a constrained dropdown
The system SHALL let the user choose the transcription language from a dropdown populated with every language the bundled model supports, defaulting to "Auto-detect," rather than free-text entry. Selecting "Auto-detect" SHALL behave identically to leaving the language unset (no `--language` flag passed), and selecting a specific language SHALL pass its code exactly as faster-whisper expects.

#### Scenario: Default is Auto-detect
- **WHEN** a user opens the app without changing the language field
- **THEN** the field reads "Auto-detect" and no `--language` flag is passed to the sidecar for a live session or file transcription

#### Scenario: User selects a specific language
- **WHEN** a user picks a specific language from the dropdown before starting a live session or transcribing a file
- **THEN** the sidecar is invoked with `--language <code>` for that language
