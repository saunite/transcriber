#!/usr/bin/env bash
# Smoke-test a frozen sidecar before anything is packaged
# (openspec/changes/01-add-release-pipeline, design.md Decision 7): it must
# list devices (valid JSON; an empty list is fine on a headless runner) and
# transcribe a generated clip with the bundled model. Needs `python` on PATH
# only to write the clip and parse the JSON -- the sidecar itself needs none.
#
# Usage: bash .github/smoke-test.sh <path-to-frozen-sidecar>
set -euo pipefail

sidecar="$1"
model="src-tauri/resources/model"
work="$(mktemp -d)"

python -c "import sys, wave; w = wave.open(sys.argv[1], 'wb'); w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000); w.writeframes(b'\0\0' * 32000); w.close()" "$work/silence.wav"

"$sidecar" --list-devices-json > "$work/devices.json"
python -c "import json, sys; json.load(open(sys.argv[1]))" "$work/devices.json"

"$sidecar" --file "$work/silence.wav" --model-path "$model" --output "$work/out.txt"
test -f "$work/out.txt"

echo "Smoke test passed: $sidecar"
