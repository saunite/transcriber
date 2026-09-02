## ADDED Requirements

### Requirement: Decode media without an external media tool
The system SHALL accept both audio and video files for transcription and SHALL decode them using its bundled decoding library, without requiring any external media tool to be installed or present on PATH.

#### Scenario: Video file transcribed with no ffmpeg installed
- **WHEN** a user transcribes a video file (e.g. mp4, mkv, mov, webm) on a machine with no ffmpeg binary available on PATH
- **THEN** the system decodes the file's audio stream and transcribes it successfully, without invoking any external process

#### Scenario: Audio file transcribed with no ffmpeg installed
- **WHEN** a user transcribes an audio file (e.g. mp3, wav, flac, m4a, ogg, opus) on a machine with no ffmpeg binary available on PATH
- **THEN** the system decodes and transcribes it successfully

#### Scenario: No temporary extracted audio is written
- **WHEN** a user transcribes a video file
- **THEN** the system reads the original file directly and writes no intermediate extracted audio file

#### Scenario: Undecodable file
- **WHEN** a user transcribes a file that exists but cannot be decoded (unsupported format or corrupt media)
- **THEN** the system reports a clear single-line error naming the file and stating that the format is unsupported or the file is corrupt, and exits with a non-zero code without emitting a raw traceback
