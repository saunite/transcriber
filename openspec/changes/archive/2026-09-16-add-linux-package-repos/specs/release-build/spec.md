## ADDED Requirements

### Requirement: Publishing a release publishes its package repositories
When a release is published, the system SHALL generate the repository metadata describing that release's Linux packages, sign it, and make it available where the registered repositories look for it. Building a draft release, or running the build manually, SHALL NOT change what any repository offers.

#### Scenario: A release is published
- **WHEN** a maintainer publishes a release
- **THEN** the repository metadata for that release's packages is generated, signed and published, so registered package managers offer that version

#### Scenario: A draft is built
- **WHEN** a tagged build produces a draft release, or a maintainer triggers the build manually
- **THEN** no repository metadata is published, and registered package managers keep offering the previously published version

#### Scenario: Signing material is unavailable
- **WHEN** the signing key is not available to the publishing run
- **THEN** the run fails with a message naming what is missing, and no unsigned metadata is published
