# Audio Capture

## Purpose

Capture live system audio (and optionally microphone audio) for real-time transcription, including WASAPI loopback support on Windows and device listing.

## Requirements

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

### Requirement: Capture microphone audio
The system SHALL capture microphone input concurrently with system audio when microphone inclusion is enabled, tagging its segments distinctly from system audio.

#### Scenario: Capture with microphone enabled
- **WHEN** a user starts live capture with microphone inclusion enabled and a valid mic device
- **THEN** the system captures both system audio and microphone audio concurrently and labels transcription segments from the mic as `[MIC]`

#### Scenario: Invalid microphone device
- **WHEN** the specified microphone device is not an input device or cannot be queried
- **THEN** the system reports an error and aborts the run

### Requirement: Capture dual-source live audio on Linux
The system SHALL support concurrent system-audio and microphone capture on Linux, using the auto-detected PulseAudio/PipeWire monitor source for system audio and an ordinary input device for the microphone, without requiring a platform-specific loopback API.

#### Scenario: Linux dual-source capture with default devices
- **WHEN** a user starts live capture on Linux with microphone inclusion enabled, no `--wasapi` or `--coreaudio-tap` flag, and a working monitor source is available
- **THEN** the system captures both the monitor source and the microphone concurrently and labels transcription segments `[SYS]`/`[MIC]` exactly as the Windows and macOS dual-source paths do

#### Scenario: No monitor source available
- **WHEN** a user starts live capture with microphone inclusion enabled on Linux and no monitor/loopback source can be auto-detected
- **THEN** the system reports the same "could not auto-detect loopback device" error it already gives for system-audio-only capture, rather than silently falling back to mic-only capture

### Requirement: Capture WASAPI loopback on Windows
The system SHALL support WASAPI loopback capture on Windows via pyaudiowpatch, including Bluetooth-connected output devices, and SHALL convert captured int16 PCM audio to float32 mono for transcription.

#### Scenario: WASAPI capture with default loopback
- **WHEN** a user starts WASAPI live capture without a device index
- **THEN** the system auto-detects the default output's loopback device and captures from it

#### Scenario: WASAPI no loopback device
- **WHEN** no WASAPI loopback device can be found
- **THEN** the system prints an error and exits with a non-zero code

#### Scenario: Stereo to mono conversion
- **WHEN** WASAPI captures a stereo stream
- **THEN** the system averages the channels to mono and normalizes samples to the float32 range [-1, 1]

### Requirement: List audio devices
The system SHALL list all available audio devices with their input channel counts and default sample rates when requested.

#### Scenario: List devices requested
- **WHEN** a user requests the list of audio devices
- **THEN** the system prints each device's index, name, max input channels, and default sample rate and exits
