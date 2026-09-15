## 1. Fix

- [ ] 1.1 In `src/main.js` `applyFilters()`, keep hiding and highlighting lines in both lists as today, but count a hit only when the line matches, passes the **Show** filter, and is in the displayed chart's list (`els.chartLive.hidden ? els.transcriptFile : els.transcriptLive`). In `selectTab()`, call `applyFilters()` after switching. Verify `node --check src/main.js`, and that the existing GUI tests still pass.

## 2. Tests

- [ ] 2.1 Add a `chart search count` scenario to `tests/test_gui.py`, feeding lines through the fake bridge's `transcript-line` events.
  - **Pen filter:** a SYS line and a MIC line both containing "budget", "SYS only", and a search for "budget" give "1 line", with one `.trace-hit`.
  - **Other chart:** a match only in the file list, with the Live tab shown, gives "0 lines".
  - **Tab switch:** after switching to File, the count reflects the file list.
  - **Cleared search:** the count is hidden.

  A line reaches the file list when `currentFlow === "file"` (`src/main.js`, the `transcript-line` listener), so file-list lines are fed after dropping a file (`drop(page, "/media/one.mp4")`). Live lines are fed before that. Verify the scenario passes, and fails with the 1.1 change reverted.

## 3. Verification

- [ ] 3.1 Run `.venv/bin/python run_tests.py` with `TRANSCRIBER_TEST_SPEECH` set, and verify it exits 0.
