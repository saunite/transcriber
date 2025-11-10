#!/usr/bin/env python3
"""
Audio Transcriber CLI
Cross-platform audio transcription tool using faster-whisper.

License: GPLv2
"""

import sys
import argparse
from pathlib import Path
from audio_extractor import AudioExtractor
from audio_capture import AudioCapture, setup_loopback_instructions
from transcription_engine import TranscriptionEngine
from speaker_diarization import SpeakerDiarization
from audio_buffer import AudioBuffer
import time


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
        
        # Transcribe
        segments, info = engine.transcribe_file(
            audio_file,
            language=args.language,
            task=args.task
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
                include_timestamps=not args.no_timestamps
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
    if args.diarize:
        print("⚠️  Note: Speaker diarization in live mode will be applied at the end")
    print("="*60 + "\n")
    
    # Initialize components
    capture = AudioCapture(sample_rate=16000, channels=1)
    
    # Storage for segments
    all_segments = []
    all_audio_data = []
    segment_counter = [0]  # Use list for mutable counter in closure
    
    # Create buffer with callback
    def process_chunk(audio_chunk):
        """Process audio chunk through transcription."""
        segment_counter[0] += 1
        print(f"\n[Chunk {segment_counter[0]}] Processing {len(audio_chunk)/16000:.1f}s of audio...")
        
        try:
            # Store audio for diarization later
            if args.diarize:
                all_audio_data.append(audio_chunk.copy())
            
            # Transcribe chunk
            segments, info = engine.transcribe_chunk(audio_chunk, language=args.language)
            
            # Print and store results
            for seg in segments:
                if seg['text'].strip():
                    timestamp = f"[{engine._format_time(seg['start'])} -> {engine._format_time(seg['end'])}]"
                    print(f"{timestamp} {seg['text']}")
                    all_segments.append(seg)
            
            if not segments:
                print("  (no speech detected)")
                
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
                include_timestamps=not args.no_timestamps
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


if __name__ == "__main__":
    sys.exit(main())
