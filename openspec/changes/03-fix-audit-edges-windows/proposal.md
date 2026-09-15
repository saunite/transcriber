## Why

Logic audit cluster D, the Windows-only items (2026-09-15, `openspec/backlog.md`). The shared and Linux items are `01-fix-audit-edges` and `02-fix-audit-edges-linux`.

- **D2:** `win-start-transcription.bat` tests `"%~1:~0,1%"`, but cmd's substring syntax only works on variables, not on `%1`. The test is never `-`, so every first argument is taken as the name prefix. `win-start-transcription.bat --silence-timeout 0` names the file `--silence-timeout_<stamp>.txt` and passes a bare `0` to the CLI, which rejects it.
- **D3:** `transcribe_file.bat` hard-codes `--language en`, so a recording in any other language is transcribed as if it were English.
- **D4 (Windows launchers):** both `.bat` files run `transcriber.py` (and `win-start-transcription.bat` the venv's `activate.bat`) by relative path, so from a source checkout they only work from the project folder. `win-start-transcription.bat` also passes `--model base`, so a `--model-path` passed through is labelled "base".
- **D6 (Windows half):** `WASAPICapture.get_default_loopback_device` compares the **MME** default output's name, which Windows truncates to 31 characters, as a substring of each loopback device's name. It returns the first containing match. With two similarly named outputs, for example "Headphones" and "Headphones (2- Bluetooth)", it can record the wrong one.

## What Changes

- **Flags-only launches work:** `win-start-transcription.bat` takes the first argument as the name prefix only if it doesn't start with `-`, as the Linux and macOS launchers already do.
- **`transcribe_file.bat` auto-detects the language**, like the CLI and GUI.
- **Windows launchers work from any folder:** they run the checkout's `transcriber.py` and venv from the script's own folder, keep writing the transcript to the current folder, and stop passing `--model base`.
- **The default output's own loopback is recorded:** the reference is the **WASAPI** default output device, and the loopback device is the one named exactly `<that name> [Loopback]`. The existing first-loopback fallback stays for when there is no exact match.
- **Backlog:**
  - remove the rest of "Logic audit follow-ups" (D2, D3, D4, D6);
  - park "Windows system audio doesn't follow a default-output change mid-session", which the user scoped out of cluster D on 2026-09-15.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `teams-launcher`:
  - **"Default to wall-clock timestamps"** gains a flags-only launch scenario;
  - **added:** "Windows launchers work from any folder, name the model they load, and detect the language".
- `audio-capture`, "Capture WASAPI loopback on Windows": auto-detection records the default output's own loopback device, not a similarly named one.

## Impact

- **`win-start-transcription.bat`, `transcribe_file.bat`:** argument parsing, `%~dp0`-relative `transcriber.py`, `.venv` and `activate.bat`, no `--model base`, no `--language en`.
- **`wasapi_capture.py`:** `get_default_loopback_device` uses `get_default_wasapi_device(d_out=True)` from pyaudiowpatch (present in the pinned `>=0.2.12.5` line) and an exact name match.
- **Tests:** `test_wasapi_capture.py` gains a similarly named devices case, with fakes, runnable on Linux. The `.bat` behaviour is checked in a Windows session.
- **Verification needs a Windows session** (the user's), like earlier Windows checks.
- **No GUI, shell (Rust), engine or dependency changes.**
