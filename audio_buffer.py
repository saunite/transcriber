"""
Audio buffering system for real-time streaming transcription.
Manages audio chunks with overlap for continuous transcription.
"""

import numpy as np
from collections import deque
from typing import Optional, Callable
import threading
import time


class AudioBuffer:
    """
    Circular buffer for real-time audio streaming with overlap.
    Maintains context windows for better transcription quality.
    """
    
    def __init__(
        self,
        sample_rate: int = 16000,
        chunk_duration: float = 30.0,
        overlap_duration: float = 5.0,
        callback: Optional[Callable] = None
    ):
        """
        Initialize audio buffer.
        
        Args:
            sample_rate: Audio sample rate in Hz
            chunk_duration: Duration of each chunk to process (seconds)
            overlap_duration: Overlap between consecutive chunks (seconds)
            callback: Function to call when a chunk is ready
        """
        self.sample_rate = sample_rate
        self.chunk_duration = chunk_duration
        self.overlap_duration = overlap_duration
        
        # Calculate sizes
        self.chunk_size = int(sample_rate * chunk_duration)
        self.overlap_size = int(sample_rate * overlap_duration)
        self.step_size = self.chunk_size - self.overlap_size
        
        # Buffer storage
        self.buffer = deque(maxlen=self.chunk_size * 2)
        self.callback = callback
        
        # Threading
        self.lock = threading.Lock()
        self.is_active = False
        self.process_thread = None
        
        # Statistics
        self.total_samples = 0
        self.chunks_processed = 0
    
    def add_audio(self, audio_data: np.ndarray) -> None:
        """
        Add audio data to the buffer.
        
        Args:
            audio_data: Audio samples (1D numpy array)
        """
        with self.lock:
            # Flatten if needed
            if audio_data.ndim > 1:
                audio_data = audio_data.flatten()
            
            # Add to buffer
            for sample in audio_data:
                self.buffer.append(sample)
            
            self.total_samples += len(audio_data)
    
    def get_chunk(self) -> Optional[np.ndarray]:
        """
        Get a chunk of audio if enough data is available.
        
        Returns:
            Audio chunk as numpy array, or None if not enough data
        """
        with self.lock:
            if len(self.buffer) >= self.chunk_size:
                # Extract chunk
                chunk = np.array(list(self.buffer)[:self.chunk_size], dtype=np.float32)
                
                # Remove processed samples (keep overlap)
                for _ in range(self.step_size):
                    if len(self.buffer) > 0:
                        self.buffer.popleft()
                
                self.chunks_processed += 1
                return chunk
        
        return None
    
    def get_all_remaining(self) -> Optional[np.ndarray]:
        """
        Get all remaining audio in buffer (for final processing).
        
        Returns:
            Remaining audio as numpy array, or None if empty
        """
        with self.lock:
            if len(self.buffer) > 0:
                chunk = np.array(list(self.buffer), dtype=np.float32)
                self.buffer.clear()
                return chunk
        
        return None
    
    def start_processing(self, interval: float = 0.5) -> None:
        """
        Start automatic processing thread.
        
        Args:
            interval: How often to check for new chunks (seconds)
        """
        if self.callback is None:
            raise ValueError("Callback function required for automatic processing")
        
        self.is_active = True
        self.process_thread = threading.Thread(
            target=self._process_loop,
            args=(interval,),
            daemon=True
        )
        self.process_thread.start()
    
    def stop_processing(self) -> None:
        """Stop automatic processing."""
        self.is_active = False
        if self.process_thread:
            self.process_thread.join(timeout=2.0)
    
    def _process_loop(self, interval: float) -> None:
        """Internal processing loop."""
        while self.is_active:
            chunk = self.get_chunk()
            if chunk is not None and self.callback:
                try:
                    self.callback(chunk)
                except Exception as e:
                    print(f"Error in buffer callback: {e}")
            
            time.sleep(interval)
        
        # Process remaining audio
        final_chunk = self.get_all_remaining()
        if final_chunk is not None and self.callback:
            try:
                self.callback(final_chunk)
            except Exception as e:
                print(f"Error in final callback: {e}")
    
    def clear(self) -> None:
        """Clear the buffer."""
        with self.lock:
            self.buffer.clear()
    
    def get_stats(self) -> dict:
        """Get buffer statistics."""
        with self.lock:
            return {
                'total_samples': self.total_samples,
                'chunks_processed': self.chunks_processed,
                'buffer_size': len(self.buffer),
                'buffer_fullness': len(self.buffer) / self.chunk_size if self.chunk_size > 0 else 0,
                'duration_seconds': self.total_samples / self.sample_rate
            }


class VADBuffer:
    """
    Voice Activity Detection buffer to filter silence.
    Uses WebRTC VAD to detect speech segments.
    """
    
    def __init__(
        self,
        sample_rate: int = 16000,
        frame_duration_ms: int = 30,
        aggressiveness: int = 2
    ):
        """
        Initialize VAD buffer.
        
        Args:
            sample_rate: Audio sample rate (must be 8000, 16000, 32000, or 48000)
            frame_duration_ms: Frame duration in ms (10, 20, or 30)
            aggressiveness: VAD aggressiveness (0-3, higher = more aggressive filtering)
        """
        try:
            import webrtcvad
            self.vad = webrtcvad.Vad(aggressiveness)
        except ImportError:
            print("Warning: webrtcvad not available, VAD disabled")
            self.vad = None
        
        self.sample_rate = sample_rate
        self.frame_duration_ms = frame_duration_ms
        self.frame_size = int(sample_rate * frame_duration_ms / 1000)
        
        # Validate parameters
        if sample_rate not in [8000, 16000, 32000, 48000]:
            print(f"Warning: VAD requires sample rate of 8000, 16000, 32000, or 48000 Hz. Got {sample_rate}. VAD disabled.")
            self.vad = None
        
        if frame_duration_ms not in [10, 20, 30]:
            print(f"Warning: VAD frame duration must be 10, 20, or 30 ms. Got {frame_duration_ms}. VAD disabled.")
            self.vad = None
    
    def is_speech(self, audio_frame: np.ndarray) -> bool:
        """
        Check if audio frame contains speech.
        
        Args:
            audio_frame: Audio samples (must be correct frame size)
        
        Returns:
            True if speech detected, False otherwise
        """
        if self.vad is None:
            return True  # If VAD not available, assume all is speech
        
        # Convert to int16 PCM
        if audio_frame.dtype != np.int16:
            audio_frame = (audio_frame * 32767).astype(np.int16)
        
        # Check size
        if len(audio_frame) != self.frame_size * 2:  # *2 for stereo or different format
            # Ensure correct size
            audio_frame = audio_frame[:self.frame_size * 2]
        
        try:
            return self.vad.is_speech(audio_frame.tobytes(), self.sample_rate)
        except Exception:
            return True  # On error, assume speech
    
    def filter_audio(
        self,
        audio_data: np.ndarray,
        padding_frames: int = 10
    ) -> np.ndarray:
        """
        Filter audio to keep only speech segments with padding.
        
        Args:
            audio_data: Input audio
            padding_frames: Number of frames to keep before/after speech
        
        Returns:
            Filtered audio containing only speech segments
        """
        if self.vad is None:
            return audio_data
        
        # Process in frames
        num_frames = len(audio_data) // self.frame_size
        speech_frames = []
        
        for i in range(num_frames):
            start = i * self.frame_size
            end = start + self.frame_size
            frame = audio_data[start:end]
            
            if self.is_speech(frame):
                speech_frames.append(i)
        
        # Add padding
        padded_frames = set()
        for frame_idx in speech_frames:
            for offset in range(-padding_frames, padding_frames + 1):
                padded_idx = frame_idx + offset
                if 0 <= padded_idx < num_frames:
                    padded_frames.add(padded_idx)
        
        # Extract speech segments
        result = []
        for i in sorted(padded_frames):
            start = i * self.frame_size
            end = start + self.frame_size
            result.extend(audio_data[start:end])
        
        return np.array(result, dtype=audio_data.dtype) if result else np.array([], dtype=audio_data.dtype)
