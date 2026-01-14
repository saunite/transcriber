"""
Real-time audio capture utilities for cross-platform system audio recording.
Supports capturing system audio output (loopback) on Windows and Linux.
"""

import platform
import sys
import numpy as np
import sounddevice as sd
from typing import Callable, Optional
from queue import Queue
import threading


class AudioCapture:
    """Cross-platform real-time audio capture from system output."""
    
    def __init__(self, sample_rate: int = 16000, channels: int = 1):
        """
        Initialize audio capture.
        
        Args:
            sample_rate: Audio sample rate in Hz (default: 16000 for Whisper)
            channels: Number of audio channels (1=mono, 2=stereo)
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.system = platform.system()
        self.is_capturing = False
        self.audio_queue = Queue()
        
    def list_devices(self) -> None:
        """List all available audio devices."""
        print("\n=== Available Audio Devices ===")
        devices = sd.query_devices()
        for idx, device in enumerate(devices):
            print(f"[{idx}] {device['name']}")
            print(f"    Max Input Channels: {device['max_input_channels']}")
            print(f"    Default Sample Rate: {device['default_samplerate']}")
        print()
    
    def get_loopback_device(self) -> Optional[int]:
        """
        Find the system audio loopback device.
        
        Returns:
            Device index for loopback recording, or None if not found
        """
        devices = sd.query_devices()
        
        if self.system == "Windows":
            # On Windows, look for WASAPI loopback devices
            # These often have "Stereo Mix" or contain the device name + "(loopback)"
            for idx, device in enumerate(devices):
                name = device['name'].lower()
                if 'stereo mix' in name or 'wave out' in name or 'loopback' in name:
                    if device['max_input_channels'] > 0:
                        return idx
                        
        elif self.system == "Linux":
            # On Linux with PulseAudio/PipeWire, look for monitor devices
            # First try explicit monitor sources
            for idx, device in enumerate(devices):
                name = device['name'].lower()
                if 'monitor' in name and device['max_input_channels'] > 0:
                    return idx
            
            # If no explicit monitor found, try pipewire (usually the monitor source on modern Linux)
            for idx, device in enumerate(devices):
                name = device['name'].lower()
                if 'pipewire' in name and device['max_input_channels'] > 0:
                    return idx
            
            # Last resort: try 'default' device on Linux (often routes to monitor on PipeWire)
            for idx, device in enumerate(devices):
                name = device['name'].lower()
                if name == 'default' and device['max_input_channels'] > 0:
                    return idx
        
        return None
    
    def _audio_callback(self, indata, frames, time_info, status):
        """Callback function for audio stream."""
        if status:
            print(f"Audio callback status: {status}", file=sys.stderr)
        
        # Put audio data in queue for processing
        self.audio_queue.put(indata.copy())
    
    def capture_stream(
        self,
        callback: Callable[[np.ndarray], None],
        device: Optional[int] = None,
        duration: Optional[float] = None,
        chunk_size: int = 1024
    ) -> None:
        """
        Capture audio from system in real-time and send to callback.
        
        Args:
            callback: Function to process audio chunks (receives numpy array)
            device: Device index to capture from (None = default, -1 = auto-detect loopback)
            duration: Duration to capture in seconds (None = infinite)
            chunk_size: Size of audio chunks to capture at once
        """
        # Auto-detect loopback device if requested
        if device == -1:
            device = self.get_loopback_device()
            if device is None:
                print("\n⚠️  Warning: Could not auto-detect loopback device.")
                print("Available devices:")
                self.list_devices()
                print("\nPlease specify a device manually or set up audio loopback:")
                if self.system == "Windows":
                    print("  - Enable 'Stereo Mix' in Windows Sound Settings")
                    print("  - Or install VB-Cable virtual audio device")
                elif self.system == "Linux":
                    print("  - Use PulseAudio/PipeWire monitor source")
                    print("  - Run: pactl list sources | grep -i monitor")
                raise RuntimeError("No loopback device found")
            print(f"Using loopback device: {sd.query_devices(device)['name']}")
        
        self.is_capturing = True
        start_time = None
        
        try:
            with sd.InputStream(
                device=device,
                channels=self.channels,
                samplerate=self.sample_rate,
                blocksize=chunk_size,
                callback=self._audio_callback
            ):
                print("🎙️  Capturing audio... Press Ctrl+C to stop")
                start_time = __import__('time').time()
                
                # Process audio from queue
                while self.is_capturing:
                    if not self.audio_queue.empty():
                        audio_chunk = self.audio_queue.get()
                        callback(audio_chunk)
                    
                    # Check duration
                    if duration is not None and start_time is not None:
                        elapsed = __import__('time').time() - start_time
                        if elapsed >= duration:
                            print(f"\n✓ Capture completed ({duration}s)")
                            break
                    
                    # Small sleep to prevent busy-waiting
                    __import__('time').sleep(0.01)
                        
        except KeyboardInterrupt:
            print("\n\n✓ Capture stopped by user")
        except Exception as e:
            print(f"\n❌ Error during capture: {e}")
            raise
        finally:
            self.is_capturing = False
    
    def capture_to_file(
        self,
        output_file: str,
        duration: float,
        device: Optional[int] = None
    ) -> None:
        """
        Capture audio to a WAV file.
        
        Args:
            output_file: Path to output WAV file
            duration: Duration to record in seconds
            device: Device index to capture from
        """
        import soundfile as sf
        
        print(f"Recording {duration} seconds to {output_file}...")
        
        if device == -1:
            device = self.get_loopback_device()
        
        recording = sd.rec(
            int(duration * self.sample_rate),
            samplerate=self.sample_rate,
            channels=self.channels,
            device=device
        )
        sd.wait()  # Wait until recording is finished
        
        # Save as WAV file
        sf.write(output_file, recording, self.sample_rate)
        print(f"✓ Saved to {output_file}")


def setup_loopback_instructions():
    """Print instructions for setting up audio loopback on the current system."""
    system = platform.system()
    
    print("\n=== Audio Loopback Setup Instructions ===\n")
    
    if system == "Windows":
        print("Windows - Enable Stereo Mix:")
        print("1. Right-click the speaker icon in taskbar → Sounds")
        print("2. Go to 'Recording' tab")
        print("3. Right-click empty area → Show Disabled Devices")
        print("4. Enable 'Stereo Mix' or 'Wave Out Mix'")
        print("5. Set it as default recording device")
        print("\nAlternatively, install VB-Cable virtual audio device:")
        print("  https://vb-audio.com/Cable/")
        
    elif system == "Linux":
        print("Linux - PulseAudio/PipeWire Monitor:")
        print("1. List monitor sources:")
        print("   pactl list sources | grep -i monitor")
        print("\n2. Find your monitor device name")
        print("\n3. The transcriber will auto-detect monitor devices")
        
    else:
        print(f"Platform {system} - Please refer to system documentation")
    
    print("\n" + "="*50 + "\n")
