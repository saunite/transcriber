#!/usr/bin/env bash
# Teams Meeting Transcription Launcher (Linux)
# This script starts live transcription with dual-capture (system audio +
# microphone, tagged [SYS]/[MIC]) for complete Teams meeting coverage.
# Mirrors win-start-transcription.bat's argument convention and defaults.
#
# Usage: ./linux-start-transcription.sh [name-prefix] [transcriber flags...]
#   name-prefix:  prefix for the output filename (default: meeting)
#   Timestamps default to wall-clock time (--actual-time is always passed).
#   flags:        passed through to transcriber.py, e.g.
#                   --silence-timeout 0      never auto-stop on silence
#                   --language en            force a language
#   Example: ./linux-start-transcription.sh sprint-review --silence-timeout 0
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

# Start transcription with Linux's default dual-source capture (system audio
# + microphone, tagged [SYS]/[MIC] -- no --wasapi/--coreaudio-tap needed,
# --include-mic alone selects it). Built into one array and both echoed and
# executed from it, so the printed line can never drift from what actually
# runs (same pattern as win-start-transcription.bat, using bash's native
# array type instead of cmd.exe's nested-quote string workaround).
CMD=("${PY_CMD}" transcriber.py --live --include-mic --model base --output "${output_file}" --chunk-duration 10 --actual-time "$@")
printf '%q ' "${CMD[@]}"
echo
"${CMD[@]}"

echo
echo "============================================================"
echo "Transcription saved to: ${output_file}"
echo "============================================================"
