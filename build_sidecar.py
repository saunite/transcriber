#!/usr/bin/env python3
"""
Build the frozen transcriber sidecar binary (openspec/changes/add-tauri-gui
tasks 2.1-2.3). Run this on each target OS -- PyInstaller doesn't
cross-compile, so Windows/Linux/macOS sidecars each need building on that
OS.

The build is driven by transcriber-sidecar.spec rather than command-line
flags, because PyInstaller has no flag to exclude a bundled shared library
and the Linux sidecar must not ship its build host's libasound
(openspec/changes/fix-linux-live-capture-alsa). --onefile, the binary name,
the per-OS icon, and the faster_whisper asset data all live in that spec
now; only --distpath/--workpath stay here.

faster_whisper ships a VAD ONNX model as package data
(faster_whisper/assets/silero_vad_v6.onnx) that PyInstaller's default
import analysis does not pick up on its own (no bundled/community hook
covers it as of authoring -- confirmed missing by actually running the
frozen Windows binary, which failed with onnxruntime.NoSuchFile until it
was added explicitly). If faster_whisper adds more asset files in a future
version, they need adding to the spec's datas too.

Usage: python build_sidecar.py
"""
import platform
import subprocess
import sys
from pathlib import Path


def _in_virtualenv() -> bool:
    return sys.prefix != sys.base_prefix


def main() -> int:
    # ponytail: only catches the plain "no venv at all" case (the actual
    # cause of the flexiblas crash below), not a --system-site-packages venv.
    if not _in_virtualenv():
        print(
            "ERROR: build_sidecar.py must run from a venv (python -m venv .venv; "
            "source .venv/bin/activate; pip install -r requirements-linux.txt pyinstaller), "
            "not the system Python.\n"
            "System numpy/scipy on some distros (e.g. Fedora) link against FlexiBLAS, "
            "which loads its actual math backend via dlopen() at runtime -- invisible to "
            "PyInstaller's static analysis. The frozen binary then ships libflexiblas.so.3 "
            "with no backend and aborts on first use. A venv's pip-installed numpy/scipy "
            "wheels bundle their own BLAS statically, so this can't happen.",
            file=sys.stderr,
        )
        return 1

    system = platform.system().lower()
    # Everything that used to be a command-line flag -- --onefile, --name,
    # --add-data for faster_whisper's assets, and the per-OS --icon -- now
    # lives in transcriber-sidecar.spec, because a spec-based build IGNORES
    # those flags. The move exists so the Linux build can drop the bundled
    # libasound.so.2 from the analysis, which PyInstaller offers no flag for
    # (openspec/changes/fix-linux-live-capture-alsa design.md Decision 1).
    spec = Path(__file__).resolve().parent / "transcriber-sidecar.spec"
    args = [
        sys.executable, "-m", "PyInstaller",
        "--distpath", f"dist/{system}",
        "--workpath", f"build/{system}",
        "--noconfirm",
        str(spec),
    ]
    return subprocess.call(args)


if __name__ == "__main__":
    sys.exit(main())
