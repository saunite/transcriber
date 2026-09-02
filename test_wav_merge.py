"""
Round-trip test for drop-ffmpeg-dependency: asserts _merge_sys_mic_wav
(transcriber.py) produces the same shape of output the ffmpeg
`amerge=duration=shortest` call it replaces did -- a stereo WAV with
system audio on the left channel and mic audio on the right, truncated to
the shorter of the two inputs (see
openspec/changes/drop-ffmpeg-dependency/design.md, Decision 2).

Uses synthetic mono 16-bit WAVs of *different* lengths -- no real audio
device or subprocess involved, consistent with test_transcript_line_format.py.

Run: python test_wav_merge.py
"""
import os
import tempfile
import wave

import numpy as np

from transcriber import _merge_sys_mic_wav


def _write_mono_wav(path: str, samples: np.ndarray, sample_rate: int = 16000) -> None:
    with wave.open(path, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)  # int16
        w.setframerate(sample_rate)
        w.writeframes(samples.tobytes())


def test_merge_produces_stereo_16bit_16khz():
    with tempfile.TemporaryDirectory() as tmp:
        sys_path = os.path.join(tmp, "sys.wav")
        mic_path = os.path.join(tmp, "mic.wav")
        out_path = os.path.join(tmp, "merged.wav")

        # Different lengths -- sys longer than mic, mirroring a real
        # session where the two capture streams don't stop at the exact
        # same sample.
        sys_samples = np.arange(1000, dtype=np.int16)
        mic_samples = (-np.arange(700, dtype=np.int16))

        _write_mono_wav(sys_path, sys_samples)
        _write_mono_wav(mic_path, mic_samples)

        _merge_sys_mic_wav(sys_path, mic_path, out_path)

        with wave.open(out_path, 'rb') as out_wav:
            assert out_wav.getnchannels() == 2, "merged WAV must be stereo"
            assert out_wav.getsampwidth() == 2, "merged WAV must stay 16-bit"
            assert out_wav.getframerate() == 16000, "merged WAV must stay 16kHz"

            shorter = min(len(sys_samples), len(mic_samples))
            assert out_wav.getnframes() == shorter, (
                f"expected {shorter} frames (truncated to shorter input), "
                f"got {out_wav.getnframes()}"
            )

            frames = np.frombuffer(out_wav.readframes(out_wav.getnframes()), dtype=np.int16)
            stereo = frames.reshape(-1, 2)
            left, right = stereo[:, 0], stereo[:, 1]

            assert np.array_equal(left, sys_samples[:shorter]), "left channel must round-trip system audio"
            assert np.array_equal(right, mic_samples[:shorter]), "right channel must round-trip mic audio"

        print("OK: merged WAV is stereo/16-bit/16kHz, truncated to the shorter input, "
              "channels round-trip sys (L) and mic (R) correctly")


if __name__ == "__main__":
    test_merge_produces_stereo_16bit_16khz()
