## Why

A live session transcribes its audio in 10-second chunks, and nothing transcribes what is left when it stops. `_drain_and_transcribe` in `transcriber.py` only runs inference once its buffer reaches the chunk threshold, and exits when the session stops and the queue is empty. Whatever was captured since the last full chunk, up to about 9 seconds, is dropped. Those are the last words spoken before the user presses Stop or Ctrl+C, often the conclusion of the meeting. The engine test's live-chunk check had the same gap, and a 16-second recording exposed it on 2026-09-18 (`openspec/changes/fix-linux-native-window-frame`, task 4.1).

## What Changes

- When a live session stops, each source's worker transcribes the audio still in its buffer as one last, shorter chunk, then exits:
  - it covers only audio not already transcribed, so the carried overlap isn't repeated;
  - the microphone's silence gate still applies;
  - its lines are stamped at their true position, like any other chunk;
  - they reach the transcript file before it is closed.
- This covers every stop the engine runs its shutdown for: Ctrl+C in the CLI on every platform, the silence timeout, and the desktop app's Stop on Linux and macOS (SIGINT, with up to 15 s before a kill).
- The Windows app's Stop kills the engine outright, so this alone doesn't help there. That is `02-flush-live-tail-on-stop-windows`.
- `tests/test_engine.py`'s live-chunk check feeds the recording's tail the same way, so a recording that doesn't divide into whole chunks is checked in full.
- `test_dual_capture.py` gets a check that stopping mid-chunk transcribes the remainder once, and that a silent microphone tail stays gated.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `transcription`: "Transcribe live audio chunks" adds that the audio remaining when a session stops is transcribed as a final chunk.
- `cli`: "Handle interruption gracefully" adds that an interrupted live session's transcript includes everything captured up to the interruption.

## Impact

- `transcriber.py` (`_drain_and_transcribe`, the stop path of `_run_dual_capture`).
- `tests/test_engine.py` (`check_live_chunks`) and `test_dual_capture.py`.
- No change to the app, the CLI's flags or the file transcription path.
