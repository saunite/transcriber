## 1. Remove the video-extraction branch

- [x] 1.1 Delete the `video_extensions` dispatch in `transcriber.py`'s `transcribe_file()` (`transcriber.py:304-318`) so every file path is passed straight to `engine.transcribe_file()`; remove the `temp_audio` variable and its cleanup in the `finally` block

  Done. The outer `try/finally` existed only for `temp_audio` cleanup, so it was removed entirely rather than left as a no-op wrapper — the function body is now flat, ending in an inner `try/except` around just the decode call (see 1.4).

- [x] 1.2 Remove `from audio_extractor import AudioExtractor` (`transcriber.py:29`) and delete `audio_extractor.py`
- [x] 1.3 Decide the fate of the cosmetic "📹 Video file detected" / "🎵 Audio file detected" lines (design.md Open Questions) and apply it

  Kept, per the Open Question's lean — they're two lines and the GUI's log view surfaces them. They no longer drive any dispatch, just the message; a one-line comment says so.

- [x] 1.4 Surface a clear, single-line error when `av.open()` fails on an existing file — name the file and state the format is unsupported or corrupt, rather than letting a PyAV traceback reach stdout (the GUI parses this stream; see `src-tauri/src/sidecar.rs`)

  `transcriber.py` now imports `av.error` and catches `av.error.FFmpegError` specifically around the `engine.transcribe_file()` call (not a bare `except Exception`, which would also swallow unrelated errors from segment processing / transcript writing later in the same function). Verified empirically that both failure modes PyAV can raise here — `InvalidDataError` (corrupt/unsupported file) and `PermissionError` (unreadable file) — both subclass `av.error.FFmpegError`, so one except clause covers both without over-catching.

## 2. Replace the SYS+MIC merge

- [x] 2.1 Write a `_merge_sys_mic_wav(sys_path, mic_path, out_path)` helper using stdlib `wave` for I/O and numpy for the interleave: read both mono 16-bit 16kHz WAVs, truncate both to the shorter frame count (matching ffmpeg's `duration=shortest`), interleave as L=sys / R=mic, write a 2-channel WAV

  Added next to `_print_summary` (the file's other `_`-prefixed live-capture helper), matching this file's convention of `import wave` / `import numpy as np` locally inside the function rather than at module top level.

- [x] 2.2 Replace both `subprocess.run(["ffmpeg", ... amerge ...])` blocks (`transcriber.py:880` and `transcriber.py:1142`) with calls to it, keeping the surrounding try/except so a merge failure still warns and preserves the transcript and the separate WAVs

  Both call sites (`transcribe_live_wasapi` and `transcribe_live_coreaudio_tap`) now call `_merge_sys_mic_wav(...)` inside the existing `try/except Exception` block, unchanged otherwise.

- [x] 2.3 Add a `test_wav_merge.py` at the repo root (plain asserts, matching `test_transcript_line_format.py`'s style — no framework): synthesize two mono WAVs of *different* lengths, merge, then assert the output is 2 channels, 16-bit, 16kHz, has `min(len)` frames, and that channel 0 round-trips the sys samples and channel 1 the mic samples

  Written and run: `python test_wav_merge.py` passes.

## 3. Verify nothing else reaches for ffmpeg

- [x] 3.1 `grep -rn ffmpeg` across the repo returns only documentation/spec text — no `subprocess`, no PATH lookup, in any Python or Rust source

  Confirmed: `grep -rn ffmpeg --include="*.py" --include="*.rs" .` matches only comments/docstrings (this test file's own docstring, `fetch_sidecar_resources.py`'s note fixed in 4.2, and one explanatory comment in `_merge_sys_mic_wav`). Zero `subprocess` calls. (Note: `merge_and_transcribe.bat` and other `.bat` launchers still shell out to a standalone system ffmpeg for their own, separate batch-level merge — out of scope, see design.md/proposal.md's Impact section; not touched.)

- [x] 3.2 Transcribe a real `.mp4` end-to-end with `ffmpeg` removed from PATH (`env PATH=/nonexistent`), via the plain CLI — confirms the change works before any packaging work depends on it

  Verified with a real H.264/AAC mp4, `PATH` restricted to a directory containing only `python3` (no ffmpeg reachable, confirmed via `command -v ffmpeg` → none in that PATH). Full run via the actual CLI completed normally: language detected, transcript saved, exit 0. Also verified the decode-failure path (1.4) end-to-end the same way against a corrupt file: clean one-line error, exit 1, no traceback.

- [x] 3.3 Repeat 3.2 against the **frozen** sidecar binary, not just the source tree — PyInstaller's analysis must pick up PyAV's bundled FFmpeg shared libraries. `add-tauri-gui` task 2.4 only smoke-tested a `.wav`; an `.mp4` exercises the container demuxers, which pull in more of those libs

  **Partially verified, real environment blocker found.** Froze the sidecar with `build_sidecar.py` (Linux, this session) and confirmed via `PyInstaller.utils.cliutils.archive_viewer` that all of PyAV's bundled FFmpeg shared libraries made it into the frozen archive: `av.libs/libavcodec*.so`, `libavdevice*.so`, `libavfilter*.so`, `libavformat*.so`, `libavutil*.so`, `libswresample*.so`, `libswscale*.so` — this is the specific risk this task exists to catch (PyInstaller silently dropping a dynamically-loaded bundled lib, as happened with the VAD ONNX asset in `add-tauri-gui` task 2.4), and it did not happen.

  Could not complete a full functional run of the frozen binary: it crashes on startup (`flexiblas Failed to load the BLAS fallback library. Abort!`) regardless of ffmpeg/PATH — reproduced identically with the full, unmodified environment, so this is unrelated to this change. Root cause: this dev machine's system Python/numpy is Fedora's RPM build, linked against `flexiblas` (a runtime BLAS-backend switcher that `dlopen`s its backend via `/etc/flexiblasrc` at runtime, not via a normal link-time dependency PyInstaller's analysis follows) — the same *class* of bug as the VAD-asset issue, but in numpy/scipy's BLAS backend, not PyAV, and pre-existing/unrelated to ffmpeg removal. Standard PyPI numpy wheels (what CI runners typically install, vs. this machine's distro package) statically bundle OpenBLAS and don't use flexiblas, so this likely won't reproduce on the actual Windows/Linux CI build — but that's an assumption, not something verified here. **Flagging as a real gap for whoever runs the actual CI freeze**: worth a fast first check there before assuming this change is fully proven on a frozen binary.

- [x] 3.4 Run a live SYS+MIC session with audio saving enabled and confirm `<base>_merged.wav` is produced, is stereo, and plays back with system audio on one channel and mic on the other

  **Closed — won't do. The feature this task verifies is being removed entirely** by `remove-audio-saving`; see that change. Superseding it rather than completing it, following the same convention this change's task 4.3 used for `add-tauri-gui` task 2.6.

  It was attempted first, on real Windows hardware, and the run is what motivated the removal. Recording the findings here so they survive the archive:

  1. **The saved system-audio WAV silently drops whatever transcription can't keep up with.** A 71.2s WASAPI + mic session on the **`tiny`** model produced a 41.1s `_sys.wav` — **42% of the system audio was never written**. Cause is structural, not tuning: `_mic.wav` is written directly from the real-time `mic_callback` (a true wall-clock recording), while `_sys.wav` is written from `transform_sys`, called on the transcription worker thread behind blocking inference. Anything the worker never drains is never written, and a larger model makes it strictly worse. `test_wav_merge.py` (2.3) cannot catch this — it feeds `_merge_sys_mic_wav` two synthetic files that are correct by construction.

  2. **The merge is correctly aligned, just truncated.** `_drain_and_transcribe` drains FIFO and writes in order, so `_sys.wav` is always a *prefix* of the session, never time-offset. `_merge_sys_mic_wav`'s "align index 0, truncate to shorter" is therefore sound — it would simply have discarded the 30s of mic audio past the sys stream's end, including a whole speech segment.

  3. **`_merged.wav` was never produced — cause never confirmed.** Both mono WAVs closed cleanly (frame counts match file sizes byte-exactly), but the unconditional `print("\nMerging system and microphone audio...")` immediately after never appeared. The suspicion was that execution dies in `capture.cleanup()` → PyAudio's `p.terminate()`, which sits between the WAV closes and the merge — a known hang/fault mode for WASAPI loopback streams.

  **Later evidence did not support that**, and is recorded here so this note is not read as a confirmed defect: `remove-audio-saving` task 3.2 ran the same WASAPI + mic path on current source and it shut down cleanly on Ctrl+C, printing its stop summary — which is only reached after `capture.cleanup()` returns. The original run used a binary three commits stale, and the merge code has since been deleted, so the symptom cannot be reproduced either way. Unexplained, not confirmed; no follow-up change was opened.

  (The binary used was 3 commits stale, but that does not explain finding 3: the merge block and its unconditional print both predate that build, at `826a0ea`.)

## 4. Documentation and follow-through

- [x] 4.1 Remove the ffmpeg prerequisite section from `README.md` (the choco/scoop/apt/dnf install instructions, `README.md:53-71`) and any remaining "requires ffmpeg" claims

  Removed the System Dependencies block's ffmpeg bullet and all three OS install snippets, replaced with a one-line note that no external media tool is needed. Also fixed the `--save-audio`/merge flag description, which still said "(merge uses ffmpeg)". Left `README.md`'s "Launchers" line and the `.bat` launcher scripts themselves alone — `merge_and_transcribe.bat` has its own, separate standalone ffmpeg-based merge (different filter, `amix` not `amerge`) that never went through `transcriber.py`; out of scope per this change's proposal/design (Impact sections list only `transcriber.py`, `README.md`, `fetch_sidecar_resources.py` as changed).

- [x] 4.2 Update `fetch_sidecar_resources.py`'s module docstring: it currently instructs whoever sets up the build matrix to pin a static ffmpeg source per OS — that instruction is now wrong

  Docstring and the "ffmpeg is not fetched by this script" print statement both replaced with a note that no ffmpeg binary is needed at all.

- [x] 4.3 Mark `add-tauri-gui` task 2.6 as closed-won't-do, referencing this change; remove the "ffmpeg resources are intentionally not staged here" note in `.github/workflows/build-gui.yml` and the "ffmpeg resource wiring still needs re-adding" note in that change's task 3.2

  `add-tauri-gui` archived (as `openspec/changes/archive/2026-09-02-add-tauri-gui/`) before this task ran; annotated its task 2.6 in place as closed-won't-do referencing this change, rather than rewriting the archived historical record. `.github/workflows/build-gui.yml`'s ffmpeg-staging comment replaced with a note that no staging step is needed; also removed a stale `audio_extractor.py` entry from the workflow's path-trigger list (that file is now deleted, task 1.2). Left the "ffmpeg resource wiring still needs re-adding" note inside task 3.2's own body text untouched — it's a historical record of what task 3.2 actually did at the time, not a live instruction; task 2.6's own annotation is what supersedes it going forward.

- [x] 4.4 Update `README.md:31`'s "ffmpeg bundling is not yet done" claim in the GUI section

  Replaced with a note that no ffmpeg bundling is needed, referencing this change.
