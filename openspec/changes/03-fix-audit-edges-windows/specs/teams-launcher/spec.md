## MODIFIED Requirements

### Requirement: Default to wall-clock timestamps
Each platform's launcher script (`win-start-transcription.bat` on Windows, `linux-start-transcription.sh` on Linux, `mac-start-transcription.sh` on macOS) SHALL pass `--actual-time` to `transcriber.py` by default, so a user running the script without extra flags gets wall-clock timestamps rather than timestamps relative to the meeting/session start. Additional flags passed to the script SHALL still be appended after the defaults.

#### Scenario: Launch with no extra flags
- **WHEN** a user runs a platform's launcher script with no arguments (or only a name prefix)
- **THEN** the underlying `transcriber.py` invocation includes `--actual-time`, and output timestamps are wall-clock rather than relative

#### Scenario: Launch with additional flags
- **WHEN** a user runs a platform's launcher script with a name prefix and an additional flag (for example, `--silence-timeout 0`)
- **THEN** the underlying invocation includes both the default `--actual-time` and the user-supplied flag

#### Scenario: Launch with only flags
- **WHEN** a user runs a platform's launcher script with flags and no name prefix (for example, `win-start-transcription.bat --silence-timeout 0`)
- **THEN** the output filename uses the default `meeting` prefix, and every flag, with its value, is passed through to the invocation

## ADDED Requirements

### Requirement: Windows launchers work from any folder, name the model they load, and detect the language
`win-start-transcription.bat` and `transcribe_file.bat` SHALL run `transcriber.py`, and use the project's virtual environment, from the folder the script is in, so they work when started from any current folder, while still resolving the output file against the current folder. `win-start-transcription.bat` SHALL NOT pass a model size of its own, so a `--model-path` passed through to it is loaded and named after its folder. `transcribe_file.bat` SHALL NOT force a language, so the recording's language is auto-detected.

#### Scenario: Started from another folder in a source checkout
- **WHEN** a user runs `C:\path\to\checkout\win-start-transcription.bat` from a different current folder
- **THEN** the launcher runs the checkout's `transcriber.py` with the checkout's virtual environment, and the transcript file is created in the current folder

#### Scenario: A model folder passed through on Windows
- **WHEN** a user runs `win-start-transcription.bat --model-path C:\models\small`
- **THEN** the underlying invocation contains no `--model` flag, and the transcription output names the model `small`

#### Scenario: A non-English recording through the file script
- **WHEN** a user runs `transcribe_file.bat` on a recording in Portuguese
- **THEN** the invocation contains no `--language` flag, and the engine detects and transcribes Portuguese
