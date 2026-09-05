## ADDED Requirements

### Requirement: Select Linux dual-source live capture mode
The system SHALL route live capture through the auto-detected monitor/loopback source with optional concurrent microphone capture via `--include-mic` and `--mic-device` when neither `--wasapi` nor `--coreaudio-tap` is set (the Linux default live-capture path).

#### Scenario: Default live capture with microphone
- **WHEN** a user runs `--live --include-mic --mic-device N` with no `--wasapi` or `--coreaudio-tap`
- **THEN** the system captures the monitor source and microphone concurrently, labeling segments `[SYS]` and `[MIC]`

#### Scenario: Default live capture without microphone
- **WHEN** a user runs `--live` without `--include-mic`, `--wasapi`, or `--coreaudio-tap`
- **THEN** the system captures only the monitor source, unchanged from today's behavior
