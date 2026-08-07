"""
Transcription engine using faster-whisper.
Handles both file-based and streaming audio transcription.
"""

import os
import ssl
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Tuple, List
import numpy as np
from tqdm import tqdm

# Disable SSL verification (corporate networks / offline model downloads)
ssl._create_default_https_context = ssl._create_unverified_context
os.environ['SSL_CERT_FILE'] = ''

from faster_whisper import WhisperModel


class TranscriptionEngine:
    """Wrapper for faster-whisper transcription."""
    
    def __init__(
        self,
        model_size: str = "base",
        device: str = "auto",
        compute_type: str = "auto"
    ):
        """
        Initialize the transcription engine.
        
        Args:
            model_size: Model size (tiny, base, small, medium, large, turbo)
            device: Device to run on ("cpu", "cuda", or "auto")
            compute_type: Computation type ("int8", "float16", "float32", or "auto")
        """
        self.model_size = model_size
        
        # Auto-detect best settings
        if device == "auto":
            try:
                import torch
                device = "cuda" if torch.cuda.is_available() else "cpu"
            except ImportError:
                device = "cpu"
        
        if compute_type == "auto":
            if device == "cuda":
                compute_type = "float16"  # Fast on GPU
            else:
                compute_type = "int8"  # Efficient on CPU
        
        self.device = device
        self.compute_type = compute_type
        
        print(f"Loading {model_size} model on {device} with {compute_type}...")
        self.model = WhisperModel(
            model_size,
            device=device,
            compute_type=compute_type
        )
        print("✓ Model loaded successfully")
    
    def transcribe_file(
        self,
        audio_path: str,
        language: Optional[str] = None,
        task: str = "transcribe",
        output_path: Optional[str] = None,
        use_actual_time: bool = False,
        base_time: Optional[datetime] = None
    ) -> Tuple[List[dict], dict]:
        """
        Transcribe an audio/video file.
        
        Args:
            audio_path: Path to audio or video file
            language: Language code (e.g., "en", "es") or None for auto-detection
            task: "transcribe" or "translate" (translate to English)
            output_path: Path to save transcript incrementally (optional)
            use_actual_time: Use wall-clock timestamps instead of relative offsets
            base_time: Base wall-clock time for timestamp calculations
        
        Returns:
            Tuple of (segments, info) where:
                segments: List of transcription segments with timestamps
                info: Metadata about the transcription
        """
        if not Path(audio_path).exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        print(f"\nTranscribing: {audio_path}")
        print(f"Language: {language or 'auto-detect'}")
        
        # Transcribe
        segments_gen, info = self.model.transcribe(
            audio_path,
            language=language,
            task=task,
            beam_size=5,
            vad_filter=True  # Voice activity detection to filter silence
        )
        
        # Convert generator to list with progress bar
        segments = []
        print(f"\nDetected language: {info.language} (probability: {info.language_probability:.2f})")
        print(f"Duration: {info.duration:.2f} seconds\n")
        
        if use_actual_time and base_time is None:
            base_time = datetime.now()

        # Open file for incremental writing if requested
        output_file = None
        if output_path:
            output_file = open(output_path, 'w', encoding='utf-8')
            output_file.write(f"# Transcription (in progress...)\n")
            output_file.write(f"# Language: {info.language} (probability: {info.language_probability:.2f})\n")
            output_file.write(f"# Duration: {info.duration:.2f} seconds\n\n")
            output_file.flush()
        
        # Process segments
        try:
            for segment in tqdm(segments_gen, desc="Processing segments", unit="segment"):
                segment_dict = {
                    'start': segment.start,
                    'end': segment.end,
                    'text': segment.text.strip()
                }
                segments.append(segment_dict)
                
                # Write segment immediately to file
                if output_file:
                    timestamp = self.format_timestamp(
                        segment.start,
                        segment.end,
                        use_actual_time=use_actual_time,
                        base_time=base_time
                    )
                    output_file.write(f"{timestamp} {segment.text.strip()}\n")
                    output_file.flush()  # Ensure it's written to disk immediately
        finally:
            if output_file:
                output_file.close()
        
        info_dict = {
            'language': info.language,
            'language_probability': info.language_probability,
            'duration': info.duration
        }
        
        return segments, info_dict
    
    def transcribe_chunk(
        self,
        audio_chunk: np.ndarray,
        language: Optional[str] = None
    ) -> List[dict]:
        """
        Transcribe a single audio chunk.
        Optimized for real-time streaming with lower beam size.
        
        Args:
            audio_chunk: Audio data as numpy array
            language: Language code or None for auto-detection
        
        Returns:
            List of transcription segments
        """
        # Ensure audio is float32
        if audio_chunk.dtype != np.float32:
            audio_chunk = audio_chunk.astype(np.float32)
        
        # Transcribe with faster settings
        segments_gen, _ = self.model.transcribe(
            audio_chunk,
            language=language,
            beam_size=3,  # Lower for speed
            vad_filter=True
        )
        
        # Convert to list
        segments = []
        for segment in segments_gen:
            segments.append({
                'start': segment.start,
                'end': segment.end,
                'text': segment.text.strip()
            })
        
        return segments
    
    @staticmethod
    def _format_time(seconds: float) -> str:
        """Format seconds as MM:SS.mmm"""
        mins = int(seconds // 60)
        secs = seconds % 60
        return f"{mins:02d}:{secs:06.3f}"

    @staticmethod
    def _format_wall_time(base_time: datetime, seconds: float) -> str:
        """Format wall-clock time with millisecond precision."""
        timestamp = base_time + timedelta(seconds=seconds)
        return timestamp.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

    def format_timestamp(
        self,
        start_seconds: float,
        end_seconds: float,
        use_actual_time: bool = False,
        base_time: Optional[datetime] = None
    ) -> str:
        """Format a timestamp range for output."""
        if use_actual_time:
            if base_time is None:
                base_time = datetime.now()
            start = self._format_wall_time(base_time, start_seconds)
            end = self._format_wall_time(base_time, end_seconds)
        else:
            start = self._format_time(start_seconds)
            end = self._format_time(end_seconds)
        return f"[{start} -> {end}]"
    
    def save_transcript(
        self,
        segments: List[dict],
        output_path: str,
        format_type: str = "txt",
        include_timestamps: bool = True,
        use_actual_time: bool = False,
        base_time: Optional[datetime] = None
    ) -> None:
        """
        Save transcript to file.
        
        Args:
            segments: List of segment dictionaries
            output_path: Path to output file
            format_type: Output format ("txt", "srt", "vtt")
            include_timestamps: Include timestamps (for txt format)
            use_actual_time: Use wall-clock timestamps instead of relative offsets
            base_time: Base wall-clock time for timestamp calculations
        """
        output_path = Path(output_path)
        
        if format_type == "txt":
            lines = []
            if use_actual_time and base_time is None:
                base_time = datetime.now()
            for segment in segments:
                if include_timestamps:
                    timestamp = self.format_timestamp(
                        segment['start'],
                        segment['end'],
                        use_actual_time=use_actual_time,
                        base_time=base_time
                    )
                    lines.append(f"{timestamp} {segment['text']}")
                else:
                    lines.append(segment['text'])
            output_path.write_text('\n'.join(lines), encoding='utf-8')
            
        elif format_type == "srt":
            self._save_srt(segments, output_path)
            
        elif format_type == "vtt":
            self._save_vtt(segments, output_path)
            
        else:
            raise ValueError(f"Unsupported format: {format_type}")
        
        print(f"\n✓ Transcript saved to: {output_path}")
    
    def _save_srt(self, segments: List[dict], output_path: Path) -> None:
        """Save transcript in SRT subtitle format."""
        lines = []
        for i, segment in enumerate(segments, 1):
            lines.append(str(i))
            lines.append(
                f"{self._format_srt_time(segment['start'])} --> "
                f"{self._format_srt_time(segment['end'])}"
            )
            lines.append(segment['text'])
            lines.append("")  # Empty line between subtitles
        
        output_path.write_text('\n'.join(lines), encoding='utf-8')
    
    def _save_vtt(self, segments: List[dict], output_path: Path) -> None:
        """Save transcript in WebVTT format."""
        lines = ["WEBVTT", ""]
        for segment in segments:
            lines.append(
                f"{self._format_vtt_time(segment['start'])} --> "
                f"{self._format_vtt_time(segment['end'])}"
            )
            lines.append(segment['text'])
            lines.append("")
        
        output_path.write_text('\n'.join(lines), encoding='utf-8')
    
    @staticmethod
    def _format_srt_time(seconds: float) -> str:
        """Format time for SRT (HH:MM:SS,mmm)"""
        hours = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{mins:02d}:{secs:02d},{millis:03d}"
    
    @staticmethod
    def _format_vtt_time(seconds: float) -> str:
        """Format time for WebVTT (HH:MM:SS.mmm)"""
        hours = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{mins:02d}:{secs:02d}.{millis:03d}"
