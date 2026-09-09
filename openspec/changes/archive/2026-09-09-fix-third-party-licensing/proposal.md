# Fix third-party licensing disclosure

## Why

`drop-ffmpeg-dependency` changed what this project distributes, and the licensing paperwork was never updated to match. Before it, users installed ffmpeg themselves and the project redistributed no FFmpeg code at all — `LICENSE`'s note that *"FFmpeg must be installed separately on the system"* was accurate. After it, FFmpeg's libraries ship **inside** `transcriber-sidecar.exe` via PyAV's bundled wheels, which makes this project a redistributor of GPL code with obligations it does not currently meet.

Verified against the actual shipped binary: `avcodec` load-time-imports `libx264` and `libx265`, both **GPL-2.0-or-later only**, so the bundled FFmpeg is a `--enable-gpl` build, not LGPL. `libopencore-amrnb/amrwb` and `libgmp` additionally imply `--enable-version3`, making the effective license of the distributed binary **GPLv3**. Meanwhile the bundled Whisper weights are MIT but ship with no notice, and the README still claims the project is plain "GPLv2" while naming only faster-whisper among its dependencies.

Nothing here is a license *conflict* — the project is GPL-2.0-or-later, so GPL FFmpeg is compatible and the "or later" clause covers the GPLv3 components. The gap is disclosure and obligations. There are currently zero releases, so no distribution has occurred and none of these obligations have yet been triggered; fixing it before the first release avoids remediating after the fact.

## What Changes

- Rewrite `LICENSE`'s "Third-Party Components" section to describe what is actually bundled: PyAV's FFmpeg libraries (GPL, with x264/x265), the Whisper model weights (MIT, OpenAI + Systran), CTranslate2, ONNX Runtime, numpy/scipy, sounddevice/PortAudio, pyaudiowpatch, tqdm, the Tauri/Rust stack, and `WebView2Loader.dll`. Remove the false "must be installed separately" note.
- Satisfy the corresponding-source obligation for the bundled GPL components (FFmpeg, x264, x265) under GPLv3 §6(d), by publishing maintained directions to their upstream source rather than attaching archives or making a written offer — see `design.md` decision 3. This requires first determining which upstream versions PyAV 16.0.1 actually built.
- Add a `THIRD-PARTY-LICENSES.txt` and ship it **inside** the distributed artifact, so a user who extracts the zip can see the notices. This requires a `build_portable.py` change, not just a doc edit.
- Ship the MIT notice and attribution for the bundled model alongside it in `resources/model/`.
- Correct `README.md`'s License section: it says "GPLv2" and names only faster-whisper. It should state the effective license of the distributed binary and point at `LICENSE` for the full component list.

### Explicitly not in scope

- **Do not attempt to strip the unused encoders.** `libx264`/`libx265` are load-time imports of `avcodec`, not `dlopen`ed — deleting them makes `avcodec` unloadable, which breaks `import av`, which breaks faster-whisper at `audio.py:15`, which breaks the whole app including live capture. Escaping GPL would mean building a custom FFmpeg and compiling PyAV from source against it, per platform, forever. See `design.md`.
- **Do not relicense the project.** GPL-2.0-or-later stays.
- **Do not audit transitive Rust crate licenses individually.** The Tauri/Rust stack is MIT/Apache-2.0 and compatible under the "or later" clause; an exhaustive per-crate audit is a separate exercise if ever wanted.
- **Do not remove `resources/model/.cache/huggingface/`** (32 KB of download metadata that ships by accident). Harmless, and unrelated to licensing.

## Capabilities

### New Capabilities

- `licensing` — the obligations attached to what this project redistributes: notices shipped with artifacts, reachable corresponding source for bundled GPL components, and project license statements that match reality.

### Modified Capabilities

None. `documentation`'s purpose is README/command sync; licensing statements are a distinct concern and live in the new capability, including the README's License section.

## Impact

- `LICENSE` — third-party section rewritten; the false "installed separately" note removed.
- `THIRD-PARTY-LICENSES.txt` — new file at repo root.
- `SOURCE-PROVENANCE.txt` — new file recording `av==16.0.1`, the bundled library versions, the FFmpeg configure string, and a verified-resolving upstream source URL for each GPL component. Ships with the artifact.
- Release procedure — documented to include re-checking that those source links resolve, plus the standing duty to fix or rehost any that stop resolving.
- `build_portable.py` — must copy the notices file into the assembled artifact for every platform.
- `README.md` — License section corrected.
- `src-tauri/resources/model/` — model notice file added; `tauri.conf.json` already bundles this directory, so it travels with the app.
- No source-code behavior changes. Nothing about transcription, capture, or the GUI is affected.
