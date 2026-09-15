## ADDED Requirements

### Requirement: The engine does not leave its unpacked copy behind
The application's engine unpacks itself into the system temporary directory each time it runs. The system SHALL give a stopping live session's engine enough time to exit on its own, so that its unpacked copy is removed, before terminating it forcibly. When the application quits, it SHALL stop any engine that is still running in the same way, so no engine keeps capturing or transcribing after the application has closed. When the application starts, the system SHALL remove, without delaying the window from opening, every unpacked copy in the system temporary directory that belongs to the application's engine and whose engine process is no longer running. The system SHALL NOT remove a copy used by a running engine, nor any temporary folder that does not belong to the application's engine.

#### Scenario: A stop that takes a few seconds
- **WHEN** a user stops a live session whose engine needs several seconds to finish the audio it is transcribing
- **THEN** the engine exits on its own before being terminated forcibly, and its unpacked copy no longer exists afterwards

#### Scenario: Quitting the application during a session
- **WHEN** a user closes the application while a live session or a file transcription is running
- **THEN** that engine stops, no engine process from the application keeps running, and its unpacked copy no longer exists afterwards

#### Scenario: Leftovers from a killed engine are removed at the next start
- **WHEN** the application starts and the system temporary directory holds an unpacked copy of the application's engine whose engine process is no longer running
- **THEN** that copy is removed, and the window opens without waiting for the removal

#### Scenario: A running engine's copy is kept
- **WHEN** the application starts while another running instance's engine is using its unpacked copy
- **THEN** that copy is left in place

#### Scenario: Other applications' folders are untouched
- **WHEN** the application starts and the system temporary directory holds unpacked folders of other applications built the same way, whether or not their processes are running
- **THEN** those folders are left in place
