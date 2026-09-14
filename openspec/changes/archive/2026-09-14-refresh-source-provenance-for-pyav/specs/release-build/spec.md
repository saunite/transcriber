## ADDED Requirements

### Requirement: The bundled PyAV version matches the source-provenance record
Before any platform build starts, on every run of the release workflow, the system SHALL verify that each platform's dependency list pins PyAV to one exact version, that all platforms pin the same version, and that the source-provenance file records that same version. If any of these does not hold, the run SHALL fail before any platform build starts, naming the files and versions involved.

#### Scenario: Pins and provenance agree
- **WHEN** every platform's dependency list pins PyAV to the same exact version and the source-provenance file records that version
- **THEN** the check passes and the platform builds proceed

#### Scenario: PyAV is bumped without refreshing the provenance
- **WHEN** a dependency list pins a PyAV version different from the one the source-provenance file records
- **THEN** the run fails before any platform build starts, naming both versions and the file that differs

#### Scenario: PyAV is not pinned exactly
- **WHEN** a platform's dependency list does not pin PyAV to an exact version, so the build would take whatever version is newest
- **THEN** the run fails before any platform build starts, naming that dependency list

#### Scenario: Platforms disagree
- **WHEN** two platforms' dependency lists pin different PyAV versions
- **THEN** the run fails before any platform build starts, naming each file and its version
