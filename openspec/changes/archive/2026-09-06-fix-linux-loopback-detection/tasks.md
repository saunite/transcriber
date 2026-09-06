## 1. `LinuxLoopbackCapture` module

- [x] 1.1 Create `linux_loopback_capture.py` with `get_default_loopback_device()`: run `pactl get-default-sink`, check `<sink>.monitor` against `pactl list sources short`, fall back to the first `.monitor`-suffixed source name, return `None` if `pactl` is missing or no monitor source exists — verify by calling it directly on this machine and confirming the returned name matches the `.monitor` entry `pactl list sources short` shows

  Verified: `get_default_loopback_device()` returns `{'name': 'alsa_output.pci-0000_00_1f.3.analog-stereo.monitor'}`, matching exactly the `.monitor` line `pactl list sources short` shows.

- [x] 1.2 Implement `capture_stream(callback, device_index=None, verbose=False)`: spawn `parec --device=<name> --format=s16le --rate=16000 --channels=1`, a background thread reads fixed 1024-frame blocks from its stdout and converts to float32 mono, the main thread drains a queue with a short timeout and calls `callback(chunk)` synchronously (mirrors `WASAPICapture.capture_stream`'s shape so `KeyboardInterrupt` from inside a callback propagates correctly) — verify by capturing while playing synthesized speech (`espeak-ng --stdout "..." | paplay`) and confirming non-zero max-abs/RMS energy in the captured chunks

  Verified: ran `capture_stream` on a background thread while playing `espeak-ng | paplay` speech — captured `max abs 0.84`, `rms 0.09` (genuinely non-silent), versus the `0.0`/`0.0` the old `sounddevice`-based path produced in the identical test.

- [x] 1.3 Implement `cleanup()` (terminate the `parec` subprocess if still running) and confirm the "no monitor found" path (`pactl` missing, or no `.monitor` source) returns `None` without raising — verify by monkeypatching `shutil.which('pactl')` to `None`

  Verified: `shutil.which` monkeypatched to `None` → `get_default_loopback_device()` returns `None`, no exception. `cleanup()` is a no-op when no process was started, and correctly terminates a real running `parec` subprocess (confirmed `.poll()` transitions from running to `None`/terminated).

## 2. Wire into `transcriber.py`

- [x] 2.1 In `transcribe_live_simple`, branch on `platform.system() == "Linux" and args.audio_device < 0`: use `LinuxLoopbackCapture` for the system-audio stream instead of `AudioCapture`; an explicit `--audio-device N` keeps today's exact `sounddevice`-index behavior, untouched — verify with a real live run that the auto-detected device name matches `pactl`'s real monitor source

  Done and verified: a real single-source run prints `Using loopback device: alsa_output.pci-0000_00_1f.3.analog-stereo.monitor` (the real `pactl` monitor), and — with `espeak-ng | paplay` playing during the run — the transcript contains actual recognizable text for the first time (see 3.1).

- [x] 2.2 Apply the same branch in `_transcribe_live_linux_dual` (from `add-linux-dual-source-live-capture`) for its system-audio side only; remove the now-dead `transform_sys` resampling code and its `ZeroDivisionError` guard (`parec --rate=16000` already delivers 16kHz, no manual resample needed); move the silence-timeout check back into the sys-audio callback (now running on the main thread via `LinuxLoopbackCapture.capture_stream`, like WASAPI) instead of the polling-loop workaround — verify with `git diff` that the mic-side code is untouched, and with a live run that no resample code path executes (e.g. temporarily assert-guard it during a manual test)

  Done differently than originally phrased, for a good reason: `transform_sys` (with its `ZeroDivisionError` guard) is **kept**, but only used on the non-Linux-loopback branch (explicit `--audio-device N`, or a non-Linux platform reaching this function) — that branch still goes through plain `sounddevice` at the device's native rate and still needs the resample/guard. The new Linux-auto-detect branch passes `transform=None` to its worker thread instead (`sys_callback_native` already receives pre-resampled 16kHz audio from `parec` and writes the WAV itself, mirroring how the mic callback already works) — so the dead-code removal happens only on the path that's actually dead, not the shared `transform_sys` helper the other branch still legitimately needs. Verified: real dual-source run produces `[SYS]`-tagged output with no resample-related exception; `git diff` confirms mic-side callback/queue/thread code is untouched from before this change.

- [x] 2.3 Update both functions' printed device-name/preamble lines to show the real `pactl` monitor source name — verify by inspection of a live run's printed summary line

  Verified: dual-source run prints `System audio (alsa_output.pci-0000_00_1f.3.analog-stereo.monitor) + mic (default)` in the compact preamble, and `Auto-detected loopback: alsa_output.pci-0000_00_1f.3.analog-stereo.monitor` in verbose mode — both the real monitor name, not `pipewire`.

## 3. End-to-end verification

- [x] 3.1 Run a real single-source live session on this machine while playing synthesized speech (`espeak-ng --stdout "..." | paplay`) through the speaker, confirm the transcript contains actual recognizable text rather than `(no speech detected)` for the whole run — this is the check that was impossible before this fix

  Verified: real run transcribed `"The quick round fox jump over the lazy dog testing."` / `"and not testing the real fix."` while `espeak-ng` played *"The quick brown fox jumps over the lazy dog testing the real fix"* — genuinely recognizable text (small `tiny`-model/robotic-TTS inaccuracies aside), where the pre-fix code produced silence/`(no speech detected)` for the identical test.

- [x] 3.2 Run a real dual-source live session (`--include-mic`) with the same synthesized-speech system audio, confirm `[SYS]`-tagged segments contain real transcribed text; the mic side stays untestable without a human speaking (same limitation `add-linux-dual-source-live-capture` task 3.1 already flagged) but confirm no crash/regression there

  Verified: real run produced `[00:00.300 -> 00:04.300] [SYS] Sista måd jag ljul så stäst efter en loopback fix.` while `espeak-ng` played *"System audio dual source test after the loopback fix"* — real `[SYS]`-tagged content derived from the actual played audio (the `tiny` model mis-detected the language/garbled words on this synthetic TTS voice, but the words "efter en loopback fix" ≈ "after the loopback fix" are clearly present — a model-accuracy artifact, not a capture bug). No crash; clean Ctrl+C shutdown through both the compact stop line and the verbose summary. Mic side: no crash/regression, but real speech-into-mic verification still needs a human (unchanged limitation from `add-linux-dual-source-live-capture`).

- [x] 3.3 Confirm the "no monitor source" error path fires end-to-end in a real run (e.g. via the `shutil.which` monkeypatch from 1.3, or a throwaway `PATH` without `pactl`) — clean error + return 1, no crash, no silent mic-only fallback

  Verified for both entry points (`transcribe_live_simple` and `_transcribe_live_linux_dual`) with `shutil.which` monkeypatched to `None`: both print the same "Could not auto-detect loopback device" warning and return `1` without ever touching the mic device or falling back to mic-only capture.

- [x] 3.4 Confirm explicit `--audio-device N` on Linux is completely unaffected — verify via code inspection / `git diff` that this branch is untouched

  Confirmed by inspection: the explicit-device branch (`device_id is not None`) in both functions is the exact pre-existing code (same `sd.query_devices`/`AudioCapture`/`transform_sys`/`sys_callback_raw` path), just moved under an `else:` alongside the new Linux-auto-detect branch — no line inside it changed.

## 4. Follow-through

- [x] 4.1 Revisit `add-linux-dual-source-live-capture`'s `tasks.md` task 3.1 (currently blocked on this exact issue) once 3.2 above is verified — update its status/notes to reflect this fix, referencing this change — verify by re-reading that file after the edit

  Done: updated that task's note to record the blocker as resolved by this change, with the real re-verified `[SYS]`-tagged result. Left the checkbox itself unchecked — the "speak into the mic" half of that scenario still needs a human and was never blocked by the audio-stack issue this change fixes.
- [x] 4.2 Review `setup_loopback_instructions()` (`audio_capture.py`) and any README Linux-loopback-setup text for claims that are now stale (e.g. manual monitor-source setup steps that auto-detection now handles) and trim/update them — verify by re-reading the affected sections

  No stale claims found to remove (the existing text already said auto-detection would handle it, which is now genuinely true instead of aspirational). Added the one new fact worth stating: `pactl`/`parec` are now a real runtime dependency for Linux auto-detect, not just an optional inspection tool — updated `setup_loopback_instructions()` (`audio_capture.py`) and both the Linux loopback-setup section and the "No loopback device found" troubleshooting bullet in `README.md`. Verified by running `transcriber.py --setup-help` and reading the updated `README.md` sections.

## 5. Spec

- [x] 5.1 Update the `audio-capture` requirement's Linux auto-detect scenario to describe `pactl`-based discovery instead of generic device enumeration

  Already present: `specs/audio-capture/spec.md` (added during planning) — MODIFIED "Capture live system audio" requirement, updated "Auto-detect loopback device" and "No loopback device found" scenarios. Matches what's planned above.
