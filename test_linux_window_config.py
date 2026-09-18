#!/usr/bin/env python3
"""The Linux window config repeats the main one except that it starts hidden
(openspec/changes/fix-linux-native-window-frame, design.md Decision 2).

Tauri merges src-tauri/tauri.linux.conf.json over tauri.conf.json on Linux, and
the merge replaces arrays whole, so the window entry is written twice. The setup
hook shows the window once tao's header bar is removed; a size or title changed
in only one file would silently differ between Linux and the other platforms.
Run: python test_linux_window_config.py
"""
import json
import sys
from pathlib import Path

TAURI = Path(__file__).resolve().parent / "src-tauri"


def main() -> int:
    main_windows = json.loads((TAURI / "tauri.conf.json").read_text())["app"]["windows"]
    linux_windows = json.loads((TAURI / "tauri.linux.conf.json").read_text())["app"]["windows"]
    assert len(main_windows) == len(linux_windows) == 1, "expected exactly one window in each config"
    main_win, linux_win = main_windows[0], linux_windows[0]
    assert linux_win.get("visible") is False, "the Linux window must start hidden"
    strip = lambda w: {k: v for k, v in w.items() if k != "visible"}
    assert strip(main_win) == strip(linux_win), (
        f"the window entries differ beyond 'visible':\n  tauri.conf.json:       {strip(main_win)}\n"
        f"  tauri.linux.conf.json: {strip(linux_win)}"
    )
    print("PASS  Linux window config matches the main one and starts hidden")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except AssertionError as exc:
        print(f"FAIL  Linux window config: {exc}")
        sys.exit(1)
