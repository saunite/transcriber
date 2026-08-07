## Context

The codebase grew speculative features that were never wired up. A ponytail audit found ~500 lines of dead code (a diarization feature whose modules `speaker_diarization.py`/`audio_buffer.py` have never existed, an unreachable AudioBuffer live path, an unused streaming API, dead WAV/device-listing methods), a standalone converter that duplicates the engine's SRT writer, and three inline copies of the same chunk→resample→transcribe→offset loop. This change removes the dead weight and consolidates the duplicated logic without changing any working behavior.

## Goals / Non-Goals

**Goals:**
- Remove all dead code and speculative features identified by the audit.
- Remove two capabilities from the spec tree (`speaker-diarization`, `transcript-conversion`) and keep the remaining specs accurate.
- Consolidate the duplicated live-chunk processing into a single helper.
- Shrink to a minimal dependency set.

**Non-Goals:**
- Fixing correctness bugs or performance issues found incidentally (out of audit scope).
- Rewriting the two working live-capture modes (`transcribe_live_simple` and the WASAPI path) into one — they use different backends and stay separate; only their shared chunk-processing loop is extracted.
- Removing behavior that works: `--save-audio`, silence auto-stop, WASAPI/mic dual capture, incremental saving, actual-time timestamps all stay.

## Decisions

1. **Delete the diarization feature wholesale** (flags, file/live diarization blocks, the AudioBuffer-based `transcribe_live`, `DIARIZATION_AVAILABLE` import dance). The modules it imports never existed, so `DIARIZATION_AVAILABLE` is always `False` and `transcribe_live` always falls through to `transcribe_live_simple`. Keeping a graceful-degradation path for software that isn't present is dead flexibility. Alternative considered: implementing diarization for real — rejected; out of scope and not requested.
2. **Delete `convert_to_srt.py` and the `transcript-conversion` capability.** The engine already writes SRT via `save_transcript("srt")` / `_format_srt_time`. The one thing the standalone script did differently — parsing an existing timestamped transcript file — is not needed since the CLI emits SRT directly. Alternative considered: keeping the script and deleting `_save_srt` — rejected; the engine's path is the one actually used.
3. **Drop word-level timestamp plumbing** (`words` list in segment dicts, `include_words` param, `_format_time`-based word rendering). `include_words` is never set `True` anywhere. This also simplifies `transcribe_file`/`transcribe_chunk` to build flat `{start, end, text}` dicts.
4. **Single helper for the live chunk loop.** Extract `buffer→concat→resample→transcribe→offset→timestamp` into one function (e.g. `_process_audio_chunk(audio, offset, use_actual_time, base_time, source_tag)` returning adjusted segments and the new offset) used by `transcribe_live_simple`, `sys_worker`, and `mic_worker`. The three call sites differ only in sample rate (native vs 16 kHz), source tag (`[SYS]`/`[MIC]`/none), and WAV-writing side effects, which stay at the call sites.
5. **One SSL-disable mechanism.** Keep the `ssl._create_default_https_context` override plus the env-var clears in a single short block; drop the `httpx.Client.__init__` monkey-patch, which is the most invasive of the three and redundant once `SSL_CERT_FILE=''` is set. Note: the monkey-patch also silently skips if httpx is absent, which hides the real mechanism.
6. **Collapse the three Teams `.bat` launchers into one** (`start_teams_transcription.bat`) taking optional args (`--silence-timeout 0`, `--actual-time`, meeting-name prefix) passed through to `transcriber.py`. The `-no-timeout` and `start_t_actual_time` variants are just flag permutations of the same script.
7. **Remove `pydub` and `onnxruntime` from requirements.** Grep confirms neither is imported anywhere in the tree. `soundfile` stays (WASAPI `--save-audio` merge), `scipy` stays (resampling), `tqdm` stays (progress bar).

## Risks / Trade-offs

- [Users relying on the never-working `--diarize` flags] → These flags crash at runtime today (import of nonexistent modules); removing them turns a crash into a clean "unknown argument" error. Documented in the migration notes of the removed specs and README.
- [Collapsing the `.bat` launchers breaks muscle-memory workflows] → The primary launcher keeps its exact path and behavior; the flag variants map to the same one-liner documented in README.
- [Extracting the chunk loop could introduce an offset bug] → The helper takes and returns the offset explicitly and is covered by a self-check task that compares timestamps across two chunks against the manual arithmetic.
- [Deleting `convert_to_srt.py` removes a documented workflow] → README's "converting existing transcripts" section is updated to point at `--format srt`.

## Migration Plan

1. Apply code removals file by file (`transcriber.py`, `transcription_engine.py`, `audio_capture.py`, `wasapi_capture.py`), then delete `convert_to_srt.py`.
2. Update `requirements*.txt`, README, and the `.bat` launchers.
3. Run `transcriber.py --help` and the file/live smoke paths to confirm the CLI surface matches the remaining flags.
4. Archive the change, which deletes `openspec/specs/speaker-diarization/` and `openspec/specs/transcript-conversion/` and syncs the `transcription` delta.
