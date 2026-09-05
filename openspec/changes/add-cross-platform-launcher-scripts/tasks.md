## 1. Windows: rename only

- [ ] 1.1 `git mv start_teams_transcription.bat win-start-transcription.bat` — verify the file's content is byte-identical after the rename (no behavior change) and `git status` shows a rename, not a delete+add

## 2. Linux launcher

- [ ] 2.1 Create `linux-start-transcription.sh`: port the batch script's argument convention (leading non-`-` argument is the name-prefix, default `meeting`; remaining args pass through) into bash, reusing `linux_start_transcription.sh`'s existing venv-detection idiom (prefer `.venv/bin/python`, fall back to `python3`) — verify `./linux-start-transcription.sh --help` (no name-prefix) and `./linux-start-transcription.sh sprint-review --silence-timeout 0` both parse correctly (echo the parsed name-prefix and remaining args to check)
- [ ] 2.2 Build the `transcriber.py` invocation as a bash array (`CMD=(...)`), not a string, with `--live --model base --output "$output_file" --chunk-duration 10 --actual-time` plus the passed-through args, deliberately without `--wasapi`, `--coreaudio-tap`, or `--include-mic` — echo the array (`printf '%q ' "${CMD[@]}"` or equivalent) then execute it (`"${CMD[@]}"`) so the printed line can't drift from what runs — verify by running with `--silence-timeout 0` and confirming the echoed line matches the actual `ps`/process args
- [ ] 2.3 Add the disclosure that only system audio is captured (no microphone), in the script's own printed output before it starts capturing — verify the text appears on every run, not just once
- [ ] 2.4 `chmod +x linux-start-transcription.sh` — verify `ls -l` shows the executable bit and `./linux-start-transcription.sh` runs without `bash` being invoked explicitly

## 3. macOS launcher

- [ ] 3.1 Create `mac-start-transcription.sh`: same argument convention and `CMD`-array pattern as the Linux script (task 2.1/2.2), but with `--coreaudio-tap --include-mic` instead of plain `--live`, and no PulseAudio-equivalent device-scanning preamble (Core Audio Tap needs none) — verify the script's structure by inspection against `linux-start-transcription.sh`, since no macOS hardware exists in this environment to run it (same caveat this codebase already carries for other macOS-only code)
- [ ] 3.2 `chmod +x mac-start-transcription.sh`

## 4. Spec coordination

- [ ] 4.1 Update the filename reference in the still-open `compact-live-cli-output` change's own pending delta spec (`openspec/changes/compact-live-cli-output/specs/teams-launcher/spec.md`) from `start_teams_transcription.bat` to `win-start-transcription.bat`, so it stays correct whenever that change eventually archives and syncs — verify by re-reading the file after the edit

## 5. Documentation

- [ ] 5.1 Update `README.md` and any other docs referencing `start_teams_transcription.bat` by its old name, and add a mention of the new Linux/macOS launchers alongside it — verify with `grep -rn "start_teams_transcription.bat"` returning no remaining hits anywhere in the repo (docs or code)

## 6. Verification

- [ ] 6.1 Confirm `win-start-transcription.bat` behavior is unaffected by the rename — this needs Windows hardware to actually run (same class of blocker as `compact-live-cli-output`'s own tasks 4.1/4.2); at minimum, confirm no other file in the repo (docs, other scripts) still references the old filename and would silently break
- [ ] 6.2 Run `linux-start-transcription.sh` on this Linux machine end-to-end (a short live session, Ctrl+C to stop) and confirm it behaves like `win-start-transcription.bat` minus the microphone: same defaults, same compact output shape, correct timestamped output file produced
