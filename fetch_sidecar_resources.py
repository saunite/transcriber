#!/usr/bin/env python3
"""
Stage the installer resources bundled alongside the frozen sidecar
(openspec/changes/add-tauri-gui tasks 2.5-2.6): the `base` faster-whisper
model into src-tauri/resources/model/, matching tauri.conf.json's
bundle.resources entry (Tauri resolves bundle.resources paths relative to
src-tauri/, not the repo root).

No ffmpeg binary is fetched, and none is needed: the sidecar decodes audio
and video via PyAV (bundled with faster-whisper, frozen into the sidecar
by build_sidecar.py), not an external ffmpeg process. See
openspec/changes/drop-ffmpeg-dependency/.

Usage: python fetch_sidecar_resources.py
"""
import shutil
import sys
from pathlib import Path

from faster_whisper.utils import download_model

MODEL_SIZE = "base"  # matches the CLI's --model default


def main() -> int:
    path = download_model(MODEL_SIZE, output_dir="src-tauri/resources/model")
    # download_model leaves its own bookkeeping (per-file .lock files, a
    # CACHEDIR.TAG, a trees/*.json) in .cache/ inside the output dir, and
    # tauri.conf.json's bundle.resources copies this directory wholesale --
    # so those files shipped inside the .deb/.rpm/AppImage
    # (openspec/changes/drop-model-cache-from-bundles). ignore_errors: a
    # future faster-whisper may stop creating it.
    shutil.rmtree(Path(path) / ".cache", ignore_errors=True)
    print(f"Staged '{MODEL_SIZE}' model at: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
