## 1. Engine: explicit model path

- [ ] 1.1 Add `model_path: Optional[str] = None` to `TranscriptionEngine.__init__`; when set, pass it to `WhisperModel(model_path, ...)` instead of `model_size`
- [ ] 1.2 Before constructing `WhisperModel`, validate the path exists and looks like a model directory (e.g. contains `model.bin`); raise a clear error naming the missing path otherwise
- [ ] 1.3 Add `--model-path <dir>` to `transcriber.py`'s argparse and thread it through to `TranscriptionEngine(...)` construction (both file and live code paths already share the single `engine` instance, so one wiring point covers both)
- [ ] 1.4 Confirm `--model` is still required/used for display/logging purposes even when `--model-path` is set (so log output still says what model size is running)

## 2. Verify the fix isn't masked by this machine's cache

- [ ] 2.1 Run with `HF_HOME` (or equivalent) pointed at an empty temp directory and `--model-path` unset -- confirm this reproduces the real bug (attempts network download / fails without network)
- [ ] 2.2 Same empty-cache setup, with `--model-path src-tauri/resources/model` -- confirm transcription succeeds with no network access needed
- [ ] 2.3 Regression-check existing tests (`test_transcript_line_format.py`, `test_macos_capture.py`, `test_wasapi_capture.py`) still pass

## 3. GUI: sidecar always passes the bundled model path

- [ ] 3.1 In `src-tauri/src/sidecar.rs`, resolve the bundled model directory relative to the running app's own location (works for both installed and portable layouts)
- [ ] 3.2 Pass `--model-path <resolved dir>` when spawning the sidecar for both `start_live_session` and `start_file_transcription`
- [ ] 3.3 Rebuild via the Docker cross-compile path and confirm `cargo check`/`cargo tauri build` still succeed

## 4. Portable build assembly

- [ ] 4.1 Write an assembly script (e.g. `build_portable.ps1` or `.py`) that copies `transcriber-gui.exe`, `transcriber-sidecar.exe`, `WebView2Loader.dll` from `src-tauri/target/<triple>/release/`, plus `src-tauri/resources/model/`, into an output folder
- [ ] 4.2 Optionally zip the assembled folder
- [ ] 4.3 Smoke-test: extract/copy the assembled folder to a different location, run `transcriber-gui.exe` from there, confirm it starts and the sidecar resolves its model path correctly (no dependency on `src-tauri/`'s original location)

## 5. Documentation

- [ ] 5.1 README: note the portable build option alongside the installer instructions, with the assembly script usage
- [ ] 5.2 Cross-reference in `add-tauri-gui`'s tasks.md that the model-bundling gap it flagged (6.3 area) is addressed here
