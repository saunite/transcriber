## 1. Baseline Documentation Setup

- [x] 1.1 Confirm `openspec/specs/` is empty and no existing capability specs need modification
- [x] 1.2 Create the six capability spec folders under the change's `specs/` directory: audio-extraction, audio-capture, transcription, speaker-diarization, transcript-conversion, cli

## 2. Audio Extraction Spec

- [x] 2.1 Verify spec requirements against `audio_extractor.py` (ffmpeg availability check, extract to temp or explicit path, mono 16kHz output, temp cleanup)
- [x] 2.2 Confirm each scenario in `specs/audio-extraction/spec.md` matches observable behavior in the code

## 3. Audio Capture Spec

- [x] 3.1 Verify spec requirements against `audio_capture.py` (loopback auto-detection for Windows/Linux, device listing, capture callback loop, save-to-WAV)
- [x] 3.2 Verify spec requirements against `wasapi_capture.py` (WASAPI loopback capture, stereo-to-mono conversion, default loopback auto-detect)
- [x] 3.3 Verify the mic capture and WAV merging behaviors in `transcriber.py` (`transcribe_live_wasapi`) match the `[SYS]`/`[MIC]` labeling and `<base>_sys.wav`/`_mic.wav`/`_merged.wav` scenarios

## 4. Transcription Spec

- [x] 4.1 Verify spec requirements against `transcription_engine.py` (file transcription, chunk transcription, model/device/compute auto-detection, language/task options)
- [x] 4.2 Verify timestamp formatting (relative vs wall-clock) and txt/srt/vtt saving match `format_timestamp`, `save_transcript`, `_save_srt`, `_save_vtt`
- [x] 4.3 Verify incremental save and silence-timeout behavior match code in `transcription_engine.py` and `transcriber.py`

## 5. Speaker Diarization Spec

- [x] 5.1 Verify spec requirements reflect the optional diarization path (`--diarize`, HF token, speaker count options, merge, statistics, speaker-prefixed TXT) and the graceful degradation when torch/pyannote are absent

## 6. Transcript Conversion Spec

- [x] 6.1 Verify spec requirements against `convert_to_srt.py` (timestamp parsing with/without `[SYS|MIC]` label, SRT writing, default `.srt` output naming, error handling)

## 7. CLI Spec

- [x] 7.1 Verify spec requirements against `transcriber.py` `main()` (input-source requirement, `--list-devices`/`--setup-help` utilities, WASAPI routing, Ctrl+C handling)

## 8. Final Verification

- [x] 8.1 Run `openspec validate --change add-initial-specs` and fix any requirement/scenario formatting issues
- [x] 8.2 Confirm `openspec status --change add-initial-specs` shows all artifacts complete and the change is apply-ready
