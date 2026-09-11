## ADDED Requirements

### Requirement: macOS release artifacts
The macOS leg SHALL produce, for Apple Silicon (arm64), a disk image, a zipped application bundle, and a standalone CLI archive, and SHALL attach all three to the release. Until a maintainer verifies them on real macOS hardware, the project's download documentation SHALL state that the macOS artifacts are built automatically but untested on real hardware, and SHALL invite users to report results.

#### Scenario: macOS artifacts in a release
- **WHEN** a release's macOS leg completes
- **THEN** the release contains the arm64 disk image, the zipped application bundle, and the macOS CLI archive, each named with the release version

#### Scenario: Untested status is visible
- **WHEN** a user reads the macOS download instructions
- **THEN** they are told the macOS artifacts are built automatically but have not been tested on real hardware, and how to report whether they work

### Requirement: macOS standalone CLI carries its audio-tap helper
The macOS standalone CLI executable SHALL contain the native audio-tap helper that system-audio capture depends on, so `--coreaudio-tap` needs no separately built helper. The macOS build SHALL fail rather than produce a CLI executable without the helper.

#### Scenario: Helper is inside the executable
- **WHEN** the macOS standalone CLI executable is built
- **THEN** the audio-tap helper is included inside it, at the location the capture code resolves at runtime

#### Scenario: Helper was not built
- **WHEN** the macOS sidecar freeze runs before the audio-tap helper has been built
- **THEN** the freeze fails with a message saying the helper must be built first
