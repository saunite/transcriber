## ADDED Requirements

<!-- Extends the desktop-gui capability introduced by the not-yet-archived
     add-tauri-gui change; there is no base spec in openspec/specs/ yet to
     diff against, so this is expressed as ADDED requirements rather than
     MODIFIED. -->

### Requirement: Sidecar always loads the bundled model explicitly
The system SHALL resolve the bundled model directory relative to the running application's own location and pass it to the sidecar explicitly for every spawned session (live or file), so the sidecar never depends on an ambient network/cache-based model lookup, whether running from an installed or portable location.

#### Scenario: Live session uses the bundled model
- **WHEN** a user starts a live session
- **THEN** the sidecar is spawned with an explicit path to the bundled model directory

#### Scenario: File transcription uses the bundled model
- **WHEN** a user transcribes a dropped file
- **THEN** the sidecar is spawned with an explicit path to the bundled model directory

### Requirement: Portable build available alongside the installer
The system SHALL support assembling a self-contained portable build (application executable, sidecar executable, required runtime DLLs, and bundled model resources in one folder) that runs without installation, in addition to the NSIS installer.

#### Scenario: Portable build runs without installing
- **WHEN** a user extracts the portable build folder and runs the application executable directly
- **THEN** the application starts and functions the same as the installed version, without any installation step
