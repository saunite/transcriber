## MODIFIED Requirements

### Requirement: Select Linux dual-source live capture mode
The system SHALL route live capture through the auto-detected monitor/loopback source with optional concurrent microphone capture via `--include-mic` and `--mic-device` when neither `--wasapi` nor `--coreaudio-tap` is set (the Linux default live-capture path). A microphone device that cannot open at the transcription sample rate (16 kHz) SHALL be opened at its own default sample rate and resampled to 16 kHz rather than failing the session. A microphone that cannot be auto-detected SHALL likewise not fail the session: the system SHALL fall back to the first device reporting input channels, and SHALL only exit when no input device exists at all.

#### Scenario: Default live capture with microphone
- **WHEN** a user runs `--live --include-mic --mic-device N` with no `--wasapi` or `--coreaudio-tap`
- **THEN** the system captures the monitor source and microphone concurrently, labeling segments `[SYS]` and `[MIC]`

#### Scenario: Default live capture without microphone
- **WHEN** a user runs `--live` without `--include-mic`, `--wasapi`, or `--coreaudio-tap`
- **THEN** the system captures only the monitor source, unchanged from today's behavior

#### Scenario: Microphone that refuses 16 kHz
- **WHEN** the selected or auto-detected microphone refuses to open at 16 kHz (for example a raw ALSA `hw:` device that only accepts 44.1 or 48 kHz)
- **THEN** the system opens it at the device's default sample rate, resamples its audio to 16 kHz, and transcribes `[MIC]` segments as usual, instead of exiting with an "Invalid sample rate" error

#### Scenario: Microphone that cannot be auto-detected
- **WHEN** a user runs `--live --include-mic` without `--mic-device` and the audio layer cannot resolve a default input device, while other devices with input channels are present
- **THEN** the system selects the first such device, names it in its output, and transcribes `[MIC]` segments as usual, instead of printing "Could not auto-detect microphone" and exiting

#### Scenario: Bundled audio libraries do not hide the host's devices
- **WHEN** a released Linux artifact runs on a distribution whose audio-library layout differs from the machine that built it
- **THEN** live capture enumerates the same input devices and monitor sources that the host system exposes to other audio applications, rather than a reduced set that omits the default input
