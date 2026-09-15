## Context

See proposal.md - Why. Facts, 2026-09-14:

- **The app makes no network requests today.** Both sidecar launch paths pass `--model-path` with the bundled model (`src-tauri/src/sidecar.rs` 469-471 and 823-824), and `tauri.conf.json`'s CSP is `default-src 'self'; connect-src ipc: http://ipc.localhost`.
- **`src-tauri/src/main.rs`** registers `tauri_plugin_shell` and `tauri_plugin_dialog`, and five commands in `generate_handler!`. Capabilities grant `core:default`, `dialog:default` and `core:window:allow-set-theme`.
- **Already available:** `semver` is in the runtime graph through `tauri-utils`, and Tauri's `PackageInfo::version` is a `semver::Version` taken from `tauri.conf.json` (`0.1.0`). `serde_json` also comes with Tauri. `reqwest` appears in `Cargo.lock` only through build tooling, so the app has no HTTP client.
- **The GitHub API:** `GET https://api.github.com/repos/saunite/transcriber/releases/latest` returns the newest published, non-draft, non-prerelease release, and requires a `User-Agent` header. Today it returns **404** (`{"message":"Not Found",…}`), because `v0.1.0` is a draft. Unauthenticated calls are limited to 60 an hour per IP, which fits a manual button.
- **Crates:** `ureq` 3.4.2 (MIT OR Apache-2.0, rustls by default, with an optional `platform-verifier` feature) and `tauri-plugin-opener` 2.5.5 (Tauri 2; the 3.x line is alpha).
- **Tauri 2 runs a non-`async` command on the main thread,** so a blocking call inside one would freeze the window.
- **Frontend:** the settings rail ends with the Theme `<label class="rail-field">` in `src/index.html`. `showNote()` in `src/main.js` displays dismissible notes. `tests/test_gui.py`'s command-drift check requires every `invoke("…")` to be registered in `main.rs`.

## Goals / Non-Goals

**Goals:**
- One manual check that never runs by itself, never opens a URL taken from the network, and never breaks anything when offline.
- Everything except the live HTTP call is testable offline.

**Non-Goals:**
- Automatic checks, downloads or installs, pre-releases, the CLI, and the Model dropdown observation.

## Decisions

### 1. The check lives in Rust, in a new `src-tauri/src/update.rs`

- **Pure function:** `fn classify(current: &semver::Version, status: u16, body: &str) -> UpdateStatus` maps an HTTP status and body to `UpToDate { current }`, `Available { latest }`, `NoRelease` (404), or `Unavailable` (anything else, including a missing or unparsable `tag_name`). A leading `v` is stripped before parsing, and an equal or older version counts as up to date. It's easy to unit test with no network.
- **Network function:** `fn fetch_latest() -> Result<(u16, String), String>` makes the `ureq` call: fixed URL, `User-Agent: Transcriber/<version>`, `Accept: application/vnd.github+json`, and an overall timeout of about 10 seconds. It returns the status code and body, including for non-2xx statuses, which `ureq` 3 reports as errors unless told otherwise.
- **Command:** `#[tauri::command] async fn check_for_update(app) -> UpdateStatus` runs `fetch_latest` on `tauri::async_runtime::spawn_blocking`, with any transport error turning into `Unavailable`. `UpdateStatus` serialises with `serde` as `{ "state": "…", "version": "…" }` for the page.

**Rejected: `tauri-plugin-http` from JavaScript.** The request would come from the page, so the CSP would have to allow `api.github.com` and the page would get network permissions, which reverses the hardening just made.

**Rejected: the Python sidecar making the check.** It already has TLS, but it adds a 2–3 second start per click, needs the app version passed in, and puts an app concern into the transcription engine.

### 2. `ureq` with the operating system's certificate store

`ureq = { version = "3", default-features = false, features = ["rustls", "platform-verifier"] }`, with the exact feature names confirmed against 3.4.2's manifest at implementation time. Checking certificates against the OS trust store means a corporate TLS-inspecting proxy whose CA is installed on the machine works, without ever turning verification off. gzip and JSON features are unneeded: `serde_json::from_str` parses the body, and the response is small.

**Rejected: `reqwest`.** It pulls in tokio/hyper machinery for one GET, where `ureq` is blocking and small.

### 3. Opening the page: a fixed URL, from Rust

`#[tauri::command] fn open_releases_page(app)` calls `app.opener().open_url("https://github.com/saunite/transcriber/releases/latest", None::<&str>)` from `tauri-plugin-opener`, registered with `.plugin(tauri_plugin_opener::init())`. The URL is a constant, never taken from the API response. The page gets no `opener:` capability, so script in the window can't open anything itself. The repository slug is one Rust constant shared by both URLs.

### 4. UI: a button and a note, with no new layout

A `<button id="check-updates-btn" class="…">Check for updates</button>` goes in its own `rail-field` under Theme, reusing an existing button style. On click it disables itself and shows "Checking…", then invokes `check_for_update` and reports the result through `showNote()`:
- **up to date:** "You're up to date (0.1.0)";
- **available:** "Transcriber 0.2.0 is available", with an **Open download page** control that invokes `open_releases_page`;
- **no release:** "No releases published yet";
- **unavailable:** "Couldn't check for updates. Check your connection and try again."

All text goes through `textContent`, as elsewhere. `showNote` currently takes plain text, so the "available" note needs a small extension: an optional action label and callback, added without changing existing callers.

### 5. Licences

Any licence in the new dependency tree beyond MIT/Apache-2.0 gets named in `THIRD-PARTY-LICENSES.txt`'s desktop-shell section: `ring` (ISC-style) if rustls brings it, and `webpki-roots` or `rustls-platform-verifier` terms if present. The task reads the actual list from `cargo metadata` rather than guessing.

## Risks / Trade-offs

- **[Risk]** GitHub rate limits or API changes → the check returns `Unavailable`, the user sees "Couldn't check", and nothing else is affected.
- **[Risk]** A tag that isn't semver, or doesn't match the app version → `Unavailable` rather than a wrong verdict. The release workflow already enforces that tags match the version.
- **[Risk]** The live "update available" path can't be exercised against GitHub until a release is published. → `classify` is unit-tested with real GitHub response bodies. A manual check of the available path temporarily builds a debug app with an older version, or feeds `classify` a captured response.
- **[Trade-off]** The README's "100% offline" becomes "offline unless you click Check for updates". That's honest, and it's what the maintainer chose.
- **[Trade-off]** One more native dependency tree (TLS) in the Rust binary, about 1–2 MB, which is negligible next to the ~290 MB packages.
