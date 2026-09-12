## MODIFIED Requirements

### Requirement: Capture microphone audio
The system SHALL capture microphone input concurrently with system audio when microphone inclusion is enabled, tagging its segments distinctly from system audio. When no microphone device is specified and the audio layer reports no default input device, the system SHALL fall back to the first available device that has input channels rather than ending the session, and SHALL only abort when no input device exists at all.

#### Scenario: Capture with microphone enabled
- **WHEN** a user starts live capture with microphone inclusion enabled and a valid mic device
- **THEN** the system captures both system audio and microphone audio concurrently and labels transcription segments from the mic as `[MIC]`

#### Scenario: Invalid microphone device
- **WHEN** the specified microphone device is not an input device or cannot be queried
- **THEN** the system reports an error and aborts the run

#### Scenario: No default input device, but input devices exist
- **WHEN** a user starts live capture with microphone inclusion enabled and no explicit microphone device, and the audio layer cannot resolve a default input device
- **THEN** the system selects the first device reporting input channels, names the device it chose, and continues the session instead of exiting

#### Scenario: No input devices at all
- **WHEN** a user starts live capture with microphone inclusion enabled and the audio layer reports no device with input channels
- **THEN** the system reports that no microphone was found, names the commands for listing devices and selecting one explicitly, and exits non-zero
