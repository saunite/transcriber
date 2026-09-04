## Why

Clicking Stop on a live session shows nothing in the engine log and no confirmation the sidecar actually stopped. Traced during real-hardware testing: `stop_live_session` force-kills the process tree via `taskkill /F /T /PID`, giving the Python process zero chance to log its own shutdown — and `taskkill`'s own result is discarded (`let _ = ...output()`), so even a failed kill (wrong PID, access denied, process already gone) is silently swallowed. The user has no way to know whether the stop actually worked.

## What Changes

- `stop_live_session` (`src-tauri/src/sidecar.rs`) stops discarding `taskkill`'s result and checks it: on success, emits a `sidecar-log` line confirming the session stopped; on failure, emits one reporting the kill did not succeed.
- No change to the kill mechanism itself (`taskkill /F /T /PID` stays) and no change to `transcriber.py` — this surfaces information already being collected, it doesn't add a new stop protocol.

**Deliberately not building**: a graceful, stdin-based stop protocol in `transcriber.py` (letting the Python process detect the stop request itself, run its own shutdown, and log a *real* "stopping" message before exiting). That's the deeper fix the existing code comment already names as the eventual "upgrade path," but it's a genuine behavior change to the CLI's live-capture loop (a stdin-reader thread during blocking audio capture) — bigger, riskier, and not what closes the immediate gap. A synthetic client-side "Stopping…" message was considered and rejected outright: it would say something happened without knowing whether it actually did, which is worse than today's honest silence given the user's own "not sure if it did stop."

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `desktop-gui`: adds one requirement — live-session stop confirmation is genuine (based on the actual kill result), not cosmetic.

## Impact

- **Changed**: `src-tauri/src/sidecar.rs` (`stop_live_session` — check `taskkill`'s `Output` instead of discarding it, emit a real `sidecar-log` line either way).
- **Unaffected**: `transcriber.py`, the kill mechanism itself, `main.js` (already listens for `sidecar-log` and appends to the debug log — no new listener needed, the existing pipe just carries real content now).
