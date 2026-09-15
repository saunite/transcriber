## Context

See proposal.md - Why. The facts this design rests on, 2026-09-14:

- **How `tests/test_gui.py` loads the page today.** `open_page()` creates a page, records `pageerror`, adds `tests/fake_tauri.js` (and optional canned responses) with `page.add_init_script`, then `page.goto(file://…/src/index.html)`. `report()` fails a scenario on any recorded page error. The test also reads `src-tauri/tauri.conf.json` as text for the `csp_problems()` check, added by `harden-webview-csp-and-tls`.
- **How Tauri 2 builds the policy it enforces.** Read in `tauri-codegen` 2.6.3 and `tauri` 2.11.5:
  - at build time, `inject_script_hashes` (`tauri-codegen/src/context.rs`) hashes every `script:not(:empty)` element's text, after `normalize_script_for_csp` turns CRLF and lone CR into LF, as `'sha256-<base64>'`;
  - at request time, `set_csp` and `replace_csp_nonce` (`tauri/src/manager/mod.rs`) take the configured policy, and when there are hashes or nonces they add to `script-src`, creating it if absent, with `'self'` first and then the hashes;
  - `style-src` is added the same way only for `<style>` elements, and `src/index.html` has none;
  - script nonces apply only to `script[src^='http']` (remote scripts), and there are none.

  So for `index.html` the enforced policy is the configured `default-src 'self'; connect-src ipc: http://ipc.localhost`, plus `script-src 'self' 'sha256-<theme script>'`.
- **A throwaway Playwright spike (Chromium, 2026-09-14),** serving a page with a route that sets `Content-Security-Policy`:
  - **with the policy and hash:** the init-script bridge ran, the hashed inline script ran, and the same-origin external script ran; an injected `<img onerror>` and `setTimeout("…")` did **not** run, and `securitypolicyviolation` reported `script-src-attr inline` and `script-src eval`;
  - **without the hash:** the inline script was blocked (`script-src-elem inline`);
  - **without the policy:** both injections ran and nothing was reported.
  - `page.evaluate` worked under the policy. An unrouted sub-request (the injected `<img src=x>`) made the handler raise, so unknown paths must get a 404.

## Goals / Non-Goals

**Goals:**
- Every GUI scenario runs under the page's real effective policy, and fails on any violation.
- One scenario proves injected script is refused, in a way that fails if the policy isn't applied.

**Non-Goals:**
- WebKitGTK or WebView2 engines, or Tauri's real IPC.
- Testing `connect-src`. The fake bridge makes no network calls, so a wrong `connect-src` stays a real-app check.

## Decisions

### 1. Serve `src/` through a Playwright route on `http://tauri.localhost`

`open_page()` routes `http://tauri.localhost/**`. It maps the URL path to a file under `src/` and fulfils it with a content type by extension (`.html`, `.js`, `.css`). Unknown paths get a 404, and so does any path that doesn't resolve inside `src/`. The HTML response carries the `Content-Security-Policy` header from Decision 2. The page then loads from `http://tauri.localhost/index.html` instead of `file://`, so `'self'` means that origin. That's also the origin Tauri uses on Windows.

**Rejected: injecting a `<meta http-equiv>` into the HTML.** Rewriting the served document would test a modified page. Also, `insertAdjacentHTML` probes interact with meta-delivered policy the same way, so a header is both simpler and closer to how Tauri delivers the policy on each asset response.

**Rejected: a real local HTTP server.** A route needs no port and no process, which is the same reason `file://` was chosen originally (automated-tests design Decision 2).

### 2. Compute the effective policy the way Tauri does

A helper `effective_csp(tauri_conf, html)`:
- reads `app.security.csp`;
- extracts the text of every non-empty inline `<script>` with `html.parser`, taking the element text exactly as written;
- normalises CR/CRLF to LF, and hashes each as `'sha256-<base64>'`;
- appends `script-src 'self' <hashes>` when there are hashes. The configured policy has no `script-src` today; if it ever gains one, the helper extends it rather than duplicating it, as `replace_csp_nonce` does.

It cites the Tauri source it mirrors. A future Tauri upgrade that changes the scheme can only make the test stricter than the app, never looser: extra hashes would be a Tauri addition, not ours.

### 3. Record violations and fail on them, like page errors

The existing init script chain gains a small listener. It pushes `violatedDirective` and `blockedURI` for each `securitypolicyviolation` into `window.__cspViolations`. `report()` reads it after each scenario and fails with the list when it isn't empty, in the same place page errors fail today. The injection scenario (Decision 4) reads and clears it itself, because its violations are expected.

### 4. The injection scenario checks state, with a control built in

After load, the scenario:
1. sets `window.__probe = 0` and inserts `<img src=x onerror="window.__probe=1">`;
2. sets `window.__evalran = 0` and calls `setTimeout("window.__evalran = 1", 0)`;
3. waits ~300 ms.

It asserts that both flags are still 0, and that the recorded violations include an inline-attribute (`script-src-attr`) and an `eval` violation. As the spike showed, the same steps without the policy header set both flags to 1, which is exactly what the "policy not applied" scenario requires the test to catch.

## Risks / Trade-offs

- **[Risk]** A future Tauri changes how it derives hashes, for example by also hashing `<style>`, so the test's policy drifts from the app's. → The helper cites the Tauri source, and it only ever adds our own inline-script hashes. Drift shows up as the real app refusing something the test allowed, which the manual real-app checks already cover.
- **[Risk]** The route changes page behaviour compared to `file://`, for example `localStorage` origin or relative URLs. → Every existing scenario must still pass, which task 2.1 verifies before any new assertion is added. `http://tauri.localhost` is also closer to the real app's origin than `file://`.
- **[Trade-off]** Chromium stands in for WebKitGTK and WebView2. CSP is a shared standard, and the real-webview confirmation is `harden-webview-csp-and-tls`'s one-time manual check.
