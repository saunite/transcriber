"""
Speaker diarization module using pyannote.audio.
Identifies who spoke when in audio recordings.
"""

import os
import numpy as np
import torch
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import tempfile


class SpeakerDiarization:
    """
    Speaker diarization using pyannote.audio.
    Identifies and separates different speakers in audio.
    """
    
    def __init__(self, auth_token: Optional[str] = None):
        """
        Initialize speaker diarization.
        
        Args:
            auth_token: Hugging Face auth token for pyannote models
                       Can also be set via HUGGINGFACE_TOKEN environment variable
        """
        self.auth_token = auth_token or os.getenv('HUGGINGFACE_TOKEN')
        self.pipeline = None
        self._initialized = False
    
    def _initialize_pipeline(self):
        """Lazy initialization of the diarization pipeline."""
        if self._initialized:
            return
        
        try:
            from pyannote.audio import Pipeline
            
            if not self.auth_token:
                print("\n⚠️  Warning: No Hugging Face token provided for speaker diarization.")
                print("To use speaker diarization:")
                print("1. Create account at https://huggingface.co/")
                print("2. Accept license at https://huggingface.co/pyannote/speaker-diarization-3.1")
                print("3. Get your token from https://huggingface.co/settings/tokens")
                print("4. Set environment variable: HUGGINGFACE_TOKEN=your_token")
                print("   Or pass token when running the script\n")
                raise RuntimeError("Hugging Face token required for speaker diarization")
            
            print("Loading speaker diarization model...")
            self.pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1",
                use_auth_token=self.auth_token
            )
            
            # Use GPU if available
            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            self.pipeline.to(device)
            print(f"✓ Diarization model loaded on {device}")
            
            self._initialized = True
            
        except ImportError:
            raise ImportError(
                "pyannote.audio not installed. Install with: pip install pyannote.audio"
            )
        except Exception as e:
            raise RuntimeError(f"Failed to initialize diarization pipeline: {e}")
    
    def diarize_file(
        self,
        audio_path: str,
        num_speakers: Optional[int] = None,
        min_speakers: Optional[int] = None,
        max_speakers: Optional[int] = None
    ) -> List[Dict]:
        """
        Perform speaker diarization on an audio file.
        
        Args:
            audio_path: Path to audio file
            num_speakers: Exact number of speakers (if known)
            min_speakers: Minimum number of speakers
            max_speakers: Maximum number of speakers
        
        Returns:
            List of speaker segments with format:
            [
                {
                    'start': float,  # Start time in seconds
                    'end': float,    # End time in seconds
                    'speaker': str   # Speaker label (e.g., 'SPEAKER_00')
                },
                ...
            ]
        """
        self._initialize_pipeline()
        
        if not Path(audio_path).exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        print(f"\nPerforming speaker diarization on: {audio_path}")
        
        # Run diarization
        kwargs = {}
        if num_speakers is not None:
            kwargs['num_speakers'] = num_speakers
        else:
            if min_speakers is not None:
                kwargs['min_speakers'] = min_speakers
            if max_speakers is not None:
                kwargs['max_speakers'] = max_speakers
        
        diarization = self.pipeline(audio_path, **kwargs)
        
        # Convert to list of segments
        segments = []
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            segments.append({
                'start': turn.start,
                'end': turn.end,
                'speaker': speaker
            })
        
        # Get speaker statistics
        speakers = set(seg['speaker'] for seg in segments)
        print(f"✓ Detected {len(speakers)} speaker(s): {', '.join(sorted(speakers))}")
        
        return segments
    
    def diarize_array(
        self,
        audio_array: np.ndarray,
        sample_rate: int = 16000,
        **kwargs
    ) -> List[Dict]:
        """
        Perform speaker diarization on numpy audio array.
        
        Args:
            audio_array: Audio data as numpy array
            sample_rate: Sample rate of audio
            **kwargs: Additional arguments for diarize_file
        
        Returns:
            List of speaker segments
        """
        # Save to temporary file
        import soundfile as sf
        
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
            tmp_path = tmp_file.name
        
        try:
            sf.write(tmp_path, audio_array, sample_rate)
            return self.diarize_file(tmp_path, **kwargs)
        finally:
            # Clean up
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
    
    def merge_transcription_with_diarization(
        self,
        transcription_segments: List[Dict],
        diarization_segments: List[Dict],
        overlap_threshold: float = 0.5
    ) -> List[Dict]:
        """
        Merge transcription with speaker diarization.
        
        Args:
            transcription_segments: Segments from transcription (with 'start', 'end', 'text')
            diarization_segments: Segments from diarization (with 'start', 'end', 'speaker')
            overlap_threshold: Minimum overlap ratio to assign speaker
        
        Returns:
            Merged segments with speaker labels
        """
        merged = []
        
        for trans_seg in transcription_segments:
            trans_start = trans_seg['start']
            trans_end = trans_seg['end']
            trans_duration = trans_end - trans_start
            
            # Find overlapping speakers
            speaker_overlaps = {}
            
            for diar_seg in diarization_segments:
                diar_start = diar_seg['start']
                diar_end = diar_seg['end']
                speaker = diar_seg['speaker']
                
                # Calculate overlap
                overlap_start = max(trans_start, diar_start)
                overlap_end = min(trans_end, diar_end)
                overlap_duration = max(0, overlap_end - overlap_start)
                
                if overlap_duration > 0:
                    overlap_ratio = overlap_duration / trans_duration
                    if overlap_ratio > overlap_threshold:
                        speaker_overlaps[speaker] = speaker_overlaps.get(speaker, 0) + overlap_ratio
            
            # Assign speaker with most overlap
            if speaker_overlaps:
                assigned_speaker = max(speaker_overlaps.items(), key=lambda x: x[1])[0]
            else:
                assigned_speaker = "UNKNOWN"
            
            merged.append({
                **trans_seg,
                'speaker': assigned_speaker
            })
        
        return merged
    
    @staticmethod
    def format_with_speakers(segments: List[Dict], include_timestamps: bool = True) -> str:
        """
        Format transcription with speaker labels.
        
        Args:
            segments: Merged segments with speaker and text
            include_timestamps: Include timestamps in output
        
        Returns:
            Formatted text
        """
        lines = []
        current_speaker = None
        
        for seg in segments:
            speaker = seg.get('speaker', 'UNKNOWN')
            text = seg.get('text', '')
            
            # Add speaker label when speaker changes
            if speaker != current_speaker:
                if lines:  # Add blank line between speakers
                    lines.append("")
                lines.append(f"\n[{speaker}]")
                current_speaker = speaker
            
            if include_timestamps:
                start = seg['start']
                end = seg['end']
                timestamp = f"[{SpeakerDiarization._format_time(start)} -> {SpeakerDiarization._format_time(end)}]"
                lines.append(f"  {timestamp} {text}")
            else:
                lines.append(f"  {text}")
        
        return '\n'.join(lines)
    
    @staticmethod
    def _format_time(seconds: float) -> str:
        """Format seconds as MM:SS"""
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins:02d}:{secs:02d}"
    
    def get_speaker_statistics(self, segments: List[Dict]) -> Dict[str, Dict]:
        """
        Get statistics about each speaker.
        
        Args:
            segments: Diarization or merged segments
        
        Returns:
            Dictionary with speaker statistics
        """
        stats = {}
        
        for seg in segments:
            speaker = seg.get('speaker', 'UNKNOWN')
            duration = seg['end'] - seg['start']
            
            if speaker not in stats:
                stats[speaker] = {
                    'total_duration': 0,
                    'segments': 0,
                    'words': 0
                }
            
            stats[speaker]['total_duration'] += duration
            stats[speaker]['segments'] += 1
            
            # Count words if text available
            if 'text' in seg:
                stats[speaker]['words'] += len(seg['text'].split())
        
        return stats
