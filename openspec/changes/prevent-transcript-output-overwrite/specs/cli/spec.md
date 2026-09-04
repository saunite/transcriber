## ADDED Requirements

### Requirement: File transcription's auto-derived output filename includes a timestamp
When transcribing a file without an explicit `--output` path, the system SHALL derive the output filename from the input file's name and include a timestamp, so transcribing the same input file more than once never overwrites an earlier run's transcript. An explicit `--output` path SHALL be used exactly as given, with no timestamp added.

#### Scenario: Same file transcribed twice without --output
- **WHEN** a user transcribes the same input file twice without specifying `--output`
- **THEN** each run writes to a distinct, timestamped output filename, and neither run's transcript is overwritten by the other

#### Scenario: Explicit --output is honored exactly
- **WHEN** a user supplies an explicit `--output` path
- **THEN** the system writes to that exact path, unchanged and unstamped
