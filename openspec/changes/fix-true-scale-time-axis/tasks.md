## 1. Engine tests first

- [x] 1.1 In `test_dual_capture.py`, add scenarios driving `_run_dual_capture` with the fake engine and `_feed`. Use a fixed `datetime.now` / `time` where needed, and `chunk_duration=2`, so chunk boundaries are deterministic:
  - **Position:** relative stamps (`actual_time=False`) for three consecutive SYS chunks with a segment at `start=0.6` in each are `00:00.60`, `00:01.60` and `00:02.60`. Today they are `00:00.60`, `00:02.60` and `00:04.60`, because the offset counts the overlap.
  - **Skipped chunk:** a silent MIC chunk followed by an audible one stamps the audible chunk's segment after the silent chunk's time, not at the silent chunk's start.
  - **Speech time:** with `actual_time=True` and the clock frozen for the whole run, a segment at `start=1.2` in the second SYS chunk is stamped `stream_start + 1 s + 1.2 s`. Two segments of one chunk (`start=0.1` and `start=1.4`) get different stamps.

  Verify each scenario **fails** against today's `transcriber.py`, recording which assertions fail.

  **Done 2026-09-15.** `_check_time_axis` is called from `main()`. Each section was run on its own against the unchanged engine, and each fails:
  - **Position:** `00.60`, `02.60`, `04.60` (expected `00.60`, `01.60`, `02.60`).
  - **Skipped chunk:** the MIC line is stamped `01.20` (expected `05.20`), since the silent 5 s chunk didn't advance the offset. It uses a paced fake mic stream that delivers a silent block, then an audible one.
  - **Speech time:** four lines, all `12:00:00`, the frozen print time. Expected three: `11:59:59`, `12:00:00` and `12:00:01`. The fourth line is the overlap repeat.

  Deviation: the speech-time section uses segments at 0.1 s and 1.4 s in each chunk, rather than one at 1.2 s in chunk 2. That one run covers both "distinct stamps within a chunk" and the second chunk's position.

- [x] 1.2 Add a word-cut check with a fake engine that returns segments carrying `words`, calling `_process_audio_chunk` directly (in `test_resample.py` beside its existing `_process_audio_chunk` check, or a new root `test_chunk_words.py` if that reads better). For a 10 s chunk with 1 s overlap on both sides:
  - words starting at 0.3 s and 9.7 s are dropped;
  - words at 0.5 s and 9.4 s are kept;
  - a segment left with no words is dropped;
  - the rebuilt segment's text and start/end come from the kept words;
  - the first chunk (`chunk_start == 0`) keeps a word at 0.1 s;
  - a segment without `words` is kept or dropped by its own start.

  Verify it fails against today's code.

  **Done 2026-09-15.** It's a new root `test_chunk_words.py` (the resample test is about resampling). Its fake segments carry `words`, and it checks:
  - the leading 0.3 s word and the trailing 9.7 s word are dropped, while 0.5 s and 9.4 s are kept;
  - a segment left empty is dropped;
  - the first chunk keeps 0.1 s;
  - a plain segment is kept or dropped by its start.

  Against today's code it fails: `_process_audio_chunk` has no overlap cut, so the call is rejected (`unexpected keyword argument 'lead'`).

- [x] 1.3 Measure word-timestamp cost. Run `TranscriptionEngine.transcribe_chunk` on 10 s chunks of `$TRANSCRIBER_TEST_SPEECH` with the bundled model, on CPU, with and without `word_timestamps=True`, and record the mean time per chunk for both under this task.

  Verify the slowdown is at most 25 %. If it's more, pause apply and report the numbers (design.md, Risks).

  **Done 2026-09-15.** 28.8 s recording, three 10 s chunks, bundled `base` model on CPU int8, `beam_size=3`, `vad_filter=True`, one warm-up, two rounds:
  - **plain:** 1.458 and 1.600 s per chunk (mean 1.53 s);
  - **with words:** 1.579 and 1.555 s per chunk (mean 1.57 s).

  That's about +2.5 %, well within 25 %, and inference stays far below the 10 s chunk.

- [x] 1.4 In `tests/test_engine.py`, add a real-speech check, "live chunks do not repeat words". It runs only when a speech recording is set and no `--engine` binary is given, since it runs in-process:
  - decode the recording to 16 kHz;
  - feed 10 s chunks with the 1 s overlap through `_process_audio_chunk`, the way `_drain_and_transcribe` cuts them;
  - join the lines, and assert (a) that word trigrams repeated within 12 words occur no more often than in the script, and (b) that the script's key words still reach `KEYWORD_THRESHOLD`.

  Verify it fails against today's chunking, or, if today's code happens to pass on this recording, record that and confirm it fails with the overlap cut disabled once 2.2 is in.

  **Done 2026-09-15.** `check_live_chunks` runs as "live chunks do not repeat words". On today's code the recording's chunked transcript repeats "what you should do" and "will get it perfect", and the stamps run at 10 s and 20 s instead of 9 s and 18 s. The new call is also rejected outright (`lead`).

  After 2.2 it passes. With the word filter mutated to keep every word, it fails with "a phrase repeats: … I will get it perfect. will get it perfect …". The file was restored afterwards and the filter confirmed present.

## 2. Engine fix

- [x] 2.1 `transcription_engine.py`: `transcribe_chunk` passes `word_timestamps=True` and adds `words: [(start, end, text)]` to each segment. File transcription stays unchanged.

  Verify `tests/test_engine.py`'s file speech check still passes.

  **Done 2026-09-15.** `word_timestamps=True`, and each segment gains `words: [(start, end, word)]`. "speech sample transcribes" still passes.

- [x] 2.2 `transcriber.py`, per design.md Decisions 1–3:
  - `_process_audio_chunk(engine, audio, chunk_start, language, sample_rate, lead, trail, stream_start=None)` returns `(results, spoke)`. It cuts words by `lead`/`trail`, and stamps with `_wall_clock_stamp(stream_start + ...)` when `stream_start` is set, or the relative range otherwise.
  - `_wall_clock_stamp` takes an optional datetime.
  - `_drain_and_transcribe` and `transcribe_live_simple` record `stream_start` from their first block, advance `position` by the new audio of every chunk before the gate and the `try`, and use the returned stamp instead of reading the clock at emit.

  Verify 1.1, 1.2 and 1.4 pass, and `test_resample.py`, `test_dual_capture.py` and `test_transcript_line_format.py` still pass.

  **Done 2026-09-15.**
  - **`_process_audio_chunk`:** now takes `chunk_start`, `lead`, `trail` and `stream_start`, and returns `(results, spoke)` with the stamp already formatted.
  - **`_wall_clock_stamp(at=None)`**.
  - **Both live paths:** keep `position` (new audio consumed) and `carried` (overlap the next chunk starts with). A chunk starts at `position - carried`, with `lead = carried / 2` and `trail = kept / 2`. `position` advances before the gate and the `try`. `stream_start` is read from the first block or callback, minus that block's length. `timedelta` is imported at module level.
  - **Verified:** `test_chunk_words.py`, `test_dual_capture.py` (including the new time-axis section), `test_resample.py`, `test_transcript_line_format.py` and all three `tests/test_engine.py` checks pass.

## 3. GUI

- [x] 3.1 In `tests/test_gui.py`, add `time axis` with the fake bridge:
  - **Late line:** emit SYS `14:22:10`, then SYS `14:22:30`, then MIC `14:22:20`. The MIC line sits between the two SYS lines in `#transcript-live`, and the elapsed labels read `0:00`, `0:10` and `0:20` in DOM order.
  - **Earlier than the first line:** a MIC `14:22:05` after those lines becomes the first child. The labels become `0:00`, `0:05`, `0:15` and `0:25`.
  - **Filtered gap:** lines SYS `14:00:00`, MIC `14:00:50`, SYS `14:01:40` with Show = SYS. The visible second SYS line's gap note reads "1 min 40 s", not "50 s".
  - **Durations:** `formatDuration(59.6)`, `formatDuration(3599.6)` and `formatDuration(7199.5)` read "1 min", "1 h" and "2 h". `main.js` is a classic script, so the function is reachable from `page.evaluate`.

  Verify each part fails against today's `src/main.js`.

  **Done 2026-09-15.** `test_time_axis` is registered as "time axis", selects "Time into session", and runs its four parts on one chart. Each part was run on its own, with the other parts' assertions disabled, against the unchanged `src/main.js`, and each fails:
  - **Late line:** order is `one, three, two`.
  - **Earlier than the first line:** order is `one, three, two, zero`.
  - **Filtered gap:** the note reads "50 s".
  - **Durations:** `60 s`, `59 min 60 s`, `1 h 60 min`.

  Deviation: the filtered-gap lines are at 15:00:00, 15:00:50 and 15:01:40 on the same chart, after the earlier lines, instead of 14:00. The last SYS line's gap is still measured from the previous visible SYS line.

- [x] 3.2 In `src/main.js`, per design.md Decisions 4–5: `appendTranscriptLine` inserts by offset and re-bases `sessionOrigin`, `relayout` skips hidden lines, and `formatDuration` rounds first.

  Verify with `node --check`, then that `time axis` and all other GUI scenarios pass.

  **Done 2026-09-15.**
  - **`appendTranscriptLine`:** walks back from the last line past lines with a later offset, and inserts there. A line without an offset appends. A negative offset shifts every existing `data-offset` and becomes the origin.
  - **`relayout`:** gives hidden lines no margin and doesn't take `previous` from them.
  - **`formatDuration`:** rounds the total, and whole minutes for the hour form, before splitting.
  - **Verified:** `node --check` passes, and all 16 GUI scenarios pass, including "time axis".

- [x] 3.3 **Impeccable pass on the chart roll.** This is behaviour on an existing surface, with no new component. Using the `impeccable` skill on the `src-index-html` surface and following `DESIGN.md`, check a dual-source session with a late MIC line inserted mid-roll, and a Show = MIC filtered view with gap notes. Confirm the `mark-lands` arrival animation reads correctly on a line that lands above the bottom, and record any adjustment.

  Verify with light and dark screenshots at 900×640 and 640×480, with no overflow.

  **Done 2026-09-15.** Impeccable, Operate mode, a verify-only pass on the incumbent roll (context loaded with `context.mjs --target src/index.html`). The fixture has seven lines: SYS 14:02:10, 14:02:18, 14:02:31, then a late MIC 14:02:24, a 6-minute silence, SYS 14:08:40, a late SYS 14:08:47 and MIC 14:08:52. It was captured in light and dark, at 900×640 and 640×480, in three states: mid-landing (90 ms after the late MIC line), settled, and Show = MIC.
  - **Late line:** it lands between 14:02:18 and 14:02:31 with the same `mark-lands` slide and fade as a bottom arrival. A mark landing on the paper where it belongs reads right for a chart recorder, so there's no change to the motion.
  - **Spacing:** proportional around the inserted lines; the 6- and 7-second gaps read as tighter than the silence.
  - **Show = MIC:** the gap note above 14:08:52 reads "6 min 28 s", measured from the previous MIC line (14:02:24), not the hidden SYS line.
  - **Checks:** no horizontal overflow, script errors or CSP violations in any of the 12 captures.
  - **Adjustments:** none.

- [x] 3.4 Finish the Impeccable pass:
  - the `impeccable-finish-reviewer` agent reviews the roll behaviour from 3.3 (not an inline self-review), material fixes are applied and re-screenshotted once, and its verdict is recorded;
  - run `detect.mjs` once on the changed files, noting if it ran degraded;
  - update `DESIGN.md`'s roll description (line order by speech time, gaps between visible lines), and `.impeccable/design.json` only if a component changed.

  Verify `DESIGN.md` describes both.

  **Done 2026-09-15.**
  - **Reviewer:** the `impeccable-finish-reviewer` agent returned **Verdict: ship**, with no material fixes.
    - **Mid-roll insertion** matches "The Chart Recorder" and makes the calibrated-axis promise truer than arrival order did.
    - **A late line can't land off-screen:** chunk lag puts it at most about 10 s before the newest line, which is inside the viewport while the roll follows the bottom, so no cue is needed.
    - **The filtered gap note** ("6 min 28 s" under Show = MIC, "6 min 9 s" unfiltered) names the silence the reader can see.
    - **Unchanged:** type, material and ground.

    It kept the principle: always measure from what's visible, in true time order.
  - **Its two non-material notes:**
    - the insertion walk stops at a line without an offset (an unparseable stamp), which is harmless;
    - the 90 ms still can't prove `mark-lands` played, but the element and class are unchanged.

    No change was made, so there was no re-screenshot.
  - **Detector:** `detect.mjs` ran once on `src/main.js`, the only changed UI file, with 0 findings (`--json` gives `[]`) and no degraded notice. `src/index.html` and `src/style.css` are unchanged and keep their 16 older advisories.
  - **Docs:** `DESIGN.md`'s roll description now says lines sit in speech order, a late mark lands mid-roll, and the earliest line is the origin. The Gap note entry now says gaps are measured between visible lines and durations are rounded whole. The reviewer judged the old wording still accurate; this makes both points explicit. `.impeccable/design.json` is unchanged, since no component changed.

## 4. Docs, backlog and verification

- [x] 4.1 README: `--actual-time` on live capture stamps when the speech began, not when the line was printed. Update the `--actual-time` help text in `transcriber.py` to match.

  Verify `python transcriber.py --help` shows it.

  **Done 2026-09-15.** The README's `--actual-time` entry and the help text now say that live lines carry the time their speech began. `--help` shows it.

- [x] 4.2 Remove cluster C from `openspec/backlog.md`'s "Logic audit follow-ups", and update that item's intro. Verify C1–C4 no longer appear and cluster D is unchanged.

  **Done 2026-09-15.** Cluster C is removed, and the intro names `fix-true-scale-time-axis`. C1–C4 no longer appear, and D1–D7 are unchanged.

- [x] 4.3 Run `.venv/bin/python run_tests.py` with `TRANSCRIBER_TEST_SPEECH` set and a network that reaches GitHub, and verify it exits 0.

  **Done 2026-09-15.** With `TRANSCRIBER_TEST_SPEECH` set and GitHub reachable ("No releases published yet"): 14/14 suites passed, exit 0. There's one more suite than before (`test_chunk_words.py`), and it includes "live chunks do not repeat words" and the "time axis" GUI scenario. It ran after the code, README and help-text edits; only `DESIGN.md` and task notes changed afterwards.

- [ ] 4.4 **Manual check, by the user:** a short live session in the app with system audio and microphone, talking over a playing video, with nothing kept afterwards unless the user wants it. Verify that:
  - lines from one chunk are spaced apart on the chart;
  - SYS and MIC lines for the same moment sit together;
  - no words repeat at chunk boundaries;
  - the stamps match the clock when the words were said, within a couple of seconds.
