# Release Build

## Purpose

Defines how a release of the application is triggered, gated, built, and published, and which artifacts every release must contain for each supported platform.

## Requirements

### Requirement: A pushed version tag produces a draft release
When a tag of the form `v<version>` is pushed, the system SHALL build every platform's release artifacts and attach them to a draft GitHub release for that tag. The release SHALL NOT be published automatically; publishing is a manual action.

#### Scenario: Release tag pushed
- **WHEN** a maintainer pushes the tag `v0.2.0`
- **THEN** a draft release for `v0.2.0` is created containing every platform leg's artifacts, and it is not publicly visible until a maintainer publishes it

#### Scenario: A platform leg fails
- **WHEN** any platform's build fails during a tagged run
- **THEN** the release remains a draft, the failure is visible in the workflow run, and nothing is published

### Requirement: Release version matches the tag
The system SHALL refuse to build a release when the version in the tag differs from the application version declared in the project. The check SHALL run before any platform build starts.

#### Scenario: Tag and version disagree
- **WHEN** the tag `v0.3.0` is pushed while the project declares version `0.2.0`
- **THEN** the run fails before any platform build starts, with a message naming both versions, and no release is created

#### Scenario: Tag and version agree
- **WHEN** the tag `v0.2.0` is pushed while the project declares version `0.2.0`
- **THEN** the platform builds proceed

### Requirement: Builds can run without releasing
The system SHALL support manually triggering the same platform builds without a tag. A manual run SHALL produce downloadable build outputs and SHALL NOT create or modify any release.

#### Scenario: Manual build
- **WHEN** a maintainer triggers the workflow manually
- **THEN** every platform's artifacts are downloadable from that run, and the repository's release list is unchanged

### Requirement: Source-provenance directions are verified and attached
Before building a release, the system SHALL check that every concrete source location listed in the project's source-provenance file resolves, and SHALL fail the release if any does not. The system SHALL NOT attach the source-provenance file to a release as a downloadable asset. Instead, every release's notes SHALL include a section, placed before any automatically generated notes, that names the bundled GPL-licensed components and links to the source-provenance file as it exists at that release's tag, so the directions shown always match the release they accompany.

#### Scenario: A source location no longer resolves
- **WHEN** a release tag is pushed and one source URL in the provenance file returns an error
- **THEN** the run fails before any platform build starts, naming the URL that failed

#### Scenario: Provenance accompanies the release
- **WHEN** a draft release is created
- **THEN** its notes begin with a section linking to the source-provenance file at that release's tag, and the file is not among the release's attached assets

#### Scenario: Provenance changes in a later release
- **WHEN** a later release is tagged after the source-provenance file was updated
- **THEN** that release's notes link to the updated file at the new tag, while earlier releases keep linking to the file as it was at their own tags

### Requirement: Frozen sidecar is smoke-tested before packaging
Each platform leg SHALL run its frozen sidecar standalone, listing devices and transcribing a short audio file with the bundled model, before producing any package. The leg SHALL fail if either check fails.

#### Scenario: Sidecar works
- **WHEN** the frozen sidecar lists devices (exit 0, valid JSON, an empty list is acceptable) and transcribes a short generated audio file with the bundled model (exit 0, output file written)
- **THEN** the leg continues to packaging

#### Scenario: Sidecar is broken
- **WHEN** either check exits non-zero
- **THEN** the leg fails and no package from it is attached to the release

### Requirement: Linux release artifacts
The Linux leg SHALL produce an AppImage, a `.deb` package, a `.rpm` package, and a standalone CLI archive. The `.deb` SHALL install with its dependencies resolved by the package manager on current Debian stable and Ubuntu LTS. The `.rpm` SHALL install with its dependencies resolved by the package manager on current Fedora, openSUSE Leap, and openSUSE Tumbleweed.

#### Scenario: Debian-family install
- **WHEN** the `.deb` is installed with `apt` on current Debian stable or Ubuntu LTS
- **THEN** its dependencies resolve from the distribution's repositories and the install succeeds

#### Scenario: RPM-family install
- **WHEN** the `.rpm` is installed with `dnf` on current Fedora, or with `zypper` on openSUSE Leap or Tumbleweed
- **THEN** its dependencies resolve from that distribution's repositories and the install succeeds

#### Scenario: Package removal
- **WHEN** the installed package is removed through the package manager
- **THEN** the application's files and menu entry are removed

### Requirement: Standalone CLI archive in every release
Each platform leg SHALL attach a standalone CLI archive carrying the same version as the GUI artifacts. The archive SHALL contain the CLI executable, the bundled `base` model together with its license, that platform's launcher script(s), and the project's license and third-party notice files. The CLI SHALL run from the extracted archive with no Python installation and no network access.

#### Scenario: Offline file transcription from the archive
- **WHEN** a user extracts the CLI archive on a machine with no Python and no network access and runs the CLI with `--file <audio>`
- **THEN** the file is transcribed using the bundled model, with no download attempted

#### Scenario: Executable permission survives extraction
- **WHEN** a Linux or macOS user extracts the CLI archive with the platform's standard archive tool
- **THEN** the CLI executable and launcher scripts are already executable

#### Scenario: Notices ship with the CLI
- **WHEN** a user lists the extracted CLI archive
- **THEN** the license file, the third-party notices, the source-provenance file, and the model's license are present

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

### Requirement: Windows release artifacts
The Windows leg SHALL produce a per-user installer, a portable zip, and a standalone CLI zip for 64-bit Windows, and SHALL attach all three to the release.

#### Scenario: Windows artifacts in a release
- **WHEN** a release's Windows leg completes
- **THEN** the release contains the Windows installer, the Windows portable zip, and the Windows CLI zip, each named with the release version
