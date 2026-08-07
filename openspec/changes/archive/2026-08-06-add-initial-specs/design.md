## Context

This change adds the initial OpenSpec baseline for an existing, working audio transcription CLI. The repository contains:
- `transcriber.py` — CLI entry point and orchestration (file mode, live mode, WASAPI live mode)
- `transcription_engine.py` — faster-whisper wrapper (file/chunk transcription, timestamp formatting, txt/srt/vtt saving)
- `audio_capture.py` — cross-platform loopback capture via sounddevice + loopback instructions
- `wasapi_capture.py` — Windows WASAPI loopback capture via pyaudiowpatch
- `audio_extractor.py` — ffmpeg-based video-to-audio extraction with temp cleanup
- `convert_to_srt.py` — standalone transcript-to-SRT converter
- Optional diarization modules (`speaker_diarization.py`, `audio_buffer.py`) imported lazily; code degrades gracefully when torch/pyannote.audio are absent

There are no existing specs under `openspec/specs/`. This change documents current behavior as-is — it makes no runtime code changes. The specs are the contract; future changes will build deltas on top of them.

## Goals / Non-Goals

**Goals:**
- Produce a baseline set of OpenSpec capability specs that accurately describe the system's current behavior.
- Cover the six capabilities identified in the proposal: audio-extraction, audio-capture, transcription, speaker-diarization, transcript-conversion, cli.
- Ensure every requirement is testable with concrete scenarios.

**Non-Goals:**
- Refactoring, fixing bugs, or changing runtime behavior of the transcriber.
- Adding new features (e.g., new output formats, web UI, GPU tuning).
- Documenting every internal helper; specs capture externally observable behavior.

## Decisions

- **Spec-driven schema baseline, not delta-only**: Since `openspec/specs/` is empty, each capability gets a new `specs/<name>/spec.md` using `## ADDED Requirements`. This is the standard baseline workflow — the same files will later be synced to main specs and archived.

- **Capability granularity mirrors module boundaries**: The six capabilities map cleanly to modules (`audio_extractor.py`, `audio_capture.py`+`wasapi_capture.py`, `transcription_engine.py`, optional diarization, `convert_to_srt.py`, `transcriber.py`). Rationale: it keeps each spec cohesive and easy to evolve independently. Alternative considered: a single monolithic "transcription" spec — rejected because it would conflate capture, engine, and CLI concerns and make deltas coarse.

- **Scenarios use WHEN/THEN observable behavior only**: Requirements describe outcomes a user can verify (files created, labels emitted, exit codes) rather than internal implementation. Rationale: specs remain valid even if internals are rewritten. Alternative considered: documenting internal call graphs — rejected as too implementation-coupled.

- **Audio-capture merges sounddevice and WASAPI paths**: Both capture modes are documented under one capability because they share the same user-visible contract (live chunk delivery, device listing, WAV saving). WASAPI-specific behaviors are separate requirements within that spec. Rationale: keeps the capability list short; alternatives of splitting WASAPI into its own capability was considered but rejected as it is a platform-specific implementation of the same capability.

- **Timestamps, formats, silence timeout are transcription-capability requirements**: These live in the `transcription` spec since they are behaviors of the engine/CLI output pipeline, not capture.

## Risks / Trade-offs

- **Specs may drift from code** → Mitigation: this change's task list includes verifying each requirement/scenario against the source files; future changes must follow OpenSpec delta workflow to update specs when behavior changes.
- **Optional dependencies (torch/pyannote, onnxruntime) make diarization environment-specific** → Mitigation: the speaker-diarization spec explicitly captures the graceful-degradation requirement, so spec accuracy holds even where the modules are absent.
- **Baseline only captures current behavior, including known limitations** (e.g., hardcoded 16kHz target rate, 1s overlap in simple live mode) → Mitigation: documented as-is; future deltas can improve these.

## Migration Plan

No runtime migration is needed — no code or data changes. The spec files are introduced under the change and later synced/archived into `openspec/specs/` as the project baseline. There is no rollback concern beyond deleting the spec files if the baseline is unwanted.

## Open Questions

- None for this change. If later deltas propose behavior changes, the respective capability specs will be MODIFIED accordingly.
