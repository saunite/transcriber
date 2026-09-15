## 1. Rust

- [ ] 1.1 Add `ureq` (rustls with the platform verifier, no default features; confirm the feature names against 3.4.2's manifest), `tauri-plugin-opener = "2"` and an explicit `semver = "1"` to `src-tauri/Cargo.toml`. Verify `cargo check` passes, and that `cargo tree -i semver` still shows a single `semver` version.
- [ ] 1.2 Add `src-tauri/src/update.rs` with `classify(current, status, body)`, `fetch_latest()` and the `UpdateStatus` enum (design.md Decision 1). Add unit tests for `classify`: a newer `v0.2.0` → `Available 0.2.0`; `v0.1.0` for current 0.1.0 → `UpToDate`; an older tag → `UpToDate`; a tag without the `v` → still parsed; status 404 → `NoRelease`; status 403 or 500 → `Unavailable`; a 200 body without `tag_name`, or with a non-semver tag → `Unavailable`. Use a real GitHub releases JSON body as the fixture. Verify `cargo test` passes, and fails when the `v`-prefix strip is removed.
- [ ] 1.3 Add the commands `check_for_update` (async, `spawn_blocking`) and `open_releases_page` (fixed URL through the opener plugin) (Decisions 1 and 3). Register `tauri_plugin_opener::init()` and both commands in `main.rs`. Verify `cargo check`, and that `capabilities/default.json` is unchanged (no `opener:` permission for the page).

## 2. Frontend

- [ ] 2.1 Add the "Check for updates" button under Theme in `src/index.html`, and its handler in `src/main.js`: disable while checking, then a note for each of the four states. Extend `showNote` with an optional action, used for "Open download page" (Decision 4). Verify `node --check src/main.js`, and that the existing GUI tests still pass, including command drift and the policy scenarios.
- [ ] 2.2 Add GUI scenarios to `tests/test_gui.py`, where the fake bridge answers `check_for_update` with each state:
  - **available:** the note shows "0.2.0 is available", and clicking its action invokes `open_releases_page`;
  - **up to date:** shows "You're up to date (0.1.0)";
  - **no release:** shows "No releases published yet";
  - **unavailable:** shows "Couldn't check for updates", and the button is enabled again afterwards.
  Also check that loading the page never invokes `check_for_update` by itself. Verify they pass, and that the no-automatic-check assertion fails if a check is temporarily triggered on page load.

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
