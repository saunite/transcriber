"""
Fixture test for add-tauri-gui: asserts transcript lines emitted by
transcriber.py's live-capture paths match the regex the Tauri sidecar
wrapper uses to parse them (see
openspec/changes/add-tauri-gui/design.md, Decision 2). This is the
mitigation for that design's stated risk: if the engine's line format ever
changes, this test fails in CI instead of the GUI silently misparsing the
live transcript in the field.

Exercises the actual formatting functions used by the engine's
live-capture code paths (TranscriptionEngine.format_timestamp,
transcriber._wall_clock_stamp) against synthetic segment data -- no real
audio device, subprocess, or Whisper model involved, consistent with how
test_wasapi_capture.py fakes the layer below it instead of doing real
audio I/O.

Run: python test_transcript_line_format.py
"""
import re

from transcription_engine import TranscriptionEngine
from transcriber import _wall_clock_stamp

# Python-syntax mirror of the regex documented in
# openspec/changes/add-tauri-gui/design.md, Decision 2, for the Rust
# sidecar wrapper to use when parsing the engine's stdout.
TRANSCRIPT_LINE_REGEX = re.compile(r"^\[(?P<ts>[^\]]+)\](?:\s\[(?P<tag>SYS|MIC)\])?\s(?P<text>.*)$")


def _relative_timestamp_line(text: str, tag: str = None) -> str:
    """Build a line exactly as the relative-timestamp emit call sites do
    (transcribe_live_simple / _wasapi / _coreaudio_tap all use
    engine.format_timestamp(...) + optional [TAG] + text)."""
    engine = TranscriptionEngine.__new__(TranscriptionEngine)  # skip __init__, no model load needed
    stamp = engine.format_timestamp(1.5, 3.25)
    return f"{stamp} [{tag}] {text}" if tag else f"{stamp} {text}"


def test_simple_mode_line_matches():
    line = _relative_timestamp_line("hello world")
    match = TRANSCRIPT_LINE_REGEX.match(line)
    assert match, f"simple-mode line did not match: {line!r}"
    assert match.group("tag") is None
    assert match.group("text") == "hello world"
    print(f"OK: simple-mode line matches -- {line!r}")


def test_sys_tagged_line_matches():
    line = _relative_timestamp_line("system audio text", tag="SYS")
    match = TRANSCRIPT_LINE_REGEX.match(line)
    assert match, f"SYS-tagged line did not match: {line!r}"
    assert match.group("tag") == "SYS"
    assert match.group("text") == "system audio text"
    print(f"OK: [SYS]-tagged line matches -- {line!r}")


def test_mic_tagged_line_matches():
    line = _relative_timestamp_line("mic audio text", tag="MIC")
    match = TRANSCRIPT_LINE_REGEX.match(line)
    assert match, f"MIC-tagged line did not match: {line!r}"
    assert match.group("tag") == "MIC"
    print(f"OK: [MIC]-tagged line matches -- {line!r}")


def test_wall_clock_stamp_line_matches():
    """Mirrors the --actual-time emit call sites: `_wall_clock_stamp() + [TAG] + text`."""
    stamp = _wall_clock_stamp()
    line = f"{stamp} [SYS] wall clock text"
    match = TRANSCRIPT_LINE_REGEX.match(line)
    assert match, f"wall-clock line did not match: {line!r}"
    assert match.group("ts") == stamp.strip("[]")
    print(f"OK: wall-clock timestamp line matches -- {line!r}")


def test_non_transcript_lines_do_not_match():
    """Headers/status lines must NOT match, so the Rust wrapper routes them to
    the sidecar-log fallback (design.md Decision 2) instead of the transcript view."""
    non_transcript_lines = [
        "Audio Transcriber",
        "  (no speech detected)",
        "🎙️  Listening... (Press Ctrl+C to stop)",
        "",
    ]
    for line in non_transcript_lines:
        assert not TRANSCRIPT_LINE_REGEX.match(line), f"non-transcript line unexpectedly matched: {line!r}"
    print("OK: header/status lines do not match the transcript-line regex")


if __name__ == "__main__":
    test_simple_mode_line_matches()
    test_sys_tagged_line_matches()
    test_mic_tagged_line_matches()
    test_wall_clock_stamp_line_matches()
    test_non_transcript_lines_do_not_match()
