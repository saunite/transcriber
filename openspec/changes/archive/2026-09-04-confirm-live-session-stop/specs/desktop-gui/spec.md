## ADDED Requirements

### Requirement: Live session stop is confirmed genuinely, not cosmetically
When a user stops a live session, the system SHALL report whether the stop actually succeeded, based on the real result of terminating the sidecar process, rather than assuming success.

#### Scenario: Stop succeeds
- **WHEN** a user stops an active live session and the sidecar process is successfully terminated
- **THEN** the system logs a confirmation that the session stopped

#### Scenario: Stop fails
- **WHEN** a user stops an active live session and terminating the sidecar process does not succeed
- **THEN** the system logs that the stop did not succeed, rather than silently reporting nothing
