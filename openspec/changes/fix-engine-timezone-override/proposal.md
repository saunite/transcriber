## Why

In one session on 2026-09-13 the app named the transcript `transcript_20260913_084328.txt` and showed the start as `08:43:28`, while the engine stamped its own lines `07:43`/`07:44`. An hour apart, in the same session, on the same machine. Parked then; investigated on 2026-09-16 with the user's go-ahead.

**It does not reproduce, and both suspected causes are disproven** (recorded in tasks 1.1 and 1.2):

- The engine honours `TZ`. With `TZ=Pacific/Kiritimati`, the frozen sidecar and the source engine both stamped `2026-09-17 09:47`, matching Python in that zone. The `os.environ.pop("TZ", None)` at import cannot change the zone on Linux at all, because glibc caches it and only re-reads on `tzset()`.
- The page's runtime is not carrying stale daylight-saving rules: the webview reports `America/Mexico_City` with the correct post-2022 offset, agreeing with the system clock to the second, as does the engine.

What remains is a theory that cannot be tested without changing the machine's timezone under a running application: a webview resolves the timezone once and keeps it for the life of the process, so an app left open across a system timezone change or a `tzdata` update would keep the old offset while every freshly spawned engine reads the new one. That is exactly a one-hour gap wherever daylight-saving rules are involved, and exactly a symptom seen once and never again.

So this change stops chasing the defect and makes a recurrence diagnose itself, which is what the investigation lacked.

## What Changes

- **The engine says which timezone its stamps are in.** Its compact summary line names the resolved zone and offset, so the engine log in the app records what the engine believed the local time was. If the gap ever returns, comparing that against the app's own clock answers in one glance what took an investigation this time.
- **A test pins the behaviour that is correct today:** started with a `TZ` its platform can interpret, the engine stamps in that zone. It passes now and guards against a future change quietly reintroducing the suspected defect.
- **No change to how the timezone is resolved.** `os.environ.pop("TZ", None)` stays as it is, including on Windows, where it was added for a Cygwin shell exporting an unparseable `TZ`.
- **Parked instead:** that line is ineffective on Linux, so the Windows behaviour it was written for may never have worked. Checking needs a Windows session, and goes to the backlog.
- **Not in this change:** the stamp format, `--actual-time`'s meaning, the app's own clock, or anything in `src/main.js`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `transcription`, "Format timestamps for output": local time follows the session's configured zone, including a `TZ` the platform's library can interpret, with the existing Windows fallback unchanged.
- `cli`, "Live capture output is compact by default": the summary line also names the timezone the timestamps use.

## Impact

- **`transcriber.py`:** the compact summary line gains the resolved zone and offset.
- **Tests:** a subprocess check that the engine's stamps follow `TZ`, and that the summary line names the zone it used.
- **Docs:** none; the added detail explains itself in the line it appears on.
- **No GUI, shell (Rust) or dependency changes, and no change to timezone resolution.**
