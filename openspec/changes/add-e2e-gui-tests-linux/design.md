## Context

- `run_tests.py` runs `cargo test`, then every root `test_*.py` and `tests/test_*.py`. A new `tests/test_e2e_linux.py` joins automatically.
- `cargo build` in `src-tauri/` produces `target/debug/transcriber-gui`. `tauri-build` copies the bundle resources (`resources/model`, the licence files) next to it, and the app reads them from that directory in debug. `frontendDist` is `../src` with no `devUrl`, so the debug binary serves the real page under the real CSP. The staged sidecar lives in `src-tauri/binaries/transcriber-sidecar-x86_64-unknown-linux-gnu`.
- Once the page loads it invokes `get_platform` and `list_devices`. The latter spawns the sidecar with `--list-devices-json`. That is a deterministic "page loaded" signal visible to `strace`.
- `tauri-plugin-opener` opens URLs through the `open` 5.4.3 crate, which on Linux tries `xdg-open` first (`open-5.4.3/src/unix.rs`), then `gio open`.
- Tools present on this machine: `/usr/bin/WebKitWebDriver`, `strace`, `unshare`, `ip` (iproute2 6.17), `kernel.yama.ptrace_scope = 0`. `tauri-driver` is not installed yet; `cargo-tauri` 2.11.4 is.
- `tests/test_engine.py` already accepts `--engine <frozen binary>` and `TRANSCRIBER_TEST_SPEECH`, and skips speech without a recording.

## Goals / Non-Goals

**Goals:**
- Replace `add-manual-update-check` 4.2's manual checks with a repeatable local suite.
- Leave a small, reusable harness (start app, find element, click, read text) that `choose-model-folder` can extend.

**Non-Goals:**
- Running in CI. It would need Xvfb, a built sidecar and a `tauri-driver` install in the workflow; that's a later change.
- Windows or macOS end-to-end tests.
- Visual or screenshot assertions, which `test_gui.py` and Impeccable cover.
- File-transcription scenarios in the GUI. Native drag-drop and the file dialog aren't drivable through WebDriver.

## Decisions

### 1. `tauri-driver` + `WebKitWebDriver`, driven by a stdlib WebDriver client
The suite starts `tauri-driver` (port 4444, native driver on 4445) and creates a session with `{"capabilities": {"alwaysMatch": {"tauri:options": {"application": "<target/debug/transcriber-gui>"}}}}`. It speaks W3C WebDriver JSON over `urllib.request` using a handful of calls: new session, find element by CSS, click, element text, execute script, delete session. That's about 40 lines.

- *Alternative:* Selenium or WebdriverIO. This is the setup Tauri's docs show, but it adds a Python or Node dependency for six HTTP calls. Rejected.
- *Alternative:* Playwright against WebKitGTK. Playwright can't attach to an embedded webview. Rejected.

### 2. One process tree per scenario, torn down every time
Each scenario starts its own `tauri-driver` and app, and in `finally` deletes the session and kills the process group (`start_new_session=True`, then `os.killpg`). No state is shared, and a crashed scenario can't poison the next one. The debug build runs once, at suite start. If `cargo build` fails, the whole suite fails rather than skips, because a broken build is a real failure.

### 3. Offline: re-run the offline scenarios inside `unshare -rn`
The suite re-executes itself as `unshare -rn sh -c 'ip link set lo up && exec <python> tests/test_e2e_linux.py --inside-netns'`. In that network namespace:
- the loopback interface is brought up, so the test client can still reach `tauri-driver` on 127.0.0.1;
- the external network doesn't exist, so GitHub is unreachable by construction, not by a firewall rule;
- the Wayland/X11 and D-Bus sockets are Unix-domain filesystem sockets, so the window still opens.

Inside, it runs the offline update-check scenario, then `tests/test_engine.py --engine <staged sidecar>`, so the speech sample is transcribed with no network. The inner results are printed and folded into the outer report.

- *Alternative:* blocking the network with a firewall, or pointing `HTTPS_PROXY` at a dead port. The first needs root, and the second doesn't prove anything about code that ignores proxies. Rejected.

### 4. Startup: `strace` on the bare app, no WebDriver
The suite runs `strace -f -qq -e trace=connect,execve -o <log> target/debug/transcriber-gui`. It polls the log until an `execve` of the sidecar with `--list-devices-json` appears (60 s timeout), waits 3 s more, then kills the tree. It fails on any `connect(` line with `sa_family=AF_INET` or `AF_INET6`, to any address, loopback included, because a DNS lookup through `127.0.0.53` is a request. Unix-socket connects are allowed.

WebDriver is left out of this scenario on purpose: `tauri-driver` and the automation session open their own loopback TCP connections, which would pollute the trace.

- *Mutation check:* appending `checkForUpdate();` to `src/main.js` must make this scenario fail.

### 5. Download page: a recording `xdg-open` first on `PATH`
The suite writes a temp directory holding an executable `xdg-open` that appends `"$@"` to a file and exits 0, and puts it first on `PATH` for the app process. The scenario:
- online, when **Open download page** is showing, clicks it;
- otherwise calls `window.__TAURI__.core.invoke('open_releases_page')` through WebDriver's execute-script, which still exercises the real command, plugin and opener.

It then asserts the file holds exactly `https://github.com/saunite/transcriber/releases/latest`. It runs in the offline pass too, since opening a URL needs no network.

- *Mutation check:* removing `.plugin(tauri_plugin_opener::init())` from `main.rs` must make it fail.

### 6. Online verdict is real but tolerant of the release state
The scenario accepts any of the three real verdicts: up to date, available or no release. The expected one changes as releases are published, and the verdict logic itself is covered by the Rust unit tests. It fails on "Couldn't check". Before starting, a 5 s TCP connect to `api.github.com:443` decides reachability. If that fails, the scenario is skipped as "no route to GitHub", so an offline laptop can't turn the suite red.

### 7. Skips mirror the speech check
Checks happen in order: `sys.platform`, then a display variable, then `shutil.which` for `tauri-driver`, `WebKitWebDriver`, `strace`, `unshare` and `ip`, then the staged sidecar file. The first missing piece skips the whole suite, with one `SKIP` line per scenario naming it and the install hint (e.g. `cargo install tauri-driver --locked`), and exits 0.

## Risks / Trade-offs

- **The WebKit web process sandbox (bubblewrap) may refuse to start inside the user and network namespace.** → Verify in the first apply task. If it fails, set `WEBKIT_DISABLE_SANDBOX_THIS_IS_DANGEROUS=1` only for the app launched inside the test namespace, with a comment, and record it. The product is never started that way.
- **WebKit may open loopback TCP connections of its own at startup,** for example a web inspector or its network process. → Found on first run. Any such connection is investigated, and allowed only with a documented reason in the test.
- **Execute-script might be blocked by the page CSP.** WebKit automation normally bypasses it. → Verify in the first apply task. If it is blocked, the offline pass drives the download page only when the button is visible, and the scenario records that.
- **Timing and flakiness:** the first debug build and model-loading sidecars are slow. → Poll with generous timeouts (60 s), never fixed sleeps except the 3 s settle after the startup signal.
- **A graphical session is required, and windows flash on screen while the suite runs.** → Documented in the README. Headless Xvfb is left to the CI change.
- **Suite time grows by roughly a minute locally.** → Accepted. It still runs from the single test command.

## Migration Plan

- Additive. `add-manual-update-check` 4.2 is re-worded to "satisfied by `tests/test_e2e_linux.py`", and closed when the suite passes on this machine.
- Rollback: delete the test file. No product code changes.
