"""
WASAPI loopback audio capture for Windows - captures system audio including Bluetooth
"""
import pyaudiowpatch as pyaudio
import numpy as np
from typing import Callable, Optional
import threading
from queue import Queue


class WASAPICapture:
    """Windows WASAPI loopback capture - works with Bluetooth headsets!"""
    
    def __init__(self):
        """Initialize WASAPI capture."""
        self.p = pyaudio.PyAudio()
        self.is_capturing = False
        
    def list_loopback_devices(self):
        """List all WASAPI loopback devices."""
        print("\n=== WASAPI Loopback Devices ===")
        for device in self.p.get_loopback_device_info_generator():
            print(f"[{device['index']}] {device['name']}")
            print(f"    Channels: {device['maxInputChannels']}")
            print(f"    Sample Rate: {int(device['defaultSampleRate'])} Hz")
        print()
    
    def get_default_loopback_device(self):
        """Get the loopback device for the default output."""
        try:
            # Get default output
            default_output = self.p.get_default_output_device_info()
            
            # Find its loopback variant
            for device in self.p.get_loopback_device_info_generator():
                # Match by name (loopback devices have " [Loopback]" suffix)
                if default_output['name'] in device['name']:
                    return device
            
            # Fallback: return first loopback device
            for device in self.p.get_loopback_device_info_generator():
                return device
                
        except Exception as e:
            print(f"Error getting default loopback: {e}")
            return None
    
    def capture_stream(
        self,
        callback: Callable[[np.ndarray], None],
        device_index: Optional[int] = None,
        duration: Optional[float] = None,
        chunk_size: int = 1024
    ):
        """
        Capture audio from WASAPI loopback device.
        
        Args:
            callback: Function called with each audio chunk (numpy array)
            device_index: WASAPI loopback device index (None = auto-detect)
            duration: Duration in seconds (None = infinite)
            chunk_size: Number of frames per callback
        """
        # Get device
        if device_index is None:
            device_info = self.get_default_loopback_device()
            if not device_info:
                raise RuntimeError("No WASAPI loopback device found")
        else:
            device_info = self.p.get_device_info_by_index(device_index)
        
        print(f"🎙️  Capturing from: {device_info['name']}")
        
        # Audio parameters
        CHANNELS = device_info['maxInputChannels']
        RATE = int(device_info['defaultSampleRate'])
        
        # Open stream
        stream = self.p.open(
            format=pyaudio.paInt16,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            frames_per_buffer=chunk_size,
            input_device_index=device_info['index']
        )
        
        self.is_capturing = True
        frames_captured = 0
        total_frames = int(RATE / chunk_size * duration) if duration else None
        
        try:
            print("🎙️  Capturing audio... Press Ctrl+C to stop\n")
            
            while self.is_capturing:
                if total_frames and frames_captured >= total_frames:
                    break
                
                try:
                    # Read audio data with timeout to allow Ctrl+C responsiveness
                    data = stream.read(chunk_size, exception_on_overflow=False)
                    audio_chunk = np.frombuffer(data, dtype=np.int16)
                    
                    # Convert to float32 mono for Whisper
                    if CHANNELS == 2:
                        # Convert stereo to mono
                        audio_chunk = audio_chunk.reshape(-1, 2).mean(axis=1)
                    
                    # Normalize to float32 [-1, 1]
                    audio_chunk = audio_chunk.astype(np.float32) / 32768.0
                    
                    # Call user callback
                    callback(audio_chunk)
                    
                    frames_captured += 1
                except IOError as e:
                    # Handle buffer overflow/underflow gracefully
                    if e.errno != pyaudio.paInputOverflowed:
                        raise
                    continue
                
        except KeyboardInterrupt:
            print("\n✓ Capture stopped by user")
        finally:
            stream.stop_stream()
            stream.close()
            self.is_capturing = False
    
    def cleanup(self):
        """Clean up PyAudio resources."""
        self.p.terminate()
