## Why

The repository has a fully functional audio transcription system but no OpenSpec specifications documenting its capabilities. Without specs, there is no contract describing the system's behavior, making changes risky and hard to reason about. This change establishes the baseline specs by analyzing the existing code and capturing its actual behavior.

## What Changes

- Create initial capability specs under `openspec/specs/` that document the system's existing behavior:
  - **Audio extraction** from video files via ffmpeg
  - **Audio capture** of system loopback and microphone audio (sounddevice + WASAPI)
  - **Transcription engine** wrapping faster-whisper (file and chunk/streaming modes, timestamps, output formats)
  - **Speaker diarization** (optional, requires torch + pyannote, HF token)
  - **Transcript-to-SRT conversion** via `convert_to_srt.py`
  - **CLI** entry point and option surface in `transcriber.py`
- No runtime behavior is changed; specs reflect the current implementation.
- No breaking changes.

## Capabilities

### New Capabilities
- `audio-extraction`: Extract mono 16kHz WAV audio from video files using ffmpeg, with temporary file cleanup.
- `audio-capture`: Capture live system audio (loopback) and microphone input via sounddevice and WASAPI loopback on Windows.
- `transcription`: Transcribe audio from files or live chunks using faster-whisper, with language/task/model/device options, timestamps, and txt/srt/vtt output.
- `speaker-diarization`: Identify speakers per segment via pyannote.audio, merge with transcription, and report speaker statistics.
- `transcript-conversion`: Convert timestamped transcript files (`[MM:SS -> MM:SS] [SYS|MIC] text`) into SRT subtitles.
- `cli`: Provide the `transcriber.py` command-line interface wiring input, model, device, capture, diarization, and output options.

### Modified Capabilities
<!-- None - no existing specs. -->

## Impact

- **Code touched**: none at runtime; only `openspec/specs/**` documentation files are added.
- **Dependencies referenced**: faster-whisper, sounddevice, soundfile, numpy, scipy, pydub, pyaudiowpatch, tqdm, ffmpeg (system), pyannote.audio (optional), torch (optional).
- **Platforms**: Windows (WASAPI), Linux (PulseAudio/PipeWire monitor).
