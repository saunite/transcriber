## Why

Stopping a live session does not stop audio capture on Linux or macOS. The GUI logs `stop requested`, reports success, and returns to "Not transcribing" — while the engine keeps recording the microphone and system audio indefinitely and keeps appending to the live transcript file.

The user found it with a three-step repro on Fedora 44 (installed AppImage and `.rpm`):

1. File transcription — fine.
2. Live transcription, then stop — looks fine.
3. File transcription — the file transcribes correctly, **but everything spoken or played on the system also appears in the GUI**, tagged `[MIC]`/`[SYS]`.

**Root cause, measured.** PyInstaller's `--onefile` bootloader execs into a separate worker process. `stop_live_session` kills only the handle it holds — the bootloader — orphaning the worker that actually owns the audio device and the stdout pipe. Running the frozen sidecar here shows the two-process tree (bootloader `1115116` → worker `1116659`); `kill -9` on the bootloader alone leaves the worker alive, reparented, still capturing.

The Windows branch of that same function already documents this exact failure — *"child.kill() below only terminates that bootloader and orphans the actual worker process, which keeps running and holding the audio device"* — and fixes it with `taskkill /F /T`. The `#[cfg(not(windows))]` branch is a bare `child.kill()`, which signals one PID.

This is not hypothetical: the user's own 08:43 session was still running **~8 minutes after they stopped it**, still holding the mic, and only stopped when killed by hand. Its transcript had stopped growing because the room went quiet, not because capture had ended.

Three consequences follow, all visible in the user's screenshots:

- **Capture continues after a visible stop.** The app records microphone and system audio while the UI says "Not transcribing". That is a privacy defect, not a cosmetic one.
- **The orphan keeps the inherited stdout pipe**, so its `[SYS]`/`[MIC]` lines keep arriving. The UI routes lines by the current flow, so once a file run starts they are misfiled into the FILE transcript and chart — the symptom the user noticed first.
- **Nothing prevents two engines at once.** `start_file_transcription` never checks whether a live session is active, and discards its own child handle (`let (rx, _child) = …`), so its process cannot be terminated either.

## What Changes

- **Stopping a live session terminates the whole process tree, not just the bootloader** — the Unix analogue of the existing Windows `taskkill /F /T` branch. A graceful signal goes to the process that owns capture first, so the engine's existing interrupt handler can flush and close the transcript, with escalation if it does not exit.
- **Success is reported only when capture has actually ended.** The stop result is based on no surviving tree member, not on one kill call returning `Ok`.
- **A file transcription cannot start while a live engine is alive**, and the file run's process is tracked so it can be stopped too.
- **The `SYS`/`MIC` indicators reflect real capture state.** Today they are a display of *configuration*: `syncMicPen()` drives `data-armed` from the include-mic checkbox, and `pen-sys` is hardcoded `data-armed="true"` in the markup with no code ever writing it — so both read "Armed" permanently, which is why the UI looked like it was capturing. (Whether this lands here or as a follow-up is a design decision; it is the user's reported symptom either way.)
- **Not changed**: the Windows branch, which already terminates the tree correctly and must not regress.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities

- `desktop-gui`: "On-demand sidecar lifecycle with crash recovery" — its *Stop live capture* scenario already requires that the system "signals the sidecar to stop gracefully and waits for it to exit before returning to idle state". The Unix path does none of those three things: it force-kills the bootloader, does not wait, and does not confirm exit. The delta makes the guarantee explicit about the process that owns capture, and adds the rule that a file run cannot begin while a live engine is alive.
- `desktop-gui`: "Live session stop is confirmed genuinely, not cosmetically" — it already says the report must be "based on the real result of terminating the sidecar process, rather than assuming success", which the current Unix behaviour violates by reporting success while capture continues. The delta ties "succeeded" to capture having actually ended, with no surviving process holding the audio device.

Deliberately **not** modified: `audio-capture`'s capture requirements. They describe how audio is captured while a session runs, and nothing about that changes — the defect is in ending a session.

## Impact

- **Changed**: `src-tauri/src/sidecar.rs` (the Unix stop path, the spawn guard, tracking the file run's child), and `src/main.js`/`src/index.html` if the indicators become real state in this change.
- **Effect**: a stop that stops. No process keeps the microphone open after the UI says it is idle, and file transcriptions are no longer polluted by a previous session's audio.
- **Severity**: this is the most serious defect found so far in this project — silent continued recording of microphone and system audio after the user stopped it, in shipped Linux packages.
- **Platforms**: Linux is verifiable here. **macOS gets the same Unix code path and cannot be tested** (no Mac), so it must be recorded as implemented-but-unverified, consistent with how this project treats macOS. Windows is unaffected.
- **Ruled out while diagnosing**, so the fix does not chase the wrong layer: the engine does not tag file-run output (only the Linux dual-capture path emits `[SYS]`/`[MIC]`); the Rust parser's tag group is optional, so a bare file line yields no tag; the UI styles an untagged line as `SYS`, never `MIC`; and the file queue does set the current flow before invoking. The `MIC` lines in the file view were genuinely live audio from the orphan, not mislabelled file audio.
- **Related, not included**: the engine's wall-clock stamps and the GUI's session markers disagreed by an hour in the user's log (`transcription started · 08:43:28` against transcript lines at `07:43`). Unrelated to this defect and worth triaging separately.
