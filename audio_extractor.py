"""
Audio extraction utilities for cross-platform audio processing.
Handles extracting audio from video files using ffmpeg.
"""

import os
import platform
import subprocess
import tempfile
from pathlib import Path
from typing import Optional


class AudioExtractor:
    """Extract audio from video files using ffmpeg."""
    
    def __init__(self):
        self.system = platform.system()
        
    def _check_ffmpeg(self) -> bool:
        """Check if ffmpeg is available on the system."""
        try:
            subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True,
                check=True
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def extract_audio(
        self,
        video_path: str,
        output_path: Optional[str] = None,
        sample_rate: int = 16000
    ) -> str:
        """
        Extract audio from a video file.
        
        Args:
            video_path: Path to the input video file
            output_path: Path for the output audio file (WAV format)
                        If None, creates a temporary file
            sample_rate: Audio sample rate in Hz (default: 16000, required for Whisper)
        
        Returns:
            Path to the extracted audio file
            
        Raises:
            FileNotFoundError: If video file doesn't exist or ffmpeg is not installed
            RuntimeError: If audio extraction fails
        """
        if not self._check_ffmpeg():
            raise FileNotFoundError(
                "ffmpeg is not installed or not in PATH. "
                "Please install ffmpeg to extract audio from videos."
            )
        
        video_path = Path(video_path)
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        # Create output path if not provided
        if output_path is None:
            temp_dir = tempfile.gettempdir()
            output_path = os.path.join(temp_dir, f"extracted_audio_{os.getpid()}.wav")
        else:
            output_path = str(Path(output_path))
        
        # Build ffmpeg command (cross-platform)
        command = [
            "ffmpeg",
            "-i", str(video_path),
            "-vn",  # No video
            "-acodec", "pcm_s16le",  # PCM 16-bit little-endian
            "-ar", str(sample_rate),  # Sample rate
            "-ac", "1",  # Mono audio
            "-y",  # Overwrite output file
            output_path
        ]
        
        try:
            # Run ffmpeg with suppressed output
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True
            )
            
            if not Path(output_path).exists():
                raise RuntimeError("Audio extraction completed but output file not found")
            
            return output_path
            
        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"Failed to extract audio from video:\n{e.stderr}"
            )
    
    def cleanup_temp_audio(self, audio_path: str) -> None:
        """Remove temporary audio file."""
        try:
            if audio_path and Path(audio_path).exists():
                Path(audio_path).unlink()
        except Exception as e:
            print(f"Warning: Could not delete temporary file {audio_path}: {e}")
