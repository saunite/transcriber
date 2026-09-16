## 1. Tests first

- [x] 1.1 In `test_wasapi_capture.py`, add a similarly-named-devices case with the fake `pyaudiowpatch`:
  - `get_default_output_device_info` returns the truncated MME name "Headphones";
  - `get_default_wasapi_device(d_out=True)` returns "Headphones";
  - the loopback generator yields "Headphones (2- Bluetooth) [Loopback]" first, then "Headphones [Loopback]".

  Assert `get_default_loopback_device()` returns "Headphones [Loopback]". Add a second case with no exact match that still returns the first loopback (the existing fallback).

  Verify the first case fails against today's `wasapi_capture.py`, and that `test_wasapi_capture.py` runs on Linux.

## 2. Fixes

- [x] 2.1 `wasapi_capture.py` `get_default_loopback_device`:
  - use `self.p.get_default_wasapi_device(d_out=True)` as the reference;
  - return the loopback whose name equals `<reference name> [Loopback]`;
  - otherwise the first loopback, as today;
  - keep the error print and `None` on exceptions.

  Verify 1.1 passes, and `test_dual_capture.py` still passes.

- [x] 2.2 `win-start-transcription.bat`:
  - copy `%~1` into a variable before the `if` block, and test that variable's first character, so a leading `-` isn't taken as the prefix;
  - use `%~dp0`-relative `.venv\Scripts\activate.bat` and `transcriber.py`;
  - drop `--model base`.

  Verify by reading the script that the output filename is still relative to the current folder and `--actual-time` and `--include-mic` are still passed.

- [x] 2.3 `transcribe_file.bat`: use `%~dp0`-relative `.venv\Scripts\python.exe` and `transcriber.py`, and drop `--language en`. Verify by reading the script.

  **Done, with two more fixes found by running both scripts** (2026-09-16, cmd on Windows, from another folder, with the scripts in a folder named `check out (x86)` beside a stub `transcriber.py` that prints its arguments, and in a second folder beside a dummy `transcriber.exe`):
  - `shift` also shifts `%0`, so after the argument loop `%~dp0` named the current folder or an argument's folder (`C:\models\` for `--model-path C:\models\small`), not the script's. This already affected the `transcriber.exe` lookup. `win-start-transcription.bat` now reads `%~dp0` into `HERE` before any `shift`.
  - A `)` in the script's path (`Program Files (x86)`) ended the `if exist ( ... )` block early: `\transcriber.exe"" was unexpected at this time`. Both scripts now choose between the exe and Python with `goto` instead of a block.

  Results: flags-only gives `meeting_<stamp>.txt` with `--silence-timeout 0` intact; a prefix with `--model-path` gives `sprint-review_<stamp>.txt` and no `--model`; no arguments works; `transcribe_file.bat` passes no `--language` and keeps `"a b.mp4"` as one argument; both scripts run the script folder's `transcriber.py` or `transcriber.exe`, and the transcript name is relative to the current folder.

## 3. Docs and backlog

- [x] 3.1 README Windows launcher notes:
  - flags-only launches;
  - starting from any folder;
  - `transcribe_file.bat` auto-detects the language.

  Verify each is described.

- [x] 3.2 `openspec/backlog.md`:
  - remove what remains of "Logic audit follow-ups" (D2, D3, the Windows half of D4 and D6, and the "Only skimmed" note, moved to "Minor" if still relevant);
  - add a parked item: "Windows system audio doesn't follow a default-output change mid-session" (WASAPI loopback is opened once; scoped out of cluster D by the user, 2026-09-15).

  Verify the audit section is gone, the new item is present, and the "Only skimmed" note is kept.

## 4. Verification

- [x] 4.1 Run `.venv/bin/python run_tests.py` with `TRANSCRIBER_TEST_SPEECH` set and a network that reaches GitHub, and verify it exits 0.

  **Done 2026-09-16**, run as `.venv-linux/bin/python run_tests.py` — on this machine `.venv/` is the Windows-targeted venv (`Scripts/`) and `.venv-linux/` the Linux one. GitHub reachable (404). **16/16 suites passed, exit 0**, 93.1 s; `test_wasapi_capture.py` includes both new cases ("the default output's own loopback wins over a similarly named one", "no exact match falls back to the first loopback"). Without `TRANSCRIBER_TEST_SPEECH` — no recording exists on this machine after the WSL migration — the two speech checks print `SKIP` and the suites still pass; the user accepted that.

  The first run failed one scenario, `tests/test_e2e_linux.py` "model folder used", which was **not** caused by this change. Tauri treats the running binary as a development build, and so resolves the bundled model next to it, only when its folder is `target/<profile>` or `target/<triple>/<profile>` (`tauri-utils-2.9.3/src/platform.rs:298`). The README's recommended `~/.cargo/config.toml` `target-dir` was `~/.cache/transcriber-target`, so the check failed and the app asked for `/usr/lib/Transcriber/resources/model`, which doesn't exist. Fixed at the root: README now recommends a path ending in `/target` and says why, and this machine's `target-dir` moved to `~/.cache/transcriber/target` (cargo reused the moved artifacts; no full rebuild). Re-run: 16/16.

- [x] 4.2 **Windows session, by the user** (Windows CLI archive built from this change, or a source checkout with the Windows venv):
  1. `win-start-transcription.bat --silence-timeout 0` from another folder creates `meeting_<stamp>.txt` in the current folder and runs;
  2. `win-start-transcription.bat sprint-review --model-path <bundled model folder>` names the file `sprint-review_<stamp>.txt` and reports the model by the folder's name;
  3. `transcribe_file.bat` on a non-English clip reports that language as detected;
  4. with two output devices whose names overlap (or any two, noting their names), live capture records the default output's loopback, as shown in `--verbose` output.

  Record the results under this task.

  **Done 2026-09-16, by the user**, in a Windows session with the current folder different from the script's folder. All four scenarios passed as written: the flags-only launch named the file `meeting_<stamp>.txt` in the current folder and ran with `--silence-timeout 0` intact; the prefix-plus-`--model-path` launch named the file `sprint-review_<stamp>.txt` and reported the model by its folder name, with no `--model`; `transcribe_file.bat` on a non-English clip reported that language as detected; and with two output devices whose names overlap, `--verbose` showed live capture on the default output's own loopback.
