## MODIFIED Requirements

### Requirement: Fully offline first run
The application SHALL be able to complete a live capture or file transcription with no network access, using the model bundled with the application, and SHALL require no separately installed media tool for either flow.

#### Scenario: Offline transcription immediately after install
- **WHEN** a user installs the application on a machine with no network access and starts a transcription
- **THEN** the transcription completes successfully using the bundled model, with no download attempted

#### Scenario: Dropped video file on a machine without ffmpeg
- **WHEN** a user drops a video file onto the application on a machine with no ffmpeg installed
- **THEN** the file is transcribed normally, using the sidecar's bundled decoder rather than an external process
