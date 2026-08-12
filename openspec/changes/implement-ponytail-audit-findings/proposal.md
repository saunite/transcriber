## Why

The codebase has accumulated inefficiencies and confusing patterns that add complexity without benefit. Code duplication between live transcription modes, an unused queue-based audio buffering pattern, and awkward imports reduce maintainability and readability. Simplifying these patterns reduces cognitive load and improves code clarity while preserving all functionality—especially critical for time-sensitive transcription behavior that must not be disrupted.

## What Changes

- Remove the unused queue-based audio buffering pattern from `AudioCapture` and replace with direct callback invocation
- Fix awkward `__import__('time')` workaround; use standard `import time` at module level
- Extract repeated setup/summary code between `transcribe_live_simple` and `transcribe_live_wasapi` functions
- Consolidate device query logic to eliminate duplication across capture modes
- Improve SSL certificate handling from broad module-level manipulation to more targeted approach
- Preserve all existing APIs and user-facing behavior—no breaking changes

## Capabilities

### New Capabilities

None. This is a code-quality and maintainability improvement, not a feature addition.

### Modified Capabilities

- `audio-capture`: Internal implementation streamlined (queue pattern removed, direct callback used), but external API and real-time capture behavior unchanged

## Impact

- **Code files affected**: `audio_capture.py`, `transcriber.py`, `transcription_engine.py`
- **User-facing changes**: None. All CLI options, output formats, and transcription behavior remain identical
- **Critical constraint**: Timezone/wall-clock timestamp handling in `transcription_engine.py` must not be affected; time-based features (`--actual-time`, silence timeout) must continue working correctly
- **No API changes**: All public methods and class interfaces unchanged
- **No dependency changes**: No new or removed packages
