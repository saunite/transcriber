#!/usr/bin/env python3
"""
Stage the installer resources bundled alongside the frozen sidecar
(openspec/changes/add-tauri-gui tasks 2.5-2.6): the `base` faster-whisper
model into src-tauri/resources/model/, matching tauri.conf.json's
bundle.resources entry (Tauri resolves bundle.resources paths relative to
src-tauri/, not the repo root).

ffmpeg is NOT fetched here: there's no single canonical "official" static
build URL to hardcode with confidence (unlike the model, which has one
unambiguous source via faster_whisper's own downloader). Whoever wires up
the CI build matrix (tasks.md 7.2) should pin a specific, verified ffmpeg
build source into resources/ffmpeg/ for each OS.

Usage: python fetch_sidecar_resources.py
"""
import sys

from faster_whisper.utils import download_model

MODEL_SIZE = "base"  # matches the CLI's --model default


def main() -> int:
    path = download_model(MODEL_SIZE, output_dir="src-tauri/resources/model")
    print(f"Staged '{MODEL_SIZE}' model at: {path}")
    print("ffmpeg is not fetched by this script -- see the module docstring.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
