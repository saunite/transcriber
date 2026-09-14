## Context

See proposal.md - Why. Facts from inspection, 2026-09-14:

- **`tauri.conf.json`:** `app.security.csp` is `null`, `app.withGlobalTauri` is `true`, and `build.frontendDist` is `../src`. Capabilities grant `core:default`, `dialog:default` and `set-theme`, not the shell plugin's JavaScript API.
- **Frontend resources:**
  - `src/index.html` has **one inline `<script>`**, the first-paint theme selector in `<head>`, plus `style.css` and `main.js`;
  - no `<img>`, no inline `style=` attributes, no inline event handlers;
  - `style.css` has no `url(...)`, `@import` or `@font-face`;
  - `main.js` sets styles only through the CSSOM (`el.style.marginTop = …`, `style.setProperty(...)`), which CSP does not restrict. It uses `innerHTML` only to clear elements (`= ""`), with no `eval` or `new Function`.
- **Tauri 2's build step modifies the policy:** `tauri-codegen` 2.6.3 (`context.rs`, `embedded_assets.rs`) and `tauri-utils` 2.9.3 (`html.rs`) parse the bundled HTML and add `'sha256-…'` hashes for inline scripts and styles to `script-src` and `style-src`, unless `dangerousDisableAssetCspModification` is set. So the theme script is allowed by hash, and injected inline script is not.
- **Tauri 2's IPC endpoints:** a custom `ipc:` scheme on Linux and macOS, and `http://ipc.localhost` on Windows (WebView2).
- **The TLS override:** `_suppress_ssl_verification()` in `transcription_engine.py` is a context manager around `WhisperModel(...)`. It patches `ssl._create_default_https_context`, which only `urllib` and `http.client` use. faster-whisper downloads through `huggingface_hub.snapshot_download`, and `huggingface_hub` 1.30.0 uses `httpx` (`utils/_http.py` imports `httpx`, not `requests`), which builds its own `SSLContext` from certifi. `PYTHONHTTPSVERIFY` is set in `win-start-transcription.bat:39` and `transcribe_file.bat:36`. No spec mentions certificate handling or a corporate-network workaround.

## Goals / Non-Goals

**Goals:**
- The window refuses any script that isn't the app's own, with no change to how the app looks or works.
- Nothing in the project turns off certificate verification.

**Non-Goals:**
- Restricting `outputPath` in Rust (proposal: out of scope).
- A per-directive policy finer than the app needs. The page loads no images, fonts or media, so `default-src 'self'` covers them.

## Decisions

### 1. The policy: `default-src 'self'; connect-src ipc: http://ipc.localhost`

- **`default-src 'self'`** covers `script-src`, `style-src`, `img-src`, `font-src`, `object-src`, `frame-src` and so on. Only files served from the app's own origin load. Tauri then adds hashes for the inline theme script.
- **`connect-src ipc: http://ipc.localhost`** allows exactly Tauri's IPC transport on every platform. `'self'` alone doesn't match the `ipc:` scheme, so without this every `invoke` would fail.
- **No `'unsafe-inline'` and no `'unsafe-eval'`:** that is the point of the change.

**Rejected: also adding `asset: http://asset.localhost` to `img-src`,** as Tauri's docs show. The app uses no asset-protocol URLs, and an allowance nobody uses is attack surface for nothing.

**Rejected: a `<meta http-equiv="Content-Security-Policy">` in `index.html`.** Tauri's config-level CSP is applied by the framework, together with the hash injection, and it can't drift from the bundled HTML. A meta tag would need hand-maintained hashes.

### 2. A test pins the policy's essentials

`tests/test_gui.py` gains a text-level check like its existing command-name and listening-line checks. It parses `src-tauri/tauri.conf.json` and fails unless `app.security.csp` is a non-empty string that contains `default-src 'self'` and contains neither `'unsafe-inline'` nor `'unsafe-eval'`. It can't prove the window enforces the policy (Playwright runs Chromium without Tauri), but it stops someone from quietly setting the policy back to `null` or loosening it.

### 3. Remove the TLS override, don't replace it

Delete the context manager, its `ssl` and `contextmanager` imports if nothing else uses them, and the `with` around `WhisperModel(...)`; delete both `set PYTHONHTTPSVERIFY=0` lines. There's no opt-out flag: nobody depends on the override, and a "disable TLS verification" option is itself a risk. Users behind TLS-intercepting proxies configure certificates the standard way (`SSL_CERT_FILE`, or `REQUESTS_CA_BUNDLE`/`HF_HUB_*` settings), which `httpx` and `huggingface_hub` already honour.

## Risks / Trade-offs

- **[Risk]** The CSP breaks something the static inspection missed, such as a style Tauri or WebKitGTK injects, or IPC on a platform using an unexpected scheme. → Verify in the real app: a Linux local build, where the user exercises theme, live and file flows, plus a devtools check for CSP violations in a `tauri dev` window; and a Windows CI build (`http://ipc.localhost`). macOS uses the same `ipc:` scheme as Linux, but can't be tested on hardware.
- **[Risk]** The hash injection doesn't cover the inline theme script, so the first paint flashes the wrong theme. → The devtools check catches a blocked inline script. The fallback would be moving that script to a file, which costs the first-paint guarantee, so it's only used if needed.
- **[Trade-off]** Removing the TLS helper could break a corporate-proxy user who depended on it. It has not affected the actual download client since `huggingface_hub` moved to `httpx`, so nobody can depend on it today.
