"""
Transcription engine using faster-whisper.
Handles both file-based and streaming audio transcription.
"""

import os
from pathlib import Path
from typing import Optional, Iterator, Tuple, List
import numpy as np
from faster_whisper import WhisperModel
from tqdm import tqdm


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
        beam_size: int = 5,
        word_timestamps: bool = True
    ) -> Tuple[List[dict], dict]:
        """
        Transcribe an audio/video file.
        
        Args:
            audio_path: Path to audio or video file
            language: Language code (e.g., "en", "es") or None for auto-detection
            task: "transcribe" or "translate" (translate to English)
            beam_size: Beam size for decoding (higher = more accurate but slower)
            word_timestamps: Include word-level timestamps
        
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
            beam_size=beam_size,
            word_timestamps=word_timestamps,
            vad_filter=True  # Voice activity detection to filter silence
        )
        
        # Convert generator to list with progress bar
        segments = []
        print(f"\nDetected language: {info.language} (probability: {info.language_probability:.2f})")
        print(f"Duration: {info.duration:.2f} seconds\n")
        
        # Process segments
        for segment in tqdm(segments_gen, desc="Processing segments", unit="segment"):
            segments.append({
                'start': segment.start,
                'end': segment.end,
                'text': segment.text.strip(),
                'words': [
                    {
                        'start': word.start,
                        'end': word.end,
                        'word': word.word,
                        'probability': word.probability
                    }
                    for word in (segment.words or [])
                ] if word_timestamps else []
            })
        
        info_dict = {
            'language': info.language,
            'language_probability': info.language_probability,
            'duration': info.duration,
            'duration_after_vad': getattr(info, 'duration_after_vad', None)
        }
        
        return segments, info_dict
    
    def transcribe_stream(
        self,
        audio_iterator: Iterator[np.ndarray],
        language: Optional[str] = None,
        chunk_duration: float = 30.0
    ) -> Iterator[str]:
        """
        Transcribe streaming audio in real-time.
        
        Args:
            audio_iterator: Iterator yielding audio chunks (numpy arrays)
            language: Language code or None for auto-detection
            chunk_duration: Duration of audio chunks to accumulate before transcribing
        
        Yields:
            Transcribed text segments
        """
        print("🎙️  Real-time streaming transcription started")
        print("Note: There may be a delay as audio accumulates for processing\n")
        
        for audio_chunk in audio_iterator:
            # Ensure audio is float32
            if audio_chunk.dtype != np.float32:
                audio_chunk = audio_chunk.astype(np.float32)
            
            # Transcribe the chunk
            try:
                segments, _ = self.model.transcribe(
                    audio_chunk,
                    language=language,
                    beam_size=3,  # Lower beam size for faster processing
                    vad_filter=True,
                    word_timestamps=False  # Disable for speed
                )
                
                # Yield transcribed text
                for segment in segments:
                    if segment.text.strip():
                        yield segment.text.strip()
                        
            except Exception as e:
                print(f"⚠️  Error transcribing chunk: {e}")
                continue
    
    def transcribe_chunk(
        self,
        audio_chunk: np.ndarray,
        language: Optional[str] = None
    ) -> Tuple[List[dict], dict]:
        """
        Transcribe a single audio chunk.
        Optimized for real-time streaming with lower beam size.
        
        Args:
            audio_chunk: Audio data as numpy array
            language: Language code or None for auto-detection
        
        Returns:
            Tuple of (segments, info)
        """
        # Ensure audio is float32
        if audio_chunk.dtype != np.float32:
            audio_chunk = audio_chunk.astype(np.float32)
        
        # Transcribe with faster settings
        segments_gen, info = self.model.transcribe(
            audio_chunk,
            language=language,
            beam_size=3,  # Lower for speed
            vad_filter=True,
            word_timestamps=True
        )
        
        # Convert to list
        segments = []
        for segment in segments_gen:
            segments.append({
                'start': segment.start,
                'end': segment.end,
                'text': segment.text.strip(),
                'words': [
                    {
                        'start': word.start,
                        'end': word.end,
                        'word': word.word,
                        'probability': word.probability
                    }
                    for word in (segment.words or [])
                ]
            })
        
        info_dict = {
            'language': info.language,
            'language_probability': info.language_probability,
            'duration': info.duration
        }
        
        return segments, info_dict
    
    def format_transcript(
        self,
        segments: List[dict],
        include_timestamps: bool = True,
        include_words: bool = False
    ) -> str:
        """
        Format transcription segments into readable text.
        
        Args:
            segments: List of segment dictionaries
            include_timestamps: Include timestamps in output
            include_words: Include word-level timestamps
        
        Returns:
            Formatted transcript string
        """
        lines = []
        
        for segment in segments:
            if include_timestamps:
                timestamp = f"[{self._format_time(segment['start'])} -> {self._format_time(segment['end'])}]"
                lines.append(f"{timestamp} {segment['text']}")
            else:
                lines.append(segment['text'])
            
            # Add word-level timestamps if requested
            if include_words and segment.get('words'):
                for word in segment['words']:
                    word_ts = f"  {self._format_time(word['start'])}-{self._format_time(word['end'])}"
                    lines.append(f"{word_ts} {word['word']} (conf: {word['probability']:.2f})")
        
        return '\n'.join(lines)
    
    @staticmethod
    def _format_time(seconds: float) -> str:
        """Format seconds as MM:SS.mmm"""
        mins = int(seconds // 60)
        secs = seconds % 60
        return f"{mins:02d}:{secs:06.3f}"
    
    def save_transcript(
        self,
        segments: List[dict],
        output_path: str,
        format_type: str = "txt",
        include_timestamps: bool = True
    ) -> None:
        """
        Save transcript to file.
        
        Args:
            segments: List of segment dictionaries
            output_path: Path to output file
            format_type: Output format ("txt", "srt", "vtt")
            include_timestamps: Include timestamps (for txt format)
        """
        output_path = Path(output_path)
        
        if format_type == "txt":
            transcript = self.format_transcript(segments, include_timestamps)
            output_path.write_text(transcript, encoding='utf-8')
            
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
