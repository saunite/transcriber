#!/usr/bin/env bash
# Live Audio Transcription Launcher for Linux
# This script starts live transcription of system audio

echo "============================================================"
echo "Live Audio Transcriber"
echo "============================================================"
echo ""
echo "This will capture and transcribe system audio in real-time"
echo ""
echo "Press Ctrl+C to stop transcription"
echo "============================================================"
echo ""

# Prefer the project venv (expected to be Python 3.11+); fall back to system python
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PY="${SCRIPT_DIR}/.venv/bin/python"
if [[ -x "${VENV_PY}" ]]; then
  PY_CMD="${VENV_PY}"
else
  PY_CMD="python3"
fi

# Find and list audio devices with monitors
echo "Scanning for available audio devices..."
echo ""

# Try to find monitor sources using pactl
MONITORS=$(pactl list short sources 2>/dev/null | grep -i monitor)

if [[ -n "${MONITORS}" ]]; then
    echo "📢 Found system audio monitor sources:"
    echo "${MONITORS}"
    echo ""
    echo "The transcriber will try to auto-detect these."
    echo ""
else
    echo "⚠️  No monitor sources found. Available devices:"
    "${PY_CMD}" transcriber.py --list-devices
    echo ""
    echo "If no 'monitor' devices appear above:"
    echo "  1. Ensure PulseAudio/PipeWire is running"
    echo "  2. Try: pactl list short sources | grep -i monitor"
    echo "  3. Or load snd-aloop: sudo modprobe snd-aloop"
    echo ""
fi

# Check if device index was provided as command-line argument
if [[ -n "$1" && "$1" =~ ^[0-9]+$ ]]; then
    AUDIO_DEVICE_FLAG="--audio-device $1"
    echo "Using audio device: $1"
else
    AUDIO_DEVICE_FLAG="--audio-device -1"
    echo "Using auto-detect mode..."
fi

echo ""

# Generate timestamp for output filename
timestamp=$(date +%Y%m%d_%H%M%S)
output_file="transcription_${timestamp}.txt"

echo "Starting transcription..."
echo "Output will be saved to: ${output_file}"
echo "Auto-stop after 10 minutes of silence (use --silence-timeout 0 to disable)"
echo ""

# Start transcription with selected audio device
# To disable auto-stop, add: --silence-timeout 0
"${PY_CMD}" transcriber.py --live ${AUDIO_DEVICE_FLAG} --model base --output "${output_file}" --chunk-duration 10
