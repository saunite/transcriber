## Why

Every GUI bug fixed recently was found by the user clicking through the app: the "Start Recording" wording, a file queue that let a second file start, SYS/MIC indicators stuck on "Armed", the missing refusal when a file is dropped during a live session. Each fix was then re-checked by hand. Nothing checks the engine end to end either: `.github/smoke-test.sh` only transcribes a silent clip, so no test confirms that real speech comes out as text.

The tests that do exist are not run by anything. The repo has 7 `test_*.py` scripts and 13 Rust unit tests, all passing on Linux today, but no command runs them together and no CI step runs them, so they help only when someone remembers to run them.

## What Changes

- **GUI behaviour tests without the desktop app.** The window is a web page (`frontendDist: "../src"`), and its only link to the app is `window.__TAURI__` (`withGlobalTauri: true`). The tests load `src/index.html` in headless Chromium through Playwright and inject a fake `window.__TAURI__` before `main.js` runs. The fake records `invoke` calls, returns canned data, and lets a test fire the app's events (`transcript-line`, `sidecar-crashed`, `file-transcription-complete`, `tauri://drag-drop`). Tests drive the real page and check what it sends and shows.
- **An engine test on real speech.** It transcribes a local English recording that the maintainer keeps outside the repository and never commits, so it is not redistributed. Its path is given to the test, and the words it says sit in a text file beside it. It checks the engine exits cleanly, writes a transcript whose lines have the expected `[start -> end] text` format, detects the language, and recognises most of the script's key words. A second test feeds undecodable input and expects a clean failure: exit 1, the "No decodable audio" message, no traceback and no output file. The engine is a parameter: `transcriber.py` from the venv by default, or a frozen sidecar binary when given one.
- **One command runs everything:** `cargo test` in `src-tauri/`, every existing `test_*.py`, and both new suites. It exits non-zero if anything fails.
- **A development dependency file** for Playwright, and a README section on setting up and running the tests.
- **Not in scope:**
  - **CI.** Running these in `release.yml` or a separate workflow is a natural follow-up, and the engine parameter is there to make it easy, but this change is local only.
  - **Real-app end-to-end testing** through `tauri-driver`/WebDriver, which is heavy on Linux and unsupported on macOS.
  - **Testing in WebKit.**
  - **Moving the existing root-level tests.**

**Observed while planning, deliberately not fixed here:** `desktop-gui`'s "Drop a video file" scenario says the GUI shows "the resulting transcript", but file mode writes segments only to the output file and prints none to stdout. So `sidecar.rs` emits no `transcript-line` events during a file run, and the File view stays empty. The GUI tests will not assert on this in either direction: asserting the transcript appears would fail, and asserting it doesn't would enshrine the gap. It needs its own change.

## Capabilities

### New Capabilities
- `automated-tests`: what the project's automated tests guarantee. One command runs every suite. GUI behaviour is verified against a fake app bridge, with no desktop app and no audio hardware. The engine is verified by transcribing a committed speech recording and by failing cleanly on undecodable input.

### Modified Capabilities
(none. The tests verify existing `desktop-gui` and `cli` requirements without changing them. The `desktop-gui` gap above is reported, not modified.)

## Impact

- **New files:** a test runner at the repo root; GUI tests with the fake-bridge script; engine tests; a development requirements file. The speech recording and its script stay outside the repository.
- **Changed:** `README.md`, since `documentation` requires it to cover setup and requirements files.
- **New development dependency:** Playwright for Python, plus a one-time Chromium download. Not needed by the app, its build or its users.
- **Unchanged:** application code, packaging, CI, and the existing tests, which stay where they are and run unmodified.
- **User action required:** point the engine test at a local recording and its script before the speech check runs. Without one it is reported as skipped.
- **Runtime:** GUI tests a few seconds, the engine speech test roughly 5–15 seconds (model load plus a short clip), the existing Python and Rust tests about as long as they take today.
