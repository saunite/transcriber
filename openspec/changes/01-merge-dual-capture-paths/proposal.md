## Why

`transcriber.py`'s three dual-source live paths are near-copies: `_transcribe_live_linux_dual` (267 lines), `transcribe_live_wasapi` (231) and `transcribe_live_coreaudio_tap` (215). A ponytail audit on 2026-09-14 found about 100 lines identical in all three and 145 shared between WASAPI and Core Audio: the queues, the output-file header, the mic callback, the `_emit` and `_drain_and_transcribe` worker, stop and join, and the summary. Every fix to that core has to land three times, and the copies have already drifted:

- **WASAPI resamples from a hardcoded 48 kHz** (`wasapi_rate = 48000`), but `WASAPICapture` opens the loopback device at the device's own `defaultSampleRate` (`wasapi_capture.py:72`). On a 44.1 kHz output device, system audio reaches Whisper about 9% slow and low.
- **Only the Linux copy guards against few-frame chunks** that resample to zero samples, which make `scipy.signal.resample` divide by zero.
- **Only the Linux copy falls back when a microphone refuses 16 kHz**, opening it at its own rate and resampling. On Windows and macOS such a mic fails the session.

This is also the prerequisite for `02-resample-with-pyav`: once there is one resample spot instead of four, swapping the resampler is a small change.

## What Changes

- **One shared dual-capture runner** in `transcriber.py` owns the queues, output header, mic stream, worker threads, silence timeout, stop and join, and summary. Each platform function keeps only what differs: finding its system-audio source, how that source runs (a blocking capture call, or Linux's paired `sd.InputStream`s), the rate it delivers, and any platform-specific errors.
- **Shared microphone setup.** The mic query, channel count and 16 kHz-or-native-rate check are duplicated in all three preambles; one helper replaces them, so every platform gets the Linux fallback.
- **WASAPI uses the capture's real rate.** `WASAPICapture` exposes the rate it opened the device at, and the runner resamples from that.
- **The zero-sample guard applies to every path.**
- **A local test for the shared runner** drives it with a fake engine and synthetic audio, so the refactor is checked without audio hardware. It includes a 44.1 kHz WASAPI capture as a regression test.
- **The GUI listening-line test** follows the `Listening...` print into the shared runner.
- **Not in scope:**
  - The single-source `transcribe_live_simple` path, which has a different structure.
  - Replacing scipy, which is `02-resample-with-pyav`.
  - WASAPI devices with more than 2 channels, recorded in `openspec/backlog.md`.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `audio-capture`: adds a requirement that live capture delivers 16 kHz audio to transcription from whatever rate each source actually runs at, including a microphone that refuses 16 kHz, on every platform.

## Impact

- **Changed:**
  - `transcriber.py`: the three dual live functions shrink to their platform parts, plus one shared runner and one mic-setup helper. About -200 lines expected.
  - `wasapi_capture.py`: exposes the opened sample rate.
  - `tests/test_gui.py`: the listening-line check names the shared runner.
  - A new root test script for the runner.
- **Unchanged:** CLI flags, output format, the GUI, the Rust sidecar code, `macos_capture.py`, `linux_loopback_capture.py`, and packaging.
- **Verification:**
  - Local: automated tests, plus Linux live sessions in both system-audio modes (monitor auto-detect, and an explicit `--audio-device`).
  - Windows: a live session via the GUI and the launcher.
  - macOS: only the CI smoke test, since there is no Mac. The maintainer accepted shipping it unverified.
