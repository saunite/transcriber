## ADDED Requirements

### Requirement: Capture is shown as active only once the engine is listening
When a live session starts, the system SHALL show a starting state, and SHALL NOT present system audio or the microphone as being captured, nor the session as listening, until the transcription engine confirms it is listening. Engine output that arrives before that confirmation, such as model-loading messages, SHALL NOT advance the session out of the starting state. A transcript line from the engine SHALL count as confirmation, since the engine can only produce one while capturing.

#### Scenario: Engine is still loading
- **WHEN** a user starts a live session and the engine has not yet confirmed it is listening
- **THEN** the session shows a starting state, and neither system audio nor the microphone is shown as being captured

#### Scenario: Engine output before listening
- **WHEN** the engine reports progress, such as loading its model, before confirming it is listening
- **THEN** the session stays in the starting state, and no capture source is shown as active

#### Scenario: Engine confirms it is listening
- **WHEN** the engine confirms it is listening
- **THEN** the session shows that it is listening, and each included capture source is shown as being captured

#### Scenario: Engine exits before listening
- **WHEN** the engine exits during start-up, before confirming it is listening
- **THEN** no capture source was ever shown as active, and the session returns to idle with the engine's error
