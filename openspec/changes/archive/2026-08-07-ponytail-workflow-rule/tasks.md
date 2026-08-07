## 1. Update project config

- [x] 1.1 Replace the commented-out example `context` block in `openspec/config.yaml` with a concise description of the application (offline audio/video transcription via faster-whisper, Windows/Linux, Python + sounddevice/pyaudiowpatch/numpy/scipy/ffmpeg, txt/srt/vtt output, spec-driven workflow)
- [x] 1.2 Add the ponytail rule to `rules` for each artifact (`proposal`, `specs`, `design`, `tasks`): "ALWAYS use the ponytail skill on any change to ensure it is optimized. If the skill is not available, continue normally but inform the user."

## 2. Verification

- [x] 2.1 Run `openspec instructions proposal --change "ponytail-workflow-rule" --json` and confirm the output includes the project `context` and the ponytail rule in `rules`
- [x] 2.2 Run `openspec validate ponytail-workflow-rule` and confirm the change passes
- [x] 2.3 Run `openspec doctor` and confirm the config parses without warnings
