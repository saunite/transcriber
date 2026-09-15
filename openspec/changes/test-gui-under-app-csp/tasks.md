## 1. Policy computation

- [x] 1.1 Add `effective_csp(tauri_conf: Path, html: Path) -> str` to `tests/test_gui.py` (design.md Decision 2), citing `tauri-codegen` 2.6.3 `inject_script_hashes` / `normalize_script_for_csp` and `tauri` 2.11.5 `replace_csp_nonce`. Verify:
  - for today's tree it returns `default-src 'self'; connect-src ipc: http://ipc.localhost; script-src 'self' 'sha256-…'`, with exactly one hash;
  - that hash equals a hash computed separately (Python `hashlib` plus `base64`) over the theme `<script>` text;
  - on a scratch HTML with a CRLF inline script, the hash matches the LF-normalised text, not the raw text.

  **Done 2026-09-14.** `effective_csp()` uses a small `HTMLParser` that collects inline `<script>` text; `script:not(:empty)` means any script with text. For today's tree it returns `default-src 'self'; connect-src ipc: http://ipc.localhost; script-src 'self' 'sha256-jyVIFk31TRdaeYrq+p43Z6s24lYhOeJkc7NQJV9VTvY='`, with exactly one hash. That equals an independent `hashlib`/`base64` hash of the theme `<script>` text. A scratch HTML with a CRLF inline script yields the LF-normalised hash, not the raw one.

## 2. Serve the page under the policy

- [x] 2.1 Change `open_page()` to route `http://tauri.localhost/**` to files under `src/` (Decision 1): content type by extension, 404 for unknown paths or paths escaping `src/`, and the `effective_csp` header on responses. Load `http://tauri.localhost/index.html` instead of `file://`. Verify every existing GUI scenario still passes: command drift, listening wording, CSP config check, page loads, live start/stop, exit before listening, file queue, unsupported file, refusal shown.

  **Done 2026-09-14.** `serve_app()` routes `http://tauri.localhost/**` to `SRC_DIR`: content type by extension (`.html`, `.js`, `.css`), 404 for unknown types, missing files or paths resolving outside `src/`, and the `effective_csp` header on HTML. `open_page()` loads `http://tauri.localhost/index.html`. All 9 existing scenarios pass unchanged.
- [x] 2.2 Record `securitypolicyviolation` events into `window.__cspViolations` from an init script, and make `report()` fail a scenario whose page recorded any (Decision 3). Verify:
  - all scenarios still pass, with no violations;
  - a scratch copy of `src/index.html` with an added inline `onclick="…"` attribute, served by a temporary switch of the route's source directory, makes "page loads" fail and name the `script-src-attr` violation;
  - with `effective_csp` temporarily returning the policy without the inline-script hashes, "page loads" fails naming a `script-src-elem` violation for the theme script. That proves the computed hash is load-bearing: a hash computed from the served HTML can't be tested by editing that HTML.
  Restore both.

  **Done 2026-09-14.** A `RECORD_CSP_VIOLATIONS` init script pushes `violatedDirective blockedURI` into `window.__cspViolations`, and `report()` reads it before closing the page, failing with the list. All scenarios pass with no violations.
  - **Scratch `src/` whose `<body>` gains `onload="void 0"`:** every browser scenario fails with `content security policy violation: ['script-src-attr inline']`.
  - **`effective_csp` returning the policy without the hash:** every browser scenario fails with `['script-src-elem inline']`, proving the computed hash is load-bearing.
  Both were restored, and the suite passes again.

## 3. Injection scenario

- [x] 3.1 Add the "injected script is refused" scenario (Decision 4). Verify:
  - it passes;
  - with the CSP header temporarily omitted from the route, it fails because `__probe` and `__evalran` became 1;
  - with the header present but `'unsafe-inline' 'unsafe-eval'` temporarily appended to `script-src`, it also fails.
  Restore.

  **Done 2026-09-14.** `test_injected_script_refused` inserts `<img src="/no-such-file" onerror="window.__probe = 1">` (the route returns 404, so `onerror` would fire) and calls `setTimeout("window.__evalran = 1", 0)`. It asserts both flags stay 0 and that the violations include `script-src-attr` and `eval`, then clears those expected violations. It passes.
  - **CSP header removed from the route:** fails with "an injected inline event handler ran".
  - **`'unsafe-inline' 'unsafe-eval'` added to `script-src`:** fails with "string-evaluated code ran". The inline handler *stays* blocked in that case, because browsers ignore `'unsafe-inline'` when `script-src` also carries a hash (CSP Level 2). The `eval` probe is the one that catches this loosening, which is why the scenario checks both.
  Restored.

## 4. Full run

- [x] 4.1 Run `.venv/bin/python run_tests.py` with the recording set. Verify it exits 0, and record the GUI suite's duration against the previous ~2.2s.

  **Done 2026-09-14.** With the recording set, 12/12 suites passed in 23.1s. The GUI suite, now with 10 scenarios all served under the policy, took **2.7s**, against 2.2s before: +0.5s for the route and the injection scenario's 300 ms wait.
