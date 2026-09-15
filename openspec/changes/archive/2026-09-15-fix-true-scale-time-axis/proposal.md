## Why

Logic audit cluster C (2026-09-15, `openspec/backlog.md`). The chart promises a true-scale time axis, but the timestamps feeding it, and the way the page lays them out, are not true to when speech happened.

- **C1:** live `--actual-time` stamps are read when a line is *printed*, after inference.
  - Every segment of a chunk shares one stamp, so the chart can't space them.
  - SYS (10 s) and MIC (5 s) chunks lag by different amounts, so the two pens don't line up.
- **C2:** the 1 s chunk overlap is transcribed twice, so words repeat at every boundary.
  - The running offset advances by the whole chunk, overlap included. Relative stamps run +1 s fast per chunk: about +11 % on SYS (10 s for 9 s of new audio), +25 % on MIC (5 s for 4 s).
  - Found while reading: a MIC chunk skipped as silent, or one whose transcription fails, doesn't advance the offset at all, so MIC stamps fall behind after every quiet stretch.
- **C3:** `relayout()` measures a gap from the previous line even when Show or Find hides that line. An out-of-order line moves `previous` backwards, inflating the next gap.
- **C4:** `formatDuration` rounds its parts separately, printing "59 min 60 s" and "1 h 60 min".

The 2026-08-11 `fix-actual-time-drift` change chose print-time stamps. It was fixing a base time rebuilt after inference on *every* chunk, which drifted with inference time. This change instead reads the clock once per audio stream and counts position in audio samples, so inference and queue delays can't affect the stamp. The user chose this on 2026-09-15.

## What Changes

- **Speech-time stamps (C1):** with `--actual-time`, a live line carries the local time its speech began: the stream's start time plus the segment's position in the audio. The format stays a single `[YYYY-MM-DD HH:MM:SS]`, so the shell's regex, the GUI parser and the launchers are unchanged.
- **Correct stream position (C2):**
  - each chunk starts where the previous one's new audio ended, so the overlap no longer adds time;
  - every chunk advances the position, whether it was transcribed, skipped as silent, or failed.
- **No repeated words (C2):** live chunks are transcribed with word timestamps, and the overlap is split at its midpoint. A chunk keeps words that start before the midpoint of its trailing overlap; the next chunk keeps words from the midpoint of its leading overlap on. File transcription is untouched.
- **Chart order (C3):** a line is inserted where its time falls, not appended in arrival order. Gaps are measured between *visible* lines only, so Show and Find don't shrink them. The view still follows the newest arrival.
- **Durations (C4):** a duration is rounded as a whole before it's split, so it never reads "60 s" or "60 min".
- **Not in this change:**
  - audit cluster D. D1's in-callback inference drops audio on an explicit `--audio-device`, which would make those stamps lag;
  - the hour gap between GUI and engine timestamps (a separate backlog item);
  - the File view not showing file transcripts.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `transcription`:
  - **"Transcribe live audio chunks":** the offset is the chunk's position in the stream, excluding overlap. Every chunk advances it, and overlap words aren't repeated.
  - **"Format timestamps for output":** a live wall-clock stamp is the time its speech began, not the time the line was produced.
- `desktop-gui`, "Transcript time is rendered at true scale":
  - lines are ordered by time;
  - gaps are measured between visible lines;
  - gap labels never read "60 s" or "60 min".

## Impact

- **`transcriber.py`:**
  - `_process_audio_chunk` takes the chunk's start position and the overlap to split, cuts words at the midpoints and formats the stamp;
  - `_run_dual_capture._drain_and_transcribe` and `transcribe_live_simple` keep a per-stream start time and sample position.
- **`transcription_engine.py`:** `transcribe_chunk` requests `word_timestamps=True` and returns each segment's words. There's some extra inference cost, which gets measured.
- **`src/main.js`:** `appendTranscriptLine` inserts in time order and re-bases the elapsed origin when an earlier line arrives. `relayout` skips hidden lines, and `formatDuration` rounds first.
- **Tests:** `test_dual_capture.py` (positions, skipped chunks, speech-time stamps), a word-cut check with a fake engine, a real-speech check that no words repeat across chunks, and GUI scenarios for ordering, filtered gaps and durations.
- **Docs:** `DESIGN.md` (line order and gaps on the roll), and the README's `--actual-time` description.
- **No shell (Rust), dependency, line-format or layout changes.**
