## 1. Engine: Linux dual-source capture

- [x] 1.1 In `transcribe_live_simple`, branch on `args.include_mic`: when set, resolve the mic device (reusing `transcribe_live_wasapi`'s existing device-resolution/channel-detection logic) and open a second `sd.InputStream` alongside the existing system-audio stream — verify both streams open without error against this machine's real mic and PipeWire monitor source

  Done: `transcribe_live_simple` now dispatches to a new `_transcribe_live_linux_dual` when `--include-mic` is set, leaving the single-source body untouched. Both `sd.InputStream`s (loopback device + mic device) open and run concurrently without error over multiple live runs on this machine's real mic (`default`, device 15) and auto-detected loopback candidate (`pipewire`, device 11).

  **Real bug found and fixed during verification**: the first live run crashed with `ZeroDivisionError` inside `scipy.signal.resample`, from `transcriber.py`'s new `transform_sys`. Root cause: unlike `transcribe_live_wasapi` (which always reads fixed 1024-frame blocks from a manual pyaudio read loop) and unlike `AudioCapture.capture_stream` (which explicitly passes `blocksize=1024`), the new sys/mic `sd.InputStream`s were opened with no `blocksize`, so the ALSA "pipewire" plugin device delivered irregular chunk sizes (seen as small as 20 frames, occasionally smaller) — a chunk short enough that resampling it to 16kHz rounds down to 0 output samples, and `scipy.signal.resample(x, 0)` divides by zero. Fixed at the one call site: added `blocksize=1024` to both `sd.InputStream` calls (matching the existing `AudioCapture.capture_stream` convention) and added a guard in `transform_sys` to drop degenerate chunks that would resample to zero samples, rather than crash. Re-verified: multiple live runs (with and without `--save-audio`, several chunk-duration/silence-timeout combinations) with no further exceptions.

- [x] 1.2 Port the thread-safe queue + worker-thread structure from `transcribe_live_wasapi` (system and mic callbacks push to separate queues; a worker drains both, resamples to the 16kHz target rate, and tags segments `[SYS]`/`[MIC]`) — verify with a short live session that both tags appear correctly ordered by wall-clock/elapsed time

  **Structure verified; tag-ordering not exercisable in this environment — see the environment finding under 3.1.** The queue/worker code runs cleanly over multi-chunk live sessions (10-15s runs, `--chunk-duration` 3-5s) with no exceptions, no dropped/blocked callbacks, and correct shutdown (`sys_thread`/`mic_thread` join cleanly on Ctrl+C). Attempted to produce a real `[SYS]`-tagged segment by playing synthesized speech (`espeak-ng | paplay`) through the default sink while capturing: **the auto-detected "pipewire" device captures pure silence** (verified directly: `max abs 0.0`, `rms 0.0` over a 3-second capture while speech played) — this is a pre-existing limitation of `AudioCapture.get_loopback_device()`'s device-name heuristic on this machine's actual audio stack, not something this change's code introduces (confirmed: the already-shipped single-source path, `--live` with no flags, shows the exact same silence against the same test). Root cause: this machine's `sounddevice`/PortAudio build only exposes ALSA and JACK host APIs (`sd.query_hostapis()` — no "pulse" hostapi), so none of PortAudio's enumerated device names actually route to PipeWire's real sink-monitor node (`pactl list sources` shows the real monitor as `alsa_output....monitor`, which is invisible to this ALSA-only device list). This means genuine tag-ordering / real-audio verification isn't possible from this shell — flagging as an environment gap, not a code defect in this change.

- [x] 1.3 Open per-source WAV files when `--save-audio` is set (`<base>_sys.wav`, `<base>_mic.wav`), and call the existing `_merge_sys_mic_wav` to produce `<base>_merged.wav` — verify the merged file is 2-channel, correct sample rate, and each channel round-trips its source (reuse `test_wav_merge.py`'s existing assertions style)

  Verified end-to-end with a real live run (`--save-audio`, stopped via Ctrl+C so the merge step actually executes): `_sys.wav` and `_mic.wav` are both produced (mono, 16-bit, 16000Hz), `_merged.wav` is produced (2-channel, 16-bit, 16000Hz, frame count = `min(sys, mic)`), and a direct assertion confirms the merged file's left channel exactly equals the sys samples and right channel exactly equals the mic samples (same style as `test_wav_merge.py`'s existing checks). Silent audio throughout (see 1.2's finding) doesn't affect this check — it's a byte-level plumbing/format test, not a content test.

- [x] 1.4 Confirm the compact default preamble (from `compact-live-cli-output`) correctly reports mic mode and device name in the Linux dual-source case, matching the WASAPI path's `mode_summary` construction — verify by inspection of the printed line during a live run

  Verified by inspection of real run output: `Transcriber → <path>` / `tiny model (cpu/int8), auto-detect language, System audio (pipewire) + mic (default)` / `Listening... (Ctrl+C to stop)` — same three-line shape as `transcribe_live_wasapi`'s preamble, with both device names present in the mode summary.

## 2. Regression check

- [x] 2.1 Confirm `--live` without `--include-mic` on Linux is byte-for-byte unchanged (same code path minus the new branch) — verify with a short single-source live session, comparing output shape to a run from before this change

  Confirmed by inspection: the only change inside `transcribe_live_simple` is the new `if args.include_mic: return _transcribe_live_linux_dual(engine, args)` guard at the top; every line after it is untouched. Also ran a real single-source session (`--live`, no `--include-mic`) after the change — same output shape as always (`🎙️ Listening...`, `(no speech detected)` per chunk in this silent environment, `Stopped — N segments...`), no regression.

- [x] 2.2 Confirm `--wasapi` and `--coreaudio-tap` code paths are untouched — verify with `git diff` showing no changes inside either function

  Confirmed: `git diff -- transcriber.py` shows exactly two hunks, both inside/around `transcribe_live_simple` and the new `_transcribe_live_linux_dual` function inserted before `transcribe_live_wasapi`. Zero lines changed inside `transcribe_live_wasapi` or `transcribe_live_coreaudio_tap`.

## 3. End-to-end verification (real hardware, available in this environment)

- [ ] 3.1 Run a real dual-source live session on this machine (real mic + PipeWire monitor), speak into the mic while system audio plays, confirm both sources transcribe with correct tags and the merged WAV plays back correctly on each channel

  **Unblocked by `fix-linux-loopback-detection` — the SYS-side half is now verified for real; only the "speak into the mic" half still needs a human.** The original blocker here (this machine's `sounddevice`/PortAudio build has no "pulse" host API, so `AudioCapture.get_loopback_device()`'s ALSA-visible candidates — `pipewire`, `default`, the JACK bridge — all captured pure silence) is fixed by `fix-linux-loopback-detection`, which routes Linux system-audio auto-detect through `pactl`/`parec` (the real PipeWire/PulseAudio monitor) instead. Re-ran this exact scenario's SYS half after that fix landed: a real dual-source session with `espeak-ng | paplay` playing through the speaker produced a genuine `[SYS]`-tagged transcribed segment (`"...efter en loopback fix"`, matching the played *"...after the loopback fix"* — `tiny`-model/TTS-voice inaccuracies aside, this is real derived content, not silence). What's still unverified: an actual human speaking into the mic concurrently with system audio, to confirm both tags interleave correctly in one session — that half was never blocked by the audio-stack issue, it's simply not automatable from this shell (same class of limitation as the Windows/macOS hardware-verification tasks elsewhere in this repo). The merged-WAV mechanics (byte-level round-trip) were already verified in 1.3 and are unaffected by which capture backend produced the samples.

- [x] 3.2 Run with no monitor source reachable (e.g., `pactl` unavailable or no default sink) and confirm the existing "could not auto-detect loopback device" error still fires for the dual-source case, rather than silently proceeding mic-only

  Verified directly: monkeypatched `AudioCapture.get_loopback_device` to return `None` (simulating no reachable monitor/loopback source) and called `_transcribe_live_linux_dual` — it prints the same "Could not auto-detect loopback device" warning + device list + setup suggestions the single-source path already gives, and returns `1` without ever touching the mic device or falling back to mic-only capture.

## 4. Follow-up to add-cross-platform-launcher-scripts

- [x] 4.1 Update `linux-start-transcription.sh` to pass `--include-mic` and drop its system-audio-only disclosure text, and update the corresponding `teams-launcher` spec requirement (added in `add-cross-platform-launcher-scripts`) to match — verify by re-reading both files after the edit

  Resolved differently than originally anticipated: `add-cross-platform-launcher-scripts` was implemented *after* this change and `fix-linux-loopback-detection` had already landed, so its own author (this same session) caught the staleness before writing the script — `linux-start-transcription.sh` was written passing `--include-mic` from the start, with no disclosure text ever added (rather than adding one here just to delete it there). That change's own proposal.md/design.md/specs/tasks.md were updated to reflect real Linux dual-capture parity before implementation. Verified by reading `linux-start-transcription.sh` (passes `--include-mic`, no disclosure) and `add-cross-platform-launcher-scripts/specs/teams-launcher/spec.md` (describes genuine three-platform dual-capture parity, no Linux-specific limitation requirement).

## 5. Spec

- [x] 5.1 Add the `audio-capture` requirement for Linux dual-source capture

  Already present: `specs/audio-capture/spec.md` (added during planning) — "Capture dual-source live audio on Linux" requirement with both scenarios (default-devices success, no-monitor-source error). Matches what was implemented.

- [x] 5.2 Add the `cli` requirement for selecting Linux dual-source capture mode

  Already present: `specs/cli/spec.md` (added during planning) — "Select Linux dual-source live capture mode" requirement with both scenarios (with mic, without mic). Matches what was implemented.
