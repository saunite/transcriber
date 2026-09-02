## Context

`add-tauri-gui` task 2.6 ("Bundle a static ffmpeg binary into installer resources per OS") has been open since the change was written, deliberately: there is no single unambiguous official static-ffmpeg source to hardcode per platform, and guessing a download URL risked wiring in something unmaintained. `fetch_sidecar_resources.py`'s docstring flags this for whoever sets up the build matrix.

While scoping the portable-artifact work (`remove-installer-packaging`), the actual ffmpeg surface got measured rather than assumed:

| Flow | External `ffmpeg` binary required? |
|---|---|
| Live capture → transcript | No |
| File: `.mp3 .wav .flac .m4a .ogg .opus .wma` | No — decoded by PyAV |
| File: unrecognized extension | No — falls through to the engine → PyAV |
| File: `.mp4 .mkv .mov .webm .avi .wmv .flv .m4v` | **Yes — hard failure** |
| Live SYS+MIC merged WAV | Yes, but soft (caught, warned, transcript still saved) |

Only one row is a real break, and it is self-inflicted: `transcriber.py:304-318` checks the extension against a video set and routes to `AudioExtractor`, which raises `FileNotFoundError("ffmpeg is not installed or not in PATH")` before `TranscriptionEngine` is ever reached — for a file the engine would have opened fine.

`faster_whisper.audio.decode_audio()` is:

```python
with av.open(input_file, mode="r", metadata_errors="ignore") as container:
    frames = container.decode(audio=0)
```

`av.open()` demuxes any container FFmpeg's libraries support; `audio=0` selects the first audio stream. PyAV's wheels statically bundle those libraries — no binary on PATH. Verified on this machine against a real H.264/AAC mp4 with the environment stripped:

```
$ env -i PATH=/nonexistent HOME=$HOME python3 -c \
    "from faster_whisper.audio import decode_audio; a=decode_audio('t.mp4'); print(a.shape)"
(32322,)   # shutil.which("ffmpeg") -> None
```

## Goals / Non-Goals

**Goals:**
- No code path in the repo invokes an external `ffmpeg` process.
- Video files transcribe with nothing installed beyond the app itself.
- Task 2.6 closes as won't-do; a self-contained portable artifact stops depending on an unshipped bundling step.
- Net negative diff.

**Non-Goals:**
- Removing PyAV, or vendoring a decoder. PyAV is already there, transitively, and already frozen into the sidecar.
- Changing transcript output, timestamps, or WAV-saving behavior.
- Changing the transcription engine's own decode path — it already does the right thing; this change stops working around it.

## Decisions

### 1. Delete the video branch entirely rather than making ffmpeg optional

The tempting smaller change is "try ffmpeg, fall back to PyAV". Rejected: it keeps `audio_extractor.py`, keeps the temp-file lifecycle, keeps a second decode implementation to reason about, and leaves two code paths that produce subtly different audio (the ffmpeg path re-encodes to 16kHz mono PCM first; PyAV resamples in-process to the same target). One path is the whole point.

`transcribe_file()` keeps its extension sets only for the cosmetic "📹 Video file detected" / "🎵 Audio file detected" log lines, or drops them too. Either is fine; the dispatch behind them goes away.

**Consequence for error messages**: today an unopenable file fails at a pre-flight `ffmpeg -version` check with a friendly install hint. After this change it fails when `av.open()` raises. The engine's `transcribe_file()` already guards `Path(audio_path).exists()`; a decode failure on an existing file needs to surface as a clear "could not decode <file> — unsupported or corrupt media" rather than a raw PyAV traceback, especially since the GUI parses sidecar stdout. This is in scope (task 1.4).

### 2. SYS+MIC merge: stdlib `wave` + numpy, not ffmpeg, and not scipy

Both inputs are files this same code just wrote: mono, 16-bit, 16kHz, via `wave.open(..., 'wb')` (`transcriber.py:730`, `:737`, `:995`, `:1002`). Merging them is reading two frame buffers, interleaving L/R, and writing a 2-channel WAV — `wave` for I/O (already imported in each of these functions), numpy for the interleave (already a dependency). Roughly ten lines, replacing a subprocess, a filter graph string, and a try/except around a missing binary.

`scipy.io.wavfile` would also work and scipy is already in `requirements.txt`, but `wave` is what this file already uses for the two inputs and stdlib beats a dependency at equal size.

**Duration mismatch**: ffmpeg's `amerge=duration=shortest` trimmed to the shorter input. The replacement must do the same explicitly — truncate both to `min(len)` before interleaving — because SYS and MIC streams start and stop at slightly different times and a naive zip would silently misalign or crash.

**Behavior change**: the merge can no longer be skipped for a missing binary. The "Merge without ffmpeg" scenario in the `audio-capture` spec stops being reachable and is removed. Genuine I/O errors are still caught and warned about, preserving the existing "never lose the transcript over a merge failure" property.

### 3. Do not add PyAV to `requirements.txt`

It is a `faster-whisper` dependency; pinning it directly would mean maintaining a version constraint against a transitive we do not control. The frozen sidecar already includes it — `add-tauri-gui` task 2.4 smoke-tested `--file` on the Windows build and PyAV decoded it, so PyInstaller's analysis picks it up without a hook.

Worth one verification anyway (task 3.2): the earlier smoke test used a `.wav`. A frozen-binary test on an `.mp4` exercises PyAV's container demuxers, which pull in more of the bundled FFmpeg libs than raw PCM does.

## Risks / Trade-offs

- **[Risk]** PyAV's bundled FFmpeg build may lack a codec a distro's full ffmpeg had. Realistically this affects exotic inputs, not the mp4/mkv/mov/webm meeting recordings this tool exists for. **Mitigation**: task 1.4's clear decode-failure message names the file and says the format is unsupported, which is actionable (convert it) rather than mysterious. Accepted; the alternative is shipping 100MB per platform to cover a case nobody has hit.
- **[Risk]** Non-obvious regression in the merged WAV (channel order, endianness, truncation) that only shows up on listening, since nothing asserts on merge output today. **Mitigation**: task 2.3 — a round-trip assertion test on synthetic WAVs. Cheap, and this is exactly the "non-trivial logic leaves one runnable check behind" case.
- **[Trade-off]** Losing the pre-flight availability check means failures surface later in the run. For file transcription this is nearly instant (decode is the first thing that happens), so the practical difference is small.

## Open Questions

- Should the cosmetic "📹 Video file detected" / "🎵 Audio file detected" lines survive? They are the only remaining consumer of the extension sets. Leaning keep — they cost two lines and the GUI's log view shows them — but dropping the sets entirely is the smaller diff.
- `test_transcript_line_format.py` and the other `test_*.py` files at the repo root are the existing test convention (plain asserts, no framework). Task 2.3's merge test should follow that; confirm nothing in CI expects otherwise.
