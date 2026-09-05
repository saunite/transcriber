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

### Requirement: Live session stop is confirmed genuinely, not cosmetically
When a user stops a live session, the system SHALL report whether the stop actually succeeded, based on the real result of terminating the sidecar process, rather than assuming success.

#### Scenario: Stop succeeds
- **WHEN** a user stops an active live session and the sidecar process is successfully terminated
- **THEN** the system logs a confirmation that the session stopped

#### Scenario: Stop fails
- **WHEN** a user stops an active live session and terminating the sidecar process does not succeed
- **THEN** the system logs that the stop did not succeed, rather than silently reporting nothing

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

### Requirement: Sidecar always loads the bundled model explicitly
The system SHALL resolve the bundled model directory relative to the running application's own location and pass it to the sidecar explicitly for every spawned session (live or file), so the sidecar never depends on an ambient network/cache-based model lookup, whether running from an installed or portable location.

#### Scenario: Live session uses the bundled model
- **WHEN** a user starts a live session
- **THEN** the sidecar is spawned with an explicit path to the bundled model directory

#### Scenario: File transcription uses the bundled model
- **WHEN** a user transcribes a dropped file
- **THEN** the sidecar is spawned with an explicit path to the bundled model directory

### Requirement: Single no-install artifact per platform
The system SHALL be distributed as exactly one downloadable artifact per supported platform, each runnable without an installation step, without administrator privileges, and without writing to a system registry or shared system location. The system SHALL NOT be distributed as an installer package.

#### Scenario: Windows artifact
- **WHEN** a Windows user downloads the released artifact
- **THEN** they receive a single archive that, once extracted to any location, runs directly from its executable with no installation step and no administrator prompt

#### Scenario: Linux artifact
- **WHEN** a Linux user downloads the released artifact
- **THEN** they receive a single executable AppImage file that runs directly once marked executable, with no installation step

#### Scenario: macOS artifact
- **WHEN** a macOS user downloads the released artifact
- **THEN** they receive a single archive containing the application bundle, which runs directly once extracted, with no installation step

#### Scenario: Removal is deletion
- **WHEN** a user removes the application
- **THEN** deleting the downloaded artifact and its extracted contents leaves no application state elsewhere on the system, and no uninstaller is required

### Requirement: Bundled resources resolve identically across artifact forms
The system SHALL resolve its bundled model directory relative to the running application in every distributed artifact form, so that model loading behaves identically whether the application runs from an extracted folder, an AppImage, or an application bundle.

#### Scenario: Model loads from any artifact form
- **WHEN** the application starts a live session or a file transcription from any of its distributed artifact forms
- **THEN** the sidecar is spawned with an explicit path to the bundled model directory resolved relative to the running application, and no network or cache-based model lookup is attempted

### Requirement: Launches without a console or terminal window
The application SHALL open its own window and nothing else when launched by a user, on every supported platform. No console, terminal, or command-prompt window SHALL be displayed at launch, and none SHALL appear when the application spawns its transcription sidecar or any process the sidecar itself spawns.

#### Scenario: Double-click launch on Windows
- **WHEN** a user double-clicks the application executable from the extracted portable folder
- **THEN** only the application window appears, with no console window shown before, beside, or behind it

#### Scenario: Launch on Linux and macOS
- **WHEN** a user launches the AppImage from a file manager, or double-clicks the application bundle in Finder
- **THEN** only the application window appears, with no terminal window opened

#### Scenario: Starting a transcription
- **WHEN** the application spawns its sidecar for a live session or a file transcription
- **THEN** no console window appears or flashes for the sidecar process or for any process it spawns

#### Scenario: Development builds keep their console
- **WHEN** a developer runs a debug build of the application
- **THEN** console output remains available, so the release-build console suppression does not hinder development

### Requirement: Live session transcript is saved to a file
The system SHALL save every live session's transcript to a file, defaulting to an auto-generated, timestamped filename when the user has not specified one, and SHALL let the user choose a different file location and name via a native save dialog before starting a session.

#### Scenario: Default output filename
- **WHEN** a user starts a live session without changing the output file field
- **THEN** the transcript is saved using an auto-generated timestamped filename, and the file exists after the session ends

#### Scenario: User picks a custom output location
- **WHEN** a user selects "Browse…" and chooses a file location and name before starting a live session
- **THEN** the transcript is saved to that location instead of the default

### Requirement: Live capture defaults to dual-source (system + microphone) capture
The system SHALL default a new live session to capturing both system audio and the microphone, with a 10-second transcription chunk duration and wall-clock timestamps, while still letting the user disable microphone capture before starting.

#### Scenario: Default session captures both sources
- **WHEN** a user starts a live session without changing the microphone setting
- **THEN** both system audio and microphone audio are captured and tagged accordingly in the transcript

#### Scenario: User disables microphone capture
- **WHEN** a user unchecks "Include microphone" before starting a live session
- **THEN** only system audio is captured

### Requirement: WASAPI loopback device can be overridden, with a discouraging default message
The system SHALL default live capture to an auto-detected WASAPI loopback device, SHALL let the user optionally specify a different device by index, and SHALL display a message stating that the default is auto-detected WASAPI and that overriding is not recommended.

#### Scenario: Default session uses auto-detection
- **WHEN** a user starts a live session without setting a device override
- **THEN** the system uses the auto-detected WASAPI loopback device, exactly as it did before this override existed

#### Scenario: Override message is visible
- **WHEN** a user opens Session Settings
- **THEN** a message near the device override field states that the default is the auto-detected WASAPI device and that overriding is not recommended

#### Scenario: User overrides the device
- **WHEN** a user enters a specific device index in the override field and starts a live session
- **THEN** the system uses that device index instead of auto-detection

### Requirement: Transcript time is rendered at true scale
The system SHALL position transcript lines along a continuous time axis so that the interval between them is proportional to the elapsed time between them, making periods with no speech visible as proportional space rather than being collapsed.

#### Scenario: A silent stretch is visible
- **WHEN** a session contains a period of several minutes during which no transcript line was produced, and the user views the transcript
- **THEN** that period occupies proportionally more space along the time axis than a period of a few seconds, so the gap is visible without reading the timestamps

#### Scenario: Both sources share one axis
- **WHEN** a dual-source session has produced lines from both system audio and microphone
- **THEN** lines from both sources are positioned against the same shared time axis, so their relative timing is directly readable

### Requirement: Transcript time scale is adjustable
The system SHALL let the user adjust the scale of the transcript's time axis, from a scale that fits a long session into a single view to a scale at which transcript text is comfortably readable, without altering the proportionality of the intervals themselves.

#### Scenario: Compressing a long session
- **WHEN** a user viewing a long session reduces the time scale
- **THEN** more of the session becomes visible at once and the relative proportions of speech and silence are preserved

#### Scenario: Expanding for reading
- **WHEN** a user increases the time scale
- **THEN** transcript text is presented at a comfortably readable size, still positioned along the same proportional axis

### Requirement: A stalled capture is distinguishable from a silent one
During a live session, the system SHALL visually distinguish "capturing normally, with no speech currently detected" from "no transcript output has arrived when it was expected", so a stalled engine is not mistaken for a quiet room.

#### Scenario: Quiet room during a healthy session
- **WHEN** a live session is running normally and no speech has been detected for a short period
- **THEN** the interface indicates that capture is active and simply has nothing to record

#### Scenario: Engine stops producing output
- **WHEN** a live session is running and no transcript output has arrived for substantially longer than the expected interval between chunks
- **THEN** the interface indicates that expected output has not arrived, in a way visually distinct from the quiet-room state
