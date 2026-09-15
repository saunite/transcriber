## 1. Policy computation

- [ ] 1.1 Add `effective_csp(tauri_conf: Path, html: Path) -> str` to `tests/test_gui.py` (design.md Decision 2), citing `tauri-codegen` 2.6.3 `inject_script_hashes` / `normalize_script_for_csp` and `tauri` 2.11.5 `replace_csp_nonce`. Verify:
  - for today's tree it returns `default-src 'self'; connect-src ipc: http://ipc.localhost; script-src 'self' 'sha256-…'`, with exactly one hash;
  - that hash equals a hash computed separately (Python `hashlib` plus `base64`) over the theme `<script>` text;
  - on a scratch HTML with a CRLF inline script, the hash matches the LF-normalised text, not the raw text.

## 2. Serve the page under the policy

- [ ] 2.1 Change `open_page()` to route `http://tauri.localhost/**` to files under `src/` (Decision 1): content type by extension, 404 for unknown paths or paths escaping `src/`, and the `effective_csp` header on responses. Load `http://tauri.localhost/index.html` instead of `file://`. Verify every existing GUI scenario still passes: command drift, listening wording, CSP config check, page loads, live start/stop, exit before listening, file queue, unsupported file, refusal shown.
- [ ] 2.2 Record `securitypolicyviolation` events into `window.__cspViolations` from an init script, and make `report()` fail a scenario whose page recorded any (Decision 3). Verify:
  - all scenarios still pass, with no violations;
  - a scratch copy of `src/index.html` with an added inline `onclick="…"` attribute, served by a temporary switch of the route's source directory, makes "page loads" fail and name the `script-src-attr` violation;
  - so does a scratch copy whose theme `<script>` text is edited without any hash change being possible (proving the hash is load-bearing).
  Restore both.

## 3. Injection scenario

- [ ] 3.1 Add the "injected script is refused" scenario (Decision 4). Verify:
  - it passes;
  - with the CSP header temporarily omitted from the route, it fails because `__probe` and `__evalran` became 1;
  - with the header present but `'unsafe-inline' 'unsafe-eval'` temporarily appended to `script-src`, it also fails.
  Restore.

## 4. Full run

- [ ] 4.1 Run `.venv/bin/python run_tests.py` with the recording set. Verify it exits 0, and record the GUI suite's duration against the previous ~2.2s.
