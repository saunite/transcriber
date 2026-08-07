## Context

The repo was audited for over-engineering. The findings are all internal: dead parameters, dead imports, duplicated logic, leftover whisper config, and a Python dependency (`soundfile`) used only to merge two WAVs that ffmpeg (already a hard dependency) can merge natively. No spec-level requirement changes; every user-visible behavior must stay identical.

## Goals / Non-Goals

**Goals:**
- Remove dead flexibility and dead code with no behavior change.
- Drop one Python dependency (`soundfile`).
- Collapse duplicated live-capture worker logic.

**Non-Goals:**
- No spec requirement changes (incremental saving, WAV saving/merging, timestamp formatting, and silence auto-stop all behave as specified).
- No performance tuning, no correctness fixes beyond the `start_transcription.sh` flag bug found in the same pass.
- No new abstractions beyond the single parametrized worker.

## Decisions

1. **Keep the incremental write block in `transcribe_file()`; remove only the `incremental_save` parameter.** The audit flagged the block because `save_transcript()` overwrites the file at the end, but the block is the only mechanism keeping a partial transcript if the user interrupts mid-transcription (the spec requires it). Dropping the always-`True` parameter removes the dead flexibility without touching the requirement.

2. **One parametrized WASAPI worker instead of `sys_worker`/`mic_worker`.** Both threads run an identical drain-buffer-concatenate-overlap-transcribe loop; only the queue, output tag, chunk threshold, and silence gate (`np.max(np.abs(...)) > 0.01`) differ. One function `_run_worker(queue, tag, threshold, gate_enabled)` called twice removes ~30 lines of duplication. Each worker keeps its own buffer and time offset via closure, so behavior is unchanged.

3. **ffmpeg `amerge` replaces the `soundfile` merge.** The current code stacks sys (L) and mic (R) mono 16 kHz WAVs into a stereo file, trimming to the shorter input. ffmpeg reproduces this with `[0:a][1:a]amerge=inputs=2:duration=shortest`. ffmpeg is already a documented hard dependency (audio extraction; bat launchers add it to PATH), so `--save-audio` gaining the same requirement is acceptable. `soundfile` is removed from `requirements.txt` and `requirements-linux.txt`. Alternative considered: keep `soundfile` (merge works without ffmpeg) — rejected because it keeps a whole dependency for ~15 lines of code the platform tool already does.

4. **Drop `word_timestamps=True` from both `model.transcribe()` calls.** The last cleanup removed word-level data from segment dicts but left the flag, which makes faster-whisper compute word timestamps that are discarded.

5. **`transcribe_chunk()` returns only segments.** The sole caller destructures with `segments, _ =`, so the `info_dict` (language, probability, duration) is built and discarded every chunk. The file-path `transcribe_file()` keeps its `info_dict` (the CLI summary uses it).

6. **Delete dead capture params and bookkeeping.** Both `capture_stream()` implementations expose `duration` and `chunk_size` that callers never set (`duration=None`, default `chunk_size`), plus WASAPI's `total_frames`/`frames_captured` counter. Removing them also removes the now-unreachable duration-check branches.

7. **Misc dead code removal:** unused imports (`threading`, `Queue` in `wasapi_capture.py`; `threading` in `audio_capture.py`), the never-read `AudioExtractor.system` attribute (and its `platform` import), and the unused `output_path` parameter of `AudioExtractor.extract_audio()`.

8. **Inline `format_transcript()`.** It has one caller (the txt branch of `save_transcript()`); the body moves there and the method is deleted. This avoids the more invasive alternative of keeping a public formatter nobody outside the class uses.

9. **Fix `start_transcription.sh`** to use `$AUDIO_DEVICE_FLAG` (it referenced a nonexistent `$DEVICE_FLAG`, so the chosen device was silently ignored). One-line correctness fix surfaced by the audit.

## Risks / Trade-offs

- ffmpeg required for `--save-audio` merge → ffmpeg is already a documented hard dependency; the merge runs only in WASAPI mode (Windows), where the bat launchers add ffmpeg to PATH.
- `amerge` pads to `shortest` rather than the current explicit `min()` trim → `duration=shortest` matches the existing behavior exactly.
- Worker extraction touches the WASAPI hot path → the helper preserves per-worker buffer/offset state and the same queue-drain pattern; verify with a live WASAPI smoke test.
- `word_timestamps=False` changes whisper compute slightly → output segment dicts are unchanged (words were never collected).
