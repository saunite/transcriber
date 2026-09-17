## MODIFIED Requirements

### Requirement: macOS release artifacts
The macOS leg SHALL produce, for Apple Silicon (arm64), a disk image, a zipped application bundle, and a standalone CLI archive, and SHALL attach all three to the release. Until a maintainer verifies them on real macOS hardware, the project's download documentation SHALL state that the macOS artifacts are built automatically but untested on real hardware, and SHALL invite users to report results. Once a release is published, that invitation SHALL link to the latest published release, where the macOS artifacts can be downloaded, using a link that stays valid when a newer release is published.

#### Scenario: macOS artifacts in a release
- **WHEN** a release's macOS leg completes
- **THEN** the release contains the arm64 disk image, the zipped application bundle, and the macOS CLI archive, each named with the release version

#### Scenario: Untested status is visible
- **WHEN** a user reads the macOS download instructions
- **THEN** they are told the macOS artifacts are built automatically but have not been tested on real hardware, and how to report whether they work

#### Scenario: A tester goes to the downloads
- **WHEN** a Mac user who wants to test follows the link in the call for testers
- **THEN** they land on the latest published release, which lists the macOS disk image, zipped application bundle and CLI archive, and the link keeps pointing at the newest release after later releases are published
