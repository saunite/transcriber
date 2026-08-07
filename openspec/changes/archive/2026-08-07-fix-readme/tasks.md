## 1. Update README install section

- [x] 1.1 Add a Linux install note: `pip install -r requirements-linux.txt` (avoids the Windows-only `pyaudiowpatch` in `requirements.txt`)
- [x] 1.2 Add ffmpeg install hints for the two main Linux families: Debian/Ubuntu (`apt`) and RHEL/Fedora (`dnf`)

## 2. Update Real-time Audio Capture section

- [x] 2.1 Add a Linux live-capture subsection documenting `start_transcription.sh [device-index]`
- [x] 2.2 Document `--save-audio` behavior: in WASAPI mode it writes `_sys.wav` and `_mic.wav`, then merges them into a stereo `_merged.wav` (ffmpeg)

## 3. Add launcher documentation

- [x] 3.1 Add a "Launchers" section documenting `transcribe_file.bat` and `merge_and_transcribe.bat` with usage examples

## 4. Update Complete Options

- [x] 4.1 Add `--setup-help` to the Complete Options list (already used in examples)

## 5. Verification

- [x] 5.1 Re-read README and confirm emojis render as intended (no `?`/mojibake in a UTF-8 viewer); confirm file has 0 U+FFFD replacement characters
- [x] 5.2 Run `openspec validate fix-readme` and confirm the change still passes
