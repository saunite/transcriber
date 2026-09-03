## ADDED Requirements

### Requirement: Split platform-specific work into separate changes
When a piece of work requires genuinely different implementation per platform for any part of it to be considered complete, the system SHALL split that work into separate OpenSpec changes: one change for the platform-agnostic part, plus one additional change per platform requiring distinct implementation. The system SHALL surface this requirement in the artifact instructions of every change via the project config. A change that is merely verified on multiple platforms, with no implementation divergence, is not required to split.

#### Scenario: New requirement needs different implementation per platform
- **WHEN** a proposed requirement needs different implementation on Windows than on Linux to be considered complete
- **THEN** the system creates separate changes - one for the platform-agnostic part and one per platform needing distinct implementation - rather than one change covering all platforms

#### Scenario: Same implementation, verified on multiple platforms
- **WHEN** a proposed change has one implementation that is simply verified on more than one platform, with no per-platform code differences
- **THEN** the system keeps it as a single change

### Requirement: Number related changes in application order
When multiple related changes are created together, the system SHALL prefix each change's directory name with a two-digit number reflecting the order the changes are intended to be applied (e.g. `01-foo`, `02-foo-linux`, `03-foo-windows`).

#### Scenario: Platform split produces a batch of related changes
- **WHEN** the system splits a piece of work into a general change plus one or more platform-specific changes per the platform-split requirement
- **THEN** each resulting change directory name carries a two-digit prefix indicating its application order relative to the others in the batch

#### Scenario: Standalone change created alone
- **WHEN** a single change is created that is not part of a related batch
- **THEN** the system does not require a numeric prefix on its directory name
