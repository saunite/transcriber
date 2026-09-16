# CLI

## Purpose

Provide a command-line interface for the transcriber: selecting input sources, help/setup utilities, WASAPI and macOS native tap live capture modes, and graceful interruption handling.

## Requirements

### Requirement: Accept input source flags
The system SHALL require exactly one input source: `--file` for file transcription or `--live` for live capture, and SHALL print usage and exit with an error when neither is given.

#### Scenario: No input source specified
- **WHEN** a user runs the CLI without `--file` or `--live`
- **THEN** the system prints help and an error message and exits with a non-zero code

#### Scenario: File input
- **WHEN** a user passes `--file path/to/video.mp4`
- **THEN** the system transcribes the file

#### Scenario: Live input
- **WHEN** a user passes `--live`
- **THEN** the system captures and transcribes audio in real time

### Requirement: File transcription's auto-derived output filename includes a timestamp
When transcribing a file without an explicit `--output` path, the system SHALL derive the output filename from the input file's name and include a timestamp, so transcribing the same input file more than once never overwrites an earlier run's transcript. An explicit `--output` path SHALL be used exactly as given, with no timestamp added.

#### Scenario: Same file transcribed twice without --output
- **WHEN** a user transcribes the same input file twice without specifying `--output`
- **THEN** each run writes to a distinct, timestamped output filename, and neither run's transcript is overwritten by the other

#### Scenario: Explicit --output is honored exactly
- **WHEN** a user supplies an explicit `--output` path
- **THEN** the system writes to that exact path, unchanged and unstamped

### Requirement: Provide help and setup utilities
The system SHALL provide `--list-devices` to enumerate audio devices and `--setup-help` to print audio loopback setup instructions, each exiting after printing.

#### Scenario: List devices requested
- **WHEN** a user runs with `--list-devices`
- **THEN** the system prints audio devices and exits without transcribing

#### Scenario: Setup help requested
- **WHEN** a user runs with `--setup-help`
- **THEN** the system prints loopback setup instructions and exits

### Requirement: Provide machine-readable device listing
The system SHALL provide `--list-devices-json` to enumerate audio devices as a JSON array (index, name, max input channels, default sample rate per device) to stdout, exiting after printing without transcribing. This is additive: `--list-devices` SHALL continue to print the existing human-readable text format unchanged.

#### Scenario: JSON device list requested
- **WHEN** a user runs with `--list-devices-json`
- **THEN** the system prints a JSON array of device objects to stdout and exits without transcribing

#### Scenario: Existing text device list unaffected
- **WHEN** a user runs with `--list-devices`
- **THEN** the system prints the existing human-readable device listing exactly as before

### Requirement: Select WASAPI live capture mode
The system SHALL route live capture through WASAPI loopback on Windows when `--wasapi` is set, with optional concurrent microphone capture via `--include-mic` and `--mic-device`.

#### Scenario: WASAPI with microphone
- **WHEN** a user runs `--live --wasapi --include-mic --mic-device N`
- **THEN** the system captures system audio via WASAPI loopback and microphone concurrently, labeling segments `[SYS]` and `[MIC]`

#### Scenario: WASAPI without microphone
- **WHEN** a user runs `--live --wasapi` without `--include-mic`
- **THEN** the system captures only system audio via WASAPI loopback

### Requirement: Select macOS native loopback capture mode
The system SHALL provide `--coreaudio-tap` to select native macOS system-audio loopback capture, analogous to `--wasapi` on Windows, and SHALL reject platform-mismatched flags with a clear error instead of attempting to run.

#### Scenario: macOS native tap selected
- **WHEN** a user runs `--live --coreaudio-tap` on macOS
- **THEN** the system captures system audio via the native Core Audio Process Tap

#### Scenario: Wrong-platform flag usage
- **WHEN** a user runs `--coreaudio-tap` on Windows or Linux, or `--wasapi` on macOS
- **THEN** the system prints a clear error naming the correct flag for the current platform and exits without attempting capture

### Requirement: Select Linux dual-source live capture mode
The system SHALL route live capture through the auto-detected monitor/loopback source (or the explicit `--audio-device`) with optional concurrent microphone capture, using the same capture and transcription behaviour whether or not a microphone is included, via `--include-mic` and `--mic-device` when neither `--wasapi` nor `--coreaudio-tap` is set (the Linux default live-capture path). A microphone device that cannot open at the transcription sample rate (16 kHz) SHALL be opened at its own default sample rate and resampled to 16 kHz rather than failing the session. A microphone that cannot be auto-detected SHALL likewise not fail the session: the system SHALL fall back to the first device reporting input channels, and SHALL only exit when no input device exists at all.

#### Scenario: Default live capture with microphone
- **WHEN** a user runs `--live --include-mic --mic-device N` with no `--wasapi` or `--coreaudio-tap`
- **THEN** the system captures the monitor source and microphone concurrently, labeling segments `[SYS]` and `[MIC]`

#### Scenario: Default live capture without microphone
- **WHEN** a user runs `--live` without `--include-mic`, `--wasapi`, or `--coreaudio-tap`
- **THEN** the system captures only the system-audio source and labels its segments `[SYS]`, with the same compact output as a session with a microphone

#### Scenario: Explicit system-audio device without microphone
- **WHEN** a user runs `--live --audio-device N` without `--include-mic`, and speech continues for longer than one chunk
- **THEN** no captured audio is dropped while chunks are transcribed, and the lines are labelled `[SYS]`

#### Scenario: Silence stop without microphone
- **WHEN** a user runs `--live --silence-timeout S` without `--include-mic`, with or without `--audio-device`, and no speech is detected for S seconds
- **THEN** the session stops and exits successfully, as a session with a microphone does

#### Scenario: Microphone that refuses 16 kHz
- **WHEN** the selected or auto-detected microphone refuses to open at 16 kHz (for example a raw ALSA `hw:` device that only accepts 44.1 or 48 kHz)
- **THEN** the system opens it at the device's default sample rate, resamples its audio to 16 kHz, and transcribes `[MIC]` segments as usual, instead of exiting with an "Invalid sample rate" error

#### Scenario: Microphone that cannot be auto-detected
- **WHEN** a user runs `--live --include-mic` without `--mic-device` and the audio layer cannot resolve a default input device, while other devices with input channels are present
- **THEN** the system selects the first such device, names it in its output, and transcribes `[MIC]` segments as usual, instead of printing "Could not auto-detect microphone" and exiting

#### Scenario: Bundled audio libraries do not hide the host's devices
- **WHEN** a released Linux artifact runs on a distribution whose audio-library layout differs from the machine that built it
- **THEN** live capture enumerates the same input devices and monitor sources that the host system exposes to other audio applications, rather than a reduced set that omits the default input

### Requirement: Accept an explicit local model path
The system SHALL provide `--model-path <dir>` to load the whisper model from a local directory directly, bypassing the network/cache-based model name lookup, for both file and live transcription modes. When `--model-path` is not given, the standalone (frozen) CLI executable SHALL load its bundled model from a `model` directory next to the executable if that directory holds a model and the requested `--model` size is the bundled size (`base`). Wherever the system names the model in its output (transcript file header, live summary line, and live header), it SHALL use the `--model` value when `--model` is given, and the name of the `--model-path` directory when `--model-path` is given without `--model`; with neither, it SHALL use the default size `base`.

#### Scenario: File transcription with explicit model path
- **WHEN** a user runs `--file audio.wav --model-path C:\path\to\model`
- **THEN** the system loads the model from the given directory instead of resolving `--model` by name

#### Scenario: Live capture with explicit model path
- **WHEN** a user runs `--live --model-path C:\path\to\model`
- **THEN** the system loads the model from the given directory instead of resolving `--model` by name

#### Scenario: No model path given
- **WHEN** `--model-path` is not passed and the system is not running as a standalone executable with a bundled model next to it
- **THEN** the system behaves exactly as before, resolving `--model` by name

#### Scenario: Standalone executable with its bundled model
- **WHEN** the standalone CLI executable is run without `--model-path`, with `--model base` or no `--model` flag, and a `model` directory containing a model sits next to the executable
- **THEN** the system loads the model from that directory and attempts no download

#### Scenario: Standalone executable asked for a different model size
- **WHEN** the standalone CLI executable is run without `--model-path` and with a `--model` size other than `base`
- **THEN** the system ignores the bundled model and resolves the requested size by name, as before

#### Scenario: Output names a model path by its folder
- **WHEN** a user runs `--live --model-path /models/faster-whisper-small` without `--model`
- **THEN** the transcript header, summary line, and live header name the model `faster-whisper-small`, not `base`

#### Scenario: Explicit model name still labels the output
- **WHEN** a user runs with both `--model small` and `--model-path /models/anything`
- **THEN** the output names the model `small`

### Requirement: Handle interruption gracefully
The system SHALL handle Ctrl+C by stopping capture, finalizing the transcript, cleaning up resources, and exiting without a crash.

#### Scenario: User interrupts live capture
- **WHEN** the user presses Ctrl+C during live capture
- **THEN** the system stops capture and worker threads, closes the output file, releases audio devices, and saves any transcript produced

#### Scenario: User interrupts file transcription
- **WHEN** the user presses Ctrl+C during file transcription
- **THEN** the system stops cleanly and exits with the interrupted exit code

### Requirement: Live capture output is compact by default, with verbose detail available on request
During live capture, the system SHALL print a compact default output — one line naming the output file, one line summarizing model/language/capture mode/devices, and one line confirming it is listening — rather than the full startup/device-detection/shutdown detail. The system SHALL provide a `--verbose` flag that restores the full detail (startup banners, explicit per-device auto-detection messages, and capture-module start/stop announcements) in addition to the compact lines, and SHALL leave transcript line formatting and file-mode output unaffected by this flag.

#### Scenario: Default live capture output
- **WHEN** a user runs `--live` without `--verbose`
- **THEN** the system prints a compact preamble (output file, model/language/mode/device summary, listening confirmation) and a compact stop summary, without the full startup banners or per-device detail

#### Scenario: Verbose live capture output
- **WHEN** a user runs `--live --verbose`
- **THEN** the system prints the compact lines plus the full startup banners, explicit device auto-detection messages, and capture-module start/stop announcements

#### Scenario: File transcription is unaffected
- **WHEN** a user runs `--file` with or without `--verbose`
- **THEN** file-mode output is unchanged by this flag

### Requirement: File transcription fails on input with no decodable audio
File transcription SHALL fail when no audio can be decoded from the input file, meaning the decoder yields effectively zero duration (under 0.1 seconds), as happens with a non-media file given a media extension. On such input the system SHALL exit non-zero, report that the file has no decodable audio, and SHALL NOT leave a transcript file behind. Input that decodes to real audio with no speech in it is not a failure.

#### Scenario: Non-media file with a media extension
- **WHEN** a user transcribes a binary file renamed to `.mp3` and the decoder yields effectively zero duration
- **THEN** the command exits non-zero with a message that the file has no decodable audio, and no transcript file is created

#### Scenario: Silent recording
- **WHEN** a user transcribes a real audio file several seconds long that contains no speech
- **THEN** the command succeeds as before, exiting 0 with an empty transcript

### Requirement: Live capture saves a transcript by default
When `--live` is run without `--output`, the system SHALL save the transcript to a new file named `transcript_<YYYYMMDD_HHMMSS>.txt` in the current directory, stamped with the time the session starts, and SHALL name that file in its first output line. `--output <path>` SHALL save to the given path instead. `--no-output` SHALL print the transcript without saving it, and combining `--no-output` with `--output` SHALL be rejected with an error.

#### Scenario: Bare live capture
- **WHEN** a user runs `--live` with neither `--output` nor `--no-output`
- **THEN** the transcript is written to `transcript_<YYYYMMDD_HHMMSS>.txt` in the current directory, and the first output line names that file

#### Scenario: Explicit output path
- **WHEN** a user runs `--live --output meeting.txt`
- **THEN** the transcript is written to `meeting.txt`, as before

#### Scenario: Print-only session
- **WHEN** a user runs `--live --no-output`
- **THEN** the transcript is printed only, no file is created, and the output states that no transcript file is being saved

#### Scenario: Conflicting flags
- **WHEN** a user runs `--live --output meeting.txt --no-output`
- **THEN** the command exits with an error explaining that the two flags cannot be combined, before any capture starts

#### Scenario: Consecutive sessions
- **WHEN** a user runs two bare `--live` sessions one after another
- **THEN** each session writes its own, differently stamped file, and neither overwrites the other

### Requirement: Live capture reports a lost audio source
When the system audio source of a live capture stops delivering audio on its own, rather than because the user interrupted the session or the silence timeout was reached, the system SHALL print a message saying capture ended unexpectedly, SHALL keep the transcript saved so far, and SHALL exit with a non-zero code.

#### Scenario: The audio source goes away mid-session
- **WHEN** during live capture the system audio source ends, for example because the audio server restarted or the output device disconnected
- **THEN** the system prints that capture ended unexpectedly, closes the transcript file with everything transcribed so far, and exits with a non-zero code

#### Scenario: User interrupts the session
- **WHEN** the user interrupts a live capture session
- **THEN** the system exits with a success code, as before

#### Scenario: Silence timeout ends the session
- **WHEN** a live capture session reaches its silence timeout
- **THEN** the system prints that it stopped because of silence and exits with a success code, as before

### Requirement: File transcription prints its transcript as it goes
When transcribing a file, the system SHALL print each transcribed segment to standard output as it is produced, in the same timestamped form it writes to the output file, so a caller reading the process's output sees the transcript while the run is in progress rather than only when it ends. Progress display SHALL NOT be mixed into that output.

#### Scenario: Transcribing a recording from the command line
- **WHEN** a user transcribes a file
- **THEN** each segment appears on standard output, timestamped, as it is transcribed, and the saved transcript file contains the same lines

#### Scenario: Progress does not corrupt the transcript output
- **WHEN** a caller reads only the standard output of a file transcription
- **THEN** it contains the transcript lines and no progress-bar redraws
