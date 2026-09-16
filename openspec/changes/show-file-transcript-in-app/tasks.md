## 1. Tests first

- [x] 1.1 In `tests/test_engine.py`'s `check_speech`, assert that the engine's own output carries the transcript: every line matching `^\[[^\]]+ -> [^\]]+\] \S` that the run printed, in the same order and with the same text as the saved transcript file's lines. It already captures stdout and stderr and reads the file, so this is an assertion, not new plumbing.

  Verify it **fails** against today's engine, recording what it reported.

  **Done 2026-09-16.** The check compares the timestamped lines the run printed with the lines in the saved file, in order. Against today's engine: "the engine printed 0 transcript lines but saved 7".

- [x] 1.2 In `tests/test_gui.py`, add `file transcript` with the fake bridge: drop a file, wait for `start_file_transcription`, emit two `transcript-line` events with relative stamps (`00:01.000 -> 00:03.000`), and assert both land in `#transcript-file`, none in `#transcript-live`, and the File chart's empty state is hidden. Then emit `file-transcription-complete` and assert the lines stay.

  This is the routing the fix depends on; if it passes today, record that, since the missing piece is then only the engine's output.

  **Done 2026-09-16.** Registered as "file transcript". It **passes against today's `src/main.js`**, as the task anticipated: the page already routes a file run's lines to `#transcript-file`, hides the empty state and keeps the lines after `file-transcription-complete`. The missing piece is only the engine's output, so this scenario is a guard against the routing regressing, not a failing test.

- [x] 1.3 In `tests/test_e2e_linux.py`, add a scenario that drops `$TRANSCRIBER_TEST_SPEECH` on the built app and asserts `#transcript-file` holds at least one line once the queue reports the file done. It prints `SKIP` when no recording is set, like the suite's other optional pieces.

  The existing file-drop scenarios use a silent WAV, which yields no segments, so they can't show this. Verify the new scenario fails against today's engine.

  **Done 2026-09-16.** "file transcript shown" drops `$TRANSCRIBER_TEST_SPEECH` on the built app, waits for the queue to stop saying "transcribing", and counts `#transcript-file .trace-text`. It raises `Skip` with what to set when no recording is configured, and it got its own temporary directory (the runner now makes 8).

  Against today's engine it fails: "the File view shows no transcript line after transcribing a recording". The same run also failed "engine offline", which runs `tests/test_engine.py` against the frozen sidecar and hits the 1.1 assertion.

## 2. Fix

- [x] 2.1 In `transcription_engine.py`'s `transcribe_file`, print each segment's `"{timestamp} {text}"` line as it is written, using the same `format_timestamp` call that builds the file line, so the printed and saved lines match. Keep tqdm's bar on stderr, and keep printing when no `--output` is given (the GUI always passes one; a CLI run without one still deserves its transcript).

  Verify 1.1, 1.2 and 1.3 pass, and that `tests/test_engine.py`'s undecodable-input check and `test_transcript_line_format.py` still pass.

  **Done 2026-09-16.** The timestamp is now built for every segment, not only when an output file is open, and the same string is printed and written, so the two can't drift. `print(..., flush=True)` keeps the app's view current on a piped stdout.

  **Verified:** all three `tests/test_engine.py` checks pass, `test_transcript_line_format.py` passes, and after restaging the frozen sidecar (the e2e suite runs the binary, not the source) all 11 e2e scenarios pass, with "file transcript shown: 7 transcript lines shown".

- [x] 2.2 Check the app end to end by hand once (`npm run tauri dev` or a rebuilt app): drop a recording on the File tab and watch the chart fill while it transcribes. Record what the chart showed, including whether the lines are spaced by the recording's own timeline.

  **Done 2026-09-16**, driven through the e2e harness (the real built app and its real engine) rather than by hand, with two screenshots taken from the running window.
  - **Mid-run:** the rail reads "Transcribing test-audio.ogg (1 of 1)" while the File chart already holds all seven lines, each with its time in the gutter (0:00, 0:05, 0:08, 0:14, 0:17, 0:22, 0:26). Those are the recording's own timeline, not the wall clock.
  - **Spacing:** the offsets are the segment starts, so the axis is fed correctly, but at the default chart speed all margins are 0 except one (0.8 px at 0:14): a 5-second gap at that scale is smaller than a row's height, so consecutive lines simply stack. Turning the chart speed up spaces them apart. That's the existing axis behaviour, unchanged by this change.
  - **After completion:** the lines stay, and the queue reports the file done.

## 3. Docs and verification

- [x] 3.1 `docs/user-guide.md`: file transcription prints the transcript as it goes, in both the app and the CLI. Verify it's described.

  **Done 2026-09-16.** "Transcribe a Video File" now opens with a note that each segment is printed as it is transcribed, saved to the same file, and fills the File view in the app.

- [x] 3.2 Remove "The File view never shows a file run's transcript" from `openspec/backlog.md`'s parked changes. Verify it no longer appears.

  **Done 2026-09-16.** Removed from "Parked changes"; the phrase appears nowhere in the file. The other parked items are unchanged.

- [x] 3.3 Run `.venv/bin/python run_tests.py` with `TRANSCRIBER_TEST_SPEECH` set and a network that reaches GitHub, and verify it exits 0.

  **Done 2026-09-16.** With `TRANSCRIBER_TEST_SPEECH` set and GitHub reachable: 16/16 suites passed, exit 0, nothing skipped. The GUI suite includes "file transcript" and the e2e suite "file transcript shown".
