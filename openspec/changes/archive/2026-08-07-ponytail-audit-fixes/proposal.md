## Why

A ponytail audit found ~500 lines of dead code, speculative features, and reinvented logic: the speaker-diarization feature references modules that have never existed in the repo, two whole capabilities are duplicates or unreachable, and three nearly identical live-transcription loops are copied inline. Removing them shrinks the codebase without losing any working behavior.

## What Changes

- **BREAKING** Remove speaker diarization entirely: `--diarize`, `--hf-token`, `--num-speakers`, `--min-speakers`, `--max-speakers` flags, the diarization blocks in file and live modes, and the unreachable AudioBuffer-based live path. The referenced `speaker_diarization.py` and `audio_buffer.py` modules do not exist, so enabling diarization crashes today.
- **BREAKING** Delete the standalone `convert_to_srt.py` script; SRT writing is already covered by `save_transcript("srt")`.
- Delete dead methods: `transcribe_stream()`, `AudioCapture.capture_to_file()`, `WASAPICapture.list_loopback_devices()`, and the unused `duration_after_vad` metadata field.
- Remove dead word-level timestamp plumbing: `include_words` is never enabled, so drop the `words` list from segment dicts and the `include_words` branch in `format_transcript`.
- Collapse the three SSL-verification-disable mechanisms (ssl context patch, three env vars, httpx monkey-patch) into a single env var.
- Extract the triple-copied chunk→resample→transcribe→offset logic (`transcribe_live_simple`, `sys_worker`, `mic_worker`) into one helper.
- Merge the three near-identical Teams `.bat` launchers into one script parameterized by flags.
- Drop redundant `shutdown_requested` checks in capture callbacks (the signal handler already raises `KeyboardInterrupt`).
- Remove unused requirements: `pydub`, `onnxruntime`.

## Capabilities

### New Capabilities

### Modified Capabilities
- `transcription`: segment dicts no longer include word-level timestamps; the unused streaming-iterator API and word-data plumbing are removed.
- `speaker-diarization`: **REMOVED** — the capability is deleted; no implementation exists for it.
- `transcript-conversion`: **REMOVED** — the standalone transcript-to-SRT converter is deleted; SRT output remains available via `--format srt`.

## Impact

- Code: `transcriber.py`, `transcription_engine.py`, `audio_capture.py`, `wasapi_capture.py`, `convert_to_srt.py` (deleted), `start_teams_transcription*.bat`, `start_t_actual_time.bat`, `requirements*.txt`, `README.md` (drop diarization/convert docs), `openspec/specs/speaker-diarization/` and `openspec/specs/transcript-conversion/` (deleted at sync).
- CLI surface: the five diarization flags are removed (**BREAKING** for any script that passes them).
- Dependencies: `pydub`, `onnxruntime` removed from requirements.
