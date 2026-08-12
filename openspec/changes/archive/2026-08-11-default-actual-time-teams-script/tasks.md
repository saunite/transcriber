## 1. Update the launcher script

- [x] 1.1 In `start_teams_transcription.bat`, add `--actual-time` to the fixed `python transcriber.py ...` invocation, before `%REST%`, so it's always passed by default.

## 2. Update documentation

- [x] 2.1 In README.md, update the `start_teams_transcription.bat --actual-time --save-audio` example (around the "Quick Start for Teams Meetings" section) to reflect that `--actual-time` is now the default and no longer needs to be passed explicitly.

## 3. Verify

- [x] 3.1 Confirm `start_teams_transcription.bat` with no extra arguments builds a `transcriber.py` command line that includes `--actual-time` (inspect the script or a dry-run echo of the constructed command).
