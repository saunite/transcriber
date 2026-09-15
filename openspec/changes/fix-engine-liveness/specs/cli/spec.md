## ADDED Requirements

### Requirement: Live capture reports a lost audio source
When the system audio source of a live capture stops delivering audio on its own, rather than because the user interrupted the session or the silence timeout was reached, the system SHALL print a message saying capture ended unexpectedly, SHALL keep the transcript saved so far, and SHALL exit with a non-zero code.

#### Scenario: The audio source goes away mid-session
- **WHEN** during live capture the system audio source ends, for example because the audio server restarted or the output device disconnected
- **THEN** the system prints that capture ended unexpectedly, closes the transcript file with everything transcribed so far, and exits with a non-zero code

#### Scenario: User interrupts the session
- **WHEN** the user interrupts a live capture session
- **THEN** the system exits with a success code, as before

#### Scenario: Silence timeout ends the session
- **WHEN** a live capture session reaches its silence timeout
- **THEN** the system prints that it stopped because of silence and exits with a success code, as before
