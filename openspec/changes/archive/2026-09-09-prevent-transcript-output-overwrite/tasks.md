## 1. Live session output

- [x] 1.1 `withFreshTimestamp()` stamps the output field's current value fresh at the moment `startLiveSession()` runs, stripping any prior auto-stamp first (`src/main.js`)
- [x] 1.2 The stamped path is written back into `outputPathInput` before the session starts, so what's displayed matches what's written
- [x] 1.3 On Windows hardware, start a live session, stop it, start a second one without editing the output field — confirm two distinct transcript files exist and the first wasn't truncated

  **Verified on real Windows hardware with real WASAPI loopback capture and real transcribed audio.** Two back-to-back live sessions through the packaged `dist/portable/Transcriber/transcriber-sidecar.exe`, stopped the way the GUI stops them, produced:

  ```
  transcript_20260909_133222.txt  306 bytes  07:34:06
  transcript_20260909_133432.txt  297 bytes  07:35:51
  ```

  Both hold genuine transcribed speech (`[SYS] The quick brown fox jumps over the lazy dog` / `[SYS] hack my box with 5 dozen liquor jugs`), captured from the auto-detected loopback endpoint. Session 1's file was SHA256-hashed before session 2 started and again after it finished: **byte-identical, same length, same mtime** — not truncated, not reopened.

  **The filenames were not hand-written for the test.** They came from the real `withFreshTimestamp()`/`defaultOutputFilename()` source read straight out of `src/main.js`, chained exactly as the GUI chains them: page-load default → start #1 stamps it and writes the result back into the field (`main.js:630-631`) → start #2 re-stamps that same field value with nothing edited in between. Each session was stopped with `taskkill /F /T /PID`, which is literally what `stop_live_session()` runs on Windows (`src-tauri/src/sidecar.rs`), so the stop path is the real one rather than an approximation.

  Three supporting checks closed the gaps between that and a literal button click:
  - **Frontend logic**, driven deterministically against the shipped `main.js` source with a controllable clock: ten consecutive starts yield ten distinct names with exactly one stamp each (no `_20260904_101500_20260904_101512` accumulation); a browsed absolute path keeps its directory and gets re-stamped rather than appended; extensionless names and non-stamp digit runs (`call_12345.txt`) behave; and two starts inside the same wall-clock second do collide, exactly as design.md documents as an accepted risk.
  - **Rust passthrough** had no test on this change's path, so two were added to `sidecar.rs`: `forwards_stamped_output_path_verbatim` (the stamped name reaches `--output` unmodified — any normalising here would collapse two sessions back onto one file) and `omits_output_when_empty_rather_than_passing_a_blank_path`. `cargo test sidecar::tests` → 9 passed, 0 failed.
  - **`--output` honored exactly** was already established by task 2.3.

  **What this does not cover:** the sessions were driven through the sidecar CLI with GUI-generated arguments, not by physically clicking Start/Stop/Start in `transcriber-gui.exe` — no desktop-automation tool is available here to click into a WebView. Every link in the chain is verified independently, so the composed behavior follows, but a human clicking the real button twice is still the one step nobody has performed.

  Incidental observation, not a defect in this change: capture took **60–84s to start** in these runs, all of it model load before the output file is opened. Almost certainly inflated by reading the 145MB model over the `\\wsl.localhost` UNC path rather than from a local install — worth a glance if GUI startup ever feels slow, but not measured against a local extraction here.

## 2. File-mode output

- [x] 2.1 `transcriber.py`'s auto-derived output name (the `else` branch when `args.output` is unset) now includes a `%Y%m%d_%H%M%S` timestamp
- [x] 2.2 Transcribe the same input file twice via the GUI's drop zone — confirm two distinct output files exist in the working directory and neither is truncated

  **Verified via the exact code path the GUI drop zone triggers, not the GUI itself** — no desktop-automation tool available in this environment to drive an actual drag-and-drop. Confirmed in `src-tauri/src/sidecar.rs`'s `start_file_transcription` that the GUI never passes `--output` (matches design.md's stated assumption), so it always takes `transcriber.py`'s auto-stamped `else` branch. Ran `transcriber.py --file test_tone.wav --model tiny` (no `--output`, same args the GUI sends) twice in a row: produced `test_tone_transcript_20260907_122526.txt` and `test_tone_transcript_20260907_122529.txt` — two distinct, non-empty-write-target files, first untouched by the second run.
- [x] 2.3 Confirm an explicit `--output` path (CLI usage, not currently exercised by the GUI) still writes to exactly that path, unstamped

  Verified: `transcriber.py --file test_tone.wav --output my_exact_name.txt --model tiny` wrote to `my_exact_name.txt` exactly, no timestamp appended.

## 3. Spec

- [x] 3.1 Update `desktop-gui`'s "Live session transcript is saved to a file" requirement with the re-stamp-on-start behavior and a new scenario
- [x] 3.2 Add a new `cli` requirement documenting file-mode's timestamped auto-derived output name
