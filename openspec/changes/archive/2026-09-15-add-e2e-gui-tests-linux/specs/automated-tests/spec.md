## ADDED Requirements

### Requirement: The built desktop application is tested end to end on Linux
The project SHALL provide end-to-end tests that build the desktop application and drive its real window, with its real bridge between page and application, on Linux. They SHALL verify:
- that the update check gives a real verdict when the release host is reachable, and reports that it could not check when there is no network;
- that the application makes no network connection at startup, from any of its processes;
- that the download page action opens exactly the project's fixed releases address;
- that transcription completes with no network.

The tests SHALL run from the single test command. When the environment cannot run them (not Linux, no graphical display, a missing driver or tracing tool, or no staged engine binary), each affected scenario SHALL be reported as skipped with how to make it runnable, rather than silently passing or failing. A scenario that needs the release host SHALL be reported as skipped when the host cannot be reached, and SHALL NOT pass on a "could not check" result.

#### Scenario: Update check with a network
- **WHEN** the end-to-end tests click the update-check control in the running application while the release host is reachable
- **THEN** the application shows that it is up to date, that a newer version is available, or that no release has been published, and the test fails if it shows that it could not check

#### Scenario: Update check without a network
- **WHEN** the end-to-end tests run the application with no network access and click the update-check control
- **THEN** the application shows that it could not check for updates

#### Scenario: Transcription without a network
- **WHEN** the end-to-end tests transcribe the speech sample with the application's engine binary with no network access
- **THEN** the transcription succeeds as the engine tests require, or the speech check is reported as skipped when no recording is supplied

#### Scenario: Nothing connects at startup
- **WHEN** the application is started, its page has loaded and asked for the audio device list, and no control has been used
- **THEN** no process of the application has attempted a network connection

#### Scenario: A startup request is introduced
- **WHEN** the frontend is changed to check for updates as soon as it loads
- **THEN** the startup scenario fails and reports the connection attempt

#### Scenario: Download page opens the fixed address
- **WHEN** the application's open-download-page action runs
- **THEN** the system's URL opener is asked to open exactly the project's releases address, and nothing else

#### Scenario: Environment cannot run the tests
- **WHEN** the end-to-end tests run without a graphical display, or without the WebDriver bridge installed
- **THEN** each scenario is reported as skipped with the missing piece and how to install or provide it, and the suite does not fail
