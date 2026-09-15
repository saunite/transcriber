## Context

- `src-tauri/src/sidecar.rs`:
  - `start_live_session` and `start_file_transcription` each take `model: String` from the page.
  - Both always add `--model <model> --model-path <resolve_model_dir()>`, where `resolve_model_dir()` is the bundled `resources/model`.
  - `build_live_session_args` is the unit-tested argument builder for live sessions. The file command builds its arguments inline.
- `src/main.js` sends `els.modelSelect.value` to both commands.
- The page already uses the dialog plugin (`saveFileDialog` for Save to, and `open` for dropped-file selection) under `dialog:default`. It stores the theme choice in `localStorage` (`transcriber-theme`).
- `transcriber.py`:
  - `--model` defaults to `'base'` with fixed choices, and `--model-path` defaults to `None`.
  - `_bundled_model_path(args.model)` fills `model_path` for the frozen CLI.
  - `args.model` is printed in four places: two transcript-file headers, the compact summary line, and `_print_header` (four live paths).
- `transcription_engine.py` already raises `FileNotFoundError` when `model_path` lacks `model.bin`, and `WhisperModel` loads any CTranslate2 model directory.

## Goals / Non-Goals

**Goals:**
- One source of truth for which model a GUI session uses, shown in the UI.
- A missing or wrong folder is caught before any engine is spawned.
- CLI output never names a model that wasn't loaded.

**Non-Goals:**
- Deeper validation than `model.bin`, such as tokenizer or config files. A folder that passes but is broken fails in the engine, and the existing crash note shows its error.
- Detecting a model's size or languages from its files.
- Watching the folder for changes between sessions. It is checked at each session start.

## Decisions

### 1. The shell picks and checks the folder, in one pure function
Both commands take `model_dir: Option<String>` instead of `model: String`. A pure `select_model_dir(chosen: Option<String>, bundled: String) -> Result<String, String>` returns `bundled` for `None` or an empty string. Otherwise it returns the chosen path if `<path>/model.bin` is a file, and a plain error otherwise, for example: "The model folder <path> has no model.bin. Choose a faster-whisper model folder, or switch back to the bundled model."

Both commands call it before any spawn, and before the file command's one-engine guard has any side effects. The existing `invoke` rejection path then shows the message as a note: "Could not start live capture: …" or "Could not transcribe …".

`build_live_session_args` takes the resolved directory plus a flag saying whether it is the bundled one. File arguments get the same treatment, so both are unit-testable.

- *Alternative:* check in the page. The page has no filesystem access, and adding the fs plugin for one check widens the page's permissions. Rejected.
- *Alternative:* let the engine fail. That spawns a process and surfaces a Python traceback line. Rejected, because the spec requires refusing before spawning.

### 2. `--model` is passed only for the bundled model
For the bundled folder the shell passes `--model base --model-path <bundled>`, which labels the output as today. For a chosen folder it passes only `--model-path <chosen>`, and the CLI labels it by folder name (Decision 4). The page no longer sends a size.

### 3. The choice lives in `localStorage`, like the theme
The key is `transcriber-model-dir`. An absent or empty value means the bundled model. The same try/catch pattern as the theme code is used.

- If storage is cleared, the app falls back to the bundled model, which always works.
- *Alternative:* `tauri-plugin-store` or a config file written by Rust. That adds a dependency or a settings layer for one string. Rejected until there is more than one real setting.

### 4. CLI label derived once, before the bundled lookup
`--model` gets `default=None`, and its choices stay the same. Right after parsing, and before `_bundled_model_path`, the CLI computes:
- `args.model_label = args.model or (Path(args.model_path).name if args.model_path else 'base')`, using the path with any trailing separator stripped;
- then `args.model = args.model or 'base'`.

Name resolution and the bundled lookup still see `base` as before. The four output sites print `args.model_label`. A frozen CLI that uses its bundled model therefore still says `base`.

- *Alternative:* print the full path. It's too long for the one-line summary. The folder name is what users recognise, for example `faster-whisper-small`.

### 5. The Model field is redesigned with the Impeccable skill
Replacing a select in the title block with a folder display, **Browse…** and a way back to the bundled model changes the layout. The pass runs on the `src-index-html` surface under `DESIGN.md`. Constraints:
- it must fit the title block at 900px and at the 640×480 minimum;
- it reuses the Save to field's pattern (read-only path plus quiet **Browse…**) where it fits;
- long paths are truncated to show the folder name;
- there must be a clear bundled state and a keyboard-reachable reset;
- no new colours;
- strict CSP (no inline handlers or styles).

The pass records any placement change and its reason in tasks.

## Risks / Trade-offs

- **English-only or distil models** (such as `*.en`) with a non-English language chosen: faster-whisper forces or warns about English for non-multilingual models, and the language dropdown still lists every language. → Documented in README. A per-model language list is a non-goal.
- **The chosen folder is on a removable or network drive.** → It is checked at each session start, and the refusal message says how to recover.
- **A page-supplied path reaches the sidecar's argument list.** → It is passed as a separate argument with no shell, and must contain `model.bin`. The page can already send arbitrary file paths for transcription, so no new privilege is added.
- **BREAKING for anyone relying on the dropdown's value in logs.** → It never changed the model, so nothing functional is lost.

## Migration Plan

- There is no stored data to migrate: the old dropdown was never persisted.
- Rollback is reverting the change. The page and shell ship together in one binary, so their argument shapes can't drift apart. The command-drift GUI test still guards the command names.
