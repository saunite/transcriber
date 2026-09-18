## Context

See `proposal.md` for why. How a live session ends today (`transcriber.py`, `_run_dual_capture`):

- Each source (SYS, and MIC when included) has a worker thread running `_drain_and_transcribe`. It appends blocks from its queue to `buffer`. When `sum(len(buffer)) >= threshold` (10 s at 16 kHz by default), it transcribes the buffer, advances `position`, and keeps the last second (`overlap_samples`) as `carried` for the next chunk.
- On stop (Ctrl+C / SIGINT, the silence timeout, or a lost source), the main thread closes the mic stream, sets `stop_event` and joins each worker with a 60 s timeout. The loop condition `while not stop_event.is_set() or not q.empty()` drains the queue, then exits. **Anything left in `buffer` below the threshold is dropped.** After the joins, the output file is closed.
- `_process_audio_chunk(engine, data, chunk_start, …, lead, trail, stream_start)` already handles a chunk of any length. `lead` and `trail` are the halves of the overlap shared with the neighbouring chunks, used to split boundary words.
- The desktop app stops the engine with SIGINT on Linux and macOS and waits up to `STOP_GRACE` (15 s) before a kill. On Windows it uses `taskkill /F` (see `02-flush-live-tail-on-stop-windows`).
- `tests/test_engine.py`'s `check_live_chunks` iterates `range(0, len(audio) - chunk + 1, chunk - overlap)`, so it also drops any remainder shorter than a whole chunk.

## Goals / Non-Goals

**Goals:**
- Every stop the engine runs its shutdown for transcribes the audio captured since the last chunk, once, at its true position.
- The engine check covers a recording's whole length.

**Non-Goals:**
- The Windows app's hard kill (change 02).
- Lowering the chunk length or streaming partial results while a chunk is still filling.

## Decisions

**1. Transcribe the remainder in the worker, after its loop, through the same code as a normal chunk.**
The chunk block in `_drain_and_transcribe` becomes a local function `transcribe(data, kept)`, called from the loop as today. After the loop it runs once more on whatever is buffered, with `kept = 0`, so nothing is carried and `trail = 0`, since there is no next chunk. It only runs if the buffer holds more than the `carried` overlap, meaning there's new audio. That shares the stamping, the lead/trail word split, the MIC silence gate, `last_speech_time`, `_emit` and `all_segments`, and keeps the final chunk from drifting from the others.
- *Lower the threshold when stopping, inside the loop:* same effect, but it tangles the stop condition into the chunking arithmetic.
- *Flush from the main thread after the joins:* the buffers and positions live in the worker. It would also race with the output file being closed.

**2. No minimum length for the tail.**
faster-whisper runs with `vad_filter=True` (`transcription_engine.py`), so a short or silent remainder yields no segments, and the MIC gate skips silent audio before inference. A minimum would reintroduce the loss for a final short word ("Thanks.").
- A test covers the silent tail, so a hallucinated line on silence would fail it.

**3. The resampler's few held frames are not flushed.**
A stream's resampler holds at most a few frames between blocks (`_resample`). Draining it at stop would add a few milliseconds of audio at best.
- `ponytail:` comment at the flush: the resampler's held frames aren't drained. Add `flush=True` if a tail word is ever found clipped by milliseconds.

**4. The engine check mirrors the loop: whole chunks, then one final chunk for what is left.**
After the `range` loop, if audio remains past the last chunk's end, `check_live_chunks` transcribes `audio[last_start + chunk - overlap:]` with `lead = overlap/2` and `trail = 0`, the same shape as Decision 1. A recording shorter than one chunk becomes a single final chunk from 0.

## Risks / Trade-offs

- [Transcribing the tail lengthens shutdown by one inference, about 1–2 s for up to 10 s of audio with the bundled `base` model on CPU, and longer with larger models] → Inside both the 60 s worker join and the app's 15 s grace for `base`/`small`. A slow `large` model on CPU could approach the app's 15 s, in which case the app kills the engine and the tail is lost, as today, without making anything else worse. **Measured 2026-09-18 (task 2.2):** a worst-case last chunk (the carried second plus 9 s of speech) takes a median of 2.7 s (2.46–3.06 s over five runs) with the bundled `base` model, int8, on this machine's 8-thread CPU, well inside 15 s. Larger models scale that up, so a `medium` or `large` model on a slow CPU is where the app's grace could run out.
- [A stop caused by a lost audio source also flushes] → What was captured before the source went away is genuine audio, so transcribing it is correct. The lost-source message and exit code are unchanged.
- [A tail inside the overlap only] → `buffer` holds only the carried overlap, which was already transcribed: skipped by the "more than `carried`" condition.
