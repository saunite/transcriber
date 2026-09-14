## Context

See proposal.md - Why. After `01`, SciPy is used in two places in `transcriber.py`:

- **`_run_dual_capture`'s worker transform.** It resamples every queued block from the source's rate to 16 kHz before buffering, and returns an empty array for a block too short to produce samples. Blocks from one source form a continuous stream, and each worker thread (system, mic) owns its own stream.
- **`_process_audio_chunk(..., sample_rate)`**, called by `transcribe_live_simple`. That path buffers native-rate audio, and on each 10-second chunk passes the whole chunk, including a 1-second overlap repeated from the previous chunk, to be resampled and transcribed. The dual workers call it with `sample_rate=16000`, which skips resampling.

Every capture source hands over mono float32 NumPy arrays in [-1, 1]. PyAV 18.1.0 is already a faster-whisper dependency and in every sidecar.

Spike results, 2026-09-14, PyAV 18.1.0:

```
 input            blocks      output samples   expected   1 kHz tone at
 3 s @ 48000 Hz   1024 each   48000            48000      1000.0 Hz
 3 s @ 44100 Hz   1024 each   48000            48000      1000.0 Hz
 3-frame block    1           0 (buffered, no error)
 10 s @ 44.1 kHz  1 + flush   160000           160000     8.8 ms (scipy: 9.5 ms)
```

The stateful resampler emits slightly fewer samples for the first block (filter warm-up) and releases 16 at the end on `resample(None)`.

## Goals / Non-Goals

**Goals:**
- No SciPy anywhere in the sidecar.
- Resampled audio that is at least as good as today's, with the same sample counts over a session.

**Non-Goals:**
- Changing chunk, overlap or gate parameters.
- Touching file transcription. faster-whisper's `decode_audio` already uses PyAV.

## Decisions

### 1. A stateful resampler per worker stream

The runner's transform becomes a small closure. On the first block it creates `av.AudioResampler(format="flt", layout="mono", rate=16000)`, reading the source rate from `sys_rate()` or the mic's rate as `01` does. It wraps each block with `av.AudioFrame.from_ndarray(block[None, :], format="flt", layout="mono")`, sets `sample_rate`, and concatenates the `to_ndarray()[0]` of every returned frame. When the rate is already 16 kHz, the transform stays `None`, as today.

- **The zero-length guard from `01` is deleted.** A short block just returns an empty array while the resampler holds its samples.
- **No flush on stop.** The final 16 samples (1 ms) are dropped, which is the same outcome as today's partial buffer at shutdown.

**Rejected: `np.interp` linear interpolation.** No new dependency, but no anti-aliasing filter. Content above 8 kHz in 48 kHz system audio would fold into the speech band.

**Rejected: `scipy.signal.resample_poly`.** Better at block edges than the FFT method, but it keeps SciPy, which is the point of the change.

**Rejected: `faster_whisper.audio.decode_audio`.** It takes files and byte streams, not in-memory NumPy blocks at an arbitrary rate.

### 2. A fresh, flushed resampler per chunk in `_process_audio_chunk`

Chunks passed here overlap by 1 second, so one continuous resampler would be fed the same audio twice. Each call creates a resampler, resamples the chunk, and flushes with `resample(None)`, giving exactly `len * 16000 / rate` samples. That keeps today's stateless semantics, at the same cost as SciPy per the spike.

One helper, used by both Decision 1 and 2, keeps the frame wrapping in one place:

```python
def _resample(resampler, block, rate, flush=False) -> np.ndarray
```

### 3. Remove SciPy from the dependency lists and notices

- Delete `scipy>=1.10.0` from all three `requirements*.txt`, and SciPy's line from `THIRD-PARTY-LICENSES.txt`.
- Change `build_sidecar.py`'s virtualenv error and README's venv paragraph from "numpy/scipy" to "numpy". NumPy is still the package that links FlexiBLAS on Fedora, so the advice stands.

The frozen sidecar must then contain no `scipy` entries. PyInstaller only bundles what is imported, and none of faster-whisper, CTranslate2, ONNX Runtime, tokenizers, huggingface-hub or sounddevice imports SciPy. A task checks the archive listing rather than assuming.

## Risks / Trade-offs

- **[Risk]** A transitive dependency imports SciPy optionally, so the freeze still bundles it. → The archive-listing check catches it, and it can be excluded in `transcriber-sidecar.spec`.
- **[Risk]** The resampler's warm-up means the first system and mic blocks carry a few milliseconds less audio. → That's under one block at the start of a session, before any 10-second chunk is transcribed. Session sample counts match within the 16-sample flush.
- **[Risk]** A capture reports a rate that changes mid-session. PyAV rejects a frame whose rate differs from the resampler's configuration. → No source changes rate during a session: WASAPI, Core Audio and parec rates are fixed once opened. A change would surface as a transcription error on that worker, which is logged, not a crash of the session.
- **[Trade-off]** The frame wrapping is a few more lines than `signal.resample(x, n)`. It removes a 24 MB dependency from every artifact.
