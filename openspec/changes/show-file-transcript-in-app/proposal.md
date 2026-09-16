## Why

`desktop-gui`'s "Drop a video file" scenario promises the app shows "progress and the resulting transcript", and the File tab has a chart ready for it. It never fills. File mode writes each segment to the output file (`transcription_engine.transcribe_file`) and prints none of them, so `sidecar.rs` sees no line matching its transcript regex and emits no `transcript-line` event. The user drops a recording, watches an empty chart for the length of the transcription, and has to open the file afterwards.

The spec and the code contradict each other, so one of them is wrong. Parked on 2026-09-15 while planning `add-automated-local-tests`, whose GUI tests deliberately assert nothing either way. Picked up with the user's go-ahead on 2026-09-16.

The CLI has the same gap in a milder form: a file run prints a tqdm progress bar and a summary, but never the text it is transcribing.

## What Changes

- **File transcription prints each segment as it is transcribed**, in the same `[start -> end] text` form it writes to the output file, so the app's File chart fills as the work happens and the CLI shows the transcript rather than only a bar.
- **The app shows those lines** on the File chart, which already routes them: no GUI change is expected beyond confirming it, since `currentFlow` is set to `file` for a file run and the line parser accepts the relative range format.
- **Not in this change:** progress as a percentage or a bar in the app; the `--no-timestamps` and `srt`/`vtt` output formats, which only affect the saved file.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `cli`: added "File transcription prints its transcript as it goes".
- `transcription`, "Transcribe an audio file": segments are reported as they are produced, rather than only written to the output file.
- `desktop-gui`, "File transcription via drag-and-drop": the dropped file's transcript appears in the app while it is transcribed, which is what the existing scenario already promises.

## Impact

- **`transcription_engine.py`:** `transcribe_file` prints each segment's timestamped line as it writes it. tqdm's bar goes to stderr, so the two don't interleave on stdout.
- **`src/main.js`:** no change expected; the file flow already appends `transcript-line` events to the File chart.
- **Tests:** a check that file mode prints timestamped lines on stdout (`tests/test_engine.py`, which already runs a real file transcription), a GUI scenario asserting a file run's lines land on the File chart, and the e2e Linux suite's file transcription asserting the chart is not empty.
- **Docs:** the user guide's file-transcription section.
- **No shell (Rust), dependency or layout changes.**
