## ADDED Requirements

### Requirement: Select macOS native loopback capture mode
The system SHALL provide `--coreaudio-tap` to select native macOS system-audio loopback capture, analogous to `--wasapi` on Windows, and SHALL reject platform-mismatched flags with a clear error instead of attempting to run.

#### Scenario: macOS native tap selected
- **WHEN** a user runs `--live --coreaudio-tap` on macOS
- **THEN** the system captures system audio via the native Core Audio Process Tap

#### Scenario: Wrong-platform flag usage
- **WHEN** a user runs `--coreaudio-tap` on Windows or Linux, or `--wasapi` on macOS
- **THEN** the system prints a clear error naming the correct flag for the current platform and exits without attempting capture
