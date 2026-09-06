#!/usr/bin/env bash
# Teams Meeting Transcription Launcher (macOS)
# This script starts live transcription with dual-capture (system audio +
# microphone, tagged [SYS]/[MIC]) via Core Audio Process Tap (macOS 14.4+)
# for complete Teams meeting coverage. Mirrors win-start-transcription.bat's
# and linux-start-transcription.sh's argument convention and defaults.
#
# Usage: ./mac-start-transcription.sh [name-prefix] [transcriber flags...]
#   name-prefix:  prefix for the output filename (default: meeting)
#   Timestamps default to wall-clock time (--actual-time is always passed).
#   flags:        passed through to transcriber.py, e.g.
#                   --silence-timeout 0      never auto-stop on silence
#                   --save-audio             also save sys/mic WAV files
#                   --language en            force a language
#   Example: ./mac-start-transcription.sh sprint-review --silence-timeout 0
#
# No device-scanning preamble needed here: Core Audio Process Tap requires
# no manual setup beyond granting the audio-capture permission macOS
# prompts for on first use (see add-macos-capture).
set -euo pipefail

NAME_PREFIX="meeting"
if [[ $# -gt 0 && "$1" != -* ]]; then
    NAME_PREFIX="$1"
    shift
fi

# Prefer the project venv (expected to be Python 3.11+); fall back to system python
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PY="${SCRIPT_DIR}/.venv/bin/python"
if [[ -x "${VENV_PY}" ]]; then
    PY_CMD="${VENV_PY}"
else
    PY_CMD="python3"
fi

# Generate timestamp for output filename
timestamp=$(date +%Y%m%d_%H%M%S)
output_file="${NAME_PREFIX}_${timestamp}.txt"

# Start transcription with Core Audio Tap dual-capture (system audio +
# microphone, tagged [SYS]/[MIC]). Built into one array and both echoed and
# executed from it, so the printed line can never drift from what actually
# runs (same pattern as win-start-transcription.bat/linux-start-transcription.sh).
CMD=("${PY_CMD}" transcriber.py --live --coreaudio-tap --include-mic --model base --output "${output_file}" --chunk-duration 10 --actual-time "$@")
printf '%q ' "${CMD[@]}"
echo
"${CMD[@]}"

echo
echo "============================================================"
echo "Transcription saved to: ${output_file}"
echo "============================================================"
