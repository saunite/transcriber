## Context

See proposal.md - Why/What Changes. `start_teams_transcription.bat`'s current structure: parse an optional leading name-prefix argument (anything not starting with `-`), accumulate remaining args verbatim, activate `.venv`, set a few environment variables, generate a timestamped output filename, build the full `transcriber.py` invocation into one `CMD` variable, echo it, then execute that same variable (the compact-live-cli-output change's own recent work, already present in the file's current content).

A separate, pre-existing `linux_start_transcription.sh` (underscore name) already exists at the repo root with a different argument convention (positional numeric device index) and a PulseAudio/PipeWire monitor-source scanning preamble. It is unrelated to this change and untouched by it (see proposal.md).

## Goals / Non-Goals

**Goals:**
- All three launchers share the same argument convention (name-prefix, then pass-through flags) and the same "build once, echo, execute the same value" pattern, so the printed line can never drift from what actually runs.
- macOS gets genuine dual-capture parity with Windows (`--coreaudio-tap --include-mic` vs `--wasapi --include-mic`); Linux is honest about capturing system audio only.

**Non-Goals:**
- Porting `linux_start_transcription.sh`'s PulseAudio monitor-scanning preamble into the new Linux script — that is a distinct, separate script serving a different purpose (general live transcription with manual device selection), and mixing its concerns into this one would make the three launchers structurally diverge instead of converge, which is the opposite of what this change is for.
- Implementing Linux `--include-mic` support (separate change, see proposal.md).

## Decisions

**Bash builds the command as an array, not a string.** The batch file's `set "CMD=...with embedded "quotes"..."` construction exists only because `cmd.exe` has no native array/list type, forcing a fragile nested-quote string trick (explicitly flagged as "reasoned through carefully but genuinely unverified" in `compact-live-cli-output`'s own tasks.md). Bash has a native array type built exactly for this: `CMD=(python3 transcriber.py --live --wasapi ... --output "$output_file" ...)`, printed with `printf '%q ' "${CMD[@]}"` (or a plain `"${CMD[*]}"` for a human-readable echo) and executed with `"${CMD[@]}"`. This is the "reuse the native feature" choice, not a mechanical translation of the batch workaround into bash — it sidesteps the exact class of quoting bug the batch version had to reason carefully around, by construction.

**Argument parsing ports the batch script's exact convention, not `linux_start_transcription.sh`'s.** A leading argument not starting with `-` is the name-prefix (default `meeting`); everything else is passed through verbatim to `transcriber.py`. This matches `win-start-transcription.bat`'s behavior, which is the thing being mirrored — not the older, differently-scoped Linux script.

**Reuse the existing venv-detection idiom.** `linux_start_transcription.sh` already has the right pattern for finding a Python interpreter (prefer `.venv/bin/python`, fall back to `python3`) — both new scripts reuse it verbatim rather than reinventing it, and it needs no platform variation between Linux and macOS.

**macOS gets no PulseAudio-equivalent preamble.** Core Audio Tap capture needs no device-scanning step (per `add-macos-capture`: "No additional setup required — grant the audio-capture permission when macOS prompts on first use"), so `mac-start-transcription.sh`'s structure is the plainest of the three: parse args, build `CMD` with `--coreaudio-tap --include-mic`, echo, execute.

**The Windows script's ffmpeg `PATH` addition and hardcoded personal WinGet path are preserved as-is in the rename.** This is dead weight since `drop-ffmpeg-dependency` removed the actual ffmpeg subprocess calls, but the rename is defined as behavior-preserving, and removing it is an unrelated cleanup outside this change's scope — noted here so it isn't mistaken for an oversight.

## Risks / Trade-offs

- [Two launchers now claim to do "the same thing" as Windows, but Linux is deliberately weaker (no mic)] → Mitigated by the spec's own explicit disclosure requirement and the script printing it, rather than silent behavioral drift between platforms.
- [The still-open `compact-live-cli-output` change's pending delta spec references the pre-rename filename] → Handled as an explicit task (edit that file's text), not left to rot until that change eventually archives with stale content.
