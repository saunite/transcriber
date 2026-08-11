## 1. Simple live capture path

- [x] 1.1 In `_process_audio_chunk` (transcriber.py), stop reconstructing `base_time` from `datetime.now() - chunk_duration_sec`; return plain relative segment times regardless of `use_actual_time` and let the caller decide how to timestamp the line.
- [x] 1.2 In `transcribe_live_simple`'s result loop, when `args.actual_time` is set, prefix each printed/written line with `datetime.now().strftime("%Y-%m-%d %H:%M:%S")` read at emit time instead of the `[start -> end]` wall-clock range.

## 2. WASAPI live capture path

- [x] 2.1 In `_drain_and_transcribe` / `_emit` (transcriber.py), when `args.actual_time` is set, stamp each emitted line with `datetime.now().strftime("%Y-%m-%d %H:%M:%S")` read at emit time instead of the reconstructed wall-clock range from `_process_audio_chunk`.

## 3. Verify file mode unaffected

- [x] 3.1 Confirm `transcribe_file` / `save_transcript` in transcription_engine.py still use the existing fixed-`base_time` `[start -> end]` range behavior for `--actual-time` (no code change expected there).

## 4. Update spec-adjacent docs and check

- [x] 4.1 Update any `--actual-time` usage help text/README mentions of wall-clock output to describe the new single-timestamp live format, if present.
- [x] 4.2 Manually run `python transcriber.py --live --actual-time` (or WASAPI variant) for a short session and confirm printed timestamps track the visible system clock with no accumulating drift.
