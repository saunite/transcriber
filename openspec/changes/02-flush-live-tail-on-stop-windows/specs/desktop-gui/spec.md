## MODIFIED Requirements

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

#### Scenario: Stopping on Windows is graceful too
- **WHEN** a user on Windows stops an active live session
- **THEN** the engine is asked to stop through a channel it can act on, finishes transcribing what it has captured and closes its transcript, and is terminated forcibly only if it has not exited within the same grace period used on other platforms

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
