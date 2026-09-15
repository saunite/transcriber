## 1. Tests first

- [x] 1.1 In `tests/test_gui.py`, add `refused starts`, using the fake bridge:
  - **B1:** start a live session and emit `Listening...` and one live line. Drop a file with `start_file_transcription` rejecting "A live session is still running. Stop it before transcribing a file.". Emit another live line and a heartbeat. Assert:
    - the refusal note is shown;
    - both lines are in `#transcript-live` and none in `#transcript-file`;
    - after 31 simulated seconds with heartbeats, the status isn't "stalled".
  - **B2:** after a live session ends by itself (`live-session-ended` with a silence stop), with its line still in `#transcript-live`, press Start with `start_live_session` rejecting a model-folder message. Assert:
    - the note is shown;
    - the previous line is still in `#transcript-live`;
    - `#run-detail` still shows the silence-stop explanation.
  - **During a file run:** a file run is transcribing, and a live start is refused with the busy message. Then `file-transcription-complete` still marks that file done, and the heartbeat and log handlers stay gated to the file flow, so a `sidecar-heartbeat` doesn't move the Live status.

  Verify the scenario **fails** against the current `src/main.js`, recording which assertions fail.

  **Done 2026-09-15.** `test_refused_starts` is registered as "refused starts". Each section was run on its own against the unchanged `src/main.js`, and each fails as expected:
  - **B1:** "Locator expected to have count '2'". A live line emitted after the refused drop went to the File chart.
  - **B2:** "Locator expected to have count '1'". The refused live start cleared the previous meeting.
  - **File run:** "Locator expected to have count '1'". After the refused live start, the file run's line went to the Live chart.

  One deviation from the task text: the "during a file run" check asserts the run's transcript line stays in the File chart and the queue ends `done`. A heartbeat can't show the bug there, because heartbeats only change the status while a live session is running.

## 2. Fix

- [x] 2.1 In `src/main.js`:
  - **`startLiveSession`:** move `clearTranscript(els.transcriptLive)`, `currentFlow = "live"` and the per-session resets (`sessionStartedAt`, `lastLineAt`, `lastActivityAt`, `sawFirstLine`, `silenceStopSeen`, `endedMessage`, `endedClean`) after the `invoke` resolves. Keep `startLiveBtn.disabled`, `sessionSilenceMinutes` and the output path, which the command needs, before it.
  - **`startNextFile`:** move `clearTranscript(els.transcriptFile)` and `currentFlow = "file"` after its `invoke` resolves. Keep marking the entry `transcribing` before (the queue shows the attempt), and `finishCurrentFile(false)` on refusal.

  Verify `node --check`, that `refused starts` now passes, and that all other GUI scenarios still pass.

  **Done 2026-09-15.**
  - **`startLiveSession`:** the chart clear, `currentFlow = "live"` and the per-session resets now run only after `start_live_session` resolves. The silence minutes are read before the command into a local `startMinutes`, which is sent and then stored in `sessionSilenceMinutes` on success, so a refused start doesn't overwrite the minutes of the session that just ended. The refusal branch no longer calls `setLiveState("idle")` or clears `sessionRunning`, since nothing was changed; it re-renders the unchanged state.
  - **`startNextFile`:** the File chart clear and `currentFlow = "file"` now run only after `start_file_transcription` resolves. The entry is still marked `transcribing` first, and `finishCurrentFile(false)` still runs on refusal.
  - **Verified:** `node --check` passes, each `refused starts` section passes, and all 15 GUI scenarios pass.

## 3. Backlog and verification

- [x] 3.1 Remove cluster B from `openspec/backlog.md`'s "Logic audit follow-ups", since this change picks it up. Verify B1 and B2 no longer appear there, and clusters C and D are unchanged.

  **Done 2026-09-15.** Cluster B (B1, B2) is removed from "Logic audit follow-ups", and that item's intro now says clusters A and B were done in `fix-engine-liveness` and this change. Clusters C and D are unchanged.

- [x] 3.2 Run `.venv/bin/python run_tests.py` with `TRANSCRIBER_TEST_SPEECH` set and a network that reaches GitHub, and verify it exits 0.

  **Done 2026-09-15.** With `TRANSCRIBER_TEST_SPEECH` set and GitHub reachable (404): 13/13 suites passed, exit 0. The GUI suite includes the new `refused starts` scenario.
