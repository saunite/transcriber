## Why

A repo-wide over-engineering audit surfaced dead parameters, dead imports, dead word-timestamp config, duplicated worker loops, and one dependency that reimplements a platform tool. Removing them shrinks the codebase and drops a Python dependency without changing any user-visible behavior.

## What Changes

- Remove the always-`True` `incremental_save` parameter from `TranscriptionEngine.transcribe_file()`; the incremental write block itself stays (it fulfills the "save transcripts incrementally" requirement).
- Extract the duplicated `sys_worker`/`mic_worker` drain-transcribe loops in the WASAPI live path into one parametrized worker.
- Replace the in-Python sys+mic WAV merge (via `soundfile`) with an ffmpeg `amerge` filter and remove `soundfile` from requirements.
- Remove the unused `duration`/`chunk_size` parameters and the `total_frames`/`frames_captured` bookkeeping from both capture classes.
- Drop `word_timestamps=True` from both faster-whisper calls (word-level data is no longer collected).
- Return only segments from `transcribe_chunk()` (its `info_dict` is discarded by the sole caller).
- Remove dead imports (`threading`, `Queue`) and the unused `AudioExtractor.system` attribute.
- Remove the unused `output_path` parameter from `AudioExtractor.extract_audio()`.
- Inline `format_transcript()` into its single caller, the `save_transcript()` txt branch.
- Fix the live-device flag in `start_transcription.sh` (`$DEVICE_FLAG` → `$AUDIO_DEVICE_FLAG`) — a correctness bug found during the audit.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. All changes are internal implementation details; no spec-level requirement behavior changes.

## Impact

- Code: `transcriber.py`, `transcription_engine.py`, `audio_capture.py`, `wasapi_capture.py`, `audio_extractor.py`, `start_transcription.sh`.
- Dependencies: remove `soundfile` from `requirements.txt` and `requirements-linux.txt`.
- Behavioral note: the `--save-audio` merge now requires ffmpeg on PATH (already a documented hard dependency).
