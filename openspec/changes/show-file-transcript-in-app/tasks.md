## 1. Tests first

- [ ] 1.1 In `tests/test_engine.py`'s `check_speech`, assert that the engine's own output carries the transcript: every line matching `^\[[^\]]+ -> [^\]]+\] \S` that the run printed, in the same order and with the same text as the saved transcript file's lines. It already captures stdout and stderr and reads the file, so this is an assertion, not new plumbing.

  Verify it **fails** against today's engine, recording what it reported.

- [ ] 1.2 In `tests/test_gui.py`, add `file transcript` with the fake bridge: drop a file, wait for `start_file_transcription`, emit two `transcript-line` events with relative stamps (`00:01.000 -> 00:03.000`), and assert both land in `#transcript-file`, none in `#transcript-live`, and the File chart's empty state is hidden. Then emit `file-transcription-complete` and assert the lines stay.

  This is the routing the fix depends on; if it passes today, record that, since the missing piece is then only the engine's output.

- [ ] 1.3 In `tests/test_e2e_linux.py`, add a scenario that drops `$TRANSCRIBER_TEST_SPEECH` on the built app and asserts `#transcript-file` holds at least one line once the queue reports the file done. It prints `SKIP` when no recording is set, like the suite's other optional pieces.

  The existing file-drop scenarios use a silent WAV, which yields no segments, so they can't show this. Verify the new scenario fails against today's engine.

## 2. Fix

- [ ] 2.1 In `transcription_engine.py`'s `transcribe_file`, print each segment's `"{timestamp} {text}"` line as it is written, using the same `format_timestamp` call that builds the file line, so the printed and saved lines match. Keep tqdm's bar on stderr, and keep printing when no `--output` is given (the GUI always passes one; a CLI run without one still deserves its transcript).

  Verify 1.1, 1.2 and 1.3 pass, and that `tests/test_engine.py`'s undecodable-input check and `test_transcript_line_format.py` still pass.

- [ ] 2.2 Check the app end to end by hand once (`npm run tauri dev` or a rebuilt app): drop a recording on the File tab and watch the chart fill while it transcribes. Record what the chart showed, including whether the lines are spaced by the recording's own timeline.

## 3. Docs and verification

- [ ] 3.1 `docs/user-guide.md`: file transcription prints the transcript as it goes, in both the app and the CLI. Verify it's described.

- [ ] 3.2 Remove "The File view never shows a file run's transcript" from `openspec/backlog.md`'s parked changes. Verify it no longer appears.

- [ ] 3.3 Run `.venv/bin/python run_tests.py` with `TRANSCRIBER_TEST_SPEECH` set and a network that reaches GitHub, and verify it exits 0.
