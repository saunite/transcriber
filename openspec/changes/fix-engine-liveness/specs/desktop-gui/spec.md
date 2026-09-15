## MODIFIED Requirements

### Requirement: On-demand sidecar lifecycle with crash recovery
The system SHALL spawn the bundled Python sidecar only when the user starts a live session or submits a file, SHALL stop it cleanly on user request or app quit, and SHALL detect unexpected sidecar exit and surface an error instead of leaving the UI in a stuck state. An exit of a live session's engine that the user did not request SHALL be treated as unexpected whatever its exit code, and the user SHALL be told the session ended. Stopping SHALL terminate every process the sidecar launch created, including any process the frozen binary re-executes into, since that descendant is what holds the audio device. The system SHALL NOT begin a file transcription while a live session's engine is still running, and SHALL NOT begin a live session while a live session's engine or a file transcription's engine is still running. The exit of an earlier session's engine SHALL NOT affect a session started after it.

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

## ADDED Requirements

### Requirement: Live sessions stop after a configurable silence
The system SHALL let the user set how many minutes without detected speech end a live session, defaulting to 10 minutes, with a value that turns the automatic stop off. The setting SHALL be remembered across application restarts and SHALL apply to live sessions started after it changes. When a session ends because of this limit, the system SHALL tell the user it stopped after that much silence and SHALL return the UI to idle state.

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
- **THEN** the user is told the session stopped after that many minutes of silence, the interface returns to idle, and the transcript saved so far is kept
