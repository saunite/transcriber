## 1. Rust

- [x] 1.1 Add `ureq` (rustls with the platform verifier, no default features; confirm the feature names against 3.4.2's manifest), `tauri-plugin-opener = "2"` and an explicit `semver = "1"` to `src-tauri/Cargo.toml`. Verify `cargo check` passes, and that `cargo tree -i semver` still shows a single `semver` version.

  **Done 2026-09-14.** Added `tauri-plugin-opener = "2"` (2.5.5), `ureq = { version = "3", default-features = false, features = ["rustls", "platform-verifier"] }` (3.4.2; feature names confirmed from its crates.io manifest: `rustls` pulls in the ring provider and webpki roots, `platform-verifier` adds `rustls-platform-verifier`, and the default `gzip` is dropped) and `semver = "1"`. `cargo check` passes. `Cargo.lock` holds a single `semver` package (1.0.28), already used by `tauri-utils`.
- [x] 1.2 Add `src-tauri/src/update.rs` with `classify(current, status, body)`, `fetch_latest()` and the `UpdateStatus` enum (design.md Decision 1). Add unit tests for `classify`: a newer `v0.2.0` → `Available 0.2.0`; `v0.1.0` for current 0.1.0 → `UpToDate`; an older tag → `UpToDate`; a tag without the `v` → still parsed; status 404 → `NoRelease`; status 403 or 500 → `Unavailable`; a 200 body without `tag_name`, or with a non-semver tag → `Unavailable`. Use a real GitHub releases JSON body as the fixture. Verify `cargo test` passes, and fails when the `v`-prefix strip is removed.

  **Done 2026-09-14.** `src-tauri/src/update.rs` has `UpdateStatus` (serialised with `#[serde(tag = "state", content = "version", rename_all = "snake_case")]`), `classify()` and `fetch_latest()`. `fetch_latest` uses ureq 3's `Agent::config_builder()` with `timeout_global(10s)`, `http_status_as_error(false)` and `RootCerts::PlatformVerifier`, and sends `User-Agent: Transcriber/<version>` and `Accept: application/vnd.github+json`. The fixture `src/testdata/github-latest-release.json` has the fields of a real GitHub `releases/latest` response, captured from astral-sh/uv, with `tag_name` set to `v0.2.0`. Seven unit tests pass: newer, same/older, no `v` prefix, 404, 403/500, unusable bodies, and serialisation. With the `v`-prefix strip removed, `newer_release_is_available` and `same_or_older_release_is_up_to_date` fail. **Added beyond the task text:** an `#[ignore]`d live test, `live_github_request_completes`, run on demand with `cargo test -- --ignored live_github`. Run once here, it passed: a real TLS request through the OS trust store reached GitHub and got today's 404, which classifies as `NoRelease`. It never runs in the normal suite.
- [x] 1.3 Add the commands `check_for_update` (async, `spawn_blocking`) and `open_releases_page` (fixed URL through the opener plugin) (Decisions 1 and 3). Register `tauri_plugin_opener::init()` and both commands in `main.rs`. Verify `cargo check`, and that `capabilities/default.json` is unchanged (no `opener:` permission for the page).

  **Done 2026-09-14.** The commands `check_for_update` (async, `spawn_blocking`, any transport error → `Unavailable`) and `open_releases_page` (a fixed `https://github.com/saunite/transcriber/releases/latest` through `OpenerExt::open_url`) are registered in `main.rs`, along with `tauri_plugin_opener::init()`. `cargo test` passes 20/20, and `capabilities/default.json` is unchanged, with no `opener:` permission for the page.

## 2. Frontend

- [ ] 2.1 **Design the control and the result notes with the `impeccable` skill** (design.md Decision 4), operating on the `src-index-html` surface and following `.impeccable/surfaces/src-index-html.md` and `DESIGN.md`. The pass must settle:
  - placement in the rail at both rail widths;
  - the quiet-button treatment and its checking state;
  - the note-with-action variant, resolving the click-to-dismiss conflict and keyboard access;
  - the neutral (non-MIC-red) failure treatment, and plain-language copy for all four results.
  Record its decisions and any placement change, with the reason, under this task. Verify:
  - light and dark themes, at a normal window and at the 640×480 minimum, captured the way `.impeccable/review/*.png` were;
  - "Start transcribing" is still the only filled control;
  - no MIC red is used for the failure state.
- [ ] 2.2 Implement the design from 2.1 in `src/index.html`, `src/style.css` and `src/main.js`: the button handler (disabled while checking, then a note for each of the four states) and `showNote`'s optional action invoking `open_releases_page`, with existing callers unchanged. Verify `node --check src/main.js`, and that the existing GUI tests still pass, including command drift and the content-security-policy scenarios, since no inline handlers or styles may be introduced.
- [ ] 2.3 Add GUI scenarios to `tests/test_gui.py`, where the fake bridge answers `check_for_update` with each state:
  - **available:** the note shows "0.2.0 is available", and clicking its action invokes `open_releases_page`;
  - **up to date:** shows "You're up to date (0.1.0)";
  - **no release:** shows "No releases published yet";
  - **unavailable:** shows "Couldn't check for updates", and the button is enabled again afterwards.
  Also check that loading the page never invokes `check_for_update` by itself. Verify they pass, and that the no-automatic-check assertion fails if a check is temporarily triggered on page load.

- [ ] 2.4 Finish the Impeccable pass: run its finish review of the built UI against the direction contract, and record the verdict and any fixes applied. Then update `DESIGN.md` (and `.impeccable/design.json` where a component or token changed) with the new rail control and the note-with-action variant. Verify `DESIGN.md` documents both, and the review verdict is recorded under this task.

## 3. Docs and licences

- [ ] 3.1 Update README: the "100% offline and local" feature line, and the "There's no auto-update" sentence, now say the only network request is the manual **Check for updates** button, which only reports and opens the releases page. Verify both lines are changed and README mentions the button.
- [ ] 3.2 List the new dependency tree's licences from `cargo metadata` (for the packages brought in by `ureq` and `tauri-plugin-opener`), and add any that aren't MIT or Apache-2.0 to `THIRD-PARTY-LICENSES.txt`'s desktop-shell section (Decision 5). Verify every non-MIT/Apache licence from that list is named.

## 4. Verification

- [ ] 4.1 Run `.venv/bin/python run_tests.py` with the recording set, and verify it exits 0.
- [ ] 4.2 Build locally (the AppImage/`.rpm`, or `tauri dev`) and **user check on Linux:**
  - clicking **Check for updates** with a network connection shows "No releases published yet" (the real state while `v0.1.0` is a draft);
  - with networking off, it shows "Couldn't check for updates" and transcription still works;
  - the app makes no request on startup (the check never fires by itself).
- [ ] 4.3 **The "update available" path against the real API:** once any release is published, or with a temporary debug build whose `tauri.conf.json` version is lower than the published one, clicking the button shows the newer version, and **Open download page** opens `https://github.com/saunite/transcriber/releases/latest` in the browser. Record which method was used. If no release exists yet, this stays open.
