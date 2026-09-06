## MODIFIED Requirements

### Requirement: Capture live system audio
The system SHALL capture system audio output in real time from a loopback source (Stereo Mix / Wave Out / loopback on Windows, the real PulseAudio/PipeWire monitor source on Linux) and deliver audio chunks to a callback for processing.

#### Scenario: Auto-detect loopback device
- **WHEN** a user starts live capture without specifying a device index
- **THEN** on Windows, the system auto-detects a loopback device by scanning available devices for loopback/monitor-named devices; on Linux, the system queries `pactl` for the real monitor source of the default (or specified) sink and captures it via a native `parec` subprocess, not through generic `sounddevice`/PortAudio device enumeration

#### Scenario: No loopback device found
- **WHEN** no loopback device can be auto-detected (on Linux: `pactl` is unavailable, or no monitor source exists)
- **THEN** the system lists available devices or sources, prints setup instructions, and raises an error

#### Scenario: Capture stops on user interrupt
- **WHEN** the user presses Ctrl+C during live capture
- **THEN** the system stops capturing gracefully

#### Scenario: Capture stops on user interrupt even when the underlying read stalls
- **WHEN** the user presses Ctrl+C during WASAPI live capture and the underlying audio read has stalled (no data returned, e.g. due to a device/format change, sleep/wake, or Bluetooth reconnect)
- **THEN** the system still stops promptly, without requiring the process to be killed externally
