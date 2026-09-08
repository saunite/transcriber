## 1. Remove the feature from `transcriber.py`

- [x] 1.1 Delete the `--save-audio` argument from the parser
- [x] 1.2 Delete `_merge_sys_mic_wav()` entirely, and the three post-session merge blocks that call it (one each in `transcribe_live_linux`, `transcribe_live_wasapi`, `transcribe_live_coreaudio_tap`) — including their `merged_audio_save_path` variables and `Merging system and microphone audio...` prints

  The WASAPI and Core Audio merge blocks were byte-identical, so they were removed with a single `replace_all` edit; the Linux one differs slightly (no `capture.cleanup()`) and was removed separately.

- [x] 1.3 Drop the WAV half of `_setup_output_files()` so it returns only the output file, and update its one caller in `transcribe_live_simple`. Do not inline the function

  Also dropped its `native_rate` and `include_mic` parameters. `native_rate` existed only to set the WAV frame rate, and `include_mic` was already unused — both were part of the docstring's claimed "For WASAPI with mic: (output_file, sys_wav_file, mic_wav_file, ...)" return variant, a signature this function never actually had. The function is left in place with one caller, as required.

- [x] 1.4 Drop the `audio_save_path`, `sys_audio_save_path`, `mic_audio_save_path`, and `merged_audio_save_path` parameters from `_print_summary()` and their four print lines, and update all call sites. Change nothing else about it
- [x] 1.5 In all four live-capture functions, delete the `if args.save_audio:` setup blocks, every `*_wav_file.writeframes(...)` guard, and every `*_wav_file.close()` in the `finally` blocks

  **Both load-bearing lines confirmed intact afterwards.** All three `transform_sys` definitions still resample and return (lines 843, 1105, 1327), and all seven `sys_audio_queue.put` / `mic_audio_queue.put` calls survive across the four paths. Three stale docstrings/comments that described the now-deleted WAV writing were corrected: the Linux and Core Audio `transform_sys` docstrings ("persist 16kHz WAV"), the WASAPI `mic_callback` comment ("write to disk and enqueue"), and the Linux worker-thread comment ("resamples (via parec) and writes the WAV itself").

- [x] 1.6 Remove all five local `import wave` statements — confirm with `grep -n "wave" transcriber.py` that none remain and that nothing else used them

  Two went with the functions deleted in 1.2/1.3; the remaining three were removed directly. `grep -n "wave" transcriber.py` now returns nothing.

## 2. Remove the test and documentation

- [x] 2.1 Delete `test_wav_merge.py`
- [x] 2.2 Remove the `--save-audio` flag entry and the `win-start-transcription.bat --save-audio` example from `README.md`
- [x] 2.3 Remove the `--save-audio` comment line from `win-start-transcription.bat`, `linux-start-transcription.sh`, and `mac-start-transcription.sh`
- [x] 2.4 Delete `merge_and_transcribe.bat` and its `README.md` "Launchers" entry

  **Added mid-implementation; corrects this proposal's original non-goal.** That non-goal claimed the script "merges two files the user supplies and records nothing, so it is a different feature." That was wrong: its signature is `merge_and_transcribe.bat <mic_file.wav> <sys_file.wav>`, i.e. exactly the `_mic.wav` / `_sys.wav` pair that only `--save-audio` produced. It is the downstream consumer of the feature this change removes, and after the removal nothing in the repo can produce its inputs. Deleting it here rather than in a separate change; the proposal's What Changes and non-goals were updated to match.

  Side effect: no code path in the repo invokes ffmpeg any more. See 2.5.

- [x] 2.5 Remove the dead ffmpeg `PATH` line from `transcribe_file.bat` and `win-start-transcription.bat`, and the README's "venv + ffmpeg PATH" claim

  Once 2.4 removed the last launcher that called ffmpeg, both remaining `set PATH=%PATH%;C:\Users\...\Gyan.FFmpeg_...\bin` lines were dead — and machine-specific, hardcoding one user's home directory, so on any other machine they appended a path that does not exist. Removed both, leaving the surrounding `REM Set up environment variables` block and its other `set` lines untouched. The README's Launchers intro no longer claims the launchers set up an ffmpeg PATH.

  `grep -rn ffmpeg` across the working tree now matches only prose: `README.md`'s history/notes, `PRODUCT.md`, `LICENSE`, `fetch_sidecar_resources.py`'s docstring, spec text, and archived changes. No script, no source file.

## 3. Verify

- [x] 3.1 `grep -rn "save_audio\|save-audio\|_merge_sys_mic_wav\|_sys.wav\|_mic.wav\|_merged.wav" transcriber.py README.md *.bat *.sh` returns nothing outside `merge_and_transcribe.bat`, which keeps its own separate file-merging workflow

  Passes — the single remaining match is `merge_and_transcribe.bat:45`, the documented exception.

- [x] 3.2 Run a live WASAPI session with `--include-mic` on Windows and confirm **both** `[SYS]` and `[MIC]` transcript lines still appear, and that no `.wav` file is written

  This is the check that catches a botched 1.5 — losing the resample or the mic queue put kills one stream each, and only a real session shows it.

  **Passed on real Windows hardware**, running current source through the project venv (`.venv\Scripts\python.exe transcriber.py --live --wasapi --include-mic --model tiny --chunk-duration 5`) from an interactive PowerShell session. Both streams transcribed — six `[SYS]` segments and one `[MIC]` segment across the run — so `transform_sys`'s resample and `mic_callback`'s queue put both survived 1.5 intact. `dir *.wav` returned empty: no WAV written. Session ended cleanly on Ctrl+C with `Stopped — 7 segments (not saved to a file)`.

  (An earlier attempt to run this from WSL appeared to hang after `✓ Model loaded successfully`. It was not hanging: loading the model over the `\\wsl.localhost` 9p/UNC mount is simply very slow — the user confirmed the same slow load interactively — and with stdout redirected to a file the 60s timeout expired before capture started. Not a code issue.)

- [x] 3.3 Confirm `--save-audio` is now rejected as an unknown argument

  Verified: `transcriber.py: error: unrecognized arguments: --save-audio`.
