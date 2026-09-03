## 1. Engine: explicit model path

- [x] 1.1 Add `model_path: Optional[str] = None` to `TranscriptionEngine.__init__`; when set, pass it to `WhisperModel(model_path, ...)` instead of `model_size`
- [x] 1.2 Before constructing `WhisperModel`, validate the path exists and looks like a model directory (e.g. contains `model.bin`); raise a clear error naming the missing path otherwise
- [x] 1.3 Add `--model-path <dir>` to `transcriber.py`'s argparse and thread it through to `TranscriptionEngine(...)` construction (both file and live code paths already share the single `engine` instance, so one wiring point covers both)
- [x] 1.4 Confirm `--model` is still required/used for display/logging purposes even when `--model-path` is set (so log output still says what model size is running)

  Confirmed by inspection, no change needed: `args.model` keeps its `default='base'` and is used unconditionally for `_print_header(args.model, ...)`, every `# Model: {args.model}` output-file header, and `TranscriptionEngine`'s own "Loading {model_size} model..." print — none of that branches on `model_path`.

## 2. Verify the fix isn't masked by this machine's cache

- [x] 2.1 Run with `HF_HOME` (or equivalent) pointed at an empty temp directory and `--model-path` unset -- confirm this reproduces the real bug (attempts network download / fails without network)

  Used `HF_HOME=<empty temp dir>` + `HF_HUB_OFFLINE=1` (forces offline mode deterministically rather than depending on this machine's actual network state). Reproduced exactly: `huggingface_hub.errors.LocalEntryNotFoundError: Cannot find an appropriate cached snapshot folder ... and outgoing traffic has been disabled.`

- [x] 2.2 Same empty-cache setup, with `--model-path src-tauri/resources/model` -- confirm transcription succeeds with no network access needed

  Same empty `HF_HOME` + `HF_HUB_OFFLINE=1`, with `--model-path src-tauri\resources\model`: loaded successfully ("Loading base model from src-tauri\resources\model...") and transcribed a synthetic sample WAV to completion, exit 0 -- no network/cache lookup attempted at all.
- [x] 2.3 Regression-check existing tests (`test_transcript_line_format.py`, `test_macos_capture.py`, `test_wasapi_capture.py`) still pass

  All three pass unchanged (none construct `TranscriptionEngine`, so the new `model_path` param didn't touch them).

## 3. GUI: sidecar always passes the bundled model path

- [x] 3.1 In `src-tauri/src/sidecar.rs`, resolve the bundled model directory relative to the running app's own location (works for both installed and portable layouts)

  Added `resolve_model_dir()` using `app.path().resource_dir()` (Tauri's path API, portable/installed-agnostic) joined with `resources/model`, matching `tauri.conf.json`'s `bundle.resources: ["resources/model/**/*"]`.

- [x] 3.2 Pass `--model-path <resolved dir>` when spawning the sidecar for both `start_live_session` and `start_file_transcription`
- [x] 3.3 Rebuild via the Docker cross-compile path and confirm `cargo check`/`cargo tauri build` still succeed

  `cargo check --target x86_64-pc-windows-gnu` in the Docker container: exit 0. (A prior `cargo tauri build --bundles nsis` in this same session, before these sidecar.rs changes, already confirmed the bundling pipeline works end-to-end -- this check confirms the new `resolve_model_dir()` code and its call sites compile clean.)

## 4. Portable build assembly

- [x] 4.1 Write an assembly script (e.g. `build_portable.ps1` or `.py`) that copies `transcriber-gui.exe`, `transcriber-sidecar.exe`, `WebView2Loader.dll` from `src-tauri/target/<triple>/release/`, plus `src-tauri/resources/model/`, into an output folder

  `build_portable.ps1` at the repo root, alongside the existing `build_sidecar.py`/`fetch_sidecar_resources.py` top-level build scripts. Copies the model into `<output>/resources/model` (not flattened) to match the exact relative layout `sidecar.rs`'s `resolve_model_dir()` expects next to the exe.

- [x] 4.2 Optionally zip the assembled folder

  `-Zip` switch on `build_portable.ps1` (`Compress-Archive`).
- [x] 4.3 Smoke-test: extract/copy the assembled folder to a different location, run `transcriber-gui.exe` from there, confirm it starts and the sidecar resolves its model path correctly (no dependency on `src-tauri/`'s original location)

  **Found and fixed a real bug in the process**: the first smoke-test attempt failed with `unrecognized arguments: --model-path` — `cargo tauri build` only copies whatever's already staged at `src-tauri/binaries/transcriber-sidecar-x86_64-pc-windows-gnu.exe`, it does **not** re-run `build_sidecar.py`. That staged binary was a stale PyInstaller freeze from before this change added `--model-path` to `transcriber.py`, so the just-rebuilt GUI was pairing a fixed Rust side with an old sidecar that didn't understand the flag it was being sent — a real end-to-end break this change would otherwise have shipped. Fixed by re-running `build_sidecar.py`, re-staging the fresh exe, and rebuilding. **Takeaway for anyone touching `transcriber.py`/`transcription_engine.py` going forward: re-run `build_sidecar.py` before any GUI/portable rebuild, or the bundle silently ships a stale sidecar.**

  Also independently verified `resolve_model_dir()`'s assumption by reading the actual `tauri` crate source (`tauri-utils-2.9.3/src/platform.rs`): on Windows, `resource_dir()` unconditionally returns the executable's own directory (`cfg!(target_os = "windows")` short-circuits the check), for both dev, installed, and portable layouts — confirming `<exe_dir>/resources/model` is correct, not just assumed.

  With the corrected sidecar: relocated the assembled `dist\portable\Transcriber` folder to an unrelated path, launched `transcriber-gui.exe` from there (started, stayed responsive, correct window title), and separately invoked `transcriber-sidecar.exe` directly from that same relocated folder with `--model-path <relocated>\resources\model` — loaded the bundled model and transcribed successfully, exit 0, no dependency on the original `src-tauri/` location.

## 5. Documentation

- [x] 5.1 README: note the portable build option alongside the installer instructions, with the assembly script usage
- [x] 5.2 Cross-reference in `add-tauri-gui`'s tasks.md that the model-bundling gap it flagged (6.3 area) is addressed here

  Added a note under `add-tauri-gui` task 2.5 (where the model was staged but not yet actually wired to be loaded from).
