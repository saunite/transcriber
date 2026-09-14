#!/usr/bin/env python3
"""Runs every automated test suite and exits 1 if any failed.

Order: `cargo test` in src-tauri/, every root test_*.py, every tests/test_*.py.
Each Python suite runs with this interpreter, so `.venv/bin/python run_tests.py`
uses the project venv. A failing suite never stops the rest from running.
"""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main() -> int:
    suites = [("cargo test", ["cargo", "test"], ROOT / "src-tauri")]
    for script in sorted(ROOT.glob("test_*.py")) + sorted((ROOT / "tests").glob("test_*.py")):
        suites.append((str(script.relative_to(ROOT)), [sys.executable, str(script)], ROOT))

    results = []
    for name, cmd, cwd in suites:
        print(f"\n=== {name}", flush=True)
        start = time.monotonic()
        try:
            ok = subprocess.run(cmd, cwd=cwd).returncode == 0
        except FileNotFoundError as exc:
            print(exc)
            ok = False
        results.append((name, ok, time.monotonic() - start))

    print("\n=== Summary")
    for name, ok, secs in results:
        print(f"{'PASS' if ok else 'FAIL'}  {secs:6.1f}s  {name}")
    failed = [name for name, ok, _ in results if not ok]
    total = sum(secs for _, _, secs in results)
    print(f"\n{len(results) - len(failed)}/{len(results)} passed in {total:.1f}s")
    if failed:
        print("Failed: " + ", ".join(failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
