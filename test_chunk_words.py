#!/usr/bin/env python3
"""The overlap between live chunks is split at its midpoint, by word, so speech
there is kept once (openspec/changes/fix-true-scale-time-axis).

Drives transcriber._process_audio_chunk with a fake engine; no model needed.
Run: python test_chunk_words.py
"""
import sys

import numpy as np

import transcriber


class Engine:
    def __init__(self, segments):
        self.segments = segments

    def transcribe_chunk(self, audio, language=None):
        return self.segments

    def format_timestamp(self, start, end):
        return f"[{start:.1f} -> {end:.1f}]"


def seg(*words):
    return {"start": words[0][0], "end": words[-1][1], "text": " ".join(w[2] for w in words),
            "words": [(s, e, f" {t}") for s, e, t in words]}


def texts(segments, chunk_start=5.0, lead=0.5, trail=0.5):
    audio = np.zeros(10 * 16000, np.float32)
    results, spoke = transcriber._process_audio_chunk(Engine(segments), audio, chunk_start, lead=lead, trail=trail)
    return [(ts, s["text"]) for ts, s in results], spoke


def main() -> int:
    # Words in the leading and trailing half-overlaps go; those inside stay.
    got, spoke = texts([seg((0.3, 0.45, "early"), (0.5, 0.8, "kept"), (9.4, 9.6, "late")),
                        seg((9.7, 9.9, "gone"))])
    assert got == [("[5.5 -> 14.6]", "kept late")], got
    assert spoke

    # A segment left with no words is dropped; nothing spoken remains.
    got, spoke = texts([seg((0.1, 0.3, "only"))])
    assert got == [] and not spoke, got

    # The first chunk has no leading overlap, so its first word stays.
    got, _ = texts([seg((0.1, 0.3, "first"))], chunk_start=0.0, lead=0.0)
    assert got == [("[0.1 -> 0.3]", "first")], got

    # A segment without word times is kept or dropped by its own start.
    plain = [{"start": 0.2, "end": 1.0, "text": "a"}, {"start": 2.0, "end": 3.0, "text": "b"}]
    got, _ = texts(plain, chunk_start=0.0)
    assert got == [("[2.0 -> 3.0]", "b")], got

    print("test_chunk_words: all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
