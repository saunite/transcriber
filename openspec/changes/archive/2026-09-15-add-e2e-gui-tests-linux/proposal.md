## Why

The automated tests check each layer on its own:
- `cargo test` covers pure Rust;
- `tests/test_gui.py` covers the page in Chromium against a fake `window.__TAURI__`;
- `tests/test_engine.py` covers the engine.

Nothing runs the built application, so wiring bugs between the layers pass every suite. Examples: a command not registered, a plugin not initialised, a capability permission missing, a request fired at startup. That is why `add-manual-update-check` task 4.2 is a manual user check, and why `choose-model-folder` 5.2 will be one too. Linux already has the tools to close the gap: `WebKitWebDriver` and `strace` are installed, and `unshare` can run a process with no network.

## What Changes

- **New test suite `tests/test_e2e_linux.py`.** It builds the debug app, starts it through `tauri-driver` (Tauri's official WebDriver bridge over `WebKitWebDriver`), and drives the real window. `run_tests.py` picks it up with the other `tests/test_*.py` suites. Scenarios:
  - **Update check online:** clicking **Check for updates** in the real app gives a real verdict: up to date, available, or no release. It must not give "Couldn't check". This scenario is skipped, with the reason, when GitHub isn't reachable from the machine.
  - **Update check offline:** the whole run happens inside a network-less namespace (`unshare -rn`), and the app shows "Couldn't check for updates". In the same namespace, the engine suite transcribes the speech sample with the staged frozen sidecar, proving transcription needs no network.
  - **No request at startup:** the app is launched under `strace -f` until its page has loaded and asked for the device list, plus a settle time. The run fails on any IPv4 or IPv6 `connect`, from the app, its web process or the sidecar.
  - **Open download page:** a fake `xdg-open` placed first on `PATH` records its argument. The test asserts it received exactly `https://github.com/saunite/transcriber/releases/latest`. In the online run it's driven through the real button; when no newer version is shown, the page's own invoke path is called directly.
- **Skips instead of failures when the environment can't run it.** The suite reports each scenario as skipped, with how to fix it, when:
  - the machine isn't Linux;
  - there's no display (`WAYLAND_DISPLAY`/`DISPLAY`);
  - `tauri-driver`, `WebKitWebDriver`, `strace` or `unshare` is missing;
  - the sidecar binary isn't staged.

  That matches how the speech check skips without a recording.
- **A minimal WebDriver client using only the standard library** (`urllib`, W3C JSON protocol), so there is no Selenium dependency.
- **README:** one-time setup (`cargo install tauri-driver --locked`), and how to run the suite.
- **Hand-offs:**
  - `add-manual-update-check` 4.2 is re-worded to be satisfied by this suite, and its result recorded there.
  - 4.3 (a newer release against the real API) stays manual until a release exists. No test-only update URL is added.
  - `choose-model-folder` can later add scenarios to this suite.
- **Not in this change:** Windows end-to-end tests (`msedgedriver`), CI or release-workflow integration, and macOS (`tauri-driver` has no macOS support).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `automated-tests`: adds a requirement that the built desktop application is tested end to end on Linux. It covers the update check online and offline, no network request at startup, the fixed releases URL, offline transcription, and skip reporting when the environment can't run it.

## Impact

- **New file:** `tests/test_e2e_linux.py`, holding the suite, the small WebDriver client and the `xdg-open` shim written into a temp directory.
- **`run_tests.py`:** no change expected, since it already globs `tests/test_*.py`. Its first run builds the debug app (`cargo build` in `src-tauri/`), which adds a few minutes once and seconds after that.
- **Developer prerequisites:** `tauri-driver` (cargo), `WebKitWebDriver` (distribution `webkit2gtk` driver package), `strace`, `util-linux` `unshare` and `iproute2` `ip`. A graphical session is needed.
- **No app code changes and no new runtime dependencies.** The product is untouched.
- **`openspec/changes/add-manual-update-check/tasks.md`:** task 4.2's wording and completion record.
