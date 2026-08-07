# Audio Capture


## Purpose

Capture live system audio (and optionally microphone audio) for real-time transcription, including WASAPI loopback support on Windows and device listing.

## Requirements

### Requirement: Capture live system audio
The system SHALL capture system audio output in real time from a loopback source (Stereo Mix / Wave Out / loopback on Windows, PulseAudio/PipeWire monitor on Linux) and deliver audio chunks to a callback for processing.

#### Scenario: Auto-detect loopback device
- **WHEN** a user starts live capture without specifying a device index
- **THEN** the system auto-detects a loopback device by scanning available devices for loopback/monitor sources

#### Scenario: No loopback device found
- **WHEN** no loopback device can be auto-detected
- **THEN** the system lists available devices, prints setup instructions, and raises an error

#### Scenario: Capture stops on user interrupt
- **WHEN** the user presses Ctrl+C during live capture
- **THEN** the system stops capturing gracefully

### Requirement: Capture microphone audio
The system SHALL capture microphone input concurrently with system audio when microphone inclusion is enabled, tagging its segments distinctly from system audio.

#### Scenario: Capture with microphone enabled
- **WHEN** a user starts live capture with microphone inclusion enabled and a valid mic device
- **THEN** the system captures both system audio and microphone audio concurrently and labels transcription segments from the mic as `[MIC]`

#### Scenario: Invalid microphone device
- **WHEN** the specified microphone device is not an input device or cannot be queried
- **THEN** the system reports an error and aborts the run

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

### Requirement: Save captured audio to WAV
The system SHALL optionally save captured audio (system and/or microphone) to WAV files alongside the transcript, and SHALL merge system and mic recordings into a stereo WAV when both exist, using ffmpeg.

#### Scenario: Save audio enabled in WASAPI mode
- **WHEN** a user enables audio saving in WASAPI live mode with mic capture
- **THEN** the system writes system audio to `<base>_sys.wav`, mic audio to `<base>_mic.wav`, and a merged stereo `<base>_merged.wav`

#### Scenario: Merge uses ffmpeg
- **WHEN** both system and mic WAV files exist and ffmpeg is available on PATH
- **THEN** the system merges them into a stereo WAV with system audio on one channel and mic audio on the other

#### Scenario: Merge without ffmpeg
- **WHEN** both WAV files exist but ffmpeg is not available
- **THEN** the system prints a warning that the merge was skipped and continues with the separate WAV files
