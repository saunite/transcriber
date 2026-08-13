## Context

The codebase has three primary inefficiencies:

1. **Queue Pattern in AudioCapture**: `audio_capture.py` uses a queue-based buffering pattern where `_audio_callback()` enqueues audio chunks and the main loop dequeues them. This adds unnecessary latency, complexity, and a polling loop without benefit.

2. **Code Duplication**: Both `transcribe_live_simple()` and `transcribe_live_wasapi()` in `transcriber.py` repeat header printing, file setup, device validation, and result summaries.

3. **Awkward Import Pattern**: `audio_capture.py` line 137 uses `__import__('time').sleep()` instead of a normal `import time`, creating confusion.

4. **Broad SSL Disabling**: `transcription_engine.py` lines 14–16 globally disable SSL verification via module-level modifications, which is overly broad.

## Goals / Non-Goals

**Goals:**
- Remove queue-based indirection from AudioCapture; replace with direct callback
- Eliminate repeated setup code between live transcription modes
- Use standard Python imports
- Narrow SSL certificate handling to specific operations
- Maintain 100% compatibility with existing user-facing APIs and behavior
- Preserve all timestamp functionality (`--actual-time`, relative/wall-clock time, silence timeout)
- Enable future refactoring by reducing code complexity

**Non-Goals:**
- Change transcription output format or quality
- Modify command-line interface or option structure
- Add new features (this is cleanup only)
- Refactor the WASAPI threading model (it is working and performant)
- Change audio device detection logic beyond deduplication

## Decisions

### Decision 1: Remove Queue from AudioCapture, Use Direct Callback

**Choice**: Replace `self.audio_queue` + `_audio_callback()` + polling loop with direct callback invocation.

**Rationale**: 
- The queue adds a polling loop without functional benefit (same thread context for both producer and consumer).
- Direct callbacks are simpler, lower latency, and match the pattern used in `transcriber.py`'s WASAPI code (which correctly uses thread-safe queues for cross-thread communication).
- `sounddevice` callbacks are designed to be fast; queueing audio in a synchronous context defeats the purpose.

**Implementation**:
- Store the user's callback as `self.callback` in `capture_stream()`
- Invoke it directly from `_audio_callback()` instead of queuing
- Remove `self.audio_queue` initialization and the polling loop at lines 131–134

**Alternatives Considered**:
- Keep the queue pattern: Unnecessarily complex and adds latency for no benefit.
- Use asyncio: Over-engineering for synchronous audio I/O; current approach with callbacks is idiomatic for `sounddevice`.

### Decision 2: Extract Common Setup Code

**Choice**: Create helper functions for repeated patterns in `transcribe_live_simple()` and `transcribe_live_wasapi()`.

**Rationale**:
- Both functions repeat header printing (header + 60-char rule), file opening, WAV file setup, and result summaries.
- A shared helper reduces duplication and makes future changes easier.

**Implementation**:
- Extract `_setup_output_files()`: Opens transcript and WAV files, prints headers
- Extract `_print_summary()`: Prints completion summary
- Reuse across both functions

**Alternatives Considered**:
- Merge the two functions: Infeasible due to fundamentally different threading and resampling models.
- Leave duplication: Creates maintenance burden and inconsistency.

### Decision 3: Standard Import for `time`

**Choice**: Add `import time` at module top; replace `__import__('time').sleep()` with `time.sleep()`.

**Rationale**:
- `__import__()` is a code smell; normal imports are clearer and more maintainable.
- No downside to importing `time` at module level.

### Decision 4: Improve SSL Certificate Handling

**Choice**: Use context managers or targeted urllib3 suppression instead of global `ssl._create_default_https_context` manipulation.

**Rationale**:
- Global SSL context manipulation affects all HTTPS connections in the process, potentially masking real security issues.
- A more targeted approach (e.g., context manager around model downloads, urllib3 warnings suppression) is safer.

**Implementation**:
- Wrap the `WhisperModel()` initialization with a context manager that disables SSL verification only for that call
- Or use `urllib3.disable_warnings()` combined with a custom urllib3 pool manager

**Alternatives Considered**:
- Keep global disabling: Too broad, potential security implications.
- Remove SSL disabling entirely: May fail on corporate networks; a pragmatic workaround is needed.

### Decision 5: Device Validation Deduplication

**Choice**: Extract common device info queries into a shared helper function.

**Rationale**:
- Both live capture modes call `sd.query_devices()` and validate device channels independently.
- A shared `_get_device_info()` helper eliminates duplication and makes future changes consistent.

**Implementation**:
- Create `_get_device_info(device_id)`: Returns validated device info or raises with helpful error message
- Use in both `transcribe_live_simple()` and `transcribe_live_wasapi()`

## Risks / Trade-offs

| Risk | Mitigation |
|------|-----------|
| Removing queue changes timing of audio delivery slightly | Actual impact is negligible (callbacks are per-chunk anyway); test live capture to confirm latency is acceptable |
| Direct callback might expose exceptions from user code in capture callback context | Wrap user callback in try-except to handle errors gracefully; log and continue |
| Extracted helpers must handle both simple and WASAPI modes | Design helpers with clear contracts; add unit tests for error cases (device not found, etc.) |
| SSL context manager approach might be unfamiliar to future maintainers | Document the rationale in a comment; reference corporate network issues |

## Migration Plan

1. **Phase 1**: Refactor `audio_capture.py`
   - Remove queue pattern, add direct callback
   - Add `import time` at top, fix `__import__` call
   - Add error handling in callback wrapper

2. **Phase 2**: Extract helpers in `transcriber.py`
   - Create `_setup_output_files()` and `_print_summary()` functions
   - Update both `transcribe_live_simple()` and `transcribe_live_wasapi()` to use helpers
   - Extract `_get_device_info()` for device validation

3. **Phase 3**: Fix SSL handling in `transcription_engine.py`
   - Wrap `WhisperModel()` initialization with SSL context manager
   - Remove global `ssl._create_default_https_context` manipulation
   - Test model loading on corporate network (if available)

4. **Testing**:
   - Unit tests for device validation errors (device not found, wrong channel count)
   - Integration tests for file transcription (ensure output unchanged)
   - Manual testing of live capture (simple and WASAPI modes) to verify latency and output consistency
   - Verify `--actual-time` and silence timeout behavior unchanged
   - Confirm timezone handling (machine time vs. wall-clock time) works as before

5. **Rollback**: Git revert; changes are fully reversible

## Open Questions

- Should we add a simple unit test suite for `audio_capture.py` device validation? (Recommend: Yes, to prevent regressions)
- For SSL context manager, should we use `urllib3.disable_warnings()` + custom pool, or a try-except around model download? (Recommend: Start with try-except for simplicity, upgrade to urllib3 if corporate network testing reveals issues)
