## Context

See proposal.md - Why. The three functions today, in order, all in `transcriber.py`:

```
 preamble (per platform)            shared core (copied 3x)
 +----------------------------+     +-------------------------------------------+
 | find sys source            |     | all_segments, queues, stop_event, lock    |
 | mic: query, channels, rate |     | output file + "# Live Transcription (...)"|
 | print compact status +     | --> | mic_callback, sys callback (silence check)|
 |   "Listening..." line      |     | _emit, _drain_and_transcribe(transform)   |
 +----------------------------+     | start sys/mic threads, run capture        |
                                    | finally: stop, join, close, cleanup       |
                                    | _print_summary / _print_compact_stop      |
                                    +-------------------------------------------+
```

What actually differs, found by diffing the three:

| | Linux dual | WASAPI | Core Audio tap |
|---|---|---|---|
| System source | `LinuxLoopbackCapture` (parec, blocking `capture_stream`) **or**, with `--audio-device`, `sd.InputStream` plus a poll loop | `WASAPICapture.capture_stream`, blocking | `MacOSCapture.capture_stream`, blocking |
| System rate | 16000 (parec resamples) or the device's default | hardcoded 48000, **wrong when the device isn't 48 kHz** | `capture.sample_rate`, known only after the helper's header arrives |
| Mic | always included; 16 kHz, else native rate | optional; always 16 kHz | optional; always 16 kHz |
| Silence timeout | in the parec callback, or in the poll loop | in the capture callback | in the capture callback |
| Output header | `(System Audio + Microphone)` | `(WASAPI Loopback[ + Microphone])` | `(Core Audio Process Tap[ + Microphone])` |
| Extra errors | none | none | `UnsupportedMacOSVersionError`, `AudioCapturePermissionError`, `MacOSCaptureError` → exit 1 |
| Zero-length resample guard | yes | no | no |

Every source delivers mono float32 blocks, and the capture callbacks only enqueue.

## Goals / Non-Goals

**Goals:**
- One copy of the shared core. The platform functions keep only their rows in the table above.
- Behaviour stays the same except for the three fixes in the proposal: the real WASAPI rate, the zero-length guard everywhere, and the mic rate fallback everywhere.
- A hardware-free test that exercises the shared core.

**Non-Goals:**
- `transcribe_live_simple`, the single-source path. It buffers native-rate audio in the callback and has a different shape.
- Changing the resampler itself (`02-resample-with-pyav`).
- Changing CLI flags, output lines or files, or the timing constants (10 s system chunks, 5 s mic chunks, 1 s overlap, the 0.01 mic gate).

## Decisions

### 1. One runner function, platforms pass in what differs

```python
def _run_dual_capture(engine, args, *, title, mode_summary, sys_rate, run_sys, mic,
                      cleanup=None, capture_errors=()) -> int:
```

- **`sys_rate`** is a zero-argument callable that returns the system source's rate. It is read lazily on the first system block, which is what Core Audio needs (`lambda: capture.sample_rate`). WASAPI passes `lambda: capture.sample_rate` too (Decision 3). Linux passes a constant.
- **`run_sys(on_chunk, silence_expired)`** blocks until capture ends. The runner provides `on_chunk(block)`, which checks the silence timeout, raises `KeyboardInterrupt` when it expires, and enqueues the block, just as the callbacks do today. It also provides `silence_expired()` for Linux's poll loop.
  - WASAPI and Core Audio: `lambda on_chunk, _: capture.capture_stream(callback=on_chunk, device_index=…, verbose=args.verbose)`.
  - Linux parec: the same shape.
  - Linux `--audio-device`: opens its `sd.InputStream` with a callback feeding `on_chunk`'s enqueue, and polls `silence_expired()`.
- **`mic`** is `None` or the Decision 2 result. The runner opens, starts and closes the mic stream for every platform, before `run_sys` and after it returns.
- **`cleanup`** is optional, for `capture.cleanup()`. **`capture_errors`** is a tuple of exceptions that print `❌ {e}` and exit 1, used by Core Audio.
- **The runner prints the compact status**: the `Transcriber → …` line, the model/language/`mode_summary` line, and `Listening... (Ctrl+C to stop…)`. Those lines are identical in all three copies apart from `mode_summary`.

**Rejected: a base class with per-platform subclasses.** Three implementations and no other callers. A function with callables is the same seam at a fraction of the size.

**Rejected: also merging `transcribe_live_simple`.** Its callback transcribes in place at the native rate, and folding it in would change its behaviour, not only its layout.

### 2. One mic-setup helper

```python
def _resolve_mic_config(args) -> Optional[MicConfig]:  # a small namedtuple: device, channels, name, rate
```

It wraps the existing `_resolve_mic_device(args)`, then does the query, the `max_input_channels == 0` error, `min(channels, 2)`, and the verbose prints that all three copies have. It also adds the `sd.check_input_settings(samplerate=16000)` check that only Linux has, falling back to the device's `default_samplerate`. Returns `None` after printing on any error, so callers `return 1` as they do today. WASAPI and Core Audio call it only when `args.include_mic` is set; Linux dual is only reached with it set.

### 3. `WASAPICapture` exposes the rate it opened

`capture_stream` already computes `RATE = int(device_info['defaultSampleRate'])` before opening the stream. It stores that as `self.sample_rate`, initialised to `None` in `__init__`, matching `MacOSCapture.sample_rate`. The runner's lazy `sys_rate()` reads it on the first block, which always arrives after the stream is open.

### 4. The shared resample transform keeps the Linux guard

The runner builds each worker's transform from the source's rate, returning an empty array when a block would resample to zero samples. That is the current Linux `_to_target_rate`, now used by every path. It still uses `scipy.signal.resample` here; `02` replaces it.

### 5. Test the runner, not the platforms

A new `test_dual_capture.py` at the repo root, following the existing root test scripts, fakes three things:
- **the engine**, whose `transcribe_chunk` records the audio length it received and returns one segment;
- **`sounddevice`**, inserted into `sys.modules` as in `test_mic_fallback.py`, with an `InputStream` stand-in;
- **`run_sys`**, which feeds synthetic blocks and then raises `KeyboardInterrupt`.

It asserts:
- `[SYS]` lines are emitted and written after the given header;
- a 44.1 kHz source reaches the engine as the right number of 16 kHz samples;
- a few-frame block doesn't crash;
- the silence timeout stops the run;
- a `capture_errors` exception exits 1 and still closes the output file.

A second check builds a `WASAPICapture` against the faked `pyaudiowpatch` from `test_wasapi_capture.py`, with a 44100 Hz device, and confirms `sample_rate` is 44100 once streaming.

## Risks / Trade-offs

- **[Risk]** A subtle ordering change breaks one platform. For example, the mic stream used to start before the system threads on WASAPI, and after on Linux. → The runner keeps one order: open the output file, then start the workers, then the mic, then `run_sys`. Every current order starts all three before audio matters, and the Linux and Windows live checks exercise it. macOS is covered only by the CI smoke test, which never runs live capture. The maintainer accepted that on 2026-09-14.
- **[Risk]** The `Listening...` line moves out of the three named functions, and `tests/test_gui.py`'s wording check names them. → The check's function list is updated to the runner plus `transcribe_live_simple`, so it keeps guarding every path the GUI can take.
- **[Trade-off]** Windows and macOS mics now also try 16 kHz first and fall back to the device rate. That's the fix, but it's the only behaviour change a working setup could notice, and only as a session that now starts instead of failing.
- **[Trade-off]** Callables in the signature are a little less obvious to read than inline code. They replace ~200 duplicated lines, and each platform function becomes short enough to read in full.
