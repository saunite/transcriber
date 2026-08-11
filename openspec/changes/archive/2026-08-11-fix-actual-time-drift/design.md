## Context

Live/streaming transcription (`transcribe_live_simple`, `transcribe_live_wasapi`, both funneling through `_process_audio_chunk`) buffers audio into chunks, transcribes each chunk, then formats a wall-clock timestamp for every segment in that chunk. With `--actual-time`, `_process_audio_chunk` currently computes:

```python
base_time = datetime.now() - timedelta(seconds=chunk_duration_sec)
timestamp = engine.format_timestamp(seg['start'], seg['end'], use_actual_time=True, base_time=base_time)
```

`datetime.now()` here is read *after* `engine.transcribe_chunk(...)` returns, i.e. after inference finishes. Inference latency (model size, CPU vs GPU, system load) is unbounded and varies chunk to chunk, so `base_time` is off by that latency every time — the displayed time isn't wall-clock, it's wall-clock-minus-inference-lag, and the lag isn't constant.

## Goals / Non-Goals

**Goals:**
- Live output timestamps show the real current local time, not a value reconstructed from audio-offset math.
- Fix applies uniformly to both live paths (`transcribe_live_simple`, `transcribe_live_wasapi`/`_drain_and_transcribe`).

**Non-Goals:**
- File-mode (`transcribe_file`) timestamps are unaffected — there's no live-processing lag there, and the proposal doesn't ask for that path to change.
- Not attempting sub-chunk precision (i.e. a distinct timestamp per segment reflecting exactly when that segment's audio was spoken) — that would require tracking capture-time per audio sample, well beyond what "show the local clock" needs.

## Decisions

**Stamp with `datetime.now()` at emit time, one stamp per line, drop the `[start -> end]` wall-clock range.**
Replace `format_timestamp(..., use_actual_time=True, base_time=...)` in the live paths with a direct `datetime.now().strftime("%Y-%m-%d %H:%M:%S")` read at the point each result line is printed/written (in `transcribe_live_simple`'s result loop and in `_emit`/`_drain_and_transcribe` for WASAPI). This is what the user asked for — "the local hour minute and second of the localhost" — and it's a smaller change than trying to compute a more accurate historical range, which would still be an approximation and still capable of drifting.
- Alternative considered: keep the range format but compute `base_time` from when the chunk *started* buffering instead of `now() - chunk_duration`. Rejected — still an approximation of capture time, still drifts under load (buffering + inference lag together), and doesn't match what was requested (a single "what time is it" stamp, not a reconstructed range).

**`format_timestamp`/`_format_wall_time` keep their current behavior for file mode.**
`use_actual_time` in `transcribe_file`/`save_transcript` still anchors to one `base_time = datetime.now()` set once at the start of file processing and adds segment offsets — appropriate there since there's no live streaming lag to correct for, and changing it isn't part of this fix.

**No new CLI flag.** `--actual-time` continues to mean "show wall-clock time" in the live path; only its accuracy/definition changes, not its interface.

## Risks / Trade-offs

- [Losing the segment's duration information in live output] → Segment start/end within the chunk is still available in the segment dict for anything that needs it (e.g. `--save-audio` WAV files, or piping segments elsewhere); only the printed/written line's timestamp changes from a range to a point-in-time. Acceptable since the user explicitly asked for "the local hour minute and second," not a duration.
- [Emit-time stamp still lags true speech time by however long that chunk took to transcribe] → Same lag as today, just no longer disguised as a precise-looking wall-clock range; it now reads as "time this line was printed," which is what it actually is.
