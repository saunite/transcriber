## 1. Engine

- [ ] 1.1 In `transcriber.py`, make a live capture whose system source ends on its own print `❌ System audio capture ended unexpectedly` and return 1 (design.md Decision 1). That applies after `run_sys(...)` returns normally in `_run_dual_capture`, and after `capture_stream(...)` returns normally in `transcribe_live_simple`. `KeyboardInterrupt` keeps exit 0, and the transcript keeps everything written so far. In `test_dual_capture.py`:
  - change scenario 1's fake source to end with `KeyboardInterrupt` (a user stop), which still expects exit 0;
  - add a scenario whose source simply returns, expecting exit 1, the message, and the transcript lines written before it;
  - keep the silence scenario at exit 0 with "Auto-stop".

  Verify the tests pass, and that the new scenario fails with the exit-code change reverted.
- [ ] 1.2 Add the hidden `--heartbeat` flag (`help=argparse.SUPPRESS`; Decision 2). `_drain_and_transcribe` prints `HEARTBEAT <TAG>` once per buffer that reaches its threshold, gated MIC chunks included, after the transcription attempt. `transcribe_live_simple` prints `HEARTBEAT SYS` per processed chunk. In `test_dual_capture.py`, check:
  - with the flag, a silent engine (`text=""`) still prints `HEARTBEAT SYS` and `HEARTBEAT MIC`;
  - without it, no `HEARTBEAT` appears;
  - `--help` doesn't mention it.

  Verify the tests pass, and that the heartbeat line doesn't match `test_transcript_line_format.py`'s transcript regex.

## 2. Shell

- [ ] 2.1 In `src-tauri/src/sidecar.rs`, add to `SidecarManager`: `live_generation`, `file_generation`, `file_running` and `last_line` (Decision 3). Add a pure `engine_busy(...)` used by both start commands for their refusal messages. It replaces the per-OS `pid_alive` file check. Pass each run's generation into `spawn_sidecar_events`, and ignore `Terminated` from an older generation. Unit tests:
  - `engine_busy` refuses a file run during live, a live run during a file run, and a live run during live, and allows each when idle;
  - a pure `on_terminated(state, generation, is_live, code)` helper, driving the event handler, returns "ignored" for a stale generation, "ended" (with code) for an unrequested exit of the current live run with code 0 or non-zero, "stopped" after a user stop, and "file done/failed" for file runs.

  Verify `cargo test` passes.
- [ ] 2.2 Emit `live-session-ended { code, lastLine }` for an unrequested exit of the current live run (any code), replacing `sidecar-crashed`. Emit `sidecar-heartbeat { tag }` for `HEARTBEAT` lines instead of `sidecar-log`, and exclude them from `last_line`. `build_live_session_args` gains `silence_timeout_secs` and always adds `--heartbeat --silence-timeout <n>`, and `start_live_session` takes `silence_timeout_minutes: u32`. Unit tests: the args carry `--heartbeat` and the converted seconds (10 → 600, 0 → 0), and a `HEARTBEAT MIC` line classifies as a heartbeat, not a transcript or log line. Verify `cargo test` passes, and that `grep -n sidecar-crashed src-tauri src` finds nothing.

## 3. Frontend

- [ ] 3.1 **Design the silence setting with the `impeccable` skill** (Decision 5) on the `src-index-html` surface, following `DESIGN.md`. Settle:
  - placement (Live panel);
  - control type (number of minutes vs a select of common values) and how "never" is expressed;
  - the copy for the field, the "Listening — no speech right now" status, the silence-stop notice and the unexpected-end notice.

  Record the decisions under this task. Verify with light and dark screenshots at 900×640 and 640×480, with no overflow.
- [ ] 3.2 Implement in `src/index.html`, `src/style.css` and `src/main.js`:
  - the setting, stored under `transcriber-silence-minutes` (absent means 10), sent as `silenceTimeoutMinutes`;
  - `lastActivityAt` from lines and `sidecar-heartbeat`, `QUIET_MS = 2×` and `STALL_MS = 3×` chunk, and the `advancing → listening` return on quiet (Decision 4);
  - a `live-session-ended` handler with the silence-stop and unexpected-end notices, using the minutes the session was started with.

  Verify `node --check src/main.js`, and that the existing GUI tests pass after `test_exit_before_listening` moves from `sidecar-crashed` to `live-session-ended`.
- [ ] 3.3 GUI scenarios in `tests/test_gui.py`, using Playwright's `page.clock` to advance time:
  - **quiet room:** after a line, heartbeats every 10 s for 3 minutes keep the status out of "stalled", and it reads the quiet label;
  - **stall:** after a line, no heartbeat or line for 31 s shows "stalled";
  - **silence stop:** `live-session-ended {code: 0, lastLine: "Auto-stop: 10.0 minutes of silence detected"}` shows the silence notice (no "unexpected" or error wording) and returns to idle;
  - **unexpected end:** `{code: 0, lastLine: "❌ System audio capture ended unexpectedly"}` and a non-zero code both show the unexpected-end notice with the line;
  - **setting:** the default sends 10, a changed value is sent, it persists across a reload, and "never" sends 0;
  - **refusal:** a `start_live_session` rejection with the busy message is shown.

  Verify they pass. Also verify the quiet-room scenario fails if heartbeats are ignored (temporarily), and the silence-stop scenario fails if `code 0` is ignored.
- [ ] 3.4 Finish the Impeccable pass: the `impeccable-finish-reviewer` agent reviews the built setting and status copy (not an inline self-review), material fixes are applied and re-screenshotted once, and the verdict is recorded. Run `detect.mjs` once on the changed files, noting if it ran degraded. Update `DESIGN.md`, and `.impeccable/design.json` if a component changed. Verify `DESIGN.md` describes the setting and the quiet and stall states.

## 4. Docs

- [ ] 4.1 README:
  - GUI: the stop-after-silence setting (default 10 minutes, never), and what happens when a session stops by itself;
  - CLI: `--silence-timeout` unchanged, and a lost audio source now exits non-zero.

  Verify both are present.

## 5. Verification

- [ ] 5.1 Rebuild the sidecar (`./.venv/bin/python build_sidecar.py`), since the shell now passes `--heartbeat`, which older staged sidecars reject. Then run `.venv/bin/python run_tests.py` with `TRANSCRIBER_TEST_SPEECH` set and a network that reaches GitHub. Verify it exits 0, and that every end-to-end scenario prints `PASS`.
- [ ] 5.2 **User check on Linux** (a local build):
  - with the setting at 1 minute, a live session in a quiet room shows the quiet status, not "stalled", then stops after about a minute with the silence notice, and the transcript file is kept;
  - restarting PipeWire (`systemctl --user restart pipewire pipewire-pulse`) during a session shows the unexpected-end notice;
  - pressing Start on the Live tab while a file is transcribing is refused with the busy message.
