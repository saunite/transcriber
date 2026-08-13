## 1. Refactor AudioCapture (Remove Queue Pattern)

- [x] 1.1 Add `import time` at top of `audio_capture.py` (replace `__import__('time')`)
- [x] 1.2 Remove `self.audio_queue = Queue()` initialization from `__init__`
- [x] 1.3 Remove `from queue import Queue` import (no longer needed)
- [x] 1.4 Store user callback as instance variable: `self._user_callback = callback` in `capture_stream()`
- [x] 1.5 Update `_audio_callback()` to invoke user callback directly instead of queueing
- [x] 1.6 Wrap user callback in try-except to handle errors gracefully (log + continue)
- [x] 1.7 Remove polling loop (lines 131–134) that drains `self.audio_queue`
- [x] 1.8 Replace polling with direct context manager (keep InputStream but remove queue dequeueing)
- [x] 1.9 Update while loop in `capture_stream()` to simply wait on InputStream (remove queue polling)

## 2. Extract Common Helpers in transcriber.py

- [x] 2.1 Create `_setup_output_files()` helper function
  - [x] 2.1a Accept args (output path, format, model, language, save_audio, include_mic, sample_rate)
  - [x] 2.1b Return (output_file, wav_file, audio_save_path) or similar tuple
  - [x] 2.1c Handle both simple and WASAPI modes
  - [x] 2.1d Write headers to transcript file
- [x] 2.2 Create `_print_summary()` helper function
  - [x] 2.2a Accept (segments count, output paths, wav paths, merged path)
  - [x] 2.2b Print 60-char header, summary info, 60-char footer
  - [x] 2.2c Handle both simple and WASAPI modes
- [ ] 2.3 Create `_get_device_info(device_id)` helper function
  - [ ] 2.3a Query device and validate input channels
  - [ ] 2.3b Return device info dict or raise with helpful error
  - [ ] 2.3c Used by both `transcribe_live_simple()` and `transcribe_live_wasapi()`
- [x] 2.4 Update `transcribe_live_simple()` to use new helpers
  - [x] 2.4a Replace header printing with `_setup_output_files()` call
  - [x] 2.4b Replace summary printing with `_print_summary()` call
  - [ ] 2.4c Replace device query logic with `_get_device_info()` call
- [x] 2.5 Update `transcribe_live_wasapi()` to use new helpers
  - [x] 2.5a Replace header printing with `_setup_output_files()` call
  - [x] 2.5b Replace summary printing with `_print_summary()` call
  - [ ] 2.5c Replace device query logic with `_get_device_info()` call
- [x] 2.6 Verify both functions remain functionally identical (no logic changes, only extraction)

## 3. Improve SSL Handling in transcription_engine.py

- [x] 3.1 Remove lines 14–16 (global `ssl._create_default_https_context` manipulation)
- [x] 3.2 Create context manager `_suppress_ssl_verification()` function
  - [x] 3.2a Use try-finally to temporarily disable SSL verification
  - [x] 3.2b Document rationale (corporate network compatibility)
- [x] 3.3 Wrap `WhisperModel()` initialization with context manager
- [x] 3.4 Keep `os.environ.pop("TZ", None)` in transcriber.py (timezone handling—don't touch)
- [x] 3.5 Verify model loads correctly with new approach

## 4. Testing & Verification

- [ ] 4.1 Run file transcription test
  - [ ] 4.1a Transcribe a small test video file
  - [ ] 4.1b Verify output matches previous version (timestamps, text, format)
- [ ] 4.2 Test live audio capture (simple mode)
  - [ ] 4.2a Start live capture, speak into microphone
  - [ ] 4.2b Verify audio is captured and transcribed
  - [ ] 4.2c Verify latency is acceptable (no noticeable delay from original)
- [ ] 4.3 Test live audio capture (WASAPI mode, if on Windows)
  - [ ] 4.3a Start WASAPI capture, play system audio
  - [ ] 4.3b Verify system audio and mic (if enabled) are captured separately
  - [ ] 4.3c Verify labels `[SYS]` and `[MIC]` appear correctly
- [ ] 4.4 Test device detection and error handling
  - [ ] 4.4a List devices with `--list-devices`
  - [ ] 4.4b Test invalid device ID (verify error message)
  - [ ] 4.4c Test missing loopback device (verify helpful error)
- [ ] 4.5 Test timestamp features
  - [ ] 4.5a Verify `--actual-time` produces wall-clock timestamps (unchanged)
  - [ ] 4.5b Verify relative timestamps work (unchanged)
  - [ ] 4.5c Verify silence timeout behavior (unchanged)
- [ ] 4.6 Test audio saving (WAV output)
  - [ ] 4.6a Verify `--save-audio` writes valid WAV files
  - [ ] 4.6b Verify merge creates stereo WAV (WASAPI + mic mode)
  - [ ] 4.6c Verify graceful error if ffmpeg not available
- [ ] 4.7 Code review: Verify no unintended behavior changes
  - [ ] 4.7a Compare before/after output for same input
  - [ ] 4.7b Verify all command-line options still work
  - [ ] 4.7c Check for any exceptions or warnings during normal operation
- [ ] 4.8 Performance check: Verify no latency regression
  - [ ] 4.8a Profile live capture CPU usage (should be similar or better)
  - [ ] 4.8b Check memory usage during long transcription runs

## 5. Finalization

- [x] 5.1 Create git commit with clear message referencing ponytail audit
- [ ] 5.2 Update CLAUDE.md if project tracking is needed
- [ ] 5.3 Archive this change in OpenSpec (if using OpenSpec workflow)
