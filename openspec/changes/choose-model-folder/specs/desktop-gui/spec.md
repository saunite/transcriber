## MODIFIED Requirements

### Requirement: Sidecar always loads the bundled model explicitly
The system SHALL pass the sidecar an explicit model directory for every spawned session (live or file), so the sidecar never depends on an ambient network/cache-based model lookup, whether running from an installed or portable location. That directory SHALL be the bundled model directory, resolved relative to the running application's own location, unless the user has chosen a model folder, in which case it SHALL be the chosen folder. Before spawning a session with a chosen folder, the system SHALL verify the folder exists and contains a model file; if it does not, the system SHALL refuse to start the session, tell the user the folder does not hold a usable model, and start no engine.

#### Scenario: Live session uses the bundled model
- **WHEN** a user who has not chosen a model folder starts a live session
- **THEN** the sidecar is spawned with an explicit path to the bundled model directory

#### Scenario: File transcription uses the bundled model
- **WHEN** a user who has not chosen a model folder transcribes a dropped file
- **THEN** the sidecar is spawned with an explicit path to the bundled model directory

#### Scenario: Session uses the chosen model folder
- **WHEN** a user who has chosen a model folder starts a live session or transcribes a file
- **THEN** the sidecar is spawned with an explicit path to that folder, and not to the bundled model directory

#### Scenario: Chosen folder no longer holds a model
- **WHEN** a user starts a session with a chosen folder that has been moved, deleted, or holds no model file
- **THEN** the session is refused with a message saying the folder does not hold a usable model, and no sidecar is spawned

## ADDED Requirements

### Requirement: User can choose a model folder
The system SHALL show which model transcription will use: the bundled model by default, or a model folder the user has chosen. The system SHALL let the user choose a folder through the operating system's folder picker, and SHALL let the user return to the bundled model. The choice SHALL be remembered across application restarts. The system SHALL NOT offer model sizes it cannot load.

#### Scenario: Default is the bundled model
- **WHEN** a user opens the application without having chosen a model folder
- **THEN** the model field shows that the bundled model is in use

#### Scenario: User chooses a folder
- **WHEN** a user picks a folder in the folder picker
- **THEN** the model field shows that folder as the model in use, and later sessions use it

#### Scenario: Choice survives a restart
- **WHEN** a user who chose a model folder closes and reopens the application
- **THEN** the chosen folder is still shown and used

#### Scenario: User returns to the bundled model
- **WHEN** a user who chose a model folder selects the bundled model again
- **THEN** the model field shows the bundled model, and later sessions use the bundled model directory

#### Scenario: Cancelling the picker changes nothing
- **WHEN** a user opens the folder picker and cancels it
- **THEN** the model in use is unchanged
