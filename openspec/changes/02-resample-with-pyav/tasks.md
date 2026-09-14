## 1. Resampling

- [ ] 1.1 Add `_resample(resampler, block, rate, flush=False)` to `transcriber.py` (design.md Decision 2), wrapping a mono float32 block in an `av.AudioFrame` and returning the concatenated output. Add `test_resample.py` at the repo root with these cases:
  - 3 s of a 1 kHz tone at 48000 Hz and at 44100 Hz, fed in 1,024-frame blocks through one resampler: the dominant frequency of the output is within 1 Hz of 1,000, and the total length plus the flush equals `len * 16000 / rate`;
  - a 3-frame block returns an empty array without raising;
  - a single 10-second chunk with `flush=True` returns exactly `len * 16000 / rate` samples.
  Verify the test passes.
- [ ] 1.2 Replace `_run_dual_capture`'s scipy transform and its zero-length guard with a per-worker resampler created on the first block (Decision 1). Verify `python test_dual_capture.py` passes, including its 44.1 kHz sample-count and 3-frame cases. If a count assertion assumed scipy's exact per-block lengths, change it to a whole-run total within the 16-sample flush, and record that in this task.
- [ ] 1.3 Replace `_process_audio_chunk`'s `signal.resample` with a fresh flushed resampler (Decision 2). Verify with a case added to `test_resample.py`: a 44.1 kHz chunk through `_process_audio_chunk`, with a fake engine recording its input, reaches the engine as `round(len * 16000 / 44100)` float32 samples.
- [ ] 1.4 Remove every `from scipy import signal` from `transcriber.py`. Verify that `git grep -n scipy -- '*.py'` returns only the `build_sidecar.py` message edited in 2.2, and that `python -c "import transcriber"` succeeds.

## 2. Dependencies and notices

- [ ] 2.1 Delete `scipy>=1.10.0` from `requirements.txt`, `requirements-linux.txt` and `requirements-macos.txt`, and SciPy's line from `THIRD-PARTY-LICENSES.txt`. Verify with `git grep -n -i scipy -- 'requirements*.txt' THIRD-PARTY-LICENSES.txt`, which must print nothing.
- [ ] 2.2 Change "numpy/scipy" to "numpy" in `build_sidecar.py`'s virtualenv error and README's venv paragraph (Decision 3). Verify neither file still says "scipy".
- [ ] 2.3 In a fresh venv built from `requirements-linux.txt` and `pyinstaller`, re-freeze with `build_sidecar.py`. Verify:
  - `pyi-archive_viewer -l dist/linux/transcriber-sidecar` lists no `scipy` entry;
  - `.github/smoke-test.sh dist/linux/transcriber-sidecar` passes;
  - the binary is about 24 MB smaller than the 159,053,256-byte sidecar from `01`'s build. Record both sizes.

## 3. Full verification

- [ ] 3.1 Run `.venv/bin/python run_tests.py` with the recording set, and verify it exits 0. Verify a local CLI live session with `--include-mic` on Linux still prints and saves `[SYS]` and `[MIC]` lines, and so does `--live` without `--include-mic` (the single-source path).
- [ ] 3.2 Trigger a `workflow_dispatch` CI run on `dev` (the user must ask for it). Verify all four jobs pass, the macOS smoke test included, and record each platform's sidecar size from the job logs or artifacts.
- [ ] 3.3 **User check on Windows and Linux** with builds containing `01` and `02`. This can be the same round as `01`'s 4.2 and 4.3: a live GUI session on each platform transcribes system audio and the mic correctly.
