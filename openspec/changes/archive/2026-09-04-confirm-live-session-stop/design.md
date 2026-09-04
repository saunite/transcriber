## Context

See proposal.md - Why. `stop_live_session` already runs `taskkill /F /T /PID <pid>` and captures its `Output` via `.output()` — the fix is entirely about what happens to that `Output`, currently discarded with `let _ = ...`. No new mechanism, no new process communication.

## Goals / Non-Goals

**Goals:**
- Every Stop click produces a real, truthful log entry — success or failure, never silence, never a guess.
- Zero change to the underlying kill mechanism or its reliability.

**Non-Goals:**
- A graceful stdin-based stop protocol in `transcriber.py` (the existing code comment's own named "upgrade path") — a real behavior change to the live-capture loop, out of scope for closing an information gap.
- Any change to how sidecar crash detection works (`was_active` / `sidecar-crashed` in `spawn_sidecar_events`) — unrelated code path, already correctly suppressed for deliberate stops (verified during exploration: `session_active` is set `false` synchronously before `taskkill` runs, so the crash-detection branch never fires for a user-initiated stop).

## Decisions

**Emit via the existing `sidecar-log` event, not a new one.** `main.js` already listens for `sidecar-log` and appends it to the same debug/engine log panel the user already checks — reusing it means no new frontend listener, no new UI surface, and the confirmation shows up exactly where the user already looked for it (per the "not sure if it did stop" report, in that very panel).

**Check `taskkill`'s exit status, not its stdout text.** `taskkill` returns 0 on success; nonzero (128 = process not found, others for access-denied etc.) otherwise — a real, documented Windows contract, not string-matching English output that could vary by locale/version.

**Rejected: a synthetic client-side "Stopping…"/"Stopped" message with no basis in real process state.** Considered directly (see proposal.md) and rejected — it would answer "not sure if it did stop" with a guess dressed up as a fact, which is worse than admitting uncertainty. Everything this change emits is grounded in `taskkill`'s actual, checked result.

## Risks / Trade-offs

- [`taskkill` succeeding doesn't guarantee `transcriber.py` released the audio device cleanly — only that the OS reports the process gone] → Accepted; that's the same confidence level `taskkill /F /T` has always provided, this change surfaces it rather than changing it.
- [Locale/Windows-version differences in `taskkill`'s own error text, if ever surfaced to the user] → Mitigated by design: only the exit status is checked, never `taskkill`'s own stdout/stderr text.
