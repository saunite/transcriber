## 1. Reproduce before changing anything

- [x] 1.1 Compare the three clocks in the built app. With a debug or built app running, record:
  - the page's reading: `new Date().toString()`, `new Date().getTimezoneOffset()` and `Intl.DateTimeFormat().resolvedOptions().timeZone`, taken in the webview (the e2e harness can evaluate these, or the app's engine log view);
  - the engine's reading: start a live session with `--actual-time` (the app always does) and read the first line's stamp, plus `time.tzname` and `datetime.now().astimezone().utcoffset()` from the same engine build;
  - the system's reading: `date`, `timedatectl`, `/etc/localtime`, and whether `TZ` is exported in the app's environment (`tr '\\0' '\\n' < /proc/<app pid>/environ | grep -i '^TZ='`).

  Record all three under this task, with the machine's zone. Verify whether they agree; if one differs, name which and by how much.

  **Done 2026-09-16.** Machine zone `America/Mexico_City` (CST, -0600), `TZ` unset. All three agree:
  - **system:** `2026-09-16 13:48:26 CST (-0600)`;
  - **webview** (read in the real app through the e2e harness): `Wed Sep 16 2026 13:48:26 GMT-0600 (Central Standard Time)`, `getTimezoneOffset() = 360`, `Intl` zone `America/Mexico_City`, and the filename stamp it would build, `20260916_134826`, matches `date` to the second;
  - **engine** (the staged sidecar, file mode with `--actual-time`, which reads the same clock as a live session without capturing anything): `[2026-09-16 13:47:24.270 -> ...]`, taken a minute earlier.

  **The gap does not reproduce, and the suspected cause is disproven.** The engine honours `TZ`: with `TZ=Pacific/Kiritimati` the frozen sidecar stamped `2026-09-17 09:47:28` and the source engine `2026-09-17 09:47:49`, both matching Python in that zone.

  **Why the suspected defect is not one.** `os.environ.pop("TZ", None)` cannot change the zone on Linux, because glibc caches it and only re-reads on `tzset()`:

  ```
  before pop:  09:47 ('+14', '+14')
  after  pop:  09:47 ('+14', '+14')   <- no tzset(), so the cached zone stands
  after tzset: 13:47 ('CST', 'CST')
  ```

- [x] 1.2 Decide the cause from 1.1 and write it down here before touching code:
  - **the engine ignoring an exported `TZ`** (its `os.environ.pop("TZ", None)` at import), which shows up as the engine differing while the page matches the system;
  - **stale timezone rules in the page's runtime**, which shows up as the page differing (on this machine, one hour ahead in September, since `America/Mexico_City` dropped daylight saving in 2022);
  - **something else**, in which case record what and stop to re-plan, since the proposal's expected fix would no longer apply.

  **Done 2026-09-16: "something else".** Neither candidate survives. The engine does not ignore `TZ`, and the page's runtime is not carrying stale rules: it reports `America/Mexico_City` with the post-2022 offset, agreeing with the system to the second.

  **What is left, unproven:** a long-running app process holding the zone it started with. A webview resolves the timezone once and keeps it, so an app left open across a system timezone change or a `tzdata` update would keep the old offset while each freshly spawned engine reads the new one, which is exactly a one-hour gap where daylight-saving rules are involved. That fits a symptom seen once and never since, but it cannot be reproduced without changing the machine's timezone under a running app.

  **A real finding, not the reported one:** the `os.environ.pop("TZ", None)` line is ineffective on Linux, so the Cygwin behaviour it was added for may not work as believed on Windows either. That needs a Windows session to check.

  Per this task, the apply stopped here to re-plan rather than applying a fix for a defect that does not exist.

## 2. Make a recurrence diagnose itself

- [x] 2.1 Add a root `test_engine_timezone.py` that runs the engine in a subprocess with `TZ` set to a zone far from this machine's (`Pacific/Kiritimati`) and asserts:
  - its `--actual-time` stamp is in that zone, within a few seconds of `datetime.now(ZoneInfo("Pacific/Kiritimati"))` in the parent;
  - with `TZ` unset, the stamp matches the machine's own local time.

  It pins today's correct behaviour rather than a fix, so it passes as written; record that. Skip on Windows, where the Cygwin fallback applies. Verify it fails if `time.tzset()` is called after the `TZ` deletion in `transcriber.py`, which is what the suspected defect would have looked like.

  **Done 2026-09-16.** Three checks, all passing as written, since they pin behaviour that is already correct:
  - `TZ=Pacific/Kiritimati -> 2026-09-17 09:56:02 (+14)`;
  - `no TZ -> 2026-09-16 13:56:02 (CST)`;
  - the summary line reads `CST (-06:00)`.

  It needs no model or audio: the stamp comes from `_wall_clock_stamp()`, the same helper every live line uses, run in a subprocess with a controlled environment. It skips on Windows.

  **Mutation:** adding `time.tzset()` after the `TZ` deletion, which is exactly what the suspected defect would have been, fails the first check: "with TZ=Pacific/Kiritimati the engine stamped 2026-09-16 13:56:27 (CST), but that zone reads 2026-09-17 09:56:27: 20.0 hours out". The file was restored afterwards.

- [x] 2.2 In `transcriber.py`, add the resolved timezone and offset to the compact summary line a live session prints, so the app's engine log records what the engine believed local time to be. Keep it to that one line; the output stays three lines.

  Verify `test_dual_capture.py` still passes, and extend 2.1 to assert the line names the zone the engine actually used.

  **Done 2026-09-16.** A new `_timezone_summary()` returns the zone abbreviation and offset (`CST (-06:00)`, or `+14 (+14:00)` under `TZ=Pacific/Kiritimati`), and the live session's second line now ends with "timestamps in <that>". The output is still three lines.

  **Verified:** `test_dual_capture.py` passes, and 2.1's third check compares the summary against the zone the engine resolved in a separate subprocess, so the line cannot drift from the stamps.

## 3. Backlog and verification

- [x] 3.1 `openspec/backlog.md`:
  - remove "An hour's gap between GUI and engine timestamps" from the parked changes, since it was investigated;
  - add, under "Waiting on a Windows session", that `os.environ.pop("TZ", None)` is ineffective on Linux (glibc caches the zone until `tzset()`), so the Cygwin fix it was written for may never have worked on Windows either, and `fix-cygwin-tz-override-bug`'s scenario should be re-checked there.

  Verify both by reading the file.

  **Done 2026-09-16.** The hour-gap item is gone from "Parked changes" (the phrase appears nowhere in the file), and "Waiting on a Windows session" now carries the `TZ` question, with the Linux measurement and the concrete check to run from a Cygwin shell.

- [x] 3.2 Run `.venv/bin/python run_tests.py` with `TRANSCRIBER_TEST_SPEECH` set and a network that reaches GitHub, and verify it exits 0.

  **Done 2026-09-16.** With `TRANSCRIBER_TEST_SPEECH` set and GitHub reachable: 18/18 suites passed, exit 0, nothing skipped. That is one more suite than before (`test_engine_timezone.py`).
