## REMOVED Requirements

### Requirement: Save captured audio to WAV files

**Reason**: The feature could not honor what it specified. Its "Save audio enabled in WASAPI mode" scenario requires system audio to be written to `<base>_sys.wav`, but `_sys.wav` is written from `transform_sys` on the transcription worker thread, behind blocking inference, while `_mic.wav` is written from the real-time `mic_callback`. Whatever the worker never drains is never written, silently. Measured on real Windows hardware with the fastest available model (`tiny`): a 71.2s session produced a 41.1s `_sys.wav` — 42% of the system audio lost, with no warning to the user. A larger model makes the loss strictly worse. Rather than re-architect a recording path nothing consumes — the desktop GUI never passed `--save-audio`, and no other capability reads the files — the capability is withdrawn.

**Migration**: None. `--save-audio` is removed with no replacement and no deprecation period; the tool has no releases, so no user is relying on it. Live transcription, transcript output, and every other flag are unaffected. Users who need a recording of a session should capture it with a dedicated recorder alongside the transcriber.
