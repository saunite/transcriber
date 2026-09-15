## 1. Rust

- [x] 1.1 Add `ureq` (rustls with the platform verifier, no default features; confirm the feature names against 3.4.2's manifest), `tauri-plugin-opener = "2"` and an explicit `semver = "1"` to `src-tauri/Cargo.toml`. Verify `cargo check` passes, and that `cargo tree -i semver` still shows a single `semver` version.

  **Done 2026-09-14.** Added `tauri-plugin-opener = "2"` (2.5.5), `ureq = { version = "3", default-features = false, features = ["rustls", "platform-verifier"] }` (3.4.2; feature names confirmed from its crates.io manifest: `rustls` pulls in the ring provider and webpki roots, `platform-verifier` adds `rustls-platform-verifier`, and the default `gzip` is dropped) and `semver = "1"`. `cargo check` passes. `Cargo.lock` holds a single `semver` package (1.0.28), already used by `tauri-utils`.
- [x] 1.2 Add `src-tauri/src/update.rs` with `classify(current, status, body)`, `fetch_latest()` and the `UpdateStatus` enum (design.md Decision 1). Add unit tests for `classify`: a newer `v0.2.0` → `Available 0.2.0`; `v0.1.0` for current 0.1.0 → `UpToDate`; an older tag → `UpToDate`; a tag without the `v` → still parsed; status 404 → `NoRelease`; status 403 or 500 → `Unavailable`; a 200 body without `tag_name`, or with a non-semver tag → `Unavailable`. Use a real GitHub releases JSON body as the fixture. Verify `cargo test` passes, and fails when the `v`-prefix strip is removed.

  **Done 2026-09-14.** `src-tauri/src/update.rs` has `UpdateStatus` (serialised with `#[serde(tag = "state", content = "version", rename_all = "snake_case")]`), `classify()` and `fetch_latest()`. `fetch_latest` uses ureq 3's `Agent::config_builder()` with `timeout_global(10s)`, `http_status_as_error(false)` and `RootCerts::PlatformVerifier`, and sends `User-Agent: Transcriber/<version>` and `Accept: application/vnd.github+json`. The fixture `src/testdata/github-latest-release.json` has the fields of a real GitHub `releases/latest` response, captured from astral-sh/uv, with `tag_name` set to `v0.2.0`. Seven unit tests pass: newer, same/older, no `v` prefix, 404, 403/500, unusable bodies, and serialisation. With the `v`-prefix strip removed, `newer_release_is_available` and `same_or_older_release_is_up_to_date` fail. **Added beyond the task text:** an `#[ignore]`d live test, `live_github_request_completes`, run on demand with `cargo test -- --ignored live_github`. Run once here, it passed: a real TLS request through the OS trust store reached GitHub and got today's 404, which classifies as `NoRelease`. It never runs in the normal suite.
- [x] 1.3 Add the commands `check_for_update` (async, `spawn_blocking`) and `open_releases_page` (fixed URL through the opener plugin) (Decisions 1 and 3). Register `tauri_plugin_opener::init()` and both commands in `main.rs`. Verify `cargo check`, and that `capabilities/default.json` is unchanged (no `opener:` permission for the page).

  **Done 2026-09-14.** The commands `check_for_update` (async, `spawn_blocking`, any transport error → `Unavailable`) and `open_releases_page` (a fixed `https://github.com/saunite/transcriber/releases/latest` through `OpenerExt::open_url`) are registered in `main.rs`, along with `tauri_plugin_opener::init()`. `cargo test` passes 20/20, and `capabilities/default.json` is unchanged, with no `opener:` permission for the page.

## 2. Frontend

- [x] 2.1 **Design the control and the result notes with the `impeccable` skill** (design.md Decision 4), operating on the `src-index-html` surface and following `.impeccable/surfaces/src-index-html.md` and `DESIGN.md`. The pass must settle:
  - placement in the rail at both rail widths;
  - the quiet-button treatment and its checking state;
  - the note-with-action variant, resolving the click-to-dismiss conflict and keyboard access;
  - the neutral (non-MIC-red) failure treatment, and plain-language copy for all four results.
  Record its decisions and any placement change, with the reason, under this task. Verify:
  - light and dark themes, at a normal window and at the 640×480 minimum, captured the way `.impeccable/review/*.png` were;
  - "Start transcribing" is still the only filled control;
  - no MIC red is used for the failure state.

  **Done 2026-09-14.** The user chose the placement.
  - **Placement change: no note is used.** The result stays inline in a *nameplate* at the rail's foot, under Theme. Notes were rejected for three reasons: they appear top-right, far from a button at the bottom of a scrolling rail; a click on a note dismisses it, which conflicts with an action inside it; and the 8-second timeout would take the download action away. The note-with-action variant is therefore not needed, and notes stay action-free (recorded in DESIGN.md).
  - **Layout:** a `1px panel-edge` hairline, then a `Version` label with the running version as a mono readout (from `window.__TAURI__.app.getVersion()`, allowed by `core:default`), then the quiet **Check for updates** button.
  - **Checking state:** the button disables and reads "Checking…". No badge, no spinner.
  - **Result:** one `role="status"` line under the button.
    - `ink-soft` for "You're up to date (0.1.0).", "No releases published yet." and "Couldn't check for updates. Check your connection and try again."
    - A newer version reads "Transcriber 0.2.0 is available." in `ink` at weight 600, and shows a second quiet button, **Open download page**.
    - Failure is neutral, never MIC red, and uses no new colour.
  - **Verified** with Playwright under the app CSP, in light and dark, at 900×640 and 640×480, in the available and couldn't-check states (the longest):
    - no overflow (nameplate scrollWidth = clientWidth: 231px and 183px);
    - no CSP violations or script errors;
    - Start transcribing keeps its SYS fill as the only filled control;
    - result text contrast: 4.79:1 light and 9.76:1 dark for `ink-soft` on the panel, 11.7:1 for `ink`.
  - **Detector:** `detect.mjs` ran once over the three files. It ran in degraded regex mode, because its parser modules aren't installed. It reported 16 advisories, all on lines that predate this change (type-ramp and radius values), and none in the new nameplate block.
- [x] 2.2 Implement the design from 2.1 in `src/index.html`, `src/style.css` and `src/main.js`: the button handler (disabled while checking, then a note for each of the four states) and `showNote`'s optional action invoking `open_releases_page`, with existing callers unchanged. Verify `node --check src/main.js`, and that the existing GUI tests still pass, including command drift and the content-security-policy scenarios, since no inline handlers or styles may be introduced.

  **Done 2026-09-14.** Implemented as 2.1 settled, so `showNote` is untouched: there's no note action, and existing callers are unchanged. `index.html` adds the `.nameplate` block. `style.css` adds `.nameplate`, `.nameplate-id` and `.update-result` (the `available` state uses weight, not colour). `main.js` adds `checkForUpdate()`, which disables the button while it waits and maps each state to its message, with anything unexpected or a rejected invoke treated as `unavailable`. **Open download page** invokes `open_releases_page`; if that fails, a note says so. Text is set with `textContent`, and there are no inline handlers or styles. `node --check src/main.js` passes. All 11 GUI scenarios pass, including command drift, which now sees `check_for_update` and `open_releases_page`, and the CSP scenarios.
- [x] 2.3 Add GUI scenarios to `tests/test_gui.py`, where the fake bridge answers `check_for_update` with each state:
  - **available:** the note shows "0.2.0 is available", and clicking its action invokes `open_releases_page`;
  - **up to date:** shows "You're up to date (0.1.0)";
  - **no release:** shows "No releases published yet";
  - **unavailable:** shows "Couldn't check for updates", and the button is enabled again afterwards.
  Also check that loading the page never invokes `check_for_update` by itself. Verify they pass, and that the no-automatic-check assertion fails if a check is temporarily triggered on page load.

  **Done 2026-09-14.** `test_update_check` runs the fake bridge through `available`, `up_to_date`, `no_release`, `unavailable`, and a rejected invoke. For each, it asserts the result line's text, that the button is enabled again, and that **Open download page** is shown only for `available`, where clicking it invokes `open_releases_page`. Each page also checks that `check_for_update` was not called in the 200 ms after load. The wording is "the result line", not "the note" (see 2.1). The fake bridge gained `app.getVersion`. Passes. With `checkForUpdate();` temporarily appended to `main.js`, the scenario fails with "the page checked for updates without a click". The mutation was then reverted.
- [x] 2.4 Finish the Impeccable pass: run its finish review of the built UI against the direction contract, and record the verdict and any fixes applied. Then update `DESIGN.md` (and `.impeccable/design.json` where a component or token changed) with the new rail control and the note-with-action variant. Verify `DESIGN.md` documents both, and the review verdict is recorded under this task.

  **Done 2026-09-14.** The finish review was done inline against the direction contract, not by a separate reviewer agent. **Verdict: passes, no fixes needed.**
  - Controls stay down the rail's edge, and quiet treatment is used throughout. State is shown by the control itself (disabled, "Checking…"), never a badge.
  - No third accent, and MIC red is kept for instrument faults. The mono readout is used for data (the version), not as a costume.
  - Native buttons give keyboard access and the themed `:focus-visible` ring. The result is announced through `role="status"`.
  - Copy names the action and, on failure, the recovery.

  **Independent finish review, 2026-09-15, by the `impeccable-finish-reviewer` agent, after the inline review above.** The user asked for it. **Verdict: fix.** Topology, type, material, ground and fit all matched, and the ceiling was reached. It found four material issues, all applied:
  1. **Keyboard focus lost:** disabling the focused Check button dropped focus to the page, and it didn't come back. The button now uses `aria-disabled` and ignores clicks while checking.
  2. **Result may not be announced:** the result line went from `hidden` to filled in one step. It is now always rendered, and cleared at the start of each check.
  3. **"Checking…" unreadable:** at `opacity: 0.5` it measured about 2.2:1. `[aria-disabled]` keeps full `ink-soft` and uses `cursor: progress`.
  4. **Two equal buttons under "available":** **Check for updates** is now hidden, so **Open download page** is the one action, and it receives focus.

  `test_update_check` now drives the button by keyboard. It asserts focus stays on the Check button, or moves to **Open download page** when a newer version is found, and that the Check button is hidden then. It passes, and fails against the pre-fix `main.js`. Re-screenshotted once, in light and dark at 900×640 and 640×480, in the checking and available states: focus is held with a visible ring, the text colour is at full ink, there's no overflow, and no CSP violations or script errors. `DESIGN.md` and `design.json` describe the fixed behaviour.

  `DESIGN.md` gains a **Nameplate** component, adds both buttons to the Quiet button list, adds the rail foot to Layout, and notes under Notes (toast) that notes carry no actions. `.impeccable/design.json` gains a `Nameplate` component. Tokens are unchanged. Both files already ended with a stray `</content>` line, which makes `design.json` invalid JSON. That drift predates this change and was left alone.

## 3. Docs and licences

- [x] 3.1 Update README: the "100% offline and local" feature line, and the "There's no auto-update" sentence, now say the only network request is the manual **Check for updates** button, which only reports and opens the releases page. Verify both lines are changed and README mentions the button.

  **Done 2026-09-14.** The feature line now says the only network request is the desktop app's **Check for updates** button, and only on click. The "no auto-update" sentence now says where the button is and that it only reports and can open the releases page, with nothing downloaded or installed.
- [x] 3.2 List the new dependency tree's licences from `cargo metadata` (for the packages brought in by `ureq` and `tauri-plugin-opener`), and add any that aren't MIT or Apache-2.0 to `THIRD-PARTY-LICENSES.txt`'s desktop-shell section (Decision 5). Verify every non-MIT/Apache licence from that list is named.

  **Done 2026-09-14.** Compared `Cargo.lock` before f742a17 with now: 61 new crates, licences from `cargo metadata`. Crates that aren't MIT or Apache-2.0 (an OR that includes either counts as MIT/Apache): `ring` (Apache-2.0 AND ISC), `rustls-webpki` and `untrusted` (ISC), `subtle` (BSD-3-Clause), and `webpki-roots` and `webpki-root-certs` (CDLA-Permissive-2.0). All are named in the desktop-shell section under "Update check", and ISC and CDLA-Permissive-2.0 links were added to the full-texts list.

## 4. Verification

- [x] 4.1 Run `.venv/bin/python run_tests.py` with the recording set, and verify it exits 0.

  **Done 2026-09-14.** `run_tests.py` with `TRANSCRIBER_TEST_SPEECH` set: 12/12 passed, exit 0, including `cargo test` and the new `update check` GUI scenario.
- [x] 4.2 **Linux check of the built app, automated by `tests/test_e2e_linux.py`** (openspec/changes/add-e2e-gui-tests-linux; originally a manual user check). Its scenarios cover:
  - `update check online`: clicking **Check for updates** in the real debug app with a network gives a real verdict, "No releases published yet" while `v0.1.0` is a draft, and never "Couldn't check";
  - `update check offline` and `engine offline`: inside `unshare -rn` it shows "Couldn't check for updates", and transcription still works;
  - `no request at startup`: the app makes no request on startup, since strace sees no IPv4/IPv6 connect before the page has loaded;
  - `download page`: **Open download page** hands exactly the releases URL to the OS opener.

  **Done 2026-09-15.** The suite ran on this machine with the VPN off. It had been printing `SKIP` for the online check, because the VPN tunnel dropped GitHub's 140.82.112.0/22 range.
  - All six scenarios printed `PASS`: `update check online: No releases published yet.`, `download page`, `no request at startup`, `update check offline: Couldn't check for updates. Check your connection and try again.`, `download page offline`, and `engine offline` (speech sample transcribes, undecodable input fails cleanly).
  - Exit 0.
- **4.3 (moved, not done)** **The "update available" path against the real API.** On 2026-09-15, at the user's request, this moved to `openspec/backlog.md`, "The real release", step 3, because no release is published. It's no longer a checkbox here, so it doesn't hold up archiving. The original task text follows for reference.

  **Original task:** once any release is published, or with a temporary debug build whose `tauri.conf.json` version is lower than the published one, clicking the button shows the newer version, and **Open download page** opens `https://github.com/saunite/transcriber/releases/latest` in the browser. Record which method was used. If no release exists yet, this stays open.
