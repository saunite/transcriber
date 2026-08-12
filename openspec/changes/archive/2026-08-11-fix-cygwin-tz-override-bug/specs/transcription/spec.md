## MODIFIED Requirements

### Requirement: Format timestamps for output
The system SHALL format segment times as relative `[MM:SS -> MM:SS]` ranges when actual-time mode is off. When actual-time mode is on: file transcription SHALL format wall-clock time as a `[start -> end]` range anchored to one base time captured once at the start of file processing; live/streaming transcription SHALL format wall-clock time as a single `YYYY-MM-DD HH:MM:SS` timestamp read directly from the system clock at the moment each output line is produced, not reconstructed from audio offsets or chunk duration. Local-time resolution SHALL reflect the OS's actual configured timezone regardless of an inherited shell environment variable the process can't correctly interpret.

#### Scenario: Relative timestamps
- **WHEN** actual-time mode is off
- **THEN** the system formats timestamps as relative ranges from the start of the audio

#### Scenario: Wall-clock timestamps for file transcription
- **WHEN** actual-time mode is on and transcribing a file
- **THEN** the system formats timestamps as a `[start -> end]` wall-clock range anchored to one base time captured when file transcription began

#### Scenario: Wall-clock timestamps for live transcription
- **WHEN** actual-time mode is on during live capture (simple or WASAPI mode)
- **THEN** the system stamps each output line with the current local date and time read from the system clock at the moment that line is produced, regardless of how long transcription of that chunk took

#### Scenario: Launched from a shell with an incompatible inherited TZ variable
- **WHEN** the process is launched from a shell (e.g. Cygwin) that exports an IANA-style `TZ` environment variable the Windows C runtime cannot parse
- **THEN** wall-clock timestamps still reflect the OS's actual configured local timezone, not UTC
