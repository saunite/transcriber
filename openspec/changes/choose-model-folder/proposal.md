## Why

The GUI's **Model** dropdown doesn't work. Both `start_live_session` and `start_file_transcription` always pass `--model-path <bundled base dir>`, so choosing "large" still transcribes with `base`. The engine log and the transcript header then say "large". Users with a better model already on disk have no way to use it from the GUI.

The CLI can load a folder with `--model-path`, but it mislabels it the same way. The transcript header, the compact summary line and the live header all print `--model`, which defaults to `base`, whatever folder was loaded.

## What Changes

- **GUI:** replace the Model dropdown with a model folder choice.
  - The default is the bundled `base` model.
  - The user can pick a folder that holds a faster-whisper (CTranslate2) model through the native folder dialog, or go back to the bundled model.
  - The choice is remembered between launches.
  - **BREAKING (GUI only):** the size dropdown (tiny…large) goes away. It never loaded those sizes.
- **Shell:** the sidecar is still always started with an explicit `--model-path`, either the bundled folder or the chosen one. Before spawning, the shell checks the chosen folder contains `model.bin`. If it doesn't, the session is refused with a plain message, and no engine is started.
- **CLI:** when `--model-path` is given without `--model`, output names the loaded model after its folder, not after a size that wasn't loaded. This covers the transcript header, the summary line and the live header. Explicit `--model` still labels as before, and name resolution without `--model-path` is unchanged.
- **Docs:** README explains how to get a model folder: download a faster-whisper model repository yourself and point the app or `--model-path` at it.
- **Not in this change:**
  - downloading models from the app or CLI (a possible follow-up; it would add a user-initiated network action);
  - a model manager or list of installed models;
  - per-model language lists.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `desktop-gui`:
  - "Sidecar always loads the bundled model explicitly" becomes: the sidecar always loads an explicit model folder, the bundled one or the user's validated choice.
  - Added: the user can choose a model folder, remembered between launches, and reset to the bundled model.
- `cli`: "Accept an explicit local model path" adds that output names a `--model-path` model after its folder when `--model` isn't given.

## Impact

- **`src-tauri/src/sidecar.rs`:** both start commands take an optional `model_dir` instead of `model`, with a pure, unit-tested folder check. The page's call arguments change.
- **`src/index.html`, `src/style.css`, `src/main.js`:** the title-block Model field is redesigned through the Impeccable skill, since it changes the GUI layout. `DESIGN.md` is updated.
- **`transcriber.py`:** `--model` defaults to unset, so an explicit value can be told apart. The model label is derived once and used by the three output sites.
- **Tests:** (end-to-end scenarios in `tests/test_e2e_linux.py` too, see design.md Decision 6)
  - `cargo test` for the folder check and argument building;
  - GUI scenarios for pick, remember, reset and refusal;
  - a CLI unit test for the label.
- **Unchanged:** no new dependencies, and no network use. The offline first run and the bundled model are unchanged.
