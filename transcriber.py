#!/usr/bin/env python3
"""
Audio Transcriber CLI
Cross-platform audio transcription tool using faster-whisper.

License: GPLv2
"""

import os
os.environ.pop("TZ", None)

import sys

# A piped/detached stdout (no console attached -- exactly how the Tauri
# sidecar spawns this process) falls back to the Windows ANSI codepage,
# which can't encode the unicode symbols (checkmarks, emoji) used
# throughout this codebase's print() calls, crashing on the first one.
# Force UTF-8 regardless of how/where this is launched from.
#
# Also force line buffering on stdout: a piped stdout is block-buffered by
# default, so during a long-running --live session the GUI's transcript
# view would see nothing until the OS pipe buffer filled or the process
# exited (verified: a live session's banner/status lines only appeared
# once the process was killed, never while it was running normally).
for _stream in (sys.stdout, sys.stderr):
    if _stream and _stream.encoding and _stream.encoding.lower() != "utf-8":
        _stream.reconfigure(encoding="utf-8", errors="replace")
if sys.stdout:
    sys.stdout.reconfigure(line_buffering=True)

import signal
import argparse
import multiprocessing
import platform
from datetime import datetime
from pathlib import Path
from typing import Optional
import av.error
from audio_capture import AudioCapture, setup_loopback_instructions
from transcription_engine import TranscriptionEngine
import time

def _make_signal_handler(verbose: bool):
    """Ctrl+C handler, gated on --verbose -- the compact default prints its
    own one-line stop summary once cleanup finishes (see _print_summary),
    so this immediate acknowledgement is only needed as extra detail."""
    def signal_handler(signum, frame):
        if verbose:
            print("\n\n⏹️  Shutdown requested, stopping transcription...")
        raise KeyboardInterrupt
    return signal_handler


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Transcribe audio from video files or live audio streams",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Transcribe a video file
  python transcriber.py --file meeting.mp4
  
  # Transcribe with specific language
  python transcriber.py --file video.mp4 --language en
  
  # Use larger model for better accuracy
  python transcriber.py --file audio.wav --model medium
  
  # Save as SRT subtitle file
  python transcriber.py --file video.mp4 --format srt
  
  # List audio devices
  python transcriber.py --list-devices
  
  # Show loopback setup instructions
  python transcriber.py --setup-help
        """
    )
    
    # Input options
    input_group = parser.add_mutually_exclusive_group(required=False)
    input_group.add_argument(
        '--file', '-f',
        type=str,
        help='Path to video or audio file to transcribe'
    )
    input_group.add_argument(
        '--live', '-l',
        action='store_true',
        help='Capture and transcribe system audio in real-time'
    )
    
    # Model options
    parser.add_argument(
        '--model', '-m',
        type=str,
        default='base',
        choices=['tiny', 'base', 'small', 'medium', 'large', 'turbo'],
        help='Whisper model size (default: base). Larger = more accurate but slower'
    )

    parser.add_argument(
        '--model-path',
        type=str,
        default=None,
        help='Load the model from this local directory instead of resolving '
             '--model by name via the network/cache. Used by bundled builds '
             '(GUI sidecar, portable build); --model is still used for logging.'
    )

    parser.add_argument(
        '--language',
        type=str,
        default=None,
        help='Language code (e.g., en, es, fr). Leave empty for auto-detection'
    )
    
    parser.add_argument(
        '--task',
        type=str,
        default='transcribe',
        choices=['transcribe', 'translate'],
        help='Task: transcribe in original language or translate to English'
    )
    
    # Output options
    parser.add_argument(
        '--output', '-o',
        type=str,
        default=None,
        help='Output file path (default: transcript.txt in current directory)'
    )
    
    parser.add_argument(
        '--format',
        type=str,
        default='txt',
        choices=['txt', 'srt', 'vtt'],
        help='Output format (default: txt)'
    )
    
    parser.add_argument(
        '--no-timestamps',
        action='store_true',
        help='Exclude timestamps from text output'
    )

    parser.add_argument(
        '--actual-time',
        action='store_true',
        help='Use wall-clock timestamps (local time) instead of relative offsets'
    )

    parser.add_argument(
        '--save-audio',
        action='store_true',
        help='Save captured audio to a WAV file alongside the transcript (live mode only)'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Print full startup/device-detection/shutdown detail during live capture '
             '(default: a compact summary instead)'
    )

    # Device options
    parser.add_argument(
        '--device',
        type=str,
        default='auto',
        choices=['auto', 'cpu', 'cuda'],
        help='Device to run model on (default: auto-detect)'
    )
    
    parser.add_argument(
        '--compute-type',
        type=str,
        default='auto',
        choices=['auto', 'int8', 'float16', 'float32'],
        help='Compute type (default: auto - int8 for CPU, float16 for GPU)'
    )
    
    # Audio capture options
    parser.add_argument(
        '--audio-device',
        type=int,
        default=-1,
        help='Audio device index for live capture (-1 = auto-detect loopback)'
    )
    
    parser.add_argument(
        '--wasapi',
        action='store_true',
        help='Use WASAPI loopback (Windows only, works with Bluetooth headsets!)'
    )
    
    parser.add_argument(
        '--coreaudio-tap',
        action='store_true',
        help='Use macOS Core Audio Process Tap for native system-audio loopback (macOS 14.4+, no virtual driver required)'
    )

    parser.add_argument(
        '--include-mic',
        action='store_true',
        help='Also capture microphone along with system audio (for Teams meetings)'
    )
    
    parser.add_argument(
        '--mic-device',
        type=int,
        default=-1,
        help='Microphone device index (default: -1 = auto-detect)'
    )
    
    parser.add_argument(
        '--chunk-duration',
        type=float,
        default=30.0,
        help='Duration of audio chunks for streaming (seconds, default: 30)'
    )
    
    parser.add_argument(
        '--silence-timeout',
        type=float,
        default=600.0,  # 10 minutes
        help='Stop transcription after N seconds of silence (default: 600 = 10 minutes, 0 = never stop)'
    )
    
    # Utility options
    parser.add_argument(
        '--list-devices',
        action='store_true',
        help='List available audio devices and exit'
    )

    parser.add_argument(
        '--list-devices-json',
        action='store_true',
        help='List available audio devices as JSON and exit (for GUI consumers)'
    )

    parser.add_argument(
        '--setup-help',
        action='store_true',
        help='Show instructions for setting up audio loopback and exit'
    )

    args = parser.parse_args()

    # Handle utility options
    if args.list_devices:
        capture = AudioCapture()
        capture.list_devices()
        return 0

    if args.list_devices_json:
        capture = AudioCapture()
        capture.list_devices_json()
        return 0
    
    if args.setup_help:
        setup_loopback_instructions()
        return 0
    
    # Require either file or live mode
    if not args.file and not args.live:
        parser.print_help()
        print("\n❌ Error: Either --file or --live must be specified")
        return 1
    
    try:
        # Initialize transcription engine
        if args.verbose:
            print(f"\n{'='*60}")
            print("Audio Transcriber")
            print(f"{'='*60}\n")

        # Set up signal handler for Ctrl+C
        signal.signal(signal.SIGINT, _make_signal_handler(args.verbose))
        
        engine = TranscriptionEngine(
            model_size=args.model,
            device=args.device,
            compute_type=args.compute_type,
            model_path=args.model_path
        )
        
        # File transcription mode
        if args.file:
            return transcribe_file(engine, args)
        
        # Live capture mode
        elif args.live:
            platform_error = _validate_live_capture_platform(args)
            if platform_error:
                print(platform_error)
                return 1
            if args.wasapi:
                return transcribe_live_wasapi(engine, args)
            if args.coreaudio_tap:
                return transcribe_live_coreaudio_tap(engine, args)
            return transcribe_live_simple(engine, args)
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        return 130
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


def transcribe_file(engine: TranscriptionEngine, args) -> int:
    """Handle file-based transcription."""
    file_path = Path(args.file)
    
    if not file_path.exists():
        print(f"❌ File not found: {file_path}")
        return 1
    
    # Cosmetic classification only -- the engine decodes audio and video
    # files the same way (via PyAV, bundled with faster-whisper), so this
    # no longer drives any different code path, just the log line.
    video_extensions = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v'}
    audio_extensions = {'.mp3', '.wav', '.flac', '.m4a', '.ogg', '.opus', '.wma'}

    file_ext = file_path.suffix.lower()
    audio_file = str(file_path)

    if file_ext in video_extensions:
        print(f"📹 Video file detected: {file_path.name}\n")
    elif file_ext in audio_extensions:
        print(f"🎵 Audio file detected: {file_path.name}\n")
    else:
        print(f"⚠️  Unknown file type: {file_ext}")
        print("Attempting to process as audio file...\n")

    base_time = datetime.now() if args.actual_time else None

    # Transcribe (with incremental saving)
    try:
        segments, info = engine.transcribe_file(
            audio_file,
            language=args.language,
            task=args.task,
            output_path=args.output,
            use_actual_time=args.actual_time,
            base_time=base_time
        )
    except av.error.FFmpegError as e:
        print(f"❌ Could not decode {file_path.name}: unsupported or corrupt media ({e})")
        return 1

    # Determine output path. Auto-derived names are stamped so transcribing
    # the same file twice never silently overwrites the first result --
    # the GUI never passes --output for file mode, so this is the path it
    # always takes.
    if args.output:
        output_path = Path(args.output)
    else:
        stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_name = f"{file_path.stem}_transcript_{stamp}.{args.format}"
        output_path = Path.cwd() / output_name

    # Save transcript
    engine.save_transcript(
        segments,
        str(output_path),
        format_type=args.format,
        include_timestamps=not args.no_timestamps,
        use_actual_time=args.actual_time,
        base_time=base_time
    )

    # Print summary
    print(f"\n{'='*60}")
    print("Transcription Summary")
    print(f"{'='*60}")
    print(f"Input file: {file_path}")
    print(f"Language: {info['language']} (confidence: {info['language_probability']:.1%})")
    print(f"Duration: {info['duration']:.1f} seconds")
    print(f"Segments: {len(segments)}")
    print(f"Output: {output_path}")
    print(f"{'='*60}\n")

    return 0


def _process_audio_chunk(
    engine,
    audio_data,
    time_offset,
    language=None,
    sample_rate=16000
):
    """Resample to 16 kHz, transcribe a chunk, apply the running offset, format relative timestamps.

    Returns (results, spoke, new_offset) where results is a list of
    (timestamp_str, adjusted_segment) tuples and spoke is True if any
    non-empty text was transcribed. timestamp_str is always the relative
    [MM:SS -> MM:SS] range; callers substitute a live wall-clock stamp
    (read from the system clock at emit time) when actual-time mode is on.
    """
    import numpy as np
    from scipy import signal

    if audio_data.dtype != np.float32:
        audio_data = audio_data.astype(np.float32)
    if sample_rate != 16000:
        num_samples = int(len(audio_data) * 16000 / sample_rate)
        audio_data = signal.resample(audio_data, num_samples)

    chunk_duration_sec = len(audio_data) / 16000
    segments = engine.transcribe_chunk(audio_data, language=language)

    results = []
    for seg in segments:
        if not seg['text'].strip():
            continue
        adjusted_start = seg['start'] + time_offset
        adjusted_end = seg['end'] + time_offset
        timestamp = engine.format_timestamp(adjusted_start, adjusted_end)
        adjusted_seg = seg.copy()
        adjusted_seg['start'] = adjusted_start
        adjusted_seg['end'] = adjusted_end
        results.append((timestamp, adjusted_seg))

    return results, bool(results), time_offset + chunk_duration_sec


def _validate_live_capture_platform(args) -> Optional[str]:
    """Return an error message if a platform-specific live-capture flag doesn't
    match the current OS, else None. Pulled out as a pure function (reads
    only args + platform.system()) so it's testable without constructing a
    TranscriptionEngine."""
    current = platform.system()
    if args.wasapi and current != "Windows":
        return "❌ --wasapi is only supported on Windows. Use --coreaudio-tap on macOS, or omit both on Linux."
    if args.coreaudio_tap and current != "Darwin":
        return "❌ --coreaudio-tap is only supported on macOS. Use --wasapi on Windows, or omit both on Linux."
    return None


def _wall_clock_stamp() -> str:
    """Current local date/time, read fresh at the call site."""
    return datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")


def _print_header(model: str, language: Optional[str], chunk_duration: float, mode: str = "") -> None:
    """Print header for live transcription."""
    print("\n" + "="*60)
    print("Live Audio Transcription")
    print("="*60)
    print(f"Model: {model}")
    print(f"Language: {language or 'auto-detect'}")
    print(f"Chunk duration: {chunk_duration}s")
    if mode:
        print(f"Mode: {mode}")
    print("="*60 + "\n")


def _setup_output_files(args, native_rate: int = 16000, include_mic: bool = False):
    """
    Open and initialize output transcript and WAV files.

    Returns: (output_file, wav_file, audio_save_path)
    For WASAPI with mic: (output_file, sys_wav_file, mic_wav_file, sys_audio_save_path, mic_audio_save_path)
    """
    import wave

    output_file = None
    if args.output:
        output_file = open(args.output, 'w', encoding='utf-8')
        output_file.write(f"# Live Transcription Started\n")
        output_file.write(f"# Model: {args.model}\n")
        output_file.write(f"# Language: {args.language or 'auto-detect'}\n\n")
        output_file.flush()

    wav_file = None
    audio_save_path = None
    if args.save_audio:
        if args.output:
            audio_save_path = str(Path(args.output).with_suffix('.wav'))
        else:
            audio_save_path = str(Path.cwd() / f"live_audio_{time.strftime('%Y%m%d_%H%M%S')}.wav")
        wav_file = wave.open(audio_save_path, 'wb')
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)  # int16
        wav_file.setframerate(native_rate)
        print(f"💾 Recording audio to: {audio_save_path}")

    return output_file, wav_file, audio_save_path


def _print_compact_stop(all_segments: list, output_path: Optional[str]) -> None:
    """One-line stop summary, printed regardless of --verbose -- the compact
    counterpart to _print_summary's full banner
    (openspec/changes/compact-live-cli-output)."""
    n = len(all_segments)
    if output_path:
        print(f"Stopped — {n} segment{'s' if n != 1 else ''} saved to {output_path}")
    else:
        print(f"Stopped — {n} segment{'s' if n != 1 else ''} (not saved to a file)")


def _print_summary(all_segments: list, args, output_path: Optional[str] = None, audio_save_path: Optional[str] = None, sys_audio_save_path: Optional[str] = None, mic_audio_save_path: Optional[str] = None, merged_audio_save_path: Optional[str] = None) -> None:
    """Print summary of transcription completion."""
    print(f"\n{'='*60}")
    print("Transcription Complete")
    print(f"{'='*60}")
    print(f"Total segments: {len(all_segments)}")
    if output_path:
        print(f"Saved to: {output_path}")
    if audio_save_path:
        print(f"Audio saved to: {audio_save_path}")
    if sys_audio_save_path:
        print(f"System audio saved to: {sys_audio_save_path}")
    if mic_audio_save_path:
        print(f"Microphone audio saved to: {mic_audio_save_path}")
    if merged_audio_save_path:
        print(f"Merged audio saved to: {merged_audio_save_path}")
    print(f"{'='*60}\n")


def _merge_sys_mic_wav(sys_path: str, mic_path: str, out_path: str) -> None:
    """
    Merge mono 16-bit system and mic WAV recordings into one stereo WAV
    (system on the left channel, mic on the right), truncated to the
    shorter of the two -- matching ffmpeg's amerge duration=shortest
    behavior this replaces. Both inputs are files this same module just
    wrote via `wave.open(..., 'wb')`, so their format is known: mono,
    16-bit, 16000 Hz.
    """
    import wave
    import numpy as np

    with wave.open(sys_path, 'rb') as sys_wav, wave.open(mic_path, 'rb') as mic_wav:
        params = sys_wav.getparams()
        sys_samples = np.frombuffer(sys_wav.readframes(sys_wav.getnframes()), dtype=np.int16)
        mic_samples = np.frombuffer(mic_wav.readframes(mic_wav.getnframes()), dtype=np.int16)

    n = min(len(sys_samples), len(mic_samples))
    stereo = np.empty(n * 2, dtype=np.int16)
    stereo[0::2] = sys_samples[:n]
    stereo[1::2] = mic_samples[:n]

    with wave.open(out_path, 'wb') as out_wav:
        out_wav.setnchannels(2)
        out_wav.setsampwidth(params.sampwidth)
        out_wav.setframerate(params.framerate)
        out_wav.writeframes(stereo.tobytes())


def transcribe_live_simple(engine: TranscriptionEngine, args) -> int:
    """Simple live transcription for non-WASAPI mode."""
    import numpy as np
    import sounddevice as sd

    # Get device info to use its native sample rate
    device_id = args.audio_device if args.audio_device >= 0 else None
    if device_id is not None:
        device_info = sd.query_devices(device_id)
        native_rate = int(device_info['default_samplerate'])
        print(f"Using device native sample rate: {native_rate} Hz")
    else:
        native_rate = 48000

    # Print header
    if args.verbose:
        _print_header(args.model, args.language, args.chunk_duration)

    # Initialize audio capture with native sample rate
    capture = AudioCapture(sample_rate=native_rate, channels=1)

    # Storage
    all_segments = []
    audio_buffer = []
    chunk_duration_samples = int(native_rate * args.chunk_duration)
    time_offset = 0.0  # Track cumulative time offset
    last_speech_time = time.time()  # Track time of last detected speech
    silence_timeout_enabled = args.silence_timeout > 0

    # Overlap settings to prevent speech loss at chunk boundaries
    overlap_duration = 1.0  # 1 second overlap
    overlap_samples = int(native_rate * overlap_duration)  # In native rate

    # Setup output and WAV files
    output_file, wav_file, audio_save_path = _setup_output_files(args, native_rate)

    print("🎙️  Listening... (Press Ctrl+C to stop)\n")
    if silence_timeout_enabled:
        print(f"⏱️  Auto-stop after {args.silence_timeout/60:.1f} minutes of silence\n")
    
    def audio_callback(audio_chunk):
        """Process incoming audio chunks."""
        nonlocal time_offset, last_speech_time

        # Check for silence timeout
        if silence_timeout_enabled:
            elapsed_silence = time.time() - last_speech_time
            if elapsed_silence > args.silence_timeout:
                print(f"\n⏱️  Stopping: {args.silence_timeout/60:.1f} minutes of silence detected")
                raise KeyboardInterrupt("Silence timeout")

        # Write raw audio to disk before any processing (native rate, float32 -> int16)
        if wav_file:
            int16_data = (audio_chunk.flatten() * 32767.0).clip(-32768, 32767).astype(np.int16)
            wav_file.writeframes(int16_data.tobytes())

        audio_buffer.append(audio_chunk.flatten())
        
        # Check if we have enough audio for transcription
        total_samples = sum(len(chunk) for chunk in audio_buffer)
        
        if total_samples >= chunk_duration_samples:
            # Concatenate all buffered audio
            audio_data = np.concatenate(audio_buffer)
            audio_buffer.clear()
            
            # Keep overlap for next chunk to prevent speech cutoff
            if len(audio_data) > overlap_samples:
                audio_buffer.append(audio_data[-overlap_samples:])
            
            # Transcribe
            try:
                results, spoke, new_offset = _process_audio_chunk(
                    engine, audio_data, time_offset,
                    language=args.language, sample_rate=native_rate
                )
                time_offset = new_offset

                # Reset silence timer if speech was detected
                if spoke:
                    last_speech_time = time.time()

                # Print and save results
                for timestamp, seg in results:
                    stamp = _wall_clock_stamp() if args.actual_time else timestamp
                    line = f"{stamp} {seg['text']}"
                    print(line)
                    all_segments.append(seg)
                    
                    # Write immediately to file
                    if output_file:
                        output_file.write(line + "\n")
                        output_file.flush()
                
                if not results:
                    print("  (no speech detected)")
            
            except Exception as e:
                print(f"  ❌ Error transcribing: {e}")

    
    try:
        # Start capturing
        capture.capture_stream(
            callback=audio_callback,
            device=args.audio_device
        )
    except KeyboardInterrupt:
        print("\n\n⏹️  Stopping transcription...")
    finally:
        if output_file:
            output_file.close()
        if wav_file:
            wav_file.close()

    # Print summary
    if args.verbose:
        _print_summary(all_segments, args, output_path=args.output, audio_save_path=audio_save_path)
    _print_compact_stop(all_segments, args.output)

    return 0


def transcribe_live_wasapi(engine: TranscriptionEngine, args) -> int:
    """Live transcription using WASAPI loopback (Windows, Bluetooth-compatible)."""
    import numpy as np
    from wasapi_capture import WASAPICapture
    from scipy import signal
    import sounddevice as sd
    import queue
    import threading
    import wave

    # Print header
    if args.verbose:
        _print_header(args.model, args.language, args.chunk_duration, "WASAPI Loopback (Bluetooth-compatible)")

    # Initialize WASAPI capture for system audio
    capture = WASAPICapture()

    # Get system audio loopback device
    if args.audio_device >= 0:
        device_index = args.audio_device
    else:
        # Auto-detect default loopback
        device_info = capture.get_default_loopback_device()
        if not device_info:
            # --list-devices/--list-devices-json enumerate sounddevice's
            # device list, a separate index space from pyaudiowpatch's
            # WASAPI loopback devices -- they can't produce a usable
            # --audio-device value, so don't send anyone there
            # (openspec/changes/add-wasapi-device-override).
            print("❌ No WASAPI loopback device found!")
            print("Check that an audio output device is enabled in Windows Sound settings, or specify --audio-device <n> if you know the device index.")
            return 1
        device_index = device_info['index']
        loopback_name = device_info['name']
        if args.verbose:
            print(f"Auto-detected loopback: {loopback_name}\n")

    # Get microphone device if requested
    mic_stream = None
    mic_channels = 1  # Default to mono
    mic_name = None
    if args.include_mic:
        if args.mic_device >= 0:
            mic_device = args.mic_device
        else:
            # Auto-detect default microphone
            try:
                mic_info = sd.query_devices(kind='input')
                mic_device = mic_info['index'] if isinstance(mic_info, dict) else None
                if args.verbose:
                    print(f"Auto-detected microphone: {mic_info['name']}\n")
            except:
                print("⚠️  Could not auto-detect microphone")
                return 1

        # Get device info to determine max channels
        try:
            mic_info = sd.query_devices(mic_device)
            max_input_channels = mic_info.get('max_input_channels', 0)
            if max_input_channels == 0:
                print(f"❌ Error: Device {mic_device} is not an input device (0 input channels)")
                print(f"   Device name: {mic_info['name']}")
                print("\nUse --list-devices to find your microphone device number")
                return 1
            # Use device's max channels (usually 1 for headset, 2 for arrays)
            mic_channels = min(max_input_channels, 2)
            mic_name = mic_info['name']
            if args.verbose:
                print(f"Microphone capture enabled (device {mic_device})")
                print(f"   Device: {mic_name}")
                print(f"   Channels: {mic_channels}\n")
        except Exception as e:
            print(f"❌ Error querying microphone device {mic_device}: {e}")
            return 1

    # Compact default status: identity, model/language/mode/device summary,
    # and a listening confirmation -- the one thing every run needs to show,
    # regardless of --verbose (openspec/changes/compact-live-cli-output).
    print(f"Transcriber → {args.output}" if args.output else "Transcriber (not saving a transcript file)")
    mode_summary = "WASAPI"
    if args.include_mic:
        mode_summary += f" + mic ({mic_name})" if mic_name else " + mic"
    print(f"{args.model} model ({engine.device}/{engine.compute_type}), {args.language or 'auto-detect'} language, {mode_summary}")
    listen_line = "Listening... (Ctrl+C to stop"
    if args.silence_timeout > 0:
        listen_line += f", auto-stop after {args.silence_timeout/60:.1f}m silence"
    print(listen_line + ")")

    # Storage
    all_segments = []
    last_speech_time = time.time()  # Track time of last detected speech
    silence_timeout_enabled = args.silence_timeout > 0

    # Overlap settings to prevent speech loss at chunk boundaries
    overlap_duration = 1.0  # 1 second overlap between chunks

    # WASAPI typically uses 48kHz, we need 16kHz for Whisper
    wasapi_rate = 48000
    target_rate = 16000
    # Chunk duration in TARGET rate (16kHz) since we resample before buffering
    chunk_duration_samples = int(target_rate * args.chunk_duration)
    mic_chunk_samples = int(target_rate * 5.0)  # Transcribe mic every 5 seconds
    overlap_samples = int(target_rate * overlap_duration)

    # Thread-safe queues: capture callbacks push raw audio here (non-blocking)
    # The transcription worker thread drains these queues independently.
    sys_audio_queue = queue.Queue()
    mic_audio_queue = queue.Queue()
    stop_event = threading.Event()
    write_lock = threading.Lock()

    # Open output file for incremental writing
    output_file = None
    if args.output:
        output_file = open(args.output, 'w', encoding='utf-8')
        output_file.write(f"# Live Transcription (WASAPI Loopback")
        if args.include_mic:
            output_file.write(f" + Microphone")
        output_file.write(f")\n")
        output_file.write(f"# Model: {args.model}\n")
        output_file.write(f"# Language: {args.language or 'auto-detect'}\n\n")
        output_file.flush()

    # Open WAV file(s) for audio recording if requested
    sys_wav_file = None
    mic_wav_file = None
    sys_audio_save_path = None
    mic_audio_save_path = None
    if args.save_audio:
        base_stem = Path(args.output).stem if args.output else f"live_audio_{time.strftime('%Y%m%d_%H%M%S')}"
        base_dir = Path(args.output).parent if args.output else Path.cwd()
        sys_audio_save_path = str(base_dir / f"{base_stem}_sys.wav")
        sys_wav_file = wave.open(sys_audio_save_path, 'wb')
        sys_wav_file.setnchannels(1)
        sys_wav_file.setsampwidth(2)  # int16
        sys_wav_file.setframerate(target_rate)
        print(f"💾 Recording system audio to: {sys_audio_save_path}")
        if args.include_mic:
            mic_audio_save_path = str(base_dir / f"{base_stem}_mic.wav")
            mic_wav_file = wave.open(mic_audio_save_path, 'wb')
            mic_wav_file.setnchannels(1)
            mic_wav_file.setsampwidth(2)  # int16
            mic_wav_file.setframerate(16000)
            print(f"💾 Recording microphone to: {mic_audio_save_path}")

    # Microphone callback: write to disk and enqueue, never blocks
    def mic_callback(indata, frames, time_info, status):
        if status and "overflow" not in str(status).lower():
            print(f"Mic status: {status}")
        mic_audio = indata[:, 0] if len(indata.shape) > 1 else indata
        chunk = mic_audio.flatten().copy()
        if mic_wav_file:
            int16_data = (chunk * 32767.0).clip(-32768, 32767).astype(np.int16)
            mic_wav_file.writeframes(int16_data.tobytes())
        mic_audio_queue.put(chunk)

    # Start microphone capture if enabled
    if args.include_mic:
        mic_stream = sd.InputStream(
            device=mic_device,
            channels=mic_channels,
            samplerate=16000,
            callback=mic_callback
        )
        mic_stream.start()

    # WASAPI callback: enqueue RAW audio only (no resampling here), never blocks
    def audio_callback(audio_chunk):
        if silence_timeout_enabled:
            elapsed_silence = time.time() - last_speech_time
            if elapsed_silence > args.silence_timeout:
                print(f"\nAuto-stop: {args.silence_timeout/60:.1f} minutes of silence detected")
                raise KeyboardInterrupt("Silence timeout")
        sys_audio_queue.put(audio_chunk)

    def _emit(line):
        """Print and write a transcription line (thread-safe)."""
        print(line)
        if output_file:
            with write_lock:
                output_file.write(line + "\n")
                output_file.flush()

    def _drain_and_transcribe(queue, buffer, threshold, tag, gate, transform=None):
        """Dedicated thread: drains an audio queue and runs inference."""
        nonlocal last_speech_time
        time_offset = 0.0

        while not stop_event.is_set() or not queue.empty():
            while not queue.empty():
                item = queue.get_nowait()
                if transform:
                    item = transform(item)
                buffer.append(item)

            total = sum(len(c) for c in buffer)
            if total >= threshold:
                data = np.concatenate(buffer)
                if len(data) > overlap_samples:
                    buffer[:] = [data[-overlap_samples:]]
                else:
                    buffer.clear()
                if not gate or np.max(np.abs(data)) > 0.01:
                    try:
                        results, spoke, time_offset = _process_audio_chunk(
                            engine, data, time_offset,
                            language=args.language, sample_rate=target_rate
                        )
                        if spoke:
                            last_speech_time = time.time()
                        for ts, seg in results:
                            stamp = _wall_clock_stamp() if args.actual_time else ts
                            _emit(f"{stamp} [{tag}] {seg['text']}")
                            all_segments.append(seg)
                    except Exception as e:
                        print(f"  ❌ Error transcribing {tag.lower()} audio: {e}")
            else:
                time.sleep(0.05)

    def transform_sys(raw):
        """Resample 48kHz -> 16kHz away from the capture callback, persist 16kHz WAV."""
        resampled = signal.resample(raw, int(len(raw) * target_rate / wasapi_rate))
        if sys_wav_file:
            int16_data = (resampled * 32767.0).clip(-32768, 32767).astype(np.int16)
            sys_wav_file.writeframes(int16_data.tobytes())
        return resampled

    # Start dedicated worker threads (sys and mic run in parallel, never blocking each other)
    sys_thread = threading.Thread(
        target=_drain_and_transcribe,
        args=(sys_audio_queue, [], chunk_duration_samples, "SYS", False, transform_sys),
        daemon=True
    )
    sys_thread.start()
    mic_thread = None
    if args.include_mic:
        mic_thread = threading.Thread(
            target=_drain_and_transcribe,
            args=(mic_audio_queue, [], mic_chunk_samples, "MIC", True),
            daemon=True
        )
        mic_thread.start()

    try:
        # Start capturing (callbacks only enqueue audio now, never block)
        capture.capture_stream(
            callback=audio_callback,
            device_index=device_index,
            verbose=args.verbose
        )
    except KeyboardInterrupt:
        print("\n\nStopping transcription...")
    finally:
        stop_event.set()
        sys_thread.join(timeout=60)
        if mic_thread:
            mic_thread.join(timeout=60)
        if mic_stream:
            mic_stream.stop()
            mic_stream.close()
        if output_file:
            output_file.close()
        if sys_wav_file:
            sys_wav_file.close()
        if mic_wav_file:
            mic_wav_file.close()
        capture.cleanup()

    # Merge sys + mic WAV into a stereo file if both were recorded
    merged_audio_save_path = None
    if sys_audio_save_path and mic_audio_save_path:
        base_stem = Path(sys_audio_save_path).stem.replace('_sys', '')
        base_dir = Path(sys_audio_save_path).parent
        merged_audio_save_path = str(base_dir / f"{base_stem}_merged.wav")
        print("\nMerging system and microphone audio...")
        try:
            _merge_sys_mic_wav(sys_audio_save_path, mic_audio_save_path, merged_audio_save_path)
            print(f"✓ Merged audio saved to: {merged_audio_save_path}")
        except Exception as e:
            print(f"⚠️  Could not merge audio files: {e}")
            merged_audio_save_path = None

    # Print summary
    if args.verbose:
        _print_summary(all_segments, args, output_path=args.output, sys_audio_save_path=sys_audio_save_path, mic_audio_save_path=mic_audio_save_path, merged_audio_save_path=merged_audio_save_path)
    _print_compact_stop(all_segments, args.output)

    return 0


def transcribe_live_coreaudio_tap(engine: TranscriptionEngine, args) -> int:
    """Live transcription using macOS's native Core Audio Process Tap (no virtual driver required).

    UNVERIFIED against real macOS hardware as of writing -- see
    openspec/changes/add-macos-capture/design.md. Structurally mirrors
    transcribe_live_wasapi (dual sys/mic queues drained by dedicated
    threads) since it's the same shape of problem: a background capture
    source pushing audio that must never block on transcription.
    """
    import numpy as np
    from macos_capture import (
        MacOSCapture,
        UnsupportedMacOSVersionError,
        AudioCapturePermissionError,
        MacOSCaptureError,
    )
    from scipy import signal
    import sounddevice as sd
    import queue
    import threading
    import wave

    if args.verbose:
        _print_header(args.model, args.language, args.chunk_duration, "Core Audio Process Tap (macOS)")

    capture = MacOSCapture()
    device_info = capture.get_default_loopback_device()
    if not device_info:
        print("❌ Native system-audio capture requires macOS 14.4+.")
        print("Use --live --audio-device N with a virtual audio driver (BlackHole/Loopback) instead.")
        return 1
    if args.verbose:
        print(f"Using: {device_info['name']}\n")

    # Get microphone device if requested
    mic_stream = None
    mic_channels = 1
    mic_name = None
    if args.include_mic:
        if args.mic_device >= 0:
            mic_device = args.mic_device
        else:
            try:
                mic_info = sd.query_devices(kind='input')
                mic_device = mic_info['index'] if isinstance(mic_info, dict) else None
                if args.verbose:
                    print(f"Auto-detected microphone: {mic_info['name']}\n")
            except Exception:
                print("⚠️  Could not auto-detect microphone")
                return 1

        try:
            mic_info = sd.query_devices(mic_device)
            max_input_channels = mic_info.get('max_input_channels', 0)
            if max_input_channels == 0:
                print(f"❌ Error: Device {mic_device} is not an input device (0 input channels)")
                print(f"   Device name: {mic_info['name']}")
                print("\nUse --list-devices to find your microphone device number")
                return 1
            mic_channels = min(max_input_channels, 2)
            mic_name = mic_info['name']
            if args.verbose:
                print(f"Microphone capture enabled (device {mic_device})")
                print(f"   Device: {mic_name}")
                print(f"   Channels: {mic_channels}\n")
        except Exception as e:
            print(f"❌ Error querying microphone device {mic_device}: {e}")
            return 1

    # Compact default status -- mirrors transcribe_live_wasapi
    # (openspec/changes/compact-live-cli-output).
    print(f"Transcriber → {args.output}" if args.output else "Transcriber (not saving a transcript file)")
    mode_summary = "Core Audio tap"
    if args.include_mic:
        mode_summary += f" + mic ({mic_name})" if mic_name else " + mic"
    print(f"{args.model} model ({engine.device}/{engine.compute_type}), {args.language or 'auto-detect'} language, {mode_summary}")
    listen_line = "Listening... (Ctrl+C to stop"
    if args.silence_timeout > 0:
        listen_line += f", auto-stop after {args.silence_timeout/60:.1f}m silence"
    print(listen_line + ")")

    # Storage
    all_segments = []
    last_speech_time = time.time()
    silence_timeout_enabled = args.silence_timeout > 0

    overlap_duration = 1.0
    target_rate = 16000
    chunk_duration_samples = int(target_rate * args.chunk_duration)
    mic_chunk_samples = int(target_rate * 5.0)
    overlap_samples = int(target_rate * overlap_duration)

    sys_audio_queue = queue.Queue()
    mic_audio_queue = queue.Queue()
    stop_event = threading.Event()
    write_lock = threading.Lock()

    output_file = None
    if args.output:
        output_file = open(args.output, 'w', encoding='utf-8')
        output_file.write(f"# Live Transcription (Core Audio Process Tap")
        if args.include_mic:
            output_file.write(f" + Microphone")
        output_file.write(f")\n")
        output_file.write(f"# Model: {args.model}\n")
        output_file.write(f"# Language: {args.language or 'auto-detect'}\n\n")
        output_file.flush()

    sys_wav_file = None
    mic_wav_file = None
    sys_audio_save_path = None
    mic_audio_save_path = None
    if args.save_audio:
        base_stem = Path(args.output).stem if args.output else f"live_audio_{time.strftime('%Y%m%d_%H%M%S')}"
        base_dir = Path(args.output).parent if args.output else Path.cwd()
        sys_audio_save_path = str(base_dir / f"{base_stem}_sys.wav")
        sys_wav_file = wave.open(sys_audio_save_path, 'wb')
        sys_wav_file.setnchannels(1)
        sys_wav_file.setsampwidth(2)
        sys_wav_file.setframerate(target_rate)
        print(f"💾 Recording system audio to: {sys_audio_save_path}")
        if args.include_mic:
            mic_audio_save_path = str(base_dir / f"{base_stem}_mic.wav")
            mic_wav_file = wave.open(mic_audio_save_path, 'wb')
            mic_wav_file.setnchannels(1)
            mic_wav_file.setsampwidth(2)
            mic_wav_file.setframerate(16000)
            print(f"💾 Recording microphone to: {mic_audio_save_path}")

    def mic_callback(indata, frames, time_info, status):
        if status and "overflow" not in str(status).lower():
            print(f"Mic status: {status}")
        mic_audio = indata[:, 0] if len(indata.shape) > 1 else indata
        chunk = mic_audio.flatten().copy()
        if mic_wav_file:
            int16_data = (chunk * 32767.0).clip(-32768, 32767).astype(np.int16)
            mic_wav_file.writeframes(int16_data.tobytes())
        mic_audio_queue.put(chunk)

    if args.include_mic:
        mic_stream = sd.InputStream(
            device=mic_device,
            channels=mic_channels,
            samplerate=16000,
            callback=mic_callback
        )
        mic_stream.start()

    def sys_callback(audio_chunk):
        if silence_timeout_enabled:
            elapsed_silence = time.time() - last_speech_time
            if elapsed_silence > args.silence_timeout:
                print(f"\nAuto-stop: {args.silence_timeout/60:.1f} minutes of silence detected")
                raise KeyboardInterrupt("Silence timeout")
        sys_audio_queue.put(audio_chunk)

    def _emit(line):
        print(line)
        if output_file:
            with write_lock:
                output_file.write(line + "\n")
                output_file.flush()

    def _drain_and_transcribe(q, buffer, threshold, tag, gate, transform=None):
        nonlocal last_speech_time
        time_offset = 0.0

        while not stop_event.is_set() or not q.empty():
            while not q.empty():
                item = q.get_nowait()
                if transform:
                    item = transform(item)
                buffer.append(item)

            total = sum(len(c) for c in buffer)
            if total >= threshold:
                data = np.concatenate(buffer)
                if len(data) > overlap_samples:
                    buffer[:] = [data[-overlap_samples:]]
                else:
                    buffer.clear()
                if not gate or np.max(np.abs(data)) > 0.01:
                    try:
                        results, spoke, time_offset = _process_audio_chunk(
                            engine, data, time_offset,
                            language=args.language, sample_rate=target_rate
                        )
                        if spoke:
                            last_speech_time = time.time()
                        for ts, seg in results:
                            stamp = _wall_clock_stamp() if args.actual_time else ts
                            _emit(f"{stamp} [{tag}] {seg['text']}")
                            all_segments.append(seg)
                    except Exception as e:
                        print(f"  ❌ Error transcribing {tag.lower()} audio: {e}")
            else:
                time.sleep(0.05)

    def transform_sys(raw):
        """Resample from the tap's native rate (known only once capture starts) to
        16kHz away from the capture callback, persist 16kHz WAV."""
        native_rate = capture.sample_rate or target_rate
        if native_rate != target_rate:
            raw = signal.resample(raw, int(len(raw) * target_rate / native_rate))
        if sys_wav_file:
            int16_data = (raw * 32767.0).clip(-32768, 32767).astype(np.int16)
            sys_wav_file.writeframes(int16_data.tobytes())
        return raw

    # Start dedicated worker threads (sys and mic run in parallel, never blocking each other)
    sys_thread = threading.Thread(
        target=_drain_and_transcribe,
        args=(sys_audio_queue, [], chunk_duration_samples, "SYS", False, transform_sys),
        daemon=True
    )
    sys_thread.start()
    mic_thread = None
    if args.include_mic:
        mic_thread = threading.Thread(
            target=_drain_and_transcribe,
            args=(mic_audio_queue, [], mic_chunk_samples, "MIC", True),
            daemon=True
        )
        mic_thread.start()

    exit_code = 0
    try:
        capture.capture_stream(callback=sys_callback, device_index=device_info['index'], verbose=args.verbose)
    except KeyboardInterrupt:
        print("\n\nStopping transcription...")
    except (UnsupportedMacOSVersionError, AudioCapturePermissionError, MacOSCaptureError) as e:
        print(f"❌ {e}")
        exit_code = 1
    finally:
        stop_event.set()
        sys_thread.join(timeout=60)
        if mic_thread:
            mic_thread.join(timeout=60)
        if mic_stream:
            mic_stream.stop()
            mic_stream.close()
        if output_file:
            output_file.close()
        if sys_wav_file:
            sys_wav_file.close()
        if mic_wav_file:
            mic_wav_file.close()
        capture.cleanup()

    # Merge sys + mic WAV into a stereo file if both were recorded
    merged_audio_save_path = None
    if sys_audio_save_path and mic_audio_save_path:
        base_stem = Path(sys_audio_save_path).stem.replace('_sys', '')
        base_dir = Path(sys_audio_save_path).parent
        merged_audio_save_path = str(base_dir / f"{base_stem}_merged.wav")
        print("\nMerging system and microphone audio...")
        try:
            _merge_sys_mic_wav(sys_audio_save_path, mic_audio_save_path, merged_audio_save_path)
            print(f"✓ Merged audio saved to: {merged_audio_save_path}")
        except Exception as e:
            print(f"⚠️  Could not merge audio files: {e}")
            merged_audio_save_path = None

    # Print summary
    if args.verbose:
        _print_summary(all_segments, args, output_path=args.output, sys_audio_save_path=sys_audio_save_path, mic_audio_save_path=mic_audio_save_path, merged_audio_save_path=merged_audio_save_path)
    _print_compact_stop(all_segments, args.output)

    return exit_code


if __name__ == "__main__":
    # Required for the frozen (PyInstaller) sidecar: multiprocessing's
    # resource_tracker relaunches itself by re-invoking sys.executable,
    # which in a frozen onefile build is this binary itself, not a real
    # Python interpreter. freeze_support() intercepts that re-invocation
    # before the app's own imports run -- without it, the relaunch re-runs
    # this whole script from scratch and dies on a circular import.
    multiprocessing.freeze_support()
    sys.exit(main())
