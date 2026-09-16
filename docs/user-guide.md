# User guide

Everything the transcriber can do, for both the desktop app and the CLI. To
install it, see [the README](../README.md).
## The desktop app

**Using a different model in the app.** The **Model** field in the title bar uses the bundled `base` model by default. To use a better one, download a faster-whisper model folder yourself (for example [Systran/faster-whisper-small](https://huggingface.co/Systran/faster-whisper-small); the folder must contain `model.bin`), then pick **Choose folder…** in the Model field and select it. The app remembers the choice. Pick **Bundled (base)** to go back. If the folder later moves or holds no `model.bin`, starting a transcription says so instead of starting. English-only models (names ending in `.en`) can only transcribe English.

**When a live session stops by itself.** Under **Stop after silence** in the Live panel you set how many minutes without speech end a session (default 10; 0 keeps listening until you press **Stop**). When that happens the app tells you ("Stopped after 10 minutes of silence. The transcript so far is saved.") and returns to idle. If capture ends for any other reason, such as the audio server restarting or the output device disconnecting, the app says it ended unexpectedly and shows the engine's last message. While a session is running but nobody is talking, the status reads "Listening — no speech right now"; "Transcribing stalled" appears only when the engine itself has stopped reporting for 30 seconds.

Each time the transcription engine runs, it unpacks itself (about 350 MB) into your temporary folder, `/tmp` on Linux, which is often held in RAM, and removes that copy when it exits. Pressing **Stop** gives it up to 15 seconds to finish and clean up. If a copy is left behind anyway (the app was quit mid-session, or the engine was killed), the app removes it the next time it starts. It only ever removes its own engine's copies, and only when no running engine is using them.

## Requirements

### System Dependencies

**Both Windows and Linux:**
- Python 3.9 or higher

No external media tool is required -- audio and video files are decoded by PyAV (bundled with faster-whisper), not an external ffmpeg binary.

### Python Dependencies

Install Python packages:

```bash
# Windows
pip install -r requirements.txt

# Linux (uses requirements-linux.txt, which omits the Windows-only pyaudiowpatch)
pip install -r requirements-linux.txt
```

## Usage

### Transcribe a Video File

Each segment is printed as it is transcribed, so you can read along while a
long recording is processed, and the same lines are saved to the transcript
file. In the app, they fill the File view the same way.

```bash
# Basic transcription
python transcriber.py --file path/to/video.mp4

# Specify language and larger model
python transcriber.py --file meeting.mp4 --language en --model medium
```

### Real-time Audio Capture

**Quick Start for Teams Meetings:**

Each platform has a launcher that automatically starts dual-capture transcription (system audio + microphone): `win-start-transcription.bat` (Windows), `linux-start-transcription.sh` (Linux), `mac-start-transcription.sh` (macOS). Double-click (Windows) or run it (Linux/macOS) to start. The transcript will be saved with a timestamp (e.g., `meeting_20251110_143052.txt`).

The launcher passes extra arguments through to `transcriber.py`, so you can run it with a filename prefix and/or flags. Timestamps default to wall-clock time (`--actual-time` is always passed). Windows example (Linux/macOS work the same way, just run the `.sh` script instead):

```bat
win-start-transcription.bat                  REM default: meeting_TIMESTAMP.txt
win-start-transcription.bat sprint-review    REM filename prefix
win-start-transcription.bat --silence-timeout 0   REM flags only: meeting_TIMESTAMP.txt
```

A first argument that starts with `-` is a flag, not a prefix. On every platform the launcher finds `transcriber.py` (and, from a source checkout, its `.venv`) next to itself, so you can run it from any folder (the transcript is saved in the folder you run it from). It doesn't choose a model size, so `--model small` or `--model-path <folder>` pass straight through, and output names the model you actually loaded.

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

# macOS: native system audio loopback (no virtual driver needed, macOS 14.4+)
python transcriber.py --live --coreaudio-tap --include-mic --mic-device 3
```

Live capture saves the transcript as it goes, to `transcript_<timestamp>.txt` in the current directory; the first line it prints names the file. Pass `--output <path>` to choose the file, or `--no-output` to only print the transcript.

**Understanding the Labels:**
- `[SYS]` - System audio (other meeting participants, videos, etc.)
- `[MIC]` - Your microphone (your voice)

Every live session labels its lines this way, including system-audio-only sessions (no `--include-mic`), which print `[SYS]` lines and the same compact status lines as a session with a microphone.

**Find Your Microphone Device:**
```bash
python transcriber.py --list-devices
```
Look for your Bluetooth headset in the input devices list and note the device number.

### Launchers

The repo includes ready-made launchers that set up the environment (venv) and invoke the transcriber:

```bat
REM Windows: transcribe a single file (language is auto-detected; works from any folder)
transcribe_file.bat <input_file> <output_file> [txt|srt|vtt]
REM Example:
transcribe_file.bat "meeting.mp4" "transcript.srt" srt

REM Windows: Teams meeting (WASAPI loopback + mic), with optional prefix/flags
REM Timestamps default to wall-clock time (--actual-time is always passed)
win-start-transcription.bat [name-prefix] [transcriber flags...]
REM Example:
win-start-transcription.bat sprint-review --silence-timeout 0
```

```bash
# Linux: Teams meeting (system audio + mic dual-capture), with optional prefix/flags
./linux-start-transcription.sh [name-prefix] [transcriber flags...]
# Example:
./linux-start-transcription.sh sprint-review --silence-timeout 0

# macOS: Teams meeting (Core Audio Tap dual-capture), with optional prefix/flags
./mac-start-transcription.sh [name-prefix] [transcriber flags...]
```

On Linux, use `linux_start_transcription.sh` (underscore-named) for simple system-audio-only live capture with manual device selection (see [Linux](#linux) under "Setup for Real-time Audio Capture") — a different, general-purpose script from the Teams-meeting-specific `linux-start-transcription.sh` (hyphen-named) above.

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
- `--coreaudio-tap` - Use Core Audio Process Tap for native system-audio loopback (macOS only, requires macOS 14.4+, no virtual driver needed)
- `--include-mic` - Include microphone capture alongside system audio (use with --wasapi or --coreaudio-tap)
- `--mic-device <id>` - Microphone device index (use --list-devices to find)
- `--model <size>` - Model size: tiny, base, small, medium, large, turbo (default: base)
- `--model-path <dir>` - Load the model from a local faster-whisper (CTranslate2) model folder, one containing `model.bin`, instead of resolving `--model` by name. Download one yourself, e.g. [Systran/faster-whisper-small](https://huggingface.co/Systran/faster-whisper-small). Output names the model after the folder (e.g. `faster-whisper-small`) unless `--model` is also given. English-only (`*.en`) models can only transcribe English.
- `--language <code>` - Language code (e.g., en, es, fr) - auto-detect if not specified
- `--task <type>` - Task: transcribe or translate (default: transcribe)
- `--output <path>` - Output file for transcript (default: `<name>_transcript_<timestamp>.<format>` for `--file`, `transcript_<timestamp>.txt` for `--live`, both in the current directory)
- `--no-output` - Live capture only: print the transcript without saving it to a file (cannot be combined with `--output`)
- `--format <type>` - Output format: txt, srt, vtt (default: txt)
- `--no-timestamps` - Exclude timestamps from text output
- `--actual-time` - Use wall-clock timestamps (local time) instead of relative offsets. In live capture, each line is stamped with the time its speech began, not when it was printed
- `--chunk-duration <seconds>` - Duration of audio chunks for streaming (default: 30)
- `--silence-timeout <seconds>` - Auto-stop after N seconds of silence (default: 600 = 10 min, 0 = never). A silence stop exits with code 0; if the system audio source itself ends (audio server restart, device disconnected), live capture prints `❌ System audio capture ended unexpectedly`, keeps the transcript so far and exits with code 1
- `--audio-device <id>` - Audio device index for live capture (-1 = auto-detect)
- `--setup-help` - Print audio loopback setup instructions and exit
- `--device <type>` - Device to run on: auto, cpu, cuda (default: auto)
- `--compute-type <type>` - Compute type: auto, int8, float16, float32 (default: auto)

## Setup for Real-time Audio Capture

### Windows

**For Bluetooth Headsets (Recommended - WASAPI Mode):**

The transcriber includes WASAPI loopback support which works with Bluetooth headsets. No additional setup required!

```bash
# Use WASAPI mode with microphone
python transcriber.py --live --wasapi --include-mic --mic-device 3

# Or just double-click win-start-transcription.bat
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

Uses PulseAudio/PipeWire monitor, auto-detected via `pactl`/`parec` (part of `pulseaudio-utils`, or PipeWire's own `pipewire-pulse` package — installed by default on most desktop Linux distributions). Identify your audio monitor device:
```bash
pactl list sources | grep -i monitor
```

The transcriber auto-detects and captures the real monitor source automatically — no manual device selection needed. It records the monitor of your default output device, and on PipeWire the recording follows the default when it changes mid-session (for example, when Bluetooth headphones connect), so the meeting audio keeps being transcribed. On PulseAudio itself this is untested. You can also start live transcription with the bundled launcher:

```bash
# Auto-detect the monitor device (default)
./linux_start_transcription.sh

# Use a specific PipeWire/PulseAudio monitor device index
./linux_start_transcription.sh 2
```

The script writes output to `transcription_<timestamp>.txt`, auto-stops after 10 minutes of silence (use `--silence-timeout 0` for continuous recording, or pass additional `transcriber.py` flags through as arguments).

### macOS

**Native Capture (Core Audio Process Tap, macOS 14.4+):**

```bash
python transcriber.py --live --coreaudio-tap --include-mic --mic-device 3
```

> **Known limitation, confirmed on real hardware:** macOS only shows the audio-capture permission prompt to an app launched as a proper `.app` bundle (e.g. the packaged desktop app) — plain `python transcriber.py` run from a terminal will not be prompted and will not receive audio, even if the terminal app itself has been granted access in System Settings > Privacy & Security > System Audio Recording Only. It fails clearly (a `NoAudioDataError` after a few seconds) rather than hanging silently, but the fallback below is the reliable option for bare CLI usage.

**Fallback (older macOS, or if native capture doesn't work): Virtual Audio Driver**

Install a virtual loopback driver and select it as the input device:

1. Install [BlackHole](https://github.com/ExistentialAudio/BlackHole) or [Loopback](https://rogueamoeba.com/loopback/)
2. Set it as (or aggregate it with) your output device so system audio is routed through it
3. Find its device index:
   ```bash
   python transcriber.py --list-devices
   ```
4. Run live capture against it:
   ```bash
   python transcriber.py --live --audio-device N --include-mic --mic-device M
   ```

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

## Troubleshooting

### "No loopback device found"
- **Windows**: Enable Stereo Mix or install VB-Cable
- **Linux**: Ensure PulseAudio/PipeWire is running, and `pactl`/`parec` are installed (`pulseaudio-utils`, or PipeWire's own `pipewire-pulse` package)
- **macOS**: Use `--coreaudio-tap` (macOS 14.4+), or install BlackHole/Loopback and select it with `--audio-device`
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
