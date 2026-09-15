## Why

Logic audit cluster B (2026-09-15, `openspec/backlog.md`). The page prepares for a new session **before** the shell has accepted it, and never undoes that preparation when the shell refuses:
- **B1:** `startNextFile` clears the File chart and sets `currentFlow = "file"`, then `start_file_transcription` is refused, for example "A live session is still running…". Nothing resets `currentFlow`, so every later transcript line from the running live session is routed to the File chart. The Live panel stops seeing lines and heartbeats and reports "Transcribing stalled", while the engine is fine.
- **B2:** `startLiveSession` clears the Live chart and resets the last session's state (`currentFlow`, the "why it ended" message, activity timestamps) before `start_live_session` can refuse, for example over a model folder without `model.bin` or a running file transcription. The meeting the user wanted to re-read disappears from the screen, the reason the last session ended is lost, and during a file run the routing flips to "live".

## What Changes

- **A start changes nothing until the shell accepts it:** the page clears a chart, switches `currentFlow` and resets per-session state only after the start command resolves successfully. A refused start leaves the charts, the routing and the displayed state exactly as they were, and shows the refusal note as today.
- **Queue behaviour stays:** a refused file is still marked failed and the next queued file is tried, as today.
- **Why "after success" and not "before, then undo on failure":**
  - The engine can't produce transcript lines or heartbeats before its start command resolves; it's still loading its model.
  - An undo path would have to restore several variables and a cleared chart, which is more code and easy to get wrong again.
- **Not in this change:** the File view still shows no transcript for a file run (a separate backlog item); audit clusters C and D.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `desktop-gui`: added "A refused start leaves the screen as it was": a refused live or file start doesn't clear a chart, doesn't reroute the running session's lines, and doesn't reset what the previous session showed.

## Impact

- **`src/main.js`:** in `startLiveSession` and `startNextFile`, move the chart clear, the `currentFlow` assignment and the per-session resets below the successful `invoke`. The start button's disabled state and the silence minutes the command needs stay before it.
- **`tests/test_gui.py`:** fake-bridge scenarios for both refusals, each failing against today's code.
- **`openspec/backlog.md`:** cluster B is removed, since it's picked up by this change.
- **No shell, engine, layout or dependency changes.**
