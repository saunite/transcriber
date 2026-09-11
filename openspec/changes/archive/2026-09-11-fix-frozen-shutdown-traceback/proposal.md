## Why

After every successful run, including file transcription and live capture, the frozen sidecar prints a traceback while exiting:

```
File "multiprocessing/reduction.py", line 16, in <module> … ModuleNotFoundError: No module named '_socket'
[PYI-…:ERROR] Failed to execute script 'pyi_rth_multiprocessing' due to unhandled exception!
```

The missing module varies (`_socket`, `array`, `_blake2`). Exit code and output are unaffected, but the GUI shows it in the engine log, where every run looks like a crash. It also violates `linux-sidecar-build`'s "Frozen sidecar survives multiprocessing's resource-tracker relaunch" requirement, whose scenario says no resource-tracker traceback appears across repeated runs. It was first recorded under `01-add-release-pipeline` task 1.2, where it predated that change: the Sep 4 sidecar printed the same thing.

**Root cause, confirmed in the project venv:**
- Python 3.14 made `forkserver` the default multiprocessing start method on Linux.
- tqdm's default write lock is a `multiprocessing.RLock`, and creating it now starts multiprocessing's resource tracker: one progress bar is enough, and the tracker's pid goes from `None` to a live process.
- In a PyInstaller onefile build, that tracker is a relaunch of the sidecar binary itself. The parent finishes and deletes its extraction directory while the tracker is still importing its modules, hence the varying `ModuleNotFoundError`.
- With `tqdm.set_lock(threading.RLock())` in place first, no tracker is ever started.

## What Changes

- **`transcription_engine.py` gives tqdm a thread lock,** `tqdm.set_lock(threading.RLock())`, right after importing tqdm and before any progress bar exists. The engine's progress bars are single-process, so tqdm never needed a cross-process lock here. No resource tracker starts, so there's no relaunch to race the exit.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
(none — this restores behavior `linux-sidecar-build` already requires; no requirement text changes)

This change sets `skip_specs: true` in `.openspec.yaml`.

## Impact

- **Changed**: `transcription_engine.py` (one import and one call).
- **Unchanged**: `multiprocessing.freeze_support()` in `transcriber.py`, which still handles any other relaunch; the multiprocessing start method; and progress-bar output.
- **Platforms**: the change is platform-agnostic code. Linux is where the traceback is seen and verified. Windows uses `spawn` and has no resource tracker; the POSIX tracker on macOS is avoided the same way.
