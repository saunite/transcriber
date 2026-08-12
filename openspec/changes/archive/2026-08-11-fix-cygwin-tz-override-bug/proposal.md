## Why

Running `start_teams_transcription.bat` from Cygwin produces wall-clock timestamps in UTC instead of the machine's real local timezone (verified: `[2026-08-12 03:26:33]` in the transcript vs. `22:38 EDT` on the actual clock). Root cause isolated: Cygwin's bash exports an IANA-style `TZ` environment variable (e.g. `America/New_York`), which `cmd.exe`/`python.exe` inherit. Windows' C runtime — which Python's `time`/`datetime` modules rely on for local-time resolution — only understands POSIX-style TZ strings (e.g. `EST5EDT4`), not IANA names. When it can't parse the inherited value, it silently defaults to UTC, even though the Windows OS timezone itself is correctly configured. This affects every `datetime.now()`/`time.strftime()` call in the app: transcript wall-clock timestamps (`--actual-time`) and WAV/output filename timestamps.

## What Changes

- `transcriber.py` clears any inherited `TZ` environment variable at process start, before any other import, so Python's local-time calculation always falls through to the actual Windows-configured timezone rather than a possibly-unparseable inherited value.
- No new CLI flag — this corrects existing "local time" behavior (already the documented meaning of `--actual-time` and of filename timestamps) to work correctly regardless of which shell launched the process (Cygwin, Git Bash, MSYS2, WSL-via-interop, plain cmd/PowerShell, etc.).

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `transcription`: The "Format timestamps for output" requirement's wall-clock behavior gains an explicit scenario: local-time resolution must be correct regardless of an inherited shell environment's `TZ` variable, not just when launched from a plain Windows shell.

## Impact

- `transcriber.py`: add environment normalization as the very first lines of the file, before any other import (a downstream import could otherwise trigger the Windows CRT's broken tzset caching first).
- No change to `--actual-time` semantics, output formats, or any other flag.
- Benefits both live and file-mode wall-clock timestamps, and the `live_audio_*.wav` / output filename timestamps, since all of them go through the same process-wide local-time resolution.
