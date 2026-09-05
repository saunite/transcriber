## ADDED Requirements

### Requirement: Capture dual-source live audio on Linux
The system SHALL support concurrent system-audio and microphone capture on Linux, using the auto-detected PulseAudio/PipeWire monitor source for system audio and an ordinary input device for the microphone, without requiring a platform-specific loopback API.

#### Scenario: Linux dual-source capture with default devices
- **WHEN** a user starts live capture on Linux with microphone inclusion enabled, no `--wasapi` or `--coreaudio-tap` flag, and a working monitor source is available
- **THEN** the system captures both the monitor source and the microphone concurrently and labels transcription segments `[SYS]`/`[MIC]` exactly as the Windows and macOS dual-source paths do

#### Scenario: No monitor source available
- **WHEN** a user starts live capture with microphone inclusion enabled on Linux and no monitor/loopback source can be auto-detected
- **THEN** the system reports the same "could not auto-detect loopback device" error it already gives for system-audio-only capture, rather than silently falling back to mic-only capture
