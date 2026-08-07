## 1. Transcription engine cleanup

- [x] 1.1 Remove the `incremental_save` parameter from `TranscriptionEngine.transcribe_file()` (always `True`); keep the incremental write block itself, and drop the argument at the `transcriber.py` call site
- [x] 1.2 Remove `word_timestamps=True` from both `model.transcribe()` calls in `transcribe_file()` and `transcribe_chunk()`
- [x] 1.3 Change `transcribe_chunk()` to return only the segments list (delete the `info_dict` it builds); update the `segments, _ =` destructure in `_process_audio_chunk()`
- [x] 1.4 Inline `format_transcript()` into the txt branch of `save_transcript()` and delete the method

## 2. WASAPI live path

- [x] 2.1 Replace `sys_worker`/`mic_worker` with one parametrized worker function (queue, `[SYS]`/`[MIC]` tag, chunk threshold, silence gate) invoked twice with per-worker buffer and time offset
- [x] 2.2 Replace the `soundfile` merge in `transcribe_live_wasapi()` with an ffmpeg `amerge=inputs=2:duration=shortest` subprocess call; print a warning and keep the separate WAVs when ffmpeg is unavailable
- [x] 2.3 Remove `soundfile>=0.12.1` from `requirements.txt` and `requirements-linux.txt`

## 3. Capture module cleanup

- [x] 3.1 Remove the unused `duration`/`chunk_size` parameters and the `total_frames`/`frames_captured` bookkeeping from `WASAPICapture.capture_stream()`
- [x] 3.2 Remove the unused `duration`/`chunk_size` parameters and the duration-check branch from `AudioCapture.capture_stream()`
- [x] 3.3 Remove the dead imports: `threading` and `Queue` in `wasapi_capture.py`; `threading` in `audio_capture.py`

## 4. Audio extractor cleanup

- [x] 4.1 Remove the unused `output_path` parameter from `AudioExtractor.extract_audio()` and its branch
- [x] 4.2 Remove the unused `self.system` attribute (and `platform` import) from `AudioExtractor`

## 5. Launcher fix

- [x] 5.1 Fix `start_transcription.sh` to pass `$AUDIO_DEVICE_FLAG` instead of the nonexistent `$DEVICE_FLAG`

## 6. Verification

- [x] 6.1 Grep the tree for `soundfile`, `incremental_save`, `format_transcript`, and `word_timestamps` and confirm no live references remain
- [x] 6.2 Run `python transcriber.py --help` and confirm the CLI still parses
- [x] 6.3 Smoke-test file transcription to txt, srt, and vtt
- [x] 6.4 Run `openspec validate ponytail-audit-cleanup` and confirm the change passes
