## Why

The README documents the CLI surface and launchers, but it has drifted from the actual application: it never tells Linux users to use `requirements-linux.txt`, it omits the `start_transcription.sh` live launcher, it documents neither the `--save-audio` stereo-merge output nor the `transcribe_file.bat` / `merge_and_transcribe.bat` launchers, and its options list misses `--setup-help`. (Note: the README's emoji glyphs rendered as `?`/`??` under PowerShell's cp1252 console — the file itself is clean UTF-8 with no replacement/U+FFFD characters, so no byte-level repair is needed.)

## What Changes

- Add a Linux install note pointing to `requirements-linux.txt` (avoids pulling the Windows-only `pyaudiowpatch` on Linux), with ffmpeg install hints for Debian/Ubuntu and RHEL/Fedora.
- Add a Linux live-capture section documenting `start_transcription.sh`.
- Document `--save-audio` behavior: in WASAPI mode it writes `_sys.wav` and `_mic.wav` and merges them into a stereo `_merged.wav` (merge uses ffmpeg).
- Add a "Launchers" section documenting `transcribe_file.bat` and `merge_and_transcribe.bat`.
- Add `--setup-help` to the "Complete Options" list.

## Capabilities

### New Capabilities
- `documentation`: The project's README must accurately reflect the supported commands, flags, platform setup, and launchers offered by the tool.

### Modified Capabilities

None. (No application behavior or SHALL requirements are changing; only README content.)

## Impact

- Docs: `README.md` only. No code, dependencies, or runtime behavior change.
- Specs: one new `documentation` capability (no existing spec covers documentation accuracy).
