"""
Test for add-live-default-output: live capture saves to a stamped
transcript_<YYYYMMDD_HHMMSS>.txt unless --output or --no-output says
otherwise (specs/cli "Live capture saves a transcript by default").

Run: python test_live_default_output.py
"""
from argparse import Namespace
from datetime import datetime

from transcriber import _live_output_path

NOW = datetime(2026, 9, 11, 14, 5, 9)


def _args(**overrides):
    base = dict(live=True, output=None, no_output=False)
    base.update(overrides)
    return Namespace(**base)


def test_bare_live_gets_stamped_default():
    assert _live_output_path(_args(), NOW) == "transcript_20260911_140509.txt"
    print("OK: bare --live saves to transcript_20260911_140509.txt")


def test_explicit_output_is_kept():
    assert _live_output_path(_args(output="meeting.txt"), NOW) == "meeting.txt"
    print("OK: --output is used as given")


def test_no_output_saves_nothing():
    assert _live_output_path(_args(no_output=True), NOW) is None
    print("OK: --no-output saves nothing")


def test_file_mode_untouched():
    assert _live_output_path(_args(live=False), NOW) is None
    print("OK: non-live runs are left to file mode's own naming")


if __name__ == "__main__":
    test_bare_live_gets_stamped_default()
    test_explicit_output_is_kept()
    test_no_output_saves_nothing()
    test_file_mode_untouched()
