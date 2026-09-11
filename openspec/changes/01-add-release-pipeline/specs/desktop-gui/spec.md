## ADDED Requirements

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

## MODIFIED Requirements

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

## REMOVED Requirements

### Requirement: Single no-install artifact per platform
**Reason**: Native installers (NSIS, `.deb`, `.rpm`, `.dmg`) are now offered next to the portable artifacts. The "exactly one artifact" and "SHALL NOT be distributed as an installer package" clauses no longer hold.
**Migration**: Replaced by "Portable artifact per platform, with native installers alongside", which keeps every portable-artifact guarantee (no install step, no admin rights, removal is deletion) for the portable form.
