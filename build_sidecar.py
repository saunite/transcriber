#!/usr/bin/env python3
"""
Build the frozen transcriber sidecar binary (openspec/changes/add-tauri-gui
tasks 2.1-2.3). Run this on each target OS -- PyInstaller doesn't
cross-compile, so Windows/Linux/macOS sidecars each need building on that
OS.

faster_whisper ships a VAD ONNX model as package data
(faster_whisper/assets/silero_vad_v6.onnx) that PyInstaller's default
import analysis does not pick up on its own (no bundled/community hook
covers it as of authoring -- confirmed missing by actually running the
frozen Windows binary, which failed with onnxruntime.NoSuchFile until
--add-data was added below). If faster_whisper adds more asset files in a
future version, they need to be added here too.

Usage: python build_sidecar.py
"""
import importlib.util
import platform
import subprocess
import sys
from pathlib import Path


def _faster_whisper_assets_dir() -> str:
    spec = importlib.util.find_spec("faster_whisper")
    return str(Path(spec.origin).parent / "assets")


def main() -> int:
    system = platform.system().lower()
    assets_dir = _faster_whisper_assets_dir()
    sep = ";" if platform.system() == "Windows" else ":"
    args = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--name", "transcriber-sidecar",
        "--distpath", f"dist/{system}",
        "--workpath", f"build/{system}",
        "--specpath", f"build/{system}",
        "--add-data", f"{assets_dir}{sep}faster_whisper/assets",
        "transcriber.py",
    ]
    return subprocess.call(args)


if __name__ == "__main__":
    sys.exit(main())
