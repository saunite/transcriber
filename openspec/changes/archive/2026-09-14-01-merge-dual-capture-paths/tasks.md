## 1. Shared pieces

- [x] 1.1 Add `self.sample_rate = None` to `WASAPICapture.__init__`, and set it to `RATE` in `capture_stream` before the stream opens (design.md Decision 3). Verify with a check in `test_wasapi_capture.py`, using its faked `pyaudiowpatch` with a 44100 Hz device, that `sample_rate` is 44100 once streaming, and that `python test_wasapi_capture.py` passes.
- [x] 1.2 Add `_resolve_mic_config(args)` to `transcriber.py` (Decision 2): wrap `_resolve_mic_device`, then do the query, the zero-input-channels error, `min(channels, 2)`, the verbose prints, and the 16 kHz check with the `default_samplerate` fallback, returning `None` on error. Verify with cases added to `test_mic_fallback.py` against its fake `sounddevice`: a 16 kHz-capable mic gives `rate == 16000`; a mic whose `check_input_settings` raises gives its `default_samplerate`; a zero-input-channel device gives `None` and prints the existing error.
- [x] 1.3 Add `_run_dual_capture(...)` with the Decision 1 signature. It takes over the shared core: queues, output file and header, mic stream, `on_chunk` and `silence_expired`, `_emit`, `_drain_and_transcribe`, the rate transform with the zero-length guard (Decision 4), stop, join and close, the compact status and `Listening...` lines, and the summary. Verify with 2.1.

  **Done 2026-09-14, with one refinement to the Decision 1 signature**, recorded in design.md: `run_sys(on_chunk, enqueue, check_silence)` in place of `run_sys(on_chunk, silence_expired)`. Reading the Linux `--audio-device` path showed its system stream's callback runs on PortAudio's thread, where it must only enqueue and never raise, so it needs a plain `enqueue`. `check_silence()` prints the auto-stop message and raises `KeyboardInterrupt`, so the Linux poll loop and the capture callbacks share one message instead of a boolean plus a copied print. The runner also stops the mic stream **before** joining the workers, as Linux did. WASAPI and Core Audio used to join first, which lets a still-running mic keep a draining worker busy.

## 2. Tests before the switch-over

- [x] 2.1 Add `test_dual_capture.py` at the repo root (Decision 5). It must check that:
  - `[SYS]` and `[MIC]` lines are printed and written to the output file after the given `title` header;
  - a 44100 Hz `sys_rate` delivers `round(n * 16000 / 44100)` samples per block to the engine;
  - a 3-frame block neither crashes nor stops the run;
  - the silence timeout ends the run through `silence_expired()`;
  - an exception listed in `capture_errors` returns 1 and still closes the output file.
  Verify it passes against 1.3. Then confirm it fails when the zero-length guard is removed, and when `sys_rate()` is replaced by a constant 48000, and restore both.

  **Done 2026-09-14.** Passes, 3 runs in a row. With the runner's guard removed, the system worker dies with `ZeroDivisionError` and only the mic chunk arrives (`[80000]`). With `_to_target_rate(lambda: 48000)` for system audio, the first chunk is `16170` instead of `16000`. Two test flaws were found and fixed along the way:
  - The first assertion (`16000 in chunk_lengths`) also matched the final overlap chunk, so the 48 kHz mutation slipped through. It now checks the *first* system chunk.
  - Queued blocks were drained in one go, so chunk boundaries depended on timing. Blocks are now fed 120 ms apart, longer than the worker's 50 ms poll.

## 3. Switch the platforms over

- [x] 3.1 Rewrite `_transcribe_live_linux_dual` to keep only its system-source detection (parec, or `--audio-device` via `sd`), `_resolve_mic_config`, and a `_run_dual_capture` call with its `run_sys` for both modes, `sys_rate` and title. Verify `python test_dual_capture.py` still passes, and that a local live session works in both modes: `transcriber.py --live --include-mic` (monitor auto-detect), and `--live --include-mic --audio-device <monitor index from --list-devices>`. Each must print `[SYS]` and `[MIC]` lines and save them on Ctrl+C.

  **Implemented 2026-09-14; the audio half is still open.** `_transcribe_live_linux_dual` now keeps only its two system-source setups, each with its own `run_sys`: parec calls `on_chunk`, and `--audio-device` uses an `sd.InputStream` that only `enqueue`s, polled by `check_silence()`. Then `_resolve_mic_config` and the runner. `test_dual_capture.py` passes. **Smoke-tested silently on Fedora:**
  - `--live --include-mic` auto-detected `alsa_output.pci-0000_00_1f.3.analog-stereo.monitor` and the default mic;
  - `--live --include-mic --audio-device 11` (`pipewire`) opened too;
  - both printed the status and `Listening...`, stopped on SIGINT, wrote the `# Live Transcription (System Audio + Microphone)` header, and printed no traceback.
  **Not yet checked:** real `[SYS]` and `[MIC]` lines, which need audio playing and someone speaking. That was left to the user rather than playing sound on their machine unannounced.

  **Audio half user-verified on Fedora, 2026-09-14** with the SciPy-free frozen sidecar (`dist/linux/transcriber-sidecar` from `7e46cdb`'s code, containing `01` and `02`), with a video playing and the user speaking: `--live --include-mic` (monitor auto-detect) and `--live --include-mic --audio-device 11` (`pipewire`) both worked: "all seems good".
- [x] 3.2 Rewrite `transcribe_live_wasapi` the same way, with `sys_rate=lambda: capture.sample_rate`, `cleanup=capture.cleanup`, and the mic only when `--include-mic` is set. Verify `python -c "import transcriber"` succeeds and the automated tests pass. Real Windows verification is 4.2.

  **Done 2026-09-14.** The detection block is kept verbatim; the mic goes through `_resolve_mic_config` when `--include-mic` is set, then `_run_dual_capture` with `sys_rate=lambda: capture.sample_rate` and `cleanup=capture.cleanup`. `import transcriber` succeeds. **Added beyond the task text:** with no Windows machine here, `test_dual_capture.py` case 4 runs `transcribe_live_wasapi` against a fake `WASAPICapture` whose device opens at 44100 Hz, with the runner replaced by a recorder. It confirms `sys_rate()` returns 44100, the title is `WASAPI Loopback`, and `cleanup` releases the capture. With `sys_rate=lambda: 48000` it fails: `WASAPI must pass the rate its capture opened`.
- [x] 3.3 Rewrite `transcribe_live_coreaudio_tap` the same way, with `sys_rate=lambda: capture.sample_rate` and `capture_errors` set to the three macOS exceptions. Verify the automated tests pass and `test_macos_capture.py` is unchanged and passing. There is no Mac to test on.

  **Done 2026-09-14.** The same shape, with `capture_errors` set to the three macOS exceptions. `test_macos_capture.py` is unchanged and passes. The same recorder check confirms Core Audio passes the rate from the helper's header (48000 in the fake), all three exception types, and the title `Core Audio Process Tap`. It has not run on a Mac.
- [x] 3.4 Update `tests/test_gui.py`'s `LIVE_FUNCTIONS` to `("transcribe_live_simple", "_run_dual_capture")`. Verify the listening-wording check passes, and fails naming `_run_dual_capture` when its `Listening...` is reworded in a scratch copy.

  **Done 2026-09-14.** `LIVE_FUNCTIONS = ("transcribe_live_simple", "_run_dual_capture")`. **Test flaw found and fixed:** at first, the reworded scratch copy still passed. The runner has a comment mentioning `"Listening..."`, and the check searched plain text. It now ignores comment lines. It passes on today's tree and returns `['_run_dual_capture']` when that function's print is reworded.

## 4. Full verification

- [x] 4.1 Run `.venv/bin/python run_tests.py`; it must exit 0. Record the change in `transcriber.py`'s line count, measured with `wc -l` before and after.

  **Done 2026-09-14.** With `TRANSCRIBER_TEST_SPEECH` set, 11/11 suites passed in 24.3s, including the new `test_dual_capture.py` (3.7s). `transcriber.py` went from **1451 to 1154 lines (-297)**, more than the ~200 estimated, because the three copies of the mic query also went into `_resolve_mic_config`.
- [x] 4.2 **User check on Windows** with a build containing this change (it may be combined with `02`'s round): a GUI live session and `win-start-transcription.bat` each show `[SYS]` and `[MIC]` lines and save the transcript. If an output device can be switched to 44.1 kHz in Windows Sound settings, repeat the GUI session with it and confirm the system audio still transcribes correctly.

  **User-verified 2026-09-14** (Windows 11, the `windows` artifact from CI run 34885359545 at `1656436`, containing `01` and `02`), "All 3 windows tests passed". W1: a GUI live session showed and saved `[SYS]` and `[MIC]` lines. W2: `win-start-transcription.bat TEST` saved them to `TEST_<date>_<time>.txt`. W3: with the output device switched to 44100 Hz, system audio still transcribed correctly, which confirms the WASAPI real-rate fix on hardware.
- [x] 4.3 **User check on Linux** with a local build (the AppImage or `.rpm`): a GUI live session shows `[SYS]` and `[MIC]` lines, stops cleanly, and saves the transcript.

  **User-verified on Fedora, 2026-09-14** with the local AppImage/`.rpm` built from the same code (`~/Downloads/transcriber-test/dualcapture-local/`): a GUI live session worked ("L1 test worked").
