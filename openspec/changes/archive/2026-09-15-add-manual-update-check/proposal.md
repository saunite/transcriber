## Why

The GUI has no way to tell a user that a newer release exists. README says "There's no auto-update; to upgrade, download the new version", so users only find out by visiting the releases page themselves.

The project's identity is offline privacy (README: "100% offline and local - all data stays on your machine"). Today the desktop app makes no network requests at all: it always passes the bundled model's `--model-path` to the engine (`sidecar.rs`), and its window CSP only allows IPC. During exploration on 2026-09-14 the maintainer chose a **manual** check: the app contacts GitHub only when the user clicks a button. There's no automatic or background check, and no setting. Automatic install (the Tauri updater) was set aside as much more work (signing keys, a published manifest, per-format gaps) for the current stage.

## What Changes

- **A "Check for updates" button** in the settings rail, under Theme.
- **A Rust command, `check_for_update`**, running off the UI thread. It makes one HTTPS `GET` to `https://api.github.com/repos/saunite/transcriber/releases/latest` (GitHub's newest published, non-draft, non-prerelease release), reads `tag_name`, and compares it as a semantic version with the app's own version. It returns one of:
  - up to date, with the current version;
  - update available, with the new version;
  - no release published yet (GitHub 404);
  - couldn't check (offline, timeout, rate-limited, unexpected response).
- **A Rust command, `open_releases_page`**, opening the fixed URL `https://github.com/saunite/transcriber/releases/latest` in the default browser through the official opener plugin. No URL from the network or the page is ever opened, and the page gets no permission to open URLs itself.
- **The UI shows the result as a note:** "You're up to date (0.1.0)", "Transcriber 0.2.0 is available" with an **Open download page** action, "No releases published yet", or "Couldn't check for updates". A failure is never an error dialog, and the rest of the app is unaffected.
- **README:** the offline feature line and the "no auto-update" sentence say the only network request the app makes is this manual check.
- **New Rust dependencies:** `ureq` (HTTPS client; rustls TLS) and `tauri-plugin-opener`. `semver` and `serde_json` already come with Tauri. `THIRD-PARTY-LICENSES.txt` gets a note for any non-MIT/Apache licence the TLS stack adds.
- **Not in scope:**
  - Automatic or scheduled checks, and downloading or installing updates.
  - Pre-release channels.
  - The CLI.
  - *Observed while planning, not acted on:* the GUI's Model dropdown (tiny through large) has no effect, because the bundled model path always wins. Worth its own change.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `desktop-gui`: adds a requirement for a user-initiated update check. It contacts the release host only when the user asks, reports up to date, update available, no release yet, or couldn't check, and opens only the project's own releases page. The application makes no other network request.

## Impact

- **Changed:** `src-tauri/Cargo.toml` (and `Cargo.lock`), `src-tauri/src/main.rs` (the plugin, and registering the commands), a new `src-tauri/src/update.rs`, `src/index.html` and `src/main.js` (the button and note), `tests/test_gui.py` (the fake bridge answering the new commands, and the new scenarios), `README.md`, `THIRD-PARTY-LICENSES.txt`.
- **Unchanged:** the CSP (the request is native, not from the page), the engine, packaging and CI.
- **Verification:**
  - Unit tests for the version comparison and response handling, and GUI tests for every note state.
  - A real check against GitHub on Linux, which today can only return "No releases published yet", since `v0.1.0` is still a draft.
  - The "update available" path against the live API needs a published release, so it's also checked by pointing a debug build at an older version.
