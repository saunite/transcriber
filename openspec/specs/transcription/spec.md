# Transcription

## Purpose

Transcribe audio files and live audio chunks using faster-whisper, with configurable model/device settings, language and task control, timestamp formatting, incremental saving, and silence auto-stop.

## Requirements

### Requirement: Transcribe audio files
The system SHALL transcribe an audio file using faster-whisper and return a list of segments (start, end, text) plus metadata (language, language probability, duration), applying voice activity detection to filter silence.

#### Scenario: Transcribe a file with detected language
- **WHEN** a user transcribes an audio file without specifying a language
- **THEN** the system auto-detects the language and returns segments with timestamps and the detected language with its probability

#### Scenario: Transcribe a missing file
- **WHEN** a user requests transcription of a file that does not exist
- **THEN** the system raises a file-not-found error

### Requirement: Transcribe live audio chunks
The system SHALL transcribe audio chunks in real time for streaming, using a lower beam size for speed, and accumulate timestamps across chunks using a running time offset.

#### Scenario: Chunk transcription produces segments
- **WHEN** a live audio chunk contains speech
- **THEN** the system returns segments whose start/end times are offset by the cumulative chunk time

#### Scenario: Chunk with no speech
- **WHEN** a live audio chunk contains no detectable speech
- **THEN** the system reports no speech detected and continues

### Requirement: Control model, device, and compute settings
The system SHALL let users choose the whisper model size (tiny, base, small, medium, large, turbo), the execution device (auto, cpu, cuda), and compute type (auto, int8, float16, float32), with auto-detection from the environment.

#### Scenario: Auto device detection
- **WHEN** no device is specified
- **THEN** the system selects CUDA if torch reports a GPU available, otherwise CPU, and picks float16 for GPU or int8 for CPU when compute type is auto

### Requirement: Control language and task
The system SHALL let users specify a language code and a task of transcribe (keep original language) or translate (translate to English), defaulting language to auto-detection and task to transcribe.

#### Scenario: Explicit language and translate task
- **WHEN** a user sets `--language en` and `--task translate`
- **THEN** the system transcribes with English as the language and translates to English

### Requirement: Format timestamps for output
The system SHALL format segment times either as relative `[MM:SS -> MM:SS]` ranges or as wall-clock timestamps, based on the actual-time option.

#### Scenario: Relative timestamps
- **WHEN** actual-time mode is off
- **THEN** the system formats timestamps as relative ranges from the start of the audio

#### Scenario: Wall-clock timestamps
- **WHEN** actual-time mode is on
- **THEN** the system formats timestamps using wall-clock time anchored to the session or chunk start

### Requirement: Save transcripts in multiple formats
The system SHALL save transcripts in txt, srt, or vtt format, with txt supporting timestamps toggling and srt/vtt using their standard time formats.

#### Scenario: Save as SRT
- **WHEN** a user requests SRT output
- **THEN** the system writes numbered subtitles with `HH:MM:SS,mmm --> HH:MM:SS,mmm` cue times

#### Scenario: Save as VTT
- **WHEN** a user requests VTT output
- **THEN** the system writes a `WEBVTT` header followed by `HH:MM:SS.mmm --> HH:MM:SS.mmm` cues

#### Scenario: Save as TXT without timestamps
- **WHEN** a user requests TXT output with timestamps disabled
- **THEN** the system writes only the segment text, one per line

### Requirement: Save transcripts incrementally
The system SHALL write each transcribed segment to the output file immediately as it is produced, so partial transcripts survive interruption.

#### Scenario: Incremental save during file transcription
- **WHEN** file transcription is in progress with incremental save enabled
- **THEN** the system appends each segment to the output file as soon as it is transcribed

### Requirement: Auto-stop on silence
The system SHALL automatically stop live transcription after a configurable silence timeout, and SHALL never stop when the timeout is set to zero.

#### Scenario: Silence timeout exceeded
- **WHEN** live capture detects no speech for longer than the silence timeout
- **THEN** the system prints a notice and stops transcription

#### Scenario: Silence timeout disabled
- **WHEN** the silence timeout is set to 0
- **THEN** the system continues recording indefinitely until interrupted
