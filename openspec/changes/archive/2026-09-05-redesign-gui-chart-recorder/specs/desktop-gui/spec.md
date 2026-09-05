## ADDED Requirements

### Requirement: Transcript time is rendered at true scale
The system SHALL position transcript lines along a continuous time axis so that the interval between them is proportional to the elapsed time between them, making periods with no speech visible as proportional space rather than being collapsed.

#### Scenario: A silent stretch is visible
- **WHEN** a session contains a period of several minutes during which no transcript line was produced, and the user views the transcript
- **THEN** that period occupies proportionally more space along the time axis than a period of a few seconds, so the gap is visible without reading the timestamps

#### Scenario: Both sources share one axis
- **WHEN** a dual-source session has produced lines from both system audio and microphone
- **THEN** lines from both sources are positioned against the same shared time axis, so their relative timing is directly readable

### Requirement: Transcript time scale is adjustable
The system SHALL let the user adjust the scale of the transcript's time axis, from a scale that fits a long session into a single view to a scale at which transcript text is comfortably readable, without altering the proportionality of the intervals themselves.

#### Scenario: Compressing a long session
- **WHEN** a user viewing a long session reduces the time scale
- **THEN** more of the session becomes visible at once and the relative proportions of speech and silence are preserved

#### Scenario: Expanding for reading
- **WHEN** a user increases the time scale
- **THEN** transcript text is presented at a comfortably readable size, still positioned along the same proportional axis

### Requirement: A stalled capture is distinguishable from a silent one
During a live session, the system SHALL visually distinguish "capturing normally, with no speech currently detected" from "no transcript output has arrived when it was expected", so a stalled engine is not mistaken for a quiet room.

#### Scenario: Quiet room during a healthy session
- **WHEN** a live session is running normally and no speech has been detected for a short period
- **THEN** the interface indicates that capture is active and simply has nothing to record

#### Scenario: Engine stops producing output
- **WHEN** a live session is running and no transcript output has arrived for substantially longer than the expected interval between chunks
- **THEN** the interface indicates that expected output has not arrived, in a way visually distinct from the quiet-room state
