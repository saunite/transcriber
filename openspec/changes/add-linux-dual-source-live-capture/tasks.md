## 1. Engine: Linux dual-source capture

- [ ] 1.1 In `transcribe_live_simple`, branch on `args.include_mic`: when set, resolve the mic device (reusing `transcribe_live_wasapi`'s existing device-resolution/channel-detection logic) and open a second `sd.InputStream` alongside the existing system-audio stream — verify both streams open without error against this machine's real mic and PipeWire monitor source
- [ ] 1.2 Port the thread-safe queue + worker-thread structure from `transcribe_live_wasapi` (system and mic callbacks push to separate queues; a worker drains both, resamples to the 16kHz target rate, and tags segments `[SYS]`/`[MIC]`) — verify with a short live session that both tags appear correctly ordered by wall-clock/elapsed time
- [ ] 1.3 Open per-source WAV files when `--save-audio` is set (`<base>_sys.wav`, `<base>_mic.wav`), and call the existing `_merge_sys_mic_wav` to produce `<base>_merged.wav` — verify the merged file is 2-channel, correct sample rate, and each channel round-trips its source (reuse `test_wav_merge.py`'s existing assertions style)
- [ ] 1.4 Confirm the compact default preamble (from `compact-live-cli-output`) correctly reports mic mode and device name in the Linux dual-source case, matching the WASAPI path's `mode_summary` construction — verify by inspection of the printed line during a live run

## 2. Regression check

- [ ] 2.1 Confirm `--live` without `--include-mic` on Linux is byte-for-byte unchanged (same code path minus the new branch) — verify with a short single-source live session, comparing output shape to a run from before this change
- [ ] 2.2 Confirm `--wasapi` and `--coreaudio-tap` code paths are untouched — verify with `git diff` showing no changes inside either function

## 3. End-to-end verification (real hardware, available in this environment)

- [ ] 3.1 Run a real dual-source live session on this machine (real mic + PipeWire monitor), speak into the mic while system audio plays, confirm both sources transcribe with correct tags and the merged WAV plays back correctly on each channel
- [ ] 3.2 Run with no monitor source reachable (e.g., `pactl` unavailable or no default sink) and confirm the existing "could not auto-detect loopback device" error still fires for the dual-source case, rather than silently proceeding mic-only

## 4. Follow-up to add-cross-platform-launcher-scripts

- [ ] 4.1 Update `linux-start-transcription.sh` to pass `--include-mic` and drop its system-audio-only disclosure text, and update the corresponding `teams-launcher` spec requirement (added in `add-cross-platform-launcher-scripts`) to match — verify by re-reading both files after the edit

## 5. Spec

- [ ] 5.1 Add the `audio-capture` requirement for Linux dual-source capture
- [ ] 5.2 Add the `cli` requirement for selecting Linux dual-source capture mode
