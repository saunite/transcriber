## 1. CLI

- [x] 1.1 In `transcriber.py`, set `--model` to `default=None`, keeping its choices. Add a pure `_model_label(model, model_path)` helper (design.md Decision 4). After parsing, and before `_bundled_model_path`, set `args.model_label` and then default `args.model` to `'base'`. Print `args.model_label` at the four output sites: both transcript headers, the compact summary line and `_print_header`. Add assertions to `test_bundled_model_default.py`:
  - `(None, None)` → `base`;
  - `(None, "/m/faster-whisper-small/")` → `faster-whisper-small`;
  - `("small", "/m/x")` → `small`;
  - the frozen bundled case still resolves `base`.

  Verify the test passes, and that `grep -n "args.model}" transcriber.py` finds no remaining output site.

  **Done 2026-09-15.** `_model_label(model, model_path)` is added. `--model` now defaults to `None`, with the same choices. After parsing, `args.model_label` is set and `args.model` defaults to `base`, all before `_bundled_model_path`. The two transcript headers, the summary line and the four `_print_header` calls print `args.model_label`.

  **Added beyond the task text:** the engine's load message ("Loading {model_size} model from {path}") would have named `base` for a chosen folder, so `TranscriptionEngine` now gets `model_size=args.model_label`. That's safe: the engine uses `model_size` to pick a model only when no `model_path` is given, and then the label equals `--model`.

  Verification:
  - the test gains `test_model_label_never_names_an_unloaded_size` (the three cases), the frozen bundled case still passes, and the whole file passes;
  - `grep -n "args.model}" transcriber.py` finds nothing;
  - a smoke run with `--model-path <scratch>/faster-whisper-e2e/` (symlinks to the bundled model) printed "Loading faster-whisper-e2e model from …"

## 2. Shell

- [x] 2.1 In `src-tauri/src/sidecar.rs`, add a pure `select_model_dir(chosen, bundled)` (Decision 1). Change both start commands to take `model_dir: Option<String>` instead of `model`, and to call it before spawning. Pass `--model base` only with the bundled directory (Decision 2), and give the file command's arguments a testable builder. Unit tests:
  - `None` or empty → bundled;
  - a temp directory with `model.bin` → that directory;
  - a missing directory, or one without `model.bin` → `Err` naming the path;
  - live and file args carry `--model base` only for the bundled directory, and `--model-path` always.

  Verify `cargo test` passes.

  **Done 2026-09-15.** `src-tauri/src/sidecar.rs` gains three helpers:
  - `select_model_dir(chosen, bundled) -> Result<(String, bool), String>`, which returns the folder and whether it's the bundled one (the flag drives Decision 2). An absent or empty choice gives the bundled folder. A chosen folder must contain `model.bin`; otherwise the result is "The model folder <path> has no model.bin. Choose a faster-whisper model folder, or switch back to the bundled model.";
  - `model_args(model_dir, bundled)`, which adds `--model base` only for the bundled folder and always adds `--model-path`;
  - `build_file_args(...)`, the testable file builder.

  `build_live_session_args` takes `(model_dir, bundled, …)`. Both commands take `model_dir: Option<String>` and call `select_model_dir` before any spawn; the file command calls it before its one-engine guard. New tests:
  - `no_chosen_folder_selects_the_bundled_model` (`None` and empty);
  - `chosen_folder_with_a_model_is_selected`;
  - `chosen_folder_without_a_model_is_refused_naming_it` (an empty directory and a missing one);
  - `model_size_is_passed_only_for_the_bundled_model` (live and file).

  The seven existing builder tests are updated to the new signature. `cargo test`: 24 passed, 1 ignored (the live GitHub test).

## 3. Frontend

- [x] 3.1 **Design the Model field with the `impeccable` skill** (Decision 5) on the `src-index-html` surface, following `DESIGN.md`. Settle:
  - placement in the title block;
  - how the bundled model and a chosen folder are shown, with long-path truncation;
  - **Browse…** and the keyboard-reachable return to the bundled model;
  - the copy.

  Record the decisions under this task. Verify with light and dark screenshots at 900×640 and 640×480, in both the bundled and chosen-folder states, with no overflow.

  **Done 2026-09-15.** The user chose the layout (Impeccable's one direction question).
  - **Placement unchanged:** the Model field stays a native dropdown in the title block, same position and pattern as Language. The design suggested the Save to pattern (path box plus **Browse…**) "where it fits". It doesn't fit: path box, **Browse…** and a reset button in the already full title-block row would wrap Model onto a second line at 640 px.
  - **Options:**
    - "Bundled (base)" (the default; tooltip "The base model shipped with the app");
    - the chosen folder, shown by name, with the full path in the tooltip, only once one is chosen;
    - "Choose folder…", which opens the system folder picker (title "Choose a faster-whisper model folder").
  - **Reset and cancel:** returning to the bundled model is choosing it in the list, and cancelling the picker restores the previous selection. Keyboard access is the native select's.
  - **Copy:** "Bundled (base)", "Choose folder…".
  - **No new colours or components.** The only CSS is `#model-select { max-width: 12rem; text-overflow: ellipsis }`.

  **Verified** with Playwright under the app CSP, in light and dark, at 900×640 and 640×480, in the bundled state and with a long chosen folder (`faster-whisper-large-v3-turbo-ct2-int8`): no title-block or page overflow, and no CSP violations or script errors. The first round showed a long name widening the select to 266 px and squeezing Save to at 640 px. The width cap fixed that: 192 px with an ellipsis, and Save to readable. One re-capture confirmed it.

- [x] 3.2 Implement the design in `src/index.html`, `src/style.css` and `src/main.js`:
  - remove the size dropdown;
  - pick a folder with `openFileDialog({ directory: true })`, where a cancel changes nothing;
  - store the choice under `localStorage` `transcriber-model-dir` with the theme's try/catch pattern;
  - send `modelDir` (null for bundled) to both commands.

  Verify `node --check src/main.js`, and that the existing GUI tests pass, including command drift and CSP.

  **Done 2026-09-15.** `index.html` has an empty `#model-select`, with its options built by `renderModelSelect()`. `main.js` gains:
  - `MODEL_DIR_KEY = "transcriber-model-dir"` with the theme's try/catch;
  - `chosenModelDir()` (stored path or null);
  - `setModelDir()`;
  - a `change` handler, where "Choose folder…" opens `openFileDialog({ directory: true, … })` and a non-string result re-renders, so the previous choice stays.

  Both commands now send `modelDir: chosenModelDir()` instead of `model`. `node --check` passes, and all 12 GUI scenarios pass, including command drift and CSP.

- [x] 3.3 Add GUI scenarios to `tests/test_gui.py`:
  - **default:** the field shows the bundled model, and `start_live_session` gets `modelDir: null`;
  - **pick:** the fake `dialog.open` returns `/models/small`, the field shows it, and a live start and a file drop both send `modelDir: "/models/small"`;
  - **remember:** after a reload the choice is still shown and sent;
  - **reset:** returning to the bundled model sends `null`;
  - **cancel:** a dialog returning `null` leaves the choice unchanged;
  - **refusal:** a `start_live_session` rejection with the folder message is shown as a note.

  Verify they pass. Also verify the remember scenario fails if the `localStorage` write is removed.

  **Done 2026-09-15.** `test_model_folder` covers:
  - **default:** `Bundled (base)`, and `modelDir: null`;
  - **pick:** `__fake.dialogOpen = '/models/small'` shows "small", and `/models/small` reaches `start_live_session` and `start_file_transcription`;
  - **cancel:** a `null` picker result keeps `/models/small`;
  - **remember:** after `page.reload()` it's still shown and sent;
  - **reset:** selecting the bundled option sends `null`;
  - **refusal:** a `start_live_session` rejection with the shell's folder message appears in the note.

  The fake bridge's `dialog.open` now returns `__fake.dialogOpen`. Passes, with all 13 GUI scenarios. With the `localStorage.setItem` removed the scenario fails. It fails already at "pick" (expected value `/models/small`), because the field reads its value back from storage, so "remember" can't pass without the write either.

- [x] 3.4 Finish the Impeccable pass: have the `impeccable-finish-reviewer` agent review the built field (not an inline self-review), apply any material fixes it lists and re-screenshot once, record the verdict, and update `DESIGN.md` (and `.impeccable/design.json` if a component changed) for the new Model field. Run `detect.mjs` once on the changed files. Verify `DESIGN.md` describes the field, and that the verdict is recorded here.

  **Done 2026-09-15.**
  - **Reviewer:** the `impeccable-finish-reviewer` agent returned **Verdict: fix**. Type, material, ground and fit all matched, the ceiling was reached, and it said to keep the single native select with "Bundled (base)" first. Its four material fixes were all applied:
    1. **Arrow keys opened the folder picker.** Stepping onto "Choose folder…" on a closed select fires `change` and opened the dialog. A `keydown` flag for arrow, Home, End and Page keys now makes that snap back. `test_model_folder` gained a keyboard case: End then ArrowDown gives `__fake.dialogOpens == 0`. It fails with the guard removed ("arrow keys opened the folder picker").
    2. **Hash as the folder name.** A Hugging Face cache snapshot showed its hash, so `folderName()` now names `…/models--Org--name/snapshots/<hash>` as `Org--name`. Also tested.
    3. **Save to too narrow at 640px.** `#model-select { max-width: 9rem }` applies under `52rem`: 144 px at 640, 192 px at 900.
    4. **Refusal wording.** The message now reads "the model folder <path> has no model.bin. Choose a faster-whisper model folder under Model, or pick Bundled (base).", lower-cased after the note's colon. The GUI test's string is updated.
  - **Re-screenshot:** captured once, light and dark, at 900 and 640, with a long cache path. No overflow, no CSP violations or script errors, and Save to stays readable.
  - **Detector:** `detect.mjs` ran once, in degraded regex mode (its parser modules aren't installed). It reported 16 advisories, all on older lines, none in the new CSS.
  - **Docs:** `DESIGN.md` Inputs / Fields gains **Model field**, and `.impeccable/design.json` gains a `Model Field` component.
  - **Not changed:** the CLI's `_model_label` still names a `--model-path` by its own folder, as the cli spec says, so a cache snapshot path prints its hash there. The friendlier cache naming is GUI-only.

## 4. Docs

- [x] 4.1 README:
  - GUI section: how to choose a model folder, and how to return to the bundled one;
  - CLI `--model-path` entry: what a model folder is (a faster-whisper/CTranslate2 model repository, such as `Systran/faster-whisper-small`, downloaded by the user), and that output names it by folder;
  - the English-only (`*.en`) language caveat.

  Also fix the stale sentence saying the GUI always passes the bundled `--model-path`. Verify these lines exist and none still says the GUI only uses the bundled model.

  **Done 2026-09-15.** README changes:
  - **"Download and run":** a new **Using a different model in the app** paragraph. It covers downloading a faster-whisper folder with `model.bin` (linking Systran/faster-whisper-small), **Choose folder…**, that the choice is remembered, **Bundled (base)** to go back, the refusal when the folder moves, and English-only models.
  - **Complete Options:** a new `--model-path <dir>` entry covering what the folder is, where to get one, labelling by folder unless `--model` is given, and English-only models.
  - **Stale sentence fixed:** "The GUI sidecar always passes an explicit `--model-path` pointing at its bundled model directory" now reads "…the bundled model directory … or the model folder the user chose".

  Checked against faster-whisper's `transcribe.py`: for an English-only model it forces auto-detect to `en`, and the model can't output other languages. The README says only "can only transcribe English", not that it overrides the Language field. No README line still says the GUI only uses the bundled model.

## 5. End-to-end scenarios (design.md Decision 6)

- [x] 5.1 In `tests/test_e2e_linux.py`, give each scenario's app its own data directory (`XDG_DATA_HOME` under the scenario's temp directory), so no scenario reads or writes the real `~/.local/share/com.transcriber.app`. Verify the existing six scenarios still pass, and that the real directory's modification time is unchanged by a run.

  **Done 2026-09-15.** `app_env()` sets `XDG_DATA_HOME` to `<scenario temp>/data` for every app launch. With the VPN off, all six existing scenarios passed (exit 0). `find ~/.local/share/com.transcriber.app -newer <start marker>` found nothing, and the directory's mtime was unchanged (1788629636) across the run.

- [x] 5.2 Add `model folder remembered`. Set the stored choice through the page's storage key to a temp folder holding a `model.bin`, then close the app. A second app, started with the same data directory, must show that folder in the Model field. Verify it passes, and fails if the page stops reading the stored value on load (temporarily), then revert.

  **Done 2026-09-15.** `test_model_folder_remembered` stores the choice with `localStorage.setItem` plus the page's own `renderModelSelect()`, closes the app, and starts a new app with the same `XDG_DATA_HOME`. The Model field shows `[<folder>, "faster-whisper-e2e"]`. Passes. With the page's load-time `renderModelSelect()` commented out and the app rebuilt, it failed with "timed out waiting for the Model field to load". Reverted.

- [x] 5.3 Add `model folder refused`. Store a temp folder without `model.bin`, click **Start transcribing** from script, and assert:
  - the note names the folder and says it has no usable model;
  - no `transcriber-sidecar` process was started (`pgrep -f` on the sidecar path, before and after).

  Verify it passes, and fails with `select_model_dir`'s `model.bin` check temporarily removed, then revert.

  **Done 2026-09-15.** `test_model_folder_refused` stores an empty `not-a-model` folder and clicks **Start transcribing** from script. The note must contain the folder and "has no model.bin", and `pgrep -f "transcriber-sidecar.*--live"` must find nothing before, and 1 s after. (A plain sidecar-path match wasn't used, because the page's `--list-devices-json` run is a legitimate sidecar.) Passes. With `select_model_dir`'s `model.bin` check replaced by `true` and the app rebuilt, it failed with "timed out waiting for the refusal note". Reverted and rebuilt.

- [x] 5.4 Add `model folder used`:
  - make a temp folder `faster-whisper-e2e` whose files are symlinks to the bundled model's, store it, and start a file run on a 1-second silent WAV written with the stdlib `wave` module;
  - assert the engine log (`#debug-log`) shows the model loading from that folder;
  - return to the bundled model and repeat, asserting the log shows the bundled folder.

  Before writing the scenario, check whether a `tauri://drag-drop` event emitted from script reaches the page's listener. If it doesn't, start the run by calling `start_file_transcription` with the page's own `modelDir` value through execute-script. Record which was used. Verify it passes.

  **Done 2026-09-15.** A `tauri://drag-drop` event emitted from script reaches the page's listener and runs the page's own queue, so that was used: the real `modelDir` path, not a direct invoke. `test_model_folder_used`:
  - stores `faster-whisper-e2e` (symlinks to the bundled model), drops a 1 s silent WAV, waits for the engine log to show `" model from <folder> on "`, and waits for the queue to finish;
  - clears the choice and repeats, expecting `" model from <target/debug/resources/model> on "`.

  Passes.

  **Found:** the log line reads "Loading **base** model from <chosen folder>". The debug app runs the staged frozen sidecar (`src-tauri/binaries/…`, built at 08:51, before 1.1's label change), so the scenario matches on the folder path, not the label. The label has its own unit test (1.1), and the real-build check in 6.2 will show it once the sidecar is rebuilt.

  The suite docstring and the README suites-table row now mention these scenarios.

## 6. Verification

- [x] 6.1 Run `.venv/bin/python run_tests.py` with `TRANSCRIBER_TEST_SPEECH` set, and a network that reaches GitHub. Verify it exits 0, and that every end-to-end scenario prints `PASS`.

  **Done 2026-09-15.** With `TRANSCRIBER_TEST_SPEECH` set and GitHub reachable: 13/13 suites passed, exit 0. All nine end-to-end scenarios printed `PASS`: the six from before, plus `model folder remembered`, `model folder refused` and `model folder used`.

  The first full run had two failures, both fixed:
  - **`test_dual_capture.py`:** its hand-built `args` namespace had no `model_label`, which 1.1's output sites now read. Added `model_label="base"`.
  - **`model folder remembered` (flaky):** it passed alone but failed in the full run. WebKit writes `localStorage` to its `.localstorage-wal` file about 0.5 s after `setItem`, and the test killed the app's process group sooner. The scenario now waits until the choice is in the app's storage file before closing. It then passed 3 times in a row on its own, and in the full run. A user quitting the app normally isn't affected.

- [ ] 6.2 **User check on Linux** (a local build or `tauri dev`), with a second real model folder downloaded beforehand (e.g. `Systran/faster-whisper-small`). This covers what the end-to-end suite can't drive: the native folder dialog, and a real different model.
  - **Browse…** opens the system folder picker, and choosing the folder shows it in the Model field;
  - a transcription uses it: the engine log loads from that folder, and the CLI transcript header names it by folder;
  - cancelling the picker changes nothing.
