## Why

Testing the GUI (`cargo tauri dev`) showed two problems with where transcripts end up:

- **Transcripts land in whatever folder the app was started from.** `sidecar.rs` never sets a working directory for the engine. The GUI passes no output path for file transcription, and the live default is a bare filename (`transcript_….txt`), so both resolve against the app's own working directory. In the dev run that was `src-tauri/`, inside the repository. Launched from the desktop menu it's usually the home folder. Neither is where a user would look, and the "Record to" field doesn't say.
- **The live filename is stamped in UTC.** `timestampSuffix()` uses `Date.toISOString()`. A session started at 15:43 local time (UTC−6) was saved as `transcript_20260911_214334.txt`, while the engine's own stamps use local time.

The user chose: file transcripts next to the recording, live transcripts in the Documents folder with the full path shown, and local-time stamps.

## What Changes

- **File transcripts are saved next to the recording.** The GUI starts the file-transcription sidecar with its working directory set to the recording's folder. The engine already names the transcript `<name>_transcript_<stamp>.<format>` in its working directory, so the file lands beside the recording, and the CLI's behavior is unchanged.
- **Live transcripts default to the Documents folder.** "Record to" starts as the full path `<Documents>/transcript_<stamp>.txt`. A bare name typed into it is saved in Documents too, and Browse still picks any location. If the system reports no Documents folder, the home folder is used.
- **Live filenames use local time,** matching the engine's stamps.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `desktop-gui`: "Live session transcript is saved to a file" gains the default folder, the full-path display, and local-time stamps. A new requirement says file transcripts are saved next to the recording. It's added rather than modifying "File transcription via drag-and-drop", because the open change `fix-gui-file-queue-and-linux-live` already modifies that requirement.

## Impact

- **Changed**: `src/main.js` (the timestamp, the default live path, and resolving bare names against Documents) and `src-tauri/src/sidecar.rs` (the working directory for file runs).
- **Unchanged**: the CLI and its naming, the launchers, and Tauri permissions (`core:default` already includes the path API).
