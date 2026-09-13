## Context

See proposal.md - Why. The constraints that shape the approach:

- `SidecarManager` holds `child: Option<CommandChild>` and a `session_active: bool`. `start_live_session` stores the child; `stop_live_session` takes it and kills it; `start_file_transcription` spawns with `let (rx, _child) = …`, dropping the handle entirely.
- `CommandChild` (tauri-plugin-shell) exposes `pid()` and `kill()`. `kill()` signals that one PID. There is no documented `pre_exec`/`setsid` hook on its `Command` builder, so putting the child in its own process group at spawn time may not be reachable without replacing the spawn mechanism.
- PyInstaller `--onefile` re-executes into a worker: the launched binary is the bootloader, and a second process does the real work and owns the audio device. Measured here: bootloader `1115116` → worker `1116659`; killing the bootloader leaves the worker running, reparented.
- `transcriber.py` installs a `SIGINT` handler (`_make_signal_handler`) that flushes and closes the transcript. A `SIGKILL` mid-write can truncate the last line. The existing code comment names a stdin-based stop protocol as the eventual upgrade.
- The Windows branch already solves the tree problem with `taskkill /F /T` plus `CREATE_NO_WINDOW`, and is verified on real hardware. It is not in scope.

## Goals / Non-Goals

**Goals:**
- A stop that leaves no process holding the microphone or system audio.
- A stop result that reflects reality, including reporting failure when something survives.
- No second engine running alongside a live one.

**Non-Goals:**
- Changing the Windows path, which already terminates the tree.
- A stdin-based stop protocol in the engine. It is the cleaner long-term design, but it changes the CLI's interface and is a larger change than this defect warrants.
- Reworking how audio is captured. Nothing about capture-while-running is wrong.
- Recovering transcript content from sessions already orphaned by the old behaviour.

## Decisions

### 1. Signal the worker, not just the launched process

Stopping resolves the launched PID's descendants and signals them, mirroring what the Windows branch does with `taskkill /T`.

Discovering the tree: read `/proc/<pid>/task/<tid>/children` on Linux, falling back to `pgrep -P <pid>` where that is unavailable (macOS has no `/proc`, and `pgrep -P` exists on both). A process group would be tidier — one `killpg` and no enumeration race — but that requires `setsid` at spawn time, which tauri-plugin-shell does not appear to expose; if it turns out to be reachable, prefer it and record the change here.

**Rejected: keep killing only the launched PID.** That is the current behaviour and the defect.

**Rejected: `pkill -f transcriber-sidecar`.** It would kill *any* sidecar, including a concurrent file transcription or another instance of the app, and matches on a command line the user could plausibly be running by hand. Too blunt for a stop button.

### 2. SIGINT first, verify, then escalate

Send `SIGINT` to the worker (and the bootloader) so the engine's handler flushes and closes the transcript, wait a bounded time for exit, and escalate to `SIGKILL` for anything still alive. This directly serves the delta's "Graceful stop preserves the transcript" scenario, and it is why the stop is not simply a harder kill.

The wait must be bounded and short enough not to freeze the UI (the command is async, so the wait does not block the main thread, but the user is watching a button). A few seconds is the intended order of magnitude; the exact bound belongs in implementation, tuned so a normal graceful exit is never cut short.

**Rejected: SIGKILL straight away.** Simpler, and it would fix the orphan, but it re-introduces the truncated-transcript risk the current comment warns about and discards a graceful path the engine already implements.

### 3. Report success only when nothing survives

After escalation, re-check for survivors. Report success only if none remain; otherwise log that the stop did not succeed and that capture may still be active. This is what the existing requirement asked for all along — the current code reports success because `kill()` returned `Ok`, which is true of the call and false of the outcome.

### 4. Refuse a file transcription while a live engine is alive

If `session_active` is set or a tracked child is still running, `start_file_transcription` returns an error the UI surfaces, rather than spawning a second engine.

**Rejected: silently stop the live session and proceed.** Dropping a file onto the window would then end a recording in progress with no confirmation — a worse surprise than being told to stop first.

Also: track the file run's child instead of discarding it (`let (rx, _child) = …`), so app quit and future stop logic can terminate it. Without that handle a file run is unstoppable by design.

### 5. The indicators show capture state, in this change

The delta's "Capture indicators reflect real state" scenario is part of this change rather than a follow-up, because it is the symptom the user actually reported and because leaving it would mean shipping a spec scenario with no implementation. `pen-sys` currently has no writer at all and `pen-mic` mirrors the include-mic checkbox; both need driving from session state, with the checkbox continuing to express *intent* for the next session (a distinct meaning that the UI must not conflate with activity).

### 6. macOS: same code path, explicitly unverified

The Unix branch covers macOS, and `pgrep -P` works there. There is no Mac to test on, so macOS is implemented-but-unverified and must be recorded that way — the same treatment this project already gives macOS packaging.

## Risks / Trade-offs

- **[Risk]** Enumerating children races a process that forks again between listing and signalling. → Signal, wait, re-check, escalate; the re-check in Decision 3 is what closes the gap. A process group would remove the race and should be preferred if reachable.
- **[Risk]** The graceful wait makes stop feel slower. → Bounded and small; escalation guarantees termination regardless.
- **[Risk]** `SIGINT` to the bootloader could kill it before the worker flushes, orphaning the worker again. → Signal the worker first, then the bootloader, and rely on the survivor re-check.
- **[Risk]** A hostile or hung worker ignores both signals. → Then the stop is honestly reported as failed, which is strictly better than today's false success.
- **[Trade-off]** Refusing a file run during a live session is a small workflow annoyance, accepted because the alternative silently ends a recording.
- **[Trade-off]** No stdin stop protocol means signals remain the mechanism, so this is a robust fix rather than an elegant one. Recorded as the upgrade path, unchanged from the existing comment.
