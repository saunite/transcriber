#!/usr/bin/env bash
# Build the macOS system-audio tap helper (macos_capture.py spawns the
# resulting binary). Requires Xcode Command Line Tools (swiftc) on macOS,
# targeting the macOS 14.4+ SDK (Core Audio Process Tap API). This must be
# run on macOS -- it cannot be built or verified on non-macOS machines,
# and this build script itself is untested (see design.md).
set -euo pipefail
cd "$(dirname "$0")"

swiftc -O main.swift -o audiotap-helper -target arm64-apple-macos14.4

echo "Built ./audiotap-helper (arm64)"
echo ""
echo "For a universal (arm64 + x86_64) binary:"
echo "  swiftc -O main.swift -o audiotap-helper-x86_64 -target x86_64-apple-macos14.4"
echo "  lipo -create audiotap-helper audiotap-helper-x86_64 -output audiotap-helper"
