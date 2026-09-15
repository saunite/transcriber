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

## 5. Verification

- [ ] 5.1 Run `.venv/bin/python run_tests.py` with `TRANSCRIBER_TEST_SPEECH` set, and verify it exits 0.
- [ ] 5.2 **User check on Linux** (a local build or `tauri dev`), with a second model folder downloaded beforehand:
  - choosing it makes the engine log load from that folder, and the transcript header names it;
  - after restarting the app the choice is still in effect;
  - renaming the folder, then starting a session, shows the refusal note and starts no engine;
  - returning to the bundled model transcribes offline as before.
