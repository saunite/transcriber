## Context

See proposal.md for why. The current flow:

- **Dual-source live capture** (Linux, WASAPI, Core Audio) runs through `_run_dual_capture`. Capture callbacks only enqueue audio. One `_drain_and_transcribe` thread per source takes blocks from its queue, resamples to 16 kHz, and cuts a chunk once it has `threshold` samples. The chunk is SYS `chunk_duration` (10 s from the GUI) or MIC 5 s. The last 1 s is kept as the start of the next chunk.
- **The single-source path** `transcribe_live_simple` does the same inside its capture callback, at the device's native rate. `_process_audio_chunk` resamples per chunk.
- **Both paths** call `_process_audio_chunk(engine, audio, time_offset, ...)`. It returns a new offset `time_offset + len(chunk)`, which is where C2 comes from. The MIC gate (`max < 0.01`) and an exception both skip that call, so the offset doesn't move.
- **With `--actual-time`**, each emitted line is stamped `_wall_clock_stamp()` at print time (C1). The line format `[YYYY-MM-DD HH:MM:SS] [TAG] text` is parsed by the shell's regex and `parseStamp` in `main.js`.
- **In `main.js`**, `appendTranscriptLine` appends. Each line's `data-offset` is seconds from the first line of the flow (`sessionOrigin`). `relayout` walks all children, hidden ones included, and uses `previous` from the last line with an offset.

## Goals / Non-Goals

**Goals:**
- A stamp that doesn't depend on inference, queue or buffering time.
- One position rule shared by both live paths.
- A GUI that stays correct with lines arriving out of order.

**Non-Goals:**
- Sub-second stamps. The line format keeps whole seconds, so nothing downstream changes.
- Correcting audio-clock drift against the system clock, or audio that PortAudio drops (D1).
- Reordering lines in the transcript *file*. See Risks.
- Transcribing the partial chunk left in the buffer when a session stops. That's existing behaviour, not part of cluster C.

## Decisions

### 1. The stamp is stream start plus sample position

Each stream records `stream_start = now() - len(first block) / rate` when its first block is handled:
- in `_drain_and_transcribe`, the first block taken from the queue;
- in `transcribe_live_simple`, the first callback.

The worker is idle at that moment, so the delay is at most the 50 ms poll. From then on, `position` (seconds) counts only new audio. A segment's time is `position_of_chunk + segment.start`. Its stamp is `stream_start + that`, formatted like `_wall_clock_stamp` (which gains an optional `at` argument).

- **Alternative, rejected:** reading `now()` when a chunk is cut, minus its length. It's still skewed by how long the worker was busy with the previous chunk; that is the 2026-08-11 drift again, only smaller.
- **Alternative, rejected:** a per-sample capture clock from PortAudio `time_info`. It isn't available for parec, WASAPI via pyaudiowpatch, or the Core Audio helper, so it isn't one rule for all paths.

### 2. Position advances by what the buffer does not keep

After cutting a chunk, `advance = (len(chunk) - len(kept overlap)) / rate`. That's the same arithmetic the buffer already does, so position and buffer can't disagree. It runs **before** the gate and the `try`, so a skipped or failed chunk still advances. `_process_audio_chunk` stops returning an offset: it takes `chunk_start` and returns `(results, spoke)`. Callers own the position.

### 3. The overlap is split at its midpoint, by word

`transcribe_chunk` passes `word_timestamps=True` and adds `words: [(start, end, text)]` to each segment (faster-whisper keeps them on the original timeline under `vad_filter`). `_process_audio_chunk` keeps a word when `lead <= word.start < len(chunk) - trail`:
- `lead` is half the overlap when the chunk began with carried overlap (`chunk_start > 0`), else 0;
- `trail` is half the overlap when this chunk leaves overlap for the next one, else 0.

A segment is rebuilt from its kept words: text joined, start from the first word, end from the last. A segment with no kept words is dropped. A segment without `words` (the test fakes) is treated as one word spanning the segment, so existing fakes keep working.

- **Why the midpoint:** a word cut at the end of one chunk is heard whole in the next, and each boundary word belongs to exactly one chunk.
- **Alternative, rejected:** dropping segments that sit inside the overlap. faster-whisper often returns one segment for most of a 10 s chunk, so its first words would still repeat.
- **Alternative, rejected:** text de-duplication across chunks. It's fuzzy, and it breaks on speech that genuinely repeats.

### 4. The GUI inserts by time and re-bases the origin

`appendTranscriptLine` walks back from the last child while that child's `data-offset` is greater than the new line's, and inserts after the first child that isn't. A line without an offset still appends. When a line is earlier than `sessionOrigin`, the origin moves to it and every existing `data-offset` in that list grows by the difference, so elapsed labels are measured from the earliest line. Scrolling still goes to the bottom.

`relayout` gives hidden lines no margin and doesn't update `previous` from them. With the list ordered, `previous` can't move backwards, and the clamp stays as a guard.

- **Alternative, rejected:** holding lines back to reorder them before display. It adds delay and a timer, for a window that nobody watches during capture.

### 5. `formatDuration` rounds first

It rounds to whole seconds, then splits into h/min/s. Minutes in the hour form round from the rounded total. So 3599.6 s becomes 3600 s, which reads "1 h".

## Risks / Trade-offs

- **[Word timestamps cost inference time]** → Task 1.3 measures a 10 s chunk with and without them on the bundled `base` model on CPU. If it's more than 25 % slower, apply pauses and reports before continuing.
- **[Whisper word times are approximate, ±0.2 s is typical]** → The split has half a second of margin either side. A word right at the midpoint could still, rarely, appear twice or not at all. The real-speech check bounds this on the test recording.
- **[Stamps lag if audio is dropped]** → Unbounded queues mean the dual paths don't drop audio. The explicit `--audio-device` simple path can (D1), and its stamps then fall behind real time, as the proposal notes.
- **[The transcript file keeps arrival order]** → SYS and MIC lines can appear slightly out of time order in the `.txt`, each with its correct stamp. Sorting would mean rewriting the file or holding lines back. Left as is.
- **[The first-block estimate]** → It's off by the capture backend's block latency, tens of milliseconds, well under the one-second stamp resolution.

## Migration Plan

None. The line format, CLI flags and events are unchanged. Transcripts written before the change keep their print-time stamps.
