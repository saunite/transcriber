## Context

Confirmed empirically on the target Windows machine:
- System timezone is Eastern (verified via `Get-TimeZone`), and Python's `datetime.now()` returns correct Eastern time when launched from a plain shell with no `TZ` env var set.
- Setting `$env:TZ = "America/New_York"` (the IANA-style value Cygwin's bash exports) before launching `python.exe` causes `datetime.now()`/`time.strftime()` to return UTC instead — the Windows CRT can't parse an IANA zone name and silently falls back to UTC.
- The break happens on the *first* call to a local-time function (`datetime.now()`, `time.localtime()`, `time.strftime()` with no args) after process start; the CRT appears to cache tzset state at that first call. Deleting `TZ` from `os.environ` *before* that first call fixes it for the rest of the process; deleting it *after* the first (broken) call does not un-break already-cached state.
- Verified the fix survives the real import chain (`audio_extractor`, `audio_capture`, `transcription_engine`, `time`) when the `TZ` pop happens before those imports.

## Goals / Non-Goals

**Goals:**
- `transcriber.py` produces correct Windows-local timestamps regardless of which shell launched it (Cygwin, Git Bash, MSYS2, or a shell with some other stray `TZ` export), without requiring the user to unset anything themselves.

**Non-Goals:**
- Not adding a `--timezone` flag to pick an explicit zone — nothing so far indicates a user actually wants a different real timezone than their OS's configured one; this is purely fixing local-time resolution to match what the OS is already configured for. Can revisit if that need shows up.
- Not attempting to support the inherited `TZ` value as an intentional override (e.g., "I want the app to think it's in a different zone") — out of scope; the fix's job is to make local time correct, not to add zone-selection.
- Not touching `start_transcription.sh` (Linux) — Linux's own `TZ` handling (via glibc/tzdata) correctly parses IANA names, so this bug is Windows/CRT-specific and doesn't reproduce there.

## Decisions

**Clear `TZ` from `os.environ` as the very first lines of `transcriber.py`, before any other import.**
This must run before the first local-time call *and* before any import that could trigger one indirectly (e.g., a library logging a timestamped startup message). Placing it before even `import sys`/`argparse` guarantees no downstream import can win the race.
- Alternative considered: call `time.tzset()` after clearing the env var to force a re-read. Rejected — `time.tzset()` doesn't exist on Windows (Unix-only in CPython), so it would crash; simply never letting the bad value be read in the first place is both simpler and portable (a no-op pop on Linux, where this bug doesn't occur anyway).
- Alternative considered: only pop `TZ` if it looks IANA-style (contains `/`) rather than unconditionally. Rejected as unnecessary complexity — there's no legitimate reason for this app to want a `TZ` override; unconditionally clearing it is simpler and always correct for "use the OS's real local time," which is what every existing timestamp feature already claims to do.

**No new CLI flag or config option.**
This is a correctness fix to existing "local time" behavior (`--actual-time`, WAV/output filenames), not a new capability.

## Risks / Trade-offs

- [A user who deliberately sets `TZ` to make Python think it's in a different zone loses that ability] → Not a real use case today (no flag or docs ever suggested setting `TZ` yourself); if it's ever needed, it should be a proper `--timezone` flag with explicit IANA→Windows zone conversion, not reliance on an environment variable the Windows CRT can't parse correctly anyway.
- [Clearing `TZ` unconditionally could mask a legitimate Linux use of `TZ`] → Linux's local-time resolution correctly honors IANA `TZ` values already; popping it removes an explicit override there too, falling back to the system's `/etc/localtime` default, which is the same "OS-configured local time" behavior this fix targets on Windows. Acceptable since no launcher or doc sets `TZ` intentionally today.
