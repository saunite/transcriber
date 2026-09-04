## ADDED Requirements

### Requirement: WASAPI loopback device can be overridden, with a discouraging default message
The system SHALL default live capture to an auto-detected WASAPI loopback device, SHALL let the user optionally specify a different device by index, and SHALL display a message stating that the default is auto-detected WASAPI and that overriding is not recommended.

#### Scenario: Default session uses auto-detection
- **WHEN** a user starts a live session without setting a device override
- **THEN** the system uses the auto-detected WASAPI loopback device, exactly as it did before this override existed

#### Scenario: Override message is visible
- **WHEN** a user opens Session Settings
- **THEN** a message near the device override field states that the default is the auto-detected WASAPI device and that overriding is not recommended

#### Scenario: User overrides the device
- **WHEN** a user enters a specific device index in the override field and starts a live session
- **THEN** the system uses that device index instead of auto-detection
