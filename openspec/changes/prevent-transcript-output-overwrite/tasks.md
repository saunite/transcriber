## 1. Live session output

- [x] 1.1 `withFreshTimestamp()` stamps the output field's current value fresh at the moment `startLiveSession()` runs, stripping any prior auto-stamp first (`src/main.js`)
- [x] 1.2 The stamped path is written back into `outputPathInput` before the session starts, so what's displayed matches what's written
- [ ] 1.3 On Windows hardware, start a live session, stop it, start a second one without editing the output field — confirm two distinct transcript files exist and the first wasn't truncated

## 2. File-mode output

- [x] 2.1 `transcriber.py`'s auto-derived output name (the `else` branch when `args.output` is unset) now includes a `%Y%m%d_%H%M%S` timestamp
- [x] 2.2 Transcribe the same input file twice via the GUI's drop zone — confirm two distinct output files exist in the working directory and neither is truncated

  **Verified via the exact code path the GUI drop zone triggers, not the GUI itself** — no desktop-automation tool available in this environment to drive an actual drag-and-drop. Confirmed in `src-tauri/src/sidecar.rs`'s `start_file_transcription` that the GUI never passes `--output` (matches design.md's stated assumption), so it always takes `transcriber.py`'s auto-stamped `else` branch. Ran `transcriber.py --file test_tone.wav --model tiny` (no `--output`, same args the GUI sends) twice in a row: produced `test_tone_transcript_20260907_122526.txt` and `test_tone_transcript_20260907_122529.txt` — two distinct, non-empty-write-target files, first untouched by the second run.
- [x] 2.3 Confirm an explicit `--output` path (CLI usage, not currently exercised by the GUI) still writes to exactly that path, unstamped

  Verified: `transcriber.py --file test_tone.wav --output my_exact_name.txt --model tiny` wrote to `my_exact_name.txt` exactly, no timestamp appended.

## 3. Spec

- [x] 3.1 Update `desktop-gui`'s "Live session transcript is saved to a file" requirement with the re-stamp-on-start behavior and a new scenario
- [x] 3.2 Add a new `cli` requirement documenting file-mode's timestamped auto-derived output name
