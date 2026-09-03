# Audio Transcriber

A cross-platform CLI tool for transcribing audio from video files and live audio streams using faster-whisper, with **real-time streaming** support.

## Features

- 🎥 Transcribe audio from local video files (MP4, AVI, MKV, etc.)
- 🎙️ **Real-time transcription** from system audio (live meetings, streaming videos)
- 💻 Cross-platform: Works on Windows, Linux, and macOS (live capture on macOS requires 14.4+ or a virtual audio driver — see [macOS](#macos) below)
- 🔒 100% offline and local - all data stays on your machine
- ⚡ Fast transcription with faster-whisper (MIT license)
- 🎯 Multiple output formats (TXT, SRT, VTT)

## Desktop GUI (in development)

A native desktop app (Tauri shell + this CLI as a bundled sidecar) is in progress under `src-tauri/` and `src/` — see `openspec/changes/add-tauri-gui/` for the design and current status.

### Download and run

There is no installer, no admin prompt, and no uninstaller — each platform ships as a single downloadable artifact that runs directly once extracted, and removing it is just deleting that folder/file. There is also no auto-update: getting a new version means downloading and replacing it.

- **Windows**: download the `.zip`, extract it anywhere, run `transcriber-gui.exe` from inside the extracted folder.
- **Linux**: download the `.AppImage`, `chmod +x` it, then run it. AppImages need FUSE to run directly; if your system doesn't have it, use `./transcriber-gui.AppImage --appimage-extract-and-run` instead.
- **macOS**: download the `.zip`, unzip it, and open `Transcriber.app`. The build is unsigned, so Gatekeeper will warn on first launch — right-click (or Control-click) the app and choose Open to bypass it once. Live capture is not yet available on macOS (see [macOS](#macos) below); file transcription works.

### Building it yourself

**No local Rust toolchain needed on Windows** — a Docker image (`docker/tauri-build.Dockerfile`) cross-compiles the Windows portable build from a Linux container (mingw-w64 GNU target), and builds the Linux AppImage natively in the same container:

```powershell
python build_sidecar.py                                          # freeze transcriber.py -> dist/windows/transcriber-sidecar.exe
python fetch_sidecar_resources.py                                # stage the `base` model into src-tauri/resources/model/
copy dist\windows\transcriber-sidecar.exe src-tauri\binaries\transcriber-sidecar-x86_64-pc-windows-gnu.exe

.\docker\build.ps1
# Windows artifact: dist\portable\Transcriber.zip
# Linux artifact:   dist\portable\*.AppImage
```

If you have a native Rust toolchain + [Tauri CLI](https://tauri.app/) available instead (e.g. Linux, macOS, or Windows without this machine's toolchain-install restriction), stage the sidecar binary under `src-tauri/binaries/transcriber-sidecar-<target-triple>.exe`, then:

```bash
cargo tauri build          # from src-tauri/
python build_portable.py   # assembles the portable artifact for the current OS into dist/portable/
```

#### Native Linux build from WSL (no Docker, no container)

**Check out the repo on WSL's own (ext4) filesystem, not under `/mnt/c/...`.** `/mnt/c` is a 9p/DrvFs mount of the Windows drive — `CARGO_TARGET_DIR` (below) keeps cargo's *output* off it, but the *source* (`Cargo.toml`, every `src-tauri/src/*.rs`, `tauri.conf.json`) still has to be read from wherever the checkout lives, and Tauri writes generated schema files into `src-tauri/gen/` on every build. From a native path (e.g. `~/repos/transcriber`) none of that touches the Windows filesystem at all. Confirmed working from `~/repos/transcriber`: the `.venv` Windows Python interop (used to freeze the Windows sidecar, see the Windows build notes) still reaches the venv fine via WSL's `\\wsl.localhost\...` path — only that one-shot freeze crosses the boundary, in the direction that doesn't matter for build speed.

Building directly in a WSL (or any native Linux) environment needs the same system packages the CI Linux job and the Docker image (`docker/tauri-build.Dockerfile`) use, plus `rustup` and the Tauri CLI:

```bash
sudo apt-get install -y build-essential pkg-config libssl-dev \
    libwebkit2gtk-4.1-dev libgtk-3-dev libayatana-appindicator3-dev \
    librsvg2-dev patchelf
rustup default stable
cargo install --locked tauri-cli --version "^2"
```

Point cargo's `target/` directory at a native (ext4) filesystem path — if the repo is checked out on a Windows-mounted path (e.g. `/mnt/c/...` under WSL), cargo's incremental-compile I/O against that mount is the dominant cost of a build, not the compilation itself:

```bash
export CARGO_TARGET_DIR="$HOME/.cache/transcriber-target"
```

Then build as above (`cargo tauri build` from `src-tauri/`, `python build_portable.py`) — `build_portable.py` honors `CARGO_TARGET_DIR` automatically.

The bundled artifact ships the `base` Whisper model (~145MB) for a fully offline first run. No ffmpeg bundling is needed — the sidecar decodes audio and video via PyAV (bundled with faster-whisper), not an external ffmpeg binary; see `openspec/changes/drop-ffmpeg-dependency/`.

The GUI sidecar always passes an explicit `--model-path` pointing at its bundled model directory (resolved relative to the running app, so it works the same whether run from the extracted Windows folder, the AppImage, or the `.app`), instead of relying on faster-whisper's network/cache-based model lookup. The CLI gained the same `--model-path <dir>` flag for anyone running from a bundled build directly.

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

```bash
# Basic transcription
python transcriber.py --file path/to/video.mp4

# Specify language and larger model
python transcriber.py --file meeting.mp4 --language en --model medium
```

### Real-time Audio Capture

**Quick Start for Teams Meetings (Windows with Bluetooth headset):**

Double-click `start_teams_transcription.bat` to automatically start transcription with both system audio and microphone capture. The transcript will be saved with a timestamp (e.g., `meeting_20251110_143052.txt`).

The launcher passes extra arguments through to `transcriber.py`, so you can run it with a filename prefix and/or flags. Timestamps default to wall-clock time (`--actual-time` is always passed):

```bat
start_teams_transcription.bat                  REM default: meeting_TIMESTAMP.txt
start_teams_transcription.bat sprint-review    REM filename prefix
start_teams_transcription.bat --silence-timeout 0
start_teams_transcription.bat --save-audio
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

# macOS: native system audio loopback (no virtual driver needed, macOS 14.4+)
python transcriber.py --live --coreaudio-tap --include-mic --mic-device 3
```

**Understanding the Labels:**
- `[SYS]` - System audio (other meeting participants, videos, etc.)
- `[MIC]` - Your microphone (your voice)

**Find Your Microphone Device:**
```bash
python transcriber.py --list-devices
```
Look for your Bluetooth headset in the input devices list and note the device number.

### Launchers

The repo includes ready-made launchers that set up the environment (venv + ffmpeg PATH) and invoke the transcriber:

```bat
REM Windows: transcribe a single file
transcribe_file.bat <input_file> <output_file> [txt|srt|vtt]
REM Example:
transcribe_file.bat "meeting.mp4" "transcript.srt" srt

REM Windows: merge pre-recorded mic + system WAVs into one transcript
merge_and_transcribe.bat <mic_file.wav> <sys_file.wav> [output_file] [txt|srt|vtt]
REM Example:
merge_and_transcribe.bat mic.wav sys.wav transcript.txt

REM Windows: Teams meeting (WASAPI loopback + mic), with optional prefix/flags
REM Timestamps default to wall-clock time (--actual-time is always passed)
start_teams_transcription.bat [name-prefix] [transcriber flags...]
REM Example:
start_teams_transcription.bat sprint-review --silence-timeout 0
```

On Linux, use `start_transcription.sh` for live capture (see [Linux](#linux) under "Setup for Real-time Audio Capture").

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
- `--language <code>` - Language code (e.g., en, es, fr) - auto-detect if not specified
- `--task <type>` - Task: transcribe or translate (default: transcribe)
- `--output <path>` - Output file for transcript (default: auto-generated)
- `--format <type>` - Output format: txt, srt, vtt (default: txt)
- `--no-timestamps` - Exclude timestamps from text output
- `--actual-time` - Use wall-clock timestamps (local time) instead of relative offsets
- `--save-audio` - Save captured audio to WAV files alongside the transcript (live mode only). In WASAPI mode with `--include-mic`, this writes `<base>_sys.wav`, `<base>_mic.wav`, and a merged stereo `<base>_merged.wav`
- `--chunk-duration <seconds>` - Duration of audio chunks for streaming (default: 30)
- `--silence-timeout <seconds>` - Auto-stop after N seconds of silence (default: 600 = 10 min, 0 = never)
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

The transcriber will auto-detect monitor devices automatically. You can also start live transcription with the bundled launcher:

```bash
# Auto-detect the monitor device (default)
./start_transcription.sh

# Use a specific PipeWire/PulseAudio monitor device index
./start_transcription.sh 2
```

The script writes output to `transcription_<timestamp>.txt`, auto-stops after 10 minutes of silence (use `--silence-timeout 0` for continuous recording, or pass additional `transcriber.py` flags through as arguments).

### macOS

**Native Capture (Recommended - Core Audio Process Tap, macOS 14.4+):**

No additional setup required — grant the audio-capture permission when macOS prompts on first use.

```bash
python transcriber.py --live --coreaudio-tap --include-mic --mic-device 3
```

> **Status:** this capture path was built and documented without access to macOS hardware to verify against. If it doesn't behave as documented, please file an issue — the fallback below is a reliable alternative in the meantime.

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

## License

GPLv2

This software uses faster-whisper (MIT License), compatible with GPLv2.

## Troubleshooting

### "No loopback device found"
- **Windows**: Enable Stereo Mix or install VB-Cable
- **Linux**: Ensure PulseAudio/PipeWire is running
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
