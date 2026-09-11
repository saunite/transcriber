## MODIFIED Requirements

### Requirement: File transcription via drag-and-drop
The system SHALL accept dropped (or browsed) video/audio files and transcribe them using the sidecar, producing output in the user's selected format (txt/srt/vtt). Files SHALL be transcribed one at a time: files added while a transcription is running SHALL join a visible queue instead of starting concurrently, and the system SHALL show which file is being transcribed and the state of every queued file.

#### Scenario: Drop a video file
- **WHEN** a user drags a supported video file onto the app
- **THEN** the system extracts audio and transcribes it via the sidecar, showing progress and the resulting transcript

#### Scenario: Drop an unsupported file
- **WHEN** a user drags a file with an unrecognized extension onto the app
- **THEN** the system shows an error without attempting to spawn the sidecar, and the file does not join the queue

#### Scenario: Drop a file while another is transcribing
- **WHEN** a user drops a supported file while a file transcription is running
- **THEN** the file joins the queue as waiting, no second transcription starts, and it is transcribed after the files ahead of it finish

#### Scenario: Add several files at once
- **WHEN** a user drops several supported files at once, or selects several in the file dialog
- **THEN** all of them join the queue in order and are transcribed one after another

#### Scenario: Progress is visible
- **WHEN** a file transcription is running
- **THEN** the File panel names the file being transcribed, and every queued file shows whether it is waiting, transcribing, done, or failed

#### Scenario: A queued file fails
- **WHEN** a file's transcription fails
- **THEN** that file is marked failed and the next waiting file starts

### Requirement: Device selection UI
The system SHALL let the user pick an audio input device from a list populated via the sidecar's machine-readable device listing, rather than requiring manual device index entry. The list's first entry, selected by default, SHALL be the system's default input device, which leaves the choice of device to the engine's auto-detection.

#### Scenario: Populate device picker
- **WHEN** the user opens device settings
- **THEN** the system invokes the sidecar's JSON device listing and populates a selectable list of devices with human-readable names

#### Scenario: Default microphone is the system default
- **WHEN** a user starts a live session with the microphone included and without choosing a microphone device
- **THEN** no device is passed to the sidecar, and the engine uses the system's default input device, exactly as the command line does without `--mic-device`

## ADDED Requirements

### Requirement: Live session uses the running platform's capture mode
The system SHALL start a live session with the capture mode of the platform it runs on: WASAPI loopback on Windows, the Core Audio process tap on macOS, and the default system-audio-plus-microphone capture on Linux. It SHALL NOT pass another platform's capture option to the sidecar.

#### Scenario: Live session on Linux
- **WHEN** a user on Linux starts a live session from the GUI
- **THEN** the session starts capturing system audio (and the microphone, when included) and transcribes it, with no platform-mismatch error

#### Scenario: Live session on Windows
- **WHEN** a user on Windows starts a live session from the GUI
- **THEN** the sidecar is started in WASAPI loopback mode, as before
