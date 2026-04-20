#!/usr/bin/env python3
"""
Audio Transcriber CLI
Cross-platform audio transcription tool using faster-whisper.

License: GPLv2
"""

import sys
import signal
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from audio_extractor import AudioExtractor
from audio_capture import AudioCapture, setup_loopback_instructions
from transcription_engine import TranscriptionEngine
import time

# Global flag for clean shutdown
shutdown_requested = False

def signal_handler(signum, frame):
    """Handle Ctrl+C gracefully."""
    global shutdown_requested
    shutdown_requested = True
    print("\n\n⏹️  Shutdown requested, stopping transcription...")
    raise KeyboardInterrupt

# Optional dependencies
try:
    from speaker_diarization import SpeakerDiarization
    from audio_buffer import AudioBuffer
    DIARIZATION_AVAILABLE = True
except ImportError:
    DIARIZATION_AVAILABLE = False
    print("⚠️  Note: Speaker diarization not available (install torch and pyannote.audio)")


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
    
    # Diarization options
    parser.add_argument(
        '--diarize',
        action='store_true',
        help='Enable speaker diarization (identify who spoke when)'
    )
    
    parser.add_argument(
        '--hf-token',
        type=str,
        default=None,
        help='Hugging Face token for speaker diarization (or set HUGGINGFACE_TOKEN env var)'
    )
    
    parser.add_argument(
        '--num-speakers',
        type=int,
        default=None,
        help='Expected number of speakers (for diarization)'
    )
    
    parser.add_argument(
        '--min-speakers',
        type=int,
        default=None,
        help='Minimum number of speakers (for diarization)'
    )
    
    parser.add_argument(
        '--max-speakers',
        type=int,
        default=None,
        help='Maximum number of speakers (for diarization)'
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
        '--overlap-duration',
        type=float,
        default=5.0,
        help='Overlap between chunks for streaming (seconds, default: 5)'
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
        print(f"\n{'='*60}")
        print("Audio Transcriber")
        print(f"{'='*60}\n")
        
        # Set up signal handler for Ctrl+C
        signal.signal(signal.SIGINT, signal_handler)
        
        engine = TranscriptionEngine(
            model_size=args.model,
            device=args.device,
            compute_type=args.compute_type
        )
        
        # File transcription mode
        if args.file:
            return transcribe_file(engine, args)
        
        # Live capture mode
        elif args.live:
            return transcribe_live(engine, args)
    
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
    
    # Determine if we need to extract audio from video
    video_extensions = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v'}
    audio_extensions = {'.mp3', '.wav', '.flac', '.m4a', '.ogg', '.opus', '.wma'}
    
    file_ext = file_path.suffix.lower()
    audio_file = str(file_path)
    temp_audio = None
    
    try:
        # Extract audio if it's a video file
        if file_ext in video_extensions:
            print(f"📹 Video file detected: {file_path.name}")
            extractor = AudioExtractor()
            audio_file = extractor.extract_audio(str(file_path))
            temp_audio = audio_file
            print(f"✓ Audio extracted to: {audio_file}\n")
        
        elif file_ext in audio_extensions:
            print(f"🎵 Audio file detected: {file_path.name}\n")
        
        else:
            print(f"⚠️  Unknown file type: {file_ext}")
            print("Attempting to process as audio file...\n")
        
        base_time = datetime.now() if args.actual_time else None

        # Transcribe (with incremental saving)
        segments, info = engine.transcribe_file(
            audio_file,
            language=args.language,
            task=args.task,
            output_path=args.output,
            incremental_save=True,
            use_actual_time=args.actual_time,
            base_time=base_time
        )
        
        # Speaker diarization if requested
        if args.diarize:
            print("\n" + "="*60)
            print("Running Speaker Diarization")
            print("="*60)
            
            diarizer = SpeakerDiarization(auth_token=args.hf_token)
            
            diar_segments = diarizer.diarize_file(
                audio_file,
                num_speakers=args.num_speakers,
                min_speakers=args.min_speakers,
                max_speakers=args.max_speakers
            )
            
            # Merge transcription with diarization
            segments = diarizer.merge_transcription_with_diarization(
                segments,
                diar_segments
            )
            
            # Print speaker statistics
            stats = diarizer.get_speaker_statistics(segments)
            print("\nSpeaker Statistics:")
            for speaker, speaker_stats in sorted(stats.items()):
                print(f"  {speaker}:")
                print(f"    Duration: {speaker_stats['total_duration']:.1f}s")
                print(f"    Segments: {speaker_stats['segments']}")
                if speaker_stats['words'] > 0:
                    print(f"    Words: {speaker_stats['words']}")
        
        # Determine output path
        if args.output:
            output_path = Path(args.output)
        else:
            suffix = "_diarized" if args.diarize else "_transcript"
            output_name = f"{file_path.stem}{suffix}.{args.format}"
            output_path = Path.cwd() / output_name
        
        # Save transcript
        if args.diarize and args.format == 'txt':
            # Use special formatting for diarization
            transcript = SpeakerDiarization.format_with_speakers(
                segments,
                include_timestamps=not args.no_timestamps
            )
            output_path.write_text(transcript, encoding='utf-8')
            print(f"\n✓ Transcript with speakers saved to: {output_path}")
        else:
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
        if args.diarize:
            speakers = set(seg.get('speaker', 'UNKNOWN') for seg in segments)
            print(f"Speakers: {len(speakers)}")
        print(f"Output: {output_path}")
        print(f"{'='*60}\n")
        
        return 0
    
    finally:
        # Clean up temporary audio file
        if temp_audio:
            try:
                extractor.cleanup_temp_audio(temp_audio)
            except Exception as e:
                print(f"⚠️  Warning: Could not clean up temp file: {e}")


def transcribe_live(engine: TranscriptionEngine, args) -> int:
    """Handle live audio capture and transcription."""
    print("\n" + "="*60)
    print("Live Audio Transcription")
    print("="*60)
    print(f"Model: {args.model}")
    print(f"Language: {args.language or 'auto-detect'}")
    print(f"Chunk duration: {args.chunk_duration}s")
    print(f"Overlap: {args.overlap_duration}s")
    
    # Check if using WASAPI (Windows only)
    if args.wasapi:
        print("Mode: WASAPI Loopback (Bluetooth-compatible)")
        print("="*60 + "\n")
        return transcribe_live_wasapi(engine, args)
    
    if args.diarize:
        print("⚠️  Note: Speaker diarization requires torch (not available)")
    print("="*60 + "\n")
    
    # Check if AudioBuffer is available
    if not DIARIZATION_AVAILABLE:
        print("⚠️  Advanced buffering not available. Using simple mode.")
        print("    Transcription will happen in fixed chunks.\n")
        return transcribe_live_simple(engine, args)
    
    # Initialize components
    capture = AudioCapture(sample_rate=16000, channels=1)
    
    # Storage for segments
    all_segments = []
    all_audio_data = []
    segment_counter = [0]  # Use list for mutable counter in closure
    time_offset = 0.0
    session_start_time = datetime.now() if args.actual_time else None

    def process_chunk(audio_chunk):
        """Process audio chunk through transcription."""
        nonlocal time_offset
        segment_counter[0] += 1
        print(f"\n[Chunk {segment_counter[0]}] Processing {len(audio_chunk)/16000:.1f}s of audio...")
        
        try:
            # Store audio for diarization later
            if args.diarize:
                all_audio_data.append(audio_chunk.copy())
            
            # Transcribe chunk
            chunk_duration_sec = len(audio_chunk) / 16000
            chunk_wall_anchor = datetime.now() - timedelta(seconds=chunk_duration_sec)
            segments, info = engine.transcribe_chunk(audio_chunk, language=args.language)
            
            # Print and store results
            for seg in segments:
                if seg['text'].strip():
                    adjusted_start = seg['start'] + time_offset
                    adjusted_end = seg['end'] + time_offset
                    timestamp = engine.format_timestamp(
                        seg['start'] if args.actual_time else adjusted_start,
                        seg['end'] if args.actual_time else adjusted_end,
                        use_actual_time=args.actual_time,
                        base_time=chunk_wall_anchor if args.actual_time else session_start_time
                    )
                    print(f"{timestamp} {seg['text']}")

                    adjusted_seg = seg.copy()
                    adjusted_seg['start'] = adjusted_start
                    adjusted_seg['end'] = adjusted_end
                    all_segments.append(adjusted_seg)
            
            if not segments:
                print("  (no speech detected)")

            time_offset += chunk_duration_sec
                
        except Exception as e:
            print(f"  ❌ Error: {e}")
    
    buffer = AudioBuffer(
        sample_rate=16000,
        chunk_duration=args.chunk_duration,
        overlap_duration=args.overlap_duration,
        callback=process_chunk
    )
    
    # Start buffer processing thread
    buffer.start_processing(interval=0.5)
    
    try:
        # Capture audio
        capture.capture_stream(
            callback=buffer.add_audio,
            device=args.audio_device,
            duration=None  # Infinite until Ctrl+C
        )
    except KeyboardInterrupt:
        print("\n\nStopping capture...")
    finally:
        buffer.stop_processing()
    
    # Save transcript if we got any
    if all_segments:
        print(f"\n{'='*60}")
        print("Saving Transcript")
        print(f"{'='*60}")
        
        # Apply diarization if requested
        if args.diarize and all_audio_data:
            print("\nApplying speaker diarization to captured audio...")
            try:
                import numpy as np
                combined_audio = np.concatenate(all_audio_data)
                
                diarizer = SpeakerDiarization(auth_token=args.hf_token)
                diar_segments = diarizer.diarize_array(
                    combined_audio,
                    sample_rate=16000,
                    num_speakers=args.num_speakers,
                    min_speakers=args.min_speakers,
                    max_speakers=args.max_speakers
                )
                
                # Merge
                all_segments = diarizer.merge_transcription_with_diarization(
                    all_segments,
                    diar_segments
                )
                
                # Print stats
                stats = diarizer.get_speaker_statistics(all_segments)
                print("\nSpeaker Statistics:")
                for speaker, speaker_stats in sorted(stats.items()):
                    print(f"  {speaker}: {speaker_stats['total_duration']:.1f}s, {speaker_stats['segments']} segments")
                    
            except Exception as e:
                print(f"⚠️  Could not apply diarization: {e}")
        
        # Determine output path
        if args.output:
            output_path = Path(args.output)
        else:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            suffix = "_diarized" if args.diarize else "_transcript"
            output_name = f"live{suffix}_{timestamp}.txt"
            output_path = Path.cwd() / output_name
        
        # Save
        if args.diarize and args.format == 'txt':
            transcript = SpeakerDiarization.format_with_speakers(
                all_segments,
                include_timestamps=not args.no_timestamps
            )
            output_path.write_text(transcript, encoding='utf-8')
        else:
            engine.save_transcript(
                all_segments,
                str(output_path),
                format_type=args.format,
                include_timestamps=not args.no_timestamps,
                use_actual_time=args.actual_time,
                base_time=session_start_time
            )
        
        print(f"\n✓ Transcript saved to: {output_path}")
        print(f"Total segments: {len(all_segments)}")
        
        # Print buffer stats
        stats = buffer.get_stats()
        print(f"Total audio processed: {stats['duration_seconds']:.1f}s")
        print(f"Chunks processed: {stats['chunks_processed']}")
        
        return 0
    else:
        print("\n⚠️  No transcription to save")
        return 0


def transcribe_live_simple(engine: TranscriptionEngine, args) -> int:
    """Simple live transcription without AudioBuffer (no torch dependency)."""
    import numpy as np
    import sounddevice as sd
    from scipy import signal
    
    # Get device info to use its native sample rate
    device_id = args.audio_device if args.audio_device >= 0 else None
    if device_id is not None:
        device_info = sd.query_devices(device_id)
        native_rate = int(device_info['default_samplerate'])
        print(f"Using device native sample rate: {native_rate} Hz")
    else:
        native_rate = 48000
    
    target_rate = 16000  # Whisper requires 16kHz
    
    # Initialize audio capture with native sample rate
    capture = AudioCapture(sample_rate=native_rate, channels=1)
    
    # Storage
    all_segments = []
    audio_buffer = []
    chunk_duration_samples = int(native_rate * args.chunk_duration)
    time_offset = 0.0  # Track cumulative time offset
    session_start_time = datetime.now() if args.actual_time else None
    last_speech_time = time.time()  # Track time of last detected speech
    silence_timeout_enabled = args.silence_timeout > 0
    
    # Overlap settings to prevent speech loss at chunk boundaries
    overlap_duration = 1.0  # 1 second overlap
    overlap_samples = int(target_rate * overlap_duration)  # In target rate (16kHz)
    
    # Open output file for incremental writing
    output_file = None
    if args.output:
        output_file = open(args.output, 'w', encoding='utf-8')
        output_file.write(f"# Live Transcription Started\n")
        output_file.write(f"# Model: {args.model}\n")
        output_file.write(f"# Language: {args.language or 'auto-detect'}\n\n")
        output_file.flush()
    
    print("🎙️  Listening... (Press Ctrl+C to stop)\n")
    if silence_timeout_enabled:
        print(f"⏱️  Auto-stop after {args.silence_timeout/60:.1f} minutes of silence\n")
    
    def audio_callback(audio_chunk):
        """Process incoming audio chunks."""
        nonlocal time_offset, last_speech_time
        
        # Allow clean shutdown
        if shutdown_requested:
            raise KeyboardInterrupt
        
        # Check for silence timeout
        if silence_timeout_enabled:
            elapsed_silence = time.time() - last_speech_time
            if elapsed_silence > args.silence_timeout:
                print(f"\n⏱️  Stopping: {args.silence_timeout/60:.1f} minutes of silence detected")
                raise KeyboardInterrupt("Silence timeout")
        
        audio_buffer.append(audio_chunk.flatten())
        
        # Check if we have enough audio for transcription
        total_samples = sum(len(chunk) for chunk in audio_buffer)
        
        if total_samples >= chunk_duration_samples:
            # Concatenate all buffered audio
            audio_data = np.concatenate(audio_buffer)
            
            # Resample to 16kHz if needed
            if native_rate != target_rate:
                num_samples = int(len(audio_data) * target_rate / native_rate)
                audio_data = signal.resample(audio_data, num_samples)
            
            chunk_duration_sec = len(audio_data) / target_rate
            
            # Keep overlap for next chunk to prevent speech cutoff
            if len(audio_data) > overlap_samples:
                overlap_data = audio_data[-overlap_samples:]
                audio_buffer.clear()
                audio_buffer.append(overlap_data)
            else:
                audio_buffer.clear()
            
            # Ensure float32
            if audio_data.dtype != np.float32:
                audio_data = audio_data.astype(np.float32)
            
            # Transcribe
            try:
                chunk_wall_anchor = datetime.now() - timedelta(seconds=chunk_duration_sec)
                segments, info = engine.transcribe_chunk(audio_data, language=args.language)
                
                # Reset silence timer if speech was detected
                if segments and any(s['text'].strip() for s in segments):
                    last_speech_time = time.time()
                
                # Print and save results
                for seg in segments:
                    if seg['text'].strip():
                        # Add time offset to make timestamps cumulative
                        adjusted_start = seg['start'] + time_offset
                        adjusted_end = seg['end'] + time_offset
                        timestamp = engine.format_timestamp(
                            seg['start'] if args.actual_time else adjusted_start,
                            seg['end'] if args.actual_time else adjusted_end,
                            use_actual_time=args.actual_time,
                            base_time=chunk_wall_anchor if args.actual_time else session_start_time
                        )
                        line = f"{timestamp} {seg['text']}"
                        print(line)
                        # Store adjusted segment
                        adjusted_seg = seg.copy()
                        adjusted_seg['start'] = adjusted_start
                        adjusted_seg['end'] = adjusted_end
                        all_segments.append(adjusted_seg)
                        
                        # Write immediately to file
                        if output_file:
                            output_file.write(line + "\n")
                            output_file.flush()
                
                if not segments or not any(s['text'].strip() for s in segments):
                    print("  (no speech detected)")
                
                # Update time offset for next chunk
                time_offset += chunk_duration_sec
            
            except Exception as e:
                print(f"  ❌ Error transcribing: {e}")

    
    try:
        # Start capturing
        capture.capture_stream(
            callback=audio_callback,
            device=args.audio_device,
            duration=None  # Infinite until Ctrl+C
        )
    except KeyboardInterrupt:
        print("\n\n⏹️  Stopping transcription...")
    finally:
        if output_file:
            output_file.close()
    
    # Summary
    print(f"\n{'='*60}")
    print("Transcription Complete")
    print(f"{'='*60}")
    print(f"Total segments: {len(all_segments)}")
    if args.output:
        print(f"Saved to: {args.output}")
    print(f"{'='*60}\n")
    
    return 0


def transcribe_live_wasapi(engine: TranscriptionEngine, args) -> int:
    """Live transcription using WASAPI loopback (Windows, Bluetooth-compatible)."""
    import numpy as np
    from wasapi_capture import WASAPICapture
    from scipy import signal
    import sounddevice as sd
    import queue
    import threading

    # Initialize WASAPI capture for system audio
    capture = WASAPICapture()

    # Get system audio loopback device
    if args.audio_device >= 0:
        device_index = args.audio_device
    else:
        # Auto-detect default loopback
        device_info = capture.get_default_loopback_device()
        if not device_info:
            print("❌ No WASAPI loopback device found!")
            print("Run with --list-devices to see available devices.")
            return 1
        device_index = device_info['index']
        print(f"Auto-detected loopback: {device_info['name']}\n")
    
    # Get microphone device if requested
    mic_stream = None
    mic_channels = 1  # Default to mono
    if args.include_mic:
        if args.mic_device >= 0:
            mic_device = args.mic_device
        else:
            # Auto-detect default microphone
            try:
                mic_info = sd.query_devices(kind='input')
                mic_device = mic_info['index'] if isinstance(mic_info, dict) else None
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
            print(f"Microphone capture enabled (device {mic_device})")
            print(f"   Device: {mic_info['name']}")
            print(f"   Channels: {mic_channels}\n")
        except Exception as e:
            print(f"❌ Error querying microphone device {mic_device}: {e}")
            return 1

    # Storage
    all_segments = []
    session_start_time = datetime.now() if args.actual_time else None
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

    print("Listening... (Press Ctrl+C to stop)\n")
    if silence_timeout_enabled:
        print(f"Auto-stop after {args.silence_timeout/60:.1f} minutes of silence\n")

    # Microphone callback: just enqueue raw audio, never blocks
    def mic_callback(indata, frames, time_info, status):
        if status and "overflow" not in str(status).lower():
            print(f"Mic status: {status}")
        mic_audio = indata[:, 0] if len(indata.shape) > 1 else indata
        mic_audio_queue.put(mic_audio.flatten().copy())

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
        if shutdown_requested:
            raise KeyboardInterrupt
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

    def sys_worker():
        """Dedicated thread: drains system audio queue and runs inference."""
        nonlocal last_speech_time
        sys_buffer = []
        system_time_offset = 0.0

        while not stop_event.is_set() or not sys_audio_queue.empty():
            # Drain queue into buffer (non-blocking)
            while not sys_audio_queue.empty():
                raw = sys_audio_queue.get_nowait()
                # Resample 48kHz -> 16kHz here, away from the capture callback
                resampled_len = int(len(raw) * target_rate / wasapi_rate)
                sys_buffer.append(signal.resample(raw, resampled_len))

            total_sys = sum(len(c) for c in sys_buffer)
            if total_sys >= chunk_duration_samples:
                system_data = np.concatenate(sys_buffer)
                chunk_duration_sec = len(system_data) / target_rate
                if len(system_data) > overlap_samples:
                    sys_buffer[:] = [system_data[-overlap_samples:]]
                else:
                    sys_buffer.clear()
                if system_data.dtype != np.float32:
                    system_data = system_data.astype(np.float32)
                try:
                    wall_anchor = datetime.now() - timedelta(seconds=chunk_duration_sec)
                    segments, _ = engine.transcribe_chunk(system_data, language=args.language)
                    if segments and any(s['text'].strip() for s in segments):
                        last_speech_time = time.time()
                    for seg in segments:
                        if seg['text'].strip():
                            adjusted_start = seg['start'] + system_time_offset
                            adjusted_end = seg['end'] + system_time_offset
                            ts = engine.format_timestamp(
                                seg['start'] if args.actual_time else adjusted_start,
                                seg['end'] if args.actual_time else adjusted_end,
                                use_actual_time=args.actual_time,
                                base_time=wall_anchor if args.actual_time else session_start_time
                            )
                            _emit(f"{ts} [SYS] {seg['text']}")
                            adjusted_seg = seg.copy()
                            adjusted_seg['start'] = adjusted_start
                            adjusted_seg['end'] = adjusted_end
                            all_segments.append(adjusted_seg)
                    system_time_offset += chunk_duration_sec
                except Exception as e:
                    print(f"  ❌ Error transcribing system audio: {e}")
            else:
                time.sleep(0.05)

    def mic_worker():
        """Dedicated thread: drains mic audio queue and runs inference."""
        nonlocal last_speech_time
        mic_buffer_local = []
        mic_time_offset = 0.0

        while not stop_event.is_set() or not mic_audio_queue.empty():
            while not mic_audio_queue.empty():
                mic_buffer_local.append(mic_audio_queue.get_nowait())

            total_mic = sum(len(c) for c in mic_buffer_local)
            if total_mic >= mic_chunk_samples:
                mic_data = np.concatenate(mic_buffer_local)
                chunk_duration_sec = len(mic_data) / target_rate
                if len(mic_data) > overlap_samples:
                    mic_buffer_local[:] = [mic_data[-overlap_samples:]]
                else:
                    mic_buffer_local.clear()
                if np.max(np.abs(mic_data)) > 0.01:
                    if mic_data.dtype != np.float32:
                        mic_data = mic_data.astype(np.float32)
                    try:
                        wall_anchor = datetime.now() - timedelta(seconds=chunk_duration_sec)
                        segments, _ = engine.transcribe_chunk(mic_data, language=args.language)
                        if segments and any(s['text'].strip() for s in segments):
                            last_speech_time = time.time()
                        for seg in segments:
                            if seg['text'].strip():
                                adjusted_start = seg['start'] + mic_time_offset
                                adjusted_end = seg['end'] + mic_time_offset
                                ts = engine.format_timestamp(
                                    seg['start'] if args.actual_time else adjusted_start,
                                    seg['end'] if args.actual_time else adjusted_end,
                                    use_actual_time=args.actual_time,
                                    base_time=wall_anchor if args.actual_time else session_start_time
                                )
                                _emit(f"{ts} [MIC] {seg['text']}")
                                adjusted_seg = seg.copy()
                                adjusted_seg['start'] = adjusted_start
                                adjusted_seg['end'] = adjusted_end
                                all_segments.append(adjusted_seg)
                        mic_time_offset += chunk_duration_sec
                    except Exception as e:
                        print(f"  ❌ Error transcribing microphone: {e}")
            else:
                time.sleep(0.05)

    # Start dedicated worker threads (sys and mic run in parallel, never blocking each other)
    sys_thread = threading.Thread(target=sys_worker, daemon=True)
    sys_thread.start()
    mic_thread = None
    if args.include_mic:
        mic_thread = threading.Thread(target=mic_worker, daemon=True)
        mic_thread.start()

    try:
        # Start capturing (callbacks only enqueue audio now, never block)
        capture.capture_stream(
            callback=audio_callback,
            device_index=device_index,
            duration=None  # Infinite until Ctrl+C
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
        capture.cleanup()
    
    # Summary
    print(f"\n{'='*60}")
    print("Transcription Complete")
    print(f"{'='*60}")
    print(f"Total segments: {len(all_segments)}")
    if args.output:
        print(f"Saved to: {args.output}")
    print(f"{'='*60}\n")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
