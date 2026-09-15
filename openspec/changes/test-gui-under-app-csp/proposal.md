## Why

`harden-webview-csp-and-tls` gave the app window a Content Security Policy (`default-src 'self'; connect-src ipc: http://ipc.localhost`). Its only automated guard reads that string out of `tauri.conf.json`; whether the policy blocks injected script and lets the app's own code run was left to a manual devtools session (its task 3.3). Running that check by hand exposed its weaknesses:
- the planned "window title" signal was meaningless, because Tauri's native title bar doesn't follow `document.title`;
- probing meant pasting JavaScript into a console, which damaged the page's layout;
- it has to be repeated by hand after every frontend change.

The maintainer asked for it to be automated.

The GUI tests already load the real `src/index.html` in headless Chromium with a fake `window.__TAURI__`, but from `file://` with no policy at all. So nothing automated notices if a future frontend edit adds an inline script, inline handler or `eval` that the policy would block. The app would then break only inside the real window. Nothing checks either that the policy actually refuses injected script.

## What Changes

- **The GUI tests serve the page under the same policy the app enforces.** They load `src/` through a local route instead of `file://`, with a `Content-Security-Policy` header built the way Tauri 2 builds it: the policy from `tauri.conf.json`, plus a `script-src 'self'` carrying a `'sha256-…'` hash for each non-empty inline `<script>` in the HTML, hashed after normalising line endings to LF.
- **Every existing GUI scenario runs under that policy, and any violation fails it.** The page records every `securitypolicyviolation` event, and a scenario fails on any, just as it already fails on any uncaught script error.
- **A new scenario proves injected script is refused:**
  - an inline event handler added to the page after load doesn't run;
  - a string passed to `setTimeout` doesn't run;
  - both are reported as violations.

  Checking page state, rather than the window title, makes it discriminate: without the policy header, both run and the scenario fails.
- **Not in scope:**
  - Running the tests in WebKitGTK or WebView2.
  - Exercising Tauri's real IPC endpoints; the fake bridge doesn't use them.
  - Changing the policy itself.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `automated-tests`: adds a requirement that the GUI tests run the page under the application's effective content security policy, fail on any violation during normal scenarios, and prove that injected inline handlers and string evaluation are refused.

## Impact

- **Changed:** `tests/test_gui.py` (page loading through a route with a CSP header, violation recording, a new scenario, and computing the policy from `tauri.conf.json` plus `index.html`). `tests/fake_tauri.js` is unchanged: Playwright init scripts run outside page CSP.
- **Relationship to `harden-webview-csp-and-tls`:** that change's manual task 3.3 becomes a one-time confirmation that the real webview enforces the same policy. Once this change is in, a policy regression in the page is caught automatically. That change's artifacts aren't edited here.
- **Limits:**
  - Chromium's CSP enforcement stands in for WebKitGTK's and WebView2's; they implement the same standard.
  - IPC reachability under `connect-src` remains a real-app check (`harden-webview-csp-and-tls` 3.2 on Linux, 3.4 on Windows).
- **Runtime:** a few hundred milliseconds more for the GUI suite.
