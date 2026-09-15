## Context

The default live path (no `--wasapi` or `--coreaudio-tap`) is `transcribe_live_simple` today:
- **With `--include-mic`**, it returns `_transcribe_live_linux_dual`. That function resolves the system-audio source (parec monitor on Linux auto-detect, or a PortAudio `InputStream` whose callback only enqueues, with a `check_silence()` poll loop), resolves the mic, and calls the shared `_run_dual_capture`.
- **Otherwise** it runs its own loop. On Linux auto-detect it uses the parec callback on the main thread, which is fine. With an explicit device it uses `AudioCapture.capture_stream`, whose PortAudio callback runs `_process_audio_chunk` inline and raises the silence `KeyboardInterrupt` there (D1).

`_run_dual_capture` already accepts `mic=None`: the WASAPI and Core Audio paths use it for system-audio-only sessions.

## Goals / Non-Goals

**Goals:**
- One capture and transcription runner for the default live path.
- Bash launchers that don't depend on the current folder.
- A GUI output path that keeps its folder.

**Non-Goals:**
- `AudioCapture.capture_stream` itself. It stays for `--list-devices` and the loopback lookup helpers; only the live path stops using its callback loop.
- The Windows `.bat` launchers (`03-fix-audit-edges-windows`), and the Linux monitor following a default-output change (`02-fix-audit-edges-linux`).

## Decisions

### 1. Merge the two default-path functions and make the mic optional

`transcribe_live_simple` keeps its name, since it's the entry `main()` routes to and the name the GUI test's listening check looks for. It takes over `_transcribe_live_linux_dual`'s body:
- **Source resolution:** unchanged.
- **Microphone:** `mic = _resolve_mic_config(args) if args.include_mic else None`, and the session ends only when a requested mic can't be resolved.
- **Title and mode summary:** name the mic only when there is one.

`_transcribe_live_linux_dual` and the old single-source loop are deleted. The listening check's `LIVE_FUNCTIONS` then points at `_run_dual_capture` alone, since that's where "Listening..." is printed.

- **Alternative, rejected:** moving inference out of the callback inside the old loop. That keeps two runners that already drifted apart (tags, compact output, silence handling), and the user chose the shared runner.

### 2. `[SYS]` on system-audio-only lines

This follows from Decision 1: `_run_dual_capture` tags by source, and the WASAPI and Core Audio system-audio-only sessions already print `[SYS]`. The GUI regex accepts the tag, and the transcript file header becomes `# Live Transcription (System Audio)`.

### 3. Script-relative `transcriber.py` in the bash launchers

`RUN=("${VENV_PY}" "${SCRIPT_DIR}/transcriber.py")`, and the same for the `python3` fallback. `output_file` stays relative, so transcripts still land in the current folder. `--model base` is dropped: `main()` defaults `args.model` to `base` after taking the label, and `_bundled_model_path` keys on that default.

### 4. Split the extension from the file name only

`withFreshTimestamp` looks for the last `.` after the last `/` or `\`, and ignores a leading dot in the name (a dotfile like `.transcript` has no extension).

## Risks / Trade-offs

- **[Scripts or users parsing untagged system-audio-only lines]** → The tag is the documented dual-source format and the GUI parser accepts both. It's noted as BREAKING in the proposal and README.
- **[The explicit-device PortAudio path on non-Linux without `--wasapi`/`--coreaudio-tap`]** → It's covered by the same merged function, since source resolution is unchanged, but it's not exercised on real hardware here. The fake-device test covers the thread and silence behaviour.
