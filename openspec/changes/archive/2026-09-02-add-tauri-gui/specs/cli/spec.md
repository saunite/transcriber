## ADDED Requirements

### Requirement: Provide machine-readable device listing
The system SHALL provide `--list-devices-json` to enumerate audio devices as a JSON array (index, name, max input channels, default sample rate per device) to stdout, exiting after printing without transcribing. This is additive: `--list-devices` SHALL continue to print the existing human-readable text format unchanged.

#### Scenario: JSON device list requested
- **WHEN** a user runs with `--list-devices-json`
- **THEN** the system prints a JSON array of device objects to stdout and exits without transcribing

#### Scenario: Existing text device list unaffected
- **WHEN** a user runs with `--list-devices`
- **THEN** the system prints the existing human-readable device listing exactly as before
