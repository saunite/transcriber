## Context

`README.md` is the sole project documentation and lives at the repo root. Its "Real-time Audio Capture" section is Windows-centric and several launchers and flags are undocumented or misdocumented relative to the actual CLI (`python transcriber.py --help`) and the bat/sh launchers in the repo root. The OpenSpec schema used by this repo (spec-driven) requires every change to carry at least one spec delta; since no existing capability spec governs documentation accuracy, this change introduces a `documentation` capability to make the rule explicit.

## Goals / Non-Goals

**Goals:**
- Make README match actual behavior: platforms, requirements files, launchers, flags, and the `--save-audio` merge.
- Establish a standing `documentation` requirement (README must mirror supported behavior).

**Non-Goals:**
- No code, dependency, or runtime changes.
- No rewording of already-accurate sections for style alone.
- No generation of separate docs beyond README.

## Decisions

1. **New `documentation` capability rather than editing an existing spec.** README accuracy isn't covered by `cli`, `audio-capture`, etc. — none assert "docs must mirror behavior." A minimal standing requirement in a new spec is the honest, schema-satisfying delta. Alternative considered: skip the delta (no capability changes) — rejected because the spec-driven schema rejects changes with zero deltas.

2. **Linux install split by requirements file.** Document `pip install -r requirements-linux.txt` for Linux. The single `requirements.txt` includes `pyaudiowpatch` (Windows WASAPI); `requirements-linux.txt` omits it. Users on Linux should use the Linux file. (Alternative: a single combined file filtered by markers — rejected as over-engineering; the two-file convention already exists.)

3. **Document launchers as a group.** `transcribe_file.bat` and `merge_and_transcribe.bat` are one-liner wrappers over `transcriber.py`; they get one "Launchers" section. `start_teams_transcription.bat` is already covered.

4. **Document `--save-audio` via the audio-capture "Save captured audio to WAV" requirement**, which the delta already states merges via ffmpeg; README mirrors that text without re-specifying the ffmpeg mechanism.

## Risks / Trade-offs

- README can drift again → the new `documentation` capability makes accuracy a standing requirement, so future capability changes should update README.
- The `documentation` spec is a meta-capability → acceptable: it records a real project rule and satisfies the schema.

## Migration Plan

No migration: README is regenerated in place. Old content is replaced for the affected sections only.

## Open Questions

- Whether to also host README on a docs site — out of scope; keep single README.
