## 1. Harness

- [x] 1.1 Install `tauri-driver` (`cargo install tauri-driver --locked`). Confirm the debug build's layout by running `cargo build` in `src-tauri/`, checking that `target/debug/` holds `transcriber-gui`, the `transcriber-sidecar` binary and `resources/model/model.bin`. Record the tool versions and the layout under this task. Verify with a throwaway script that starts `tauri-driver`, opens a session on the debug app and reads `#update-check-btn`'s text ("Check for updates"). In the same spike, record:
  - whether execute-script can call `window.__TAURI__.core.invoke` (design.md Risks);
  - whether the app window opens inside `unshare -rn` with `lo` up.

  Adjust design.md if either fails.

  **Done 2026-09-15.**
  - **Versions:** `tauri-driver` 2.0.6, installed to `~/.cargo/bin`, which isn't on every shell's `PATH`, so the suite also looks there. `WebKitWebDriver` and WebKitGTK are 2.52.5; on Fedora the driver ships in `webkitgtk6.0`, while the app links `webkit2gtk-4.1`.
  - **Build layout:** `cargo build` gives `target/debug/transcriber-gui`, with `transcriber-sidecar` and `resources/model/model.bin` beside it.
  - **Spike:** a session on the debug app read `#update-check-btn` as "Check for updates". Execute-script calling `window.__TAURI__.core.invoke('get_platform')` returned `linux`, so the page CSP doesn't block it.
  - **Network namespace:** the same spike ran inside `unshare -rn` with `lo` up. The window opened with the WebKit sandbox untouched; the only noise was a harmless "can't connect to a11y bus" warning.
  - **Not in the plan: native input is unsupported.** Element click, send keys, and key and pointer actions all return `unsupported operation`, inside and outside the tool sandbox, and with `GDK_BACKEND=x11` (tauri-apps/tauri#6541). With the user's agreement, clicks are made from script on the real element, and design.md Decision 1 records it.

- [x] 1.2 Create `tests/test_e2e_linux.py` with:
  - the environment checks and skip reporting (Decision 7);
  - the one-time `cargo build`;
  - the stdlib WebDriver client (Decision 1);
  - per-scenario process-group start and teardown (Decision 2);
  - the recording `xdg-open` shim (Decision 5).

  Verify the suite runs and skips cleanly with each of these: `PATH` stripped of `tauri-driver`, `WAYLAND_DISPLAY` and `DISPLAY` unset, and on this machine with everything present. With a missing tool, each scenario prints `SKIP` with its install hint and the exit code is 0.

  **Done 2026-09-15.** `tests/test_e2e_linux.py` adds the environment checks, the one-time `cargo build`, the stdlib WebDriver client (`App`), per-scenario process-group teardown, the `xdg-open` shim, and the `unshare -rn` re-exec. Verified skips, each printing `SKIP` for every scenario and exiting 0:
  - no display, via `env -u WAYLAND_DISPLAY -u DISPLAY`: "no graphical display…";
  - `PATH=/usr/bin:/bin` and a `HOME` without `.cargo/bin`: "tauri-driver not found: cargo install tauri-driver --locked".

  With everything present the suite ran, and no `transcriber-gui`, `WebKitWebDriver` or `tauri-driver` process was left afterwards.

## 2. Scenarios

- [ ] 2.1 **Update check online** (Decision 6): skip when `api.github.com:443` is unreachable. Otherwise click `#update-check-btn` and wait for `#update-result` to be filled. Pass on up to date, available or no release, and fail on "Couldn't check". Verify it passes here. Also verify it fails when `fetch_latest` temporarily points at an unroutable host, then revert.
- [x] 2.2 **Offline pass** (Decision 3): re-exec inside `unshare -rn` with `lo` up. Assert the update check shows "Couldn't check for updates". Run `tests/test_engine.py --engine <staged sidecar>` there, with `TRANSCRIBER_TEST_SPEECH` passed through. Fold both results into the outer report. Verify both pass here with the recording set, and that the engine result reads `SKIP` for speech when the variable is unset.

  **Done 2026-09-15.** The suite re-runs itself as `unshare -rn sh -c 'ip link set lo up && exec "$@"' … --inside-netns`, which runs three scenarios:
  - **update check offline:** "Couldn't check for updates. Check your connection and try again.";
  - **download page offline:** passes;
  - **engine offline:** runs `tests/test_engine.py --engine src-tauri/binaries/transcriber-sidecar-x86_64-unknown-linux-gnu`.

  The inner exit code is folded into the suite's. With `TRANSCRIBER_TEST_SPEECH` set, the engine result was "PASS speech sample transcribes; PASS undecodable input fails cleanly". Without it: "SKIP speech sample: no recording set…; PASS undecodable input fails cleanly".

- [x] 2.3 **No request at startup** (Decision 4): use `strace -f` until the sidecar's `--list-devices-json` execve plus 3 s, and fail on any `AF_INET`/`AF_INET6` `connect`. Verify it passes. Also verify it fails with the offending line when `checkForUpdate();` is temporarily appended to `src/main.js`, then revert. Record any WebKit loopback connection found and its justification.

  **Done 2026-09-15.** Passes. With the unchanged app, the trace showed no IPv4/IPv6 connect at all, so no WebKit loopback connection needed an exception. With `checkForUpdate();` appended to `src/main.js` and the app rebuilt (the frontend is embedded at compile time), it failed with `connect(43, {sa_family=AF_INET, sin_port=htons(443), sin_addr=inet_addr("140.82.112.5")}…`. Reverted and rebuilt.

- [x] 2.4 **Download page** (Decision 5), in both passes: drive **Open download page** when it's shown, and otherwise call `open_releases_page` through execute-script. Assert the shim recorded exactly `https://github.com/saunite/transcriber/releases/latest`. Verify it passes. Also verify it fails when `.plugin(tauri_plugin_opener::init())` is temporarily removed from `src-tauri/src/main.rs`, then revert.

  **Done 2026-09-15.** `test_download_page` calls `open_releases_page` through execute-script, in both passes. `test_update_check_online` clicks **Open download page** when a newer version is shown. Both assert the shim log is exactly `[RELEASES_URL]`, and pass. With `.plugin(tauri_plugin_opener::init())` commented out and the app rebuilt, the command never answers, and the scenario fails with "page script never finished within …s (a command that never answers?)". `run_async` now turns that socket timeout into this message. Reverted and rebuilt.

## 3. Docs and hand-off

- [x] 3.1 README Tests section:
  - the end-to-end suite, its Linux, display and graphical-session requirement, and its one-time setup (`cargo install tauri-driver --locked`, the distribution's WebKitWebDriver package, `strace`);
  - that windows open while it runs;
  - how it skips.

  Add a line for it in the suites table. Verify the section and table entry exist.

  **Done 2026-09-15.** README "Running the tests" gains a `tests/test_e2e_linux.py` row in the suites table, and a paragraph covering: Linux and a graphical session only, windows opening during the run, the staged sidecar, one-time installs (`cargo install tauri-driver --locked`, plus Fedora `webkitgtk6.0 strace` or Debian/Ubuntu `webkit2gtk-driver strace`), how it skips (including the online check behind a VPN), and the script-click limitation.

- [ ] 3.2 In `openspec/changes/add-manual-update-check/tasks.md`, re-word 4.2 so it is satisfied by `tests/test_e2e_linux.py` (online verdict, offline verdict and transcription, no startup connection). Record the passing run there. Leave 4.3 open and unchanged. Verify 4.2 names the suite and its scenarios.

## 4. Verification

- [ ] 4.1 Run `.venv/bin/python run_tests.py` with `TRANSCRIBER_TEST_SPEECH` set. Verify it exits 0 and the summary lists `tests/test_e2e_linux.py` as passed, with every scenario printed as `PASS`, not `SKIP`.
