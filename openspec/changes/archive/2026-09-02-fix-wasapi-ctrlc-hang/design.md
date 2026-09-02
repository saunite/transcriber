## Context

`WASAPICapture.capture_stream` (`wasapi_capture.py`) runs its audio-read loop on the **main thread** — the only thread Python delivers `SIGINT` to. The loop calls `stream.read()` (a blocking `pyaudiowpatch`/PortAudio native call) directly. Python only checks for a pending signal when control returns to the interpreter between bytecode instructions; while blocked inside `stream.read()`, no bytecode runs. Under normal conditions the read returns every ~21ms and this is unnoticeable. After a long WASAPI loopback session, the shared-mode audio engine can stall (default-device change, sleep/wake, Bluetooth reconnect) and `stream.read()` simply never returns — so the pending Ctrl+C is never processed and the process must be killed externally.

`transcriber.py` already solves the equivalent problem for microphone capture and for transcription itself: `mic_stream` uses `sounddevice.InputStream`'s callback (driven by its own thread), and `sys`/`mic` audio are drained by dedicated background threads via `queue.Queue`. The main WASAPI capture loop is the one place still doing a direct blocking read on the interruptible thread.

## Goals / Non-Goals

**Goals:**
- Ctrl+C always terminates a WASAPI live-capture session promptly, even if the underlying `stream.read()` has stalled.
- No change to `WASAPICapture.capture_stream`'s public signature or callback contract — `transcriber.py` keeps working unmodified.
- No new dependencies.

**Non-Goals:**
- Fixing or detecting *why* WASAPI stalls (device/format change, Bluetooth reconnect). We only guarantee shutdown stays responsive when it does.
- Changing the non-WASAPI (`sounddevice`) capture path — its main loop is already a `time.sleep(0.01)` poll and isn't subject to this failure mode.
- Adding a stall watchdog that proactively restarts the stream mid-session (out of scope; Ctrl+C responsiveness is the ask).

## Decisions

**Move the blocking read onto a background thread; main thread becomes a queue consumer.**

This is the exact pattern already used twice elsewhere in this codebase (mic capture, sys/mic drain workers) — reusing it here rather than inventing a new interruption mechanism. Concretely, inside `capture_stream`:
- A background `threading.Thread` runs the existing `while ...: stream.read(...); callback? no — push to queue` loop and puts raw chunks onto a `queue.Queue()`.
- The main thread loops on `queue.get(timeout=0.1)` and invokes the user `callback` itself (preserves today's behavior of the callback running synchronously off the return of `capture_stream` for a caller's expectations, and keeps `capture_stream` a normal blocking call from the caller's point of view).
- `queue.get(timeout=...)` is a stdlib-blocking call that *does* release control to the interpreter between timeouts, so it checks pending signals every 0.1s — always interruptible.
- On `KeyboardInterrupt` (or normal stop), the main thread calls `stream.stop_stream()` / `stream.close()` itself. PortAudio's stream close is documented safe to call from a different thread than the one blocked in `read()`, and forces that blocked call to return (with an error, which the background thread's read loop already treats as a reason to exit on `IOError`, mirroring the existing overflow-handling `except IOError` branch). The background thread is then joined with a short timeout before `capture_stream` returns.

Alternative considered: a stall watchdog thread that calls `stream.close()` only after detecting no data for N seconds, leaving the read loop on the main thread otherwise unchanged. Rejected — it's strictly more moving parts (a timer thread *and* a hand-rolled staleness threshold to tune) for a narrower win: it still leaves the main thread's read as the one Ctrl+C-blocking call whenever the watchdog itself hasn't fired yet, so a slow-but-not-yet-stalled read still delays shutdown. Moving the read off the main thread unconditionally is smaller and strictly fixes Ctrl+C responsiveness, not just the stall case.

Alternative considered: catch `KeyboardInterrupt` and call `stream.abort()` from a `signal.signal` handler. Rejected — signal handlers only run on the main thread and only when it returns to the interpreter, which is precisely what's broken; a handler can't run any sooner than the current blocking call returns.

## Risks / Trade-offs

- [Background thread outlives `capture_stream()` if `stream.close()` doesn't unblock a truly wedged driver] → Thread is created as a daemon and joined with a bounded timeout (mirrors the existing `sys_thread.join(timeout=60)` pattern in `transcriber.py`); `capture_stream` returns either way and the process is free to exit.
- [One extra queue hop adds latency between capture and callback] → Bounded by the `queue.get` timeout (0.1s), negligible next to the existing 10-30s chunk-duration buffering downstream.
- [Behavior change: `callback` now always runs on the main thread instead of directly inside the read loop] → No observable difference to existing callers; `capture_stream`'s documented contract is just "callback receives chunks," not which thread runs it.

## Migration Plan

Single-file, backward-compatible change to `wasapi_capture.py`. No config, data, or API migration. Manual verification: run a WASAPI live session, then Ctrl+C — should exit promptly. Simulate a stall (e.g. disconnect/reconnect the loopback output device mid-session) and confirm Ctrl+C still exits promptly rather than requiring Task Manager.

## Open Questions

None.
