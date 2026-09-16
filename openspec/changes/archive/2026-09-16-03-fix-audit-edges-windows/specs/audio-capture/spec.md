## MODIFIED Requirements

### Requirement: Capture WASAPI loopback on Windows
The system SHALL support WASAPI loopback capture on Windows via pyaudiowpatch, including Bluetooth-connected output devices, and SHALL convert captured int16 PCM audio to float32 mono for transcription.

#### Scenario: WASAPI capture with default loopback
- **WHEN** a user starts WASAPI live capture without a device index
- **THEN** the system auto-detects the default output's loopback device and captures from it

#### Scenario: Similarly named output devices
- **WHEN** a user starts WASAPI live capture without a device index, and another output device's name contains the default output device's name (for example, the default is "Headphones" and another is "Headphones (2- Bluetooth)")
- **THEN** the system captures the loopback of the default output device itself, not the other device's

#### Scenario: WASAPI no loopback device
- **WHEN** no WASAPI loopback device can be found
- **THEN** the system prints an error and exits with a non-zero code

#### Scenario: Stereo to mono conversion
- **WHEN** WASAPI captures a stereo stream
- **THEN** the system averages the channels to mono and normalizes samples to the float32 range [-1, 1]
