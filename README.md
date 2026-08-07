# Audio Transcriber

A cross-platform CLI tool for transcribing audio from video files and live audio streams using faster-whisper, with **real-time streaming** support.

## Features

- 🎥 Transcribe audio from local video files (MP4, AVI, MKV, etc.)
- 🎙️ **Real-time transcription** from system audio (live meetings, streaming videos)
- 💻 Cross-platform: Works on Windows and Linux
- 🔒 100% offline and local - all data stays on your machine
- ⚡ Fast transcription with faster-whisper (MIT license)
- 🎯 Multiple output formats (TXT, SRT, VTT)

## Requirements

### System Dependencies

**Both Windows and Linux:**
- Python 3.9 or higher
- ffmpeg (for audio extraction from videos)

**Installation:**

**Windows (PowerShell):**
```powershell
# Using Chocolatey
choco install ffmpeg

# Or using Scoop
scoop install ffmpeg
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt update && sudo apt install ffmpeg
```

### Python Dependencies

Install Python packages:
```bash
pip install -r requirements.txt
```

## Usage

### Transcribe a Video File

```bash
# Basic transcription
python transcriber.py --file path/to/video.mp4

# Specify language and larger model
python transcriber.py --file meeting.mp4 --language en --model medium
```

### Real-time Audio Capture

**Quick Start for Teams Meetings (Windows with Bluetooth headset):**

Double-click `start_teams_transcription.bat` to automatically start transcription with both system audio and microphone capture. The transcript will be saved with a timestamp (e.g., `meeting_20251110_143052.txt`).

The launcher passes extra arguments through to `transcriber.py`, so you can run it with a filename prefix and/or flags:

```bat
start_teams_transcription.bat                  REM default: meeting_TIMESTAMP.txt
start_teams_transcription.bat sprint-review    REM filename prefix
start_teams_transcription.bat --silence-timeout 0
start_teams_transcription.bat --actual-time --save-audio
```

**Manual Command:**

```bash
# Live transcription with dual-capture (system audio + microphone)
python transcriber.py --live --wasapi --include-mic --mic-device 3

# System audio only (WASAPI loopback for Bluetooth compatibility)
python transcriber.py --live --wasapi

# Traditional mode (may not work with Bluetooth headsets)
python transcriber.py --live

# Custom chunk settings for better responsiveness
python transcriber.py --live --chunk-duration 20
```

**Understanding the Labels:**
- `[SYS]` - System audio (other meeting participants, videos, etc.)
- `[MIC]` - Your microphone (your voice)

**Find Your Microphone Device:**
```bash
python transcriber.py --list-devices
```
Look for your Bluetooth headset in the input devices list and note the device number.

### Advanced Options

```bash
# Use larger model for better accuracy
python transcriber.py --file audio.wav --model medium

# Specify language
python transcriber.py --file video.mp4 --language en

# Output as SRT subtitles
python transcriber.py --file video.mp4 --format srt

# List available audio devices
python transcriber.py --list-devices

# WASAPI mode with custom microphone device
python transcriber.py --live --wasapi --include-mic --mic-device 5
```

### Complete Options

- `--file <path>` - Transcribe audio from a video/audio file
- `--live` - Capture and transcribe system audio in real-time
- `--wasapi` - Use WASAPI loopback mode (Windows only, Bluetooth-compatible)
- `--include-mic` - Include microphone capture alongside system audio (use with --wasapi)
- `--mic-device <id>` - Microphone device index (use --list-devices to find)
- `--model <size>` - Model size: tiny, base, small, medium, large, turbo (default: base)
- `--language <code>` - Language code (e.g., en, es, fr) - auto-detect if not specified
- `--task <type>` - Task: transcribe or translate (default: transcribe)
- `--output <path>` - Output file for transcript (default: auto-generated)
- `--format <type>` - Output format: txt, srt, vtt (default: txt)
- `--no-timestamps` - Exclude timestamps from text output
- `--actual-time` - Use wall-clock timestamps (local time) instead of relative offsets
- `--save-audio` - Save captured audio to WAV files alongside the transcript (live mode only)
- `--chunk-duration <seconds>` - Duration of audio chunks for streaming (default: 30)
- `--silence-timeout <seconds>` - Auto-stop after N seconds of silence (default: 600 = 10 min, 0 = never)
- `--audio-device <id>` - Audio device index for live capture (-1 = auto-detect)
- `--device <type>` - Device to run on: auto, cpu, cuda (default: auto)
- `--compute-type <type>` - Compute type: auto, int8, float16, float32 (default: auto)

## Setup for Real-time Audio Capture

### Windows

**For Bluetooth Headsets (Recommended - WASAPI Mode):**

The transcriber includes WASAPI loopback support which works with Bluetooth headsets. No additional setup required!

```bash
# Use WASAPI mode with microphone
python transcriber.py --live --wasapi --include-mic --mic-device 3

# Or just double-click start_teams_transcription.bat
```

**For Traditional Sound Cards (Stereo Mix):**

You may need to enable "Stereo Mix":

1. Right-click the speaker icon in taskbar → Sounds
2. Go to 'Recording' tab
3. Right-click empty area → Show Disabled Devices
4. Enable 'Stereo Mix' or 'Wave Out Mix'
5. Set it as default recording device

**Note:** Stereo Mix does NOT work with Bluetooth headsets. Use WASAPI mode instead.

**Alternative**: Install [VB-Cable](https://vb-audio.com/Cable/) virtual audio device

### Linux
Uses PulseAudio/PipeWire monitor. Identify your audio monitor device:
```bash
pactl list sources | grep -i monitor
```

The transcriber will auto-detect monitor devices automatically.

## Performance Tips

### For Best Accuracy
- Use `--model medium` or `--model large`
- Specify `--language` if you know it

### For Speed
- Use `--model tiny` or `--model base`
- Use `--device cuda` if you have an NVIDIA GPU
- For streaming, use shorter `--chunk-duration` (but may reduce accuracy)

### GPU Acceleration
- Install CUDA toolkit for NVIDIA GPUs
- The tool automatically uses GPU if available
- Expect 4-10x speedup with GPU

## License

GPLv2

This software uses faster-whisper (MIT License), compatible with GPLv2.

## Troubleshooting

### "No loopback device found"
- **Windows**: Enable Stereo Mix or install VB-Cable
- **Linux**: Ensure PulseAudio/PipeWire is running
- Use `--list-devices` to see available devices
- Use `--setup-help` for detailed setup instructions

### Auto-stop feature
- By default, transcription stops after 10 minutes of silence
- Disable with `--silence-timeout 0` for continuous recording
- Adjust timeout with `--silence-timeout 300` (5 minutes), etc.

### Slow transcription
- Use smaller model (`--model tiny` or `--model base`)
- Enable GPU if available
- For live mode, reduce `--chunk-duration`

### Poor accuracy
- Use larger model (`--model medium` or `--model large`)
- Specify correct `--language`
- Ensure good audio quality (no background noise)

## Examples

### Basic video transcription
```bash
python transcriber.py --file meeting.mp4
```

### Live meeting transcription
```bash
python transcriber.py --live --model base --language en
```

### Generate SRT subtitles
```bash
python transcriber.py --file video.mp4 --format srt
```
