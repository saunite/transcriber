## 1. Fix and verify

- [x] 1.1 Add `import threading` and `tqdm.set_lock(threading.RLock())` right after `from tqdm import tqdm` in `transcription_engine.py` (design.md Decision 1). Verify in the venv: after `import transcription_engine` and one tqdm bar, `multiprocessing.resource_tracker._resource_tracker._pid` is still `None` (it was a live pid before). Also verify the existing `test_*.py` files still pass.
- [x] 1.2 Re-freeze the Linux sidecar and run `--file` three times on a short clip, plus the no-decodable-audio failure path (`binary.mp3`). Verify that no run's combined output contains `Traceback`, `pyi_rth_multiprocessing`, or `ModuleNotFoundError` (they did before), and that the exit codes are 0, 0, 0, and 1.

  **Verified 2026-09-11** with the re-frozen sidecar (PyInstaller 6.22.2, Python 3.14.7): three `--file` runs on a 2 s clip exited 0, 0, 0, and `binary.mp3` exited 1. Each run's combined output had **0** lines matching `Traceback|pyi_rth_multiprocessing|ModuleNotFoundError`, where every run before the fix printed that traceback. The sidecar is re-staged in `src-tauri/binaries/` for 1.3.
- [x] 1.3 In the GUI (`cargo tauri dev` with the re-staged sidecar), transcribe a file and run a short live session. Verify that the engine log ends cleanly, with no traceback after completion or after stopping.

  **Verified by the user 2026-09-11 (`cargo tauri dev`, Fedora/KDE):** a live session ended with `── stop requested ──` and no traceback, and an 84 s video file transcription (23 segments) ended with its summary and no traceback.
