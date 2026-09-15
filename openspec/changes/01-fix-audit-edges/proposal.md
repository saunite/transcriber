## Why

Logic audit cluster D (2026-09-15, `openspec/backlog.md`): the items with the same implementation on every platform. The Linux-only half of D6 is `02-fix-audit-edges-linux`, and the Windows items are `03-fix-audit-edges-windows`.

- **D1:** a system-audio-only live session (no `--include-mic`) goes through a separate single-source loop in `transcribe_live_simple`.
  - **Inference in the audio callback:** with an explicit `--audio-device`, PortAudio's audio callback runs transcription itself. The stream overflows and audio is dropped, which since `fix-true-scale-time-axis` also makes stamps fall behind.
  - **Silence stop does nothing:** the silence timeout raises `KeyboardInterrupt` on that callback thread. The main loop never sees it, so auto-stop never stops the session.
  - **Found while reading:** that loop also ignores the compact output requirement (it prints its own emoji banners). Its lines carry no source tag, so in the GUI they disappear from the chart under Show = SYS or Show = MIC.
- **D4 (Linux and macOS launchers):** `linux-start-transcription.sh` and `mac-start-transcription.sh`:
  - run `transcriber.py` by a relative path, so from a source checkout they only work when started from the project folder;
  - pass `--model base`, so a user-added `--model-path` is labelled "base" in the output (an explicit `--model` names the model).
- **D5:** the GUI's `withFreshTimestamp` splits the output path at the last `.` anywhere in it. `/home/a.b/transcript` becomes `/home/a_<stamp>.b/transcript`, a file in a folder that doesn't exist.
- **D7:** the stall hint's "raising and lowering the pens" copy was already removed by `fix-engine-liveness`; only the stale backlog entry is left.

## What Changes

- **One live runner:** a live session without a microphone uses the shared runner that dual-source sessions already use, with no microphone. Capture callbacks only queue audio, transcription runs on a worker thread, and the silence timeout stops the session. The separate single-source loop is deleted.
  - **BREAKING (CLI output):** system-audio-only lines are now tagged `[SYS]` (`[stamp] [SYS] text`), like dual-source sessions, and use the compact status lines. The GUI's line parser already accepts the tag.
- **Launchers (bash):** they run `transcriber.py` from the script's own folder, and no longer pass `--model base`. It's the default anyway, and the standalone CLI's bundled-model lookup keys on the same default.
- **GUI output path:** only the file name's extension is split off, never a dot in a folder name.
- **Backlog:**
  - remove D1, D5 and the stale D7;
  - trim D4 to its Windows half, which `03-fix-audit-edges-windows` covers.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `cli`, "Select Linux dual-source live capture mode": live capture without a microphone captures system audio through the same runner, labels segments `[SYS]`, and stops on silence.
- `teams-launcher`: adds "Launcher works from any folder and names the model it loads".
- `desktop-gui`, "Live session transcript is saved to a file": a dot in a folder name doesn't move the file.

## Impact

- **`transcriber.py`:** `transcribe_live_simple` becomes the single entry for the default live path. It merges `_transcribe_live_linux_dual`'s device resolution with an optional microphone. The old single-source loop, about 100 lines, is deleted.
- **`linux-start-transcription.sh`, `mac-start-transcription.sh`:** script-relative `transcriber.py`, and `--model base` removed.
- **`src/main.js`:** `withFreshTimestamp`.
- **Tests:**
  - `test_dual_capture.py`: a no-mic session with an explicit device, covering silence stop, the `[SYS]` tag, and no transcription on the callback thread;
  - a new root `test_launchers.py`;
  - a GUI scenario for a dotted folder;
  - `tests/test_gui.py`'s "listening wording" check, whose function list changes.
- **Docs:** README's live-capture section, where system-audio-only output shows `[SYS]`.
- **No shell (Rust), dependency or layout changes.**
