## Why

`--actual-time` timestamps are supposed to show the real local clock time, but they're reconstructed as `base_time + audio_offset_seconds`. Each chunk's `base_time` is recomputed as `datetime.now() - chunk_duration`, computed *after* that chunk finishes transcribing — so the timestamp silently bakes in however long inference took for that chunk. Since inference time varies (load, model size, GPU vs CPU), the printed time doesn't track the real wall clock consistently; it drifts by a different amount each chunk instead of just showing "what time is it right now."

## What Changes

- Wall-clock timestamps (`--actual-time`) now show the actual local time at the moment a segment is emitted, read directly from the system clock — no more reconstructing a historical time from audio-offset arithmetic.
- Live/streaming timestamp format switches from a `[start -> end]` wall-clock range to a single `YYYY-MM-DD HH:MM:SS` stamp per line, since the range was an approximation anyway and a single current-time stamp is what was asked for.
- File-mode (`transcribe_file`) wall-clock timestamps still use the existing `[start -> end]` range derived from one fixed `base_time` — no live-processing lag applies there, so no drift exists to fix.

## Capabilities

### Modified Capabilities
- `transcription`: The "Format timestamps for output" requirement's wall-clock scenario changes from "anchored to the session or chunk start" (offset math) to "read from the system clock at the moment the segment/line is produced" (live/streaming paths only).

## Impact

- `transcription_engine.py`: `format_timestamp` / `_format_wall_time` usage for live paths.
- `transcriber.py`: `_process_audio_chunk`, `transcribe_live_simple`, `transcribe_live_wasapi` — remove per-chunk `base_time` reconstruction, stamp with current time at emit.
- No CLI flag or output file path changes; `--actual-time` behavior is unchanged for file mode.
