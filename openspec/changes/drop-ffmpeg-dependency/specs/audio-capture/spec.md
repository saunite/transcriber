## REMOVED Requirements

### Requirement: Save captured audio to WAV

**Reason**: Replaced below by an equivalent requirement whose merge step no longer depends on an external ffmpeg binary. Expressed as REMOVED + ADDED rather than MODIFIED because both of its merge scenarios ("Merge uses ffmpeg", "Merge without ffmpeg") describe a conditional-on-ffmpeg behavior that ceases to exist — a MODIFIED block would have to carry them forward verbatim.

**Migration**: None for users. The saved WAV files, their names, and their contents are unchanged; only the mechanism producing `<base>_merged.wav` changes.

## ADDED Requirements

### Requirement: Save captured audio to WAV files
The system SHALL optionally save captured audio (system and/or microphone) to WAV files alongside the transcript, and SHALL merge system and mic recordings into a stereo WAV when both exist, without invoking any external media tool.

#### Scenario: Save audio enabled in WASAPI mode
- **WHEN** a user enables audio saving in WASAPI live mode with mic capture
- **THEN** the system writes system audio to `<base>_sys.wav`, mic audio to `<base>_mic.wav`, and a merged stereo `<base>_merged.wav`

#### Scenario: Merge produces an aligned stereo file
- **WHEN** both system and mic WAV files exist
- **THEN** the system writes a 2-channel WAV at the same sample rate and bit depth as the inputs, with system audio on one channel and mic audio on the other, truncated to the shorter of the two recordings

#### Scenario: Merge fails
- **WHEN** the merge cannot be completed (for example an I/O error reading or writing the WAV files)
- **THEN** the system prints a warning that the merge was skipped and continues, leaving the transcript and the separate WAV files intact
