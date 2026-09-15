## MODIFIED Requirements

### Requirement: Transcript time is rendered at true scale
The system SHALL position transcript lines along a continuous time axis so that the interval between them is proportional to the elapsed time between them, making periods with no speech visible as proportional space rather than being collapsed. Lines SHALL be ordered by their time, even when a line arrives after lines with later times. When lines are hidden by a filter or search, intervals SHALL be measured between the lines that remain visible. A duration shown for a gap SHALL never read as 60 seconds or 60 minutes of a larger unit.

#### Scenario: A silent stretch is visible
- **WHEN** a session contains a period of several minutes during which no transcript line was produced, and the user views the transcript
- **THEN** that period occupies proportionally more space along the time axis than a period of a few seconds, so the gap is visible without reading the timestamps

#### Scenario: Both sources share one axis
- **WHEN** a dual-source session has produced lines from both system audio and microphone
- **THEN** lines from both sources are positioned against the same shared time axis, so their relative timing is directly readable

#### Scenario: A line arrives late
- **WHEN** a line arrives whose time is earlier than lines already shown, because its source took longer to transcribe
- **THEN** it is placed among the other lines where its time falls, the spacing around it stays proportional, and the elapsed times shown are measured from the session's earliest line

#### Scenario: Filtered view keeps true gaps
- **WHEN** the user shows only one source, or searches, so that some lines are hidden
- **THEN** the space and any duration label between two visible lines reflect the time between those two lines, not the time from a hidden line

#### Scenario: Gap durations near a unit boundary
- **WHEN** a gap lasts just under a whole minute or a whole hour, such as 59 minutes 59.6 seconds
- **THEN** its label rounds to the next unit (for example "1 h"), and never reads "60 s" or "60 min"
