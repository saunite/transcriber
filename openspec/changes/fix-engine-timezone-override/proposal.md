## Why

In one session on 2026-09-13 the app named the transcript `transcript_20260913_084328.txt` and showed the start as `08:43:28`, while the engine stamped its own lines `07:43`/`07:44`. An hour apart, in the same session, on the same machine. Parked then; picked up with the user's go-ahead on 2026-09-16.

The two clocks come from different processes: the file name from the page's JavaScript (`timestampSuffix`, local time), the line stamps from the engine's Python (`_wall_clock_stamp`, local time). Both read "local", so one of them resolved the local zone differently.

**A defect in our own code can produce exactly this.** `transcriber.py` deletes `TZ` from the environment at import, before anything reads the clock:

```python
os.environ.pop("TZ", None)
```

It was added for a Windows-specific bug (`fix-cygwin-tz-override-bug`): a Cygwin shell exports an IANA-style `TZ` that the Windows C runtime can't parse, so the engine fell back to UTC. On Linux and macOS the C library reads IANA zones correctly, so deleting `TZ` there doesn't fix anything, and it makes the engine ignore a zone the rest of the desktop session honours. Whenever an exported `TZ` differs from `/etc/localtime`, the engine and the app disagree, and the transcript's stamps are wrong rather than merely inconsistent.

Whether that is what happened on 2026-09-13 isn't proven: `TZ` is unset on this machine today and the shell, Python and Node agree. This machine is in `America/Mexico_City`, which stopped observing daylight saving in 2022, so software with stale rules reads exactly one hour ahead in September, which is the other candidate, on the app's side. The first task settles it before anything is changed.

## What Changes

- **Reproduce first:** compare, in the built app, what the page's JavaScript, the engine and the system clock each say the local time is, and what each thinks the local zone is, and record it.
- **Then fix what that shows.** The expected fix, if the investigation supports it: the `TZ` deletion becomes Windows-only, so on Linux and macOS the engine honours the session's `TZ` like every other program, and the Cygwin behaviour on Windows is unchanged.
- **The engine and the app agree, or say why:** whatever the cause, the session's stamps and the name of the file they're saved in come from one reading of local time.
- **Not in this change:** the stamp format, `--actual-time`'s meaning, or how the app positions lines on its time axis.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `transcription`, "Format timestamps for output": local time follows the session's configured zone, including an exported `TZ` the platform's C library can read; the Windows fallback for an unparseable `TZ` stays.

## Impact

- **`transcriber.py`:** the `os.environ.pop("TZ", None)` line at import.
- **`src/main.js`:** only if the investigation points at the page instead.
- **Tests:** a subprocess check that the engine's wall-clock stamps follow `TZ` on this platform, which fails today.
- **Docs:** only if behaviour visible to a user changes.
- **No GUI layout, shell (Rust) or dependency changes.**
