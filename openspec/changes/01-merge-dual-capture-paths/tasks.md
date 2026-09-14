## 1. Shared pieces

- [ ] 1.1 Add `self.sample_rate = None` to `WASAPICapture.__init__`, and set it to `RATE` in `capture_stream` before the stream opens (design.md Decision 3). Verify with a check in `test_wasapi_capture.py`, using its faked `pyaudiowpatch` with a 44100 Hz device, that `sample_rate` is 44100 once streaming, and that `python test_wasapi_capture.py` passes.
- [ ] 1.2 Add `_resolve_mic_config(args)` to `transcriber.py` (Decision 2): wrap `_resolve_mic_device`, then do the query, the zero-input-channels error, `min(channels, 2)`, the verbose prints, and the 16 kHz check with the `default_samplerate` fallback, returning `None` on error. Verify with cases added to `test_mic_fallback.py` against its fake `sounddevice`: a 16 kHz-capable mic gives `rate == 16000`; a mic whose `check_input_settings` raises gives its `default_samplerate`; a zero-input-channel device gives `None` and prints the existing error.
- [ ] 1.3 Add `_run_dual_capture(...)` with the Decision 1 signature. It takes over the shared core: queues, output file and header, mic stream, `on_chunk` and `silence_expired`, `_emit`, `_drain_and_transcribe`, the rate transform with the zero-length guard (Decision 4), stop, join and close, the compact status and `Listening...` lines, and the summary. Verify with 2.1.

## 2. Tests before the switch-over

- [ ] 2.1 Add `test_dual_capture.py` at the repo root (Decision 5). It must check that:
  - `[SYS]` and `[MIC]` lines are printed and written to the output file after the given `title` header;
  - a 44100 Hz `sys_rate` delivers `round(n * 16000 / 44100)` samples per block to the engine;
  - a 3-frame block neither crashes nor stops the run;
  - the silence timeout ends the run through `silence_expired()`;
  - an exception listed in `capture_errors` returns 1 and still closes the output file.
  Verify it passes against 1.3. Then confirm it fails when the zero-length guard is removed, and when `sys_rate()` is replaced by a constant 48000, and restore both.

## 3. Switch the platforms over

- [ ] 3.1 Rewrite `_transcribe_live_linux_dual` to keep only its system-source detection (parec, or `--audio-device` via `sd`), `_resolve_mic_config`, and a `_run_dual_capture` call with its `run_sys` for both modes, `sys_rate` and title. Verify `python test_dual_capture.py` still passes, and that a local live session works in both modes: `transcriber.py --live --include-mic` (monitor auto-detect), and `--live --include-mic --audio-device <monitor index from --list-devices>`. Each must print `[SYS]` and `[MIC]` lines and save them on Ctrl+C.
- [ ] 3.2 Rewrite `transcribe_live_wasapi` the same way, with `sys_rate=lambda: capture.sample_rate`, `cleanup=capture.cleanup`, and the mic only when `--include-mic` is set. Verify `python -c "import transcriber"` succeeds and the automated tests pass. Real Windows verification is 4.2.
- [ ] 3.3 Rewrite `transcribe_live_coreaudio_tap` the same way, with `sys_rate=lambda: capture.sample_rate` and `capture_errors` set to the three macOS exceptions. Verify the automated tests pass and `test_macos_capture.py` is unchanged and passing. There is no Mac to test on.
- [ ] 3.4 Update `tests/test_gui.py`'s `LIVE_FUNCTIONS` to `("transcribe_live_simple", "_run_dual_capture")`. Verify the listening-wording check passes, and fails naming `_run_dual_capture` when its `Listening...` is reworded in a scratch copy.

## 4. Full verification

- [ ] 4.1 Run `.venv/bin/python run_tests.py`; it must exit 0. Record the change in `transcriber.py`'s line count, measured with `wc -l` before and after.
- [ ] 4.2 **User check on Windows** with a build containing this change (it may be combined with `02`'s round): a GUI live session and `win-start-transcription.bat` each show `[SYS]` and `[MIC]` lines and save the transcript. If an output device can be switched to 44.1 kHz in Windows Sound settings, repeat the GUI session with it and confirm the system audio still transcribes correctly.
- [ ] 4.3 **User check on Linux** with a local build (the AppImage or `.rpm`): a GUI live session shows `[SYS]` and `[MIC]` lines, stops cleanly, and saves the transcript.
