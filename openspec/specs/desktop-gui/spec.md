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
The system SHALL spawn the bundled Python sidecar only when the user starts a live session or submits a file, SHALL stop it cleanly on user request or app quit, and SHALL detect unexpected sidecar exit and surface an error instead of leaving the UI in a stuck state. An exit of a live session's engine that the user did not request SHALL be treated as unexpected whatever its exit code, except a stop at the configured silence limit, which is an expected, clean end the user SHALL be informed of rather than warned about (see "Live sessions stop after a configurable silence"). Stopping SHALL terminate every process the sidecar launch created, including any process the frozen binary re-executes into, since that descendant is what holds the audio device. The system SHALL NOT begin a file transcription while a live session's engine is still running, and SHALL NOT begin a live session while a live session's engine or a file transcription's engine is still running. The exit of an earlier session's engine SHALL NOT affect a session started after it.

#### Scenario: Start live capture
- **WHEN** a user starts a live capture session
- **THEN** the system spawns the sidecar with equivalent flags to the CLI's `--live` mode and shows a "starting" state until output begins

#### Scenario: Stop live capture
- **WHEN** a user stops an active live capture session
- **THEN** the system signals the sidecar to stop gracefully and waits for it to exit before returning to idle state

#### Scenario: Stopping reaches the process that owns capture
- **WHEN** a user stops a live session whose frozen sidecar has re-executed into a worker process
- **THEN** the worker process is terminated too, so no process retains the microphone or system-audio device after the session ends

#### Scenario: Graceful stop preserves the transcript
- **WHEN** a live session that is saving a transcript is stopped
- **THEN** the engine is given the chance to flush and close its transcript file before being terminated, so the saved transcript is complete rather than truncated mid-line

#### Scenario: File transcription is refused while a live engine runs
- **WHEN** a file transcription is submitted while a live session's engine has not yet exited
- **THEN** the system does not start a second engine alongside it, and the user is told why rather than being shown output from both

#### Scenario: Live session is refused while another engine runs
- **WHEN** a user starts a live session while a file transcription's engine or another live session's engine has not yet exited
- **THEN** the system does not start a second engine, and the user is told why

#### Scenario: Sidecar crashes mid-session
- **WHEN** the sidecar process exits unexpectedly while a session is active
- **THEN** the system shows an error with the sidecar's last output and returns the UI to idle state, without requiring an app restart

#### Scenario: Engine ends a session by itself with a success code
- **WHEN** a live session's engine exits with a success code without the user having stopped it, for a reason other than the silence limit
- **THEN** the system tells the user the session ended unexpectedly, shows the engine's last output, and returns the UI to idle state

#### Scenario: A quick restart is not disturbed by the previous session
- **WHEN** a user stops a live session and immediately starts a new one, and the previous engine's exit is reported after the new session has started
- **THEN** the new session is neither reported as ended nor loses the ability to be stopped

### Requirement: Live session stop is confirmed genuinely, not cosmetically
When a user stops a live session, the system SHALL report whether the stop actually succeeded, based on the real result of terminating the sidecar process, rather than assuming success. A stop SHALL count as successful only when no process from that session survives holding the audio device; a termination call that returns successfully while capture continues SHALL NOT be reported as success.

#### Scenario: Stop succeeds
- **WHEN** a user stops an active live session and the sidecar process is successfully terminated
- **THEN** the system logs a confirmation that the session stopped

#### Scenario: Stop fails
- **WHEN** a user stops an active live session and terminating the sidecar process does not succeed
- **THEN** the system logs that the stop did not succeed, rather than silently reporting nothing

#### Scenario: A surviving capture process is reported as a failed stop
- **WHEN** a stop is attempted and a process from that session is still running after the attempt
- **THEN** the system reports the stop as unsuccessful and says that capture may still be active, instead of reporting success because a kill call returned without error

#### Scenario: Capture indicators reflect real state
- **WHEN** no live session is running
- **THEN** the system's capture-source indicators do not present system audio or the microphone as active, so the UI never shows capture while the engine is idle

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
The system SHALL let the user pick an audio input device from a list populated via the sidecar's machine-readable device listing, rather than requiring manual device index entry. The list's first entry, selected by default, SHALL be the system's default input device, which leaves the choice of device to the engine's auto-detection.

#### Scenario: Populate device picker
- **WHEN** the user opens device settings
- **THEN** the system invokes the sidecar's JSON device listing and populates a selectable list of devices with human-readable names

#### Scenario: Default microphone is the system default
- **WHEN** a user starts a live session with the microphone included and without choosing a microphone device
- **THEN** no device is passed to the sidecar, and the engine uses the system's default input device, exactly as the command line does without `--mic-device`

### Requirement: File transcription via drag-and-drop
The system SHALL accept dropped (or browsed) video/audio files and transcribe them using the sidecar, producing output in the user's selected format (txt/srt/vtt). Files SHALL be transcribed one at a time: files added while a transcription is running SHALL join a visible queue instead of starting concurrently, and the system SHALL show which file is being transcribed and the state of every queued file.

#### Scenario: Drop a video file
- **WHEN** a user drags a supported video file onto the app
- **THEN** the system extracts audio and transcribes it via the sidecar, and the transcript appears in the file view line by line while the transcription runs, not only once it finishes

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

### Requirement: Fully offline first run
The application SHALL be able to complete a live capture or file transcription with no network access, using the model bundled with the application, and SHALL require no separately installed media tool for either flow.

#### Scenario: Offline transcription immediately after install
- **WHEN** a user installs the application on a machine with no network access and starts a transcription
- **THEN** the transcription completes successfully using the bundled model, with no download attempted

#### Scenario: Dropped video file on a machine without ffmpeg
- **WHEN** a user drops a video file onto the application on a machine with no ffmpeg installed
- **THEN** the file is transcribed normally, using the sidecar's bundled decoder rather than an external process

### Requirement: Graceful macOS degradation pending live capture support
On macOS, the system SHALL run the GUI shell and support file transcription, but SHALL disable live-capture controls with an explanatory message rather than presenting a non-functional live-capture UI.

#### Scenario: macOS user opens live capture
- **WHEN** a user on macOS opens the live capture screen
- **THEN** live-capture controls are disabled and a message explains that live capture is not yet available on macOS

#### Scenario: macOS file transcription works normally
- **WHEN** a user on macOS drops a file for transcription
- **THEN** the system transcribes it the same as on Windows/Linux

### Requirement: Sidecar always loads the bundled model explicitly
The system SHALL pass the sidecar an explicit model directory for every spawned session (live or file), so the sidecar never depends on an ambient network/cache-based model lookup, whether running from an installed or portable location. That directory SHALL be the bundled model directory, resolved relative to the running application's own location, unless the user has chosen a model folder, in which case it SHALL be the chosen folder. Before spawning a session with a chosen folder, the system SHALL verify the folder exists and contains a model file; if it does not, the system SHALL refuse to start the session, tell the user the folder does not hold a usable model, and start no engine.

#### Scenario: Live session uses the bundled model
- **WHEN** a user who has not chosen a model folder starts a live session
- **THEN** the sidecar is spawned with an explicit path to the bundled model directory

#### Scenario: File transcription uses the bundled model
- **WHEN** a user who has not chosen a model folder transcribes a dropped file
- **THEN** the sidecar is spawned with an explicit path to the bundled model directory

#### Scenario: Session uses the chosen model folder
- **WHEN** a user who has chosen a model folder starts a live session or transcribes a file
- **THEN** the sidecar is spawned with an explicit path to that folder, and not to the bundled model directory

#### Scenario: Chosen folder no longer holds a model
- **WHEN** a user starts a session with a chosen folder that has been moved, deleted, or holds no model file
- **THEN** the session is refused with a message saying the folder does not hold a usable model, and no sidecar is spawned

### Requirement: Portable artifact per platform, with native installers alongside
The system SHALL be distributed, for each supported platform, as one portable artifact that runs without an installation step, without administrator privileges, and without writing to a system registry or shared system location. Native installer packages SHALL be offered in addition to the portable artifact, never instead of it, so every release contains the portable artifact for every platform it supports.

#### Scenario: Windows portable artifact
- **WHEN** a Windows user downloads the portable artifact
- **THEN** they receive a single archive that, once extracted to any location, runs directly from its executable with no installation step and no administrator prompt

#### Scenario: Linux portable artifact
- **WHEN** a Linux user downloads the portable artifact
- **THEN** they receive a single executable AppImage file that runs directly once marked executable, with no installation step

#### Scenario: macOS portable artifact
- **WHEN** a macOS user downloads the portable artifact
- **THEN** they receive a single archive containing the application bundle, which runs directly once extracted, with no installation step

#### Scenario: Removing a portable artifact is deletion
- **WHEN** a user removes a portable artifact
- **THEN** deleting the downloaded artifact and its extracted contents leaves no application state elsewhere on the system beyond the OS-managed web-view caches, and no uninstaller is required

#### Scenario: Installer offered alongside
- **WHEN** a release offers a native installer for a platform
- **THEN** the same release also offers that platform's portable artifact

### Requirement: Bundled resources resolve identically across artifact forms
The system SHALL resolve its bundled model directory relative to the running application in every distributed artifact form, so that model loading behaves identically whether the application runs from an extracted folder, an AppImage, an application bundle, or a location an installer or package manager installed it to.

#### Scenario: Model loads from any artifact form
- **WHEN** the application starts a live session or a file transcription from any of its distributed artifact forms
- **THEN** the sidecar is spawned with an explicit path to the bundled model directory resolved relative to the running application, and no network or cache-based model lookup is attempted

#### Scenario: Model loads from an installed location
- **WHEN** the application was installed by a native installer or a package manager and starts a transcription with no network access
- **THEN** the transcription completes using the model installed with the application

### Requirement: Launches without a console or terminal window
The application SHALL open its own window and nothing else when launched by a user, on every supported platform. No console, terminal, or command-prompt window SHALL be displayed at launch, and none SHALL appear when the application spawns its transcription sidecar or any process the sidecar itself spawns.

#### Scenario: Double-click launch on Windows
- **WHEN** a user double-clicks the application executable from the extracted portable folder
- **THEN** only the application window appears, with no console window shown before, beside, or behind it

#### Scenario: Launch on Linux and macOS
- **WHEN** a user launches the AppImage from a file manager, or double-clicks the application bundle in Finder
- **THEN** only the application window appears, with no terminal window opened

#### Scenario: Launch from an installed menu entry
- **WHEN** a user launches the application from the Start Menu, desktop application menu, or Applications folder entry created by an installer or package manager
- **THEN** only the application window appears, with no console or terminal window opened

#### Scenario: Starting a transcription
- **WHEN** the application spawns its sidecar for a live session or a file transcription
- **THEN** no console window appears or flashes for the sidecar process or for any process it spawns

#### Scenario: Development builds keep their console
- **WHEN** a developer runs a debug build of the application
- **THEN** console output remains available, so the release-build console suppression does not hinder development

### Requirement: Live session transcript is saved to a file
The system SHALL save every live session's transcript to a file, defaulting to an auto-generated, timestamped file in the user's Documents folder (the home folder if the system reports no Documents folder) when the user has not specified one, and SHALL show the full path of that file in the output field. It SHALL let the user choose a different file location and name via a native save dialog before starting a session, and SHALL save a bare filename typed into the output field in the same default folder. The filename actually used SHALL be stamped with the current local time at the moment each session starts — not fixed once when the app opens or once when a path is chosen — so starting another session without editing the output field never overwrites a previous session's transcript.

#### Scenario: Default output filename
- **WHEN** a user starts a live session without changing the output file field
- **THEN** the transcript is saved in the Documents folder using an auto-generated timestamped filename, the output field shows that file's full path, and the file exists after the session ends

#### Scenario: Starting a second session without editing the output field
- **WHEN** a user stops a live session and starts a new one without editing the output file field
- **THEN** the new session's transcript is saved to a freshly-timestamped file distinct from the first, and the first session's transcript file is left intact

#### Scenario: User picks a custom output location
- **WHEN** a user selects "Browse…" and chooses a file location and name before starting a live session
- **THEN** the transcript is saved to that location, with the current timestamp stamped into the filename so reusing the same browsed location across two starts still doesn't collide

#### Scenario: User types a bare filename
- **WHEN** a user types a filename without a folder (for example `standup.txt`) into the output field and starts a session
- **THEN** the transcript is saved in the Documents folder under that name, with the session's timestamp stamped in

#### Scenario: Timestamp uses local time
- **WHEN** a session starts at 15:43:34 local time
- **THEN** the stamped filename contains `_154334`, whatever the system's UTC offset

#### Scenario: A folder name contains a dot
- **WHEN** a user starts a live session with an output path whose folder contains a dot and whose file name has no extension, such as `/home/a.b/transcript`
- **THEN** the transcript is saved in that folder, as `/home/a.b/transcript_<timestamp>`, not in a folder derived from the part before the dot

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
The system SHALL position transcript lines along a continuous time axis so that the interval between them is proportional to the elapsed time between them, making periods with no speech visible as proportional space rather than being collapsed. Lines SHALL be ordered by their time, even when a line arrives after lines with later times. When lines are hidden by a filter or search, intervals SHALL be measured between the lines that remain visible. A duration shown for a gap SHALL never read as 60 seconds or 60 minutes of a larger unit.

#### Scenario: A silent stretch is visible
- **WHEN** a session contains a period of several minutes during which no transcript line was produced, and the user views the transcript
- **THEN** that period occupies proportionally more space along the time axis than a period of a few seconds, so the gap is visible without reading the timestamps

#### Scenario: Both sources share one axis
- **WHEN** a dual-source session has produced lines from both system audio and microphone
- **THEN** lines from both sources are positioned against the same shared time axis, so their relative timing is directly readable

#### Scenario: A line arrives late
- **WHEN** a line arrives whose time is earlier than lines already shown, because its source took longer to transcribe
- **THEN** it is placed among the other lines where its time falls, the spacing around it stays proportional, and the elapsed times shown are measured from the session's earliest line

#### Scenario: Filtered view keeps true gaps
- **WHEN** the user shows only one source, or searches, so that some lines are hidden
- **THEN** the space and any duration label between two visible lines reflect the time between those two lines, not the time from a hidden line

#### Scenario: Gap durations near a unit boundary
- **WHEN** a gap lasts just under a whole minute or a whole hour, such as 59 minutes 59.6 seconds
- **THEN** its label rounds to the next unit (for example "1 h"), and never reads "60 s" or "60 min"

### Requirement: Transcript time scale is adjustable
The system SHALL let the user adjust the scale of the transcript's time axis, from a scale that fits a long session into a single view to a scale at which transcript text is comfortably readable, without altering the proportionality of the intervals themselves.

#### Scenario: Compressing a long session
- **WHEN** a user viewing a long session reduces the time scale
- **THEN** more of the session becomes visible at once and the relative proportions of speech and silence are preserved

#### Scenario: Expanding for reading
- **WHEN** a user increases the time scale
- **THEN** transcript text is presented at a comfortably readable size, still positioned along the same proportional axis

### Requirement: A stalled capture is distinguishable from a silent one
During a live session, the system SHALL visually distinguish "capturing normally, with no speech currently detected" from "no transcript output has arrived when it was expected", so a stalled engine is not mistaken for a quiet room. A period without speech SHALL NOT be shown as a stall while the engine keeps confirming that it is processing audio, whether or not speech was transcribed earlier in the session.

#### Scenario: Quiet room during a healthy session
- **WHEN** a live session is running normally and no speech has been detected for a short period
- **THEN** the interface indicates that capture is active and simply has nothing to record

#### Scenario: Quiet room after speech
- **WHEN** a live session has transcribed speech, and then no one speaks for several minutes while the engine keeps processing audio
- **THEN** the interface indicates that capture is active with nothing to record, not that output is overdue

#### Scenario: Engine stops producing output
- **WHEN** a live session is running and neither transcript output nor any sign of the engine processing audio has arrived for substantially longer than the expected interval between chunks
- **THEN** the interface indicates that expected output has not arrived, in a way visually distinct from the quiet-room state

### Requirement: Theme defaults to and follows the system setting
The system SHALL resolve the effective theme to the operating system's current light/dark preference when no explicit user theme preference has been stored, and SHALL update the effective theme automatically if the system preference changes while the app is running and no explicit override is set.

#### Scenario: First launch with no stored preference
- **WHEN** a user launches the app for the first time, with no theme preference stored
- **THEN** the app renders in whichever of light or dark matches the operating system's current setting

#### Scenario: System theme changes while the app is open
- **WHEN** a user changes their operating system's theme while the app is running and no explicit in-app theme override is set
- **THEN** the app's rendered theme updates to match the new system setting without requiring a restart

### Requirement: User can override the theme, or return to following the system
The system SHALL let the user explicitly choose Light, Dark, or System from a theme control, and SHALL persist that choice so it survives an app restart until the user changes it again.

#### Scenario: User picks an explicit theme
- **WHEN** a user selects Light or Dark from the theme control
- **THEN** the app immediately renders in that theme regardless of the operating system's setting, and still renders in that theme after the app is restarted

#### Scenario: User returns the control to System
- **WHEN** a user who had previously chosen an explicit theme selects System
- **THEN** the app resumes following the operating system's theme, including any future system theme changes

### Requirement: Resolved theme applies to native window chrome, on a best-effort basis
The system SHALL request the resolved theme (whether system-followed or explicitly overridden) for the application's native window decorations via the platform's window-theming API, not only for the in-page content. Whether the operating system's window chrome actually renders that request is outside the application's control on every platform, and SHALL NOT be required where the platform provides no per-window override.

#### Scenario: Native title bar matches the resolved theme (Windows/macOS)
- **WHEN** the resolved theme is dark, on a platform whose window-theming API supports a genuine per-window override
- **THEN** the operating system-drawn window title bar renders in its dark variant alongside the in-page dark palette, and correspondingly renders in its light variant when the resolved theme is light

#### Scenario: Best-effort request on Linux/GTK
- **WHEN** the resolved theme changes on a Linux desktop environment
- **THEN** the system still issues the platform's theme-request call (GTK's global "prefer dark theme" hint, the only mechanism `tao`/Tauri expose on Linux), but the window chrome's actual appearance follows the desktop environment's own system-wide theme setting rather than this app's request, and this is not treated as a defect

### Requirement: Language selection is a constrained dropdown
The system SHALL let the user choose the transcription language from a dropdown populated with every language the bundled model supports, defaulting to "Auto-detect," rather than free-text entry. Selecting "Auto-detect" SHALL behave identically to leaving the language unset (no `--language` flag passed), and selecting a specific language SHALL pass its code exactly as faster-whisper expects.

#### Scenario: Default is Auto-detect
- **WHEN** a user opens the app without changing the language field
- **THEN** the field reads "Auto-detect" and no `--language` flag is passed to the sidecar for a live session or file transcription

#### Scenario: User selects a specific language
- **WHEN** a user picks a specific language from the dropdown before starting a live session or transcribing a file
- **THEN** the sidecar is invoked with `--language <code>` for that language

### Requirement: Live session uses the running platform's capture mode
The system SHALL start a live session with the capture mode of the platform it runs on: WASAPI loopback on Windows, the Core Audio process tap on macOS, and the default system-audio-plus-microphone capture on Linux. It SHALL NOT pass another platform's capture option to the sidecar.

#### Scenario: Live session on Linux
- **WHEN** a user on Linux starts a live session from the GUI
- **THEN** the session starts capturing system audio (and the microphone, when included) and transcribes it, with no platform-mismatch error

#### Scenario: Live session on Windows
- **WHEN** a user on Windows starts a live session from the GUI
- **THEN** the sidecar is started in WASAPI loopback mode, as before

### Requirement: File transcripts are saved next to the recording
The system SHALL save the transcript of a dropped or chosen file in the same folder as that file, named `<recording name>_transcript_<timestamp>.<format>`, independent of the folder the application was started from.

#### Scenario: Transcribing a recording from another folder
- **WHEN** a user transcribes `~/Downloads/talk.mp4` as txt
- **THEN** the transcript is saved as `~/Downloads/talk_transcript_<timestamp>.txt`, and no transcript is written to the application's working directory

### Requirement: Distributed application carries the project icon
The desktop application SHALL show the project icon (the Transcriber mark on its light-blue background) wherever its platform displays an application icon: launcher and menu entries, the application window and taskbar, the executable and installer on Windows, and the application bundle and disk image on macOS. Every icon size SHALL be rendered down from a source at least as large as that size, never upscaled from a smaller image. On Linux, the window SHALL identify itself to the desktop in a way that matches its installed launcher entry, so the desktop can find the icon for a running window under both Wayland and X11.

#### Scenario: Installed on Linux
- **WHEN** a user installs the `.deb` or `.rpm` and opens the desktop's application launcher
- **THEN** the Transcriber entry shows the project icon, with sizes of at least 256 pixels available to the desktop

#### Scenario: Running window on Linux
- **WHEN** a user opens the installed `.deb` or `.rpm` application on a Wayland session, or the AppImage
- **THEN** the desktop matches the window to the Transcriber launcher entry, and the window's title bar (where the frame shows an icon) and its taskbar entry show the project icon rather than a generic one

#### Scenario: Windows executable and installer
- **WHEN** a Windows user views the application executable or the installer in Explorer
- **THEN** both show the project icon rather than a generic or placeholder icon

#### Scenario: macOS application bundle
- **WHEN** a macOS user views the application bundle in Finder or the Dock
- **THEN** it shows the project icon

#### Scenario: No upscaled sizes
- **WHEN** the application's icon files are generated
- **THEN** each size is derived from a source of at least 1024×1024 pixels

### Requirement: The Linux window uses the desktop's own frame
On Linux, the application window SHALL be framed the way the user's desktop frames its other windows, and SHALL NOT impose a title bar of its own. Where the window system can draw the frame (as KDE's KWin can), the application SHALL let it, so the frame follows the user's decoration theme, button layout and title bar size. Where it cannot, the window SHALL use the toolkit's standard title bar, which follows the desktop's own button layout setting. The window SHALL stay a native client of the session's display server rather than being moved to a compatibility layer to achieve this.

#### Scenario: KDE Plasma on Wayland
- **WHEN** the installed `.deb` or `.rpm` application is opened on a KDE Plasma Wayland session
- **THEN** its frame is drawn by the window manager, matching the other windows' decoration theme, button positions and title bar height, and it is still a native Wayland window

#### Scenario: A desktop that does not draw frames
- **WHEN** the application is opened on a Wayland session whose window manager does not draw window frames, such as GNOME
- **THEN** the window has the toolkit's standard title bar with close, minimize and maximize controls, arranged by the desktop's button layout setting, and can still be moved, resized, maximized and closed

#### Scenario: The window opens without delay
- **WHEN** the application is started on Linux
- **THEN** the window appears framed from its first frame, with no visible change of frame after it is shown, and opens as quickly as before

### Requirement: Linux names follow one case rule
On Linux, the package name, the package file names of the `.deb` and `.rpm`, and the command that starts the desktop application SHALL be lowercase. Every name the desktop displays or uses to match a running window to its launcher entry SHALL be `Transcriber`: the launcher entry's file name, the window's Wayland application ID, its X11 window class, and the class the launcher entry declares for matching. The AppImage file name SHALL keep the capitalised `Transcriber` form.

#### Scenario: Installing and starting from a terminal
- **WHEN** a user installs the package with `apt` or `dnf` and starts the app from a terminal
- **THEN** the package is named `transcriber` and the command is `transcriber-gui`

#### Scenario: The desktop matches the window to its launcher entry
- **WHEN** the application is running, from the `.deb`, the `.rpm` or the AppImage, on Wayland or X11
- **THEN** the window identifies itself as `Transcriber`, the installed launcher entry is `Transcriber.desktop` and declares the same class, so the desktop matches the window to it by either route

### Requirement: Windows installer installs per user without administrator rights
The Windows installer SHALL install the application into the current user's own profile without requesting administrator privileges and without writing machine-wide registry keys. It SHALL create a Start Menu entry and an uninstaller, and uninstalling SHALL remove the installed application files and the Start Menu entry.

#### Scenario: Install from a standard user account
- **WHEN** a user without administrator rights runs the installer
- **THEN** installation completes with no administrator (UAC) prompt, and the application is installed under that user's profile

#### Scenario: Launch after install
- **WHEN** the user starts the application from the Start Menu entry the installer created
- **THEN** the application opens and can complete a file transcription with no network access

#### Scenario: Uninstall
- **WHEN** the user uninstalls the application through Windows' installed-apps settings or the uninstaller
- **THEN** the installed application files and the Start Menu entry are removed, with no administrator prompt

### Requirement: Capture is shown as active only once the engine is listening
When a live session starts, the system SHALL show a starting state, and SHALL NOT present system audio or the microphone as being captured, nor the session as listening, until the transcription engine confirms it is listening. Engine output that arrives before that confirmation, such as model-loading messages, SHALL NOT advance the session out of the starting state. A transcript line from the engine SHALL count as confirmation, since the engine can only produce one while capturing.

#### Scenario: Engine is still loading
- **WHEN** a user starts a live session and the engine has not yet confirmed it is listening
- **THEN** the session shows a starting state, and neither system audio nor the microphone is shown as being captured

#### Scenario: Engine output before listening
- **WHEN** the engine reports progress, such as loading its model, before confirming it is listening
- **THEN** the session stays in the starting state, and no capture source is shown as active

#### Scenario: Engine confirms it is listening
- **WHEN** the engine confirms it is listening
- **THEN** the session shows that it is listening, and each included capture source is shown as being captured

#### Scenario: Engine exits before listening
- **WHEN** the engine exits during start-up, before confirming it is listening
- **THEN** no capture source was ever shown as active, and the session returns to idle with the engine's error

### Requirement: The application window runs only the application's own code
The application window SHALL enforce a content security policy that allows scripts, styles and other resources only from the application's own bundled files, and network connections only to the application's own inter-process channel. Script that is not part of the bundled application, whether injected into the page or loaded from a remote location, SHALL be refused by the window rather than executed.

#### Scenario: The application works under the policy
- **WHEN** a user opens the application and uses it normally: switching theme, starting and stopping a live session, and transcribing a dropped file
- **THEN** everything works as before, and the window reports no content-security-policy violations

#### Scenario: Injected script is refused
- **WHEN** markup containing an inline script or a reference to a remote script ends up in the application window
- **THEN** the window does not execute that script

#### Scenario: The policy cannot be silently dropped
- **WHEN** the application's configuration no longer sets a content security policy restricting scripts to the application's own code
- **THEN** the automated tests fail

### Requirement: Chart search counts the matching lines the user can see
When the user searches the chart, the system SHALL show a count of the transcript lines that contain the search text, are shown by the current source filter, and belong to the chart currently displayed (live or file). Lines hidden by the source filter, and lines in the chart that is not displayed, SHALL NOT be counted. The count SHALL update when the search text, the source filter, or the displayed chart changes, and when new transcript lines arrive. With no search text, no count SHALL be shown.

#### Scenario: Source filter hides some matches
- **WHEN** the live chart has one system-audio line and one microphone line containing "budget", the source filter shows system audio only, and the user searches for "budget"
- **THEN** one line is shown highlighted and the count reads "1 line"

#### Scenario: Matches in the chart that is not displayed
- **WHEN** the file chart contains a line with "budget", the live chart is displayed with no line containing "budget", and the user searches for "budget"
- **THEN** the count reads "0 lines"

#### Scenario: Switching charts updates the count
- **WHEN** a search is active and the user switches from the live chart to the file chart
- **THEN** the count reflects the matching visible lines of the file chart

#### Scenario: Search cleared
- **WHEN** the user clears the search text
- **THEN** no count is shown

### Requirement: Users can check for a newer release on demand
The application SHALL offer a control that checks whether a newer release of the application has been published, and SHALL contact the network for that check only when the user activates the control. It SHALL NOT check automatically, in the background, or at startup. Apart from this user-initiated check, the application SHALL make no network request. The result SHALL tell the user one of: that they are up to date, which newer version is available, that no release has been published yet, or that the check could not be completed. When a newer version is available, the application SHALL offer to open the project's own releases page in the user's browser, and SHALL NOT open any location supplied by the network.

#### Scenario: A newer release exists
- **WHEN** the user checks for updates and the newest published release has a higher version than the running application
- **THEN** the application reports that version as available and offers to open the project's releases page

#### Scenario: Already on the newest release
- **WHEN** the user checks for updates and the newest published release is the same as or older than the running application
- **THEN** the application reports that it is up to date, naming the running version

#### Scenario: No release published yet
- **WHEN** the user checks for updates and the project has no published release
- **THEN** the application reports that no release has been published yet

#### Scenario: The check cannot complete
- **WHEN** the user checks for updates with no network access, or the release host does not answer or answers unexpectedly
- **THEN** the application reports that it could not check for updates, without an error dialog, and every other feature keeps working

#### Scenario: No check without the user
- **WHEN** the application starts and is used for transcription without the user activating the update check
- **THEN** the application makes no network request

### Requirement: User can choose a model folder
The system SHALL show which model transcription will use: the bundled model by default, or a model folder the user has chosen. The system SHALL let the user choose a folder through the operating system's folder picker, and SHALL let the user return to the bundled model. The choice SHALL be remembered across application restarts. The system SHALL NOT offer model sizes it cannot load.

#### Scenario: Default is the bundled model
- **WHEN** a user opens the application without having chosen a model folder
- **THEN** the model field shows that the bundled model is in use

#### Scenario: User chooses a folder
- **WHEN** a user picks a folder in the folder picker
- **THEN** the model field shows that folder as the model in use, and later sessions use it

#### Scenario: Choice survives a restart
- **WHEN** a user who chose a model folder closes and reopens the application
- **THEN** the chosen folder is still shown and used

#### Scenario: User returns to the bundled model
- **WHEN** a user who chose a model folder selects the bundled model again
- **THEN** the model field shows the bundled model, and later sessions use the bundled model directory

#### Scenario: Cancelling the picker changes nothing
- **WHEN** a user opens the folder picker and cancels it
- **THEN** the model in use is unchanged

### Requirement: Live sessions stop after a configurable silence
The system SHALL let the user set how many minutes without detected speech end a live session, defaulting to 10 minutes, with a value that turns the automatic stop off. The setting SHALL be remembered across application restarts and SHALL apply to live sessions started after it changes. A stop at this limit is a clean end of the session, not an error: the engine SHALL exit successfully, the system SHALL NOT present it as a failure, and SHALL tell the user plainly that it stopped after that much silence before returning the UI to idle state.

#### Scenario: Default limit
- **WHEN** a user starts a live session without having changed the setting
- **THEN** the session stops by itself after 10 minutes without detected speech

#### Scenario: User changes the limit
- **WHEN** a user sets the limit to a different number of minutes and starts a live session
- **THEN** the session stops by itself only after that many minutes without detected speech

#### Scenario: Automatic stop turned off
- **WHEN** a user turns the automatic stop off and starts a live session
- **THEN** the session never stops by itself because of silence

#### Scenario: Setting survives a restart
- **WHEN** a user who changed the limit closes and reopens the application
- **THEN** the changed limit is still shown and used

#### Scenario: User is told about a silence stop
- **WHEN** a live session stops because the silence limit was reached
- **THEN** the user is told, as information and not as an error, that the session stopped after that many minutes of silence; the interface returns to idle, and the transcript saved so far is kept

### Requirement: The engine does not leave its unpacked copy behind
The application's engine unpacks itself into the system temporary directory each time it runs. The system SHALL give a stopping live session's engine enough time to exit on its own, so that its unpacked copy is removed, before terminating it forcibly. When the application quits, it SHALL stop any engine that is still running in the same way, so no engine keeps capturing or transcribing after the application has closed. When the application starts, the system SHALL remove, without delaying the window from opening, every unpacked copy in the system temporary directory that belongs to the application's engine and whose engine process is no longer running. The system SHALL NOT remove a copy used by a running engine, nor any temporary folder that does not belong to the application's engine.

#### Scenario: A stop that takes a few seconds
- **WHEN** a user stops a live session whose engine needs several seconds to finish the audio it is transcribing
- **THEN** the engine exits on its own before being terminated forcibly, and its unpacked copy no longer exists afterwards

#### Scenario: Quitting the application during a session
- **WHEN** a user closes the application while a live session or a file transcription is running
- **THEN** that engine stops, no engine process from the application keeps running, and its unpacked copy no longer exists afterwards

#### Scenario: Leftovers from a killed engine are removed at the next start
- **WHEN** the application starts and the system temporary directory holds an unpacked copy of the application's engine whose engine process is no longer running
- **THEN** that copy is removed, and the window opens without waiting for the removal

#### Scenario: A running engine's copy is kept
- **WHEN** the application starts while another running instance's engine is using its unpacked copy
- **THEN** that copy is left in place

#### Scenario: Other applications' folders are untouched
- **WHEN** the application starts and the system temporary directory holds unpacked folders of other applications built the same way, whether or not their processes are running
- **THEN** those folders are left in place

### Requirement: A refused start leaves the screen as it was
When the application refuses to start a live session or a file transcription, the system SHALL tell the user why and SHALL leave everything else as it was before the attempt: the transcript already shown in either chart stays visible, lines from a session that is still running keep appearing in that session's own chart, the running session's status keeps reflecting that session, and what the interface showed about how the previous session ended stays shown.

#### Scenario: File dropped during a live session
- **WHEN** a live session is running and the user drops a file, and the application refuses to transcribe it because the live session is still running
- **THEN** the user is told why, later transcript lines from the live session still appear in the live chart, the live status does not report a stall for lines that did arrive, and the file chart keeps whatever it showed before

#### Scenario: Live start refused
- **WHEN** the live chart shows a previous session's transcript and the user starts a new live session that the application refuses to start
- **THEN** the user is told why, and the previous session's transcript and the explanation of how that session ended remain shown

#### Scenario: Live start refused during a file transcription
- **WHEN** a file transcription is running and a live start is refused because of it
- **THEN** the file transcription's queue and output keep being shown as that file transcription's, not as a live session's
