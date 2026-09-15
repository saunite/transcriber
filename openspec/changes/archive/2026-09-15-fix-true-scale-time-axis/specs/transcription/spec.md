## MODIFIED Requirements

### Requirement: Transcribe live audio chunks
The system SHALL transcribe audio chunks in real time for streaming, using a lower beam size for speed. Each segment's time SHALL be its position in the captured audio stream: overlap carried between consecutive chunks SHALL NOT be counted twice, and every chunk SHALL advance the stream position, whether it was transcribed, skipped as silent, or failed to transcribe. Speech in the audio shared by two consecutive chunks SHALL appear in the output once, not repeated.

#### Scenario: Chunk transcription produces segments
- **WHEN** a live audio chunk contains speech
- **THEN** the system returns segments whose start and end times are their position in the captured stream, so stamps across many chunks stay in step with the audio rather than running ahead by the overlap

#### Scenario: Chunk with no speech
- **WHEN** a live audio chunk contains no detectable speech
- **THEN** the system reports no speech detected and continues

#### Scenario: A skipped chunk still takes time
- **WHEN** a microphone chunk is skipped as silent, or a chunk's transcription fails, and a later chunk contains speech
- **THEN** that later speech is stamped at its true position in the stream, including the time of the skipped or failed chunk

#### Scenario: Speech across a chunk boundary is not repeated
- **WHEN** a word is spoken within the audio shared by two consecutive chunks
- **THEN** the transcript contains that word once

### Requirement: Format timestamps for output
The system SHALL format segment times as relative `[MM:SS -> MM:SS]` ranges when actual-time mode is off. When actual-time mode is on: file transcription SHALL format wall-clock time as a `[start -> end]` range anchored to one base time captured once at the start of file processing; live/streaming transcription SHALL format wall-clock time as a single `YYYY-MM-DD HH:MM:SS` timestamp giving the local time at which that line's speech began, derived from when that audio source started delivering audio plus the speech's position in that source's audio, and unaffected by how long buffering or transcription took. Local-time resolution SHALL reflect the OS's actual configured timezone regardless of an inherited shell environment variable the process can't correctly interpret.

#### Scenario: Relative timestamps
- **WHEN** actual-time mode is off
- **THEN** the system formats timestamps as relative ranges from the start of the audio

#### Scenario: Wall-clock timestamps for file transcription
- **WHEN** actual-time mode is on and transcribing a file
- **THEN** the system formats timestamps as a `[start -> end]` wall-clock range anchored to one base time captured when file transcription began

#### Scenario: Wall-clock timestamps for live transcription
- **WHEN** actual-time mode is on during live capture
- **THEN** the system stamps each output line with the local date and time at which that line's speech began, regardless of how long transcription of that chunk took

#### Scenario: Lines from one chunk carry their own times
- **WHEN** actual-time mode is on during live capture and one chunk yields several segments spoken seconds apart
- **THEN** each line's stamp reflects when its own speech began, so the lines do not all share one stamp

#### Scenario: Both sources share one clock
- **WHEN** actual-time mode is on, system audio and the microphone use different chunk durations, and the same moment of speech is heard on both
- **THEN** the lines from both sources carry stamps for that same moment, within the precision of the stamp, rather than differing by how long each source's chunk took to fill and transcribe

#### Scenario: Launched from a shell with an incompatible inherited TZ variable
- **WHEN** the process is launched from a shell (e.g. Cygwin) that exports an IANA-style `TZ` environment variable the Windows C runtime cannot parse
- **THEN** wall-clock timestamps still reflect the OS's actual configured local timezone, not UTC
