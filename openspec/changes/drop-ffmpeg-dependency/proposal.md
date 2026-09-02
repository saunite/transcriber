## Why

The GUI is meant to ship as a self-contained artifact a user can run with nothing else installed (`add-tauri-gui`'s "Fully offline first run"). Today it can't: `add-tauri-gui` task 2.6 is still open because no static ffmpeg binary has been bundled, so a user without ffmpeg on PATH gets a hard failure on any video file.

Bundling ffmpeg (~80-100MB per OS, plus picking and pinning a trustworthy static build source per platform — the exact reason 2.6 stalled) turns out to be unnecessary. `faster-whisper` already depends on **PyAV**, whose wheels ship FFmpeg's libraries compiled in, and its `decode_audio()` calls `av.open()` + `container.decode(audio=0)` — a full container demux that handles mp4/mkv/mov/webm directly. Verified empirically on a real mp4 with `PATH` emptied:

```
$ env -i PATH=/nonexistent python3 -c "from faster_whisper.audio import decode_audio; ..."
decoded mp4 without any ffmpeg binary on PATH: (32322,) float32
```

So `transcriber.py`'s video branch shells out to an external ffmpeg to produce a temp WAV that the engine would have decoded itself. It is a decode-then-re-encode round trip that adds a hard dependency, a temp file, and a failure mode, and buys nothing.

Removing it closes task 2.6 by deletion rather than by adding 100MB per platform.

## What Changes

- **Delete the video-extraction branch.** `transcriber.py`'s `transcribe_file()` no longer special-cases video extensions; every file path goes straight to `TranscriptionEngine.transcribe_file()`, which decodes via PyAV. `audio_extractor.py` and its `AudioExtractor` import are deleted along with the temp-file creation/cleanup they existed to manage.
- **Replace the SYS+MIC merge with stdlib.** The two `subprocess.run(["ffmpeg", ... amerge ...])` call sites (`transcriber.py:880` and `:1142`) become a small helper that reads both mono 16-bit 16kHz WAVs with the `wave` module (already used throughout this file to *write* them), interleaves the frames with numpy (already a dependency), and writes a stereo WAV. Same output file, same `<base>_merged.wav` name, no external process.
- **Error handling moves, it doesn't disappear.** A file the decoder genuinely cannot open must still produce a clear, user-facing error — it just comes from the decode attempt rather than from a pre-flight `ffmpeg -version` check.
- After this change, no code path in the repo invokes an external `ffmpeg` binary. `add-tauri-gui` task 2.6 (bundle a static ffmpeg per OS) is closed as won't-do.

## Capabilities

### Modified Capabilities
- `audio-extraction`: the capability's three requirements (extract via ffmpeg, validate ffmpeg availability, clean up temp audio) are all removed — the behavior they describe ceases to exist. Media decoding moves into `transcription`.
- `transcription`: gains an explicit requirement that the system accepts audio *and* video files and decodes them with the bundled decoder library, requiring no external media tool.
- `audio-capture`: "Save captured audio to WAV" no longer specifies ffmpeg as the merge mechanism; the merge is now unconditional (it can't be skipped for a missing binary).
- `desktop-gui` (from the in-flight `add-tauri-gui` change): "Fully offline first run" no longer cites a bundled ffmpeg binary.
- `documentation`: README's ffmpeg install instructions (choco/scoop/apt/dnf) are removed from the prerequisites.

## Impact

- **Deleted**: `audio_extractor.py` (~95 lines), the video branch in `transcriber.py`, both ffmpeg `subprocess` merge blocks, README's ffmpeg install section.
- **Changed**: `transcriber.py` (`transcribe_file()`, plus the two live-capture merge sites), `README.md`, `fetch_sidecar_resources.py`'s ffmpeg docstring note.
- **Unchanged**: `transcription_engine.py`, `audio_capture.py`, `wasapi_capture.py`, `macos_capture.py`, all Tauri/Rust code, `requirements*.txt` (PyAV arrives transitively via `faster-whisper` and is already frozen into the sidecar — task 2.4's smoke test decoded a WAV through it successfully).
- **Net line count**: negative. This is a deletion, not a feature.
- **Side benefit on Windows**: both ffmpeg call sites use plain `subprocess.run` with no creation flags, from a sidecar that itself has no console (`tauri-plugin-shell` spawns it with `CREATE_NO_WINDOW`). Windows allocates a *new* console for a console-subsystem child of a console-less process, so each merge would flash a console window mid-session. Deleting these call sites removes that; see `remove-installer-packaging`'s design.md Decision 5.
- **Behavioral risk**: PyAV's format coverage vs. the system ffmpeg's. PyAV bundles a full FFmpeg build, so the common containers are covered, but an exotic input that a distro ffmpeg handled could now fail. See design.md.

## Ordering

Apply this change **before** `remove-installer-packaging`. That change ships one no-install artifact per OS; until this one lands, that artifact still hard-fails on any video file because `add-tauri-gui` task 2.6 (bundle a static ffmpeg) was never done. Nothing here depends on packaging work, and all of it is verifiable from the plain CLI with no Rust toolchain or Docker build.

(`add-tauri-gui` has since archived, so this change's `desktop-gui` delta is a normal MODIFIED diff against `openspec/specs/desktop-gui/spec.md` directly.)
