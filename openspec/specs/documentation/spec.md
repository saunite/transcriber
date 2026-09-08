# documentation

## Purpose

Ensure the project's README stays in sync with the tool's user-facing capabilities so contributors and users can discover supported commands, platform setup, and launchers.

## Requirements

### Requirement: Project documentation mirrors supported behavior

The project's README SHALL accurately document the supported commands, flags, platform-specific setup, requirements files, and launchers (batch and shell) offered by the tool, and SHALL be updated whenever a capability's user-facing behavior changes. The README SHALL NOT list prerequisites the tool no longer requires.

#### Scenario: New launcher added

- **WHEN** a new launcher script is added to the repo root
- **THEN** the README SHALL include it in a "Launchers" section with its usage

#### Scenario: Platform-specific setup documented

- **WHEN** a capability has platform-specific setup
- **THEN** the README SHALL document the correct setup per platform, referencing the correct requirements file

#### Scenario: A prerequisite is no longer required

- **WHEN** the tool stops requiring an external prerequisite
- **THEN** the README SHALL remove that prerequisite's install instructions rather than leaving them as stale setup steps
