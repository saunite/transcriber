#!/usr/bin/env python3
"""Engine tests on real input (openspec/changes/add-automated-local-tests).

- Speech: transcribes a local English recording that is never committed
  (--speech, or TRANSCRIBER_TEST_SPEECH) and checks the transcript's format,
  detected language and that most of the key words of its script (--script,
  default: the same name with .txt) came through. Skipped when none is set.
- Undecodable input: random bytes must fail cleanly, with no traceback and no
  transcript file.

Run:  python tests/test_engine.py [--speech clip.ogg] [--engine dist/linux/transcriber-sidecar] [--model-path DIR]
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LINE = re.compile(r"^\[[^\]]+ -> [^\]]+\] \S")
KEYWORD_THRESHOLD = 0.7


def run_engine(engine, model_path, media, output):
    result = subprocess.run(
        [*engine, "--file", str(media), "--model-path", str(model_path), "--output", str(output)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    return result.returncode, result.stdout + result.stderr


def words(text):
    return set(re.findall(r"[a-z]+", text.lower()))


def check_speech(engine, model_path, media, script):
    with tempfile.TemporaryDirectory() as tmp:
        output = Path(tmp) / "speech.txt"
        code, out = run_engine(engine, model_path, media, output)
        assert code == 0, f"engine exited {code}:\n{out[-2000:]}"
        assert "Traceback" not in out, f"traceback in engine output:\n{out[-2000:]}"
        assert output.is_file(), "no transcript file was written"
        transcript = output.read_text(encoding="utf-8")

    lines = [l for l in transcript.splitlines() if l.strip() and not l.startswith("#")]
    assert lines, "the transcript is empty"
    bad = [l for l in lines if not LINE.match(l)]
    assert not bad, f"lines without a [start -> end] timestamp: {bad[:3]}"
    assert "Detected language: en" in out, "the engine did not report detecting English"

    key = {w for w in words(script.read_text(encoding="utf-8")) if len(w) >= 5}
    heard = key & words(transcript)
    ratio = len(heard) / len(key)
    assert ratio >= KEYWORD_THRESHOLD, (
        f"only {len(heard)}/{len(key)} key words recognised ({ratio:.0%}, need {KEYWORD_THRESHOLD:.0%}); "
        f"missing: {sorted(key - heard)}"
    )


def check_undecodable(engine, model_path, media=None):
    with tempfile.TemporaryDirectory() as tmp:
        if media is None:
            media = Path(tmp) / "garbage.mp3"
            media.write_bytes(os.urandom(20000))
        output = Path(tmp) / "garbage.txt"
        code, out = run_engine(engine, model_path, media, output)
        assert code != 0, "the engine exited 0 on undecodable input"
        assert "No decodable audio" in out or "Could not decode" in out, f"no decode-failure message:\n{out[-2000:]}"
        assert "Traceback" not in out, f"traceback in engine output:\n{out[-2000:]}"
        assert not output.exists(), "a transcript file was left behind"


def repeated_trigrams(text, window=12):
    """Word trigrams that recur within `window` words: a phrase said twice."""
    w = re.findall(r"[a-z']+", text.lower())
    grams = [tuple(w[i:i + 3]) for i in range(len(w) - 2)]
    return sum(1 for i, g in enumerate(grams) if g in grams[max(0, i - window):i])


def check_live_chunks(model_path, media, script):
    """Cuts the recording as live capture does (10 s chunks, 1 s carried
    overlap) and checks the overlap is not transcribed twice, while boundary
    words still come through (openspec/changes/fix-true-scale-time-axis)."""
    sys.path.insert(0, str(ROOT))
    import transcriber
    from faster_whisper import decode_audio
    from transcription_engine import TranscriptionEngine

    audio = decode_audio(str(media), sampling_rate=16000)
    engine = TranscriptionEngine(model_path=str(model_path))
    chunk, overlap = 10 * 16000, 16000
    lines, position = [], 0.0
    for start in range(0, len(audio) - chunk + 1, chunk - overlap):
        results, _ = transcriber._process_audio_chunk(
            engine, audio[start:start + chunk], position,
            lead=overlap / 32000 if start else 0.0, trail=overlap / 32000)
        lines += [seg["text"] for _, seg in results]
        position += (chunk - overlap) / 16000
    transcript = " ".join(lines)

    said = script.read_text(encoding="utf-8")
    assert repeated_trigrams(transcript) <= repeated_trigrams(said), f"a phrase repeats: {transcript}"
    key = {w for w in words(said) if len(w) >= 5}
    heard = key & words(transcript)
    assert len(heard) / len(key) >= KEYWORD_THRESHOLD, f"missing key words {sorted(key - heard)}: {transcript}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--engine", help="frozen engine binary (default: transcriber.py with this Python)")
    parser.add_argument("--model-path", type=Path, default=ROOT / "src-tauri" / "resources" / "model")
    parser.add_argument("--speech", type=Path, default=os.environ.get("TRANSCRIBER_TEST_SPEECH") or None,
                        help="local English recording, kept outside the repo (default: $TRANSCRIBER_TEST_SPEECH)")
    parser.add_argument("--script", type=Path, default=os.environ.get("TRANSCRIBER_TEST_SCRIPT") or None,
                        help="what the recording says (default: the recording's path with .txt)")
    args = parser.parse_args()
    script = args.script or (args.speech.with_suffix(".txt") if args.speech else None)
    engine = [args.engine] if args.engine else [sys.executable, str(ROOT / "transcriber.py")]

    if not (args.model_path / "model.bin").is_file():
        print(f"FAIL  no model at {args.model_path}: stage it with `python fetch_sidecar_resources.py` first")
        return 1

    checks = [("undecodable input fails cleanly", lambda: check_undecodable(engine, args.model_path))]
    if args.speech is None:
        print("SKIP  speech sample: no recording set. Pass --speech <audio>, or set TRANSCRIBER_TEST_SPEECH, "
              "with the words it says in a .txt beside it")
    elif not (args.speech.is_file() and script.is_file()):
        print(f"FAIL  speech sample: need both {args.speech} and {script}")
        return 1
    else:
        checks.insert(0, ("speech sample transcribes", lambda: check_speech(engine, args.model_path, args.speech, script)))
        if not args.engine:  # in-process: only when testing the source engine
            checks.insert(1, ("live chunks do not repeat words",
                              lambda: check_live_chunks(args.model_path, args.speech, script)))

    failures = 0
    for name, check in checks:
        try:
            check()
            print(f"PASS  {name}")
        except AssertionError as exc:
            failures += 1
            print(f"FAIL  {name}: {exc}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
