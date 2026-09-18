## MODIFIED Requirements

### Requirement: Transcribe live audio chunks
The system SHALL transcribe audio chunks in real time for streaming, using a lower beam size for speed. Each segment's time SHALL be its position in the captured audio stream: overlap carried between consecutive chunks SHALL NOT be counted twice, and every chunk SHALL advance the stream position, whether it was transcribed, skipped as silent, or failed to transcribe. Speech in the audio shared by two consecutive chunks SHALL appear in the output once, not repeated. When a live session stops, the audio captured since the last chunk SHALL be transcribed as one final, shorter chunk rather than discarded, under the same rules: stamped at its position in the stream, its overlap with the previous chunk not repeated, and the microphone's silence gate applied.

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

#### Scenario: Speech just before a stop is kept
- **WHEN** a live session stops part-way through a chunk, with speech in the audio captured since the last chunk
- **THEN** that speech is transcribed and written to the transcript, stamped at its position in the stream, and nothing already transcribed is repeated

#### Scenario: A silent tail adds nothing
- **WHEN** a live session stops and the audio captured since the last chunk is silent
- **THEN** no line is added for it
