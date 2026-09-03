## ADDED Requirements

<!-- openspec/specs/desktop-gui/spec.md now exists (synced from
     add-tauri-gui on archive). These are new requirements with no
     counterpart in that base spec, so ADDED is still correct here -- this
     is not a modification of existing base text.

     Also supersedes "Portable build available alongside the installer"
     from the still-active add-portable-build change's own desktop-gui
     delta -- the portable artifact is no longer an alternative to an
     installer, it is the only form. That change should archive before or
     alongside this one; see this change's tasks.md. -->

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

## REMOVED Requirements

### Requirement: Portable build available alongside the installer
**Reason**: Superseded by "Single no-install artifact per platform" above — the portable build is no longer an alternative packaging form offered alongside an installer; it is the only distributed form, and the installer is removed entirely.
**Migration**: See "Single no-install artifact per platform" for the current requirement covering the same functionality (a self-contained, no-install artifact per platform).
