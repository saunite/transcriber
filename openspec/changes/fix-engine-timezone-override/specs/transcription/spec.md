## MODIFIED Requirements

### Requirement: Format timestamps for output
The system SHALL format segment times as relative `[MM:SS -> MM:SS]` ranges when actual-time mode is off. When actual-time mode is on: file transcription SHALL format wall-clock time as a `[start -> end]` range anchored to one base time captured once at the start of file processing; live/streaming transcription SHALL format wall-clock time as a single `YYYY-MM-DD HH:MM:SS` timestamp giving the local time at which that line's speech began, derived from when that audio source started delivering audio plus the speech's position in that source's audio, and unaffected by how long buffering or transcription took. Local-time resolution SHALL follow the timezone the session is configured to use, including a `TZ` environment variable the platform's own date and time library can interpret, so that the engine and any application running it read the same local time. Where an inherited `TZ` cannot be interpreted by the platform's library, local time SHALL fall back to the OS's configured timezone rather than to UTC.

#### Scenario: Relative timestamps
- **WHEN** actual-time mode is off
- **THEN** the system formats timestamps as relative ranges from the start of the audio

#### Scenario: Wall-clock timestamps for file transcription
- **WHEN** actual-time mode is on and transcribing a file
- **THEN** the system formats timestamps as a `[start -> end]` wall-clock range anchored to one base time captured when file transcription began

#### Scenario: Wall-clock timestamps for live transcription
- **WHEN** actual-time mode is on during live capture
- **THEN** the system stamps each output line with the local date and time at which that line's speech began, regardless of how long transcription of that chunk took

#### Scenario: Lines from one chunk carry their own times
- **WHEN** actual-time mode is on during live capture and one chunk yields several segments spoken seconds apart
- **THEN** each line's stamp reflects when its own speech began, so the lines do not all share one stamp

#### Scenario: Both sources share one clock
- **WHEN** actual-time mode is on, system audio and the microphone use different chunk durations, and the same moment of speech is heard on both
- **THEN** the lines from both sources carry stamps for that same moment, within the precision of the stamp, rather than differing by how long each source's chunk took to fill and transcribe

#### Scenario: Launched from a shell with an incompatible inherited TZ variable
- **WHEN** the process is launched from a shell (e.g. Cygwin) that exports an IANA-style `TZ` environment variable the Windows C runtime cannot parse
- **THEN** wall-clock timestamps still reflect the OS's actual configured local timezone, not UTC

#### Scenario: Launched with a TZ the platform understands
- **WHEN** the process is launched with a `TZ` environment variable its platform's date and time library can interpret, naming a zone other than the machine's default
- **THEN** wall-clock timestamps are in that zone, the same as any other program started from that environment

#### Scenario: The engine reports the zone it resolved
- **WHEN** a live session starts
- **THEN** the engine's own output names the timezone and offset its timestamps use, so a reader can tell what the engine believed local time to be without inferring it from the stamps
