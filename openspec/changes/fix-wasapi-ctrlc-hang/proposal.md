## Why

After a long WASAPI live-capture session, Ctrl+C stops working: the process must be killed via Task Manager. Root cause is `WASAPICapture.capture_stream` blocking on `stream.read()` from the main thread — Python only checks for a pending SIGINT when control returns to the interpreter, and a stalled WASAPI read (device/format change, sleep/wake, Bluetooth reconnect) never returns, so the interrupt is queued forever and never delivered.

## What Changes

- Move the blocking WASAPI `stream.read()` loop off the main thread and onto a background thread, mirroring the queue/thread pattern already used for mic capture and the sys/mic drain workers in `transcriber.py`.
- The main thread becomes a simple, always-interruptible wait loop that pulls chunks off a queue and invokes the existing callback — same external behavior, same `capture_stream(callback, device_index)` signature.
- On shutdown (Ctrl+C or normal stop), close the PortAudio stream from the main thread, which forces any stalled background read to unblock and return, then join the background thread briefly.
- No change to the simple (non-WASAPI) `sounddevice`-based capture path — its main loop is already a lightweight `sleep()` poll and is not affected by this failure mode.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `audio-capture`: the "Capture stops on user interrupt" requirement is strengthened to guarantee shutdown even when the underlying WASAPI read stalls indefinitely, not just under normal operation.

## Impact

- `wasapi_capture.py`: `WASAPICapture.capture_stream` reworked internally (thread + `queue.Queue`); public signature and callback contract unchanged.
- `transcriber.py`: no changes required — it calls `capture.capture_stream(...)` the same way.
- No new dependencies (uses `threading`/`queue` from stdlib, already used elsewhere in the codebase).
