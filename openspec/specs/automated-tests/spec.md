# Automated Tests

## Purpose

Defines what the project's automated tests guarantee: one command runs every suite, the GUI's behaviour is checked without the desktop app, and the transcription engine is checked on a local speech recording and on undecodable input.

## Requirements

### Requirement: One command runs every automated test
The project SHALL provide a single command that runs the Rust unit tests, every Python test script, the GUI behaviour tests and the engine tests, reports the result of each, and exits with a non-zero status when any of them fails. A failing suite SHALL NOT prevent the remaining suites from running.

#### Scenario: Every suite passes
- **WHEN** a developer runs the test command and all suites pass
- **THEN** each suite is reported as passed and the command exits with status 0

#### Scenario: One suite fails
- **WHEN** one suite fails
- **THEN** the remaining suites still run, the failing suite is named in the summary, and the command exits with a non-zero status

### Requirement: GUI behaviour is tested without the desktop app
The GUI tests SHALL load the application's real frontend files in a headless browser, with a fake app bridge standing in for the desktop application. They SHALL need no built application, no audio hardware and no transcription engine. They SHALL verify both the commands the page sends to the application and the state the page shows in response to the application's events. Every command the page sends SHALL correspond to a command the application actually provides, so the fake bridge cannot silently accept a command the real application lacks.

#### Scenario: The page loads cleanly
- **WHEN** the frontend is loaded against the fake bridge
- **THEN** no script error occurs and the page requests the platform and the audio device list

#### Scenario: A live session starts and stops
- **WHEN** a test starts a live session with the default settings
- **THEN** the page requests a live session with the system-default microphone and the capture indicators show capturing
- **WHEN** the test then stops the session
- **THEN** the page requests the stop and the capture indicators return to idle

#### Scenario: Files are transcribed one at a time
- **WHEN** several supported files are dropped at once
- **THEN** only one file transcription is requested, the rest are shown as waiting, and the next is requested only after the previous one reports completion
- **WHEN** a file's transcription reports failure
- **THEN** that file is shown as failed and the next waiting file is requested

#### Scenario: An unsupported file never reaches the engine
- **WHEN** a file with an unsupported extension is dropped
- **THEN** no file transcription is requested and the user is shown an error

#### Scenario: The application refuses a file transcription
- **WHEN** the application rejects a file transcription request
- **THEN** the page shows the reason it was rejected

#### Scenario: A command the application does not provide
- **WHEN** the page's script requests a command that the application does not register
- **THEN** the GUI tests fail and name that command

### Requirement: The engine transcribes a recorded speech sample
The engine tests SHALL transcribe a recording of human speech in English with the bundled model, offline. They SHALL fail unless the engine:
- exits successfully without a traceback;
- writes a transcript whose lines carry `[start -> end] text` timestamps;
- reports the recording's language;
- recognises most of the key words of the script the recording was read from.

The engine under test SHALL be selectable: the source engine by default, or a given frozen engine binary. The recording and its script SHALL be supplied from outside the repository and SHALL NOT be committed, so a recording the project may not redistribute can still be used locally. When no recording is supplied, the speech check SHALL be reported as skipped, with how to supply one, rather than silently passing or failing.

#### Scenario: The speech sample transcribes
- **WHEN** the engine tests run against the source engine
- **THEN** the engine exits successfully without a traceback, writes a timestamped transcript, reports the sample's language, and the transcript contains most of the script's key words

#### Scenario: A frozen engine binary is tested
- **WHEN** the engine tests are given the path to a frozen engine binary
- **THEN** the same checks run against that binary instead of the source engine

#### Scenario: No recording is supplied
- **WHEN** the engine tests run without a recording
- **THEN** the speech check is reported as skipped with how to supply a recording, and the other engine checks still run

#### Scenario: The model is not available
- **WHEN** the engine tests run before the bundled model has been staged
- **THEN** they fail with a message naming how to stage the model, rather than attempting a download

### Requirement: The engine fails cleanly on undecodable input
The engine tests SHALL verify that a file containing no decodable audio makes the engine exit with a non-zero status and a human-readable message, without printing a traceback and without leaving a transcript file behind.

#### Scenario: A corrupt file is transcribed
- **WHEN** the engine is given a file whose contents are not decodable media
- **THEN** it exits with a non-zero status, prints a message saying the media could not be decoded, prints no traceback, and creates no transcript file

### Requirement: GUI tests run under the application's content security policy
The GUI tests SHALL load the application's frontend under the same content security policy the application window enforces, derived from the application's configuration and its bundled pages in the way the application framework derives it. Every GUI behaviour scenario SHALL fail if the page reports any content-security-policy violation. The tests SHALL also prove that the policy refuses script that isn't part of the application, by checking that injected script had no effect.

#### Scenario: Normal use violates nothing
- **WHEN** the GUI behaviour scenarios run under the application's policy
- **THEN** they pass, and the page reports no content-security-policy violation

#### Scenario: A frontend change breaks under the policy
- **WHEN** the frontend gains code the policy blocks, such as an inline event handler or an unhashed inline script
- **THEN** the GUI tests fail and report the violation

#### Scenario: Injected script is refused
- **WHEN** a test injects an inline event handler and string-evaluated code into the running page
- **THEN** neither changes the page's state, and each is reported as a violation

#### Scenario: The policy is not actually applied
- **WHEN** the page is served without the application's policy
- **THEN** the injected-script scenario fails, because the injected script takes effect
