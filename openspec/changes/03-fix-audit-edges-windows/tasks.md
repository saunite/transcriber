## 1. Tests first

- [ ] 1.1 In `test_wasapi_capture.py`, add a similarly-named-devices case with the fake `pyaudiowpatch`:
  - `get_default_output_device_info` returns the truncated MME name "Headphones";
  - `get_default_wasapi_device(d_out=True)` returns "Headphones";
  - the loopback generator yields "Headphones (2- Bluetooth) [Loopback]" first, then "Headphones [Loopback]".

  Assert `get_default_loopback_device()` returns "Headphones [Loopback]". Add a second case with no exact match that still returns the first loopback (the existing fallback).

  Verify the first case fails against today's `wasapi_capture.py`, and that `test_wasapi_capture.py` runs on Linux.

## 2. Fixes

- [ ] 2.1 `wasapi_capture.py` `get_default_loopback_device`:
  - use `self.p.get_default_wasapi_device(d_out=True)` as the reference;
  - return the loopback whose name equals `<reference name> [Loopback]`;
  - otherwise the first loopback, as today;
  - keep the error print and `None` on exceptions.

  Verify 1.1 passes, and `test_dual_capture.py` still passes.

- [ ] 2.2 `win-start-transcription.bat`:
  - copy `%~1` into a variable before the `if` block, and test that variable's first character, so a leading `-` isn't taken as the prefix;
  - use `%~dp0`-relative `.venv\Scripts\activate.bat` and `transcriber.py`;
  - drop `--model base`.

  Verify by reading the script that the output filename is still relative to the current folder and `--actual-time` and `--include-mic` are still passed.

- [ ] 2.3 `transcribe_file.bat`: use `%~dp0`-relative `.venv\Scripts\python.exe` and `transcriber.py`, and drop `--language en`. Verify by reading the script.

## 3. Docs and backlog

- [ ] 3.1 README Windows launcher notes:
  - flags-only launches;
  - starting from any folder;
  - `transcribe_file.bat` auto-detects the language.

  Verify each is described.

- [ ] 3.2 `openspec/backlog.md`:
  - remove what remains of "Logic audit follow-ups" (D2, D3, the Windows half of D4 and D6, and the "Only skimmed" note, moved to "Minor" if still relevant);
  - add a parked item: "Windows system audio doesn't follow a default-output change mid-session" (WASAPI loopback is opened once; scoped out of cluster D by the user, 2026-09-15).

  Verify the audit section is gone, the new item is present, and the "Only skimmed" note is kept.

## 4. Verification

- [ ] 4.1 Run `.venv/bin/python run_tests.py` with `TRANSCRIBER_TEST_SPEECH` set and a network that reaches GitHub, and verify it exits 0.

- [ ] 4.2 **Windows session, by the user** (Windows CLI archive built from this change, or a source checkout with the Windows venv):
  1. `win-start-transcription.bat --silence-timeout 0` from another folder creates `meeting_<stamp>.txt` in the current folder and runs;
  2. `win-start-transcription.bat sprint-review --model-path <bundled model folder>` names the file `sprint-review_<stamp>.txt` and reports the model by the folder's name;
  3. `transcribe_file.bat` on a non-English clip reports that language as detected;
  4. with two output devices whose names overlap (or any two, noting their names), live capture records the default output's loopback, as shown in `--verbose` output.

  Record the results under this task.
