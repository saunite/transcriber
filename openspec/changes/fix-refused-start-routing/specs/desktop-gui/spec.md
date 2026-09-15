## ADDED Requirements

### Requirement: A refused start leaves the screen as it was
When the application refuses to start a live session or a file transcription, the system SHALL tell the user why and SHALL leave everything else as it was before the attempt: the transcript already shown in either chart stays visible, lines from a session that is still running keep appearing in that session's own chart, the running session's status keeps reflecting that session, and what the interface showed about how the previous session ended stays shown.

#### Scenario: File dropped during a live session
- **WHEN** a live session is running and the user drops a file, and the application refuses to transcribe it because the live session is still running
- **THEN** the user is told why, later transcript lines from the live session still appear in the live chart, the live status does not report a stall for lines that did arrive, and the file chart keeps whatever it showed before

#### Scenario: Live start refused
- **WHEN** the live chart shows a previous session's transcript and the user starts a new live session that the application refuses to start
- **THEN** the user is told why, and the previous session's transcript and the explanation of how that session ended remain shown

#### Scenario: Live start refused during a file transcription
- **WHEN** a file transcription is running and a live start is refused because of it
- **THEN** the file transcription's queue and output keep being shown as that file transcription's, not as a live session's
