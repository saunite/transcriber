# Remove audio saving

## Why

`--save-audio` never delivered what it promised. On real Windows hardware a 71.2s WASAPI + mic session on the **`tiny`** model produced a 41.1s `_sys.wav` — **42% of the system audio was silently discarded**, with no warning. The cause is structural: `_mic.wav` is written from the real-time `mic_callback`, but `_sys.wav` is written from `transform_sys` on the transcription worker thread, behind blocking inference. Whatever the worker never drains is never written, and a larger model makes it strictly worse.

A recording feature that quietly drops nearly half its input is worse than no recording feature, because the loss is invisible until someone needs the audio. The GUI never exposed it, nothing else consumes the files, and there are no releases and therefore no users to migrate. Deleting it removes ~210 lines and an entire class of bugs instead of paying to fix a feature nobody asked for.

## What Changes

- **BREAKING** Remove the `--save-audio` CLI flag. No deprecation period — the tool has no releases.
- Remove all WAV recording from the three live-capture paths (`transcribe_live_simple`, `transcribe_live_linux`, `transcribe_live_wasapi`, `transcribe_live_coreaudio_tap`): file handles, per-chunk writes, close calls, and the post-session merge blocks.
- Delete `_merge_sys_mic_wav()` and its test `test_wav_merge.py`.
- Drop the audio-save parameters and print lines from `_print_summary()`, and the WAV half of `_setup_output_files()`.
- Update `README.md` (flag reference and the `--save-audio` example) and the three launcher scripts' comment lines.
- Delete `merge_and_transcribe.bat` and its `README.md` "Launchers" entry. Its signature is `<mic_file.wav> <sys_file.wav>` — the `_mic.wav` / `_sys.wav` pair only `--save-audio` produced — so it is the downstream consumer of the feature being removed, not an independent one, and nothing else in the repo can produce its inputs.
- Remove the dead ffmpeg `PATH` line from `transcribe_file.bat` and `win-start-transcription.bat`, and the README's claim that the launchers set up an "ffmpeg PATH". After the deletion above, no launcher invokes ffmpeg, so both lines only prepended a hardcoded, machine-specific WinGet directory that does not exist on any other machine.

### Explicitly not in scope

Deletion only. The surrounding code gets *smaller*, not rearranged — these are called out because the removal makes each one tempting, and each would grow the diff without being asked for:

- **Do not inline `_setup_output_files()`** even though it is left returning a single value and has one caller. Inlining is a larger diff than deleting.
- **Do not restructure `_print_summary()`** beyond dropping the four now-unused parameters.
- **Do not unify the live-capture functions**, which become more similar once the WAV code is gone. They diverge on genuine platform specifics; merging them is a separate change that must stand on its own.
- **Do not touch what the launchers otherwise do.** Their venv activation, `PYTHONHTTPSVERIFY`, encoding and codepage setup are unrelated to this change and stay exactly as they are.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `audio-capture` — removes the `Save captured audio to WAV files` requirement outright.
- `cli` — the `Handle interruption gracefully` scenario says Ctrl+C "closes output and WAV files"; there will be no WAV files to close.

## Impact

- `transcriber.py` — ~140 lines removed across five regions, plus all five local `import wave` statements (every one exists only for audio saving).
- `test_wav_merge.py` — deleted (71 lines).
- `README.md:162`, `README.md:262`; comment lines in `win-start-transcription.bat`, `linux-start-transcription.sh`, `mac-start-transcription.sh`.
- Two load-bearing lines sit *inside* blocks that look deletable and must survive: `transform_sys()`'s `signal.resample()` (feeds transcription) and `mic_callback()`'s `mic_audio_queue.put()` (**is** the mic transcription path). Deleting either callback body wholesale breaks live capture.

### Related: a suspected shutdown bug that did not reproduce

Investigating this removal, `_merged.wav` was never produced on a real Windows run even though both mono WAVs closed cleanly, and the unconditional `Merging system and microphone audio...` print that follows never appeared. The hypothesis was that shutdown dies inside `capture.cleanup()` → PyAudio's `p.terminate()`, which sits between the WAV closes and the merge, and that this was independent of audio saving.

**Task 3.2 does not support that.** Running current source, the same WASAPI + mic path shut down cleanly on Ctrl+C and printed its stop summary — which is reached only *after* `capture.cleanup()` returns. So `p.terminate()` completed normally here. The original observation came from a binary three commits stale, and the merge code it concerned is now deleted, so the symptom is no longer reproducible either way. Recorded as unexplained rather than confirmed; no follow-up change is opened on this evidence.
