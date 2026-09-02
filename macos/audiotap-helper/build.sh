#!/usr/bin/env bash
# Build the macOS system-audio tap helper (macos_capture.py spawns the
# resulting binary at ./audiotap-helper). Requires Xcode Command Line Tools
# (Swift 5.9+ toolchain) on macOS, targeting the macOS 14.4+ SDK (Core Audio
# Process Tap API). This must be run on macOS -- it cannot be built or
# verified on non-macOS machines, and this build script itself is untested
# (see design.md).
#
# Run `swift test` first (or via CI) to exercise the hardware-independent
# logic in AudioTapCore -- see tasks.md 4.3.
set -euo pipefail
cd "$(dirname "$0")"

swift build -c release --arch arm64 --arch x86_64
cp .build/apple/Products/Release/audiotap-helper ./audiotap-helper

echo "Built ./audiotap-helper (universal arm64 + x86_64)"
echo ""
echo "For an arm64-only build (e.g. if the x86_64 SDK leg is unavailable):"
echo "  swift build -c release"
echo "  cp .build/release/audiotap-helper ./audiotap-helper"
