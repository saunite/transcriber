"""
WASAPI loopback audio capture for Windows - captures system audio including Bluetooth
"""
import queue
import threading
import pyaudiowpatch as pyaudio
import numpy as np
from typing import Callable, Optional


class WASAPICapture:
    """Windows WASAPI loopback capture - works with Bluetooth headsets!"""
    
    def __init__(self):
        """Initialize WASAPI capture."""
        self.p = pyaudio.PyAudio()
        self.is_capturing = False
        
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
        verbose: bool = False
    ):
        """
        Capture audio from WASAPI loopback device.

        The blocking device read runs on a background thread so Ctrl+C
        (delivered only to the main thread) is never stuck waiting on a
        stalled read; the main thread only ever blocks on a short-timeout
        queue read, which always returns control to the interpreter.

        Args:
            callback: Function called with each audio chunk (numpy array)
            device_index: WASAPI loopback device index (None = auto-detect)
            verbose: print device/start/stop detail (transcriber.py's compact
                default already covers this via its own status lines)
        """
        # Get device
        if device_index is None:
            device_info = self.get_default_loopback_device()
            if not device_info:
                raise RuntimeError("No WASAPI loopback device found")
        else:
            device_info = self.p.get_device_info_by_index(device_index)

        if verbose:
            print(f"🎙️  Capturing from: {device_info['name']}")

        # Audio parameters
        CHANNELS = device_info['maxInputChannels']
        RATE = int(device_info['defaultSampleRate'])
        chunk_size = 1024

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
        audio_queue = queue.Queue()

        def _read_loop():
            """Background reader. stream.close() (called from the main
            thread on shutdown) forces a blocked read to raise here,
            which is how this loop exits."""
            while self.is_capturing:
                try:
                    data = stream.read(chunk_size, exception_on_overflow=False)
                except IOError as e:
                    if e.errno == pyaudio.paInputOverflowed:
                        continue
                    self.is_capturing = False  # unrecoverable read error or closed stream
                    break
                except Exception:
                    self.is_capturing = False
                    break

                audio_chunk = np.frombuffer(data, dtype=np.int16)
                if CHANNELS == 2:
                    audio_chunk = audio_chunk.reshape(-1, 2).mean(axis=1)
                audio_chunk = audio_chunk.astype(np.float32) / 32768.0
                audio_queue.put(audio_chunk)

        reader_thread = threading.Thread(target=_read_loop, daemon=True)
        reader_thread.start()

        try:
            if verbose:
                print("🎙️  Capturing audio... Press Ctrl+C to stop\n")

            while self.is_capturing:
                try:
                    audio_chunk = audio_queue.get(timeout=0.1)
                except queue.Empty:
                    continue
                callback(audio_chunk)

        except KeyboardInterrupt:
            if verbose:
                print("\n✓ Capture stopped by user")
        finally:
            self.is_capturing = False
            stream.stop_stream()
            stream.close()
            reader_thread.join(timeout=5)
    
    def cleanup(self):
        """Clean up PyAudio resources."""
        self.p.terminate()
