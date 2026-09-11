## Context

See proposal.md - Why for the traced cause. The pieces involved:

- **Where the lock comes from.** `transcription_engine.py` imports tqdm and wraps file transcription's segment loop in a progress bar. The first bar calls `tqdm.get_lock()`, which lazily builds `TqdmDefaultWriteLock`, and that holds a `multiprocessing.RLock`.
- **Why that starts a process.** Under `forkserver` (the Python 3.14 default on Linux), a multiprocessing semaphore is registered with `multiprocessing.resource_tracker`. The tracker is started with `sys.executable -c …`, and in a onefile build `sys.executable` is the sidecar itself.
- **What already exists.** `multiprocessing.freeze_support()` at the top of `transcriber.py` (`linux-sidecar-build` requirement) makes such a relaunch run the tracker instead of the whole app. The relaunch still has to import from the parent's `_MEI*` directory, and when the parent exits first, it finds that directory gone.

## Goals / Non-Goals

**Goals:**
- No resource-tracker process at all during a sidecar run, and so no exit traceback.

**Non-Goals:**
- Changing the multiprocessing start method, or making PyInstaller onefile relaunches exit-safe in general.
- Switching the sidecar to PyInstaller `--onedir`. That's a standing open question from `remove-installer-packaging`, and it would also remove the race, but it changes packaging and `sidecar.rs`.

## Decisions

### 1. Give tqdm a thread lock at import time

`tqdm.set_lock(threading.RLock())` goes immediately after `from tqdm import tqdm` in `transcription_engine.py`. `transcriber.py` imports the engine before any tqdm use, so it's set before the first progress bar. tqdm's documented `set_lock` API exists for exactly this: it replaces the lock tqdm uses to keep concurrent bars from garbling each other's output. The only bars here are in the one process, so a thread lock gives the same safety.

- **Rejected: `multiprocessing.set_start_method("fork")`.** It changes process semantics for all code, and `fork` with threads is what Python 3.14 moved away from. The live paths are threaded.
- **Rejected: preventing the tracker with private `resource_tracker` internals.** That's fragile across Python versions.
- **Rejected: `--onedir`.** It's a correct but much larger change (see Non-Goals).

## Risks / Trade-offs

- **[Risk]** Another dependency creates a multiprocessing primitive and starts the tracker anyway → task 1.2 checks the frozen binary itself, across file and live runs, not just the venv. If a traceback remains, the log shows which import path still starts it.
- **[Trade-off]** Parallel progress bars from several processes could interleave in a terminal. There are none in this codebase.
