## ADDED Requirements

### Requirement: Windows release artifacts
The Windows leg SHALL produce a per-user installer, a portable zip, and a standalone CLI zip for 64-bit Windows, and SHALL attach all three to the release.

#### Scenario: Windows artifacts in a release
- **WHEN** a release's Windows leg completes
- **THEN** the release contains the Windows installer, the Windows portable zip, and the Windows CLI zip, each named with the release version
