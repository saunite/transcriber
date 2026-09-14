## Why

A whole-codebase security review on 2026-09-14 found no exploitable vulnerability, but flagged two hardening gaps worth closing while they are cheap.

1. **The app window has no Content Security Policy** (`src-tauri/tauri.conf.json`: `"security": { "csp": null }`), and `app.withGlobalTauri` exposes the IPC bridge to any script on the page. No injection path exists today: every untrusted string (transcript text, engine log lines, file names, device names) goes in through `textContent`. But nothing backs that up. If a future change ever let script run in the window, it could call `start_live_session`, whose `outputPath` is passed straight through, and write a transcript to a file of its choosing. A CSP limiting the page to the app's own bundled code is the standard backstop, and Tauri 2 supports it directly: at build time it adds hashes for the app's own inline scripts to the policy.
2. **TLS certificate verification is switched off in two places:**
   - `transcription_engine.py` wraps model loading in `_suppress_ssl_verification()`, which swaps `ssl._create_default_https_context` for an unverified context, described as "for corporate network compatibility";
   - `win-start-transcription.bat` and `transcribe_file.bat` set `PYTHONHTTPSVERIFY=0`.

   Neither does anything today. Model downloads go through `huggingface_hub` 1.30, which uses `httpx` with its own certificate store and never reads Python's default HTTPS context. `PYTHONHTTPSVERIFY` is only honoured by a few patched distro Pythons. But both advertise "we turn off certificate checks", and would silently weaken any future code path that does use `urllib`.

## What Changes

- **Set a CSP in `tauri.conf.json`:** `default-src 'self'; connect-src ipc: http://ipc.localhost`. The page may load only its own files and talk only to Tauri's IPC endpoints (`ipc:` on Linux and macOS, `http://ipc.localhost` on Windows). Inline and remote scripts, `eval`, and remote connections are refused. Tauri's build-time hash injection keeps the existing inline theme script in `index.html` working.
- **A test guards the policy.** `tests/test_gui.py` fails if `tauri.conf.json`'s CSP is missing, lacks `default-src 'self'`, or allows `'unsafe-inline'` or `'unsafe-eval'` for scripts.
- **Remove `_suppress_ssl_verification`** and its use around `WhisperModel(...)`, and remove `set PYTHONHTTPSVERIFY=0` from both batch launchers. Certificate verification then stays at the libraries' defaults.
- **Not in scope:**
  - Validating `outputPath` in Rust. It's defence-in-depth behind the CSP, and a real UX decision about where transcripts may be saved.
  - Checksum-verifying the model download in CI.
  - `dangerousDisableAssetCspModification`, freezing the prototype, or other Tauri security toggles.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `desktop-gui`: adds a requirement that the application window runs only the application's own bundled code and can reach only the application itself, so injected or remote script is refused by the window. The TLS removal changes no specified behaviour, since no spec promises the corporate-network workaround.

## Impact

- **Changed:** `src-tauri/tauri.conf.json`, `transcription_engine.py` (the helper and its call are removed), `win-start-transcription.bat`, `transcribe_file.bat`, `tests/test_gui.py`.
- **Unchanged:** the IPC commands, the frontend code, and the engine's behaviour.
- **Risk to watch:** a CSP that's too strict would break the window, for example IPC calls, the theme script or styles. The Playwright GUI tests load the page in Chromium without Tauri's CSP, so they can't catch that. Verification is the real app: a local Linux build, and a Windows CI build, because Windows reaches IPC through `http://ipc.localhost`. macOS gets no hardware check.
