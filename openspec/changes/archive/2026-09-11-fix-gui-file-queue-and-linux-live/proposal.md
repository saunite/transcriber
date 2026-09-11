## Why

Installing the `v0.1.0` `.rpm` on Fedora/KDE (`01-add-release-pipeline` task 5.2) exposed two GUI bugs that predate the packaging work:

- **Dropping a file while another is transcribing starts a second run.** `transcribeFile()` sets a `fileBusy` flag but never checks it, and each call spawns a new, untracked sidecar. The only busy sign is a small "Transcribing" dot, so the user can't tell anything is happening.
- **Live capture from the GUI fails on Linux** with `❌ --wasapi is only supported on Windows`, because `build_live_session_args()` always passes `--wasapi`. A `ponytail:` note there recorded this shortcut, and only macOS is gated off in the UI, so GUI live capture has never worked on Linux.

The user chose a queue for dropped files: accept any number of files and transcribe them one at a time, showing which is running and which are waiting. Refusing drops while busy was the other option.

## What Changes

- **File queue in the GUI.** Dropped or chosen files join a visible queue and are transcribed one after another. Each entry shows its state (waiting, transcribing, done, failed), and the running file is named in the File panel's status. Multiple files can be dropped at once, or picked at once in the file dialog. Unsupported files are rejected with a note and never queued.
- **Live capture passes the running platform's capture flag:** `--wasapi` on Windows, `--coreaudio-tap` on macOS (dormant while macOS live capture stays disabled in the GUI), and nothing on Linux, whose default `--live` path already does system audio plus microphone.
- **The device-override hint stops saying "WASAPI"** on every platform; it says "auto-detected system-audio device".

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `desktop-gui`: "File transcription via drag-and-drop" gains queue behavior, and a new requirement says a live session uses the running platform's capture mode.

## Impact

- **Changed**: `src/main.js` (the queue, and multi-file drop and pick), `src/index.html` (queue list, device-hint wording), `src/*.css` (queue list style), and `src-tauri/src/sidecar.rs` (the per-platform flag in `build_live_session_args()`, plus a unit test).
- **Unchanged**: the sidecar CLI and `transcriber.py`. Every flag used already exists, and the Linux `--live` path works from the command line today.
- **Platform split:** the live-capture fix is one function choosing a flag per OS, not a separate implementation per platform, so per the project's split rule it stays a single change. Linux is the only platform where the change is visible now: Windows already passed `--wasapi`, and macOS live capture is disabled.
- **Found through**: `01-add-release-pipeline` task 5.2, which still owns the packaging problems from the same test.
