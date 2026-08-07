## ADDED Requirements

### Requirement: Project documentation mirrors supported behavior
The project's README SHALL accurately document the supported commands, flags, platform-specific setup, requirements files, and launchers (batch and shell) offered by the tool, and SHALL be updated whenever a capability's user-facing behavior changes.

#### Scenario: New launcher added
- **WHEN** a new launcher script (e.g., a `.bat` or `.sh`) is added to the repo root
- **THEN** the README SHALL include it in a "Launchers" section with its usage

#### Scenario: Platform-specific setup documented
- **WHEN** a capability has platform-specific setup (e.g., a Windows-only dependency or a Linux audio monitor)
- **THEN** the README SHALL document the correct setup per platform, referencing the correct requirements file
