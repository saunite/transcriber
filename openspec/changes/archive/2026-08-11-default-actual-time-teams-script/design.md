## Context

`start_teams_transcription.bat` builds a fixed `transcriber.py --live --wasapi --include-mic ...` command and appends whatever extra flags the user passes on the command line (`%REST%`). `--actual-time` already exists and already works correctly (fixed in `fix-actual-time-drift`) — it's simply not part of the script's default invocation, so a user who launches the script without knowing about the flag gets relative timestamps.

## Goals / Non-Goals

**Goals:**
- Running `start_teams_transcription.bat` with no extra flags produces wall-clock timestamps by default.

**Non-Goals:**
- No change to `transcriber.py`'s argument parsing or `--actual-time` semantics.
- No change to `start_transcription.sh` (Linux launcher) — not requested.
- Not adding a way to opt back into relative time from this script; `transcriber.py --live` directly still supports relative time (the default when `--actual-time` isn't passed).

## Decisions

**Add `--actual-time` to the fixed argument list in the script's `python transcriber.py ...` line, before `%REST%`.**
This is the smallest change that fixes the reported problem: the flag is now always present, and `%REST%` still lets a user pass any additional flags (`--silence-timeout`, `--save-audio`, etc.) exactly as before.
- Alternative considered: change `transcriber.py`'s own default for `--actual-time` to `True` repo-wide. Rejected — that would change behavior for every caller (including file-mode and any other launcher), not just the Teams script, which is broader than what was asked and would be a breaking default-behavior change to the general CLI.

## Risks / Trade-offs

- [User wants relative time from this specific script] → Not supported after this change since `--actual-time` is a `store_true` flag with no counter-flag; acceptable because the user explicitly asked for actual time to be the default here, and they can still run `transcriber.py --live ...` directly without the flag for relative time.
