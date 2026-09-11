## Why

The GUI's live controls say "Start recording" and "Stop recording", and the status line says "Recording". The app doesn't record: it transcribes live audio and saves a transcript, and since `remove-audio-saving` it keeps no audio at all. The wording promises an audio file the user will never get, and it clashes with the rest of the interface, which talks about transcripts.

## What Changes

- **Live-capture controls and status say "transcribing"** (user's choice of wording):

  | Where | Now | Becomes |
  |---|---|---|
  | Main button | Start recording | Start transcribing |
  | Stop button | Stop recording | Stop transcribing |
  | Status, idle | Not recording | Not transcribing |
  | Status, running | Recording | Transcribing |
  | Status, stalled | Recording stalled — no output | Transcribing stalled — no output |
  | Live chart empty state | Nothing recorded yet. / Press **Start recording** to capture this meeting. | Nothing transcribed yet. / Press **Start transcribing** to capture this meeting. |
  | Engine log marker | recording started | transcription started |

- **The live output field is labelled "Save to"** instead of "Record to". It holds the transcript's file path.
- **`DESIGN.md`'s button example** quotes the new label.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
(none — no requirement names these labels. `desktop-gui` requires the states be distinguishable, the transcript be saved, and so on; all of that still holds word for word.)

This change sets `skip_specs: true` in `.openspec.yaml`: it is user-visible wording only, with no behavior change.

## Impact

- **Changed**: `src/index.html`, `src/main.js` (the status label table and one log marker), `DESIGN.md` (one line).
- **Deliberately unchanged**:
  - **File-side wording** — "Drop recordings", "No recording loaded", "relative to the start of the recording". A dropped `.mp4` genuinely is a recording, and the main specs use the word that way too ("File transcripts are saved next to the recording").
  - **CSS class names** (`.btn-record`, `.btn-record-pen`) and the `--shadow` "Record lift" token: internal names, no user-visible text, and renaming them would churn the stylesheet for nothing.
  - **`DESIGN.md`'s "chart recorder" north star**: it describes how the instrument looks, not a claim that the app records audio.
