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
The system SHALL let users choose the whisper model size (tiny, base, small, medium, large, turbo), the execution device (auto, cpu, cuda), and compute type (auto, int8, float16, float32), with auto-detection from the environment. The system SHALL also accept an explicit local model directory path, which SHALL be used to load the model directly instead of resolving the model by name through the network/cache lookup, when provided.

#### Scenario: Auto device detection
- **WHEN** no device is specified
- **THEN** the system selects CUDA if torch reports a GPU available, otherwise CPU, and picks float16 for GPU or int8 for CPU when compute type is auto

#### Scenario: Explicit local model path provided
- **WHEN** a local model directory path is provided
- **THEN** the system loads the model from that directory directly, without attempting a network or cache-based model name lookup

#### Scenario: Local model path missing or incomplete
- **WHEN** a local model directory path is provided but the directory does not exist or is missing required model files
- **THEN** the system reports a clear error identifying the missing path before attempting to construct the model

#### Scenario: No local model path provided
- **WHEN** no local model directory path is provided
- **THEN** the system resolves the model by name exactly as before (network/cache lookup), unaffected by this capability

### Requirement: Control language and task
The system SHALL let users specify a language code and a task of transcribe (keep original language) or translate (translate to English), defaulting language to auto-detection and task to transcribe.

#### Scenario: Explicit language and translate task
- **WHEN** a user sets `--language en` and `--task translate`
- **THEN** the system transcribes with English as the language and translates to English

### Requirement: Format timestamps for output
The system SHALL format segment times as relative `[MM:SS -> MM:SS]` ranges when actual-time mode is off. When actual-time mode is on: file transcription SHALL format wall-clock time as a `[start -> end]` range anchored to one base time captured once at the start of file processing; live/streaming transcription SHALL format wall-clock time as a single `YYYY-MM-DD HH:MM:SS` timestamp read directly from the system clock at the moment each output line is produced, not reconstructed from audio offsets or chunk duration. Local-time resolution SHALL reflect the OS's actual configured timezone regardless of an inherited shell environment variable the process can't correctly interpret.

#### Scenario: Relative timestamps
- **WHEN** actual-time mode is off
- **THEN** the system formats timestamps as relative ranges from the start of the audio

#### Scenario: Wall-clock timestamps for file transcription
- **WHEN** actual-time mode is on and transcribing a file
- **THEN** the system formats timestamps as a `[start -> end]` wall-clock range anchored to one base time captured when file transcription began

#### Scenario: Wall-clock timestamps for live transcription
- **WHEN** actual-time mode is on during live capture (simple or WASAPI mode)
- **THEN** the system stamps each output line with the current local date and time read from the system clock at the moment that line is produced, regardless of how long transcription of that chunk took

#### Scenario: Launched from a shell with an incompatible inherited TZ variable
- **WHEN** the process is launched from a shell (e.g. Cygwin) that exports an IANA-style `TZ` environment variable the Windows C runtime cannot parse
- **THEN** wall-clock timestamps still reflect the OS's actual configured local timezone, not UTC

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
