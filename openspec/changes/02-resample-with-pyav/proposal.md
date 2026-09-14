## Why

SciPy is bundled into every sidecar only for `scipy.signal.resample`, which converts live audio to 16 kHz. In the frozen Linux sidecar it is 24.4 MB compressed of 159 MB, the third-largest component after CTranslate2 and PyAV. Every AppImage, `.deb`, `.rpm`, Windows installer and zip, and macOS `.dmg` and zip carries it. PyAV is already bundled at 35.4 MB, and its `AudioResampler` wraps FFmpeg's libswresample, which does the same job.

It is also a small quality fix. The live workers resample each captured block on its own with an FFT method, which assumes every block is periodic and can leave artifacts at block edges. A stateful resampler carries the filter across blocks. A spike on 2026-09-14 confirmed:
- a 1 kHz tone at 48 kHz and 44.1 kHz, fed in 1,024-frame blocks, comes out at exactly 1,000 Hz with the exact expected sample count;
- a 3-frame block yields 0 samples without error and is carried into the next block.

Depends on `01-merge-dual-capture-paths`, which leaves one live resample spot instead of three.

## What Changes

- **Live dual capture resamples with one `av.AudioResampler` per worker** (system and mic), created on the first block from the source's real rate. This replaces the per-block `scipy.signal.resample`, and removes the zero-length guard that `01` generalised, since the resampler handles short blocks itself.
- **`_process_audio_chunk`**, used by the single-source `transcribe_live_simple` path, resamples each overlapping 10-second chunk with a fresh resampler that is flushed at the end. That matches today's one-chunk-at-a-time semantics.
- **SciPy is removed** from `requirements.txt`, `requirements-linux.txt` and `requirements-macos.txt`, and from `THIRD-PARTY-LICENSES.txt`.
- **A local resampling test** checks the frequency and the sample count.
- **Not in scope:**
  - Changing chunk sizes or the overlap.
  - File transcription, which faster-whisper already decodes and resamples through PyAV.
  - NumPy, which the engine itself needs.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
(none. Transcription behaviour and every spec'd output stay the same. The spec for 16 kHz conversion from each source's real rate is added by `01`. `skip_specs` is set.)

## Impact

- **Changed:**
  - `transcriber.py`: the resampling in `_run_dual_capture` and `_process_audio_chunk`, and the four `from scipy import signal` imports removed.
  - The three `requirements*.txt` files.
  - `THIRD-PARTY-LICENSES.txt`.
  - `build_sidecar.py`'s and `README.md`'s venv explanation, which names "numpy/scipy".
  - A new root test script.
- **Size:** each frozen sidecar is expected to shrink by about 24 MB compressed. Verified by listing the frozen archive.
- **Unchanged:** the engine, the GUI, the Rust sidecar, packaging scripts and CLI flags. `linux-sidecar-build`'s spec wording ("numpy/scipy are system packages") stays accurate as a description of those distributions, so it is not edited.
- **Verification:** the same hardware round as `01`: live sessions on Linux and Windows. macOS gets the CI smoke test only.
