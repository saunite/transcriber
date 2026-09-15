## 1. Engine tests first

- [ ] 1.1 In `test_dual_capture.py`, add scenarios driving `_run_dual_capture` with the fake engine and `_feed`. Use a fixed `datetime.now` / `time` where needed, and `chunk_duration=2`, so chunk boundaries are deterministic:
  - **Position:** relative stamps (`actual_time=False`) for three consecutive SYS chunks with a segment at `start=0.6` in each are `00:00.60`, `00:01.60` and `00:02.60`. Today they are `00:00.60`, `00:02.60` and `00:04.60`, because the offset counts the overlap.
  - **Skipped chunk:** a silent MIC chunk followed by an audible one stamps the audible chunk's segment after the silent chunk's time, not at the silent chunk's start.
  - **Speech time:** with `actual_time=True` and the clock frozen for the whole run, a segment at `start=1.2` in the second SYS chunk is stamped `stream_start + 1 s + 1.2 s`. Two segments of one chunk (`start=0.1` and `start=1.4`) get different stamps.

  Verify each scenario **fails** against today's `transcriber.py`, recording which assertions fail.

- [ ] 1.2 Add a word-cut check with a fake engine that returns segments carrying `words`, calling `_process_audio_chunk` directly (in `test_resample.py` beside its existing `_process_audio_chunk` check, or a new root `test_chunk_words.py` if that reads better). For a 10 s chunk with 1 s overlap on both sides:
  - words starting at 0.3 s and 9.7 s are dropped;
  - words at 0.5 s and 9.4 s are kept;
  - a segment left with no words is dropped;
  - the rebuilt segment's text and start/end come from the kept words;
  - the first chunk (`chunk_start == 0`) keeps a word at 0.1 s;
  - a segment without `words` is kept or dropped by its own start.

  Verify it fails against today's code.

- [ ] 1.3 Measure word-timestamp cost. Run `TranscriptionEngine.transcribe_chunk` on 10 s chunks of `$TRANSCRIBER_TEST_SPEECH` with the bundled model, on CPU, with and without `word_timestamps=True`, and record the mean time per chunk for both under this task.

  Verify the slowdown is at most 25 %. If it's more, pause apply and report the numbers (design.md, Risks).

- [ ] 1.4 In `tests/test_engine.py`, add a real-speech check, "live chunks do not repeat words". It runs only when a speech recording is set and no `--engine` binary is given, since it runs in-process:
  - decode the recording to 16 kHz;
  - feed 10 s chunks with the 1 s overlap through `_process_audio_chunk`, the way `_drain_and_transcribe` cuts them;
  - join the lines, and assert (a) that word trigrams repeated within 12 words occur no more often than in the script, and (b) that the script's key words still reach `KEYWORD_THRESHOLD`.

  Verify it fails against today's chunking, or, if today's code happens to pass on this recording, record that and confirm it fails with the overlap cut disabled once 2.2 is in.

## 2. Engine fix

- [ ] 2.1 `transcription_engine.py`: `transcribe_chunk` passes `word_timestamps=True` and adds `words: [(start, end, text)]` to each segment. File transcription stays unchanged.

  Verify `tests/test_engine.py`'s file speech check still passes.

- [ ] 2.2 `transcriber.py`, per design.md Decisions 1–3:
  - `_process_audio_chunk(engine, audio, chunk_start, language, sample_rate, lead, trail, stream_start=None)` returns `(results, spoke)`. It cuts words by `lead`/`trail`, and stamps with `_wall_clock_stamp(stream_start + ...)` when `stream_start` is set, or the relative range otherwise.
  - `_wall_clock_stamp` takes an optional datetime.
  - `_drain_and_transcribe` and `transcribe_live_simple` record `stream_start` from their first block, advance `position` by the new audio of every chunk before the gate and the `try`, and use the returned stamp instead of reading the clock at emit.

  Verify 1.1, 1.2 and 1.4 pass, and `test_resample.py`, `test_dual_capture.py` and `test_transcript_line_format.py` still pass.

## 3. GUI

- [ ] 3.1 In `tests/test_gui.py`, add `time axis` with the fake bridge:
  - **Late line:** emit SYS `14:22:10`, then SYS `14:22:30`, then MIC `14:22:20`. The MIC line sits between the two SYS lines in `#transcript-live`, and the elapsed labels read `0:00`, `0:10` and `0:20` in DOM order.
  - **Earlier than the first line:** a MIC `14:22:05` after those lines becomes the first child. The labels become `0:00`, `0:05`, `0:15` and `0:25`.
  - **Filtered gap:** lines SYS `14:00:00`, MIC `14:00:50`, SYS `14:01:40` with Show = SYS. The visible second SYS line's gap note reads "1 min 40 s", not "50 s".
  - **Durations:** `formatDuration(59.6)`, `formatDuration(3599.6)` and `formatDuration(7199.5)` read "1 min", "1 h" and "2 h". `main.js` is a classic script, so the function is reachable from `page.evaluate`.

  Verify each part fails against today's `src/main.js`.

- [ ] 3.2 In `src/main.js`, per design.md Decisions 4–5: `appendTranscriptLine` inserts by offset and re-bases `sessionOrigin`, `relayout` skips hidden lines, and `formatDuration` rounds first.

  Verify with `node --check`, then that `time axis` and all other GUI scenarios pass.

- [ ] 3.3 **Impeccable pass on the chart roll.** This is behaviour on an existing surface, with no new component. Using the `impeccable` skill on the `src-index-html` surface and following `DESIGN.md`, check a dual-source session with a late MIC line inserted mid-roll, and a Show = MIC filtered view with gap notes. Confirm the `mark-lands` arrival animation reads correctly on a line that lands above the bottom, and record any adjustment.

  Verify with light and dark screenshots at 900×640 and 640×480, with no overflow.

- [ ] 3.4 Finish the Impeccable pass:
  - the `impeccable-finish-reviewer` agent reviews the roll behaviour from 3.3 (not an inline self-review), material fixes are applied and re-screenshotted once, and its verdict is recorded;
  - run `detect.mjs` once on the changed files, noting if it ran degraded;
  - update `DESIGN.md`'s roll description (line order by speech time, gaps between visible lines), and `.impeccable/design.json` only if a component changed.

  Verify `DESIGN.md` describes both.

## 4. Docs, backlog and verification

- [ ] 4.1 README: `--actual-time` on live capture stamps when the speech began, not when the line was printed. Update the `--actual-time` help text in `transcriber.py` to match.

  Verify `python transcriber.py --help` shows it.

- [ ] 4.2 Remove cluster C from `openspec/backlog.md`'s "Logic audit follow-ups", and update that item's intro. Verify C1–C4 no longer appear and cluster D is unchanged.

- [ ] 4.3 Run `.venv/bin/python run_tests.py` with `TRANSCRIBER_TEST_SPEECH` set and a network that reaches GitHub, and verify it exits 0.

- [ ] 4.4 **Manual check, by the user:** a short live session in the app with system audio and microphone, talking over a playing video, with nothing kept afterwards unless the user wants it. Verify that:
  - lines from one chunk are spaced apart on the chart;
  - SYS and MIC lines for the same moment sit together;
  - no words repeat at chunk boundaries;
  - the stamps match the clock when the words were said, within a couple of seconds.
