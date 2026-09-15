## 1. Tests first

- [x] 1.1 In `test_dual_capture.py`, add a no-mic scenario that calls `transcriber.transcribe_live_simple` with `include_mic=False`, `audio_device=3`, `silence_timeout=0.5`, on Linux or with `platform.system` faked. Use a fake `sounddevice` whose `InputStream` feeds 16 kHz blocks to its callback from its own thread and records that thread, and a fake engine that records the thread each `transcribe_chunk` runs on and returns a line only for the first chunk. Assert:
  - the run returns 0 within 5 s, with "minutes of silence detected" in the output;
  - no `transcribe_chunk` call ran on the stream's callback thread;
  - the transcript lines are `[SYS]`-tagged.

  Verify it **fails** against today's code, recording how: expected a hang caught by the time limit, a transcription on the callback thread, and untagged lines.

  **Done 2026-09-15.** `_check_no_mic_device` is called from `main()`. The fake `sounddevice` is also installed as `audio_capture.sd`, which the old loop's `AudioCapture` uses. Its stream thread swallows callback exceptions, as PortAudio does. The session runs on a worker thread with a 5 s join. Against today's engine all three fail:
  - **Hang:** "the silence timeout never stopped the session". The worker was still alive, printing "⏱️ Stopping: 0.0 minutes of silence detected" on every callback, because the `KeyboardInterrupt` is raised on the callback thread.
  - **Callback thread:** all 5 `transcribe_chunk` calls ran on the stream's callback thread.
  - **Tag:** lines were untagged (`[00.00 -> 01.00] hello`).

  The second and third were read from a scratch copy with the hang assertion disabled.

- [x] 1.2 Add a root `test_launchers.py` that runs `linux-start-transcription.sh` and `mac-start-transcription.sh` from a temporary copy of the checkout layout. The copy has the script, a stub `transcriber.py`, and a stub `.venv/bin/python` that writes its argv to a file. It runs from a different current folder, with `--model-path /models/small`. Assert:
  - the stub received the absolute path of the copied `transcriber.py`;
  - `--model` is absent, and `--model-path /models/small` and `--actual-time` are present;
  - the output file argument is relative (so it lands in the current folder).

  Verify it fails against today's scripts.

  **Done 2026-09-15.** `test_launchers.py` copies each script into `<tmp>/checkout` beside an empty `transcriber.py` and a stub `.venv/bin/python` that writes its argv to a file, then runs it with bash from `<tmp>/elsewhere`. Against today's scripts both fail: `linux-start-transcription.sh ran 'transcriber.py', not the checkout's transcriber.py`, and the same for `mac-start-transcription.sh`. Their argv also carries `--model base`, which the next assertion rejects.

- [x] 1.3 In `tests/test_gui.py`, add `dotted output folder`: type `/home/a.b/transcript` into the output field, start a live session, and assert the `start_live_session` call's `outputPath` matches `^/home/a\.b/transcript_\d{8}_\d{6}$`. Also check `/home/a.b/notes.txt` gives `/home/a.b/notes_<stamp>.txt`.

  Verify it fails against today's `src/main.js`.

  **Done 2026-09-15.** It's registered as "dotted output folder". The start call's `outputPath` is checked, and `withFreshTimestamp` is called directly for `/home/a.b/notes.txt` and a Windows path `C:\Users\a.b\notes`. Against today's code it fails with `/home/a_20260915_142703.b/transcript`.

## 2. Fixes

- [x] 2.1 `transcriber.py`, per design.md Decisions 1–2: merge `_transcribe_live_linux_dual` into `transcribe_live_simple` with an optional mic, and delete the old single-source loop and `_transcribe_live_linux_dual`. Point `tests/test_gui.py`'s `LIVE_FUNCTIONS` at the function that prints "Listening...", and update `test_transcript_line_format.py`'s comment naming `transcribe_live_simple`.

  Verify 1.1 passes, and `test_dual_capture.py`, `test_transcript_line_format.py`, `test_mic_fallback.py`, `test_live_default_output.py` and the GUI "listening wording" check all pass.

  **Done 2026-09-15.**
  - **Deleted:** the old single-source loop, and `_setup_output_files`, which only that loop used.
  - **Renamed:** `_transcribe_live_linux_dual` is now `transcribe_live_simple`. It resolves the mic only with `--include-mic`, with title "System Audio" and mode summary `System audio (<name>)` when there's no mic, and the verbose header says "System audio" (+ " + microphone").
  - **Listening check:** `LIVE_FUNCTIONS` is now `("_run_dual_capture",)`, where every live path prints "Listening...".
  - **Comment:** `test_transcript_line_format.py`'s comment now names `_process_audio_chunk`/`_run_dual_capture`.
  - **Verified:** all listed checks pass, including the no-mic scenario.

- [x] 2.2 Bash launchers, per Decision 3: script-relative `transcriber.py`, and no `--model base`. Verify 1.2 passes.

  **Done 2026-09-15.** Both scripts run `"${SCRIPT_DIR}/transcriber.py"` for the venv and `python3` branches, and drop `--model base`, with a comment saying why. `bash -n` passes, `test_launchers.py` passes, and nothing else in the repo expects `--model base` from a launcher.

- [x] 2.3 `src/main.js` `withFreshTimestamp`, per Decision 4. Verify with `node --check`, then that 1.3 and all GUI scenarios pass.

  **Done 2026-09-15.** The extension is split only when the last `.` comes after the start of the file name (after the last `/` or `\`) and isn't its first character. `node --check` passes, and all 17 GUI scenarios pass, including "dotted output folder".

## 3. Docs, backlog and verification

- [x] 3.1 README:
  - system-audio-only live output is `[SYS]`-tagged, with the same compact status lines;
  - the Linux and macOS launchers work from any folder and take `--model` or `--model-path`.

  Verify both are described.

  **Done 2026-09-15.** README "Real-time Audio Capture" gains two notes:
  - the Linux and macOS launchers run from any folder, choose no model, and pass `--model`/`--model-path` through;
  - under "Understanding the Labels", every live session labels its lines, including system-audio-only sessions, which print `[SYS]` and the compact status lines.

- [x] 3.2 `openspec/backlog.md`, "Logic audit follow-ups":
  - remove D1, D5 and D7;
  - reword D4 to its Windows half (`win-start-transcription.bat` and `transcribe_file.bat` run `transcriber.py` by relative path, and the `.bat` passes `--model base`), noting that `03-fix-audit-edges-windows` covers it;
  - leave D2, D3 and D6 unchanged.

  Verify by reading the section.

  **Done 2026-09-15.** D1, D5 and D7 are removed. D4 now reads "D4 (Windows half)" and points at `03-fix-audit-edges-windows`. The intro records what `01-fix-audit-edges` did. D2, D3 and D6 are unchanged.

- [x] 3.3 Run `.venv/bin/python run_tests.py` with `TRANSCRIBER_TEST_SPEECH` set and a network that reaches GitHub, and verify it exits 0.

  **Done 2026-09-15.** With `TRANSCRIBER_TEST_SPEECH` set and GitHub reachable: 15/15 suites passed, exit 0. That's one more suite than before (`test_launchers.py`), and it includes the no-mic scenario, "dotted output folder", and the e2e Linux suite. It ran after the README and backlog edits.

- [ ] 3.4 **Manual check, by the user, on a rebuilt sidecar:** first rebuild and stage the sidecar (`build_sidecar.py`, copied to `src-tauri/binaries/`), then build the app. In the app, untick the microphone and start a short live session over a playing video, keeping nothing afterwards. Verify:
  - lines appear on the chart;
  - they stay visible under Show = SYS;
  - with Stop after silence set to 1 minute, the session stops by itself after a minute of silence.
