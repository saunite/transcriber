## MODIFIED Requirements

### Requirement: On-demand sidecar lifecycle with crash recovery
The system SHALL spawn the bundled Python sidecar only when the user starts a live session or submits a file, SHALL stop it cleanly on user request or app quit, and SHALL detect unexpected sidecar exit and surface an error instead of leaving the UI in a stuck state. Stopping SHALL terminate every process the sidecar launch created, including any process the frozen binary re-executes into, since that descendant is what holds the audio device. The system SHALL NOT begin a file transcription while a live session's engine is still running.

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

#### Scenario: Sidecar crashes mid-session
- **WHEN** the sidecar process exits unexpectedly while a session is active
- **THEN** the system shows an error with the sidecar's last output and returns the UI to idle state, without requiring an app restart

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
