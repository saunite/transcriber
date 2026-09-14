## 1. Setup and the single runner

- [ ] 1.1 Add `requirements-dev.txt` listing `playwright` (design.md Decision 7). Install it into the project venv, then run `python -m playwright install chromium`. Verify that `.venv/bin/python -c "from playwright.sync_api import sync_playwright as p; b = p().start().chromium.launch(); b.close()"` exits 0, proving headless Chromium actually launches on this machine rather than only importing.
- [ ] 1.2 Add `run_tests.py` at the repository root (design.md Decision 6). It runs `cargo test` in `src-tauri/`, then every root `test_*.py`, then every `tests/test_*.py`, each as a subprocess with `sys.executable`. It prints PASS/FAIL per suite and a summary, and exits 1 if any suite failed. Standard library only. Verify:
  - on today's tree, `.venv/bin/python run_tests.py` reports the 7 existing Python scripts and `cargo test` as passing and exits 0;
  - a temporary `tests/test_always_fails.py` makes it exit 1 while still running and reporting every other suite. Delete the temporary file afterwards.

## 2. GUI behaviour tests

- [ ] 2.1 Add `tests/fake_tauri.js`, the fake bridge from design.md Decision 3. Include:
  - recorded `invoke` calls, with per-command responses and rejections;
  - stored `listen` handlers fired through `__fake.emit`;
  - fixed `path` results, dialogs that resolve `null`, and a `Proxy` for `getCurrentWindow()`.
  Add `tests/test_gui.py` with a shared page setup that injects the bridge via `add_init_script`, loads `src/index.html` over `file://`, and fails on any `pageerror`. Verify with the first scenario: the page loads with no script error and records `get_platform` and `list_devices`.
- [ ] 2.2 Add the command drift check: every `invoke("…")` literal in `src/main.js` must appear in `generate_handler![…]` in `src-tauri/src/main.rs`, and a failure names the missing command (design.md Decision 3). Verify it passes on today's tree. Then temporarily rename one `invoke` literal in a scratch copy of `main.js` read by the check, and confirm it fails naming that command.
- [ ] 2.3 Add the live start/stop scenario. Start a session with default settings, then check that:
  - `start_live_session` was requested with `micDevice: null`;
  - both capture indicators read "Capturing";
  - after stopping, `stop_live_session` was requested and both indicators read "Idle";
  - no visible label says "Record".
  Verify it passes. Then temporarily make `renderPens()` always write the old "Armed" text, confirm the test fails, and restore it.
- [ ] 2.4 Add the file queue scenarios. Drop two supported paths via `tauri://drag-drop`, then check that:
  - exactly one `start_file_transcription` is requested and the second file shows as waiting;
  - emitting `file-transcription-complete` with `true` requests the second file;
  - emitting `false` for a file marks it failed and requests the next waiting file.
  Verify it passes. Then temporarily make the queue start every file at once, confirm the test fails, and restore it.
- [ ] 2.5 Add the unsupported-file scenario. Dropping a file with an unsupported extension must request no `start_file_transcription` and must show an error note. Verify it passes, and that it fails if the test's expectation is flipped to require a call. That proves it discriminates rather than passing vacuously.
- [ ] 2.6 Add the refusal scenario. Configure the fake to reject `start_file_transcription` with "A live session is still running. Stop it before transcribing a file.", drop a supported file, and check that the note shows that reason. Verify it passes, and fails when the fake resolves instead of rejecting.

## 3. Engine tests

- [ ] 3.1 **User action:** record the speech sample from design.md Decision 5's script, about 10–15 seconds in English at a normal pace somewhere quiet, and save it as `tests/fixtures/speech-en.<ext>` in any format. Add `tests/fixtures/speech-en.txt` containing the exact script. Verify both files exist and that `.venv/bin/python transcriber.py --file tests/fixtures/speech-en.* --model-path src-tauri/resources/model --output /tmp/check.txt` produces a non-empty transcript.
- [ ] 3.2 Add the speech check to `tests/test_engine.py` (design.md Decision 4), with `--engine <path>` (default `[sys.executable, "transcriber.py"]`) and `--model-path <dir>` (default `src-tauri/resources/model`). It fails unless:
  - the exit status is 0 and there is no `Traceback`;
  - the transcript's non-comment lines match `^\[[^\]]+ -> [^\]]+\] \S`;
  - stdout contains `Detected language: en`;
  - at least 70% of the script's distinct words of five or more letters appear, compared case- and punctuation-insensitively.
  A missing `model.bin` stops the test with a message naming `fetch_sidecar_resources.py`. Verify:
  - it passes against the source engine;
  - it passes with `--engine dist/linux/transcriber-sidecar` (frozen binary);
  - it fails on the keyword threshold when pointed at a script file of unrelated words;
  - `--model-path` pointed at an empty temporary directory gives the missing-model message. Never move the real model to test this.
- [ ] 3.3 Add the undecodable-input check to `tests/test_engine.py`. Random bytes in a temporary `garbage.mp3` must give a non-zero exit, `No decodable audio` or `Could not decode` in the output, no `Traceback`, and no transcript file. Verify it passes, and that it fails when pointed at the valid speech sample instead, proving the check discriminates.

## 4. Documentation and a full run

- [ ] 4.1 Add a "Running the tests" section to README covering:
  - installing `requirements-dev.txt` and `python -m playwright install chromium`;
  - running `.venv/bin/python run_tests.py`;
  - what each suite covers;
  - the speech fixture and its script;
  - `--engine` for testing a frozen binary.
  Verify the section names `requirements-dev.txt`, `playwright install chromium`, `run_tests.py` and `--engine`, as the `documentation` spec requires for requirements files and commands.
- [ ] 4.2 Record the gap found during planning in `openspec/backlog.md`: `desktop-gui` "Drop a video file" promises "the resulting transcript" in the GUI, but file mode prints no transcript lines, so the File view stays empty. Verify the entry exists and states that the GUI tests deliberately do not assert on it.
- [ ] 4.3 Run the whole suite: `.venv/bin/python run_tests.py` exits 0 with `cargo test`, the 7 existing Python scripts, `tests/test_gui.py` and `tests/test_engine.py` all passing. Record the total run time and each suite's duration, so a slow suite is visible from the start.
