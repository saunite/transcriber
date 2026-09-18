## MODIFIED Requirements

### Requirement: Handle interruption gracefully
The system SHALL handle Ctrl+C by stopping capture, finalizing the transcript, cleaning up resources, and exiting without a crash. An interrupted live session's transcript SHALL include what was said up to the interruption, not only up to the last completed chunk.

#### Scenario: User interrupts live capture
- **WHEN** the user presses Ctrl+C during live capture
- **THEN** the system stops capture and worker threads, closes the output file, releases audio devices, and saves any transcript produced

#### Scenario: The last words before an interruption are kept
- **WHEN** the user presses Ctrl+C a few seconds after speech that has not yet filled a chunk
- **THEN** that speech appears in the saved transcript before the system exits

#### Scenario: User interrupts file transcription
- **WHEN** the user presses Ctrl+C during file transcription
- **THEN** the system stops cleanly and exits with the interrupted exit code
