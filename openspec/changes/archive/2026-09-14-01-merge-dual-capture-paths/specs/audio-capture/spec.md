## ADDED Requirements

### Requirement: Live audio reaches transcription at 16 kHz from each source's real rate
During live dual-source capture on every platform, the system SHALL convert system audio and microphone audio to 16 kHz for transcription starting from the sample rate each source actually delivers, never from an assumed rate. A microphone that cannot be opened at 16 kHz SHALL be opened at its own default rate and converted, instead of failing the session. An audio block too short to yield any 16 kHz samples SHALL be skipped, without interrupting capture.

#### Scenario: System audio at 44.1 kHz on Windows
- **WHEN** a WASAPI live session captures from an output device running at 44.1 kHz
- **THEN** the audio passed to transcription is 16 kHz and plays at its original speed and pitch

#### Scenario: Microphone that refuses 16 kHz
- **WHEN** a live session includes a microphone that does not accept 16 kHz, on any platform
- **THEN** the session opens the microphone at its default rate, converts its audio to 16 kHz, and transcribes `[MIC]` segments

#### Scenario: A very short audio block
- **WHEN** a capture source delivers a block too short to produce any 16 kHz samples
- **THEN** that block is skipped and the session keeps capturing and transcribing
