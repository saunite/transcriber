## 1. Harness

- [ ] 1.1 Install `tauri-driver` (`cargo install tauri-driver --locked`). Confirm the debug build's layout by running `cargo build` in `src-tauri/`, checking that `target/debug/` holds `transcriber-gui`, the `transcriber-sidecar` binary and `resources/model/model.bin`. Record the tool versions and the layout under this task. Verify with a throwaway script that starts `tauri-driver`, opens a session on the debug app and reads `#update-check-btn`'s text ("Check for updates"). In the same spike, record:
  - whether execute-script can call `window.__TAURI__.core.invoke` (design.md Risks);
  - whether the app window opens inside `unshare -rn` with `lo` up.

  Adjust design.md if either fails.
- [ ] 1.2 Create `tests/test_e2e_linux.py` with:
  - the environment checks and skip reporting (Decision 7);
  - the one-time `cargo build`;
  - the stdlib WebDriver client (Decision 1);
  - per-scenario process-group start and teardown (Decision 2);
  - the recording `xdg-open` shim (Decision 5).

  Verify the suite runs and skips cleanly with each of these: `PATH` stripped of `tauri-driver`, `WAYLAND_DISPLAY` and `DISPLAY` unset, and on this machine with everything present. With a missing tool, each scenario prints `SKIP` with its install hint and the exit code is 0.

## 2. Scenarios

- [ ] 2.1 **Update check online** (Decision 6): skip when `api.github.com:443` is unreachable. Otherwise click `#update-check-btn` and wait for `#update-result` to be filled. Pass on up to date, available or no release, and fail on "Couldn't check". Verify it passes here. Also verify it fails when `fetch_latest` temporarily points at an unroutable host, then revert.
- [ ] 2.2 **Offline pass** (Decision 3): re-exec inside `unshare -rn` with `lo` up. Assert the update check shows "Couldn't check for updates". Run `tests/test_engine.py --engine <staged sidecar>` there, with `TRANSCRIBER_TEST_SPEECH` passed through. Fold both results into the outer report. Verify both pass here with the recording set, and that the engine result reads `SKIP` for speech when the variable is unset.
- [ ] 2.3 **No request at startup** (Decision 4): use `strace -f` until the sidecar's `--list-devices-json` execve plus 3 s, and fail on any `AF_INET`/`AF_INET6` `connect`. Verify it passes. Also verify it fails with the offending line when `checkForUpdate();` is temporarily appended to `src/main.js`, then revert. Record any WebKit loopback connection found and its justification.
- [ ] 2.4 **Download page** (Decision 5), in both passes: drive **Open download page** when it's shown, and otherwise call `open_releases_page` through execute-script. Assert the shim recorded exactly `https://github.com/saunite/transcriber/releases/latest`. Verify it passes. Also verify it fails when `.plugin(tauri_plugin_opener::init())` is temporarily removed from `src-tauri/src/main.rs`, then revert.

## 3. Docs and hand-off

- [ ] 3.1 README Tests section:
  - the end-to-end suite, its Linux, display and graphical-session requirement, and its one-time setup (`cargo install tauri-driver --locked`, the distribution's WebKitWebDriver package, `strace`);
  - that windows open while it runs;
  - how it skips.

  Add a line for it in the suites table. Verify the section and table entry exist.
- [ ] 3.2 In `openspec/changes/add-manual-update-check/tasks.md`, re-word 4.2 so it is satisfied by `tests/test_e2e_linux.py` (online verdict, offline verdict and transcription, no startup connection). Record the passing run there. Leave 4.3 open and unchanged. Verify 4.2 names the suite and its scenarios.

## 4. Verification

- [ ] 4.1 Run `.venv/bin/python run_tests.py` with `TRANSCRIBER_TEST_SPEECH` set. Verify it exits 0 and the summary lists `tests/test_e2e_linux.py` as passed, with every scenario printed as `PASS`, not `SKIP`.
