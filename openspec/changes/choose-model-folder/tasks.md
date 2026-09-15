## 1. CLI

- [ ] 1.1 In `transcriber.py`, set `--model` to `default=None`, keeping its choices. Add a pure `_model_label(model, model_path)` helper (design.md Decision 4). After parsing, and before `_bundled_model_path`, set `args.model_label` and then default `args.model` to `'base'`. Print `args.model_label` at the four output sites: both transcript headers, the compact summary line and `_print_header`. Add assertions to `test_bundled_model_default.py`:
  - `(None, None)` → `base`;
  - `(None, "/m/faster-whisper-small/")` → `faster-whisper-small`;
  - `("small", "/m/x")` → `small`;
  - the frozen bundled case still resolves `base`.

  Verify the test passes, and that `grep -n "args.model}" transcriber.py` finds no remaining output site.

## 2. Shell

- [ ] 2.1 In `src-tauri/src/sidecar.rs`, add a pure `select_model_dir(chosen, bundled)` (Decision 1). Change both start commands to take `model_dir: Option<String>` instead of `model`, and to call it before spawning. Pass `--model base` only with the bundled directory (Decision 2), and give the file command's arguments a testable builder. Unit tests:
  - `None` or empty → bundled;
  - a temp directory with `model.bin` → that directory;
  - a missing directory, or one without `model.bin` → `Err` naming the path;
  - live and file args carry `--model base` only for the bundled directory, and `--model-path` always.

  Verify `cargo test` passes.

## 3. Frontend

- [ ] 3.1 **Design the Model field with the `impeccable` skill** (Decision 5) on the `src-index-html` surface, following `DESIGN.md`. Settle:
  - placement in the title block;
  - how the bundled model and a chosen folder are shown, with long-path truncation;
  - **Browse…** and the keyboard-reachable return to the bundled model;
  - the copy.

  Record the decisions under this task. Verify with light and dark screenshots at 900×640 and 640×480, in both the bundled and chosen-folder states, with no overflow.
- [ ] 3.2 Implement the design in `src/index.html`, `src/style.css` and `src/main.js`:
  - remove the size dropdown;
  - pick a folder with `openFileDialog({ directory: true })`, where a cancel changes nothing;
  - store the choice under `localStorage` `transcriber-model-dir` with the theme's try/catch pattern;
  - send `modelDir` (null for bundled) to both commands.

  Verify `node --check src/main.js`, and that the existing GUI tests pass, including command drift and CSP.
- [ ] 3.3 Add GUI scenarios to `tests/test_gui.py`:
  - **default:** the field shows the bundled model, and `start_live_session` gets `modelDir: null`;
  - **pick:** the fake `dialog.open` returns `/models/small`, the field shows it, and a live start and a file drop both send `modelDir: "/models/small"`;
  - **remember:** after a reload the choice is still shown and sent;
  - **reset:** returning to the bundled model sends `null`;
  - **cancel:** a dialog returning `null` leaves the choice unchanged;
  - **refusal:** a `start_live_session` rejection with the folder message is shown as a note.

  Verify they pass. Also verify the remember scenario fails if the `localStorage` write is removed.
- [ ] 3.4 Finish the Impeccable pass: have the `impeccable-finish-reviewer` agent review the built field (not an inline self-review), apply any material fixes it lists and re-screenshot once, record the verdict, and update `DESIGN.md` (and `.impeccable/design.json` if a component changed) for the new Model field. Run `detect.mjs` once on the changed files. Verify `DESIGN.md` describes the field, and that the verdict is recorded here.

## 4. Docs

- [ ] 4.1 README:
  - GUI section: how to choose a model folder, and how to return to the bundled one;
  - CLI `--model-path` entry: what a model folder is (a faster-whisper/CTranslate2 model repository, such as `Systran/faster-whisper-small`, downloaded by the user), and that output names it by folder;
  - the English-only (`*.en`) language caveat.

  Also fix the stale sentence saying the GUI always passes the bundled `--model-path`. Verify these lines exist and none still says the GUI only uses the bundled model.

## 5. End-to-end scenarios (design.md Decision 6)

- [ ] 5.1 In `tests/test_e2e_linux.py`, give each scenario's app its own data directory (`XDG_DATA_HOME` under the scenario's temp directory), so no scenario reads or writes the real `~/.local/share/com.transcriber.app`. Verify the existing six scenarios still pass, and that the real directory's modification time is unchanged by a run.
- [ ] 5.2 Add `model folder remembered`. Set the stored choice through the page's storage key to a temp folder holding a `model.bin`, then close the app. A second app, started with the same data directory, must show that folder in the Model field. Verify it passes, and fails if the page stops reading the stored value on load (temporarily), then revert.
- [ ] 5.3 Add `model folder refused`. Store a temp folder without `model.bin`, click **Start transcribing** from script, and assert:
  - the note names the folder and says it has no usable model;
  - no `transcriber-sidecar` process was started (`pgrep -f` on the sidecar path, before and after).

  Verify it passes, and fails with `select_model_dir`'s `model.bin` check temporarily removed, then revert.
- [ ] 5.4 Add `model folder used`:
  - make a temp folder `faster-whisper-e2e` whose files are symlinks to the bundled model's, store it, and start a file run on a 1-second silent WAV written with the stdlib `wave` module;
  - assert the engine log (`#debug-log`) shows the model loading from that folder;
  - return to the bundled model and repeat, asserting the log shows the bundled folder.

  Before writing the scenario, check whether a `tauri://drag-drop` event emitted from script reaches the page's listener. If it doesn't, start the run by calling `start_file_transcription` with the page's own `modelDir` value through execute-script. Record which was used. Verify it passes.

## 6. Verification

- [ ] 6.1 Run `.venv/bin/python run_tests.py` with `TRANSCRIBER_TEST_SPEECH` set, and a network that reaches GitHub. Verify it exits 0, and that every end-to-end scenario prints `PASS`.
- [ ] 6.2 **User check on Linux** (a local build or `tauri dev`), with a second real model folder downloaded beforehand (e.g. `Systran/faster-whisper-small`). This covers what the end-to-end suite can't drive: the native folder dialog, and a real different model.
  - **Browse…** opens the system folder picker, and choosing the folder shows it in the Model field;
  - a transcription uses it: the engine log loads from that folder, and the CLI transcript header names it by folder;
  - cancelling the picker changes nothing.
