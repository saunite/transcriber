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
from collections import namedtuple
from datetime import datetime
from pathlib import Path
from typing import Optional
import av.error
from audio_capture import AudioCapture, setup_loopback_instructions
from transcription_engine import NoDecodableAudioError, TranscriptionEngine
import time

# Set when a live session was asked to stop (Ctrl+C/SIGINT, or the silence
# timeout). Every capture_stream swallows KeyboardInterrupt and returns
# normally, so a normal return only means "the source ended on its own" when
# no stop was requested (openspec/changes/fix-engine-liveness).
_stop_requested = False


def _request_stop(reason=""):
    global _stop_requested
    _stop_requested = True
    raise KeyboardInterrupt(reason)


# Set once a lost audio source has been detected: the process then exits
# directly, since PortAudio's own shutdown can block on an audio server that
# went away (see __main__).
_source_lost = False


def _source_ended_unexpectedly() -> bool:
    """Called after capture returned normally: True unless a stop was requested."""
    global _source_lost
    lost = not _stop_requested
    _source_lost = _source_lost or lost
    return lost


def _print_or_stop(line: str) -> None:
    """Print a line, stopping the session gracefully once nobody reads stdout.

    The desktop app reads the engine's stdout; when the app goes away (closed,
    crashed or killed) that pipe breaks. A worker thread's print then raised
    and killed only that thread, while the main capture loop kept recording,
    orphaned, with its unpacked copy in use (openspec/changes/fix-sidecar-temp-leak).
    Raising KeyboardInterrupt in the main thread takes the normal stop path."""
    try:
        print(line)
    except (BrokenPipeError, ValueError):  # ValueError: stdout already closed
        if not _stop_requested:
            # interrupt_main() runs the SIGINT handler, which marks the stop
            # itself; marking it here first would make the handler ignore it
            # as a repeat.
            import _thread
            _thread.interrupt_main()


def _close_stream_bounded(stream, timeout: float = 5.0) -> bool:
    """Stop and close a PortAudio stream without hanging the session's end.

    After the audio server restarts (systemctl --user restart pipewire),
    stream.stop() never returns -- it waits on a PipeWire connection that is
    gone -- which kept the engine alive and silent instead of reporting the
    lost source (openspec/changes/fix-engine-liveness). Returns False if it
    was abandoned after `timeout`."""
    import threading

    done = threading.Event()

    def close():
        try:
            stream.stop()
            stream.close()
        except Exception:
            pass
        done.set()

    threading.Thread(target=close, daemon=True).start()
    if done.wait(timeout):
        return True
    print("⚠️  The microphone stream did not close; continuing without it")
    return False


# Printed as the session's very last line, after the stop summary, so the GUI
# can show it as the reason (openspec/changes/fix-engine-liveness).
LOST_SOURCE_MESSAGE = "❌ System audio capture ended unexpectedly"


def _make_signal_handler(verbose: bool):
    """Ctrl+C handler, gated on --verbose -- the compact default prints its
    own one-line stop summary once cleanup finishes (see _print_summary),
    so this immediate acknowledgement is only needed as extra detail."""
    def signal_handler(signum, frame):
        # Once a stop is under way, a repeat interrupt is ignored. The desktop
        # app signals the engine and its PyInstaller launcher, which forwards
        # the signal again: that second KeyboardInterrupt landed mid-cleanup,
        # abandoned the worker joins, and the interpreter crashed on exit
        # ("free(): invalid size"), too slowly to beat the stop grace -- so
        # the engine was killed and its unpacked copy left in /tmp
        # (openspec/changes/fix-sidecar-temp-leak).
        if _stop_requested:
            return
        if verbose:
            print("\n\n⏹️  Shutdown requested, stopping transcription...")
        _request_stop()
    return signal_handler


def _bundled_model_path(model: str) -> Optional[str]:
    """The model shipped next to the standalone (frozen) CLI in a release's
    CLI archive, if this run can use it (openspec/changes/01-add-release-pipeline).
    Only `base` is bundled; other sizes keep resolving by name."""
    if model != "base" or not getattr(sys, "frozen", False):
        return None
    model_dir = Path(sys.executable).parent / "model"
    return str(model_dir) if (model_dir / "model.bin").exists() else None


def _model_label(model: Optional[str], model_path: Optional[str]) -> str:
    """How output names the model: --model if given, else the --model-path
    folder's name, else the default size -- never a size that wasn't loaded
    (openspec/changes/choose-model-folder)."""
    if model:
        return model
    return Path(model_path).name if model_path else 'base'


def _live_output_path(args, now: datetime) -> Optional[str]:
    """Where a live session saves its transcript: --output if given, nothing
    with --no-output, otherwise a stamped transcript_<YYYYMMDD_HHMMSS>.txt in
    the current directory -- the GUI's default naming, so a new session never
    overwrites an old one (openspec/changes/add-live-default-output)."""
    if args.output or args.no_output or not args.live:
        return args.output
    return f"transcript_{now:%Y%m%d_%H%M%S}.txt"


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
        default=None,
        choices=['tiny', 'base', 'small', 'medium', 'large', 'turbo'],
        help='Whisper model size (default: base). Larger = more accurate but slower'
    )

    parser.add_argument(
        '--model-path',
        type=str,
        default=None,
        help='Load the model from this local directory instead of resolving '
             '--model by name via the network/cache. Used by bundled builds '
             '(GUI sidecar, portable build). Output names the model after this '
             'folder unless --model is also given.'
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
        help='Output file path (default: file mode writes <name>_transcript_<timestamp>.<format>, '
             'live capture writes transcript_<timestamp>.txt, both in the current directory)'
    )

    parser.add_argument(
        '--no-output',
        action='store_true',
        help='Live capture only: print the transcript without saving it to a file'
    )

    # For the desktop app only: one line per audio chunk that went through the
    # pipeline, speech or not, so a quiet room is not mistaken for a stalled
    # engine (openspec/changes/fix-engine-liveness). Hidden from --help.
    parser.add_argument('--heartbeat', action='store_true', help=argparse.SUPPRESS)
    
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
    args.model_label = _model_label(args.model, args.model_path)
    args.model = args.model or 'base'
    if not args.model_path:
        args.model_path = _bundled_model_path(args.model)
    if args.output and args.no_output:
        parser.error("--output and --no-output cannot be combined")
    args.output = _live_output_path(args, datetime.now())

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
            model_size=args.model_label,  # names a --model-path folder in the load message
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
    except NoDecodableAudioError as e:
        print(f"❌ No decodable audio in {file_path.name} ({e}) -- unsupported or corrupt media")
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


def _new_resampler():
    """A 16 kHz mono float32 resampler; the input rate comes from the first frame."""
    import av
    return av.AudioResampler(format="flt", layout="mono", rate=16000)


def _resample(resampler, block, rate, flush=False):
    """Resample a mono float32 block with PyAV's libswresample, which is already
    bundled for decoding -- no SciPy (openspec/changes/02-resample-with-pyav).

    One resampler per continuous stream keeps its filter state across blocks,
    so block edges carry no artifacts, and a block too short to yield a sample
    is simply held until the next one. flush=True also drains what it holds,
    for a one-off chunk.
    """
    import av
    import numpy as np

    frames = []
    if len(block):
        frame = av.AudioFrame.from_ndarray(
            np.ascontiguousarray(block, dtype=np.float32)[None, :], format="flt", layout="mono")
        frame.sample_rate = rate
        frames = resampler.resample(frame)
    if flush:
        frames = list(frames) + list(resampler.resample(None))
    out = [f.to_ndarray()[0] for f in frames]
    return np.concatenate(out) if out else np.empty(0, dtype=np.float32)


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

    if audio_data.dtype != np.float32:
        audio_data = audio_data.astype(np.float32)
    if sample_rate != 16000:
        # A fresh, flushed resampler: chunks here overlap by a second, so one
        # continuous stream would be fed the same audio twice.
        audio_data = _resample(_new_resampler(), audio_data, sample_rate, flush=True)

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


def _resolve_mic_device(args) -> Optional[int]:
    """Resolve which input device a live session should use for the mic.

    Returns the device index, or None when no microphone can be used at all --
    the caller then aborts. An explicit --mic-device is passed through
    untouched; validating it stays with the caller, whose "not an input
    device" error is unchanged.

    Why the fallback exists: a frozen build whose bundled ALSA library cannot
    load the host's plugins reports no default input even when real inputs are
    present, and that used to end the session outright
    (openspec/changes/fix-linux-live-capture-alsa).
    """
    # Imported here, not at module scope, like every other caller in this
    # file: importing sounddevice initialises PortAudio, and a --file run has
    # no reason to pay for that.
    import sounddevice as sd

    if args.mic_device >= 0:
        return args.mic_device

    try:
        mic_info = sd.query_devices(kind='input')
        index = mic_info['index'] if isinstance(mic_info, dict) else None
        if index is not None:
            if args.verbose:
                print(f"Auto-detected microphone: {mic_info['name']}\n")
            return index
    except Exception:
        pass  # no default input -- fall through to the scan below

    try:
        devices = sd.query_devices()
    except Exception:
        devices = []
    for device in devices:
        if device.get('max_input_channels', 0) > 0:
            print(f"⚠️  No default microphone; using {device['name']}")
            return device['index']

    print("❌ No microphone found.")
    print("   Use --list-devices to see the available devices, then --mic-device <n> to choose one.")
    return None


MicConfig = namedtuple("MicConfig", "device channels name rate")


def _resolve_mic_config(args) -> Optional[MicConfig]:
    """Pick the mic and how to open it, for every dual-capture platform.

    Returns None after printing why when no usable microphone exists. A mic
    that refuses 16 kHz (a raw ALSA hw: device, for one) is opened at its own
    default rate and resampled by the caller instead of failing the session
    (openspec/changes/fix-gui-file-queue-and-linux-live) -- once Linux-only,
    now shared (openspec/changes/01-merge-dual-capture-paths).
    """
    import sounddevice as sd

    mic_device = _resolve_mic_device(args)
    if mic_device is None:
        return None
    try:
        mic_info = sd.query_devices(mic_device)
        max_input_channels = mic_info.get('max_input_channels', 0)
        if max_input_channels == 0:
            print(f"❌ Error: Device {mic_device} is not an input device (0 input channels)")
            print(f"   Device name: {mic_info['name']}")
            print("\nUse --list-devices to find your microphone device number")
            return None
        channels = min(max_input_channels, 2)
        try:
            sd.check_input_settings(device=mic_device, channels=channels, samplerate=16000)
            rate = 16000
        except Exception:
            rate = int(mic_info['default_samplerate'])
        if args.verbose:
            print(f"Microphone capture enabled (device {mic_device})")
            print(f"   Device: {mic_info['name']}")
            print(f"   Channels: {channels}\n")
    except Exception as e:
        print(f"❌ Error querying microphone device {mic_device}: {e}")
        return None
    return MicConfig(mic_device, channels, mic_info['name'], rate)


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


def _setup_output_files(args):
    """
    Open and initialize the output transcript file.

    Returns: output_file
    """
    output_file = None
    if args.output:
        output_file = open(args.output, 'w', encoding='utf-8')
        output_file.write(f"# Live Transcription Started\n")
        output_file.write(f"# Model: {args.model_label}\n")
        output_file.write(f"# Language: {args.language or 'auto-detect'}\n\n")
        output_file.flush()

    return output_file


def _print_compact_stop(all_segments: list, output_path: Optional[str]) -> None:
    """One-line stop summary, printed regardless of --verbose -- the compact
    counterpart to _print_summary's full banner
    (openspec/changes/compact-live-cli-output)."""
    n = len(all_segments)
    if output_path:
        print(f"Stopped — {n} segment{'s' if n != 1 else ''} saved to {output_path}")
    else:
        print(f"Stopped — {n} segment{'s' if n != 1 else ''} (not saved to a file)")


def _print_summary(all_segments: list, args, output_path: Optional[str] = None) -> None:
    """Print summary of transcription completion."""
    print(f"\n{'='*60}")
    print("Transcription Complete")
    print(f"{'='*60}")
    print(f"Total segments: {len(all_segments)}")
    if output_path:
        print(f"Saved to: {output_path}")
    print(f"{'='*60}\n")


def _run_dual_capture(engine, args, *, title, mode_summary, sys_rate, run_sys, mic,
                      cleanup=None, capture_errors=()) -> int:
    """The shared core of every dual-source live path: system audio plus an
    optional microphone, each drained and transcribed on its own thread and
    tagged [SYS]/[MIC] (openspec/changes/01-merge-dual-capture-paths).

    Platforms pass in only what differs:
      title          -- the transcript file's "# Live Transcription (...)" label
      mode_summary   -- the capture-mode part of the compact status line
      sys_rate()     -- the system source's real sample rate, read on its first
                        block (Core Audio only knows it once capture starts)
      run_sys(on_chunk, enqueue, check_silence)
                     -- blocks while system audio is captured. on_chunk
                        enqueues after checking the silence timeout, for
                        callbacks on the capture's own drain loop; enqueue
                        only enqueues, for PortAudio's thread, which must
                        never raise; check_silence raises KeyboardInterrupt
                        once the timeout passes, for a poll loop.
      mic            -- a MicConfig, or None to capture system audio only
      cleanup        -- releases the capture after the session
      capture_errors -- exceptions that end the session with exit code 1
    """
    import numpy as np
    import sounddevice as sd
    import queue
    import threading
    global _stop_requested, _source_lost
    _stop_requested = False
    _source_lost = False

    # Compact default status: identity, model/language/mode/device summary,
    # and a listening confirmation (openspec/changes/compact-live-cli-output).
    # The GUI waits for the "Listening..." line before showing capture as
    # active (openspec/changes/fix-capturing-shown-before-listening).
    print(f"Transcriber → {args.output}" if args.output else "Transcriber (not saving a transcript file)")
    print(f"{args.model_label} model ({engine.device}/{engine.compute_type}), {args.language or 'auto-detect'} language, {mode_summary}")
    listen_line = "Listening... (Ctrl+C to stop"
    if args.silence_timeout > 0:
        listen_line += f", auto-stop after {args.silence_timeout/60:.1f}m silence"
    print(listen_line + ")")

    all_segments = []
    last_speech_time = time.time()
    target_rate = 16000
    chunk_duration_samples = int(target_rate * args.chunk_duration)
    mic_chunk_samples = int(target_rate * 5.0)
    overlap_samples = int(target_rate * 1.0)  # keeps speech at chunk boundaries

    sys_audio_queue = queue.Queue()
    mic_audio_queue = queue.Queue()
    stop_event = threading.Event()
    write_lock = threading.Lock()

    output_file = None
    if args.output:
        output_file = open(args.output, 'w', encoding='utf-8')
        output_file.write(f"# Live Transcription ({title})\n")
        output_file.write(f"# Model: {args.model_label}\n")
        output_file.write(f"# Language: {args.language or 'auto-detect'}\n\n")
        output_file.flush()

    def check_silence():
        if args.silence_timeout > 0 and (time.time() - last_speech_time) > args.silence_timeout:
            print(f"\nAuto-stop: {args.silence_timeout/60:.1f} minutes of silence detected")
            _request_stop("Silence timeout")

    def on_chunk(audio_chunk):
        check_silence()
        sys_audio_queue.put(audio_chunk)

    # Capture callbacks only enqueue -- they run on the capture's own thread
    # and must return immediately or the stream overflows.
    def mic_callback(indata, frames, time_info, status):
        if status and "overflow" not in str(status).lower():
            print(f"Mic status: {status}")
        mic_audio = indata[:, 0] if len(indata.shape) > 1 else indata
        mic_audio_queue.put(mic_audio.flatten().copy())

    def _emit(line):
        """Write and print a transcription line (thread-safe). The file comes
        first, so a line is kept even when nobody reads stdout any more."""
        if output_file:
            with write_lock:
                output_file.write(line + "\n")
                output_file.flush()
        _print_or_stop(line)

    def _to_target_rate(rate_fn):
        """Resample from a source's real rate to 16 kHz, on the worker thread.
        The rate is read on the first block (Core Audio only knows it once
        capture starts). One stateful resampler per stream carries its filter
        across blocks, and holds few-frame slivers -- which some backends,
        the ALSA "pipewire" plugin device in particular, deliver -- until the
        next block (openspec/changes/02-resample-with-pyav)."""
        rate = None
        resampler = None

        def transform(raw):
            nonlocal rate, resampler
            if rate is None:
                rate = rate_fn() or target_rate
                if rate != target_rate:
                    resampler = _new_resampler()
            return _resample(resampler, raw, rate) if resampler else raw
        return transform

    def _drain_and_transcribe(q, buffer, threshold, tag, gate, transform):
        """Dedicated thread: drains an audio queue and runs inference."""
        nonlocal last_speech_time
        time_offset = 0.0

        while not stop_event.is_set() or not q.empty():
            while not q.empty():
                buffer.append(transform(q.get_nowait()))

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
                if args.heartbeat:
                    _print_or_stop(f"HEARTBEAT {tag}")
            else:
                time.sleep(0.05)

    # Separate worker threads, so system audio and the mic never block each other.
    sys_thread = threading.Thread(
        target=_drain_and_transcribe,
        args=(sys_audio_queue, [], chunk_duration_samples, "SYS", False, _to_target_rate(sys_rate)),
        daemon=True
    )
    sys_thread.start()
    mic_thread = None
    if mic:
        mic_thread = threading.Thread(
            target=_drain_and_transcribe,
            args=(mic_audio_queue, [], mic_chunk_samples, "MIC", True, _to_target_rate(lambda: mic.rate)),
            daemon=True
        )
        mic_thread.start()

    exit_code = 0
    source_lost = False
    mic_stream = None
    try:
        if mic:
            mic_stream = sd.InputStream(device=mic.device, channels=mic.channels, samplerate=mic.rate,
                                        blocksize=1024, callback=mic_callback)
            mic_stream.start()
        run_sys(on_chunk, sys_audio_queue.put, check_silence)
        # A normal return with no stop requested: the system audio source ended
        # on its own (parec EOF, a WASAPI read error).
        if _source_ended_unexpectedly():
            exit_code, source_lost = 1, True
    except KeyboardInterrupt:
        print("\n\nStopping transcription...")
    except capture_errors as e:
        print(f"❌ {e}")
        exit_code = 1
    finally:
        # Stop feeding the queues before waiting for the workers to drain them.
        if mic_stream:
            _close_stream_bounded(mic_stream)
        stop_event.set()
        sys_thread.join(timeout=60)
        if mic_thread:
            mic_thread.join(timeout=60)
        if output_file:
            output_file.close()
        if cleanup:
            cleanup()

    if args.verbose:
        _print_summary(all_segments, args, output_path=args.output)
    _print_compact_stop(all_segments, args.output)
    if exit_code == 1 and source_lost:
        print(LOST_SOURCE_MESSAGE)
    return exit_code


def transcribe_live_simple(engine: TranscriptionEngine, args) -> int:
    """Simple live transcription for non-WASAPI/non-Core-Audio-tap mode (the
    Linux default). Dual-source (system audio + mic) is split into its own
    function since it needs the WASAPI-style queue/worker-thread structure;
    this single-source path is left completely unchanged
    (openspec/changes/add-linux-dual-source-live-capture)."""
    if args.include_mic:
        return _transcribe_live_linux_dual(engine, args)

    global _stop_requested, _source_lost
    _stop_requested = False
    _source_lost = False

    import numpy as np
    import sounddevice as sd

    # Get device info to use its native sample rate
    device_id = args.audio_device if args.audio_device >= 0 else None
    # sounddevice/PortAudio's ALSA-only device list can't see the real
    # PipeWire/PulseAudio monitor source (openspec/changes/fix-linux-loopback-detection)
    # -- auto-detect (no explicit --audio-device) on Linux goes through the
    # real pactl/parec monitor instead. An explicit device index keeps
    # today's sounddevice behavior unchanged.
    use_linux_loopback = platform.system() == "Linux" and device_id is None
    loopback_name = None
    if device_id is not None:
        device_info = sd.query_devices(device_id)
        native_rate = int(device_info['default_samplerate'])
        print(f"Using device native sample rate: {native_rate} Hz")
    elif use_linux_loopback:
        native_rate = 16000  # parec resamples server-side; nothing to do here
    else:
        native_rate = 48000

    # Print header
    if args.verbose:
        _print_header(args.model_label, args.language, args.chunk_duration)

    # Initialize audio capture with native sample rate
    if use_linux_loopback:
        from linux_loopback_capture import LinuxLoopbackCapture
        capture = LinuxLoopbackCapture()
        device_info = capture.get_default_loopback_device()
        if not device_info:
            print("\n⚠️  Warning: Could not auto-detect loopback device.")
            print("Please specify a device manually or set up audio loopback:")
            print("  - Use PulseAudio/PipeWire monitor source")
            print("  - Run: pactl list sources | grep -i monitor")
            return 1
        loopback_name = device_info['name']
        print(f"Using loopback device: {loopback_name}")
    else:
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

    # Setup output file
    output_file = _setup_output_files(args)

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
                _request_stop("Silence timeout")

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
            if args.heartbeat:
                _print_or_stop("HEARTBEAT SYS")

    
    exit_code = 0
    try:
        # Start capturing
        if use_linux_loopback:
            capture.capture_stream(callback=audio_callback, device_index=loopback_name, verbose=args.verbose)
        else:
            capture.capture_stream(callback=audio_callback, device=args.audio_device)
        if _source_ended_unexpectedly():
            exit_code = 1
    except KeyboardInterrupt:
        print("\n\n⏹️  Stopping transcription...")
    finally:
        if output_file:
            output_file.close()

    # Print summary
    if args.verbose:
        _print_summary(all_segments, args, output_path=args.output)
    _print_compact_stop(all_segments, args.output)
    if exit_code == 1:
        print(LOST_SOURCE_MESSAGE)

    return exit_code


def _transcribe_live_linux_dual(engine: TranscriptionEngine, args) -> int:
    """Linux dual-source live transcription: system audio (auto-detected
    PulseAudio/PipeWire monitor) + microphone, tagged [SYS]/[MIC]
    (openspec/changes/add-linux-dual-source-live-capture). The capture loop
    itself is shared with WASAPI and Core Audio in _run_dual_capture."""
    import sounddevice as sd

    if args.verbose:
        _print_header(args.model_label, args.language, args.chunk_duration, "System audio + microphone (Linux)")

    # Resolve system-audio (loopback/monitor) device. sounddevice/PortAudio
    # can't see the real PipeWire/PulseAudio monitor source
    # (openspec/changes/fix-linux-loopback-detection) -- auto-detect on
    # Linux goes through pactl/parec instead. An explicit device index (or
    # a non-Linux platform reaching this function) keeps the
    # sounddevice-based path.
    device_id = args.audio_device if args.audio_device >= 0 else None

    if platform.system() == "Linux" and device_id is None:
        from linux_loopback_capture import LinuxLoopbackCapture
        linux_capture = LinuxLoopbackCapture()
        device_info = linux_capture.get_default_loopback_device()
        if not device_info:
            print("\n⚠️  Warning: Could not auto-detect loopback device.")
            print("Please specify a device manually or set up audio loopback:")
            print("  - Use PulseAudio/PipeWire monitor source")
            print("  - Run: pactl list sources | grep -i monitor")
            return 1
        sys_name = device_info['name']
        native_rate = 16000  # parec resamples server-side
        if args.verbose:
            print(f"Auto-detected loopback: {sys_name}\n")

        def run_sys(on_chunk, enqueue, check_silence):
            # The parec callback runs on LinuxLoopbackCapture's own drain loop,
            # not PortAudio's thread, so it may raise the silence timeout.
            # capture_stream cleans up its own subprocess.
            linux_capture.capture_stream(callback=on_chunk, device_index=sys_name, verbose=args.verbose)
    else:
        audio_capture = AudioCapture()
        if device_id is not None:
            sys_device = device_id
        else:
            sys_device = audio_capture.get_loopback_device()
            if sys_device is None:
                print("\n⚠️  Warning: Could not auto-detect loopback device.")
                print("Available devices:")
                audio_capture.list_devices()
                print("\nPlease specify a device manually or set up audio loopback:")
                print("  - Use PulseAudio/PipeWire monitor source")
                print("  - Run: pactl list sources | grep -i monitor")
                return 1
            if args.verbose:
                print(f"Auto-detected loopback: {sd.query_devices(sys_device)['name']}\n")

        sys_info = sd.query_devices(sys_device)
        native_rate = int(sys_info['default_samplerate'])
        sys_name = sys_info['name']

        def run_sys(on_chunk, enqueue, check_silence):
            # PortAudio's callback thread must only enqueue; the silence
            # timeout is checked from this poll loop instead.
            def sys_callback(indata, frames, time_info, status):
                if status and "overflow" not in str(status).lower():
                    print(f"Audio callback status: {status}", file=sys.stderr)
                sys_audio = indata[:, 0] if len(indata.shape) > 1 else indata
                enqueue(sys_audio.flatten().copy())

            with sd.InputStream(device=sys_device, channels=1, samplerate=native_rate,
                                blocksize=1024, callback=sys_callback):
                while True:
                    check_silence()
                    time.sleep(0.1)

    mic = _resolve_mic_config(args)
    if mic is None:
        return 1

    return _run_dual_capture(
        engine, args,
        title="System Audio + Microphone",
        mode_summary=f"System audio ({sys_name}) + mic ({mic.name})",
        sys_rate=lambda: native_rate,
        run_sys=run_sys,
        mic=mic,
    )


def transcribe_live_wasapi(engine: TranscriptionEngine, args) -> int:
    """Live transcription using WASAPI loopback (Windows, Bluetooth-compatible).
    The capture loop is shared in _run_dual_capture."""
    from wasapi_capture import WASAPICapture

    # Print header
    if args.verbose:
        _print_header(args.model_label, args.language, args.chunk_duration, "WASAPI Loopback (Bluetooth-compatible)")

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

    mic = None
    if args.include_mic:
        mic = _resolve_mic_config(args)
        if mic is None:
            return 1

    mode_summary = "WASAPI"
    if mic:
        mode_summary += f" + mic ({mic.name})"

    return _run_dual_capture(
        engine, args,
        title="WASAPI Loopback" + (" + Microphone" if mic else ""),
        mode_summary=mode_summary,
        # The rate WASAPICapture actually opened the device at, which is not
        # always 48 kHz (openspec/changes/01-merge-dual-capture-paths).
        sys_rate=lambda: capture.sample_rate,
        run_sys=lambda on_chunk, enqueue, check_silence: capture.capture_stream(
            callback=on_chunk, device_index=device_index, verbose=args.verbose),
        mic=mic,
        cleanup=capture.cleanup,
    )


def transcribe_live_coreaudio_tap(engine: TranscriptionEngine, args) -> int:
    """Live transcription using macOS's native Core Audio Process Tap (no virtual driver required).

    UNVERIFIED against real macOS hardware as of writing -- see
    openspec/changes/add-macos-capture/design.md. The capture loop is shared
    with Linux and WASAPI in _run_dual_capture.
    """
    from macos_capture import (
        MacOSCapture,
        UnsupportedMacOSVersionError,
        AudioCapturePermissionError,
        MacOSCaptureError,
    )

    if args.verbose:
        _print_header(args.model_label, args.language, args.chunk_duration, "Core Audio Process Tap (macOS)")

    capture = MacOSCapture()
    device_info = capture.get_default_loopback_device()
    if not device_info:
        print("❌ Native system-audio capture requires macOS 14.4+.")
        print("Use --live --audio-device N with a virtual audio driver (BlackHole/Loopback) instead.")
        return 1
    if args.verbose:
        print(f"Using: {device_info['name']}\n")

    mic = None
    if args.include_mic:
        mic = _resolve_mic_config(args)
        if mic is None:
            return 1

    mode_summary = "Core Audio tap"
    if mic:
        mode_summary += f" + mic ({mic.name})"

    return _run_dual_capture(
        engine, args,
        title="Core Audio Process Tap" + (" + Microphone" if mic else ""),
        mode_summary=mode_summary,
        # Known only once the helper's header arrives, i.e. after capture starts.
        sys_rate=lambda: capture.sample_rate,
        run_sys=lambda on_chunk, enqueue, check_silence: capture.capture_stream(
            callback=on_chunk, device_index=device_info['index'], verbose=args.verbose),
        mic=mic,
        cleanup=capture.cleanup,
        capture_errors=(UnsupportedMacOSVersionError, AudioCapturePermissionError, MacOSCaptureError),
    )


if __name__ == "__main__":
    # Required for the frozen (PyInstaller) sidecar: multiprocessing's
    # resource_tracker relaunches itself by re-invoking sys.executable,
    # which in a frozen onefile build is this binary itself, not a real
    # Python interpreter. freeze_support() intercepts that re-invocation
    # before the app's own imports run -- without it, the relaunch re-runs
    # this whole script from scratch and dies on a circular import.
    multiprocessing.freeze_support()
    code = main()
    if _source_lost:
        # ponytail: skips atexit on this one failure path, where sounddevice's
        # PortAudio termination can block on the dead audio server just like
        # stream.stop() did; the transcript is already closed by then.
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(code)
    sys.exit(code)
