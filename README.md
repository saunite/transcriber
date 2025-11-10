# Audio Transcriber

A cross-platform CLI tool for transcribing audio from video files and live audio streams using faster-whisper, with **real-time streaming** and **speaker diarization** support.

## Features

- 🎥 Transcribe audio from local video files (MP4, AVI, MKV, etc.)
- 🎙️ **Real-time transcription** from system audio (live meetings, streaming videos)
- 👥 **Speaker diarization** - Identify who spoke when
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

# With speaker diarization
python transcriber.py --file meeting.mp4 --diarize --hf-token YOUR_TOKEN

# Specify number of speakers
python transcriber.py --file video.mp4 --diarize --num-speakers 3 --hf-token YOUR_TOKEN
```

### Real-time Audio Capture

```bash
# Live transcription from system audio
python transcriber.py --live

# Live transcription with speaker diarization
python transcriber.py --live --diarize --hf-token YOUR_TOKEN

# Custom chunk settings for better responsiveness
python transcriber.py --live --chunk-duration 20 --overlap-duration 3
```

### Advanced Options

```bash
# Use larger model for better accuracy
python transcriber.py --file audio.wav --model medium

# Specify language
python transcriber.py --file video.mp4 --language en

# Output as SRT subtitles with speakers
python transcriber.py --file video.mp4 --format srt --diarize --hf-token YOUR_TOKEN

# List available audio devices
python transcriber.py --list-devices

# Get help for audio loopback setup
python transcriber.py --setup-help
```

### Complete Options

- `--file <path>` - Transcribe audio from a video/audio file
- `--live` - Capture and transcribe system audio in real-time
- `--diarize` - Enable speaker diarization
- `--hf-token <token>` - Hugging Face token for diarization (or set HUGGINGFACE_TOKEN env var)
- `--num-speakers <n>` - Expected number of speakers
- `--min-speakers <n>` - Minimum number of speakers
- `--max-speakers <n>` - Maximum number of speakers
- `--model <size>` - Model size: tiny, base, small, medium, large, turbo (default: base)
- `--language <code>` - Language code (e.g., en, es, fr) - auto-detect if not specified
- `--task <type>` - Task: transcribe or translate (default: transcribe)
- `--output <path>` - Output file for transcript (default: auto-generated)
- `--format <type>` - Output format: txt, srt, vtt (default: txt)
- `--no-timestamps` - Exclude timestamps from text output
- `--chunk-duration <seconds>` - Duration of audio chunks for streaming (default: 30)
- `--overlap-duration <seconds>` - Overlap between chunks (default: 5)
- `--audio-device <id>` - Audio device index for live capture (-1 = auto-detect)
- `--device <type>` - Device to run on: auto, cpu, cuda (default: auto)
- `--compute-type <type>` - Compute type: auto, int8, float16, float32 (default: auto)

## Setup for Real-time Audio Capture

### Windows
Real-time capture uses WASAPI loopback. You may need to enable "Stereo Mix":

1. Right-click the speaker icon in taskbar → Sounds
2. Go to 'Recording' tab
3. Right-click empty area → Show Disabled Devices
4. Enable 'Stereo Mix' or 'Wave Out Mix'
5. Set it as default recording device

**Alternative**: Install [VB-Cable](https://vb-audio.com/Cable/) virtual audio device

### Linux
Uses PulseAudio/PipeWire monitor. Identify your audio monitor device:
```bash
pactl list sources | grep -i monitor
```

The transcriber will auto-detect monitor devices automatically.

## Speaker Diarization Setup

Speaker diarization uses pyannote.audio which requires a Hugging Face account:

1. Create a free account at [https://huggingface.co/](https://huggingface.co/)
2. Accept the license at [https://huggingface.co/pyannote/speaker-diarization-3.1](https://huggingface.co/pyannote/speaker-diarization-3.1)
3. Get your access token from [https://huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)
4. Use the token with `--hf-token YOUR_TOKEN` or set environment variable:

**Windows (PowerShell):**
```powershell
$env:HUGGINGFACE_TOKEN="your_token_here"
```

**Linux/Mac:**
```bash
export HUGGINGFACE_TOKEN="your_token_here"
```

## Performance Tips

### For Best Accuracy
- Use `--model medium` or `--model large`
- Specify `--language` if you know it
- Use `--diarize` with correct `--num-speakers` if known

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

This software uses faster-whisper (MIT License) and pyannote.audio (MIT License), both compatible with GPLv2.

## Troubleshooting

### "No loopback device found"
- **Windows**: Enable Stereo Mix or install VB-Cable
- **Linux**: Ensure PulseAudio/PipeWire is running
- Use `--list-devices` to see available devices
- Use `--setup-help` for detailed setup instructions

### "Hugging Face token required"
- Speaker diarization requires authentication
- Follow setup steps in "Speaker Diarization Setup" section above

### Slow transcription
- Use smaller model (`--model tiny` or `--model base`)
- Enable GPU if available
- For live mode, reduce `--chunk-duration`

### Poor accuracy
- Use larger model (`--model medium` or `--model large`)
- Specify correct `--language`
- Ensure good audio quality (no background noise)
- For diarization, specify `--num-speakers` if known

## Examples

### Basic video transcription
```bash
python transcriber.py --file meeting.mp4
```

### Transcribe with speakers identified
```bash
python transcriber.py --file interview.mp4 --diarize --num-speakers 2 --hf-token YOUR_TOKEN
```

### Live meeting transcription
```bash
python transcriber.py --live --model base --language en
```

### Live transcription with speaker detection
```bash
export HUGGINGFACE_TOKEN="your_token"
python transcriber.py --live --diarize --min-speakers 2 --max-speakers 5
```

### Generate subtitles with speaker labels
```bash
python transcriber.py --file video.mp4 --format srt --diarize --hf-token YOUR_TOKEN
```
