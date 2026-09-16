## MODIFIED Requirements

### Requirement: File transcription via drag-and-drop
The system SHALL accept dropped (or browsed) video/audio files and transcribe them using the sidecar, producing output in the user's selected format (txt/srt/vtt). Files SHALL be transcribed one at a time: files added while a transcription is running SHALL join a visible queue instead of starting concurrently, and the system SHALL show which file is being transcribed and the state of every queued file.

#### Scenario: Drop a video file
- **WHEN** a user drags a supported video file onto the app
- **THEN** the system extracts audio and transcribes it via the sidecar, and the transcript appears in the file view line by line while the transcription runs, not only once it finishes

#### Scenario: Drop an unsupported file
- **WHEN** a user drags a file with an unrecognized extension onto the app
- **THEN** the system shows an error without attempting to spawn the sidecar, and the file does not join the queue

#### Scenario: Drop a file while another is transcribing
- **WHEN** a user drops a supported file while a file transcription is running
- **THEN** the file joins the queue as waiting, no second transcription starts, and it is transcribed after the files ahead of it finish

#### Scenario: Add several files at once
- **WHEN** a user drops several supported files at once, or selects several in the file dialog
- **THEN** all of them join the queue in order and are transcribed one after another

#### Scenario: Progress is visible
- **WHEN** a file transcription is running
- **THEN** the File panel names the file being transcribed, and every queued file shows whether it is waiting, transcribing, done, or failed

#### Scenario: A queued file fails
- **WHEN** a file's transcription fails
- **THEN** that file is marked failed and the next waiting file starts
