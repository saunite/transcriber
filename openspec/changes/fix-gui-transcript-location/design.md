## Context

See proposal.md - Why. The relevant code:

- **`src/main.js`**:
  - `timestampSuffix()` returns `toISOString()` digits, so UTC.
  - `defaultOutputFilename()` returns the bare `transcript_<stamp>.txt`, which fills "Record to" at load.
  - Session start sends `withFreshTimestamp(value || "transcript.txt")` as `outputPath`.
- **`src-tauri/src/sidecar.rs`**: `start_file_transcription` passes `--file <path>` with no `--output`, and never sets `current_dir`. `transcriber.py` then writes `Path.cwd() / f"{stem}_transcript_{stamp}.{format}"`.
- **Available tools:** `tauri-plugin-shell` 2.3.6 has `Command::current_dir()`. The capability `core:default` already grants the path API (`documentDir`, `homeDir`, `join`, `isAbsolute`) through `window.__TAURI__.path`.

## Goals / Non-Goals

**Goals:**
- A transcript is never written to a surprise location, and the live location is visible before the session starts.

**Non-Goals:**
- Changing where the CLI writes; it stays the current directory.
- Creating a missing Documents folder, or a Transcriber subfolder.
- Remembering the last browsed folder between app runs.

## Decisions

### 1. File mode: set the sidecar's working directory to the recording's folder

`start_file_transcription` takes the dropped path's parent (when non-empty) and calls `.current_dir(parent)` on the sidecar command. The engine's existing default does the rest: its naming and timestamp stay the single source of truth.

- **Rejected: the GUI computing `--output <dir>/<stem>_transcript_<stamp>.<fmt>`.** It would duplicate the engine's naming and stamp format in JavaScript.
- **Rejected: changing the engine's file-mode default to "next to the input".** That changes the CLI, which the user didn't ask for.

The model path is already absolute (`resolve_model_dir()`), and dropped paths are absolute, so nothing else depends on the working directory.

### 2. Live mode: a full default path in Documents, and bare names resolved there too

At load, "Record to" is filled asynchronously with `join(<Documents>, "transcript_<stamp>.txt")`. If `documentDir()` rejects, `homeDir()` is used. At session start, a value that isn't `isAbsolute` is joined onto the same folder before `withFreshTimestamp`, so a typed `standup.txt` lands in Documents rather than the engine's working directory. Browse's default path is the field's value or the same default. `withFreshTimestamp` already works on full paths: it re-stamps the part before the last `.`.

**Rejected: setting the live sidecar's working directory to Documents and keeping bare names.** The field would still show a bare, location-less name, and the user asked to see the full path.

### 3. Local-time stamp

`timestampSuffix()` builds `YYYYMMDD_HHMMSS` from local `Date` getters, padded with `padStart`. That's the same shape as before, so `withFreshTimestamp`'s `_\d{8}_\d{6}$` strip still matches, and it's the same clock the engine uses.

## Risks / Trade-offs

- **[Risk]** On Linux the XDG Documents directory can be configured but not exist, in which case the engine can't open the file → the session fails with the engine's open error, visible in the log. Creating the folder is left out (Non-Goals); the user can Browse elsewhere. Most desktops create it at first login.
- **[Trade-off]** Transcribing a recording from a read-only folder (for example a mounted camera card) fails to save, because the transcript goes next to the recording. The engine reports the write error. Choosing a different folder for file mode can come later if it's ever needed.
