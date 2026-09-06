"""
Linux system-audio loopback capture via pactl/parec.

sounddevice/PortAudio's ALSA-only device enumeration (no "pulse" host API
in most prebuilt wheels -- confirmed via sd.query_hostapis()) cannot see
PipeWire/PulseAudio's real sink-monitor source: every ALSA-visible name
("pipewire", "default", a JACK bridge) silently captures pure silence
instead of system audio (openspec/changes/fix-linux-loopback-detection).
This mirrors wasapi_capture.py/macos_capture.py's shape (native
capture -> background reader thread -> queue -> capture_stream(callback)),
but drives the real PulseAudio/PipeWire client tools instead of a
sounddevice device index.
"""
import queue
import shutil
import subprocess
import threading
import numpy as np
from typing import Callable, Optional

CHUNK_FRAMES = 1024
SAMPLE_RATE = 16000
CHANNELS = 1
_BYTES_PER_FRAME = 2  # s16le mono


class LinuxLoopbackCapture:
    """Captures the real PulseAudio/PipeWire monitor source via `parec`."""

    def __init__(self):
        self.is_capturing = False
        self._process: Optional[subprocess.Popen] = None

    def get_default_loopback_device(self) -> Optional[dict]:
        """
        Find the real monitor source for the default sink.

        Returns a dict with 'name' (the pactl source name, passed to
        `parec --device=`), or None if pactl isn't on PATH or no monitor
        source exists.
        """
        if shutil.which('pactl') is None:
            return None

        try:
            sources_output = subprocess.run(
                ['pactl', 'list', 'sources', 'short'],
                capture_output=True, text=True, timeout=5, check=True
            ).stdout
        except (subprocess.SubprocessError, OSError):
            return None

        monitor_names = [
            fields[1]
            for fields in (line.split('\t') for line in sources_output.splitlines())
            if len(fields) >= 2 and fields[1].endswith('.monitor')
        ]
        if not monitor_names:
            return None

        try:
            default_sink = subprocess.run(
                ['pactl', 'get-default-sink'],
                capture_output=True, text=True, timeout=5, check=True
            ).stdout.strip()
        except (subprocess.SubprocessError, OSError):
            default_sink = None

        if default_sink:
            preferred = f"{default_sink}.monitor"
            if preferred in monitor_names:
                return {'name': preferred}

        return {'name': monitor_names[0]}

    def capture_stream(
        self,
        callback: Callable[[np.ndarray], None],
        device_index: Optional[str] = None,
        verbose: bool = False
    ) -> None:
        """
        Capture the monitor source in real time via `parec`, requesting
        16kHz mono directly -- PulseAudio/PipeWire resamples server-side,
        so no manual resampling is needed here.

        The blocking subprocess-pipe read runs on a background thread so
        Ctrl+C (delivered only to the main thread) is never stuck waiting
        on a stalled read -- same reasoning as WASAPICapture.capture_stream.

        Args:
            callback: Function called with each audio chunk (numpy array)
            device_index: pactl source name (None = auto-detect)
            verbose: print device/start/stop detail
        """
        if device_index is None:
            device_info = self.get_default_loopback_device()
            if not device_info:
                raise RuntimeError("No PulseAudio/PipeWire monitor source found")
            device_index = device_info['name']

        if verbose:
            print(f"🎙️  Capturing from: {device_index}")

        read_size = CHUNK_FRAMES * _BYTES_PER_FRAME

        self._process = subprocess.Popen(
            [
                'parec',
                f'--device={device_index}',
                '--format=s16le',
                f'--rate={SAMPLE_RATE}',
                f'--channels={CHANNELS}',
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )

        self.is_capturing = True
        audio_queue = queue.Queue()

        def _read_loop():
            """Background reader. cleanup() closing the process (called
            from the main thread on shutdown) forces a blocked read to
            return empty, which is how this loop exits."""
            stdout = self._process.stdout
            while self.is_capturing:
                data = stdout.read(read_size)
                # BufferedReader.read(n) blocks until n bytes or EOF; a
                # short, non-empty read only happens right at EOF/shutdown.
                usable = len(data) - (len(data) % _BYTES_PER_FRAME)
                if usable:
                    audio_chunk = np.frombuffer(data[:usable], dtype=np.int16).astype(np.float32) / 32768.0
                    audio_queue.put(audio_chunk)
                if len(data) < read_size:
                    self.is_capturing = False
                    break

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
            self.cleanup()
            reader_thread.join(timeout=5)

    def cleanup(self):
        """Terminate the parec subprocess if still running."""
        if self._process and self._process.poll() is None:
            self._process.terminate()
            try:
                self._process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self._process.kill()
        self._process = None
