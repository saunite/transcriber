# Desktop GUI

## Purpose

Provide a Tauri-based desktop GUI shell around the existing CLI/sidecar transcriber: fast app open, on-demand sidecar lifecycle, live transcript viewing, device selection, drag-and-drop file transcription, fully offline operation, and graceful degradation on macOS pending live capture support.

## Requirements

### Requirement: Fast, non-blocking app open
The application window SHALL be shown and interactive without waiting for the transcription sidecar or model to load. The sidecar process SHALL NOT be spawned at app startup.

#### Scenario: Cold launch
- **WHEN** a user launches the installed application
- **THEN** the main window is shown and its controls (menus, file drop target, settings) are usable before any Python sidecar process is spawned

#### Scenario: UI remains responsive during sidecar activity
- **WHEN** the sidecar is starting, transcribing, or capturing live audio
- **THEN** the UI thread never blocks on sidecar I/O; all sidecar communication happens asynchronously

### Requirement: On-demand sidecar lifecycle with crash recovery
The system SHALL spawn the bundled Python sidecar only when the user starts a live session or submits a file, SHALL stop it cleanly on user request or app quit, and SHALL detect unexpected sidecar exit and surface an error instead of leaving the UI in a stuck state.

#### Scenario: Start live capture
- **WHEN** a user starts a live capture session
- **THEN** the system spawns the sidecar with equivalent flags to the CLI's `--live` mode and shows a "starting" state until output begins

#### Scenario: Stop live capture
- **WHEN** a user stops an active live capture session
- **THEN** the system signals the sidecar to stop gracefully and waits for it to exit before returning to idle state

#### Scenario: Sidecar crashes mid-session
- **WHEN** the sidecar process exits unexpectedly while a session is active
- **THEN** the system shows an error with the sidecar's last output and returns the UI to idle state, without requiring an app restart

### Requirement: Live transcript view
The system SHALL display live transcript lines as they are produced, tagged by source (`SYS`/`MIC`) when dual-capture is active, by parsing the sidecar's existing stdout output.

#### Scenario: Single-source live transcript
- **WHEN** a live session without microphone capture is running
- **THEN** transcript lines appear in the UI as they are emitted by the sidecar, in order

#### Scenario: Dual-source live transcript
- **WHEN** a live session with `--include-mic`-equivalent capture is running
- **THEN** transcript lines are visually distinguished by `SYS` vs `MIC` source

#### Scenario: Unparsed sidecar output is not lost
- **WHEN** the sidecar emits a line that is not a recognized transcript line (headers, warnings, status messages)
- **THEN** the system surfaces it in a debug/log view rather than discarding it or crashing the parser

### Requirement: Device selection UI
The system SHALL let the user pick an audio input device from a list populated via the sidecar's machine-readable device listing, rather than requiring manual device index entry.

#### Scenario: Populate device picker
- **WHEN** the user opens device settings
- **THEN** the system invokes the sidecar's JSON device listing and populates a selectable list of devices with human-readable names

### Requirement: File transcription via drag-and-drop
The system SHALL accept a dropped (or browsed) video/audio file and transcribe it using the sidecar, producing output in the user's selected format (txt/srt/vtt).

#### Scenario: Drop a video file
- **WHEN** a user drags a supported video file onto the app
- **THEN** the system extracts audio and transcribes it via the sidecar, showing progress and the resulting transcript

#### Scenario: Drop an unsupported file
- **WHEN** a user drags a file with an unrecognized extension onto the app
- **THEN** the system shows an error without attempting to spawn the sidecar

### Requirement: Fully offline first run
The installed application SHALL be able to complete a live capture or file transcription with no network access, using the model and ffmpeg binary bundled in the installer.

#### Scenario: Offline transcription immediately after install
- **WHEN** a user installs the application on a machine with no network access and starts a transcription
- **THEN** the transcription completes successfully using the bundled model and bundled ffmpeg, with no download attempted

### Requirement: Graceful macOS degradation pending live capture support
On macOS, the system SHALL run the GUI shell and support file transcription, but SHALL disable live-capture controls with an explanatory message rather than presenting a non-functional live-capture UI.

#### Scenario: macOS user opens live capture
- **WHEN** a user on macOS opens the live capture screen
- **THEN** live-capture controls are disabled and a message explains that live capture is not yet available on macOS

#### Scenario: macOS file transcription works normally
- **WHEN** a user on macOS drops a file for transcription
- **THEN** the system transcribes it the same as on Windows/Linux
