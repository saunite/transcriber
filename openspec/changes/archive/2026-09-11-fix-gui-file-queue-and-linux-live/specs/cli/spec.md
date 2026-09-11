## MODIFIED Requirements

### Requirement: Select Linux dual-source live capture mode
The system SHALL route live capture through the auto-detected monitor/loopback source with optional concurrent microphone capture via `--include-mic` and `--mic-device` when neither `--wasapi` nor `--coreaudio-tap` is set (the Linux default live-capture path). A microphone device that cannot open at the transcription sample rate (16 kHz) SHALL be opened at its own default sample rate and resampled to 16 kHz rather than failing the session.

#### Scenario: Default live capture with microphone
- **WHEN** a user runs `--live --include-mic --mic-device N` with no `--wasapi` or `--coreaudio-tap`
- **THEN** the system captures the monitor source and microphone concurrently, labeling segments `[SYS]` and `[MIC]`

#### Scenario: Default live capture without microphone
- **WHEN** a user runs `--live` without `--include-mic`, `--wasapi`, or `--coreaudio-tap`
- **THEN** the system captures only the monitor source, unchanged from today's behavior

#### Scenario: Microphone that refuses 16 kHz
- **WHEN** the selected or auto-detected microphone refuses to open at 16 kHz (for example a raw ALSA `hw:` device that only accepts 44.1 or 48 kHz)
- **THEN** the system opens it at the device's default sample rate, resamples its audio to 16 kHz, and transcribes `[MIC]` segments as usual, instead of exiting with an "Invalid sample rate" error

## ADDED Requirements

### Requirement: File transcription fails on input with no decodable audio
File transcription SHALL fail when no audio can be decoded from the input file, meaning the decoder yields effectively zero duration (under 0.1 seconds), as happens with a non-media file given a media extension. On such input the system SHALL exit non-zero, report that the file has no decodable audio, and SHALL NOT leave a transcript file behind. Input that decodes to real audio with no speech in it is not a failure.

#### Scenario: Non-media file with a media extension
- **WHEN** a user transcribes a binary file renamed to `.mp3` and the decoder yields effectively zero duration
- **THEN** the command exits non-zero with a message that the file has no decodable audio, and no transcript file is created

#### Scenario: Silent recording
- **WHEN** a user transcribes a real audio file several seconds long that contains no speech
- **THEN** the command succeeds as before, exiting 0 with an empty transcript
