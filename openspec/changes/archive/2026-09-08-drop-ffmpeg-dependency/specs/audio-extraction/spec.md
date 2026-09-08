## REMOVED Requirements

### Requirement: Extract audio from video files

**Reason**: The extraction step is redundant. `faster-whisper` decodes through PyAV, whose wheels bundle FFmpeg's libraries, and its `decode_audio()` calls `av.open()` + `container.decode(audio=0)` — a full container demux that opens mp4/avi/mkv/mov/webm directly. Shelling out to an external ffmpeg to produce a temp 16kHz mono WAV was a decode-then-re-encode round trip in front of a decoder that handles the original file. Media decoding is now covered by the `transcription` capability.

**Migration**: None for users of audio files (behavior identical). Video files are passed to the transcription engine unchanged instead of being pre-extracted; no flag, path, or output changes.

### Requirement: Validate ffmpeg availability

**Reason**: No code path invokes an external ffmpeg binary after this change, so there is nothing to pre-flight. A file the bundled decoder genuinely cannot open now fails at the decode attempt with a clear message naming the file and format (see `transcription`'s "Decode media without an external media tool").

**Migration**: Users no longer need ffmpeg installed or on PATH.

### Requirement: Clean up temporary audio files

**Reason**: No temporary audio file is created — the engine reads the user's original file directly.

**Migration**: None; the temp files this described no longer exist.
