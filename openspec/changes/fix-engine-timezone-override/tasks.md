## 1. Reproduce before changing anything

- [ ] 1.1 Compare the three clocks in the built app. With a debug or built app running, record:
  - the page's reading: `new Date().toString()`, `new Date().getTimezoneOffset()` and `Intl.DateTimeFormat().resolvedOptions().timeZone`, taken in the webview (the e2e harness can evaluate these, or the app's engine log view);
  - the engine's reading: start a live session with `--actual-time` (the app always does) and read the first line's stamp, plus `time.tzname` and `datetime.now().astimezone().utcoffset()` from the same engine build;
  - the system's reading: `date`, `timedatectl`, `/etc/localtime`, and whether `TZ` is exported in the app's environment (`tr '\\0' '\\n' < /proc/<app pid>/environ | grep -i '^TZ='`).

  Record all three under this task, with the machine's zone. Verify whether they agree; if one differs, name which and by how much.

- [ ] 1.2 Decide the cause from 1.1 and write it down here before touching code:
  - **the engine ignoring an exported `TZ`** (its `os.environ.pop("TZ", None)` at import), which shows up as the engine differing while the page matches the system;
  - **stale timezone rules in the page's runtime**, which shows up as the page differing (on this machine, one hour ahead in September, since `America/Mexico_City` dropped daylight saving in 2022);
  - **something else**, in which case record what and stop to re-plan, since the proposal's expected fix would no longer apply.

## 2. Test, then fix

- [ ] 2.1 Add a check to `test_transcript_line_format.py` (or a new root test if it reads better) that runs `transcriber.py --help`-style startup in a subprocess with `TZ` set to a zone far from this machine's (for example `TZ=Pacific/Kiritimati`) and asserts the engine's own wall-clock stamp is in that zone: compare `transcriber._wall_clock_stamp()` printed by the subprocess against `datetime.now(ZoneInfo("Pacific/Kiritimati"))` in the parent, allowing a few seconds. Skip on Windows, where the Cygwin fallback applies.

  Verify it **fails** against today's engine, which drops `TZ` at import and stamps in the machine's own zone.

- [ ] 2.2 Apply the fix 1.2 chose. If it is the expected one: make the `TZ` deletion conditional on Windows in `transcriber.py`, keeping the comment's explanation of the Cygwin case, so Linux and macOS honour `TZ`.

  Verify 2.1 passes, `test_transcript_line_format.py` and `test_dual_capture.py` still pass, and a run with no `TZ` set stamps exactly as before.

- [ ] 2.3 If 1.1 showed the page's runtime is the one with stale rules, record what would fix it (a newer timezone database in the packaged runtime) and whether it is ours to fix. Do not change `src/main.js` to compensate for a wrong clock; a shifted stamp would then be wrong in the other direction on a correct machine.

## 3. Verification

- [ ] 3.1 Repeat 1.1's comparison on the fixed build and verify the three readings agree.

- [ ] 3.2 Remove "An hour's gap between GUI and engine timestamps" from `openspec/backlog.md`'s parked changes, recording the cause found in 1.2. If 2.3 applies, park that follow-up instead. Verify the item no longer appears.

- [ ] 3.3 Run `.venv/bin/python run_tests.py` with `TRANSCRIBER_TEST_SPEECH` set and a network that reaches GitHub, and verify it exits 0.

- [ ] 3.4 **Manual check, by the user, on a rebuilt sidecar:** run a short live session and confirm the transcript's file name and its first line agree on the hour. Nothing needs to be kept.
