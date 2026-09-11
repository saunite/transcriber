## Context

See proposal.md - Why. Relevant current code:

- `src/main.js`:
  - `transcribeFile(path)` validates the extension, clears the file transcript, sets `currentFlow = "file"`, calls `setFileBusy(true)`, and invokes `start_file_transcription`.
  - The drop handler passes only `paths[0]`, and the dialog uses `multiple: false`.
  - `fileBusy` is written but never read.
- `src-tauri/src/sidecar.rs`: `start_file_transcription` spawns an untracked sidecar each time. When that process terminates, `spawn_sidecar_events` emits `file-transcription-complete` with `true` on exit code 0 and `false` otherwise, and `main.js` then calls `setFileBusy(false)`.
- `build_live_session_args()` always puts `--wasapi` after `--live`. On Linux the CLI's default `--live` path, plus `--include-mic`, is exactly the dual-source capture the GUI wants, and an explicit `--audio-device` index is honored there too.

## Goals / Non-Goals

**Goals:**
- Never more than one file sidecar at a time, with the queue and its progress always visible.
- GUI live capture that works on Linux, without changing Windows behavior.

**Non-Goals:**
- Removing or reordering queued files, or cancelling the running one. `ponytail:` add these when a real queue gets long enough to need them.
- Keeping each file's transcript on screen after the next file starts. Every file's transcript is saved to its output file; the chart shows the file currently running.
- Coordinating a file queue with a live session running at the same time. Transcript lines are routed by `currentFlow` today, so starting live capture mid-queue would misroute file lines. That predates this change and is left as is (see Risks).
- Enabling live capture on macOS. The `--coreaudio-tap` branch is added but stays unreachable behind the existing platform gate.

## Decisions

### 1. The queue lives in the frontend

The completion event already exists and carries success or failure, so the queue is a small piece of state in `main.js`: an array of `{ path, name, state }`. `enqueue(paths)` validates each path (unsupported ones get a note and are skipped), appends the valid ones as `waiting`, renders, and calls `startNext()` if nothing is running. `startNext()` marks the first waiting entry `transcribing`, clears the file transcript, and invokes `start_file_transcription`. If the invoke itself throws, the entry is marked `failed` and the queue moves on. The `file-transcription-complete` handler marks the running entry `done` or `failed` and calls `startNext()`. When nothing is waiting, the busy state clears.

- **Rejected: a queue in Rust** (a `SidecarManager` for file runs). The backend already reports completion, and there's a single window, so moving the queue there adds state and IPC for no behavior gain.
- **The frontend is the only caller of `start_file_transcription`.** A backend guard against concurrent runs is therefore optional. It's skipped (`ponytail:` add one if another caller ever appears).

### 2. Queue UI in the File panel

An `<ol id="file-queue">` sits under the drop zone. There's one row per file: the file name, plus a state label that reuses the existing `run-state`/`run-dot` styling (running rows look like the current "Transcribing" indicator). The existing `#file-state` label becomes `Transcribing <name> (n of m)`, so the running file is named right where the eye already goes. The drop zone stays enabled, because dropping more is how the queue grows; while busy its hint line changes to "Drop more to add them to the queue". Done and failed rows stay in the list until the next drop into an idle queue, which starts a fresh list. That way the user can see what happened to each file in the last batch.

### 3. Multi-file input

The drop handler enqueues every path in `event.payload.paths`, and the file dialog sets `multiple: true`, which returns an array (or `null` if cancelled). Both go through `enqueue()`, so validation and ordering behave the same way for both.

### 4. The live-capture flag comes from the target OS

`build_live_session_args()` starts from `--live`, then adds `--wasapi` when `cfg!(windows)`, or `--coreaudio-tap` when `cfg!(target_os = "macos")`, and nothing on Linux. It's a compile-time choice with no runtime detection, because the binary only ever runs on the OS it was built for. The existing `ponytail:` comment is replaced by a short explanation. A unit test asserts that the flag matches the compile target, and that the other platforms' flags are absent.

### 5. Device hint wording

`src/index.html` line 108, "auto-detected WASAPI device", becomes "auto-detected system-audio device". That's true on all platforms, and it's the only Windows-specific text a Linux user sees in the live panel.

### 6. The microphone dropdown defaults to "System default"

Found in task 1.3's first GUI test. The dropdown listed every input device and defaulted to the first, which on Linux is often a raw ALSA `hw:` device that refuses 16 kHz. A new first option, "System default (recommended)", has an empty value, and `startLiveSession` sends `micDevice: null` for it. The sidecar then gets `--include-mic` with no `--mic-device`, and the engine auto-detects exactly as the CLI does. Explicit devices stay selectable for the rare case where the default is wrong.

**Rejected: hiding raw `hw:`/ALSA plugin devices from the list.** Which devices are "raw" differs per system, and 1.5 makes them work anyway, so filtering would be guesswork for no gain.

### 7. The engine falls back to the mic's own sample rate and resamples

For robustness, when someone does pick a raw device, or a CLI user passes `--mic-device` for one: before opening the mic, `sd.check_input_settings(device, channels, samplerate=16000)` decides the rate. If 16 kHz is refused, the mic opens at its `default_samplerate`. The system-audio resampler (`transform_sys`) becomes `_to_target_rate(rate)`, and the mic's worker thread gets `_to_target_rate(mic_rate)` when that rate isn't 16 kHz. As with system audio, resampling happens off PortAudio's callback thread. The 16 kHz fast path is unchanged, so devices that already work get no transform. This is limited to `_transcribe_live_linux_dual`: the Windows and macOS paths already work, and changing them is outside this change's scope.

### 8. "No decodable audio" is a failure, decided by decoded duration

Found in task 2.4's GUI test. FFmpeg's decoders (MP3 especially) resync on anything that looks like a frame header, so a binary file given a media extension often decodes to a sliver of nothing instead of raising `FFmpegError`. `/usr/bin/ls` gives 0.02 s and a 300 MB `.rpm` gives 0.00 s. The engine then saved an empty transcript and exited 0, and the GUI faithfully reported success. The rule: after decoding, if `info['duration'] < 0.1` s, `transcribe_file` prints `❌ No decodable audio in <name> (decoded 0.00 s) — unsupported or corrupt media`, deletes any output file the run created, and returns 1. The GUI needs no change: exit 1 already marks the queue entry failed and shows the failure note.

- **Why duration:** it's objective and already computed. No real recording is under a tenth of a second, while a genuinely silent recording has real duration and keeps succeeding.
- **Rejected: failing on "0 segments".** That would turn every silent or music-only recording into an error.
- **Rejected: sniffing file headers or FFmpeg probe scores.** That's heuristic, format-specific, and duplicates what the decoder already reports through the duration.

## Risks / Trade-offs

- **[Risk]** A user starts a live session while files are queued, and file transcript lines land on the live chart (`currentFlow` routing). The problem predates this change, but a queue makes long file runs more likely → it's listed under Non-Goals and recorded here. If it bites, a follow-up can disable Start while the queue runs, or route lines by source instead of `currentFlow`.
- **[Risk]** The Linux dual-source live path has only been exercised from the CLI and the launcher, never from the GUI → task 1.3 verifies it in the GUI on the Fedora development machine.
- **[Trade-off]** Only the running file's transcript is on screen. Earlier files' transcripts are in their output files, and the queue list shows each file's final state.
