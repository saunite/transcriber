## ADDED Requirements

### Requirement: Extract audio from video files
The system SHALL extract audio from video files (e.g., mp4, avi, mkv, mov, wmv, flv, webm, m4v) to a mono WAV file using ffmpeg, resampled to 16000 Hz.

#### Scenario: Extract audio from an existing video file
- **WHEN** a user requests transcription of a video file that exists
- **THEN** the system extracts its audio to a mono 16000 Hz WAV file using ffmpeg and uses the extracted audio for transcription

#### Scenario: Extract audio to a temporary file
- **WHEN** no explicit output path is provided for extraction
- **THEN** the system writes the extracted audio to a temporary WAV file in the system temp directory

#### Scenario: Extract audio to a specified path
- **WHEN** an explicit output path is provided
- **THEN** the system writes the extracted audio to that path

### Requirement: Validate ffmpeg availability
The system SHALL check that ffmpeg is available in PATH before attempting extraction and SHALL raise an error if it is not installed.

#### Scenario: ffmpeg is not installed
- **WHEN** a user attempts to extract audio and ffmpeg is not installed or not in PATH
- **THEN** the system raises an error instructing the user to install ffmpeg

### Requirement: Clean up temporary audio files
The system SHALL delete the temporary extracted audio file after transcription completes.

#### Scenario: Temp audio cleanup on success
- **WHEN** file transcription completes and a temporary audio file was created
- **THEN** the system removes the temporary audio file

#### Scenario: Temp audio cleanup failure
- **WHEN** the temporary audio file cannot be deleted after transcription
- **THEN** the system prints a warning and continues without failing the run
