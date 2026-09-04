## 1. Live session output

- [x] 1.1 `withFreshTimestamp()` stamps the output field's current value fresh at the moment `startLiveSession()` runs, stripping any prior auto-stamp first (`src/main.js`)
- [x] 1.2 The stamped path is written back into `outputPathInput` before the session starts, so what's displayed matches what's written
- [ ] 1.3 On Windows hardware, start a live session, stop it, start a second one without editing the output field — confirm two distinct transcript files exist and the first wasn't truncated

## 2. File-mode output

- [x] 2.1 `transcriber.py`'s auto-derived output name (the `else` branch when `args.output` is unset) now includes a `%Y%m%d_%H%M%S` timestamp
- [ ] 2.2 Transcribe the same input file twice via the GUI's drop zone — confirm two distinct output files exist in the working directory and neither is truncated
- [ ] 2.3 Confirm an explicit `--output` path (CLI usage, not currently exercised by the GUI) still writes to exactly that path, unstamped

## 3. Spec

- [x] 3.1 Update `desktop-gui`'s "Live session transcript is saved to a file" requirement with the re-stamp-on-start behavior and a new scenario
- [x] 3.2 Add a new `cli` requirement documenting file-mode's timestamped auto-derived output name
