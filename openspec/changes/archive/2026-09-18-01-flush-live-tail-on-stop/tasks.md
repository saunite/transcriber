# Tasks

## 1. Engine

- [x] 1.1 In `transcriber.py`, move the chunk block of `_drain_and_transcribe` into a local `transcribe(data, kept)`. The loop calls it as today; after the loop, call it once on the remaining buffer with `kept = 0` when that buffer holds more than `carried` samples, and add the `ponytail:` comment from design.md Decision 3. Verify `test_dual_capture.py` still passes unchanged.
- [x] 1.2 In `test_dual_capture.py`, add checks using the existing fake engine and synthetic `run_sys`, and verify each fails against the old code (`git stash`) and passes with 1.1:
  - SYS stopped mid-chunk after about 14 s of audio: the fake engine receives a final chunk covering only the audio after the last one, stamped at its position, and its line reaches the output file;
  - a stop exactly at a chunk boundary adds no final chunk;
  - with a mic whose tail is silent, no MIC line is added.

  **Done 2026-09-18.** `_check_stop_keeps_tail` in `test_dual_capture.py`, all passing with 1.1:
  - **SYS stopped mid-chunk:** 2 s chunks with 2.5 s fed. The engine gets `[32000, 24000]`, stamps `[00.60 …]` and `[01.60 …]`, and the last line is in the transcript file.
  - **Stop on a chunk boundary:** `[32000]` only, so no extra chunk.
  - **Microphone gate:** a silent 5 s chunk, then a 0.5 s tail. A silent tail adds 0 MIC lines, an audible one adds 1.

  Against the old `transcriber.py` (`git stash`), the SYS case gives `[32000]` and the audible mic tail gives 0 lines. The boundary case passes on both, as intended, since it guards against an unneeded chunk.

  Two things found while writing it:
  - **The microphone's chunks are a fixed 5 s** (`mic_chunk_samples`), whatever `--chunk-duration` says, so its tail can be up to about 4 s.
  - **The gate checks the whole last chunk**, including the carried second, as it does for every chunk. A silent tail right after speech is therefore still sent to the model, and the real engine's VAD filter is what keeps silence out of the transcript. That's unchanged behaviour, so the gate check starts from a silent chunk.


## 2. Engine check and real-model verification

- [x] 2.1 In `tests/test_engine.py`, make `check_live_chunks` transcribe the remainder after the last whole chunk as a final chunk (design.md Decision 4). Verify it passes with the 15.96 s recording (`TRANSCRIBER_TEST_SPEECH=~/Downloads/transcriber-test/test-audio.ogg`), which fails today on `almost`, `entirely`, `subsurface`, `these`.
- [x] 2.2 With the bundled model, time the final chunk for a 9 s tail, run from `test_dual_capture.py`'s harness or a one-off script with the real engine, and record it in design.md's Risks.

  **Done 2026-09-18.** With the bundled `base` model (int8, CPU, 8 threads), `_process_audio_chunk` on 10 s of the recording (the carried second plus 9 s of speech), after a warm-up run, took 3.06, 2.72, 2.78, 2.46 and 2.63 s, a median of 2.7 s. That's recorded in design.md's Risks: well inside the app's 15 s grace and the workers' 60 s join.


## 3. Suites and docs

- [x] 3.1 Run `.venv/bin/python run_tests.py` with `TRANSCRIBER_TEST_SPEECH` set and verify every suite passes with no skips other than the opt-in packaging suite.

  **Done 2026-09-18.** 19/19 suites passed in 96.7 s with the 15.96 s recording. The only skips were the three opt-in packaging checks (`TRANSCRIBER_TEST_PACKAGING`). `tests/test_engine.py`'s "live chunks do not repeat words", which failed before this change, now passes.

- [x] 3.2 Check `docs/user-guide.md` for any statement about what Ctrl+C or Stop keeps, and correct it if it says or implies the last seconds are lost. Verify with `grep -n -i "ctrl+c\|stop" docs/user-guide.md`.

  **Done 2026-09-18, no edit needed.** `docs/user-guide.md` describes Stop and the silence stop but never says or implies that the last seconds are lost or kept, and the README doesn't discuss it.

- [x] 3.3 Run `openspec validate 01-flush-live-tail-on-stop --strict` and verify it passes.
