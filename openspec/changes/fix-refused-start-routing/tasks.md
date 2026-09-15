## 1. Tests first

- [ ] 1.1 In `tests/test_gui.py`, add `refused starts`, using the fake bridge:
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

## 2. Fix

- [ ] 2.1 In `src/main.js`:
  - **`startLiveSession`:** move `clearTranscript(els.transcriptLive)`, `currentFlow = "live"` and the per-session resets (`sessionStartedAt`, `lastLineAt`, `lastActivityAt`, `sawFirstLine`, `silenceStopSeen`, `endedMessage`, `endedClean`) after the `invoke` resolves. Keep `startLiveBtn.disabled`, `sessionSilenceMinutes` and the output path, which the command needs, before it.
  - **`startNextFile`:** move `clearTranscript(els.transcriptFile)` and `currentFlow = "file"` after its `invoke` resolves. Keep marking the entry `transcribing` before (the queue shows the attempt), and `finishCurrentFile(false)` on refusal.

  Verify `node --check`, that `refused starts` now passes, and that all other GUI scenarios still pass.

## 3. Backlog and verification

- [ ] 3.1 Remove cluster B from `openspec/backlog.md`'s "Logic audit follow-ups", since this change picks it up. Verify B1 and B2 no longer appear there, and clusters C and D are unchanged.
- [ ] 3.2 Run `.venv/bin/python run_tests.py` with `TRANSCRIBER_TEST_SPEECH` set and a network that reaches GitHub, and verify it exits 0.
