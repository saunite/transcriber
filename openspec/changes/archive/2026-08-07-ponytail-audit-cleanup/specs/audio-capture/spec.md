## MODIFIED Requirements

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
