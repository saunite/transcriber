# Audio Capture (Implementation Optimization)

## Purpose

This change optimizes the internal implementation of audio capture without modifying user-facing requirements or behavior. All existing requirements from the main audio-capture specification remain unchanged.

## Summary of Changes

**This change contains no requirement modifications.** All external APIs, user-facing behavior, and functional scenarios remain identical to the main spec. Internal optimization includes:

- Removing the unused queue-based buffering pattern from `AudioCapture`
- Replacing with direct callback invocation (more efficient, lower latency)
- Fixing awkward imports and deduplicating device validation logic

The refactoring is fully transparent to users and integrating systems.

## Unchanged Requirements

All requirements from `openspec/specs/audio-capture/spec.md` remain in effect:
- Live system audio capture (with auto-detect and device selection)
- Microphone capture concurrently with system audio
- WASAPI loopback on Windows (including Bluetooth devices)
- Audio device listing
- Optional audio-to-WAV saving and merging

All scenarios and behaviors defined in the main spec continue to function exactly as documented.

## Testing Scope

Implementation changes require verification that:
- Live capture (simple and WASAPI modes) captures audio with the same latency characteristics
- Device auto-detection and validation continues to work
- Error handling for missing/invalid devices provides the same user feedback
- All existing scenarios pass unchanged
