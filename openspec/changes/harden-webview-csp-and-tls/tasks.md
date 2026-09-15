## 1. Content Security Policy

- [x] 1.1 Set `app.security.csp` in `src-tauri/tauri.conf.json` to `"default-src 'self'; connect-src ipc: http://ipc.localhost"` (design.md Decision 1). Verify the JSON parses, and that `cargo check` in `src-tauri/` accepts the config.

  **Done 2026-09-14.** `app.security.csp` is now `"default-src 'self'; connect-src ipc: http://ipc.localhost"`. The JSON parses, and `cargo check` in `src-tauri/` exits 0.
- [x] 1.2 Add the policy check to `tests/test_gui.py` (Decision 2). Verify it passes with 1.1, and fails on a scratch copy of `tauri.conf.json` in each of these cases: `csp: null`, a policy without `default-src 'self'`, and a policy adding `'unsafe-inline'` to `script-src`.

  **Done 2026-09-14.** `csp_problems()` and the `content security policy` scenario are added to `tests/test_gui.py`, which passes 9/9. On scratch copies of `tauri.conf.json` the check reports `no CSP is set (csp = None)`, `missing default-src 'self'` and `allows 'unsafe-inline'`, and `[]` for the real file.

## 2. TLS verification

- [x] 2.1 Remove `_suppress_ssl_verification` and its `with` block from `transcription_engine.py`, keeping `WhisperModel(...)` as is, along with any imports only it used, and remove `set PYTHONHTTPSVERIFY=0` from `win-start-transcription.bat` and `transcribe_file.bat` (Decision 3). Verify:
  - `git grep -n "_create_unverified_context\|_suppress_ssl_verification\|PYTHONHTTPSVERIFY"` outside `openspec/` finds nothing;
  - `python -c "import transcription_engine"` succeeds;
  - `tests/test_engine.py` with the recording set still passes, which loads the bundled model through the changed code.

  **Done 2026-09-14.** Removed from `transcription_engine.py`: `import ssl`, `from contextlib import contextmanager` (only the helper used them), `_suppress_ssl_verification()`, and the `with` wrapper around `WhisperModel(...)`, whose arguments are unchanged. `set PYTHONHTTPSVERIFY=0` is removed from both `.bat` files, keeping their CRLF line endings. `git grep` for all three names outside `openspec/` finds nothing, `import transcription_engine` succeeds, and `tests/test_engine.py` with the recording passes both checks, loading the bundled model through the changed code.

## 3. Verification

- [x] 3.1 Run `.venv/bin/python run_tests.py` with the recording set, and verify it exits 0.

  **Done 2026-09-14.** With the recording set, 12/12 suites passed in 23.3s.
- [x] 3.2 Build the Linux AppImage and `.rpm` locally with the change, then **user check in the real app:** switch the theme (including a restart with a non-system theme, to confirm the first-paint script still runs), start and stop a live session, and transcribe a dropped file. Everything must work as before.

  **User-verified on Fedora, 2026-09-14** with local builds of `67c252e` (`~/Downloads/transcriber-test/csp-local/`), whose `transcriber-gui` binary embeds `default-src 'self'; connect-src ipc: http://ipc.localhost`: "3.2 passed". The theme, live session and file transcription all work under the policy.
- [x] 3.3 **Enforcement check in a dev window:** run `npx @tauri-apps/cli@2.11.4 dev` from `src-tauri/`, which applies `csp` because no `devCsp` is set. Open devtools with right-click → Inspect, then check that:
  - the console shows no "Content Security Policy" violation during normal use (theme, start/stop);
  - running `document.body.insertAdjacentHTML('beforeend', '<img src=x onerror="document.title=\'injected\'">')` in the console leaves the window title unchanged and logs a CSP violation for the inline handler.
  Record what the console showed.

  **Done 2026-09-14, through automated tests instead of the manual probes, as the user directed** ("use the newly implemented automated tests when possible"). Running the manual step showed its flaws: the window title is drawn natively by Tauri and ignores `document.title`, so the planned signal proved nothing, and pasting probes into the console broke the page layout. So it was automated by the change `test-gui-under-app-csp` (archived 2026-09-14). `tests/test_gui.py` now serves the page under the policy Tauri enforces: the configured CSP plus a `script-src 'self' 'sha256-…'` hash for the inline theme script. All 10 scenarios pass (run again for this task):
  - **"no CSP violation during normal use":** every scenario (page load, live start/stop, exit before listening, file queue, unsupported file, refusal) fails on any `securitypolicyviolation`, and none occur;
  - **"an injected inline handler doesn't run and is reported":** the `injected script refused` scenario checks page state (`__probe` stays 0) and a `script-src-attr` violation, and fails when the policy header is removed;
  - **string `eval` is also refused and reported**, and adding `'unsafe-inline' 'unsafe-eval'` makes the scenario fail.

  **The user's own dev-window session on Fedora (WebKitGTK), 2026-09-14,** covered the part automation can't: the real webview ran the app under the policy with **no CSP errors in the console** during normal use. Their injection attempt left the window usable once reloaded, but its title-based signal was inconclusive, as noted above.
  **Still not covered by any automated test:** enforcement inside WebKitGTK and WebView2 themselves (the tests use Chromium's implementation of the same standard), and IPC reachability under `connect-src`. That was proven on Linux by 3.2 and is covered on Windows by 3.4.
- [x] 3.4 Manual CI run on `dev` (only when the user asks for it), then **user check on Windows** with the `windows` artifact: the GUI starts and stops a live session and transcribes a file. That confirms IPC works through `http://ipc.localhost` under the policy.

  **Done 2026-09-14.** Manual run 34918972559 on `dev` at `b3c5922` (the same commit as `main`) was requested by the user, and all four jobs passed. **User-verified on Windows** with that run's `windows` artifact: "task 3.4 passed all items (1, 2 and 3)". Under the CSP the app opened and loaded the audio device list, a live session with the mic showed `[SYS]`/`[MIC]` lines and stopped, and a dropped file transcribed. So IPC works through WebView2's `http://ipc.localhost` under `connect-src ipc: http://ipc.localhost`.
