## 1. Transcription engine cleanup

- [x] 1.1 Delete `transcribe_stream()` from `transcription_engine.py`
- [x] 1.2 Drop word-level timestamps: remove `words` from segment dicts in `transcribe_file()` and `transcribe_chunk()`, drop the `include_words` param and its branch in `format_transcript()`, and remove the now-unused `_format_time()` word rendering
- [x] 1.3 Remove `duration_after_vad` from the `info_dict` returned by `transcribe_file()`
- [x] 1.4 Hardcode `beam_size=5` / `word_timestamps=True` in `transcribe_file()` and remove the `beam_size`/`word_timestamps` parameters (callers never override them)
- [x] 1.5 Collapse the SSL-verification-disable block (ssl context patch + env vars + httpx monkey-patch) to a single short block using `ssl._create_default_https_context` and `SSL_CERT_FILE=''`; delete the httpx monkey-patch

## 2. Remove diarization from the CLI

- [x] 2.1 Delete the `DIARIZATION_AVAILABLE`/`SpeakerDiarization`/`AudioBuffer` import block in `transcriber.py`
- [x] 2.2 Delete the five diarization argparse flags (`--diarize`, `--hf-token`, `--num-speakers`, `--min-speakers`, `--max-speakers`)
- [x] 2.3 Remove the diarization block and diarized-save branch from `transcribe_file()`; simplify output-name suffix to always `_transcript`
- [x] 2.4 Delete the unreachable AudioBuffer-based `transcribe_live()` path and route `--live` (non-WASAPI) straight to `transcribe_live_simple`; remove the `--overlap-duration` flag if now unused
- [x] 2.5 Remove the `shutdown_requested` checks in the live capture callbacks (the signal handler already raises `KeyboardInterrupt`); drop the now-unused global flag if nothing else reads it

## 3. Extract shared live-chunk loop

- [x] 3.1 Add one helper (e.g. `_process_audio_chunk()`) that buffers, resamples to 16 kHz, transcribes, applies the running time offset, formats timestamps, and returns adjusted segments plus the new offset
- [x] 3.2 Rewire `transcribe_live_simple()` to use the helper, keeping its native-rate WAV writing and incremental `output_file` writes at the call site
- [x] 3.3 Rewire `sys_worker()` and `mic_worker()` in the WASAPI path to use the helper, keeping `[SYS]`/`[MIC]` tags and per-stream WAV writing at the call sites

## 4. Capture module cleanup

- [x] 4.1 Delete `AudioCapture.capture_to_file()` from `audio_capture.py`
- [x] 4.2 Delete `WASAPICapture.list_loopback_devices()` from `wasapi_capture.py`

## 5. Delete duplicate converter and trim deps

- [x] 5.1 Delete `convert_to_srt.py`
- [x] 5.2 Remove `pydub` from `requirements.txt` and `requirements-linux.txt`; remove `onnxruntime` from `requirements-linux.txt`

## 6. Launcher and docs consolidation

- [x] 6.1 Merge the three Teams launchers into one `start_teams_transcription.bat` that passes through optional args (`--silence-timeout 0`, `--actual-time`, meeting-name prefix); delete `start_teams_transcription-no-timeout.bat` and `start_t_actual_time.bat`
- [x] 6.2 Update `README.md`: remove diarization setup/flags/examples, remove the "Converting Existing Transcripts to SRT" section, and note the launcher's passthrough args

## 7. Verification

- [x] 7.1 Confirm no remaining references to `speaker_diarization`, `AudioBuffer`, `--diarize`, `convert_to_srt`, `pydub`, or `onnxruntime` in `.py`, `.bat`, and `requirements*.txt` files
- [x] 7.2 Run `python transcriber.py --help` and confirm the flag surface matches (no diarization flags)
- [x] 7.3 Smoke-test file transcription to txt, srt, and vtt to confirm `--format srt` still produces valid SRT
- [x] 7.4 Run `openspec validate` (or the repo's equivalent) to confirm the delta specs parse before archiving
