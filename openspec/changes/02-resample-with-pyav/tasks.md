## 1. Resampling

- [x] 1.1 Add `_resample(resampler, block, rate, flush=False)` to `transcriber.py` (design.md Decision 2), wrapping a mono float32 block in an `av.AudioFrame` and returning the concatenated output. Add `test_resample.py` at the repo root with these cases:
  - 3 s of a 1 kHz tone at 48000 Hz and at 44100 Hz, fed in 1,024-frame blocks through one resampler: the dominant frequency of the output is within 1 Hz of 1,000, and the total length plus the flush equals `len * 16000 / rate`;
  - a 3-frame block returns an empty array without raising;
  - a single 10-second chunk with `flush=True` returns exactly `len * 16000 / rate` samples.
  Verify the test passes.

  **Done 2026-09-14.** Added `_new_resampler()` (`av.AudioResampler(format="flt", layout="mono", rate=16000)`) alongside `_resample`. An empty block with `flush=True` just drains, which the streaming test uses to flush. All three cases pass: exact lengths and a 1,000 Hz peak at 48000 and 44100, an empty result for 3 frames, and 160,000 samples for the flushed 10-second chunk. Labelling every frame 48000 Hz makes the 44.1 kHz case fail.
- [x] 1.2 Replace `_run_dual_capture`'s scipy transform and its zero-length guard with a per-worker resampler created on the first block (Decision 1). Verify `python test_dual_capture.py` passes, including its 44.1 kHz sample-count and 3-frame cases. If a count assertion assumed scipy's exact per-block lengths, change it to a whole-run total within the 16-sample flush, and record that in this task.

  **Done 2026-09-14.** `_to_target_rate` creates one `_new_resampler()` per worker on the first block, only when the source isn't already 16 kHz. The zero-length guard is gone. **The count assertion did need changing, as anticipated:** the stateful resampler's warm-up moved the first chunk boundary to 17585. Case 1 now wraps `_resample` and checks the system audio's whole-run total is within 16 samples of 19200. Passes 3 runs in a row; forcing 48000 for system audio gives 17624 and fails.
- [x] 1.3 Replace `_process_audio_chunk`'s `signal.resample` with a fresh flushed resampler (Decision 2). Verify with a case added to `test_resample.py`: a 44.1 kHz chunk through `_process_audio_chunk`, with a fake engine recording its input, reaches the engine as `round(len * 16000 / 44100)` float32 samples.

  **Done 2026-09-14.** `_process_audio_chunk` uses `_resample(_new_resampler(), audio_data, sample_rate, flush=True)`. The new case passes a float64 44.1 kHz chunk and gets 160000 float32 samples at the engine. Without `flush=True` the case fails on length.
- [x] 1.4 Remove every `from scipy import signal` from `transcriber.py`. Verify that `git grep -n scipy -- '*.py'` returns only the `build_sidecar.py` message edited in 2.2, and that `python -c "import transcriber"` succeeds.

  **Done 2026-09-14.** The last `from scipy import signal` (in `_run_dual_capture`) is removed. `git grep -n scipy -- '*.py'` then listed only `build_sidecar.py`'s message, changed in 2.2, and `import transcriber` succeeds.

## 2. Dependencies and notices

- [x] 2.1 Delete `scipy>=1.10.0` from `requirements.txt`, `requirements-linux.txt` and `requirements-macos.txt`, and SciPy's line from `THIRD-PARTY-LICENSES.txt`. Verify with `git grep -n -i scipy -- 'requirements*.txt' THIRD-PARTY-LICENSES.txt`, which must print nothing.

  **Done 2026-09-14.** `scipy>=1.10.0` is removed from all three requirements files, and the `SciPy 1.16.3 BSD-3-Clause` line from `THIRD-PARTY-LICENSES.txt`.
- [x] 2.2 Change "numpy/scipy" to "numpy" in `build_sidecar.py`'s virtualenv error and README's venv paragraph (Decision 3). Verify neither file still says "scipy".

  **Done 2026-09-14.** `build_sidecar.py` now says "System numpy on some distros" and "A venv's pip-installed numpy wheels". README says "on distros where numpy is a system package".
- [x] 2.3 In a fresh venv built from `requirements-linux.txt` and `pyinstaller`, re-freeze with `build_sidecar.py`. Verify:
  - `pyi-archive_viewer -l dist/linux/transcriber-sidecar` lists no `scipy` entry;
  - `.github/smoke-test.sh dist/linux/transcriber-sidecar` passes;
  - the binary is about 24 MB smaller than the 159,053,256-byte sidecar from `01`'s build. Record both sizes.

  **Done 2026-09-14,** with a fresh venv at `~/.cache/venv-noscipy`, where `import scipy` gives `ModuleNotFoundError`:
  - **Size:** 159,053,256 → **130,094,904 bytes (-28,958,352, about -27.6 MiB)**. That's more than the ~24 MB estimated, which was SciPy's compressed size alone.
  - **Smoke test:** `.github/smoke-test.sh` passes.
  - **Archive listing:** no SciPy package entry. Two lines do match "scipy": `numpy.libs/libscipy_openblas64_-f48b354e.so` and its top-level symlink. That is **NumPy's own OpenBLAS**, which the scipy-openblas project publishes for NumPy wheels, so it stays with NumPy. Recorded here so a future grep isn't mistaken for SciPy coming back.

## 3. Full verification

- [x] 3.1 Run `.venv/bin/python run_tests.py` with the recording set, and verify it exits 0. Verify a local CLI live session with `--include-mic` on Linux still prints and saves `[SYS]` and `[MIC]` lines, and so does `--live` without `--include-mic` (the single-source path).

  **Automated half done 2026-09-14; the live half is waiting on the user.** With the recording set, `run_tests.py` passed 12/12 in 25.9s, including the new `test_resample.py`. `tests/test_engine.py --engine dist/linux/transcriber-sidecar` also passes both checks against the SciPy-free frozen binary. Packages built from it: AppImage 399,141,368 → 370,358,776 bytes, `.rpm` 321,462,573 → 292,504,145 bytes. The CLI live sessions need real audio and are the user's L2–L4.

  **Live half user-verified on Fedora, 2026-09-14** with the SciPy-free frozen sidecar (`dist/linux/transcriber-sidecar` from `7e46cdb`'s code, containing `01` and `02`). Dual capture (`--live --include-mic`) worked. The single-source path (`--live --audio-device 11`, a 44.1 kHz device, so `_process_audio_chunk` resamples with PyAV) also worked. **The user noticed L4 took long to show its first line.** That is the CLI default `--chunk-duration 30.0`: with no mic, nothing prints until 30 s of audio have built up. L2/L3's `[MIC]` lines are fixed 5 s chunks, so they looked quicker, and the GUI and launchers pass `--chunk-duration 10`. Not a regression: the single-source path only gained the resampler, about 9 ms per chunk. The test instructions should have passed `--chunk-duration 10`.
- [ ] 3.2 Trigger a `workflow_dispatch` CI run on `dev` (the user must ask for it). Verify all four jobs pass, the macOS smoke test included, and record each platform's sidecar size from the job logs or artifacts.
- [ ] 3.3 **User check on Windows and Linux** with builds containing `01` and `02`. This can be the same round as `01`'s 4.2 and 4.3: a live GUI session on each platform transcribes system audio and the mic correctly.

  **Linux half user-verified 2026-09-14** (the GUI with the local AppImage/`.rpm`; see `01` 4.3). The Windows half is waiting on a CI build.
