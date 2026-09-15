## 1. Engine

- [x] 1.1 In `transcriber.py`, make a live capture whose system source ends on its own print `❌ System audio capture ended unexpectedly` and return 1 (design.md Decision 1). That applies after `run_sys(...)` returns normally in `_run_dual_capture`, and after `capture_stream(...)` returns normally in `transcribe_live_simple`. `KeyboardInterrupt` keeps exit 0, and the transcript keeps everything written so far. In `test_dual_capture.py`:
  - change scenario 1's fake source to end with `KeyboardInterrupt` (a user stop), which still expects exit 0;
  - add a scenario whose source simply returns, expecting exit 1, the message, and the transcript lines written before it;
  - keep the silence scenario at exit 0 with "Auto-stop".

  Verify the tests pass, and that the new scenario fails with the exit-code change reverted.

  **Done 2026-09-15.**
  - **Design correction:** every `capture_stream` swallows `KeyboardInterrupt` and returns normally, so "returned normally" alone would have reported every user stop and silence stop as a lost source. `_request_stop()` now sets `_stop_requested` from the SIGINT handler and both silence checks, and `_source_ended_unexpectedly()` prints `❌ System audio capture ended unexpectedly` only when no stop was requested. The flag is reset at the start of `_run_dual_capture` and `transcribe_live_simple`. Both paths return 1 in that case, and the transcript is closed by the existing `finally`.
  - **Tests** in `test_dual_capture.py`:
    - scenario 1 already ends with `KeyboardInterrupt`, so it's unchanged and still expects exit 0;
    - `_feed(..., then=None)` returns normally;
    - new 3b: a source that returns gives exit 1, the message, and the `[SYS] hello` line still in the transcript;
    - new 3c: a `run_sys` that swallows `KeyboardInterrupt` like the real captures, with a 0.2 s silence timeout, gives exit 0, "Auto-stop", and no "ended unexpectedly";
    - the silence scenario (2) still gives exit 0.
  - **Ordering:** the lost-source message (`LOST_SOURCE_MESSAGE`) is printed as the session's very last line, after the stop summary, so the GUI can show it as the reason; 3b asserts it is the final line. A silence stop's own line is followed by the stop summary too, so the page recognises a silence stop from the engine log during the session, not from the last line (noted for 3.2).
  - **Verified:** the tests pass. With the lost-source report disabled, 3b fails; with the stop flag ignored, 3c fails.

- [x] 1.2 Add the hidden `--heartbeat` flag (`help=argparse.SUPPRESS`; Decision 2). `_drain_and_transcribe` prints `HEARTBEAT <TAG>` once per buffer that reaches its threshold, gated MIC chunks included, after the transcription attempt. `transcribe_live_simple` prints `HEARTBEAT SYS` per processed chunk. In `test_dual_capture.py`, check:
  - with the flag, a silent engine (`text=""`) still prints `HEARTBEAT SYS` and `HEARTBEAT MIC`;
  - without it, no `HEARTBEAT` appears;
  - `--help` doesn't mention it.

  Verify the tests pass, and that the heartbeat line doesn't match `test_transcript_line_format.py`'s transcript regex.

  **Done 2026-09-15.** `--heartbeat` is added with `help=argparse.SUPPRESS`. `_drain_and_transcribe` prints `HEARTBEAT <TAG>` after every buffer that reached its threshold, whether transcribed, gated or errored. `transcribe_live_simple` prints `HEARTBEAT SYS` after each processed chunk. Engine stdout is already line-buffered, so beats reach the GUI immediately.

  Tests:
  - `test_dual_capture.py` 3d: with a silent engine, the flag prints exactly `{HEARTBEAT SYS, HEARTBEAT MIC}`, and without it no `HEARTBEAT` line appears;
  - `transcriber.main()` with `--help` doesn't mention `--heartbeat`;
  - `test_transcript_line_format.py`'s must-not-match list gains `HEARTBEAT SYS` and `HEARTBEAT MIC`.

  `_args` gained `heartbeat=False`. All nine root test scripts pass.

## 2. Shell

- [x] 2.1 In `src-tauri/src/sidecar.rs`, add to `SidecarManager`: `live_generation`, `file_generation`, `file_running` and `last_line` (Decision 3). Add a pure `engine_busy(...)` used by both start commands for their refusal messages. It replaces the per-OS `pid_alive` file check. Pass each run's generation into `spawn_sidecar_events`, and ignore `Terminated` from an older generation. Unit tests:
  - `engine_busy` refuses a file run during live, a live run during a file run, and a live run during live, and allows each when idle;
  - a pure `on_terminated(state, generation, is_live, code)` helper, driving the event handler, returns "ignored" for a stale generation, "ended" (with code) for an unrequested exit of the current live run with code 0 or non-zero, "stopped" after a user stop, and "file done/failed" for file runs.

  Verify `cargo test` passes.

  **Done 2026-09-15.**
  - **`SidecarManager`** gains `file_running`, `live_generation`, `file_generation` and `last_line`.
  - **`engine_busy(sidecar, starting_live)`** gives the refusal for both start commands: live during live, live during a file run, a file run during live, and a file run during a file run. It replaces the per-OS `pid_alive` file check; the Windows branch used to refuse nothing.
  - **`on_terminated(sidecar, generation, is_live, code)`** returns `Ignored` for a stale generation, `LiveEnded(code)` when the current live run exits with `session_active` still set (any code), `LiveStopped` after a user stop, and `FileDone(ok)` for file runs, clearing the matching state.
  - **`spawn_sidecar_events`** now takes `(generation, is_live)`, and both commands bump their generation on spawn.
  - **Tests:** `one_engine_at_a_time_in_both_directions`, `a_live_exit_is_reported_whatever_the_code_unless_the_user_stopped_it` (codes 0, 1 and a signal), and `a_late_exit_from_an_older_run_changes_nothing` (live and file). `cargo test` passes.

- [x] 2.2 Emit `live-session-ended { code, lastLine }` for an unrequested exit of the current live run (any code), replacing `sidecar-crashed`. Emit `sidecar-heartbeat { tag }` for `HEARTBEAT` lines instead of `sidecar-log`, and exclude them from `last_line`. `build_live_session_args` gains `silence_timeout_secs` and always adds `--heartbeat --silence-timeout <n>`, and `start_live_session` takes `silence_timeout_minutes: u32`. Unit tests: the args carry `--heartbeat` and the converted seconds (10 → 600, 0 → 0), and a `HEARTBEAT MIC` line classifies as a heartbeat, not a transcript or log line. Verify `cargo test` passes, and that `grep -n sidecar-crashed src-tauri src` finds nothing.

  **Done 2026-09-15.**
  - **Events:** `live-session-ended { code, lastLine }` (camelCase) is emitted for `LiveEnded`, replacing `sidecar-crashed` in the shell. `HEARTBEAT <TAG>` lines emit `sidecar-heartbeat { tag }`, and `last_line` records transcript and log lines of the current live generation but never heartbeats.
  - **Arguments:** `build_live_session_args` takes `silence_timeout_minutes`, converts with `saturating_mul(60)`, and always adds `--heartbeat --silence-timeout <secs>`. `start_live_session` takes `silence_timeout_minutes: u32`.
  - **Tests:** `heartbeats_are_neither_transcript_nor_log_lines`, and `live_args_carry_the_heartbeat_and_the_silence_limit_in_seconds_from_minutes` (10 → 600, 0 → 0). The existing builder tests pass the new argument.
  - **Verified:** `cargo test` passes 29, and `cargo build` has no warnings. `grep sidecar-crashed` over `src-tauri/src` finds nothing; the page's listener in `src/main.js` is replaced in 3.2.

## 3. Frontend

- [x] 3.1 **Design the silence setting with the `impeccable` skill** (Decision 5) on the `src-index-html` surface, following `DESIGN.md`. Settle:
  - placement (Live panel);
  - control type (number of minutes vs a select of common values) and how "never" is expressed;
  - the copy for the field, the "Listening — no speech right now" status, the silence-stop notice and the unexpected-end notice.

  Record the decisions under this task. Verify with light and dark screenshots at 900×640 and 640×480, with no overflow.

  **Done 2026-09-15.** Impeccable, Operate mode, refining the rail with no new component.
  - **Placement:** the Live panel, after Microphone device and before System audio device override, because it applies only to live sessions and the override stays the last, discouraged field.
  - **Control:** "Stop after silence" as a number input with a `min` unit beside it, plus a hint: "Ends the session after this long without speech. 0 keeps listening until you press Stop." It mirrors the existing System audio device override (label, number, hint). A number, not a select of presets, because the user asked to *specify* the time. Off is 0, which the hint explains.
  - **Status copy:** "Listening — no speech right now" once a line has arrived, and "no speech yet" before that. Silence stop: "Stopped after N minutes of silence. The transcript so far is saved." Unexpected end: "Transcription ended unexpectedly: <engine's last line>".
  - **Stall detail:** rewritten as "The engine has reported nothing for Ns; it normally reports every 10s, speech or not. Check the engine log below, or stop and start again." This also removes the "raising and lowering the pens" copy (audit item D7).
  - **CSS:** only `.rail-input-unit` and `.rail-unit`, using existing tokens.

  **Verified** with Playwright under the app CSP and a simulated clock, in light and dark, at 900×640 and 640×480, with the field scrolled into view, in the quiet state (a line, then 60 s of heartbeats) and the stalled state (a line, then 36 s of nothing):
  - labels read as intended;
  - the stall detail shows only when stalled;
  - no rail overflow, no CSP violations or script errors.

- [x] 3.2 Implement in `src/index.html`, `src/style.css` and `src/main.js`:
  - the setting, stored under `transcriber-silence-minutes` (absent means 10), sent as `silenceTimeoutMinutes`;
  - `lastActivityAt` from lines and `sidecar-heartbeat`, `QUIET_MS = 2×` and `STALL_MS = 3×` chunk, and the `advancing → listening` return on quiet (Decision 4);
  - a `live-session-ended` handler with the silence-stop and unexpected-end notices, using the minutes the session was started with.

  Verify `node --check src/main.js`, and that the existing GUI tests pass after `test_exit_before_listening` moves from `sidecar-crashed` to `live-session-ended`.

  **Done 2026-09-15.**
  - **`index.html`:** the `#silence-minutes-input` field.
  - **`main.js`:**
    - `silenceMinutes()` clamps to 0–1440, and `initSilenceMinutes()` stores under `transcriber-silence-minutes` with the theme's try/catch (absent means 10);
    - `start_live_session` receives `silenceTimeoutMinutes`, captured in `sessionSilenceMinutes`;
    - `lastActivityAt` is set by lines and by the new `sidecar-heartbeat` listener (`markHeartbeat`, which also leaves "starting");
    - `tickInstrument` gives `penlift` past `STALL_MS` (30 s), `advancing` while a line is within `QUIET_MS` (20 s), and `listening` otherwise;
    - `silenceStopSeen` is set from the engine log's "minutes of silence detected", because the stop summary follows it, so it can't be the last line;
    - the `live-session-ended` handler shows the silence notice only for code 0 with `silenceStopSeen`, and the unexpected-end notice otherwise, replacing the `sidecar-crashed` listener.
  - **Tests:** `test_exit_before_listening` now emits `live-session-ended {code: 1, lastLine}`. `node --check` passes, and all 13 GUI scenarios pass, including command drift and CSP. `grep sidecar-crashed` over `src`, `src-tauri/src` and `tests` finds nothing.

- [x] 3.3 GUI scenarios in `tests/test_gui.py`, using Playwright's `page.clock` to advance time:
  - **quiet room:** after a line, heartbeats every 10 s for 3 minutes keep the status out of "stalled", and it reads the quiet label;
  - **stall:** after a line, no heartbeat or line for 31 s shows "stalled";
  - **silence stop:** `live-session-ended {code: 0, lastLine: "Auto-stop: 10.0 minutes of silence detected"}` shows the silence notice (no "unexpected" or error wording) and returns to idle;
  - **unexpected end:** `{code: 0, lastLine: "❌ System audio capture ended unexpectedly"}` and a non-zero code both show the unexpected-end notice with the line;
  - **setting:** the default sends 10, a changed value is sent, it persists across a reload, and "never" sends 0;
  - **refusal:** a `start_live_session` rejection with the busy message is shown.

  Verify they pass. Also verify the quiet-room scenario fails if heartbeats are ignored (temporarily), and the silence-stop scenario fails if `code 0` is ignored.

  **Done 2026-09-15.** `open_page(..., clock=True)` installs Playwright's clock. `test_engine_liveness` covers:
  - **quiet room:** a line, then 18 heartbeats 10 s apart (3 simulated minutes); the status is never "stalled" and ends on "Listening — no speech right now";
  - **stall:** then 31 s with nothing gives "stalled";
  - **silence stop:** the log line "Auto-stop: 10.0 minutes of silence detected", then `live-session-ended {code: 0, lastLine: "Stopped — …"}`, shows "Stopped after 10 minutes of silence. The transcript so far is saved." with no unexpected/error/fail wording, and returns to idle;
  - **unexpected ends:** `code 0` with the lost-source line, and `code 1`, each show "Transcription ended unexpectedly: <line>" and return to idle;
  - **setting:** 10 by default and sent as `silenceTimeoutMinutes: 10`; 25 is remembered after a reload; 0 is sent as 0;
  - **refusal:** the shell's busy message is shown.

  Passes, and all 14 GUI scenarios pass. With heartbeats ignored, it failed with "a quiet room read as stalled". With code-0 ends ignored (the old behaviour), it failed at the silence notice.

- [x] 3.4 Finish the Impeccable pass: the `impeccable-finish-reviewer` agent reviews the built setting and status copy (not an inline self-review), material fixes are applied and re-screenshotted once, and the verdict is recorded. Run `detect.mjs` once on the changed files, noting if it ran degraded. Update `DESIGN.md`, and `.impeccable/design.json` if a component changed. Verify `DESIGN.md` describes the setting and the quiet and stall states.

  **Done 2026-09-15.**
  - **Reviewer:** the `impeccable-finish-reviewer` agent returned **Verdict: fix**. The field matches the rail pattern and fits both sizes in both themes, quiet vs stalled read clearly apart, and the ceiling was reached. It said to keep a silence stop as neutral information and "no speech right now" distinct from "stalled". Its three material fixes were all applied:
    1. **The silence-stop note cleared itself after 8 s**, while the user was likely away. `showNote(..., { persist: true })` now skips the timeout for session-ended notes, and the reason also stays in `#run-detail` (now `role="status"`) while idle, until the next Start.
    2. **"Transcribing" showed before any speech** when a heartbeat came within 20 s of Start, because `lastLineAt` was seeded at start. The `advancing` branch is now gated on `sawFirstLine`.
    3. **Hint wording:** it now reads "Stops transcribing after this many minutes without speech. Set 0 to keep going until you press Stop transcribing.", in the button's own words.
  - **Found in the re-screenshot:** `.run-detail` is styled with the MIC-red fault colour, so the silence explanation showed red. `data-tone="info"` (neutral `ink-soft`) is now set for a clean end, and `"fault"` otherwise.
  - **Tests** added to `test_engine_liveness`:
    - a heartbeat 5 s after Start with no line reads "Listening — no speech yet";
    - the silence note is still there 60 simulated seconds later;
    - `#run-detail` shows the reason with `data-tone="info"`, and `"fault"` for unexpected ends.

    With the persistence removed the scenario fails; with the `sawFirstLine` gate removed it fails at "Listening — no speech yet". All 14 GUI scenarios pass.
  - **Re-screenshot:** captured once, light and dark, at 900 and 640, in the quiet, stalled and ended states with the field in view. The reason is neutral, with no overflow and no CSP or script errors.
  - **Detector:** `detect.mjs` ran once, degraded (no parser modules). Its one new advisory (`.rail-unit` at 0.75rem, off the type ramp) was fixed to 0.6875rem, back to the 16 older advisories.
  - **Docs:** `DESIGN.md` gains the Stop after silence field (Inputs), "Quiet room vs stall" and "Why a session ended" (Transport / Pens), and the persistent-note exception (Notes). `.impeccable/design.json` is unchanged: no new component or token, since the field reuses the rail field pattern and the tones reuse existing ink.

## 4. Docs

- [x] 4.1 README:
  - GUI: the stop-after-silence setting (default 10 minutes, never), and what happens when a session stops by itself;
  - CLI: `--silence-timeout` unchanged, and a lost audio source now exits non-zero.

  Verify both are present.

  **Done 2026-09-15.** README changes:
  - **"Download and run":** a new **When a live session stops by itself** paragraph covering the setting (default 10, 0 = until Stop), the silence notice, the unexpected-end notice, and the quiet vs stalled statuses.
  - **Complete Options, `--silence-timeout`:** a silence stop exits 0, and a lost system audio source prints `❌ System audio capture ended unexpectedly`, keeps the transcript and exits 1.

## 5. Verification

- [ ] 5.1 Rebuild the sidecar (`./.venv/bin/python build_sidecar.py`), since the shell now passes `--heartbeat`, which older staged sidecars reject. Then run `.venv/bin/python run_tests.py` with `TRANSCRIBER_TEST_SPEECH` set and a network that reaches GitHub. Verify it exits 0, and that every end-to-end scenario prints `PASS`.
- [ ] 5.2 **User check on Linux** (a local build):
  - with the setting at 1 minute, a live session in a quiet room shows the quiet status, not "stalled", then stops after about a minute with the silence notice, and the transcript file is kept;
  - restarting PipeWire (`systemctl --user restart pipewire pipewire-pulse`) during a session shows the unexpected-end notice;
  - pressing Start on the Live tab while a file is transcribing is refused with the busy message.
