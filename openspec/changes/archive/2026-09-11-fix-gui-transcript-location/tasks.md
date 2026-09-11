## 1. Implementation

- [x] 1.1 In `src/main.js`, build `timestampSuffix()` from local time (design.md Decision 3). Verify with `node --check src/main.js`, and check the stamp format against the regex in `withFreshTimestamp` (`_\d{8}_\d{6}$`).
- [x] 1.2 In `src/main.js`, fill "Record to" with `<Documents>/transcript_<stamp>.txt` (falling back to home), resolve a non-absolute value against the same folder at session start, and use the same default for Browse (design.md Decision 2). Verify with `node --check`, and by reading that `startLiveSession` now only sends absolute paths.
- [x] 1.3 In `start_file_transcription` (`src-tauri/src/sidecar.rs`), set the sidecar's `current_dir` to the dropped file's parent folder (design.md Decision 1). Verify that `cargo check` and `cargo test` pass in `src-tauri/` with no warnings.

## 2. Verification in the dev GUI (user, Fedora/KDE)

- [x] 2.1 Restart `cargo tauri dev`, then check each:
  - "Record to" shows a full path in Documents, with the current **local** time in its stamp.
  - A live session saves there.
  - Typing `standup.txt` and starting saves `Documents/standup_<stamp>.txt`.
  - Transcribing a file from `~/Downloads/…` writes `<name>_transcript_<stamp>.txt` next to it, and nothing new appears in `src-tauri/`.

  **Verified by the user 2026-09-11 (`cargo tauri dev`, Fedora/KDE): "All tests passed"**: the full Documents path with a local-time stamp, live saving there, a bare name resolved into Documents, and the file transcript written next to the recording.
