## MODIFIED Requirements

### Requirement: Handle interruption gracefully
The system SHALL handle Ctrl+C by stopping capture, finalizing the transcript, cleaning up resources, and exiting without a crash.

#### Scenario: User interrupts live capture
- **WHEN** the user presses Ctrl+C during live capture
- **THEN** the system stops capture and worker threads, closes the output file, releases audio devices, and saves any transcript produced

#### Scenario: User interrupts file transcription
- **WHEN** the user presses Ctrl+C during file transcription
- **THEN** the system stops cleanly and exits with the interrupted exit code
