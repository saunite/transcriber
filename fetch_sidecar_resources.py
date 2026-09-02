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
import sys

from faster_whisper.utils import download_model

MODEL_SIZE = "base"  # matches the CLI's --model default


def main() -> int:
    path = download_model(MODEL_SIZE, output_dir="src-tauri/resources/model")
    print(f"Staged '{MODEL_SIZE}' model at: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
