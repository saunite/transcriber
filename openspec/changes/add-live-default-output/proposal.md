## Why

A bare `transcriber.py --live` prints the transcript and saves nothing. It says "Transcriber (not saving a transcript file)" up front, but the user still expected a file, and the transcript of a long session is lost unless `--output` was remembered. File transcription already saves by default (to `<name>_transcript_<stamp>.<format>`), and the launchers and GUI always pass `--output`, so the bare CLI live mode is the one path where forgetting a flag loses work. The `--output` help text also claims "default: transcript.txt in current directory", which was never true.

## What Changes

- **Live capture saves by default.** `--live` without `--output` writes to `transcript_<YYYYMMDD_HHMMSS>.txt` in the current directory, stamped at session start. That's the same naming as the GUI's default, and a new session never overwrites an old one. The first output line names the file, as it already does when `--output` is given.
- **A new `--no-output` flag** keeps today's print-only behavior for quick tests. Combining it with `--output` is rejected.
- **`--output` help text** describes the real defaults for both modes.
- **README:** the live examples and the options list mention the default file and `--no-output`.
- **Unchanged:** `--output <path>`, file transcription, the launchers and the GUI, which all pass `--output` already.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `cli`: adds the requirement that live capture saves a transcript by default, with `--no-output` to opt out.

## Impact

- **Changed**: `transcriber.py` (the flag, a small helper that picks the live output path, and the help text), and `README.md`.
- **New**: `test_live_default_output.py`.
- **Behavior change for CLI users:** a bare `--live` now leaves a file in the current directory. That's the point of the change; `--no-output` restores the old behavior.
