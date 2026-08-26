## 1. Rework WASAPICapture.capture_stream

- [x] 1.1 Add a background `threading.Thread` that runs the existing `stream.read()` loop and pushes raw chunks onto a `queue.Queue()` instead of calling `callback` directly.
- [x] 1.2 Replace the main-thread loop with a `queue.get(timeout=0.1)` consumer that invokes `callback` on each chunk, so the main thread is always interruptible.
- [x] 1.3 On `KeyboardInterrupt` (or normal loop exit), call `stream.stop_stream()` / `stream.close()` from the main thread to force-unblock the background thread's read, then join the background thread with a short bounded timeout.
- [x] 1.4 Keep `capture_stream`'s public signature and callback contract unchanged so `transcriber.py` requires no edits.

## 2. Verify

- [x] 2.1 Run a WASAPI live session and confirm Ctrl+C exits promptly under normal conditions. (Verified via `test_wasapi_capture.py`, which exercises normal reads before shutdown; no physical WASAPI device available in this environment for a live manual run.)
- [x] 2.2 Simulate a stalled read (e.g. change/disconnect the default output device mid-session) and confirm Ctrl+C still exits promptly instead of requiring Task Manager. (Verified via `test_wasapi_capture.py`, which mocks `pyaudiowpatch` with a read that blocks indefinitely until the stream is closed, and asserts `capture_stream()` returns in well under 2s once shutdown is requested.)
- [x] 2.3 Confirm `--include-mic` and `--save-audio` still work end-to-end (unaffected paths) after the change. (Verified by inspection: `capture_stream`'s signature and callback contract are unchanged, and `transcriber.py` was not modified. Not run against real hardware/a live Teams meeting in this environment -- recommend one real-world smoke test before relying on this.)
