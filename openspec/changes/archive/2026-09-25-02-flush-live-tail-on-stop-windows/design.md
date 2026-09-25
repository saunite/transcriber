## Context

See `proposal.md` for why.
- **Windows Stop today:** `stop_live_session` takes the `CommandChild` and calls `taskkill_tree(pid)`, which runs `taskkill /F /T /PID`. The frozen engine is a PyInstaller onefile. On Windows its bootloader re-executes into a worker process that holds the audio device, which is why `/T` is used.
- **How the app sees exits:** its event loop already observes `CommandEvent::Terminated` for each run (`sidecar.rs`, around line 685).
- **The engine's stop path:** `_print_or_stop` already stops a session from a worker thread with `_thread.interrupt_main()`, which runs the SIGINT handler, so the normal Ctrl+C shutdown follows.
- **What exists to reuse:** `tauri-plugin-shell`'s `CommandChild::write` sends bytes to the child's standard input. Unix already has a 15 s `STOP_GRACE`.

## Goals / Non-Goals

**Goals:** the Windows app's Stop lets the engine finish (01's final chunk and a closed transcript), with the forced kill kept as a bounded fallback.

**Non-Goals:** changing the Unix stop path; a general command protocol over stdin.

## Decisions

**1. Stop over standard input, opted into by a hidden flag.**
Windows has no SIGINT a GUI app can send to a console-less child. `GenerateConsoleCtrlEvent` needs a shared console, and the sidecar runs with none. Standard input is already a pipe from the app. With `--stop-on-stdin`, the engine starts a daemon thread that reads lines. On `stop` or EOF it calls `_thread.interrupt_main()` once, unless a stop is already under way. EOF counts as a stop because the app closing its end means nobody is listening, the same reasoning as `_print_or_stop`'s broken pipe.
- *Always on:* the launchers and a terminal user run the engine with a console stdin, where a reader thread would compete for keyboard input. It stays opt-in, and hidden (`argparse.SUPPRESS`), because it's an app protocol, not a user feature.
- *Also use it on Linux and macOS:* SIGINT works and is tested there. No reason to change it.

**2. The frozen sidecar: verify the worker receives standard input.**
PyInstaller's onefile bootloader on Windows starts the worker with inherited standard handles, so a write to the bootloader's stdin pipe should reach the worker. This is the one assumption that can only be checked on Windows. If it fails, the fallback is for the engine to create a named event per run (`--stop-event <name>`) that the app signals. That would come back as a design update.

**3. Wait for the engine's exit through the existing `Terminated` event, with the same 15 s grace.**
`stop_live_session` on Windows writes `stop\n`, then waits for the run's `Terminated` event, signalled from the event loop through a one-shot channel or flag, or until 15 s pass. Only then does it call `taskkill_tree`. The existing "confirmed genuinely" reporting stays: a graceful exit reports "Capture engine stopped." and a fallback kill reports taskkill's result.

## Risks / Trade-offs

- [The worker doesn't get stdin through the bootloader] → Decision 2's check and its fallback.
- [A hung engine] → The 15 s grace, then `taskkill /F /T`, as today.
- [App quit, not Stop] → The quit path (`kill all engines on exit`) keeps its forced kill. At quit, the app isn't around to show the result anyway. Closing stdin as the app exits also stops the engine gracefully, which is a bonus.
