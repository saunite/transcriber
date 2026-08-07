## ADDED Requirements

### Requirement: Parse timestamped transcript lines
The system SHALL parse transcript lines in the format `[MM:SS -> MM:SS] text` and `[MM:SS -> MM:SS] [SYS|MIC] text`, supporting both `MM:SS` and `HH:MM:SS` timestamps, and SHALL skip comment (`#`) and blank lines.

#### Scenario: Parse a standard timestamped line
- **WHEN** a line matches `[00:05 -> 00:08] Welcome to the meeting`
- **THEN** the system records start time 5s, end time 8s, and text "Welcome to the meeting"

#### Scenario: Parse a line with channel label
- **WHEN** a line matches `[17:30 -> 17:35] [MIC] I have a question`
- **THEN** the system records the entry and prefixes the text with `[MIC]`

#### Scenario: Parse an hour-precision timestamp
- **WHEN** a line contains an `HH:MM:SS` timestamp
- **THEN** the system parses it correctly to seconds including the hour component

#### Scenario: Skip lines without valid timestamps
- **WHEN** a line does not match the timestamp pattern or has an invalid time
- **THEN** the system warns and skips the line

### Requirement: Convert parsed entries to SRT
The system SHALL convert parsed entries into SRT format with sequential numbering, `HH:MM:SS,mmm --> HH:MM:SS,mmm` cue times, and blank lines between cues.

#### Scenario: Successful conversion
- **WHEN** at least one valid entry is parsed
- **THEN** the system writes an SRT file with numbered cues and correct time formatting

#### Scenario: No valid entries
- **WHEN** no valid timestamped entries are found in the input
- **THEN** the system prints an error and exits with a non-zero code

### Requirement: Default output naming
The system SHALL write the SRT to the input path with an `.srt` extension when no output path is given, and SHALL use an explicit `--output` path when provided.

#### Scenario: Default output path
- **WHEN** a transcript file is converted without `--output`
- **THEN** the system writes the SRT next to the input file with the same base name and `.srt` extension
